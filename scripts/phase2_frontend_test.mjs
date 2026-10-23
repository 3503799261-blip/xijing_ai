/**
 * Offline contract/service/UI unit checks using explicit test doubles.
 * No provider, browser or real RAG output is used or claimed by this script.
 * Run: node scripts/phase2_frontend_test.mjs [--output path/to/report.json]
 */
import assert from 'node:assert/strict';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { dirname } from 'node:path';

const root = new URL('../', import.meta.url);
const c = await import(new URL('js/ai-workshop/contracts.js?v=phase3-1', root));
const s = await import(new URL('js/ai-workshop/services.js?v=phase3-1', root));
const results = [];
const check = async (name, operation) => {
  try { await operation(); results.push({ name, passed: true }); }
  catch (error) { results.push({ name, passed: false, error: error.message }); }
};
const citation = { id: 'test-citation', title: '离线结构测试资料', sourceId: 'test-source', locator: '测试章节', url: 'https://example.org/test', excerpt: '离线测试片段；不作为京剧知识。', contentKind: 'original_fact_summary' };
const answer = { answer: '离线结构测试：这不是AI回答。', citations: [citation], uncertain: false, requestId: 'test-request' };
const enabled = { questionAnswering: true, agentWorkflow: false, conceptImage: false, imageToModel: false, knowledgeSearch: true };
const reply = (body, status = 200) => ({ ok: status >= 200 && status < 300, status, json: async () => body });
const originalFetch = globalThis.fetch;
const originalTimeout = globalThis.setTimeout;
const originalDocument = globalThis.document;
const originalLocation = globalThis.location;
const originalWindow = globalThis.window;

await check('grounded response and original fact-summary metadata', () => assert.equal(c.validateQuestionAnswer(answer).citations[0].contentKind, 'original_fact_summary'));
await check('reject certain answer without evidence', () => assert.throws(() => c.validateQuestionAnswer({ ...answer, citations: [] })));
await check('explicit insufficient evidence may have no citations', () => assert.equal(c.validateQuestionAnswer({ ...answer, uncertain: true, citations: [] }).uncertain, true));
await check('reject duplicate citation identifiers', () => assert.throws(() => c.validateQuestionAnswer({ ...answer, citations: [citation, citation] })));
await check('reject malformed answer fields', () => assert.throws(() => c.validateQuestionAnswer({ ...answer, requestId: null })));
await check('AI capabilities follow backend gates, while default image/model stay off', () => { const caps = c.validateCapabilities({ ...enabled, agentWorkflow: true, conceptImage: true, imageToModel: true }); assert.equal(caps.agentWorkflow, true); assert.equal(caps.conceptImage, true); assert.equal(caps.imageToModel, true); assert.equal(c.validateCapabilities(enabled).imageToModel, false); assert.equal(c.validateCapabilities(enabled).conceptImage, false); });
await check('reject incomplete capabilities', () => assert.throws(() => c.validateCapabilities({ questionAnswering: true })));
await check('source URL protocol and credential validation', () => {
  for (const url of ['javascript:alert(1)', 'data:text/html,a', 'https://user:secret@example.org', '/backend/file']) assert.equal(c.safeCitationUrl(url), null);
  assert.equal(c.safeCitationUrl('https://example.org/path'), 'https://example.org/path');
});

let requests = [];
globalThis.location = { origin: 'http://127.0.0.1:8000', hash: '' };
globalThis.fetch = async (url, options) => { requests.push({ url, options }); return reply(url.endsWith('/capabilities') ? enabled : answer); };
await check('concurrent capability requests coalesce', async () => { await Promise.all([s.loadServiceCapabilities(), s.loadServiceCapabilities()]); assert.equal(requests.length, 1); });
await check('same-origin chat and idempotency header', async () => {
  await s.askOperaQuestion({ question: '  离线测试问题  ' }, { idempotencyKey: 'test-submit-123' });
  assert.equal(requests.at(-1).url, 'http://127.0.0.1:8000/api/v1/chat');
  assert.equal(requests.at(-1).options.headers['X-Idempotency-Key'], 'test-submit-123');
  assert.equal(JSON.parse(requests.at(-1).options.body).question, '离线测试问题');
});
await check('one-argument askOperaQuestion remains compatible', async () => { await s.askOperaQuestion({ question: '离线签名兼容测试' }); assert.ok(requests.at(-1).options.headers['X-Idempotency-Key']); });
await check('capability cache recovers after network failure', async () => {
  globalThis.fetch = async () => { throw new TypeError('offline test failure'); };
  await assert.rejects(s.loadServiceCapabilities(), (error) => error.code === 'NETWORK_ERROR');
  assert.equal(s.getServiceCapabilities().questionAnswering, false);
  globalThis.fetch = async () => reply(enabled);
  await s.loadServiceCapabilities();
  assert.equal(s.getServiceCapabilities().questionAnswering, true);
});
await check('failed chat immediately invalidates cached ready capabilities', async () => {
  globalThis.fetch = async () => reply(enabled);
  await s.loadServiceCapabilities();
  globalThis.fetch = async () => { throw new TypeError('offline chat failure'); };
  await assert.rejects(s.askOperaQuestion({ question: '离线连接失败状态测试' }), (error) => error.code === 'NETWORK_ERROR');
  assert.equal(s.getServiceCapabilities().questionAnswering, false);
});
await check('earlier capability request cannot restore readiness after a chat connection failure', async () => {
  globalThis.fetch = async () => reply(enabled);
  await s.loadServiceCapabilities();
  let release;
  const waiting = new Promise((resolve) => { release = resolve; });
  globalThis.fetch = async (url) => {
    if (url.endsWith('/capabilities')) { await waiting; return reply(enabled); }
    throw new TypeError('offline chat failure while capabilities are loading');
  };
  const earlier = s.loadServiceCapabilities();
  await assert.rejects(s.askOperaQuestion({ question: '离线能力请求竞争测试' }), (error) => error.code === 'NETWORK_ERROR');
  release();
  await earlier;
  assert.equal(s.getServiceCapabilities().questionAnswering, false);
});
await check('typed backend error preserves real request identifier', async () => {
  globalThis.fetch = async () => reply({ error: { code: 'LLM_NOT_CONFIGURED', message: '离线测试：模型未配置', retryable: true }, requestId: 'error-request' }, 503);
  await assert.rejects(s.askOperaQuestion({ question: '离线错误测试' }), (error) => error.code === 'LLM_NOT_CONFIGURED' && error.requestId === 'error-request');
});
await check('upstream model timeout invalidates readiness without automatically retrying chat', async () => {
  globalThis.fetch = async () => reply(enabled);
  await s.loadServiceCapabilities();
  let calls = 0;
  globalThis.fetch = async () => { calls += 1; return reply({ error: { code: 'LLM_TIMEOUT', message: '离线测试：供应商响应超时', retryable: true }, requestId: 'timeout-request' }, 504); };
  await assert.rejects(s.askOperaQuestion({ question: '离线供应商超时状态测试' }), (error) => error.code === 'LLM_TIMEOUT' && s.requiresCapabilityRecheck(error));
  assert.equal(s.getServiceCapabilities().questionAnswering, false); assert.equal(calls, 1);
});
await check('service rejects malformed successful response', async () => {
  globalThis.fetch = async () => reply({ ...answer, citations: [] });
  await assert.rejects(s.askOperaQuestion({ question: '离线坏引用测试' }), (error) => error.code === 'INVALID_RESPONSE');
});
await check('55-second budget aborts with no automatic retry (accelerated test clock)', async () => {
  const budgets = []; let calls = 0;
  globalThis.fetch = async () => reply(enabled);
  await s.loadServiceCapabilities();
  try {
    globalThis.setTimeout = (callback, milliseconds) => { budgets.push(milliseconds); return originalTimeout(callback, 5); };
    globalThis.fetch = async (url, { signal }) => {
      calls += 1;
      return new Promise((resolve, reject) => signal.addEventListener('abort', () => reject(new DOMException('Offline timeout test', 'AbortError')), { once: true }));
    };
    await assert.rejects(s.askOperaQuestion({ question: '离线超时测试' }), (error) => error.code === 'REQUEST_TIMEOUT');
    assert.deepEqual(budgets, [55000]); assert.equal(calls, 1); assert.equal(s.getServiceCapabilities().questionAnswering, false);
  } finally { globalThis.setTimeout = originalTimeout; }
});
await check('image and model services return unavailable without a network request', async () => {
  let calls = 0; globalThis.fetch = () => { calls += 1; throw new Error('must not call'); };
  for (const value of [await s.generateConceptImage({}), await s.submitModelTask({})]) assert.equal(value.available, false);
  assert.equal(calls, 0);
});

// The current chat UI is tested independently of Agent and asset controllers.
// All histories below are explicit in-memory test doubles, never real AI output.
const chatContracts = await import(new URL('js/ai-workshop/chat-contracts.js?v=product-1', root));
const chatUi = await import(new URL('js/ai-workshop/chat-controller.js?v=product-1', root));
const originalStorage = globalThis.localStorage;
const id1 = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
const id2 = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb';
const date = '2026-10-23T01:00:00Z';
const summaries = new Map(); let currentCreate = 0; const apiCalls = [];
const summary = (item) => ({ id: item.id, title: item.title, createdAt: item.createdAt, updatedAt: item.updatedAt, turnCount: item.turns.length });
const completedTurn = (question, key, result = answer) => ({ id: key, idempotencyKey: key, question, status: 'completed', answer: result, createdAt: date });
function makeConversation(id, turns = []) { const value = { id, title: '离线测试会话', createdAt: date, updatedAt: date, turns }; summaries.set(id, value); return value; }
const valueCopy = (value) => structuredClone(value);
await check('chat contracts accept separate durable conversation identities and complete citations', () => {
  const detail = makeConversation(id1, [completedTurn('离线问题', 'offline-key-001')]);
  assert.equal(chatContracts.validateConversation(detail).turns[0].answer.citations[0].id, citation.id);
  assert.equal(chatContracts.validateConversationList({ items: [summary(detail)], hasMore: false }).items[0].id, id1);
  summaries.clear();
});
await check('chat contracts reject duplicate histories, traversal, invalid dates and invented answer evidence', () => {
  const item = { id: id1, title: '测试', createdAt: date, updatedAt: date, turns: [] };
  assert.throws(() => chatContracts.conversationId('../agent/history'));
  assert.throws(() => chatContracts.validateConversationList({ items: [summary(item), summary(item)], hasMore: false }));
  assert.throws(() => chatContracts.validateConversation({ ...item, updatedAt: 'not-a-date' }));
  assert.throws(() => chatContracts.validateConversation({ ...item, turns: [completedTurn('测试', 'offline-key-002', { ...answer, citations: [] })] }));
});
class Element {
  constructor(tag = 'div') { this.tagName = tag.toUpperCase(); this.children = []; this.dataset = {}; this.attributes = {}; this.listeners = new Map(); this.hidden = false; this.disabled = false; this.value = ''; this._text = ''; this.className = ''; this.open = true; this.scrollHeight = 100; }
  set textContent(value) { this.children = []; this._text = String(value); }
  get textContent() { return this._text + this.children.map(child => child.textContent).join(''); }
  set innerHTML(_value) { throw new Error('Unsafe HTML injection'); }
  append(...elements) { for (const element of elements) { element.parent = this; this.children.push(element); } }
  replaceChildren(...elements) { this.children = []; this._text = ''; this.append(...elements); }
  remove() { if (this.parent) this.parent.children = this.parent.children.filter(child => child !== this); }
  setAttribute(name, value) { this.attributes[name] = String(value); }
  removeAttribute(name) { delete this.attributes[name]; }
  addEventListener(name, handler) { this.listeners.set(name, [...this.listeners.get(name) || [], handler]); }
  fire(name, event = {}) { const value = { preventDefault() {}, ...event }; for (const handler of this.listeners.get(name) || []) handler(value); }
  focus() { this.focused = true; }
  requestSubmit() { this.fire('submit'); }
  querySelectorAll(selector) { const all = this.children.flatMap(child => [child, ...child.querySelectorAll('*')]); return all.filter(child => selector === '*' || selector === 'button' && child.tagName === 'BUTTON' || selector === 'button[data-conversation-id]' && child.tagName === 'BUTTON' && child.dataset.conversationId || selector === '.ai-workshop-turn' && child.className === 'ai-workshop-turn'); }
  querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }
}
const ids = ['question-form', 'question', 'send', 'messages', 'qa-service-error', 'retry-question', 'question-error', 'question-count', 'qa-loading', 'conversations', 'conversation-status', 'more-conversations', 'new-conversation', 'current-conversation', 'citations', 'conversation-sidebar'];
const elements = new Map(ids.map(id => [`#ai-workshop-${id}`, new Element(id.includes('conversation') && id === 'new-conversation' ? 'button' : 'div')]));
const rootElement = new Element();
rootElement.querySelector = selector => elements.get(selector) || null;
rootElement.querySelectorAll = () => [];
const byId = id => elements.get(`#ai-workshop-${id}`);
const descendants = element => element.children.flatMap(child => [child, ...descendants(child)]);
const turns = () => byId('messages').children.filter(child => child.className === 'ai-workshop-turn');
const storage = new Map();
globalThis.localStorage = { getItem: key => storage.get(key) || null, setItem: (key, value) => storage.set(key, value) };
globalThis.document = { createElement: tag => new Element(tag), querySelector: () => null };
globalThis.window = { location: globalThis.location };
const defaultFetch = async (url, options = {}) => {
  const request = { url, options }; apiCalls.push(request);
  const parsed = new URL(url);
  if (parsed.pathname === '/api/v1/chat/conversations') {
    if (options.method === 'POST') return reply(valueCopy(makeConversation(currentCreate++ === 0 ? id1 : id2)));
    return reply({ items: [...summaries.values()].map(summary), hasMore: false });
  }
  if (parsed.pathname.startsWith('/api/v1/chat/conversations/')) return reply(valueCopy(summaries.get(parsed.pathname.split('/').at(-1))));
  if (parsed.pathname === '/api/v1/capabilities') return reply(enabled);
  if (parsed.pathname === '/api/v1/chat') {
    const body = JSON.parse(options.body); const item = summaries.get(body.conversationId); assert.ok(item, 'Existing selected conversation is required');
    const key = options.headers['X-Idempotency-Key']; const result = { ...answer, requestId: `offline-${apiCalls.length}` };
    if (!item.turns.some(turn => turn.idempotencyKey === key)) item.turns.push(completedTurn(body.question, key, result));
    return reply(result);
  }
  throw new Error('Unexpected offline route');
};
globalThis.fetch = defaultFetch;
const flush = async () => { for (let index = 0; index < 12; index += 1) await Promise.resolve(); await new Promise(resolve => originalTimeout(resolve, 0)); };
const states = [];
const controller = chatUi.initializeChat({ root: rootElement, setServiceState: (...values) => states.push(values), onServiceFailure() {} });
await flush();
const chatCalls = () => apiCalls.filter(call => new URL(call.url).pathname === '/api/v1/chat');
await check('new controller reads empty persisted history without creating conversations or sending chat', () => {
  assert.equal(apiCalls.filter(call => call.options.method === 'POST').length, 0);
  assert.ok(byId('conversation-status').textContent.includes('还没有历史会话')); assert.equal(controller.isBusy(), false);
});
await check('explicit new conversation creates one independent server session without a model request', async () => {
  byId('new-conversation').fire('click'); await flush();
  assert.equal(summaries.size, 1); assert.equal(chatCalls().length, 0); assert.equal(storage.get('xijing-selected-chat-v1'), id1);
});
await check('pending lock prevents duplicate sends and preserves a newer draft while provider result returns', async () => {
  let release; const pending = new Promise(resolve => { release = resolve; });
  globalThis.fetch = async (url, options) => { if (new URL(url).pathname === '/api/v1/chat') await pending; return defaultFetch(url, options); };
  byId('question').value = '离线第一题'; byId('question-form').fire('submit'); byId('question-form').fire('submit');
  assert.equal(controller.isBusy(), true); assert.equal(byId('send').disabled, true); assert.equal(byId('messages').attributes['aria-busy'], 'true');
  byId('question').value = '等待期间编辑的新问题'; release(); await flush();
  assert.equal(chatCalls().length, 1); assert.equal(byId('question').value, '等待期间编辑的新问题'); assert.equal(turns().length, 1); assert.equal(byId('send').disabled, false);
  globalThis.fetch = defaultFetch;
});
await check('continuing a conversation forwards its real identifier and retains ordered per-answer citations safely', async () => {
  const injected = { ...answer, answer: '<img src=x onerror=alert(1)>离线文本', requestId: 'offline-text-only' };
  globalThis.fetch = async (url, options) => {
    const response = await defaultFetch(url, options);
    if (new URL(url).pathname === '/api/v1/chat') { const item = summaries.get(id1); item.turns.at(-1).answer = injected; return reply(injected); }
    return response;
  };
  byId('question').value = '离线追问题'; byId('question-form').fire('submit'); await flush();
  assert.equal(JSON.parse(chatCalls().at(-1).options.body).conversationId, id1); assert.equal(turns().length, 2);
  assert.equal(descendants(byId('messages')).filter(child => child.dataset.messageRole === 'assistant').length, 2);
  assert.ok(byId('messages').textContent.includes('<img src=x onerror=alert(1)>'));
  assert.equal(descendants(byId('messages')).filter(child => child.tagName === 'IMG').length, 0);
  assert.equal(descendants(byId('messages')).filter(child => child.className === 'ai-workshop-answer-references').length, 2);
  globalThis.fetch = defaultFetch;
});
await check('new session has no previous messages and switching restores server messages and session draft', async () => {
  byId('question').value = '第一会话未发送草稿'; byId('new-conversation').fire('click'); await flush();
  assert.equal(storage.get('xijing-selected-chat-v1'), id2); assert.equal(turns().length, 0); assert.equal(byId('question').value, '');
  byId('question').value = '第二会话独立问题'; byId('question-form').fire('submit'); await flush();
  assert.equal(JSON.parse(chatCalls().at(-1).options.body).conversationId, id2); assert.equal(turns().length, 1);
  byId('conversations').children.find(child => child.dataset.conversationId === id1).fire('click'); await flush();
  assert.equal(turns().length, 2); assert.ok(!byId('messages').textContent.includes('第二会话独立问题')); assert.equal(byId('question').value, '第一会话未发送草稿');
});
await check('failed send keeps input and manual retry reuses one key without duplicate UI turn or automatic request', async () => {
  const keys = []; let fail = true;
  globalThis.fetch = async (url, options) => {
    if (new URL(url).pathname === '/api/v1/chat') { keys.push(options.headers['X-Idempotency-Key']); if (fail) return reply({ error: { code: 'LLM_TIMEOUT', message: '离线测试：超时，未自动重发', retryable: true }, requestId: 'offline-timeout' }, 504); }
    return defaultFetch(url, options);
  };
  byId('question').value = '离线失败重试'; byId('question-form').fire('submit'); await flush(); const count = turns().length;
  assert.equal(keys.length, 1); assert.equal(byId('question').value, '离线失败重试'); assert.equal(byId('retry-question').hidden, false); assert.equal(controller.isBusy(), false);
  await flush(); assert.equal(keys.length, 1); fail = false; byId('retry-question').fire('click'); await flush();
  assert.deepEqual(keys, [keys[0], keys[0]]); assert.equal(turns().length, count); assert.equal(byId('qa-service-error').hidden, true); assert.equal(byId('question').value, '');
  globalThis.fetch = defaultFetch;
});
await check('an older failed turn followed by a completed turn cannot be retried out of sequence', async () => {
  const item = summaries.get(id2);
  item.turns = [{ id: 'offline-old-failure', idempotencyKey: 'offline-old-failure', question: '旧失败请求', status: 'failed', error: { code: 'SEARCH_TIMEOUT', message: '离线旧失败', retryable: true }, createdAt: date }, completedTurn('后续已完成问题', 'offline-later-turn')];
  const count = chatCalls().length; byId('conversations').children.find(child => child.dataset.conversationId === id2).fire('click'); await flush();
  assert.equal(byId('retry-question').hidden, true); assert.ok(byId('messages').textContent.includes('后续已完成问题')); assert.equal(chatCalls().length, count);
  byId('conversations').children.find(child => child.dataset.conversationId === id1).fire('click'); await flush();
});
await check('unknown historical request stays visibly unresolved without enabling automatic retry', async () => {
  const item = summaries.get(id2); item.turns = [{ id: 'offline-unknown', idempotencyKey: 'offline-unknown', question: '离线未知请求', status: 'unknown', createdAt: date }];
  const count = chatCalls().length; byId('conversations').children.find(child => child.dataset.conversationId === id2).fire('click'); await flush();
  assert.ok(byId('messages').textContent.includes('结果尚未确认')); assert.equal(byId('retry-question').hidden, true); assert.equal(chatCalls().length, count);
});
await check('blank and overlong questions do not send; Enter sends while Shift+Enter and IME composition do not', async () => {
  let count = chatCalls().length;
  byId('question').value = '  '; byId('question-form').fire('submit'); await flush(); assert.equal(chatCalls().length, count);
  byId('question').value = '字'.repeat(601); byId('question-form').fire('submit'); await flush(); assert.equal(chatCalls().length, count); assert.equal(byId('question').attributes['aria-invalid'], 'true');
  byId('question').value = '离线键盘问题'; byId('question').fire('keydown', { key: 'Enter', shiftKey: true }); byId('question').fire('keydown', { key: 'Enter', isComposing: true }); await flush(); assert.equal(chatCalls().length, count);
  byId('question').fire('keydown', { key: 'Enter' }); await flush(); assert.equal(chatCalls().length, count + 1);
});
await check('chat transport rejects invalid identities locally; list/create/detail routes stay separate from Agent history', async () => {
  let calls = 0; globalThis.fetch = async () => { calls += 1; return reply({}); };
  assert.throws(() => s.getConversation('../agent/history'), error => error.code === 'INVALID_CONVERSATION'); assert.equal(calls, 0);
  assert.throws(() => s.listConversations(-1));
  const routes = [];
  globalThis.fetch = async (url, options) => { routes.push({ url, method: options.method }); return reply(options.method === 'POST' || new URL(url).pathname.endsWith(id1) ? summaries.get(id1) : { items: [], hasMore: false }); };
  await s.listConversations(); await s.createConversation(); await s.getConversation(id1);
  assert.equal(routes.length, 3); assert.ok(routes.every(route => new URL(route.url).pathname.startsWith('/api/v1/chat/conversations'))); assert.deepEqual(routes.map(route => route.method), ['GET', 'POST', 'GET']);
  globalThis.fetch = defaultFetch;
});
await check('HTML bindings, safe text rendering and module chain remain complete (static)', async () => {
  const html = await readFile(new URL('about.html', root), 'utf8'); const code = await readFile(new URL('js/ai-workshop/chat-controller.js', root), 'utf8'); const main = await readFile(new URL('js/ai-workshop/main.js', root), 'utf8'); const services = await readFile(new URL('js/ai-workshop/services.js', root), 'utf8'); const css = await readFile(new URL('css/ai-workshop.css', root), 'utf8');
  const requiredIds = [...code.matchAll(/byId\('([^']+)'\)/g)].map(match => `ai-workshop-${match[1]}`);
  for (const id of requiredIds) assert.ok(html.includes(`id="${id}"`), `missing chat HTML binding: ${id}`);
  for (const source of [code, main, services]) assert.equal(/(?:innerHTML|outerHTML)\s*=|insertAdjacentHTML|eval\s*\(/.test(source), false);
  assert.ok(main.includes('chat-controller.js?v=product-1')); assert.ok(services.includes('chat-contracts.js?v=product-1')); assert.ok(css.includes('.ai-workshop-citation')); assert.ok(css.includes('prefers-reduced-motion'));
});
globalThis.localStorage = originalStorage;

globalThis.fetch = originalFetch;
globalThis.setTimeout = originalTimeout;
globalThis.document = originalDocument;
globalThis.location = originalLocation;
globalThis.window = originalWindow;
const report = { kind: 'OFFLINE_TEST_DOUBLES_AND_STATIC_CHECKS', disclaimer: 'Not a real LLM, RAG, browser, CSS layout or API availability test.', executedAt: new Date().toISOString(), nodeVersion: process.version, command: ['node scripts/phase2_frontend_test.mjs', ...process.argv.slice(2)].join(' '), results, passed: results.filter((result) => result.passed).length, failed: results.filter((result) => !result.passed).length };
const outputIndex = process.argv.indexOf('--output');
if (outputIndex >= 0) {
  const output = process.argv[outputIndex + 1];
  if (!output) throw new Error('--output requires a path');
  await mkdir(dirname(output), { recursive: true }); await writeFile(output, `${JSON.stringify(report, null, 2)}\n`, 'utf8');
}
console.log(JSON.stringify(report, null, 2));
if (report.failed) process.exitCode = 1;
