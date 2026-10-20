/** Explicit offline test doubles only. No real model, RAG, API server or browser is used. */
import assert from 'node:assert/strict';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { dirname } from 'node:path';
import { setImmediate as yieldTurn } from 'node:timers/promises';
const repo = new URL('../', import.meta.url);
const contracts = await import(new URL('js/ai-workshop/contracts.js?v=phase3-1', repo));
const services = await import(new URL('js/ai-workshop/services.js?v=phase3-1', repo));
const ui = await import(new URL('js/ai-workshop/agent-workflow.js?v=phase3-1', repo));
const results = [];
async function check(name, action) {
  try { await action(); results.push({ name, passed: true }); }
  catch (error) { results.push({ name, passed: false, error: error.message }); }
}
const taskId = 'offline-task-001';
const runId = 'offline-run-001';
const requestId = 'offline-request-001';
const date = '2026-10-11T08:00:00+00:00';
const enabled = { questionAnswering: true, knowledgeSearch: true, agentWorkflow: true, conceptImage: true, imageToModel: true };
const created = { taskId, runId, state: 'waiting', sequence: 1, requestId, statusUrl: 'javascript:ignore-this', resultUrl: 'https://untrusted.example.org/ignore-this' };
const citation = { id: 'offline-evidence-001', title: '离线结构测试资料', sourceId: 'offline-source', locator: '测试位置', url: 'https://example.org/test', excerpt: '测试数据，不作为京剧知识。', contentKind: 'original_fact_summary' };
const feature = { description: '<img src=x onerror=alert(1)>离线结构测试', interpretation: 'evidence_based', evidenceIds: [citation.id] };
const resultFixture = {
  taskId, schemaVersion: '1.0',
  design: { schemaVersion: '1.0', name: '离线测试角色', positioning: '这是离线测试数据，不是AI创作。', costume: [feature], colors: [{ description: '测试创意色彩', interpretation: 'creative', evidenceIds: [] }], visualElements: [], creativeElements: ['测试创意'], visualPrompt: '<script>alert(1)</script>测试提示词', usedEvidenceIds: [citation.id], limitations: ['离线测试限制'] },
  review: { verdict: 'pass', issues: [], suggestions: ['测试建议'], checkedEvidenceIds: [citation.id], needsHumanReview: true },
  citations: [citation], uncertain: false, publicationAllowed: false, userConfirmed: false, knowledgeGeneration: 'offline-generation', promptVersions: { planner: 'offline', researcher: 'offline', designer: 'offline', reviewer: 'offline' }, requestId,
};
function statusFixture({ state = 'running', sequence = 2, agentState = 'running', resultReady = false, events = [] } = {}) {
  const allCompleted = resultReady && ['awaiting_confirmation', 'completed'].includes(state);
  return { taskId, runId, state, currentAgent: state === 'running' ? 'planner' : null,
    agents: contracts.WORKFLOW_AGENT_IDS.map((id) => ({ id, state: allCompleted ? 'completed' : id === 'planner' ? agentState : 'pending', summary: id === 'planner' ? '离线测试：规划阶段摘要' : '', startedAt: id === 'planner' ? date : null, finishedAt: agentState === 'completed' && id === 'planner' ? date : null, errorCode: null })),
    completedSteps: allCompleted ? 4 : agentState === 'completed' ? 1 : 0, totalSteps: 4, events, lastSequence: sequence, confirmation: state === 'awaiting_confirmation' ? { id: 'offline-confirm-001', reason: 'final_acceptance', canAccept: true } : null,
    resultReady, cancelRequested: false, requestId };
}
const event = (sequence, extra = {}) => ({ kind: 'agent', runId, agentId: 'planner', sequence, state: 'running', occurredAt: date, summary: '离线测试事件', ...extra });
const response = (body, status = 200) => ({ ok: status >= 200 && status < 300, status, json: async () => body });
const savedGlobals = Object.fromEntries(['fetch', 'document', 'window', 'location', 'sessionStorage', 'setTimeout', 'clearTimeout'].map((name) => [name, globalThis[name]]));
try {
  await check('AI capabilities follow actual backend gates instead of old future-feature constants', () => {
    const capabilities = contracts.validateCapabilities(enabled);
    assert.equal(capabilities.agentWorkflow, true); assert.equal(capabilities.conceptImage, true); assert.equal(capabilities.imageToModel, true);
    assert.equal(contracts.validateCapabilities({ ...enabled, conceptImage: false }).conceptImage, false);
    assert.equal(contracts.validateCapabilities({ ...enabled, imageToModel: false }).imageToModel, false);
    assert.equal(contracts.validateCapabilities({ ...enabled, agentWorkflow: false }).agentWorkflow, false);
  });
  await check('create/status retain separate canonical task and Agent states', () => {
    assert.equal(contracts.validateWorkflowCreated(created).state, 'waiting');
    assert.equal(contracts.validateWorkflowCreated({ ...created, state: 'completed', sequence: 9 }).state, 'completed');
    assert.equal(contracts.validateWorkflowStatus(statusFixture()).agents[0].state, 'running');
    assert.throws(() => contracts.validateWorkflowStatus({ ...statusFixture(), agents: statusFixture().agents.map((agent) => ({ ...agent, state: 'cancelled' })) }));
  });
  await check('reject malformed identities, events, duplicate Agents and late confirmation', () => {
    assert.throws(() => contracts.validateWorkflowTaskId('../config'));
    assert.throws(() => contracts.validateWorkflowCreated({ ...created, taskId: 'abc?key=1' }));
    assert.throws(() => contracts.validateWorkflowStatus({ ...statusFixture(), agents: [statusFixture().agents[0], ...statusFixture().agents.slice(0, 3)] }));
    assert.throws(() => contracts.validateWorkflowStatus({ ...statusFixture(), events: [event(2), event(1)] }));
    assert.throws(() => contracts.validateWorkflowStatus({ ...statusFixture(), events: [event(1, { runId: 'different-run' })] }));
    assert.throws(() => contracts.validateWorkflowStatus({ ...statusFixture(), confirmation: { id: 'offline-confirm-001', reason: 'final_acceptance', canAccept: true } }));
  });
  await check('accept canonical evidence-bound design and reject invented or unsupported IDs', () => {
    assert.equal(contracts.validateWorkflowResult(resultFixture).design.name, '离线测试角色');
    const changed = structuredClone(resultFixture); changed.design.costume[0].evidenceIds = ['invented-source'];
    assert.throws(() => contracts.validateWorkflowResult(changed));
    const noEvidence = structuredClone(resultFixture); noEvidence.design.costume[0].evidenceIds = [];
    assert.throws(() => contracts.validateWorkflowResult(noEvidence));
    const noUsed = structuredClone(resultFixture); noUsed.design.usedEvidenceIds = [];
    assert.throws(() => contracts.validateWorkflowResult(noUsed));
  });
  await check('reject publication before user acceptance or despite uncertainty/review failure', () => {
    assert.throws(() => contracts.validateWorkflowResult({ ...resultFixture, publicationAllowed: true }));
    assert.throws(() => contracts.validateWorkflowResult({ ...resultFixture, publicationAllowed: true, userConfirmed: true, uncertain: true }));
    assert.throws(() => contracts.validateWorkflowResult({ ...resultFixture, publicationAllowed: true, userConfirmed: true, review: { ...resultFixture.review, verdict: 'needs_revision' } }));
    assert.equal(contracts.validateWorkflowResult({ ...resultFixture, publicationAllowed: true, userConfirmed: true }).publicationAllowed, true);
  });
  let calls = [];
  globalThis.location = { origin: 'http://127.0.0.1:8000', hash: '' };
  globalThis.fetch = async (url, options) => { calls.push({ url, options }); return response(url.includes('/agent/create') ? created : url.includes('/agent/result/') ? resultFixture : url.endsWith('/capabilities') ? enabled : statusFixture()); };
  await check('creation sends trimmed explicit brief and original idempotency key; ignores server task URLs', async () => {
    const received = await services.startAgentWorkflow({ requirements: '  离线测试需求  ', style: '京剧写意', styleLabel: '不上传此字段' }, { idempotencyKey: 'offline-key-001' });
    assert.equal(received.taskId, taskId); assert.equal(received.statusUrl, undefined);
    assert.equal(calls.at(-1).url, 'http://127.0.0.1:8000/api/v1/agent/create');
    assert.deepEqual(JSON.parse(calls.at(-1).options.body), { requirements: '离线测试需求', style: '京剧写意' });
    assert.equal(calls.at(-1).options.headers['X-Idempotency-Key'], 'offline-key-001');
  });
  await check('local input guards block empty, long, invalid styles and path identifiers before network', async () => {
    const previous = calls.length;
    for (const brief of [{ requirements: '', style: '京剧写意' }, { requirements: 'x'.repeat(1201), style: '京剧写意' }, { requirements: '测试', style: '不存在风格' }]) await assert.rejects(services.startAgentWorkflow(brief), (error) => error.code === 'INVALID_CREATION_BRIEF');
    await assert.rejects(services.getAgentWorkflowStatus('../../env'), (error) => error.code === 'INVALID_TASK_ID');
    assert.equal(calls.length, previous);
  });
  await check('status cursor, confirm sequence and cancel sequence use correct server APIs', async () => {
    await services.getAgentWorkflowStatus(taskId, { afterSequence: 7 });
    assert.ok(calls.at(-1).url.endsWith(`/agent/status/${taskId}?afterSequence=7`));
    await services.confirmAgentWorkflow(taskId, { confirmationId: 'offline-confirm-001', expectedSequence: 8 });
    assert.deepEqual(JSON.parse(calls.at(-1).options.body), { confirmationId: 'offline-confirm-001', expectedSequence: 8, action: 'accept' });
    await services.cancelAgentWorkflow(taskId, { expectedSequence: 9 });
    assert.deepEqual(JSON.parse(calls.at(-1).options.body), { expectedSequence: 9 });
  });
  await check('typed backend failures and malformed results do not silently create replacement tasks', async () => {
    let count = 0;
    globalThis.fetch = async () => { count += 1; return response({ error: { code: 'STALE_WORKFLOW_STATE', message: '离线测试：任务已变化', retryable: false }, requestId }, 409); };
    await assert.rejects(services.confirmAgentWorkflow(taskId, { confirmationId: 'offline-confirm-001', expectedSequence: 8 }), (error) => error.code === 'STALE_WORKFLOW_STATE' && error.requestId === requestId);
    assert.equal(count, 1);
    globalThis.fetch = async () => response({ ...resultFixture, design: null });
    await assert.rejects(services.getAgentWorkflowResult(taskId), (error) => error.code === 'INVALID_WORKFLOW_RESPONSE');
  });
  await check('10-second workflow timeout makes one request only (accelerated clock)', async () => {
    const intervals = []; let count = 0;
    globalThis.setTimeout = (callback, milliseconds) => { intervals.push(milliseconds); return savedGlobals.setTimeout(callback, 3); };
    globalThis.fetch = async (url, { signal }) => { count += 1; return new Promise((resolve, reject) => signal.addEventListener('abort', () => reject(new DOMException('offline', 'AbortError')), { once: true })); };
    await assert.rejects(services.getAgentWorkflowStatus(taskId), (error) => error.code === 'REQUEST_TIMEOUT');
    assert.deepEqual(intervals, [10000]); assert.equal(count, 1); globalThis.setTimeout = savedGlobals.setTimeout;
  });

  class Element {
    constructor(tag = 'div') { this.tagName = tag.toUpperCase(); this.children = []; this.dataset = {}; this.attributes = {}; this.handlers = new Map(); this._text = ''; this.hidden = false; this.disabled = false; this.value = ''; this.className = ''; this.classList = { toggle() {}, add() {}, remove() {} }; }
    set textContent(value) { this._text = String(value); this.children = []; }
    get textContent() { return this._text + this.children.map((item) => item.textContent).join(''); }
    append(...children) { children.forEach((child) => { child.parent = this; this.children.push(child); }); }
    replaceChildren(...children) { this.children = []; this._text = ''; this.append(...children); }
    remove() { this.parent.children = this.parent.children.filter((item) => item !== this); }
    setAttribute(name, value) { this.attributes[name] = String(value); }
    removeAttribute(name) { delete this.attributes[name]; }
    addEventListener(name, handler) { this.handlers.set(name, [...this.handlers.get(name) || [], handler]); }
    fire(name) { (this.handlers.get(name) || []).forEach((handler) => handler({ preventDefault() {} })); }
    focus() { this.focused = true; }
    click() { this.fire('click'); }
    querySelector(selector) { return this.bindings?.get(selector) || null; }
  }
  const elements = new Map();
  const names = ['agent-start', 'agent-submit-retry', 'agent-submit-error', 'agent-service-state', 'agent-task-state', 'agent-task-id', 'agent-progress', 'agent-feedback', 'agent-query', 'agent-service-refresh', 'agent-cancel', 'agent-new', 'agent-confirmation', 'agent-confirm-reason', 'agent-confirm', 'agent-result', 'agent-result-content', 'agent-download', 'agent-events', 'brief', 'style', 'brief-error'];
  names.forEach((name) => elements.set(`#ai-workshop-${name}`, new Element()));
  const element = (name) => elements.get(`#ai-workshop-${name}`);
  const cards = contracts.WORKFLOW_AGENT_IDS.map((id) => {
    const card = new Element('article'); card.bindings = new Map(['status', 'summary', 'timing'].map((field) => [`[data-agent-${field}]`, new Element()])); elements.set(`[data-agent-id="${id}"]`, card); return card;
  });
  const root = new Element(); root.bindings = elements; root.querySelectorAll = () => [];
  const documentHandlers = new Map();
  globalThis.document = { hidden: false, createElement: (tag) => new Element(tag), querySelector: () => null, addEventListener: (name, handler) => documentHandlers.set(name, handler) };
  globalThis.window = { location: globalThis.location, history: { pushState(a, b, hash) { globalThis.location.hash = hash; } }, addEventListener() {} };
  const storage = new Map(); globalThis.sessionStorage = { setItem: (key, value) => storage.set(key, value), getItem: (key) => storage.get(key) || null, removeItem: (key) => storage.delete(key) };
  const timers = new Map(); let timerIndex = 0;
  globalThis.setTimeout = (handler, duration) => { const id = ++timerIndex; timers.set(id, { handler, duration }); return id; };
  globalThis.clearTimeout = (id) => timers.delete(id);
  const flush = async () => { for (let i = 0; i < 8; i += 1) await yieldTurn(); };
  const descendants = (value) => value.children.flatMap((child) => [child, ...descendants(child)]);
  let currentStatus = statusFixture({ events: [event(1), event(2)] });
  let currentResult = resultFixture;
  let networkFailure = false;
  let creationFailure = false;
  let requestPending = null;
  calls = [];
  globalThis.fetch = async (url, options) => {
    calls.push({ url, options });
    if (networkFailure) throw new TypeError('offline connection failure');
    if (url.endsWith('/capabilities')) return response(enabled);
    if (url.endsWith('/agent/create')) {
      if (creationFailure) throw new TypeError('offline lost creation response');
      return response(created, 202);
    }
    if (url.includes('/agent/status/')) { if (requestPending) await requestPending.promise; return response(currentStatus); }
    if (url.includes('/agent/result/')) return response(currentResult);
    if (url.includes('/agent/confirm/')) {
      currentStatus = statusFixture({ state: 'completed', sequence: 9, agentState: 'completed', resultReady: true, events: [event(9, { kind: 'task', taskState: 'completed' })] });
      currentResult = { ...resultFixture, userConfirmed: true, publicationAllowed: true }; return response(currentStatus);
    }
    throw new Error(`Unexpected offline route: ${url}`);
  };
  let selectedPanel = null;
  const controller = ui.initializeAgentWorkflow({ root, selectPanel: (name) => { selectedPanel = name; }, refreshCapabilities: async () => {} });
  controller.setCapability(contracts.validateCapabilities(enabled));
  await check('empty creation stays local; draft submit is not an Agent network action', async () => {
    const previous = calls.length; element('agent-start').fire('click'); await flush();
    assert.equal(calls.length, previous); assert.equal(element('brief').attributes['aria-invalid'], 'true');
    root.fire('submit'); assert.equal(calls.length, previous);
  });
  await check('lost creation reply offers same-body same-key manual retry despite edited input', async () => {
    element('brief').value = '离线任务需求'; element('style').value = '京剧写意'; creationFailure = true;
    element('agent-start').fire('click'); element('agent-start').fire('click'); await flush();
    const first = calls.find((call) => call.url.endsWith('/agent/create'));
    assert.ok(first); assert.equal(calls.filter((call) => call.url.endsWith('/agent/create')).length, 1);
    assert.equal(element('agent-submit-retry').hidden, false); assert.equal(element('agent-start').disabled, true);
    element('brief').value = '用户编辑后的新需求'; creationFailure = false;
    element('agent-submit-retry').fire('click'); await flush();
    const posts = calls.filter((call) => call.url.endsWith('/agent/create'));
    assert.equal(posts.length, 2); assert.equal(posts[0].options.headers['X-Idempotency-Key'], posts[1].options.headers['X-Idempotency-Key']);
    assert.equal(posts[0].options.body, posts[1].options.body); assert.equal(selectedPanel, 'agents');
    assert.deepEqual([...storage.values()], [taskId]);
  });
  await check('real returned Agent snapshot drives cards; repeated events are deduplicated', async () => {
    assert.equal(cards[0].querySelector('[data-agent-status]').dataset.state, 'running');
    assert.equal(element('agent-events').children.length, 2);
    element('agent-query').fire('click'); await flush();
    assert.equal(element('agent-events').children.length, 2);
    assert.ok(calls.filter((call) => call.url.includes('/agent/status/')).at(-1).url.endsWith('afterSequence=2'));
  });
  await check('poll queries do not overlap; hidden page pauses automatic queries', async () => {
    let release; requestPending = { promise: new Promise((resolve) => { release = resolve; }) };
    const before = calls.filter((call) => call.url.includes('/agent/status/')).length;
    element('agent-query').fire('click'); element('agent-query').fire('click'); await flush();
    assert.equal(calls.filter((call) => call.url.includes('/agent/status/')).length - before, 1);
    assert.equal(element('agent-query').disabled, true); release(); requestPending = null; await flush();
    globalThis.document.hidden = true; documentHandlers.get('visibilitychange')();
    assert.equal([...timers.values()].filter((timer) => timer.duration === 1000).length, 0);
    globalThis.document.hidden = false; documentHandlers.get('visibilitychange')(); await flush();
  });
  await check('lost status connection preserves last confirmed Agent state, pauses polling and never resubmits', async () => {
    const postCount = calls.filter((call) => call.url.endsWith('/agent/create')).length;
    networkFailure = true; element('agent-query').fire('click'); await flush();
    assert.equal(cards[0].querySelector('[data-agent-status]').dataset.state, 'running');
    assert.ok(element('agent-feedback').textContent.includes('上次后端结果'));
    assert.equal(calls.filter((call) => call.url.endsWith('/agent/create')).length, postCount);
    assert.equal([...timers.values()].filter((timer) => timer.duration === 1000).length, 0); networkFailure = false;
  });
  await check('outdated status snapshot cannot rewind a displayed stage', async () => {
    currentStatus = statusFixture({ sequence: 1, agentState: 'pending' });
    element('agent-query').fire('click'); await flush();
    assert.equal(cards[0].querySelector('[data-agent-status]').dataset.state, 'running');
  });
  await check('awaiting confirmation displays verified text and safe references; export stays disabled', async () => {
    currentStatus = statusFixture({ state: 'awaiting_confirmation', sequence: 8, agentState: 'completed', resultReady: true, events: [event(8, { kind: 'task', taskState: 'awaiting_confirmation' })] });
    element('agent-query').fire('click'); await flush();
    assert.equal(element('agent-result').hidden, false); assert.equal(element('agent-confirm').disabled, false); assert.equal(element('agent-download').disabled, true);
    const content = element('agent-result-content');
    assert.ok(content.textContent.includes('<img src=x onerror=alert(1)>'));
    assert.ok(content.textContent.includes('<script>alert(1)</script>'));
    assert.equal(descendants(content).filter((item) => ['IMG', 'SCRIPT'].includes(item.tagName)).length, 0);
    const links = descendants(content).filter((item) => item.tagName === 'A');
    assert.equal(links.length, 1); assert.equal(links[0].rel, 'noopener noreferrer');
  });
  await check('final acceptance sends current confirmation and sequence; server-confirmed export becomes available', async () => {
    element('agent-confirm').fire('click'); element('agent-confirm').fire('click'); await flush();
    const confirmations = calls.filter((call) => call.url.includes('/agent/confirm/'));
    assert.equal(confirmations.length, 1); assert.equal(JSON.parse(confirmations[0].options.body).expectedSequence, 8);
    assert.equal(element('agent-task-state').textContent, '已确认完成'); assert.equal(element('agent-download').disabled, false);
    assert.equal([...timers.values()].filter((timer) => timer.duration === 1000).length, 0);
  });
  await check('culture hold cannot be accepted or exported; no model request follows a state query', async () => {
    currentStatus = { ...statusFixture({ state: 'awaiting_confirmation', sequence: 10, resultReady: true }), confirmation: { id: 'offline-confirm-002', reason: 'needs_revision', canAccept: false } };
    currentResult = { ...resultFixture, uncertain: true, review: { ...resultFixture.review, verdict: 'needs_revision', issues: [{ field: 'costume', reason: '离线测试文化问题', evidenceIds: [citation.id] }] } };
    const confirmations = calls.filter((call) => call.url.includes('/agent/confirm/')).length;
    element('agent-query').fire('click'); await flush(); element('agent-confirm').fire('click');
    assert.equal(element('agent-confirm').hidden, true); assert.equal(element('agent-download').disabled, true);
    assert.equal(calls.filter((call) => call.url.includes('/agent/confirm/')).length, confirmations);
  });
  function newWidget() {
    const newElements = new Map(names.map((name) => [`#ai-workshop-${name}`, new Element()]));
    for (const id of contracts.WORKFLOW_AGENT_IDS) {
      const card = new Element('article'); card.bindings = new Map(['status', 'summary', 'timing'].map((field) => [`[data-agent-${field}]`, new Element()])); newElements.set(`[data-agent-id="${id}"]`, card);
    }
    const widget = new Element(); widget.bindings = newElements; widget.querySelectorAll = () => [];
    return { root: widget, element: (name) => newElements.get(`#ai-workshop-${name}`) };
  }
  await check('refresh restores only the task ID via free GET and does not re-create a paid task', async () => {
    timers.clear(); calls = []; currentStatus = statusFixture({ state: 'awaiting_confirmation', sequence: 10, resultReady: true }); currentResult = resultFixture;
    const fresh = newWidget();
    ui.initializeAgentWorkflow({ root: fresh.root, selectPanel() {}, refreshCapabilities() {} }); await flush();
    assert.equal(calls.filter((call) => call.url.endsWith('/agent/create')).length, 0);
    assert.ok(calls.some((call) => call.url.includes(`/agent/status/${taskId}`)));
    assert.ok(fresh.element('agent-task-id').textContent.includes(taskId)); assert.deepEqual([...storage.values()], [taskId]);
  });
  await check('invalid saved task identifier is ignored without a network call', async () => {
    timers.clear(); calls = []; storage.set('xijing.ai.agent.task.v1', '../../env');
    const fresh = newWidget(); ui.initializeAgentWorkflow({ root: fresh.root, selectPanel() {}, refreshCapabilities() {} }); await flush();
    assert.equal(calls.length, 0); storage.set('xijing.ai.agent.task.v1', taskId);
  });
  await check('unknown saved task is clearly invalidated; next explicit creation does not inherit its ID', async () => {
    timers.clear(); calls = [];
    globalThis.fetch = async (url, options) => {
      calls.push({ url, options }); return response({ error: { code: 'AGENT_TASK_NOT_FOUND', message: '离线测试：没有该任务', retryable: false }, requestId }, 404);
    };
    const fresh = newWidget(); const binding = ui.initializeAgentWorkflow({ root: fresh.root, selectPanel() {}, refreshCapabilities() {} }); await flush();
    assert.equal(storage.has('xijing.ai.agent.task.v1'), false); assert.equal(fresh.element('agent-task-state').textContent, '任务记录未找到');
    binding.setCapability(contracts.validateCapabilities(enabled)); fresh.element('brief').value = '离线新需求'; fresh.element('style').value = '京剧写意';
    globalThis.fetch = async (url, options) => { calls.push({ url, options }); return response(url.endsWith('/agent/create') ? created : statusFixture(), url.endsWith('/agent/create') ? 202 : 200); };
    fresh.element('agent-start').fire('click'); await flush();
    const payload = JSON.parse(calls.find((call) => call.url.endsWith('/agent/create')).options.body);
    assert.equal(payload.parentTaskId, undefined);
  });
  await check('cancel request preserves real running stage until backend marks task cancelled', async () => {
    timers.clear(); calls = []; currentStatus = statusFixture({ sequence: 2, events: [event(2)] });
    globalThis.fetch = async (url, options) => {
      calls.push({ url, options });
      if (url.includes('/agent/cancel/')) { currentStatus = { ...statusFixture({ sequence: 3 }), cancelRequested: true }; return response(currentStatus); }
      return response(currentStatus);
    };
    const fresh = newWidget(); ui.initializeAgentWorkflow({ root: fresh.root, selectPanel() {}, refreshCapabilities() {} }); await flush();
    fresh.element('agent-cancel').fire('click'); await flush();
    const cancelled = calls.find((call) => call.url.includes('/agent/cancel/'));
    assert.equal(JSON.parse(cancelled.options.body).expectedSequence, 2);
    assert.equal(fresh.element('agent-task-state').textContent, '协作运行中'); assert.equal(fresh.element('agent-cancel').disabled, true);
    currentStatus = { ...statusFixture({ state: 'cancelled', sequence: 4, agentState: 'completed' }), cancelRequested: true };
    fresh.element('agent-query').fire('click'); await flush();
    assert.equal(fresh.element('agent-task-state').textContent, '已取消');
    assert.match(fresh.element('agent-feedback').textContent, /任务已取消/);
    assert.equal(fresh.root.querySelector('[data-agent-id="researcher"]').querySelector('[data-agent-status]').dataset.state, 'pending');
    assert.equal([...timers.values()].filter((timer) => timer.duration === 1000).length, 0);
  });
  await check('automatic status polling is bounded and ends without inventing a task failure', async () => {
    timers.clear(); calls = []; currentStatus = statusFixture();
    globalThis.fetch = async (url, options) => { calls.push({ url, options }); return response(currentStatus); };
    const fresh = newWidget(); ui.initializeAgentWorkflow({ root: fresh.root, selectPanel() {}, refreshCapabilities() {} }); await flush();
    for (let index = 0; index < 200; index += 1) {
      const pending = [...timers].find(([, timer]) => timer.duration === 1000);
      if (!pending) break;
      timers.delete(pending[0]); pending[1].handler(); await flush();
    }
    assert.equal(calls.length, 180); assert.ok(fresh.element('agent-feedback').textContent.includes('自动查询已达到时限'));
    assert.equal(fresh.root.querySelector('[data-agent-id="planner"]').querySelector('[data-agent-status]').dataset.state, 'running');
    assert.equal([...timers.values()].filter((timer) => timer.duration === 1000).length, 0);
  });
  await check('HTML binding/version chain and only safe text construction (static)', async () => {
    const html = await readFile(new URL('about.html', repo), 'utf8');
    for (const name of names) assert.ok(html.includes(`id="ai-workshop-${name}"`), name);
    for (const id of contracts.WORKFLOW_AGENT_IDS) assert.ok(html.includes(`data-agent-id="${id}"`), id);
    assert.ok(html.includes('main.js?v=phase4-1')); assert.ok(html.includes('ai-workshop.css?v=phase4-1'));
    for (const file of ['main', 'services', 'agent-workflow']) {
      const source = await readFile(new URL(`js/ai-workshop/${file}.js`, repo), 'utf8');
      assert.equal(/(?:innerHTML|outerHTML)\s*=|insertAdjacentHTML|eval\s*\(/.test(source), false);
      assert.equal(source.includes('?v=phase2-1'), false);
    }
    assert.ok(html.includes('AI生成概念图 · 待开放')); assert.ok(html.includes('新增建模已关闭'));
    assert.match(html, /id="ai-workshop-model-submit"[^>]*disabled/);
    assert.ok(html.includes('第三次取消'));
  });
} finally {
  for (const [name, value] of Object.entries(savedGlobals)) {
    if (value === undefined) delete globalThis[name]; else globalThis[name] = value;
  }
}
const report = { kind: 'OFFLINE_EXPLICIT_TEST_DOUBLES_AND_STATIC_CHECKS', disclaimer: 'Not real LLM, RAG, backend, browser, CSS layout or model-availability evidence.', executedAt: new Date().toISOString(), nodeVersion: process.version, command: `node scripts/phase3_frontend_test.mjs ${process.argv.slice(2).join(' ')}`.trim(), results, passed: results.filter((item) => item.passed).length, failed: results.filter((item) => !item.passed).length };
const outputPosition = process.argv.indexOf('--output');
if (outputPosition >= 0) { const path = process.argv[outputPosition + 1]; if (!path) throw new Error('--output requires a path'); await mkdir(dirname(path), { recursive: true }); await writeFile(path, `${JSON.stringify(report, null, 2)}\n`, 'utf8'); }
console.log(JSON.stringify(report, null, 2));
if (report.failed) process.exitCode = 1;
