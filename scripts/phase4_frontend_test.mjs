/** Offline contract/DOM doubles only. This does not replace actual GLB/browser/touch tests. */
import assert from 'node:assert/strict';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { dirname } from 'node:path';
const repo = new URL('../', import.meta.url);
const contracts = await import(new URL('js/ai-workshop/contracts.js?v=phase4-1', repo));
const services = await import(new URL('js/ai-workshop/services.js?v=phase4-1', repo));
const viewerModule = await import(new URL('js/ai-workshop/model-viewer-adapter.js?v=phase4-1', repo));
const assetsModule = await import(new URL('js/ai-workshop/digital-assets.js?v=phase4-1', repo));
const results = [];
async function check(name, action) {
  try { await action(); results.push({ name, passed: true }); }
  catch (error) { results.push({ name, passed: false, error: error.message }); }
}
const id = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
const imageId = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb';
const modelId = 'cccccccc-cccc-4ccc-8ccc-cccccccccccc';
const hash = 'a'.repeat(64);
const citation = { id: 'test-evidence', sourceId: 'test-source', title: '离线测试来源', locator: '离线测试定位', url: 'https://example.org/test', excerpt: '显式离线结构数据', contentKind: 'original_fact_summary' };
const feature = { description: '离线测试元素', interpretation: 'evidence_based', evidenceIds: [citation.id] };
const image = { imageId, assetId: id, characterId: id, styleMode: 'realistic', styleVersion: 1, hash, mimeType: 'image/png', width: 300, height: 400, size: 120, provenance: 'manual_image', licenseNote: '离线测试许可', accepted: false, fileUrl: `/api/v1/assets/images/${imageId}/file` };
const model = { modelId, hash, size: 1000, format: 'glb', origin: 'local_test_fixture', title: '合法离线测试夹具', licenseNote: '离线测试许可', validation: { valid: true }, fileUrl: `/api/v1/assets/models/${modelId}/file`, downloadUrl: `/api/v1/assets/models/${modelId}/download` };
const asset = { assetId: id, characterId: id, styleMode: 'realistic', styleVersion: 1, sourceTaskId: id, sourceResultHash: hash, version: 1, name: '离线测试角色', mode: 'personal', purpose: '离线结构测试',
  characterSnapshot: { schemaVersion: '1.0', name: '离线测试角色', positioning: '离线测试定位', visualPrompt: '离线测试文字', costume: [feature], colors: [feature], visualElements: [feature], usedEvidenceIds: [citation.id] },
  characterConfirmation: { userConfirmed: true }, reviewSnapshot: { verdict: 'pass', needsHumanReview: true, checkedEvidenceIds: [citation.id] }, citationSnapshot: [citation],
  visualPrompt: { imagePrompt: '离线测试Prompt', negativePrompt: '离线测试约束', templateVersion: 'offline-v1', promptHash: hash, approved: false }, images: [image], models: [] };
const savedGlobals = Object.fromEntries(['fetch', 'document', 'window', 'location', 'sessionStorage', 'setTimeout', 'clearTimeout'].map((name) => [name, globalThis[name]]));
try {
  globalThis.location = { origin: 'http://127.0.0.1:8000' };
  globalThis.document = { querySelector: () => null };
  await check('capabilities follow backend without deriving real generation from an existing GLB', () => {
    const value = contracts.validateCapabilities({ questionAnswering: true, knowledgeSearch: true, agentWorkflow: true, conceptImage: false, imageToModel: false, modelViewer: true, assetManagement: true });
    assert.equal(value.modelViewer, true); assert.equal(value.imageToModel, false); assert.equal(value.conceptImage, false);
    const legacy = contracts.validateCapabilities({ questionAnswering: true, knowledgeSearch: true, agentWorkflow: true, conceptImage: false, imageToModel: false });
    assert.equal(legacy.assetManagement, false);
  });
  await check('registered model URL accepts same configured API only', () => {
    assert.equal(contracts.safeAssetFileUrl(model.fileUrl, 'models', modelId), `http://127.0.0.1:8000${model.fileUrl}`);
    for (const bad of ['javascript:alert(1)', 'data:model/gltf-binary;base64,x', `https://evil.example${model.fileUrl}`, `${model.fileUrl}?token=unsafe`, `/api/v1/assets/models/../${modelId}/file`, `/media/${modelId}.glb`]) {
      assert.equal(contracts.safeAssetFileUrl(bad, 'models', modelId), null, bad);
    }
    assert.equal(contracts.safeAssetFileUrl(model.fileUrl, 'models', '../../secret'), null);
  });
  await check('separate static frontend resolves asset paths to explicitly configured backend origin', () => {
    globalThis.document = { querySelector: () => ({ content: 'http://127.0.0.1:8000/api/v1' }) };
    globalThis.location.origin = 'http://127.0.0.1:8080';
    assert.equal(contracts.safeAssetFileUrl(model.fileUrl, 'models', modelId), `http://127.0.0.1:8000${model.fileUrl}`);
    assert.equal(contracts.safeAssetFileUrl(`http://127.0.0.1:8080${model.fileUrl}`, 'models', modelId), null);
    globalThis.document = { querySelector: () => null }; globalThis.location.origin = 'http://127.0.0.1:8000';
  });
  await check('asset image validates real metadata and refuses untrusted image URL', () => {
    assert.equal(contracts.validateAssetImage(image).imageId, imageId);
    assert.throws(() => contracts.validateAssetImage({ ...image, fileUrl: 'https://evil.example/private.png' }));
    assert.throws(() => contracts.validateAssetImage({ ...image, hash: 'pretend hash' }));
    assert.throws(() => contracts.validateAssetImage({ ...image, accepted: 'true' }));
  });
  await check('asset model requires GLB, license and exact controlled resource path', () => {
    assert.equal(contracts.validateAssetModel(model).origin, 'local_test_fixture');
    for (const bad of [{ format: 'png' }, { licenseNote: '' }, { validation: null }, { downloadUrl: model.fileUrl }]) assert.throws(() => contracts.validateAssetModel({ ...model, ...bad }));
  });
  await check('character snapshot requires final confirmation, reviewer pass and mapped evidence', () => {
    assert.equal(contracts.validateCharacterAsset(asset).name, asset.name);
    for (const bad of [{ characterConfirmation: { userConfirmed: false } }, { reviewSnapshot: { ...asset.reviewSnapshot, verdict: 'needs_revision' } }, { citationSnapshot: [] }, { sourceResultHash: 'fake' }]) assert.throws(() => contracts.validateCharacterAsset({ ...asset, ...bad }));
    assert.throws(() => contracts.validateCharacterAsset({ ...asset, characterSnapshot: { ...asset.characterSnapshot, usedEvidenceIds: ['fabricated-id'] } }));
  });
  await check('style identity and image ownership cannot silently cross character versions', () => {
    assert.throws(() => contracts.validateCharacterAsset({ ...asset, styleMode: 'unregistered_style' }));
    assert.throws(() => contracts.validateCharacterAsset({ ...asset, images: [{ ...image, styleMode: 'chibi' }] }));
    assert.throws(() => contracts.validateCharacterAsset({ ...asset, images: [{ ...image, styleVersion: 2 }] }));
    assert.throws(() => contracts.validateCharacterAsset({ ...asset, images: [{ ...image, characterId: modelId }] }));
  });
  await check('missing historical quota remains null and locked, fixed cap cannot become four', () => {
    const usage = contracts.validateAssetUsage({ max_calls: 3, used_calls: null, remaining_calls: null, history_verified: false, realEnabled: false, providerConfigured: false, protocolVerified: false });
    assert.equal(usage.used_calls, null);
    assert.throws(() => contracts.validateAssetUsage({ ...usage, max_calls: 4 }));
    assert.throws(() => contracts.validateAssetUsage({ ...usage, history_verified: true }));
    assert.throws(() => contracts.validateAssetUsage({ ...usage, history_verified: true, used_calls: 2, remaining_calls: 3 }));
  });
  await check('260+ degree continuous user turn unwraps 360 boundary; programmatic motion never qualifies', () => {
    const tracker = viewerModule.createOrbitTracker();
    for (let degree = 0; degree <= 370; degree += 10) tracker.add((degree % 360) * Math.PI / 180, 'user-interaction', 2);
    assert.ok(tracker.snapshot().maxContinuousDegrees > 360);
    const programmatic = viewerModule.createOrbitTracker();
    for (let degree = 0; degree <= 370; degree += 10) programmatic.add((degree % 360) * Math.PI / 180, 'none', 2);
    assert.equal(programmatic.snapshot().maxContinuousDegrees, 0);
  });
  await check('back-and-forth gestures cannot be added together to falsely pass 260 degree range', () => {
    const tracker = viewerModule.createOrbitTracker();
    [0, 45, 90, 45, 0, 45, 90, 45, 0].forEach((degree) => tracker.add(degree * Math.PI / 180, 'user-interaction', 2));
    assert.ok(tracker.snapshot().maxContinuousDegrees <= 90.001);
    assert.equal(viewerModule.unwrapTheta(350 * Math.PI / 180, 10 * Math.PI / 180).toFixed(5), (20 * Math.PI / 180).toFixed(5));
  });
  await check('enterprise purpose stays separate from unchanged Agent style and rejects overflow', () => {
    const brief = { organizationType: 'tourism', audience: '青年', useCase: '角色展览', designGoal: '原创文旅角色', culturalBoundaries: '真实资料为据', deliveryScope: '网页展示', licenseStatus: 'unverified' };
    const value = assetsModule.enterpriseRequirements(brief);
    assert.ok(value.includes('文旅机构')); assert.ok(value.includes('商用授权待核查'));
    assert.throws(() => assetsModule.enterpriseRequirements({ ...brief, designGoal: '长'.repeat(1201) }));
  });
  let calls = [];
  const response = (body, status = 200) => ({ ok: status < 400, status, json: async () => body });
  globalThis.fetch = async (url, options) => { calls.push({ url, options }); return response(asset); };
  await check('create only sends source task and purpose; server owns confirmation snapshot', async () => {
    await services.createCharacterAsset({ sourceTaskId: id, mode: 'personal', purpose: '离线结构测试' });
    const payload = JSON.parse(calls.at(-1).options.body);
    assert.deepEqual(payload, { sourceTaskId: id, mode: 'personal', purpose: '离线结构测试' });
    assert.equal(calls.at(-1).url.endsWith('/assets/characters'), true);
  });
  await check('invalid IDs, empty purpose and bad enterprise metadata stay local', async () => {
    const before = calls.length;
    await assert.rejects(services.createCharacterAsset({ sourceTaskId: '../../env', mode: 'personal', purpose: '测试' }));
    await assert.rejects(services.createCharacterAsset({ sourceTaskId: id, mode: 'personal', purpose: '  ' }));
    await assert.rejects(services.createCharacterAsset({ sourceTaskId: id, mode: 'enterprise', purpose: '测试', enterpriseBrief: { organizationType: '游戏公司' } }));
    assert.equal(calls.length, before);
  });
  await check('explicit style registration uses same source task, never starts provider generation', async () => {
    await services.createCharacterAsset({ sourceTaskId: id, mode: 'personal', styleMode: 'chibi', purpose: '离线风格测试' });
    assert.equal(JSON.parse(calls.at(-1).options.body).styleMode, 'chibi');
    assert.equal(JSON.parse(calls.at(-1).options.body).sourceTaskId, id);
    const before = calls.length;
    await assert.rejects(services.createCharacterAsset({ sourceTaskId: id, mode: 'personal', styleMode: 'fake', purpose: '测试' }));
    assert.equal(calls.length, before);
  });
  await check('manual Prompt edits submit immutable version request and reject oversized UTF8 locally', async () => {
    await services.createPromptVersion(id, { expectedPromptHash: hash, imagePrompt: '修改后的离线视觉文字', negativePrompt: '不删除文化构件' });
    assert.ok(calls.at(-1).url.endsWith(`/characters/${id}/prompt-versions`));
    assert.equal(JSON.parse(calls.at(-1).options.body).action, 'create_version');
    const before = calls.length;
    await assert.rejects(services.createPromptVersion(id, { expectedPromptHash: hash, imagePrompt: '字'.repeat(3000), negativePrompt: '短约束' }), (error) => error.code === 'PROMPT_BODY_TOO_LARGE');
    assert.equal(calls.length, before);
  });
  await check('invalid upload or absent license never sends binary data', async () => {
    const before = calls.length;
    await assert.rejects(services.uploadAssetImage({ assetId: id, file: { type: 'text/html', size: 20 }, provenance: 'manual_image', licenseNote: '测试' }));
    await assert.rejects(services.importLicensedModel({ assetId: id, file: { name: 'model.png', size: 1000 }, licenseNote: '测试' }));
    await assert.rejects(services.importLicensedModel({ assetId: id, file: { name: 'model.glb', size: 1000 }, licenseNote: '' }));
    assert.equal(calls.length, before);
  });
  await check('ordinary model submit stays explicitly unavailable and never starts provider call', async () => {
    const before = calls.length;
    const result = await services.submitModelTask({ imageId });
    assert.equal(result.available, false); assert.equal(calls.length, before);
  });
  await check('network failure makes one local request and never retries automatically', async () => {
    let count = 0; globalThis.fetch = async () => { count += 1; throw new TypeError('offline'); };
    await assert.rejects(services.getAssetUsage(), (error) => error.code === 'NETWORK_ERROR');
    assert.equal(count, 1);
  });

  class Element {
    constructor(tag = 'div') { this.tagName = tag; this.children = []; this.dataset = {}; this.attributes = {}; this.handlers = new Map(); this.disabled = false; this.hidden = false; this.textContent = ''; this.value = ''; this.files = []; this.checked = false; this.classList = { toggle() {}, add() {} }; this.orbit = { theta: 0, phi: 1, radius: 2 }; }
    addEventListener(name, handler) { this.handlers.set(name, [...this.handlers.get(name) || [], handler]); }
    fire(name, detail) { (this.handlers.get(name) || []).forEach((handler) => handler({ detail, preventDefault() {} })); }
    setAttribute(name, value) { this.attributes[name] = String(value); }
    append(...children) { this.children.push(...children); }
    prepend(...children) { this.children.unshift(...children); }
    replaceChildren(...children) { this.children = children; }
    querySelector(selector) { return this.bindings?.get(selector) || null; }
    focus() { this.focused = true; }
    getCameraOrbit() { return this.orbit; }
    jumpCameraToGoal() { this.jumped = true; }
  }
  const names = ['viewer-host', 'viewer-status', 'viewer-error', 'viewer-zoom-in', 'viewer-zoom-out', 'viewer-reset', 'viewer-touch', 'viewer-reload', 'viewer-help'];
  const elements = new Map(names.map((name) => [`#ai-workshop-${name}`, new Element()]));
  const root = { querySelector: (selector) => elements.get(selector) || null };
  globalThis.document = { querySelector: () => null, createElement: (tag) => new Element(tag) };
  let loaderCount = 0;
  const controller = viewerModule.initializeModelViewer({ root, loader: async () => { loaderCount += 1; } });
  await check('viewer module waits for explicit valid model selection; starts loading and only load event means ready', async () => {
    assert.equal(loaderCount, 0); assert.equal(controller.diagnostics().state, 'idle');
    await controller.load(model);
    assert.equal(loaderCount, 1); assert.equal(controller.diagnostics().state, 'loading');
    const element = elements.get('#ai-workshop-viewer-host').children[0];
    assert.equal(element.attributes['camera-controls'], '');
    assert.equal(element.attributes['min-camera-orbit'], 'auto 15deg auto');
    element.fire('load'); assert.equal(controller.diagnostics().state, 'ready');
    assert.equal(elements.get('#ai-workshop-viewer-reset').disabled, false);
    assert.equal(elements.get('#ai-workshop-viewer-host').dataset.cameraTheta, '0.000000');
    assert.equal(elements.get('#ai-workshop-viewer-host').dataset.cameraRadius, '2.000000');
    assert.equal(elements.get('#ai-workshop-viewer-host').dataset.userEventCount, '0');
  });
  await check('readonly DOM diagnostics follow real camera-change events and clear when style has no model', () => {
    const element = elements.get('#ai-workshop-viewer-host').children[0];
    element.orbit = { theta: 1, phi: 0.8, radius: 1.5 };
    element.fire('camera-change', { source: 'user-interaction' });
    assert.equal(elements.get('#ai-workshop-viewer-host').dataset.cameraTheta, '1.000000');
    assert.equal(elements.get('#ai-workshop-viewer-host').dataset.cameraRadius, '1.500000');
    assert.equal(elements.get('#ai-workshop-viewer-host').dataset.userEventCount, '1');
    element.orbit = { theta: 0, phi: 1, radius: 2 };
  });
  await check('zoom, reset and touch mode use actual viewer controls, preserving scroll on exit', () => {
    const element = elements.get('#ai-workshop-viewer-host').children[0];
    elements.get('#ai-workshop-viewer-zoom-in').fire('click'); assert.equal(element.cameraOrbit, '0rad 1rad 1.6m');
    elements.get('#ai-workshop-viewer-zoom-out').fire('click'); assert.equal(element.cameraOrbit, '0rad 1rad 2.5m');
    elements.get('#ai-workshop-viewer-reset').fire('click'); assert.equal(element.cameraOrbit, '0deg 75deg auto'); assert.equal(element.jumped, true);
    elements.get('#ai-workshop-viewer-touch').fire('click'); assert.equal(element.attributes['touch-action'], 'none');
    elements.get('#ai-workshop-viewer-touch').fire('click'); assert.equal(element.attributes['touch-action'], 'pan-y');
  });
  await check('load error disables controls and displays clear error without a new model task', () => {
    const before = calls.length;
    elements.get('#ai-workshop-viewer-host').children[0].fire('error');
    assert.equal(controller.diagnostics().state, 'error'); assert.equal(elements.get('#ai-workshop-viewer-error').hidden, false);
    assert.match(elements.get('#ai-workshop-viewer-error').textContent, /加载失败/);
    assert.equal(elements.get('#ai-workshop-viewer-zoom-in').disabled, true); assert.equal(calls.length, before);
  });
  await check('explicit retry bypasses only the failed registered GLB cache key, without automatic retries or provider requests', async () => {
    const before = calls.length;
    const host = elements.get('#ai-workshop-viewer-host');
    const failedSource = host.children[0].src;
    const originalMetadataUrl = model.fileUrl;
    const loadersBeforeRetry = loaderCount;
    elements.get('#ai-workshop-viewer-reload').fire('click');
    assert.equal(controller.diagnostics().state, 'loading');
    await new Promise((resolve) => setImmediate(resolve));
    const retried = host.children[0];
    assert.equal(loaderCount, loadersBeforeRetry + 1);
    const canonical = new URL(failedSource);
    const retryUrl = new URL(retried.src);
    assert.notEqual(retried.src, failedSource);
    assert.equal(retryUrl.origin, canonical.origin); assert.equal(retryUrl.pathname, canonical.pathname);
    assert.deepEqual([...retryUrl.searchParams.keys()], ['__viewer_reload']);
    assert.match(retryUrl.searchParams.get('__viewer_reload'), /^\d+-\d+$/);
    assert.equal(retryUrl.hash, ''); assert.equal(retryUrl.username, ''); assert.equal(retryUrl.password, '');
    assert.equal(model.fileUrl, originalMetadataUrl);
    retried.fire('load'); assert.equal(controller.diagnostics().state, 'ready');
    assert.equal(controller.diagnostics().modelHash, hash);
    assert.equal(controller.diagnostics().modelId, model.modelId);
    // Repeated clicks while loading cannot create extra loads. A later actual
    // failure may be manually retried with a fresh key, still the same file.
    retried.fire('error'); const loadersBeforeDoubleClick = loaderCount;
    elements.get('#ai-workshop-viewer-reload').fire('click');
    elements.get('#ai-workshop-viewer-reload').fire('click');
    await new Promise((resolve) => setImmediate(resolve));
    const second = host.children[0]; assert.notEqual(second.src, retried.src);
    assert.equal(loaderCount, loadersBeforeDoubleClick + 1);
    assert.equal(new URL(second.src).pathname, canonical.pathname);
    second.fire('load'); assert.equal(controller.diagnostics().state, 'ready');
    assert.equal(calls.length, before);
  });
  await check('retry strategy does not weaken canonical model URL validation for external or caller-supplied query URLs', async () => {
    const before = calls.length;
    const failed = viewerModule.initializeModelViewer({ root, loader: async () => { throw new Error('must never load unregistered URL'); } });
    await failed.load({ ...model, fileUrl: `https://example.org/api/v1/assets/models/${model.modelId}/file` }, true);
    assert.equal(failed.diagnostics().state, 'error');
    await failed.load({ ...model, fileUrl: `${model.fileUrl}?__viewer_reload=user_supplied` }, true);
    assert.equal(failed.diagnostics().state, 'error');
    assert.match(elements.get('#ai-workshop-viewer-error').textContent, /受控GLB路径/);
    assert.equal(calls.length, before); failed.dispose();
  });
  await check('old model callbacks cannot mark a replacement ready; diagnostics retain actual file hash', async () => {
    await controller.load(model);
    const old = elements.get('#ai-workshop-viewer-host').children[0];
    await controller.load({ ...model, title: '替换模型' });
    old.fire('load'); assert.equal(controller.diagnostics().state, 'loading');
    elements.get('#ai-workshop-viewer-host').children[0].fire('load');
    assert.equal(controller.diagnostics().modelHash, hash);
    controller.dispose();
  });
  await check('viewer module import failure has a visible error instead of a blank empty region', async () => {
    const failed = viewerModule.initializeModelViewer({ root, loader: async () => { throw new Error('explicit offline loader failure'); } });
    await failed.load(model); assert.equal(failed.diagnostics().state, 'error'); assert.match(elements.get('#ai-workshop-viewer-error').textContent, /组件无法加载/); failed.dispose();
  });
  const assetNames = ['asset-form', 'asset-feedback', 'asset-source-task', 'asset-mode', 'asset-style', 'style-state', 'style-model-select', 'style-version-select', 'style-query', 'prompt-edit-form', 'prompt-edit-save', 'prompt-edit-text', 'prompt-edit-negative', 'enterprise-fields', 'asset-summary', 'asset-prompt', 'visual-accept',
    'asset-image-form', 'asset-image-file', 'asset-image-license', 'asset-image-rights', 'asset-image-provenance', 'asset-image-preview', 'image-accept',
    'model-select', 'model-info', 'model-download', 'asset-quota', 'model-approval-summary', 'model-submit', 'model-import-form', 'asset-purpose',
    'model-import-file', 'model-import-license', 'asset-refresh', 'enterprise-to-agent', 'brief', ...names];
  const assetElements = new Map(assetNames.map((name) => [`#ai-workshop-${name}`, new Element()]));
  const ae = (name) => assetElements.get(`#ai-workshop-${name}`);
  for (const name of ['asset-form', 'asset-image-form', 'model-import-form']) ae(name).bindings = new Map([['[type="submit"]', new Element('button')]]);
  for (const field of ['organizationType', 'audience', 'useCase', 'designGoal', 'culturalBoundaries', 'deliveryScope', 'licenseStatus']) {
    const input = new Element('input'); input.value = field === 'organizationType' ? 'game' : field === 'licenseStatus' ? 'unverified' : '离线企业说明';
    assetElements.set(`[data-ai-workshop-enterprise="${field}"]`, input);
  }
  const assetRoot = new Element(); assetRoot.bindings = assetElements;
  const storage = new Map();
  globalThis.sessionStorage = { getItem: (key) => storage.get(key) || null, setItem: (key, value) => storage.set(key, value) };
  globalThis.window = { history: { pushState() {} } };
  ae('asset-mode').value = 'personal'; ae('asset-style').value = 'realistic'; ae('asset-source-task').value = id; ae('asset-purpose').value = '离线测试用途';
  const usage = { max_calls: 3, used_calls: null, remaining_calls: null, history_verified: false, realEnabled: false, providerConfigured: false, protocolVerified: false };
  calls = [];
  let creationDelay = null;
  const editedAsset = { ...asset, assetId: 'dddddddd-dddd-4ddd-8ddd-dddddddddddd', version: 2, styleVersion: 2, parentAssetId: id,
    culturalReviewRequired: true, visualPrompt: { ...asset.visualPrompt, imagePrompt: '用户修改后的离线Prompt', promptHash: 'b'.repeat(64), approved: false }, images: [], models: [] };
  globalThis.fetch = async (url, options) => {
    calls.push({ url, options });
    if (url.endsWith('/assets/models')) return response({ models: [model] });
    if (url.endsWith('/assets/usage')) return response(usage);
    if (url.includes('/assets/characters?')) return response({ characters: [asset] });
    if (url.endsWith('/assets/characters')) { if (creationDelay) await creationDelay; return response(asset); }
    if (url.endsWith('/prompt-versions')) return response(editedAsset);
    if (url.includes('/assets/characters/')) return response(asset);
    throw new Error(`Unexpected offline asset request ${url}`);
  };
  const assetController = assetsModule.initializeDigitalAssets({ root: assetRoot, selectPanel() {} });
  const flush = async () => { for (let index = 0; index < 8; index += 1) await new Promise((resolve) => setImmediate(resolve)); };
  await check('asset initialization makes zero API calls; model submit remains disabled', () => {
    assert.equal(calls.length, 0); assert.equal(ae('model-submit').disabled, true); assert.equal(ae('visual-accept').disabled, true);
  });
  await check('opening asset panel reads only local model/usage endpoints with no provider request', async () => {
    await assetController.setVisible(true);
    assert.equal(calls.length, 2);
    assert.equal(calls.every((call) => call.options.method === 'GET' && /\/assets\/(models|usage)$/.test(call.url)), true);
    assert.ok(ae('asset-quota').textContent.includes('历史待核实'));
    ae('model-submit').fire('click'); assert.equal(calls.length, 2);
  });
  await check('rapid duplicate asset registration is one local submission and confirmed image waits for visibility', async () => {
    let release;
    creationDelay = new Promise((resolve) => { release = resolve; });
    ae('asset-form').fire('submit'); ae('asset-form').fire('submit');
    await flush(); assert.equal(calls.filter((call) => call.url.endsWith('/assets/characters')).length, 1);
    release(); creationDelay = null; await flush();
    assert.equal(ae('image-accept').disabled, true);
    ae('asset-image-preview').children[0].fire('load');
    assert.equal(ae('image-accept').disabled, false);
    assert.equal(ae('model-submit').disabled, true);
    assert.equal(storage.get('xijing.ai.asset.v1'), id);
  });
  await check('concept image load error stops acceptance and gives a visible warning', () => {
    ae('asset-image-preview').children[0].fire('error');
    assert.equal(ae('image-accept').disabled, true);
    assert.match(ae('asset-feedback').textContent, /未看到图片/);
  });
  await check('Agent handoff reads registered styles only and never creates an asset or model by itself', async () => {
    const before = calls.length;
    assetRoot.fire('ai-workshop-character-selected', { taskId: id });
    await flush(); assert.equal(ae('asset-source-task').value, id); assert.equal(calls.length, before + 1);
    assert.equal(calls.at(-1).options.method, 'GET'); assert.ok(calls.at(-1).url.includes('/assets/characters?'));
  });
  await check('selecting an absent style only reads local family and clearly clears previous assets', async () => {
    const before = calls.length;
    ae('asset-style').value = 'chibi'; ae('asset-style').fire('change'); await flush();
    assert.equal(calls.length, before + 1); assert.equal(calls.at(-1).options.method, 'GET');
    assert.match(ae('style-state').textContent, /尚未登记/); assert.match(ae('viewer-status').textContent, /当前风格尚未生成3D模型/);
    assert.equal(ae('visual-accept').disabled, true); assert.equal(ae('model-submit').disabled, true);
    assert.equal(ae('asset-summary').dataset.styleMode, 'chibi');
    assert.equal(ae('asset-summary').dataset.assetId, undefined);
    assert.equal(ae('model-select').children.length, 2);
    ae('asset-style').value = 'realistic'; ae('asset-style').fire('change'); await flush();
    assert.equal(ae('asset-summary').dataset.assetId, id); assert.equal(ae('asset-summary').dataset.styleMode, 'realistic');
  });
  await check('manual editing creates unconfirmed culturally held version without replacing old images/models', async () => {
    const before = calls.length;
    ae('prompt-edit-text').value = '用户修改后的离线Prompt';
    ae('prompt-edit-negative').value = '不删除文化构件';
    ae('prompt-edit-form').fire('submit'); await flush();
    assert.equal(calls.length, before + 1); assert.ok(calls.at(-1).url.endsWith('/prompt-versions'));
    assert.equal(ae('asset-summary').dataset.styleVersion, '2'); assert.equal(ae('asset-summary').dataset.assetId, editedAsset.assetId);
    assert.equal(ae('visual-accept').disabled, true); assert.equal(ae('asset-image-form').querySelector('[type="submit"]').disabled, true);
    assert.match(ae('style-state').textContent, /文化复核/);
    assert.equal(asset.images.length, 1); assert.equal(asset.visualPrompt.promptHash, hash);
    assert.equal(ae('model-submit').disabled, true);
  });
  await check('prior style version remains selectable and is restored through GET without regeneration', async () => {
    const before = calls.length;
    assert.equal(ae('style-version-select').children.length, 3);
    ae('style-version-select').value = id; ae('style-version-select').fire('change'); await flush();
    assert.equal(calls.length, before + 1); assert.equal(calls.at(-1).options.method, 'GET');
    assert.ok(calls.at(-1).url.endsWith(`/characters/${id}`));
    assert.equal(ae('asset-summary').dataset.styleVersion, '1');
    assert.equal(ae('asset-summary').dataset.assetId, id);
  });
  await check('HTML retains all original sections and real-generation remains disabled; text-only untrusted rendering', async () => {
    const html = await readFile(new URL('about.html', repo), 'utf8');
    for (const panel of ['overview', 'qa', 'agents', 'create', 'model']) assert.ok(html.includes(`data-ai-workshop-panel="${panel}"`));
    for (const name of names) assert.ok(html.includes(`id="ai-workshop-${name}"`));
    assert.match(html, /id="ai-workshop-model-submit"[^>]*disabled/);
    assert.ok(html.includes('真实建模 · 等待单次授权'));
    for (const file of ['digital-assets', 'model-viewer-adapter', 'services', 'main', 'agent-workflow']) {
      const source = await readFile(new URL(`js/ai-workshop/${file}.js`, repo), 'utf8');
      assert.equal(/(?:innerHTML|outerHTML)\s*=|insertAdjacentHTML|eval\s*\(/.test(source), false, file);
      assert.equal(/Authorization.*Bearer|api\.neural4d|alb\.neural4d|NEURAL4D_API_KEY/.test(source), false, file);
    }
    const assetSource = await readFile(new URL('js/ai-workshop/digital-assets.js', repo), 'utf8');
    assert.equal(assetSource.includes('submitModelTask('), false);
    assert.equal(assetSource.includes('setInterval('), false);
  });
} finally {
  for (const [name, value] of Object.entries(savedGlobals)) { if (value === undefined) delete globalThis[name]; else globalThis[name] = value; }
}
const report = { kind: 'OFFLINE_EXPLICIT_TEST_DOUBLES_AND_STATIC_CHECKS', disclaimer: 'Not real GLB rendering, browser, physical touch or provider API evidence.', executedAt: new Date().toISOString(), nodeVersion: process.version, command: `node scripts/phase4_frontend_test.mjs ${process.argv.slice(2).join(' ')}`.trim(), results, passed: results.filter((value) => value.passed).length, failed: results.filter((value) => !value.passed).length };
const outputPosition = process.argv.indexOf('--output');
if (outputPosition >= 0) { const path = process.argv[outputPosition + 1]; if (!path) throw new Error('--output requires path'); await mkdir(dirname(path), { recursive: true }); await writeFile(path, `${JSON.stringify(report, null, 2)}\n`, 'utf8'); }
console.log(JSON.stringify(report, null, 2));
if (report.failed) process.exitCode = 1;
