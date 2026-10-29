/** Offline 3D format adaptation. Never imports the application or calls a provider.
 * Source files are read-only; derived GLBs and their source hashes are versioned
 * outside Git. Uses the existing local Sharp package and pinned Three Earcut.
 */
import { createReadStream } from 'node:fs';
import { readFile, writeFile, mkdir, readdir, realpath, rename, copyFile, stat } from 'node:fs/promises';
import { createInterface } from 'node:readline';
import { createHash } from 'node:crypto';
import { createRequire } from 'node:module';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { ShapeUtils, Vector2 } from '../js/vendor/three/three.module.js';

const root = path.resolve(fileURLToPath(new URL('../', import.meta.url)));
const args = process.argv.slice(2);
const arg = (key, fallback) => { const i = args.indexOf(key); return i < 0 ? fallback : args[i + 1]; };
const outputRoot = path.resolve(arg('--output-root', path.join(root, '..', '.runtime', 'digital-stage', 'assets')));
const maxTexture = Number(arg('--max-texture-size', '2048'));
if (!Number.isInteger(maxTexture) || maxTexture < 512 || maxTexture > 4096) throw new Error('Texture limit must be 512..4096.');
const sharpPackage = process.env.XIJING_SHARP_PACKAGE || 'C:/Users/35037/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp/package.json';
const sharp = createRequire(sharpPackage)('sharp');
sharp.cache(false);
const sourceStage = path.join(root, '中式古戏台SU模型');
const sourceCharacters = path.join(root, '3D人物模型');
for (const source of [sourceStage, sourceCharacters]) {
  if (outputRoot === source || outputRoot.startsWith(source + path.sep)) throw new Error('Output must not be inside a source model directory.');
}
const sha = (bytes) => createHash('sha256').update(bytes).digest('hex');
async function fileHash(file) { const hash = createHash('sha256'); for await (const part of createReadStream(file)) hash.update(part); return hash.digest('hex'); }
const exists = async (file) => { try { return (await stat(file)).isFile(); } catch { return false; } };
async function inventory(directory) {
  const result = [];
  async function walk(dir) { for (const entry of await readdir(dir, { withFileTypes: true })) {
    const file = path.join(dir, entry.name);
    if (entry.isSymbolicLink()) throw new Error('Symbolic source entries are not accepted.');
    if (entry.isDirectory()) await walk(file);
    else if (entry.isFile()) result.push({ relative: path.relative(root, file).replaceAll('\\', '/'), bytes: (await stat(file)).size, sha256: await fileHash(file) });
  } }
  await walk(directory); return result.sort((a, b) => a.relative.localeCompare(b.relative));
}
async function writeDerived(name, bytes) {
  const target = path.join(outputRoot, name);
  if (await exists(target)) {
    const oldHash = await fileHash(target);
    if (oldHash === sha(bytes)) return target;
    const archive = path.join(outputRoot, 'versions', `${path.parse(name).name}.${oldHash}.glb`);
    await mkdir(path.dirname(archive), { recursive: true });
    if (!await exists(archive)) await copyFile(target, archive);
  }
  const temp = target + '.tmp'; await writeFile(temp, bytes); await rename(temp, target); return target;
}

class Binary {
  constructor() { this.parts = []; this.length = 0; }
  append(bytes) { const offset = this.length; this.parts.push(bytes); this.length += bytes.length; const pad = (4 - bytes.length % 4) % 4; if (pad) { this.parts.push(Buffer.alloc(pad)); this.length += pad; } return { offset, length: bytes.length }; }
  bytes() { return Buffer.concat(this.parts, this.length); }
}
function packGlb(doc, binary) {
  doc.buffers = [{ byteLength: binary.length }];
  const json = Buffer.from(JSON.stringify(doc)); const jsonPad = Buffer.alloc((4 - json.length % 4) % 4, 32);
  const total = 12 + 8 + json.length + jsonPad.length + 8 + binary.length;
  const header = Buffer.alloc(20); header.writeUInt32LE(0x46546c67); header.writeUInt32LE(2, 4); header.writeUInt32LE(total, 8); header.writeUInt32LE(json.length + jsonPad.length, 12); header.writeUInt32LE(0x4e4f534a, 16);
  const chunk = Buffer.alloc(8); chunk.writeUInt32LE(binary.length); chunk.writeUInt32LE(0x004e4942, 4);
  return Buffer.concat([header, json, jsonPad, chunk, binary], total);
}
function parseGlb(bytes) {
  if (bytes.length < 28 || bytes.readUInt32LE(0) !== 0x46546c67 || bytes.readUInt32LE(4) !== 2 || bytes.readUInt32LE(8) !== bytes.length) throw new Error('Invalid GLB header or total length.');
  let doc, binary; for (let at = 12; at < bytes.length;) { const length = bytes.readUInt32LE(at), type = bytes.readUInt32LE(at + 4); if (at + 8 + length > bytes.length || length % 4) throw new Error('Invalid GLB chunk.'); const value = bytes.subarray(at + 8, at + 8 + length); if (type === 0x4e4f534a) doc = JSON.parse(value.toString('utf8')); if (type === 0x004e4942) binary = value; at += 8 + length; }
  if (!doc || !binary || doc.buffers.length !== 1 || doc.buffers[0].uri) throw new Error('Only self-contained GLB accepted.');
  for (const view of doc.bufferViews || []) if (view.buffer !== 0 || (view.byteOffset || 0) + view.byteLength > binary.length) throw new Error('GLB buffer view outside binary.');
  return { doc, binary };
}
async function normalizedImage(bytes, label) {
  const before = await sharp(bytes, { limitInputPixels: 80_000_000 }).metadata();
  const png = before.hasAlpha === true;
  let pipeline = sharp(bytes, { limitInputPixels: 80_000_000 }).toColourspace('srgb').resize({ width: maxTexture, height: maxTexture, fit: 'inside', withoutEnlargement: true });
  pipeline = png ? pipeline.png({ compressionLevel: 9 }) : pipeline.jpeg({ quality: 88, chromaSubsampling: '4:4:4' });
  const result = await pipeline.toBuffer({ resolveWithObject: true });
  return { bytes: result.data, mimeType: png ? 'image/png' : 'image/jpeg', record: { label, before: { bytes: bytes.length, width: before.width, height: before.height, space: before.space, sha256: sha(bytes) }, after: { bytes: result.data.length, width: result.info.width, height: result.info.height, space: 'srgb', sha256: sha(result.data) }, operation: 'deterministic color-space/format/size adaptation; no AI repaint' } };
}
async function character(name, id) {
  const source = path.join(sourceCharacters, name + '.glb'); const raw = await readFile(source); const { doc, binary } = parseGlb(raw);
  const imageViews = new Map(); const imageRecords = [];
  for (const [i, image] of (doc.images || []).entries()) {
    if (image.uri || !Number.isInteger(image.bufferView)) throw new Error('External character image refused.');
    const view = doc.bufferViews[image.bufferView]; const adapted = await normalizedImage(binary.subarray(view.byteOffset || 0, (view.byteOffset || 0) + view.byteLength), `${id}:image${i}`);
    imageViews.set(image.bufferView, adapted); image.mimeType = adapted.mimeType; imageRecords.push(adapted.record);
  }
  const geometryBefore = []; const combined = new Binary();
  for (const [i, view] of doc.bufferViews.entries()) {
    const original = binary.subarray(view.byteOffset || 0, (view.byteOffset || 0) + view.byteLength);
    if (!imageViews.has(i)) geometryBefore.push({ bufferView: i, sha256: sha(original), bytes: original.length });
    const added = combined.append(imageViews.get(i)?.bytes || original); view.byteOffset = added.offset; view.byteLength = added.length;
  }
  doc.asset.generator = 'Xijing deterministic asset adaptation v1; original geometry retained';
  doc.extras = { ...(doc.extras || {}), xijing: { origin: 'user_import', purpose: 'competition_only_noncommercial', originalSha256: sha(raw), pipelineVersion: 1 } };
  const converted = packGlb(doc, combined.bytes()); const verified = parseGlb(converted);
  for (const item of geometryBefore) { const view = verified.doc.bufferViews[item.bufferView]; if (sha(verified.binary.subarray(view.byteOffset, view.byteOffset + view.byteLength)) !== item.sha256) throw new Error('Character geometry changed unexpectedly.'); }
  const target = await writeDerived(id + '.glb', converted);
  const positions = (doc.accessors || []).filter((value) => value.type === 'VEC3' && value.min && value.max);
  return { id, sourceName: name, file: path.basename(target), sizeBytes: converted.length, sha256: sha(converted), originalBytes: raw.length, originalSha256: sha(raw), geometryBufferViewsUnchanged: geometryBefore, bounds: positions[0] ? { min: positions[0].min, max: positions[0].max } : null, images: imageRecords, validation: { glbVersion: 2, selfContained: true, geometryUnchanged: true } };
}

async function stage() {
  const materials = []; let current;
  for (const line of (await readFile(path.join(sourceStage, '戏台.mtl'), 'utf8')).split(/\r?\n/)) {
    const clean = line.trim(); if (!clean || clean.startsWith('#')) continue; const split = clean.indexOf(' '); const key = clean.slice(0, split), value = clean.slice(split + 1).trim();
    if (key === 'newmtl') { current = { name: value, color: [1, 1, 1], opacity: 1 }; materials.push(current); }
    else if (current && key === 'Kd') current.color = value.split(/\s+/).map(Number);
    else if (current && key === 'd') current.opacity = Number(value);
    else if (current && key === 'map_Kd') { if (value.includes('/') || value.includes('\\') || value.includes(':') || value.startsWith('.')) throw new Error('Unsafe texture path.'); current.texture = value; }
  }
  const positions = [], normals = [], uvs = []; const outPosition = [], outNormal = [], outUv = [], vertexMap = new Map(), missingNormal = new Set();
  const materialIndex = new Map(materials.map((item, i) => [item.name, i])); const groups = new Map(); let active = null, faceCount = 0, triangleCount = 0, lineNumber = 0, degenerateFaces = 0, triangulationWarnings = [];
  const bounds = { min: [Infinity, Infinity, Infinity], max: [-Infinity, -Infinity, -Infinity] };
  const atIndex = (term, length, width) => { const value = Number(term); if (!Number.isInteger(value) || !value) throw new Error(`Invalid OBJ index at ${lineNumber}`); const index = value < 0 ? length / width + value : value - 1; if (index < 0 || index >= length / width) throw new Error(`OBJ index out of range at ${lineNumber}`); return index; };
  function outputVertex(part) {
    const [v, t, n] = part.split('/'); const vi = atIndex(v, positions.length, 3); const ti = t ? atIndex(t, uvs.length, 2) : null; const ni = n ? atIndex(n, normals.length, 3) : null;
    // Deduplicate by the exact Float32 attributes that GLB will contain, rather
    // than by OBJ indices. C4D repeats equivalent tuples across source objects.
    const xyz = positions.slice(vi * 3, vi * 3 + 3).map(Math.fround);
    const normal = (ni === null ? [0, 0, 0] : normals.slice(ni * 3, ni * 3 + 3)).map(Math.fround);
    const uv = [ti === null ? 0 : uvs[ti * 2], ti === null ? 0 : 1 - uvs[ti * 2 + 1]].map(Math.fround);
    const key = [...xyz, ...normal, ...uv, ni === null ? 'generated-normal' : 'source-normal'].join('/');
    if (vertexMap.has(key)) return vertexMap.get(key);
    const index = outPosition.length / 3; outPosition.push(...xyz);
    outNormal.push(...normal);
    if (ni === null) missingNormal.add(index);
    outUv.push(...uv);
    xyz.forEach((value, axis) => { bounds.min[axis] = Math.min(bounds.min[axis], value); bounds.max[axis] = Math.max(bounds.max[axis], value); });
    vertexMap.set(key, index); return index;
  }
  function triangulate(parts) {
    const refs = parts.map((part) => { const vi = atIndex(part.split('/')[0], positions.length, 3); return positions.slice(vi * 3, vi * 3 + 3); });
    if (refs.length > 3 && refs[0].every((v, i) => v === refs.at(-1)[i])) { refs.pop(); parts.pop(); }
    if (parts.length === 3) return [[0, 1, 2]];
    const normal = [0, 0, 0]; refs.forEach((p, i) => { const q = refs[(i + 1) % refs.length]; normal[0] += (p[1] - q[1]) * (p[2] + q[2]); normal[1] += (p[2] - q[2]) * (p[0] + q[0]); normal[2] += (p[0] - q[0]) * (p[1] + q[1]); });
    const drop = normal.reduce((best, value, axis) => Math.abs(value) > Math.abs(normal[best]) ? axis : best, 0);
    const axes = [0, 1, 2].filter((axis) => axis !== drop); const projected = refs.map((p) => new Vector2(p[axes[0]], p[axes[1]]));
    const signedArea = ShapeUtils.area(projected); const area = Math.abs(signedArea);
    if (area < 1e-10) { degenerateFaces++; return []; }
    const triangles = ShapeUtils.triangulateShape(projected, []);
    if (!triangles.length) throw new Error(`Earcut could not triangulate nondegenerate OBJ face at ${lineNumber}`);
    // Earcut has its own winding convention. Restore each original face's
    // orientation so source normals and front/back lighting remain coherent.
    for (const tri of triangles) { const [a, b, c] = tri.map((i) => projected[i]); const cross = (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x); if (cross * signedArea < 0) [tri[1], tri[2]] = [tri[2], tri[1]]; }
    const covered = triangles.reduce((total, tri) => { const [a, b, c] = tri.map((i) => projected[i]); return total + Math.abs((b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x)) / 2; }, 0);
    const deviation = Math.abs(covered - area) / Math.max(area, 1e-10);
    if (deviation > 1e-4) { triangulationWarnings.push({ line: lineNumber, vertices: parts.length, relativeAreaDeviation: deviation }); if (triangulationWarnings.length > 20) throw new Error('Too many triangulation area warnings; refuse unsafe conversion.'); }
    return triangles;
  }
  const reader = createInterface({ input: createReadStream(path.join(sourceStage, '戏台.obj'), { encoding: 'utf8' }), crlfDelay: Infinity });
  for await (const raw of reader) {
    lineNumber++; const line = raw.trim(); if (!line || line.startsWith('#')) continue;
    if (line.startsWith('v ')) positions.push(...line.slice(2).trim().split(/\s+/).map(Number));
    else if (line.startsWith('vn ')) normals.push(...line.slice(3).trim().split(/\s+/).map(Number));
    else if (line.startsWith('vt ')) uvs.push(...line.slice(3).trim().split(/\s+/).slice(0, 2).map(Number));
    else if (line.startsWith('usemtl ')) { active = materialIndex.get(line.slice(7).trim()); if (active === undefined) throw new Error('OBJ references unknown material.'); if (!groups.has(active)) groups.set(active, []); }
    else if (line.startsWith('f ')) { if (active === null) throw new Error('OBJ face without material.'); const parts = line.slice(2).trim().split(/\s+/); faceCount++; const triangles = triangulate(parts); const indices = parts.map(outputVertex); const list = groups.get(active); for (const tri of triangles) { list.push(indices[tri[0]], indices[tri[1]], indices[tri[2]]); triangleCount++; } }
  }
  if (!triangleCount) throw new Error('Stage contains no geometry.');
  if (missingNormal.size) for (const indices of groups.values()) for (let i = 0; i < indices.length; i += 3) {
    const [a, b, c] = indices.slice(i, i + 3); const ab = [0, 1, 2].map((axis) => outPosition[b * 3 + axis] - outPosition[a * 3 + axis]); const ac = [0, 1, 2].map((axis) => outPosition[c * 3 + axis] - outPosition[a * 3 + axis]); const normal = [ab[1] * ac[2] - ab[2] * ac[1], ab[2] * ac[0] - ab[0] * ac[2], ab[0] * ac[1] - ab[1] * ac[0]];
    for (const index of [a, b, c]) if (missingNormal.has(index)) normal.forEach((v, axis) => { outNormal[index * 3 + axis] += v; });
  }
  for (const index of missingNormal) { const length = Math.hypot(...outNormal.slice(index * 3, index * 3 + 3)) || 1; for (let axis = 0; axis < 3; axis++) outNormal[index * 3 + axis] /= length; }
  const doc = { asset: { version: '2.0', generator: 'Xijing offline OBJ Earcut/Sharp adapter v1' }, scene: 0, scenes: [{ nodes: [0] }], nodes: [{ name: 'User supplied Chinese opera stage', mesh: 0 }], meshes: [{ primitives: [] }], accessors: [], bufferViews: [], materials: [], textures: [], images: [], samplers: [{ magFilter: 9729, minFilter: 9987, wrapS: 10497, wrapT: 10497 }], extras: { xijing: { source: 'user_import', purpose: 'competition_only_noncommercial', triangulation: 'Earcut dominant-axis projection', sourceUnits: 'unknown', sourceBounds: bounds } } };
  const blob = new Binary();
  function addView(bytes, target) { const part = blob.append(bytes); const i = doc.bufferViews.length; doc.bufferViews.push({ buffer: 0, byteOffset: part.offset, byteLength: part.length, ...(target ? { target } : {}) }); return i; }
  function accessor(data, components, componentType, type, extrema = {}) { const typed = componentType === 5126 ? new Float32Array(data) : new Uint32Array(data); const bytes = Buffer.from(typed.buffer, typed.byteOffset, typed.byteLength); const bufferView = addView(bytes, type === 'SCALAR' ? 34963 : 34962); const id = doc.accessors.length; doc.accessors.push({ bufferView, componentType, count: data.length / components, type, ...extrema }); return id; }
  const attributes = { POSITION: accessor(outPosition, 3, 5126, 'VEC3', bounds), NORMAL: accessor(outNormal, 3, 5126, 'VEC3'), TEXCOORD_0: accessor(outUv, 2, 5126, 'VEC2') };
  for (const [material, indices] of groups) if (indices.length) doc.meshes[0].primitives.push({ attributes, indices: accessor(indices, 1, 5125, 'SCALAR'), material, mode: 4 });
  const textureRecords = [];
  for (const material of materials) {
    const output = { name: material.name, pbrMetallicRoughness: { baseColorFactor: [...(material.texture ? [1, 1, 1] : material.color), material.opacity], metallicFactor: 0, roughnessFactor: 0.85 }, doubleSided: true };
    if (material.opacity < 1) output.alphaMode = 'BLEND';
    if (material.texture) {
      const texturePath = path.join(sourceStage, 'tex', material.texture); const resolved = await realpath(texturePath); if (!resolved.startsWith(await realpath(sourceStage) + path.sep)) throw new Error('Texture escapes source directory.');
      const adapted = await normalizedImage(await readFile(resolved), material.texture); const image = doc.images.length; doc.images.push({ bufferView: addView(adapted.bytes), mimeType: adapted.mimeType, name: material.texture }); const texture = doc.textures.length; doc.textures.push({ source: image, sampler: 0 }); output.pbrMetallicRoughness.baseColorTexture = { index: texture }; textureRecords.push(adapted.record);
    }
    doc.materials.push(output);
  }
  const converted = packGlb(doc, blob.bytes()); parseGlb(converted); const target = await writeDerived('stage.glb', converted);
  return { id: 'stage', file: path.basename(target), sizeBytes: converted.length, sha256: sha(converted), sourceVertices: positions.length / 3, sourceFaces: faceCount, outputVertices: outPosition.length / 3, triangles: triangleCount, primitiveCount: doc.meshes[0].primitives.length, bounds, textureRecords, triangulation: { algorithm: 'Three r180 ShapeUtils/Earcut projected along largest Newell normal axis', degenerateFaces, warnings: triangulationWarnings }, coordinateUnits: 'source units retained; scene must position/scale explicitly', uvAdaptation: 'OBJ V -> glTF 1-V', validation: { glbVersion: 2, selfContained: true, boundsFinite: [...bounds.min, ...bounds.max].every(Number.isFinite) } };
}

await mkdir(outputRoot, { recursive: true });
const startedAt = new Date().toISOString(); const before = [...await inventory(sourceStage), ...await inventory(sourceCharacters)];
console.log('Preparing original-source character derivatives...');
const characters = []; for (const [name, id] of [['杜丽娘', 'duliniang'], ['穆桂英', 'muguiying'], ['周瑜', 'zhouyu']]) { const result = await character(name, id); characters.push(result); console.log(`${id}: ${result.sizeBytes} bytes`); }
console.log('Parsing/triangulating stage OBJ and adapting textures...'); const stageResult = await stage();
const after = [...await inventory(sourceStage), ...await inventory(sourceCharacters)];
if (JSON.stringify(before) !== JSON.stringify(after)) throw new Error('A source file changed during adaptation; stop and recheck.');
const report = { schemaVersion: 1, pipelineVersion: 'digital-stage-offline-v1', startedAt, completedAt: new Date().toISOString(), command: `node scripts/prepare_digital_stage.mjs ${args.join(' ')}`.trim(), maxTextureSize: maxTexture, textureQuality: 88, originalsModified: false, sourceInventory: before, stage: stageResult, characters, sourceInvariant: { compared: before.length, allHashesUnchanged: true }, paidApiCalls: 0, neural4dCalls: 0, databaseAccess: false, limitations: ['No character motion added', 'Source stage units retained', 'PBR approximation of MTL; no claim to match proprietary offline renderer exactly', 'Browser and placement checks are separate'] };
await writeFile(path.join(outputRoot, 'manifest-conversion.json'), JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify({ status: 'PASS', stageBytes: stageResult.sizeBytes, triangles: stageResult.triangles, characters: characters.map((item) => ({ id: item.id, bytes: item.sizeBytes })), originalFilesUnchanged: before.length }));
