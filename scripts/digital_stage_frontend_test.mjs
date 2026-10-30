/** Explicit offline DOM/Fetch/renderer doubles. Actual GLB scene tests are separate. */
import assert from 'node:assert/strict';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { dirname } from 'node:path';
import { safeStageFileUrl, validateStageCatalog, loadStageCatalog, initializeDigitalStage } from '../js/ai-workshop/digital-stage.js';

const results = [];
const test = async (name, run) => { try { await run(); results.push({ name, status: 'PASS' }); } catch (error) { results.push({ name, status: 'FAIL', error: error.message }); } };
const saved = Object.fromEntries(['document', 'fetch', 'location'].map((key) => [key, globalThis[key]]));
let configured = null, calls = [];
class Element {
  constructor(tag = 'div') { this.tagName = tag; this.children = []; this.dataset = {}; this.attributes = {}; this.handlers = new Map(); this.value = ''; this.disabled = false; this.hidden = false; this.textContent = ''; this.className = ''; }
  append(...items) { this.children.push(...items); }
  replaceChildren(...items) { this.children = [...items]; this.textContent = ''; }
  setAttribute(key, value) { this.attributes[key] = String(value); }
  addEventListener(key, fn) { this.handlers.set(key, [...this.handlers.get(key) || [], fn]); }
  fire(key) { if (this.disabled) return; for (const fn of this.handlers.get(key) || []) fn({ preventDefault() {} }); }
  querySelectorAll(selector) { return this.children.flatMap((child) => [child, ...child.querySelectorAll(selector)]).filter((child) => selector === 'button' && child.tagName === 'button'); }
}
function reset() {
  configured = null; calls = []; globalThis.location = new URL('http://127.0.0.1:8000/about.html#ai-workshop-stage');
  globalThis.document = { querySelector: () => configured === null ? null : { content: configured }, createElement: (tag) => new Element(tag) };
}
function fixture() {
  return { stage: { id: 'stage', name: '离线舞台', fileUrl: '/api/v1/stage/files/stage', available: true, sha256: 'a'.repeat(64) },
    groups: [{ id: 'group-a', name: '离线分类甲', description: '明确的离线测试夹具' }, { id: 'group-b', name: '离线分类乙' }],
    characters: [{ id: 'actor-a', name: '离线人物甲', groupId: 'group-a', available: true, sha256: 'b'.repeat(64), fileUrl: '/api/v1/stage/files/actor-a', description: '离线说明，不是真实角色资料', question: '离线人物甲的问题', citations: [{ title: '离线来源', url: 'https://example.org/evidence', excerpt: '测试摘录' }] },
      { id: 'actor-b', name: '离线人物乙', groupId: 'group-b', available: true, sha256: 'c'.repeat(64), fileUrl: '/api/v1/stage/files/actor-b', question: '离线人物乙的问题' }] };
}
const flush = async () => { for (let index = 0; index < 8; index++) await new Promise((resolve) => setImmediate(resolve)); };
function ui(body = fixture(), { fail = false, held = null } = {}) {
  reset(); const names = ['host', 'group', 'group-description', 'characters', 'viewer-title', 'state', 'status', 'error', 'refresh', 'reload', 'zoom-in', 'zoom-out', 'reset', 'character-name', 'character-group', 'character-description', 'ask', 'question-note', 'citations'];
  globalThis.fetch = async (url, options = {}) => { calls.push({ url, options }); throw new Error('Unexpected fetch from isolated UI test'); };
  const elements = Object.fromEntries(names.map((name) => [name, new Element()]));
  const root = { querySelector: (selector) => elements[selector.replace('#ai-workshop-stage-', '')] || null };
  let loads = 0, viewerLoads = 0, callbacks; const scenes = [], selections = [], focuses = [], visible = [], questions = [], zoom = []; let resets = 0;
  const controller = initializeDigitalStage({ root, onAskQuestion: (question) => questions.push(question), catalogLoader: async () => { loads++; if (fail) throw new Error('明确的离线服务不可用'); return validateStageCatalog(body); }, viewerLoader: async () => ({ initializeStageViewer(options) { viewerLoads++; callbacks = options; return { setVisible(value) { visible.push(value); }, selectCharacter(id) { selections.push(id); }, focusCharacter(id) { focuses.push(id); }, zoom(value) { zoom.push(value); }, reset() { resets++; }, async loadScene(options) { scenes.push(options); callbacks.onState('loading', '离线渲染器替身加载'); if (held) await held; callbacks.onState('ready', '离线渲染器替身就绪'); } }; } }) });
  return { controller, elements, scenes, selections, focuses, visible, questions, zoom, get loads() { return loads; }, get viewerLoads() { return viewerLoads; }, get callbacks() { return callbacks; }, get resets() { return resets; } };
}
try {
  reset();
  await test('stage file URLs only use controlled ID endpoints', () => assert.equal(safeStageFileUrl('/api/v1/stage/files/stage', 'stage'), 'http://127.0.0.1:8000/api/v1/stage/files/stage'));
  await test('path traversal, external URL, credentials and signed query are rejected', () => {
    for (const value of ['../private', 'https://outside.invalid/api/v1/stage/files/stage', 'http://u:p@127.0.0.1:8000/api/v1/stage/files/stage', '/api/v1/stage/files/stage?token=secret', '/api/v1/stage/files/stage#fragment']) assert.equal(safeStageFileUrl(value, 'stage'), null);
    for (const id of ['', '../stage', 'a/b', 'x?secret=1']) assert.equal(safeStageFileUrl('/api/v1/stage/files/stage', id), null);
  });
  await test('explicit safe API origin is honored without accepting arbitrary model hosts', () => { configured = 'http://127.0.0.1:8877/api/v1'; assert.equal(safeStageFileUrl('/api/v1/stage/files/stage', 'stage'), 'http://127.0.0.1:8877/api/v1/stage/files/stage'); configured = null; });
  await test('unsafe API base configuration cannot create model resource URLs', () => { for (const value of ['file:///tmp', 'javascript:alert(1)', 'https://u:p@example.org/api/v1', 'https://example.org/api/v1?token=x']) { configured = value; assert.equal(safeStageFileUrl('/api/v1/stage/files/stage', 'stage'), null); } configured = null; });
  await test('valid current catalog preserves identities and transforms with safe file URLs', () => { const body = fixture(); body.characters[0].position = [0, 2, 0]; const value = validateStageCatalog(body); assert.deepEqual(value.characters[0].position, [0, 2, 0]); assert.equal(value.stage.id, 'stage'); assert.equal(value.characters[1].id, 'actor-b'); assert.match(value.characters[0].fileUrl, /^http:\/\/127/); });
  await test('identifiers must be actual strings instead of coerced arrays or objects', () => { assert.equal(safeStageFileUrl('/api/v1/stage/files/stage', ['stage']), null); for (const key of ['stage', 'group']) { const body = fixture(); if (key === 'stage') body.stage.id = ['stage']; else body.groups[0].id = ['group-a']; assert.throws(() => validateStageCatalog(body), /资料不完整/); } });
  await test('duplicate characters and unknown groups cannot masquerade as separate valid records', () => { const body = fixture(); body.characters.push(body.characters[0]); assert.throws(() => validateStageCatalog(body), /重复/); const other = fixture(); other.characters[0].groupId = 'missing'; assert.throws(() => validateStageCatalog(other), /分类/); });
  await test('unavailable resources remain unavailable; ready resources require a safe URL', () => { const body = fixture(); body.stage.available = false; body.stage.fileUrl = null; assert.equal(validateStageCatalog(body).stage.available, false); body.stage.available = true; assert.throws(() => validateStageCatalog(body), /地址/); });
  await test('source links are sanitized and dangerous URLs never render as links', () => { const body = fixture(); body.characters[0].citations = [{ title: '<img>', url: 'javascript:alert(1)', excerpt: '<script>test</script>' }]; const value = validateStageCatalog(body); assert.equal(value.characters[0].citations[0].url, null); assert.equal(value.characters[0].citations[0].excerpt, '<script>test</script>'); });
  await test('catalog loader sends exactly one local GET with no automatic retry or credentials', async () => { reset(); globalThis.fetch = async (url, options) => { calls.push({ url, options }); return { ok: true, status: 200, json: async () => fixture() }; }; const data = await loadStageCatalog(); assert.equal(data.characters.length, 2); assert.equal(calls.length, 1); assert.equal(calls[0].options.method, 'GET'); assert.equal(calls[0].options.credentials, 'omit'); });
  await test('network failure and resource-unavailable errors stay errors without generation fallback', async () => { reset(); globalThis.fetch = async (url, options) => { calls.push({ url, options }); throw new TypeError('offline'); }; await assert.rejects(loadStageCatalog(), /无法连接/); assert.equal(calls.length, 1); globalThis.fetch = async () => ({ ok: false, status: 503, json: async () => ({ error: {} }) }); await assert.rejects(loadStageCatalog(), /尚未准备/); });
  await test('invalid JSON is handled without declaring readiness', async () => { reset(); globalThis.fetch = async () => ({ ok: true, status: 200, json: async () => { throw new SyntaxError('fixture'); } }); await assert.rejects(loadStageCatalog(), /无法读取/); });
  await test('hidden stage is lazy and performs no catalog or renderer work', async () => { const f = ui(); await f.controller.setVisible(false); assert.equal(f.loads, 0); assert.equal(f.viewerLoads, 0); });
  await test('first visible stage loads one real category at a time and shows source details', async () => { const f = ui(); await f.controller.setVisible(true); assert.equal(f.loads, 1); assert.equal(f.viewerLoads, 1); assert.equal(f.scenes.length, 1); assert.deepEqual(f.scenes[0].characters.map((item) => item.id), ['actor-a']); assert.equal(f.elements['character-name'].textContent, '离线人物甲'); assert.equal(f.elements.host.dataset.stageState, 'ready'); assert.equal(f.elements.citations.children.length, 1); });
  await test('group switching reloads the appropriate character with no identity mixing', async () => { const f = ui(); await f.controller.setVisible(true); f.elements.group.value = 'group-b'; f.elements.group.fire('change'); await flush(); assert.equal(f.scenes.length, 2); assert.equal(f.scenes[1].characters[0].id, 'actor-b'); assert.equal(f.elements['character-name'].textContent, '离线人物乙'); assert.equal(f.elements.host.dataset.stageState, 'ready'); });
  await test('an explicit ready character card selects and focuses that character without network requests or scene reloads', async () => {
    const body = fixture(); body.characters[1].groupId = 'group-a';
    const f = ui(body); await f.controller.setVisible(true);
    const cards = f.elements.characters.querySelectorAll('button');
    assert.equal(cards[0].attributes['aria-pressed'], 'true');
    cards[1].fire('click');
    assert.equal(f.elements['character-name'].textContent, '离线人物乙');
    assert.equal(cards[0].attributes['aria-pressed'], 'false');
    assert.equal(cards[1].attributes['aria-pressed'], 'true');
    assert.equal(f.selections.at(-1), 'actor-b');
    assert.deepEqual(f.focuses, ['actor-b']);
    assert.equal(f.loads, 1); assert.equal(f.scenes.length, 1); assert.equal(calls.length, 0);
  });
  await test('initial loading, automatic category selection and a manual scene retry preserve the overview without focusing', async () => {
    const f = ui(); await f.controller.setVisible(true);
    assert.deepEqual(f.focuses, []);
    f.elements.group.value = 'group-b'; f.elements.group.fire('change'); await flush();
    assert.equal(f.elements['character-name'].textContent, '离线人物乙');
    assert.deepEqual(f.focuses, []);
    f.callbacks.onState('error', '明确的离线渲染错误'); f.elements.reload.fire('click'); await flush();
    assert.equal(f.scenes.length, 3); assert.equal(f.elements.host.dataset.stageState, 'ready');
    assert.deepEqual(f.focuses, []); assert.equal(calls.length, 0);
  });
  await test('a character card in Error updates its saved details without focusing the renderer or sending requests', async () => {
    const body = fixture(); body.characters[1].groupId = 'group-a';
    const f = ui(body); await f.controller.setVisible(true);
    f.callbacks.onState('error', '明确的离线渲染错误');
    const card = f.elements.characters.querySelectorAll('button')[1]; assert.equal(card.disabled, false); card.fire('click');
    assert.equal(f.elements['character-name'].textContent, '离线人物乙');
    assert.equal(card.attributes['aria-pressed'], 'true');
    assert.equal(f.elements.host.dataset.stageState, 'error');
    assert.deepEqual(f.focuses, []); assert.equal(f.scenes.length, 1); assert.equal(calls.length, 0);
  });
  await test('renderer character picking updates details without a new load or API request', async () => { const f = ui(); await f.controller.setVisible(true); const count = f.scenes.length; f.callbacks.onCharacterPick('actor-a'); assert.equal(f.elements['character-name'].textContent, '离线人物甲'); assert.equal(f.scenes.length, count); });
  await test('ask action hands off a question only and does not create or submit a conversation', async () => { const f = ui(); await f.controller.setVisible(true); f.elements.ask.fire('click'); assert.deepEqual(f.questions, ['离线人物甲的问题']); assert.equal(f.loads, 1); assert.equal(f.scenes.length, 1); });
  await test('zoom and reset use the existing renderer without model creation', async () => { const f = ui(); await f.controller.setVisible(true); f.elements['zoom-in'].fire('click'); f.elements['zoom-out'].fire('click'); f.elements.reset.fire('click'); assert.deepEqual(f.zoom, [0.8, 1.25]); assert.equal(f.resets, 1); assert.equal(f.scenes.length, 1); });
  await test('hiding and returning to a ready stage does not reload or poll', async () => { const f = ui(); await f.controller.setVisible(true); await f.controller.setVisible(false); await f.controller.setVisible(true); assert.equal(f.loads, 1); assert.equal(f.scenes.length, 1); assert.equal(f.visible.at(-1), true); });
  await test('missing stage resources show an honest error without starting a renderer', async () => { const body = fixture(); body.stage.available = false; const f = ui(body); await f.controller.setVisible(true); assert.equal(f.viewerLoads, 0); assert.equal(f.elements.host.dataset.stageState, 'error'); assert.match(f.elements.error.textContent, /舞台模型暂不可用/); assert.equal(f.elements['zoom-in'].disabled, true); });
  await test('catalog failure stops busy state and retains a manual retry', async () => { const f = ui(fixture(), { fail: true }); await f.controller.setVisible(true); assert.equal(f.elements.host.dataset.stageState, 'error'); assert.equal(f.elements.refresh.disabled, false); assert.equal(f.elements.reload.hidden, false); assert.equal(f.viewerLoads, 0); });
  await test('an empty category does not reuse another character or fake a GLB', async () => { const body = fixture(); body.characters = []; const f = ui(body); await f.controller.setVisible(true); assert.equal(f.scenes.length, 0); assert.equal(f.elements['character-name'].textContent, '暂无人物'); assert.equal(f.elements.ask.disabled, true); assert.equal(f.elements.host.dataset.stageState, 'error'); });
  await test('loading locks scene controls while another render is pending', async () => { let release; const held = new Promise((resolve) => { release = resolve; }); const f = ui(fixture(), { held }); const waiting = f.controller.setVisible(true); await flush(); assert.equal(f.elements.group.disabled, true); assert.equal(f.elements.refresh.disabled, true); assert.equal(f.elements['zoom-in'].disabled, true); release(); await waiting; assert.equal(f.elements.group.disabled, false); });
  await test('new primary entry and old business selectors remain in the HTML', async () => { const html = await readFile(new URL('../about.html', import.meta.url), 'utf8'); for (const id of ['stage', 'stage-host', 'stage-group', 'stage-ask', 'question-form', 'history', 'creation-form', 'model-submit', 'viewer-host', 'asset-form']) assert.ok(html.includes(`id="ai-workshop-${id}"`), id); assert.match(html, /data-ai-workshop-target="stage">数字戏台/); assert.ok(html.includes('<summary>更多工具</summary>')); assert.match(html, /id="ai-workshop-model-submit"[^>]*disabled/); });
  await test('UI uses no unsafe HTML, timers, provider calls or automatic task submission', async () => { const source = await readFile(new URL('../js/ai-workshop/digital-stage.js', import.meta.url), 'utf8'); assert.equal(/innerHTML\s*=|setInterval\(|startAgentWorkflow\(|submitModelTask\(|askOperaQuestion\(|api\.neural4d|NEURAL4D_API_KEY|DEEPSEEK_API_KEY/.test(source), false); const css = await readFile(new URL('../css/ai-workshop-stage.css', import.meta.url), 'utf8'); assert.ok(css.includes('var(--paper')); assert.ok(css.includes('var(--red')); assert.ok(css.includes('max-width: 600px')); });
} finally { for (const [key, value] of Object.entries(saved)) if (value === undefined) delete globalThis[key]; else globalThis[key] = value; }

const report = { kind: 'OFFLINE_DIGITAL_STAGE_DOM_FETCH_RENDERER_DOUBLES', disclaimer: 'Not evidence of real GLB loading, browser raycasting or physical touch; those require separate browser tests.', at: new Date().toISOString(), node: process.version, results, passed: results.filter((item) => item.status === 'PASS').length, failed: results.filter((item) => item.status === 'FAIL').length, paidApiCalls: 0, neural4dCalls: 0 };
const index = process.argv.indexOf('--output');
if (index >= 0) { const file = process.argv[index + 1]; if (!file) throw new Error('Missing output path'); await mkdir(dirname(file), { recursive: true }); await writeFile(file, JSON.stringify(report, null, 2) + '\n'); }
console.log(JSON.stringify(report, null, 2)); if (report.failed) process.exitCode = 1;
