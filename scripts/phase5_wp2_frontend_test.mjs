/** Offline DOM/Fetch doubles only; these fixtures are not real Agent history or paid API calls. */
import assert from 'node:assert/strict';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { dirname } from 'node:path';
const repo = new URL('../', import.meta.url);
const contracts = await import(new URL('js/ai-workshop/history-contracts.js?v=phase5-wp2-1', repo));
const services = await import(new URL('js/ai-workshop/history-services.js?v=phase5-wp2-1', repo));
const history = await import(new URL('js/ai-workshop/agent-history.js?v=phase5-wp2-1', repo));
const results = [];
async function check(name, action) {
  try { await action(); results.push({ name, passed: true }); }
  catch (error) { results.push({ name, passed: false, error: error.message }); }
}
const id = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
const nextId = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb';
const assetId = 'cccccccc-cccc-4ccc-8ccc-cccccccccccc';
const modelId = 'dddddddd-dddd-4ddd-8ddd-dddddddddddd';
const stamp = '2026-10-19T03:00:00+00:00';
const source = { kind: 'persisted_history', readOnly: true, note: '离线测试夹具，非生产历史' };
const task = { taskId: id, taskType: 'character_creation', title: '离线测试角色', state: 'completed', createdAt: stamp, updatedAt: stamp, startedAt: stamp, finishedAt: stamp, executedAgents: ['planner', 'researcher', 'designer', 'reviewer'], completedSteps: 4, totalSteps: 4, resultReadable: true, hasSavedResult: true, eventCount: 2, lastSequence: 2, historyCompleteness: 'complete', missingFields: [], sourceType: 'persisted_history', executionType: 'model_metadata_recorded' };
const list = { items: [task], page: 1, pageSize: 10, total: 1, totalPages: 1, availableStates: ['completed'], availableTaskTypes: ['character_creation'], source, requestId: 'offline-list-request' };
const agent = { id: 'planner', name: '任务规划Agent', state: 'completed', summary: '离线保存摘要', startedAt: stamp, finishedAt: stamp, errorCode: null, input: null, inputNote: '历史记录未保存该信息', output: { theme: '测试', execution: { model: 'offline-test' } }, outputVersion: 1, outputHash: 'a'.repeat(64), outputSavedAt: stamp, missingFields: ['input'] };
const detail = { task, brief: { requirements: '离线测试需求', style: '京剧写意' }, agents: [agent], result: { design: { name: '原创离线测试角色' }, userConfirmed: true }, citations: [{ id: 'evidence_1', sourceId: 'source_1', title: '离线来源', locator: '测试节', excerpt: '测试摘录', url: 'https://example.org/reference' }], culturalReview: { verdict: 'pass', needsHumanReview: true }, humanConfirmation: { record: { id }, userConfirmed: true, publicationAllowed: true, confirmedAt: stamp }, events: [{ sequence: 1, kind: 'task', taskState: 'running', summary: '已保存启动', occurredAt: stamp }, { sequence: 2, kind: 'task', taskState: 'completed', summary: '已保存完成', occurredAt: stamp }], eventPage: 1, eventPageSize: 30, eventTotal: 2, eventTotalPages: 1, assets: [{ assetId, characterId: id, name: '离线资产', styleMode: 'realistic', styleVersion: 1, modelIds: [modelId], viewerUrl: `/about.html?assetId=${assetId}#ai-workshop-model` }], assetAssociationStatus: 'linked', missingFields: [], source, snapshotAt: stamp, requestId: 'offline-detail-request' };
const copy = (value) => structuredClone(value);
const savedGlobals = Object.fromEntries(['fetch', 'document', 'window', 'location', 'setTimeout', 'clearTimeout'].map((name) => [name, globalThis[name]]));
class Element {
  constructor(tag = 'div') { this.tagName = tag.toUpperCase(); this.children = []; this.dataset = {}; this.attributes = {}; this.handlers = new Map(); this.disabled = false; this.hidden = false; this.value = ''; this._textContent = ''; this.classList = { toggle() {}, add() {} }; }
  get textContent() { return this._textContent + this.children.map((item) => item.textContent).join(''); }
  set textContent(value) { this._textContent = String(value); this.children = []; }
  set innerHTML(_value) { throw new Error('Unsafe HTML rendering attempted'); }
  get innerHTML() { throw new Error('Unsafe HTML rendering attempted'); }
  addEventListener(name, handler) { this.handlers.set(name, [...this.handlers.get(name) || [], handler]); }
  fire(name) { for (const handler of this.handlers.get(name) || []) handler({ preventDefault() {} }); }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; this._textContent = ''; }
  setAttribute(name, value) { this.attributes[name] = String(value); }
  focus() { this.focused = true; }
}
const descendants = (element) => [element, ...element.children.flatMap(descendants)];
const names = ['history', 'history-form', 'history-state', 'history-type', 'history-task-id', 'history-load', 'history-status', 'history-list', 'history-prev', 'history-next', 'history-page', 'history-detail', 'history-detail-status', 'history-detail-content'];
function fixture(overrideServices) {
  const elements = new Map(names.map((name) => [`#ai-workshop-${name}`, new Element()]));
  const root = { querySelector: (selector) => elements.get(selector) || null };
  const controller = history.initializeAgentHistory({ root, services: overrideServices });
  return { elements, controller, get: (name) => elements.get(`#ai-workshop-${name}`) };
}
const flush = async () => { for (let tick = 0; tick < 8; tick += 1) await Promise.resolve(); };
try {
  globalThis.location = { origin: 'http://127.0.0.1:8000' };
  globalThis.document = { querySelector: () => null, createElement: (tag) => new Element(tag) };
  await check('valid persisted list and public detail accept real integer artifact versions', () => {
    assert.equal(contracts.validateHistoryList(copy(list)).total, 1);
    assert.equal(contracts.validateHistoryDetail(copy(detail)).agents[0].outputVersion, 1);
  });
  await check('missing persisted step/output remains null without synthesizing a state', () => {
    const value = copy(detail); value.agents[0] = { ...agent, state: null, summary: null, output: null, outputVersion: null, outputHash: null, startedAt: null, finishedAt: null, outputSavedAt: null, missingFields: ['step', 'input', 'output'] };
    contracts.validateHistoryDetail(value);
    const container = new Element(); history.renderHistoryDetail(container, value);
    assert.ok(container.textContent.includes('历史记录未保存该信息')); assert.ok(!container.textContent.includes('undefined'));
  });
  await check('explicitly incomplete malformed event is visible without inferred timestamp', () => {
    const value = copy(detail); value.events = [{ sequence: 1, summary: '历史事件保存格式异常', incomplete: true }];
    contracts.validateHistoryDetail(value);
    const container = new Element(); history.renderHistoryDetail(container, value);
    assert.ok(container.textContent.includes('该历史事件不完整')); assert.ok(container.textContent.includes('记录时间：历史记录未保存该信息'));
    value.events = [{ sequence: 1, agentId: 'unknown_saved_agent', incomplete: true }]; contracts.validateHistoryDetail(value); history.renderHistoryDetail(container, value);
    assert.ok(container.textContent.includes('历史记录未保存该信息')); assert.ok(!container.textContent.includes('undefined'));
  });
  await check('wrong source, invalid pagination and invented task type are rejected', () => {
    assert.throws(() => contracts.validateHistoryList({ ...copy(list), source: { ...source, readOnly: false } }));
    assert.throws(() => contracts.validateHistoryList({ ...copy(list), totalPages: 3 }));
    assert.throws(() => contracts.validateHistoryList({ ...copy(list), items: [{ ...task, taskType: 'fake_demo' }] }));
  });
  await check('duplicate task and unknown Agent identifiers are rejected', () => {
    assert.throws(() => contracts.validateHistoryList({ ...copy(list), items: [task, task] }));
    const value = copy(detail); value.agents[0].id = 'fake'; assert.throws(() => contracts.validateHistoryDetail(value));
  });
  await check('malformed output and human confirmation metadata do not silently become confirmed', () => {
    assert.throws(() => contracts.validateHistoryDetail({ ...copy(detail), result: [] }));
    assert.throws(() => contracts.validateHistoryDetail({ ...copy(detail), humanConfirmation: { ...detail.humanConfirmation, userConfirmed: 'yes' } }));
  });
  await check('asset viewer links must match exact saved asset and same local origin', () => {
    assert.ok(contracts.safeHistoryViewerUrl(detail.assets[0].viewerUrl, assetId));
    for (const value of [`https://evil.example/about.html?assetId=${assetId}#ai-workshop-model`, `/about.html?assetId=${id}#ai-workshop-model`, `/about.html?assetId=${assetId}&token=x#ai-workshop-model`, 'javascript:alert(1)']) assert.equal(contracts.safeHistoryViewerUrl(value, assetId), null);
  });
  await check('source URLs reject scripts, credentials and signed secret query parameters', () => {
    assert.ok(contracts.safeHistoryCitationUrl('https://example.org/public'));
    for (const value of ['javascript:alert(1)', 'https://user:pass@example.org/', 'https://example.org/file?token=secret', 'https://example.org/file?q-signature=secret']) assert.equal(contracts.safeHistoryCitationUrl(value), null);
  });
  let calls = [];
  const response = (body, status = 200) => ({ ok: status < 400, status, json: async () => body });
  globalThis.fetch = async (url, options) => { calls.push({ url, options }); return response(url.includes(`/${id}?`) ? copy(detail) : copy(list)); };
  await check('list uses one GET with encoded exact filters, no payload and no cache', async () => {
    await services.listAgentHistory({ state: 'completed', taskType: 'character_creation', taskId: id });
    const call = calls.at(-1); assert.equal(call.options.method, 'GET'); assert.equal(call.options.body, undefined); assert.equal(call.options.cache, 'no-store');
    assert.equal(new URL(call.url).searchParams.get('taskId'), id); assert.equal(new URL(call.url).searchParams.get('taskType'), 'character_creation');
  });
  await check('detail uses one bounded GET and checks response task identity', async () => {
    await services.getAgentHistoryDetail(id, { eventPage: 1, eventPageSize: 30 });
    assert.equal(calls.at(-1).options.method, 'GET');
    globalThis.fetch = async () => response({ ...copy(detail), task: { ...task, taskId: nextId } });
    await assert.rejects(services.getAgentHistoryDetail(id), (error) => error.code === 'HISTORY_INVALID_RESPONSE');
  });
  await check('invalid history IDs and local query parameters never send requests', () => {
    const before = calls.length;
    assert.throws(() => services.listAgentHistory({ taskId: '../create' }));
    assert.throws(() => services.listAgentHistory({ state: 'fake' }));
    assert.throws(() => services.getAgentHistoryDetail(id, { eventPage: 0 })); assert.equal(calls.length, before);
  });
  await check('API failure never reflects server exception paths or secrets into the UI', async () => {
    globalThis.fetch = async () => response({ error: { code: 'AGENT_HISTORY_UNAVAILABLE', message: 'PRIVATE_SENTINEL' } }, 503);
    await assert.rejects(services.listAgentHistory(), (error) => !error.message.includes('PRIVATE_SENTINEL') && error.message.includes('数据库'));
  });
  await check('404 is a clear history missing error with no automatic task recreation', async () => {
    let count = 0; globalThis.fetch = async () => { count += 1; return response({ error: { code: 'AGENT_TASK_NOT_FOUND' } }, 404); };
    await assert.rejects(services.getAgentHistoryDetail(id), (error) => error.code === 'AGENT_TASK_NOT_FOUND' && error.message.includes('不会重新创建'));
    assert.equal(count, 1);
  });
  await check('network error makes only one request and permits explicit later recovery', async () => {
    let count = 0; globalThis.fetch = async () => { count += 1; throw new TypeError('offline'); };
    await assert.rejects(services.listAgentHistory(), (error) => error.code === 'HISTORY_NETWORK_ERROR'); assert.equal(count, 1);
    globalThis.fetch = async () => response(copy(list)); assert.equal((await services.listAgentHistory()).total, 1);
  });
  await check('invalid JSON and structurally invalid responses are reported accurately', async () => {
    globalThis.fetch = async () => ({ ok: true, json: async () => { throw new SyntaxError('bad'); } });
    await assert.rejects(services.listAgentHistory(), (error) => error.code === 'HISTORY_INVALID_RESPONSE');
    globalThis.fetch = async () => response({ items: [] }); await assert.rejects(services.listAgentHistory(), (error) => error.code === 'HISTORY_INVALID_RESPONSE');
  });
  await check('timeout cancels the local read and does not retry or call execution routes', async () => {
    let count = 0;
    globalThis.fetch = async (_url, options) => { count += 1; return new Promise((_resolve, reject) => options.signal.addEventListener('abort', () => reject(new Error('abort')), { once: true })); };
    await assert.rejects(services.listAgentHistory({}, { timeoutMs: 1 }), (error) => error.code === 'HISTORY_READ_TIMEOUT'); assert.equal(count, 1);
  });
  await check('history initializes idle without automatic reads or active workflow restoration', () => {
    let count = 0; const value = fixture({ listAgentHistory: async () => { count += 1; return list; }, getAgentHistoryDetail: async () => { count += 1; return detail; } });
    assert.equal(count, 0); assert.equal(value.controller.diagnostics().readOnly, true); assert.equal(value.controller.diagnostics().selectedTaskId, null);
  });
  await check('manual form lists persisted task and populates only actual saved state choices', async () => {
    const value = fixture({ listAgentHistory: async () => copy(list), getAgentHistoryDetail: async () => copy(detail) });
    value.get('history-form').fire('submit'); await flush();
    assert.ok(value.get('history-list').textContent.includes('离线测试角色')); assert.ok(value.get('history-status').textContent.includes('真实持久化记录'));
    assert.deepEqual(value.get('history-state').children.map((item) => item.value), ['', 'completed']);
  });
  await check('list pagination keeps committed filters and remains a separate manual read', async () => {
    const reads = []; const value = fixture({ listAgentHistory: async (request) => { reads.push(request); return { ...copy(list), page: request.page, total: 11, totalPages: 2 }; }, getAgentHistoryDetail: async () => detail });
    value.get('history-state').value = 'completed'; await value.controller.loadList();
    value.get('history-state').value = 'failed'; value.get('history-next').fire('click'); await flush();
    assert.equal(reads.length, 2); assert.equal(reads[1].page, 2); assert.equal(reads[1].state, 'completed');
    value.get('history-prev').fire('click'); await flush(); assert.equal(reads[2].page, 1); assert.equal(reads[2].state, 'completed');
  });
  await check('empty history state does not synthesize demo records', async () => {
    const value = fixture({ listAgentHistory: async () => ({ ...copy(list), items: [], total: 0, totalPages: 0 }), getAgentHistoryDetail: async () => detail });
    await value.controller.loadList(); assert.equal(value.get('history-list').children.length, 0); assert.ok(value.get('history-status').textContent.includes('没有符合条件'));
  });
  await check('manual list error can be recovered by another user query', async () => {
    let attempt = 0; const value = fixture({ listAgentHistory: async () => { if (++attempt === 1) throw new services.HistoryReadError('HISTORY_NETWORK_ERROR', '无法连接历史服务'); return copy(list); }, getAgentHistoryDetail: async () => detail });
    await value.controller.loadList(); assert.ok(value.get('history-status').textContent.includes('无法连接')); assert.equal(value.get('history-load').disabled, false);
    await value.controller.loadList(); assert.ok(value.get('history-list').textContent.includes('离线测试角色'));
  });
  await check('detail displays real saved JSON, citations, review and human record without accept controls', async () => {
    const value = fixture({ listAgentHistory: async () => list, getAgentHistoryDetail: async () => copy(detail) });
    await value.controller.loadDetail(id);
    const content = value.get('history-detail-content'); assert.ok(content.textContent.includes('原创离线测试角色')); assert.ok(content.textContent.includes('已保存用户接受记录')); assert.ok(content.textContent.includes('AI辅助审校通过'));
    assert.ok(content.textContent.includes('来源ID：source_1'));
    assert.deepEqual(descendants(content).filter((item) => item.tagName === 'BUTTON').map((item) => item.textContent), ['重新读取这份历史快照', '上一页事件', '下一页事件']);
  });
  await check('running record is explicitly a non-live snapshot without fake progress', () => {
    const value = copy(detail); value.task.state = 'running'; value.task.finishedAt = null;
    const container = new Element(); history.renderHistoryDetail(container, value);
    assert.ok(container.textContent.includes('记录状态：运行中（非实时监控）')); assert.ok(container.textContent.includes('这里不播放任务进度'));
  });
  await check('untrusted markup stays literal text and no executable nodes are created', () => {
    const value = copy(detail); value.task.title = '<img src=x onerror=alert(1)>'; value.result.design.name = '<script>alert(1)</script>';
    const container = new Element(); history.renderHistoryDetail(container, value);
    assert.ok(container.textContent.includes('<script>alert(1)</script>')); assert.equal(descendants(container).some((item) => ['IMG', 'SCRIPT', 'IFRAME'].includes(item.tagName)), false);
  });
  await check('very long saved output is folded and bounded with an explicit non-mutating truncation note', () => {
    const value = copy(detail); value.agents[0].output = { savedText: '长'.repeat(40000) };
    const container = new Element(); history.renderHistoryDetail(container, value);
    assert.ok(container.textContent.includes('界面仅展示前16000字')); assert.ok(descendants(container).some((item) => item.tagName === 'DETAILS'));
    assert.ok(descendants(container).filter((item) => item.tagName === 'PRE').every((item) => item.textContent.length < 16100)); assert.equal(value.agents[0].output.savedText.length, 40000);
  });
  await check('asset links refer only to exact saved realistic asset and never pretend another style model exists', () => {
    const container = new Element(); history.renderHistoryDetail(container, copy(detail));
    const assetLinks = descendants(container).filter((item) => item.tagName === 'A' && String(item.href).includes('assetId='));
    assert.equal(assetLinks.length, 1); assert.ok(assetLinks[0].href.includes(assetId)); assert.ok(container.textContent.includes(modelId));
    const value = copy(detail); value.assets[0].modelIds = []; history.renderHistoryDetail(container, value); assert.ok(container.textContent.includes('当前风格尚未生成3D模型'));
  });
  await check('unlinked history never invents a role or GLB relationship', () => {
    const value = copy(detail); value.assets = []; value.assetAssociationStatus = 'not_linked';
    const container = new Element(); history.renderHistoryDetail(container, value); assert.ok(container.textContent.includes('未建立关联'));
  });
  await check('model provenance labels distinguish saved real generation from local fixtures and unknown imports', () => {
    const value = copy(detail); value.assets[0].modelIds = [modelId, nextId]; value.assets[0].models = [{ modelId, origin: 'neural4d', format: 'glb', title: '真实来源结构夹具' }, { modelId: nextId, origin: 'local_test_fixture', format: 'glb', title: '测试夹具' }];
    contracts.validateHistoryDetail(value); const container = new Element(); history.renderHistoryDetail(container, value);
    assert.ok(container.textContent.includes('Neural4D真实生成（已保存来源）')); assert.ok(container.textContent.includes('本地测试夹具（非真实AI生成）'));
    value.assets[0].models = []; history.renderHistoryDetail(container, value); assert.ok(container.textContent.includes('不作真实生成判断'));
    value.assets[0].models = [{ modelId: id, origin: 'neural4d' }]; assert.throws(() => contracts.validateHistoryDetail(value));
  });
  await check('missing detail displays explicit failure and manual read recovery action', async () => {
    let count = 0; const value = fixture({ listAgentHistory: async () => list, getAgentHistoryDetail: async () => { if (++count === 1) throw new services.HistoryReadError('AGENT_TASK_NOT_FOUND', '历史任务不存在'); return copy(detail); } });
    await value.controller.loadDetail(id); assert.ok(value.get('history-detail-status').textContent.includes('不存在'));
    descendants(value.get('history-detail-content')).find((item) => item.id === 'ai-workshop-history-detail-refresh').fire('click'); await flush();
    assert.ok(value.get('history-detail-content').textContent.includes('原创离线测试角色')); assert.equal(count, 2);
  });
  await check('older list response cannot overwrite the latest user query', async () => {
    let resolveOld; let count = 0; const value = fixture({ listAgentHistory: async () => ++count === 1 ? new Promise((resolve) => { resolveOld = resolve; }) : ({ ...copy(list), items: [], total: 0, totalPages: 0 }), getAgentHistoryDetail: async () => detail });
    const pending = value.controller.loadList(); await value.controller.loadList(); resolveOld(copy(list)); await pending;
    assert.equal(value.get('history-list').children.length, 0); assert.ok(value.get('history-status').textContent.includes('没有符合条件'));
  });
  await check('older selected detail cannot overwrite another task or reappear after new list query', async () => {
    let resolveOld; const value = fixture({ listAgentHistory: async () => copy(list), getAgentHistoryDetail: async (taskId) => taskId === id ? new Promise((resolve) => { resolveOld = resolve; }) : { ...copy(detail), task: { ...task, taskId: nextId, title: '新的选择' } } });
    const pending = value.controller.loadDetail(id); await value.controller.loadDetail(nextId); resolveOld(copy(detail)); await pending;
    assert.ok(value.get('history-detail-content').textContent.includes('新的选择')); assert.equal(value.controller.diagnostics().selectedTaskId, nextId);
    await value.controller.loadList(); assert.equal(value.get('history-detail').hidden, true); assert.equal(value.controller.diagnostics().selectedTaskId, null);
  });
  await check('event pagination is user initiated and keeps selected historical task', async () => {
    const reads = []; const value = fixture({ listAgentHistory: async () => list, getAgentHistoryDetail: async (taskId, options) => { reads.push({ taskId, page: options.eventPage }); return { ...copy(detail), eventPage: options.eventPage, eventTotal: 31, eventTotalPages: 2 }; } });
    await value.controller.loadDetail(id);
    descendants(value.get('history-detail-content')).find((item) => item.id === 'ai-workshop-history-events-next').fire('click'); await flush();
    assert.deepEqual(reads, [{ taskId: id, page: 1 }, { taskId: id, page: 2 }]);
  });
  await check('history HTML entry and main initialization preserve old module chain and 8-page navigation', async () => {
    const html = await readFile(new URL('about.html', repo), 'utf8');
    const main = await readFile(new URL('js/ai-workshop/main.js', repo), 'utf8');
    for (const value of ['ai-workshop-history-form', 'ai-workshop-history-list', 'ai-workshop-history-detail-content', '真实持久化记录 · 只读快照', 'main.js?v=phase4-1', 'ai-workshop.css?v=phase4-1']) assert.ok(html.includes(value), value);
    assert.ok(main.includes("import('./agent-history.js?v=phase5-wp2-1')")); assert.ok(main.includes("window.location.hash === '#ai-workshop-history'"));
    for (const page of ['index', 'history', 'roles', 'facial', 'music', 'video', 'gallery', 'about']) assert.ok(html.includes(`${page}.html`));
  });
  await check('history module source contains no mutation methods, timers, SSE, local storage or HTML injection', async () => {
    const ui = await readFile(new URL('js/ai-workshop/agent-history.js', repo), 'utf8');
    const transport = await readFile(new URL('js/ai-workshop/history-services.js', repo), 'utf8');
    assert.ok(!/innerHTML|insertAdjacentHTML|EventSource\s*\(|localStorage|sessionStorage|setInterval\s*\(|setTimeout\s*\(/.test(ui));
    assert.ok(!/method:\s*['"](?:POST|DELETE|PUT|PATCH)['"]|startAgentWorkflow|confirmAgentWorkflow|cancelAgentWorkflow|createCharacterAsset|submitModelTask/.test(ui + transport));
  });
} finally {
  for (const [name, value] of Object.entries(savedGlobals)) { if (value === undefined) delete globalThis[name]; else globalThis[name] = value; }
}
const report = { scope: 'WP2 offline contract/DOM/Fetch doubles; not browser or paid API validation', timestamp: new Date().toISOString(), passed: results.filter((item) => item.passed).length, failed: results.filter((item) => !item.passed).length, skipped: 0, checks: results };
const outputIndex = process.argv.indexOf('--output');
if (outputIndex >= 0) { const output = process.argv[outputIndex + 1]; await mkdir(dirname(output), { recursive: true }); await writeFile(output, JSON.stringify(report, null, 2) + '\n'); }
console.log(JSON.stringify(report, null, 2));
if (report.failed) process.exitCode = 1;
