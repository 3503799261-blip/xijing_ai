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
await check('Agent capability follows backend; image and model remain disabled', () => { const caps = c.validateCapabilities({ ...enabled, agentWorkflow: true, conceptImage: true, imageToModel: true }); assert.equal(caps.agentWorkflow, true); assert.equal(caps.conceptImage, false); assert.equal(caps.imageToModel, false); });
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

// Minimal DOM double checks behavior and text construction only. It does not
// implement a browser renderer, HTML parser, accessibility tree or CSS layout.
class Element {
  constructor(tag = 'div') {
    this.tagName = tag.toUpperCase(); this.children = []; this.dataset = {}; this.attributes = {};
    this.listeners = new Map(); this.hidden = false; this.disabled = false; this.value = ''; this._text = '';
    this.className = ''; this.classList = { add() {}, remove() {}, toggle() {} }; this.style = { setProperty() {} };
    this.options = []; this.selectedIndex = 0; this.offsetHeight = 82; this.scrollHeight = 100;
  }
  set textContent(value) { this.children = []; this._text = String(value); }
  get textContent() { return this._text + this.children.map((child) => child.textContent).join(''); }
  append(...elements) { for (const element of elements) { element.parent = this; this.children.push(element); } }
  replaceChildren(...elements) { this.children = []; this._text = ''; this.append(...elements); }
  remove() { if (this.parent) this.parent.children = this.parent.children.filter((child) => child !== this); }
  setAttribute(name, value) { this.attributes[name] = String(value); }
  removeAttribute(name) { delete this.attributes[name]; }
  addEventListener(name, handler) { const list = this.listeners.get(name) || []; list.push(handler); this.listeners.set(name, list); }
  fire(name, event = {}) { for (const handler of this.listeners.get(name) || []) handler({ preventDefault() {}, button: 0, ...event }); }
  focus() { this.focused = true; }
  scrollIntoView() {}
  reset() { this.value = ''; }
}
const elements = new Map(); const workshop = new Element();
const names = ['overview', 'qa', 'agents', 'create', 'model'];
for (const name of names) {
  elements.set(`[data-ai-workshop-panel="${name}"]`, new Element('section'));
  elements.set(`[data-ai-workshop-panel="${name}"] h2[tabindex="-1"]`, new Element('h2'));
}
const ids = ['question-form', 'question', 'question-count', 'question-error', 'send', 'messages', 'qa-status', 'qa-loading', 'qa-service-error', 'retry-question', 'refresh-service', 'citations', 'hero-service-note', 'creation-form', 'brief', 'style', 'brief-error', 'draft-content', 'draft-status', 'save-draft', 'reset-draft', 'notice'];
for (const id of ids) elements.set(`#ai-workshop-${id}`, new Element());
const byId = (id) => elements.get(`#ai-workshop-${id}`);
const nav = names.map((name) => { const link = new Element('a'); link.dataset.aiWorkshopTarget = name; return link; });
const badges = [new Element('span'), new Element('span')];
workshop.querySelector = (selector) => elements.get(selector) || null;
workshop.querySelectorAll = (selector) => selector === '[data-ai-workshop-target]' ? nav : selector === '[data-ai-workshop-qa-capability]' ? badges : [];
globalThis.document = { readyState: 'complete', querySelector: (selector) => selector === '#ai-workshop' ? workshop : selector === '.site-header' ? new Element('header') : null, createElement: (tag) => new Element(tag) };
globalThis.window = { location: globalThis.location, history: { pushState(a, b, hash) { globalThis.location.hash = hash; } }, addEventListener() {} };
globalThis.fetch = async (url) => reply(url.endsWith('/capabilities') ? enabled : answer);
const flush = async () => { await new Promise((resolve) => originalTimeout(resolve, 0)); };
const descendants = (element) => element.children.flatMap((child) => [child, ...descendants(child)]);
const turns = () => byId('messages').children.filter((element) => element.className === 'ai-workshop-turn');
await import(new URL('js/ai-workshop/main.js?v=phase3-1', root));
await flush();

await check('UI capabilities and status are driven by fetched state (DOM double)', () => {
  assert.equal(byId('qa-status').dataset.serviceState, 'ready');
  assert.equal(badges[0].dataset.serviceState, 'ready');
});
await check('UI pending lock blocks duplicate submissions and preserves a newer input (DOM double)', async () => {
  let release; const waiting = new Promise((resolve) => { release = resolve; }); const calls = [];
  globalThis.fetch = async (url, options) => { if (url.endsWith('/capabilities')) return reply(enabled); calls.push(options); await waiting; return reply(answer); };
  byId('question').value = '离线第一题';
  byId('question-form').fire('submit'); byId('question-form').fire('submit');
  assert.equal(calls.length, 1); assert.equal(byId('send').disabled, true); assert.equal(byId('messages').attributes['aria-busy'], 'true');
  byId('question').value = '等待期间编辑的新问题'; release(); await flush();
  assert.equal(byId('question').value, '等待期间编辑的新问题'); assert.equal(byId('send').disabled, false);
  assert.equal(byId('messages').attributes['aria-busy'], 'false');
  assert.equal(turns().length, 1);
});
await check('UI keeps each answer citation identity and uses text nodes (DOM double)', async () => {
  const second = { ...answer, answer: '<img src=x onerror=alert(1)> 离线测试文本', requestId: 'test-request-2' };
  globalThis.fetch = async () => reply(second);
  byId('question').value = '离线第二题'; byId('question-form').fire('submit'); await flush();
  assert.equal(byId('citations').dataset.requestId, 'test-request-2');
  const firstAnswer = descendants(turns()[0]).find((element) => element.dataset.messageRole === 'assistant');
  firstAnswer.children.find((element) => element.tagName === 'BUTTON').fire('click');
  assert.equal(byId('citations').dataset.requestId, 'test-request');
  assert.ok(byId('messages').textContent.includes('<img src=x onerror=alert(1)>'));
  assert.equal(descendants(byId('messages')).filter((element) => element.tagName === 'IMG').length, 0);
});
await check('UI free capability recheck preserves the error, retry and history; manual retry reuses its key (DOM double)', async () => {
  const keys = []; let fail = true; let backendOnline = false; let capabilityCalls = 0;
  globalThis.fetch = async (url, options) => {
    if (url.endsWith('/capabilities')) { capabilityCalls += 1; if (!backendOnline) throw new TypeError('offline capabilities'); return reply(enabled); }
    keys.push(options.headers['X-Idempotency-Key']);
    if (fail) throw new TypeError('offline failure');
    return reply({ ...answer, requestId: 'retry-request' });
  };
  byId('question').value = '离线手动重试题'; byId('question-form').fire('submit'); await flush();
  const count = turns().length; assert.equal(byId('retry-question').hidden, false);
  const afterFailure = { calls: capabilityCalls, state: badges[0].dataset.serviceState, cache: s.getServiceCapabilities().questionAnswering, error: byId('qa-service-error').textContent, status: byId('qa-status').dataset.serviceState };
  const historyRequestIds = descendants(byId('messages')).filter((element) => element.dataset.messageRole === 'assistant').map((element) => element.dataset.requestId);
  backendOnline = true; byId('refresh-service').fire('click'); await flush();
  const afterRecovery = { state: badges[0].dataset.serviceState, error: byId('qa-service-error').textContent, retryHidden: byId('retry-question').hidden, status: byId('qa-status').dataset.serviceState, chats: keys.length };
  fail = false; byId('retry-question').fire('click'); await flush();
  assert.equal(keys.length, 2); assert.equal(keys[0], keys[1]); assert.equal(turns().length, count);
  assert.equal(byId('qa-service-error').hidden, true);
  assert.equal(afterFailure.calls, 1); assert.equal(afterFailure.state, 'unavailable'); assert.equal(afterFailure.cache, false); assert.equal(afterFailure.status, 'error');
  assert.ok(afterFailure.error.includes('无法连接知识服务')); assert.deepEqual(historyRequestIds, ['test-request', 'test-request-2']);
  assert.equal(afterRecovery.state, 'ready'); assert.equal(afterRecovery.error, afterFailure.error); assert.equal(afterRecovery.retryHidden, false); assert.equal(afterRecovery.status, 'error'); assert.equal(afterRecovery.chats, 1);
});
await check('UI trims whole turns to twelve and rejects overlong input (DOM double)', async () => {
  let calls = 0; globalThis.fetch = async () => { calls += 1; return reply({ ...answer, requestId: `history-${calls}` }); };
  for (let index = 0; index < 11; index += 1) { byId('question').value = `离线历史题${index}`; byId('question-form').fire('submit'); await flush(); }
  assert.equal(turns().length, 12);
  assert.equal(descendants(byId('messages')).filter((element) => element.dataset.messageRole === 'assistant').length, 12);
  byId('question').value = '字'.repeat(601); byId('question-form').fire('submit'); await flush();
  assert.equal(calls, 11); assert.equal(byId('question').attributes['aria-invalid'], 'true');
});
await check('HTML bindings, safe rendering and complete import version chain (static)', async () => {
  const html = await readFile(new URL('about.html', root), 'utf8');
  const main = await readFile(new URL('js/ai-workshop/main.js', root), 'utf8');
  const services = await readFile(new URL('js/ai-workshop/services.js', root), 'utf8');
  const css = await readFile(new URL('css/ai-workshop.css', root), 'utf8');
  const requiredIds = [...main.matchAll(/required\('#([^']+)'\)/g)].map((match) => match[1]);
  for (const id of requiredIds) assert.ok(html.includes(`id="${id}"`), `missing HTML binding: ${id}`);
  for (const code of [main, services]) assert.equal(/(?:innerHTML|outerHTML)\s*=|insertAdjacentHTML|eval\s*\(/.test(code), false);
  assert.ok(main.includes("from './services.js?v=phase3-1'")); assert.ok(main.includes("from './contracts.js?v=phase3-1'"));
  assert.ok(services.includes("from './contracts.js?v=phase3-1'")); assert.ok(html.includes('main.js?v=phase3-1')); assert.ok(html.includes('ai-workshop.css?v=phase3-1'));
  assert.ok(css.includes('.ai-workshop-citation')); assert.ok(css.includes('prefers-reduced-motion'));
});

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
