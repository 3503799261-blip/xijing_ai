"""Bounded local image normalization and self-contained GLB validation.

This is a structural safety gate, not a claim of full Khronos conformance or
cultural correctness. A separate official validator/browser test is required.
"""
import hashlib
import io
import json
import math
import struct
import warnings
from PIL import Image, ImageOps, UnidentifiedImageError
from ..errors import ServiceError

MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_MODEL_BYTES = 64 * 1024 * 1024
MAX_IMAGE_PIXELS = 16_000_000
MAX_TEXTURE_PIXELS = 16_000_000
MAX_TOTAL_TEXTURE_PIXELS = 32_000_000
MAX_TEXTURE_IMAGES = 16
IMAGE_MIMES = {'image/png', 'image/jpeg', 'image/webp'}


def fail(code, text, status=422):
    raise ServiceError(code, text, status)


def normalize_image(raw, claimed_mime):
    if not raw or len(raw) > MAX_IMAGE_BYTES:
        fail('IMAGE_TOO_LARGE', '概念图必须非空且不超过10MB。', 413)
    if claimed_mime not in IMAGE_MIMES:
        fail('IMAGE_FORMAT_INVALID', '仅接受PNG、JPEG或WEBP概念图。', 415)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as original:
                formats = {'PNG': 'image/png', 'JPEG': 'image/jpeg', 'WEBP': 'image/webp'}
                if formats.get(original.format) != claimed_mime or getattr(original, 'n_frames', 1) != 1:
                    fail('IMAGE_FORMAT_INVALID', '文件实际格式与声明不一致，或不是单张图片。')
                width, height = original.size
                if width < 16 or height < 16 or width > 8192 or height > 8192 or width * height > MAX_IMAGE_PIXELS:
                    fail('IMAGE_DIMENSIONS_INVALID', '概念图尺寸应为16～8192像素，且总像素不超过1600万。')
                original.load()
                image = ImageOps.exif_transpose(original).convert('RGBA' if 'A' in original.getbands() else 'RGB')
                clean = Image.new(image.mode, image.size)
                clean.paste(image)
                output = io.BytesIO()
                clean.save(output, format='PNG', optimize=False)
                normalized = output.getvalue()
                if len(normalized) > MAX_IMAGE_BYTES:
                    fail('IMAGE_TOO_LARGE', '标准化后的概念图超过10MB，请降低尺寸。', 413)
                return normalized, {'mimeType': 'image/png', 'width': clean.width, 'height': clean.height,
                                    'size': len(normalized), 'hash': hashlib.sha256(normalized).hexdigest(),
                                    'sourceHash': hashlib.sha256(raw).hexdigest(), 'normalization': 'decoded_exif_removed_png_v1'}
    except ServiceError:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        fail('IMAGE_FORMAT_INVALID', '图片无法安全解码，请检查实际格式和尺寸。')


def integer(value, minimum=0):
    return isinstance(value, int) and not isinstance(value, bool) and value >= minimum


def index(value, sequence):
    return integer(value) and value < len(sequence)


def validate_textures(doc, binary, views):
    """Bound embedded PNG/JPEG decoding and ordinary texture/material links.

    Check every declared image, including unused ones. The GLB is preserved
    byte-for-byte; this gate never silently repairs or replaces model textures.
    """
    images, textures = doc.get('images', []), doc.get('textures', [])
    samplers, materials = doc.get('samplers', []), doc.get('materials', [])
    for sequence in (images, textures, samplers, materials):
        if not isinstance(sequence, list) or any(not isinstance(item, dict) for item in sequence):
            fail('MODEL_TEXTURE_INVALID', '模型纹理或材质资源表格式无效。')
    if len(images) > MAX_TEXTURE_IMAGES:
        fail('MODEL_TEXTURE_TOO_LARGE', '模型内嵌图片超过16张，请先离线优化。')
    total_pixels = 0
    for image in images:
        if image.get('mimeType') not in ('image/png', 'image/jpeg') or not index(image.get('bufferView'), views):
            fail('MODEL_TEXTURE_INVALID', '模型图片须为内嵌PNG/JPEG，并引用有效的bufferView。')
        view = views[image['bufferView']]
        if 'byteStride' in view:
            fail('MODEL_TEXTURE_INVALID', '模型图片缓冲区不能声明几何字节步长。')
        start = view.get('byteOffset', 0)
        raw = binary[start:start + view['byteLength']]
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('error', Image.DecompressionBombWarning)
                with Image.open(io.BytesIO(raw)) as decoded:
                    formats = {'PNG': 'image/png', 'JPEG': 'image/jpeg'}
                    if formats.get(decoded.format) != image['mimeType'] or getattr(decoded, 'n_frames', 1) != 1:
                        fail('MODEL_TEXTURE_INVALID', '模型图片实际格式与声明不一致，或包含多帧图片。')
                    width, height = decoded.size
                    pixels = width * height
                    if width < 1 or height < 1 or width > 8192 or height > 8192 or pixels > MAX_TEXTURE_PIXELS:
                        fail('MODEL_TEXTURE_TOO_LARGE', '模型单张纹理尺寸超过8192像素或1600万总像素。')
                    total_pixels += pixels
                    if total_pixels > MAX_TOTAL_TEXTURE_PIXELS:
                        fail('MODEL_TEXTURE_TOO_LARGE', '模型内嵌纹理累计超过3200万像素，请先离线优化。')
                    decoded.load()
        except ServiceError:
            raise
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
            fail('MODEL_TEXTURE_INVALID', '模型内嵌图片无法安全解码。')
    for sampler in samplers:
        for name, allowed in [('magFilter', (9728, 9729)), ('minFilter', (9728, 9729, 9984, 9985, 9986, 9987)),
                              ('wrapS', (33071, 33648, 10497)), ('wrapT', (33071, 33648, 10497))]:
            if name in sampler and (type(sampler[name]) is not int or sampler[name] not in allowed):
                fail('MODEL_TEXTURE_INVALID', '模型纹理采样参数无效。')
    for texture in textures:
        if not index(texture.get('source'), images) or ('sampler' in texture and not index(texture['sampler'], samplers)):
            fail('MODEL_TEXTURE_INVALID', '模型纹理引用不存在的内嵌图片或采样器。')
    def texture_links(value):
        if not isinstance(value, dict):
            return
        for key, nested in value.items():
            if key == 'extras':
                continue
            if key.endswith('Texture'):
                if (not isinstance(nested, dict) or not index(nested.get('index'), textures)
                        or ('texCoord' in nested and not integer(nested['texCoord']))):
                    fail('MODEL_TEXTURE_INVALID', '模型材质引用不存在的纹理或无效UV通道。')
            elif isinstance(nested, dict):
                texture_links(nested)
    for material in materials:
        texture_links(material)
    return {'imageCount': len(images), 'textureCount': len(textures), 'materialCount': len(materials),
            'decodedTexturePixels': total_pixels, 'embeddedImagesDecoded': True}


def validate_glb(raw):
    try:
        return _validate_glb(raw)
    except ServiceError:
        raise
    except (KeyError, TypeError, IndexError, struct.error, OverflowError, RecursionError):
        fail('MODEL_INVALID', '模型结构或数据范围无效。')


def _validate_glb(raw):
    """Require actual uncompressed triangle geometry and no external resource URI."""
    if not raw or len(raw) > MAX_MODEL_BYTES:
        fail('MODEL_TOO_LARGE', '模型必须非空且不超过64MB。', 413)
    if len(raw) < 20 or len(raw) % 4:
        fail('MODEL_INVALID', 'GLB长度或头部不完整。')
    magic, version, length = struct.unpack_from('<4sII', raw, 0)
    if magic != b'glTF' or version != 2 or length != len(raw):
        fail('MODEL_INVALID', '仅接受长度完整的GLB 2.0文件。')
    chunks, offset = [], 12
    while offset < length:
        if offset + 8 > length:
            fail('MODEL_INVALID', 'GLB分块头部不完整。')
        size, kind = struct.unpack_from('<II', raw, offset)
        offset += 8
        if size % 4 or offset + size > length:
            fail('MODEL_INVALID', 'GLB分块越界或未正确对齐。')
        chunks.append((kind, raw[offset:offset+size]))
        offset += size
    if len(chunks) != 2 or chunks[0][0] != 0x4E4F534A or chunks[1][0] != 0x004E4942:
        fail('MODEL_INVALID', '模型须包含一个JSON分块和一个内嵌BIN分块。')
    if len(chunks[0][1]) > 4 * 1024 * 1024:
        fail('MODEL_INVALID', '模型JSON元数据过大。')
    try:
        # Duplicate keys and NaN would obscure validation decisions.
        def unique(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError('Duplicate JSON key')
                result[key] = value
            return result
        doc = json.loads(chunks[0][1].decode('utf-8'), object_pairs_hook=unique,
                         parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))
    except (UnicodeError, ValueError, RecursionError):
        fail('MODEL_INVALID', '模型JSON格式无效。')
    if not isinstance(doc, dict) or not isinstance(doc.get('asset'), dict) or doc['asset'].get('version') != '2.0':
        fail('MODEL_INVALID', '模型版本声明无效。')
    # Prevent both external textures and unusual URI-bearing extension paths.
    def no_uri(value, depth=0):
        if depth > 100:
            fail('MODEL_INVALID', '模型JSON嵌套过深。')
        if isinstance(value, dict):
            if 'uri' in value:
                fail('MODEL_EXTERNAL_RESOURCE', '仅接受完全内嵌的GLB，不允许外部文件或图片链接。')
            for nested in value.values():
                no_uri(nested, depth + 1)
        elif isinstance(value, list):
            for nested in value:
                no_uri(nested, depth + 1)
    no_uri(doc)
    required = doc.get('extensionsRequired', [])
    permitted = {'KHR_materials_unlit', 'KHR_materials_clearcoat', 'KHR_materials_transmission',
                 'KHR_materials_ior', 'KHR_materials_specular', 'KHR_materials_emissive_strength',
                 'KHR_texture_transform'}
    if not isinstance(required, list) or any(name not in permitted for name in required):
        fail('MODEL_EXTENSION_UNSUPPORTED', '模型包含尚未验证的必需扩展，请先离线转换并校验。')
    binary = chunks[1][1]
    buffers, views, accessors = doc.get('buffers', []), doc.get('bufferViews', []), doc.get('accessors', [])
    meshes, nodes, scenes = doc.get('meshes', []), doc.get('nodes', []), doc.get('scenes', [])
    for sequence in (buffers, views, accessors, meshes, nodes, scenes):
        if not isinstance(sequence, list) or any(not isinstance(item, dict) for item in sequence):
            fail('MODEL_INVALID', '模型资源表格式无效。')
    if len(buffers) != 1 or not integer(buffers[0].get('byteLength'), 1):
        fail('MODEL_INVALID', '模型缺少内嵌几何缓冲区。')
    buffer_size = buffers[0]['byteLength']
    if buffer_size > len(binary) or len(binary) - buffer_size > 3:
        fail('MODEL_INVALID', '模型BIN长度与缓冲区声明不一致。')
    for view in views:
        start, size = view.get('byteOffset', 0), view.get('byteLength')
        stride = view.get('byteStride')
        if view.get('buffer') != 0 or not integer(start) or not integer(size, 1) or start + size > buffer_size:
            fail('MODEL_INVALID', '模型bufferView越界。')
        if stride is not None and (not integer(stride, 4) or stride > 252 or stride % 4):
            fail('MODEL_INVALID', '模型字节步长无效。')
    texture_validation = validate_textures(doc, binary, views)
    widths = {5120: 1, 5121: 1, 5122: 2, 5123: 2, 5125: 4, 5126: 4}
    components = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT2': 4, 'MAT3': 9, 'MAT4': 16}
    for accessor in accessors:
        if not index(accessor.get('bufferView'), views) or 'sparse' in accessor:
            fail('MODEL_INVALID', '模型accessor缺少已验证的缓冲区，或包含未支持的稀疏结构。')
        count, start = accessor.get('count'), accessor.get('byteOffset', 0)
        width, count_components = widths.get(accessor.get('componentType')), components.get(accessor.get('type'))
        if not integer(count, 1) or not integer(start) or width is None or count_components is None:
            fail('MODEL_INVALID', '模型accessor声明无效。')
        view = views[accessor['bufferView']]
        size = width * count_components
        stride = view.get('byteStride', size)
        if stride < size or start % width or start + (count - 1) * stride + size > view['byteLength']:
            fail('MODEL_INVALID', '模型accessor范围越界。')
    scene_index = doc.get('scene', 0)
    if not index(scene_index, scenes) or not meshes:
        fail('MODEL_INVALID', '模型没有可显示的场景或几何。')
    roots = scenes[scene_index].get('nodes', [])
    if not isinstance(roots, list) or not roots:
        fail('MODEL_INVALID', '模型场景为空。')
    reachable, visiting, render_meshes = set(), set(), set()
    def visit(node_id, depth=0):
        if depth > 100 or not index(node_id, nodes) or node_id in visiting:
            fail('MODEL_INVALID', '模型场景引用无效或包含循环。')
        if node_id in reachable:
            return
        visiting.add(node_id)
        node = nodes[node_id]
        if 'mesh' in node:
            if not index(node['mesh'], meshes):
                fail('MODEL_INVALID', '模型场景引用不存在的网格。')
            render_meshes.add(node['mesh'])
        children = node.get('children', [])
        if not isinstance(children, list):
            fail('MODEL_INVALID', '模型节点结构无效。')
        for child in children:
            visit(child, depth + 1)
        visiting.remove(node_id)
        reachable.add(node_id)
    for root in roots:
        visit(root)
    vertex_count, primitive_count, triangle_count = 0, 0, 0
    for mesh_id in render_meshes:
        primitives = meshes[mesh_id].get('primitives')
        if not isinstance(primitives, list) or not primitives:
            fail('MODEL_INVALID', '模型网格没有可显示的面。')
        for primitive in primitives:
            if not isinstance(primitive, dict) or not isinstance(primitive.get('attributes'), dict):
                fail('MODEL_INVALID', '模型几何结构无效。')
            if 'material' in primitive and not index(primitive['material'], doc.get('materials', [])):
                fail('MODEL_TEXTURE_INVALID', '模型几何引用不存在的材质。')
            position = primitive['attributes'].get('POSITION')
            if not index(position, accessors):
                fail('MODEL_INVALID', '模型缺少顶点坐标。')
            accessor = accessors[position]
            if accessor.get('type') != 'VEC3' or accessor.get('componentType') != 5126 or accessor['count'] < 3:
                fail('MODEL_INVALID', '模型顶点坐标不是有效的三维浮点数组。')
            if vertex_count + accessor['count'] > 2_000_000:
                fail('MODEL_TOO_COMPLEX', '模型顶点总量超过200万，请先离线优化并保留原文件。')
            view = views[accessor['bufferView']]
            start = view.get('byteOffset', 0) + accessor.get('byteOffset', 0)
            stride = view.get('byteStride', 12)
            lower, upper = [float('inf')] * 3, [float('-inf')] * 3
            for offset in range(accessor['count']):
                values = struct.unpack_from('<3f', binary, start + offset * stride)
                if not all(math.isfinite(v) for v in values):
                    fail('MODEL_INVALID', '模型顶点坐标包含无效数值。')
                for dim, value in enumerate(values):
                    lower[dim], upper[dim] = min(lower[dim], value), max(upper[dim], value)
            if sum((upper[d] - lower[d]) ** 2 for d in range(3)) < 1e-12:
                fail('MODEL_INVALID', '模型几何退化，无法作为真实可观察模型。')
            for name, attribute_id in primitive['attributes'].items():
                if not index(attribute_id, accessors) or accessors[attribute_id]['count'] != accessor['count']:
                    fail('MODEL_INVALID', '模型属性引用或顶点数量不一致。')
            count = accessor['count']
            if 'indices' in primitive:
                if not index(primitive['indices'], accessors):
                    fail('MODEL_INVALID', '模型索引引用无效。')
                indices = accessors[primitive['indices']]
                formats = {5121: 'B', 5123: 'H', 5125: 'I'}
                component = indices.get('componentType')
                if indices.get('type') != 'SCALAR' or component not in formats:
                    fail('MODEL_INVALID', '模型面索引格式无效。')
                iview = views[indices['bufferView']]
                istart = iview.get('byteOffset', 0) + indices.get('byteOffset', 0)
                stride_i = iview.get('byteStride', widths[component])
                for offset in range(indices['count']):
                    vertex = struct.unpack_from('<' + formats[component], binary, istart + offset * stride_i)[0]
                    if vertex >= accessor['count']:
                        fail('MODEL_INVALID', '模型面索引超出顶点范围。')
                count = indices['count']
            mode = primitive.get('mode', 4)
            if mode not in (4, 5, 6) or count < 3 or (mode == 4 and count % 3):
                fail('MODEL_INVALID', '模型必须包含完整的三角面。')
            primitive_count += 1
            vertex_count += accessor['count']
            triangle_count += count // 3 if mode == 4 else count - 2
    if not primitive_count:
        fail('MODEL_INVALID', '模型场景没有可显示的三角几何。')
    return {'validator': 'xijing_glb_structural_v2', 'valid': True, 'format': 'glb', 'version': 2,
            'selfContained': True, 'externalResources': 0, 'meshCount': len(render_meshes),
            'primitiveCount': primitive_count, 'vertexCount': vertex_count, 'triangleCount': triangle_count,
            'size': len(raw), 'hash': hashlib.sha256(raw).hexdigest(),
            **texture_validation,
            'fullConformanceChecked': False}
