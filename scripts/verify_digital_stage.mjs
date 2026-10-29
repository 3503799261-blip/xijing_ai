/** Independent offline derived-asset verification. No application/DB/provider imports. */
import { readFile, writeFile, mkdir, stat } from 'node:fs/promises';
import { createReadStream } from 'node:fs';
import { createInterface } from 'node:readline';
import { createHash } from 'node:crypto';
import { createRequire } from 'node:module';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { ShapeUtils, Vector2 } from '../js/vendor/three/three.module.js';

const root = path.resolve(fileURLToPath(new URL('../', import.meta.url)));
const args = process.argv.slice(2);
const argument = (key, fallback) => { const i = args.indexOf(key); return i < 0 ? fallback : args[i + 1]; };
const directory = path.resolve(argument('--assets', path.join(root, '..', '.runtime/digital-stage/assets')));
const output = path.resolve(argument('--output', path.join(root, '..', '.runtime/digital-stage/validation/pipeline-validation.json')));
const sharp = createRequire(process.env.XIJING_SHARP_PACKAGE || 'C:/Users/35037/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp/package.json')('sharp');
const hash = (bytes) => createHash('sha256').update(bytes).digest('hex');
const fileHash = async (file) => { const value = createHash('sha256'); for await (const bytes of createReadStream(file)) value.update(bytes); return value.digest('hex'); };
const assert = (value, text) => { if (!value) throw new Error(text); };
const checks = [];
function record(name, value) { checks.push({ name, passed: true, details: value }); }
const before = JSON.parse(await readFile(path.join(directory, 'manifest-conversion.json'), 'utf8'));

function parse(bytes) {
  assert(bytes.length >= 28 && bytes.readUInt32LE(0) === 0x46546c67 && bytes.readUInt32LE(4) === 2 && bytes.readUInt32LE(8) === bytes.length, 'Invalid GLB header/length');
  let json, binary, chunks = 0;
  for (let at = 12; at < bytes.length;) { const size = bytes.readUInt32LE(at), type = bytes.readUInt32LE(at + 4); assert(size % 4 === 0 && at + 8 + size <= bytes.length, 'GLB chunk bounds/alignment'); const chunk = bytes.subarray(at + 8, at + 8 + size); if (type === 0x4e4f534a) json = JSON.parse(chunk.toString('utf8')); if (type === 0x004e4942) binary = chunk; at += size + 8; chunks++; }
  assert(json && binary && chunks === 2 && json.buffers.length === 1 && json.buffers[0].byteLength <= binary.length, 'GLB JSON/binary');
  for (const view of json.bufferViews) assert(view.buffer === 0 && (view.byteOffset || 0) % 4 === 0 && (view.byteOffset || 0) + view.byteLength <= binary.length, 'Buffer view bounds/alignment');
  assert(![...(json.images || []), ...json.buffers].some((value) => value.uri), 'External URI not accepted');
  return { bytes, json, binary };
}
const component = { 5121: [Uint8Array, 1], 5123: [Uint16Array, 2], 5125: [Uint32Array, 4], 5126: [Float32Array, 4] };
function array(glb, index) {
  const accessor = glb.json.accessors[index], view = glb.json.bufferViews[accessor.bufferView], [Class, width] = component[accessor.componentType] || [];
  const components = { SCALAR: 1, VEC2: 2, VEC3: 3, VEC4: 4 }[accessor.type];
  assert(Class && components && (!view.byteStride || view.byteStride === components * width) && !accessor.sparse, 'Unsupported verification accessor');
  const offset = (view.byteOffset || 0) + (accessor.byteOffset || 0), length = accessor.count * components * width;
  assert((accessor.byteOffset || 0) + length <= view.byteLength && offset + length <= glb.binary.length, 'Accessor outside buffer view');
  // Buffer offsets from file chunks need not align to typed-array byteOffset.
  const copy = glb.binary.subarray(offset, offset + length);
  return new Class(copy.buffer.slice(copy.byteOffset, copy.byteOffset + copy.byteLength));
}
async function validate(model) {
  const file = path.join(directory, model.file), bytes = await readFile(file); assert(bytes.length === model.sizeBytes && hash(bytes) === model.sha256, 'Derived hash mismatch'); const glb = parse(bytes);
  const images = [];
  for (const image of glb.json.images || []) {
    assert(['image/png', 'image/jpeg'].includes(image.mimeType) && Number.isInteger(image.bufferView), 'Image MIME/view');
    const view = glb.json.bufferViews[image.bufferView]; const pixels = await sharp(glb.binary.subarray(view.byteOffset || 0, (view.byteOffset || 0) + view.byteLength)).raw().toBuffer({ resolveWithObject: true });
    assert(pixels.info.width <= before.maxTextureSize && pixels.info.height <= before.maxTextureSize && pixels.info.channels >= 3, 'Image decoded dimensions/channels');
    images.push({ mimeType: image.mimeType, width: pixels.info.width, height: pixels.info.height, channels: pixels.info.channels, fullyDecoded: true });
  }
  let triangles = 0;
  for (const mesh of glb.json.meshes) for (const primitive of mesh.primitives) {
    assert(primitive.mode === undefined || primitive.mode === 4, 'Expected triangles'); const pos = array(glb, primitive.attributes.POSITION), indices = array(glb, primitive.indices); assert(indices.length % 3 === 0, 'Indices incomplete triangle');
    for (const i of indices) assert(i < pos.length / 3, 'Index outside position accessor'); triangles += indices.length / 3;
    for (const value of pos) assert(Number.isFinite(value), 'Nonfinite position');
    for (const name of ['NORMAL', 'TEXCOORD_0']) if (primitive.attributes[name] !== undefined) { const values = array(glb, primitive.attributes[name]); assert(values.length / (name === 'NORMAL' ? 3 : 2) === pos.length / 3, 'Attribute count mismatch'); for (const value of values) assert(Number.isFinite(value), 'Nonfinite vertex attribute'); }
  }
  record(`${model.id} GLB lengths/accessors/images`, { file: model.file, bytes: bytes.length, sha256: hash(bytes), triangles, images }); return glb;
}

let report;
try {
  const stage = await validate(before.stage);
  for (const character of before.characters) {
    const glb = await validate(character);
    for (const entry of character.geometryBufferViewsUnchanged) { const view = glb.json.bufferViews[entry.bufferView]; assert(hash(glb.binary.subarray(view.byteOffset || 0, (view.byteOffset || 0) + view.byteLength)) === entry.sha256, 'Character geometry bytes changed'); }
    record(`${character.id} original geometry preserved`, { geometryBufferViews: character.geometryBufferViewsUnchanged.length });
  }
  const primitives = new Map(stage.json.meshes[0].primitives.map((primitive) => [stage.json.materials[primitive.material].name, { indices: array(stage, primitive.indices), cursor: 0 }]));
  const position = array(stage, stage.json.meshes[0].primitives[0].attributes.POSITION);
  const sourcePositions = []; let active, faces = 0, triangles = 0, closedRepeatFaces = 0, simplifiedFaces = 0, simplifiedTriangleDifference = 0, degenerate = 0, reverseErrors = 0, areaErrors = 0, unmatchedVertexErrors = 0, maxAreaDeviation = 0;
  const failures = [];
  const vertex = (i) => [position[i * 3], position[i * 3 + 1], position[i * 3 + 2]];
  for await (const line of createInterface({ input: createReadStream(path.join(root, '中式古戏台SU模型/戏台.obj'), { encoding: 'utf8' }), crlfDelay: Infinity })) {
    if (line.startsWith('v ')) sourcePositions.push(...line.slice(2).trim().split(/\s+/).map(Number));
    else if (line.startsWith('usemtl ')) active = primitives.get(line.slice(7).trim());
    else if (line.startsWith('f ')) {
      assert(active, 'Missing source material in GLB'); faces++; const ids = line.slice(2).trim().split(/\s+/).map((term) => Number(term.split('/')[0]) - 1); const points = ids.map((id) => sourcePositions.slice(id * 3, id * 3 + 3));
      if (points.length > 3 && points[0].every((value, axis) => value === points.at(-1)[axis])) { points.pop(); closedRepeatFaces++; }
      const normal = [0, 0, 0]; points.forEach((p, i) => { const q = points[(i + 1) % points.length]; normal[0] += (p[1] - q[1]) * (p[2] + q[2]); normal[1] += (p[2] - q[2]) * (p[0] + q[0]); normal[2] += (p[0] - q[0]) * (p[1] + q[1]); });
      const drop = normal.reduce((best, value, i) => Math.abs(value) > Math.abs(normal[best]) ? i : best, 0), axes = [0, 1, 2].filter((axis) => axis !== drop);
      const signed = points.reduce((total, p, i) => { const q = points[(i + 1) % points.length]; return total + p[axes[0]] * q[axes[1]] - q[axes[0]] * p[axes[1]]; }, 0) / 2;
      const area = Math.abs(signed); if (points.length !== 3 && area < 1e-10) { degenerate++; continue; }
      // Earcut is reused only to allocate each source face's variable output
      // count (collinear points may be removed). Acceptance below independently
      // checks original area, winding and every output vertex's membership.
      const count = points.length === 3 ? 1 : ShapeUtils.triangulateShape(points.map((p) => new Vector2(p[axes[0]], p[axes[1]])), []).length;
      if (count !== points.length - 2) { simplifiedFaces++; simplifiedTriangleDifference += points.length - 2 - count; }
      let covered = 0;
      const keys = new Set(points.map((p) => p.map(Math.fround).join('/')));
      for (let i = 0; i < count; i++) {
        const tri = Array.from(active.indices.subarray(active.cursor, active.cursor + 3)).map(vertex); assert(tri.length === 3, 'Missing triangle data'); active.cursor += 3; triangles++;
        const [a, b, c] = tri; const signedTriangle = ((b[axes[0]] - a[axes[0]]) * (c[axes[1]] - a[axes[1]]) - (b[axes[1]] - a[axes[1]]) * (c[axes[0]] - a[axes[0]])) / 2;
        if (signedTriangle * signed < -1e-6) reverseErrors++;
        covered += Math.abs(signedTriangle);
        if (tri.some((p) => !keys.has(p.join('/')))) unmatchedVertexErrors++;
      }
      const deviation = Math.abs(covered - area) / Math.max(area, 1e-10); maxAreaDeviation = Math.max(maxAreaDeviation, deviation);
      if (deviation > 1e-4) { areaErrors++; if (failures.length < 8) failures.push({ sourceFace: faces, originalVertices: points.length, deviation }); }
    }
  }
  const unused = [...primitives.values()].reduce((n, group) => n + group.indices.length - group.cursor, 0);
  record('Original-face area/winding/vertex membership comparison', { faces, triangles, closedRepeatFaces, simplifiedFaces, simplifiedTriangleDifference, degenerate, reverseErrors, areaErrors, unmatchedVertexErrors, unusedOutputIndices: unused, maxAreaDeviation, allocationMethod: 'Earcut output count; area/winding/membership checked independently against source coordinates', failures });
  assert(reverseErrors === 0 && areaErrors === 0 && unmatchedVertexErrors === 0 && unused === 0 && triangles === before.stage.triangles, 'Independent face comparison failed');
  if (args.includes('--repeat-pipeline')) {
    const repeated = spawnSync(process.execPath, ['--max-old-space-size=6144', path.join(root, 'scripts/prepare_digital_stage.mjs'), '--output-root', directory, '--max-texture-size', String(before.maxTextureSize)], { cwd: root, encoding: 'utf8', timeout: 180_000 });
    assert(repeated.status === 0, 'Repeat pipeline failed: ' + repeated.stderr); const after = JSON.parse(await readFile(path.join(directory, 'manifest-conversion.json'), 'utf8'));
    assert(JSON.stringify(before.sourceInventory) === JSON.stringify(after.sourceInventory), 'Repeat source inventory changed');
    assert(before.stage.sha256 === after.stage.sha256 && before.characters.every((item) => item.sha256 === after.characters.find((value) => value.id === item.id)?.sha256), 'Repeat GLB hashes changed');
    record('Actual repeat-run idempotence', { glbFiles: 4, allDerivedHashesIdentical: true, sourceFiles: before.sourceInventory.length, sourceHashesUnchanged: true, metadataTimestampsExpectedToChange: true, stdout: repeated.stdout });
  }
  for (const source of before.sourceInventory) assert(await fileHash(path.join(root, source.relative)) === source.sha256, 'Source hash changed');
  record('Final original source invariants', { files: before.sourceInventory.length, allHashesUnchanged: true });
  report = { at: new Date().toISOString(), status: 'PASS', command: `node scripts/verify_digital_stage.mjs ${args.join(' ')}`.trim(), checks, paidApiCalls: 0, neural4dCalls: 0, databaseAccess: false, browserTest: false };
} catch (error) { report = { at: new Date().toISOString(), status: 'FAIL', error: error.message, checks, paidApiCalls: 0, neural4dCalls: 0, databaseAccess: false }; process.exitCode = 1; }
await mkdir(path.dirname(output), { recursive: true }); await writeFile(output, JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify({ status: report.status, error: report.error, checkGroups: checks.length, output }));
