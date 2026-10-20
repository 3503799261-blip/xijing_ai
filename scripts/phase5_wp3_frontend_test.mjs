/** Offline DOM/Fetch doubles only; not a live API, GLB, or device acceptance test. */
import assert from 'node:assert/strict';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { dirname } from 'node:path';
const repo = new URL('../', import.meta.url);
const status = await import(new URL('js/ai-workshop/demo-status.js?v=phase5-wp3-1', repo));
const guide = await import(new URL('js/ai-workshop/demo-guide.js?v=phase5-wp3-1', repo));
const results = [];
async function check(name, action) { try { await action(); results.push({ name, passed: true }); } catch (error) { results.push({ name, passed: false, error: error.message }); } }
const saved = Object.fromEntries(['document', 'location', 'fetch', 'window', 'localStorage', 'sessionStorage'].map((name) => [name, globalThis[name]]));
const identities = status.DEMO_IDENTITIES;
const health = { status: 'ready', knowledge: true, embedding: true, llmConfigured: true, llmVerified: true, documents: 12, chunks: 35, agents: { supervisorReady: true, activeTaskId: null } };
const history = { items: [{ taskId: identities.taskId, sourceType: 'persisted_history' }], page: 1, pageSize: 1, total: 22, source: { kind: 'persisted_history', readOnly: true } };
const model = { modelId: identities.realisticModelId, assetId: identities.assetId, origin: 'neural4d', format: 'glb', hash: 'a'.repeat(64), size: 15158668 };
const quota = { max_calls: 3, used_calls: 2, remaining_calls: 1, history_verified: true, realEnabled: false };
const copy = (value) => structuredClone(value);
const bodyFor = (url) => url.includes('/health') ? copy(health) : url.includes('/agent/history') ? copy(history) : url.includes('/assets/models/') ? copy(model) : copy(quota);
const response = (value, code = 200) => ({ ok: code >= 200 && code < 300, status: code, json: async () => value });
class Element {
  constructor(tag = 'div', id = '') { this.tagName = tag.toUpperCase(); this.id = id; this.attributes = {}; this.children = []; this.dataset = {}; this.events = new Map(); this.value = ''; this.type = tag === 'button' ? 'submit' : ''; this.disabled = false; this.hidden = false; this._text = ''; this.parent = null; }
  set innerHTML(_value) { throw new Error('Unsafe HTML'); }
  get innerHTML() { throw new Error('Unsafe HTML'); }
  get textContent() { return this._text + this.children.map((item) => item.textContent).join(''); }
  set textContent(value) { this._text = String(value); this.children = []; }
  append(...children) { children.forEach((child) => { child.parent = this; this.children.push(child); }); }
  replaceChildren(...children) { this.children = []; this._text = ''; this.append(...children); }
  setAttribute(key, value) { this.attributes[key] = String(value); }
  getAttribute(key) { return this.attributes[key] ?? null; }
  removeAttribute(key) { delete this.attributes[key]; }
  addEventListener(name, action, options = false) { this.events.set(name, [...this.events.get(name) || [], { action, capture: options === true || options?.capture === true }]); }
  fire(name, overrides = {}) { const event = { type: name, target: this, prevented: false, stopped: false, preventDefault() { this.prevented = true; }, stopImmediatePropagation() { this.stopped = true; }, ...overrides }; for (const item of this.events.get(name) || []) { item.action(event); if (event.stopped) break; } return event; }
  closest(selector) { if (selector === 'form') return this.tagName === 'FORM' ? this : this.parent?.closest(selector) || null; if (selector.startsWith('button,')) return this.tagName === 'BUTTON' || (this.tagName === 'INPUT' && ['submit', 'image'].includes(this.type)) || this.attributes.role === 'button' ? this : this.parent?.closest(selector) || null; return null; }
  focus() { this.focused = true; }
  scrollIntoView() { this.scrolled = true; }
  querySelector(selector) { return this.bindings?.get(selector) || null; }
}
const descendants = (element) => [element, ...element.children.flatMap(descendants)];
const names = ['demo', 'demo-start', 'demo-backup', 'demo-exit', 'demo-prev', 'demo-next', 'demo-skip', 'demo-content', 'demo-steps', 'demo-title', 'demo-description', 'demo-source', 'demo-links', 'demo-feedback', 'demo-check', 'demo-conditions', 'demo-check-time', 'history', 'history-task-id', 'history-state', 'history-type', 'asset-form', 'question', 'brief', 'asset-source-task', 'enterprise-audience', 'overview', 'qa', 'agents', 'model'];
function fixture(services = { checkDemoConditions: async () => ({ checkedAt: 'offline-test', checks: [], paidCalls: 0 }) }) {
  const elements = new Map(names.map((name) => [`#ai-workshop-${name}`, new Element(name.endsWith('-form') ? 'form' : name.startsWith('demo-') && ['start', 'backup', 'exit', 'prev', 'next', 'skip', 'check'].some((suffix) => name.endsWith(suffix)) ? 'button' : 'div', `ai-workshop-${name}`)]));
  const root = new Element(); root.bindings = elements;
  const panels = [];
  const controller = guide.initializeDemoGuide({ root, selectPanel: (panel) => panels.push(panel), services });
  return { root, controller, panels, get: (name) => elements.get(`#ai-workshop-${name}`) };
}
const flush = async () => { for (let tick = 0; tick < 8; tick += 1) await Promise.resolve(); };
try {
  globalThis.location = { origin: 'http://127.0.0.1:8000', hostname: '127.0.0.1' };
  globalThis.document = { createElement: (tag) => new Element(tag), querySelector: () => null };
  globalThis.localStorage = new Proxy({}, { get() { throw new Error('No persistent demo state'); } });
  globalThis.sessionStorage = new Proxy({}, { get() { throw new Error('No persistent demo state'); } });
  await check('status module import and guide initialization make no automatic API calls', () => {
    let count = 0; globalThis.fetch = async () => { count += 1; throw new Error('not expected'); };
    const value = fixture(); assert.equal(count, 0); assert.equal(value.controller.diagnostics().active, false); assert.equal(value.panels.length, 0); assert.ok(value.get('demo-check-time').textContent.includes('未执行'));
  });
  await check('explicit condition check makes exactly four same-origin GET requests with no payload', async () => {
    const calls = []; const report = await status.checkDemoConditions({ fetchImpl: async (url, options) => { calls.push({ url, options }); return response(bodyFor(url)); } });
    assert.equal(calls.length, 4); assert.equal(report.checks.length, 4); assert.equal(report.paidCalls, 0);
    for (const call of calls) { assert.equal(new URL(call.url).origin, globalThis.location.origin); assert.equal(call.options.method, 'GET'); assert.equal(call.options.body, undefined); assert.equal(call.options.cache, 'no-store'); assert.equal(call.options.redirect, 'error'); }
    assert.ok(report.checks.every((item) => item.state === 'ready'));
  });
  await check('health and model metadata do not imply current DeepSeek connectivity or GLB rendering success', async () => {
    const report = await status.checkDemoConditions({ fetchImpl: async (url) => response(bodyFor(url)) });
    assert.ok(report.checks.find((item) => item.key === 'backend').message.includes('不代表今日DeepSeek'));
    assert.ok(report.checks.find((item) => item.key === 'model').message.includes('未下载或检查GLB渲染'));
  });
  await check('active task status is reported without claiming backup stops the task', async () => {
    const report = await status.checkDemoConditions({ fetchImpl: async (url) => response(url.includes('/health') ? { ...copy(health), agents: { ...health.agents, activeTaskId: identities.taskId } } : bodyFor(url)) });
    assert.ok(report.checks[0].message.includes('后台记录存在活动任务')); assert.ok(report.checks[0].message.includes('不会停止'));
  });
  await check('missing local knowledge and empty real history remain honest warning states', async () => {
    const report = await status.checkDemoConditions({ fetchImpl: async (url) => response(url.includes('/health') ? { ...copy(health), knowledge: false, embedding: false } : url.includes('/agent/history') ? { ...copy(history), items: [], total: 0 } : bodyFor(url)) });
    assert.equal(report.checks[0].state, 'warning'); assert.equal(report.checks[1].state, 'warning'); assert.ok(report.checks[1].message.includes('不使用测试夹具'));
  });
  for (const code of [401, 403, 404, 429, 503]) await check(`HTTP ${code} is isolated, fixed Chinese feedback without reflecting sensitive response details`, async () => {
    const report = await status.checkDemoConditions({ fetchImpl: async (url) => response(url.includes('/agent/history') ? { error: { message: 'PRIVATE_SENTINEL' } } : bodyFor(url), url.includes('/agent/history') ? code : 200) });
    assert.equal(report.checks[1].state, 'error'); assert.ok(!report.checks[1].message.includes('PRIVATE_SENTINEL')); assert.equal(report.checks.filter((item) => item.state === 'ready').length, 3);
  });
  await check('malformed JSON is isolated from the other three successful local checks', async () => {
    const report = await status.checkDemoConditions({ fetchImpl: async (url) => url.includes('/assets/models/') ? { ok: true, json: async () => { throw new SyntaxError('private parser trace'); } } : response(bodyFor(url)) });
    assert.equal(report.checks[2].state, 'error'); assert.ok(report.checks[2].message.includes('格式异常')); assert.ok(report.checks[0].state === 'ready');
  });
  await check('wrong saved model identity, fixture origin or non-GLB format cannot be reported as main real asset', async () => {
    for (const changes of [{ modelId: identities.internalModelId }, { origin: 'local_test_fixture' }, { format: 'png' }]) {
      const report = await status.checkDemoConditions({ fetchImpl: async (url) => response(url.includes('/assets/models/') ? { ...copy(model), ...changes } : bodyFor(url)) }); assert.equal(report.checks[2].state, 'error');
    }
  });
  await check('quota is read only and unverified counts are not silently inferred from known project baseline', async () => {
    const report = await status.checkDemoConditions({ fetchImpl: async (url) => response(url.includes('/assets/usage') ? { ...copy(quota), history_verified: false, used_calls: null, remaining_calls: null } : bodyFor(url)) });
    assert.equal(report.checks[3].state, 'warning'); assert.ok(report.checks[3].message.includes('不推断使用次数')); assert.ok(!report.checks[3].message.includes('已用2/3'));
  });
  await check('unexpected open creation or quota differences warn without changing backend records', async () => {
    const report = await status.checkDemoConditions({ fetchImpl: async (url) => response(url.includes('/assets/usage') ? { ...copy(quota), realEnabled: true } : bodyFor(url)) });
    assert.equal(report.checks[3].state, 'warning'); assert.ok(report.checks[3].message.includes('不得继续创建'));
  });
  await check('network failure and local timeout return four bounded errors without automatic retry', async () => {
    let calls = 0; let report = await status.checkDemoConditions({ fetchImpl: async () => { calls += 1; throw new Error('PRIVATE_SENTINEL'); } });
    assert.equal(calls, 4); assert.ok(report.checks.every((item) => item.state === 'error' && !item.message.includes('PRIVATE_SENTINEL')));
    calls = 0; report = await status.checkDemoConditions({ timeoutMs: 1, fetchImpl: async (_url, options) => { calls += 1; return new Promise((_resolve, reject) => options.signal.addEventListener('abort', () => reject(new Error('abort')), { once: true })); } });
    assert.equal(calls, 4); assert.ok(report.checks.every((item) => item.message.includes('超时')));
  });
  await check('manual condition reread recovers after a prior API failure', async () => {
    const failed = await status.checkDemoConditions({ fetchImpl: async () => { throw new Error('offline'); } }); assert.ok(failed.checks.every((item) => item.state === 'error'));
    const recovered = await status.checkDemoConditions({ fetchImpl: async (url) => response(bodyFor(url)) }); assert.ok(recovered.checks.every((item) => item.state === 'ready'));
  });
  await check('cross-origin diagnostic API configuration is refused without a request', async () => {
    const before = globalThis.document.querySelector; globalThis.document.querySelector = () => ({ content: 'https://external.example/api/v1' });
    let count = 0; const report = await status.checkDemoConditions({ fetchImpl: async () => { count += 1; } }); globalThis.document.querySelector = before;
    assert.equal(count, 0); assert.ok(report.checks.every((item) => item.state === 'error'));
  });
  await check('six guide steps are keyboard-native buttons, start navigates and next/previous/skip stay local', () => {
    const value = fixture(); assert.equal(value.get('demo-steps').children.length, 6); value.get('demo-start').fire('click');
    assert.equal(value.controller.diagnostics().step, 0); assert.equal(value.panels.at(-1), 'overview'); assert.equal(value.get('demo-prev').disabled, true);
    value.get('demo-next').fire('click'); assert.equal(value.panels.at(-1), 'qa'); value.get('demo-prev').fire('click'); assert.equal(value.controller.diagnostics().step, 0);
    value.get('demo-skip').fire('click'); assert.equal(value.controller.diagnostics().step, 5); assert.equal(value.get('demo-next').disabled, true);
  });
  await check('guide navigation does not fill question, brief, source task or enterprise input values', () => {
    const value = fixture(); for (const name of ['question', 'brief', 'asset-source-task', 'enterprise-audience', 'history-task-id']) value.get(name).value = `saved-${name}`;
    for (let index = 0; index < 6; index += 1) value.controller.setStep(index);
    for (const name of ['question', 'brief', 'asset-source-task', 'enterprise-audience', 'history-task-id']) assert.equal(value.get(name).value, `saved-${name}`);
  });
  await check('step changes keep the guide readable until the user explicitly enters a target section', () => {
    const value = fixture(); value.controller.start(); value.controller.setStep(2);
    assert.equal(value.get('history').scrolled, undefined);
    const target = descendants(value.get('demo-links')).find(item => item.tagName === 'BUTTON' && item.textContent.startsWith('前往这一步'));
    target.fire('click'); assert.equal(value.get('history').scrolled, true);
  });
  await check('history step only navigates until explicit fill action, then leaves WP2 manual query to the user', () => {
    const value = fixture(); value.get('history-task-id').value = 'prior-id'; value.get('history-state').value = 'failed'; value.get('history-type').value = 'character_creation';
    value.controller.setStep(2); assert.equal(value.get('history-task-id').value, 'prior-id');
    const fill = descendants(value.get('demo-links')).find((item) => item.tagName === 'BUTTON' && item.textContent.startsWith('填入绛绣')); fill.fire('click');
    assert.equal(value.get('history-task-id').value, identities.taskId); assert.equal(value.get('history-state').value, ''); assert.equal(value.get('history-type').value, ''); assert.ok(value.get('demo-feedback').textContent.includes('未发送查询'));
  });
  await check('both existing model links preserve exact identities and document new-page backup boundary', () => {
    const value = fixture(); value.controller.setStep(4); const links = descendants(value.get('demo-links')).filter((item) => item.tagName === 'A');
    assert.equal(links.length, 2); assert.ok(links[0].href.includes(identities.assetId)); assert.ok(links[1].href.includes(identities.internalModelId));
    assert.ok(links.every((link) => link.target === '_blank' && link.rel.includes('noopener'))); assert.ok(value.get('demo-links').textContent.includes('不继承'));
    assert.ok(value.get('demo-source').textContent.includes('非公开')); assert.ok(value.get('demo-description').textContent.includes('不属于同一角色'));
  });
  await check('non-loopback hostname never offers the internal Q model access link', () => {
    globalThis.location.hostname = '192.0.2.2'; const value = fixture(); value.controller.setStep(4);
    assert.equal(descendants(value.get('demo-links')).filter((item) => item.tagName === 'A').length, 1); assert.ok(value.get('demo-links').textContent.includes('仅允许本机回环')); globalThis.location.hostname = '127.0.0.1';
  });
  await check('enterprise guide locates existing form without changing business fields or claiming a commercial case', () => {
    const value = fixture(); value.get('enterprise-audience').value = 'original'; value.controller.setStep(5);
    descendants(value.get('demo-links')).find((item) => item.tagName === 'BUTTON').fire('click');
    assert.equal(value.get('enterprise-audience').value, 'original'); assert.equal(value.get('asset-form').scrolled, true); assert.ok(value.get('demo-description').textContent.includes('没有真实企业商用交付案例'));
  });
  await check('backup is explicit local state with no disabled overwrite or server configuration changes', () => {
    const value = fixture(); value.get('demo-start').disabled = false; value.controller.enterBackup(); assert.equal(value.controller.diagnostics().backup, true);
    assert.equal(value.controller.diagnostics().serverConfigurationChanged, false); assert.equal(value.get('demo').dataset.mode, 'backup'); assert.equal(value.get('demo-start').disabled, false);
    assert.ok(value.get('demo-feedback').textContent.includes('不会停止'));
  });
  await check('backup capture blocks known paid and persistence button IDs, including nested label click', () => {
    const value = fixture(); value.controller.enterBackup();
    for (const id of ['send', 'retry-question', 'agent-start', 'agent-submit-retry', 'agent-confirm', 'agent-cancel', 'visual-accept', 'image-accept', 'model-submit', 'prompt-edit-save']) {
      const button = new Element('button', `ai-workshop-${id}`); button.type = 'button'; button.disabled = false; const child = new Element('span'); button.append(child);
      const event = value.root.fire('click', { target: child }); assert.equal(event.prevented, true, id); assert.equal(event.stopped, true, id); assert.equal(button.disabled, false);
    }
  });
  await check('backup blocks form submit and submit buttons except the read-only history query', () => {
    const value = fixture(); value.controller.enterBackup();
    for (const name of ['question', 'creation', 'asset', 'asset-image', 'model-import', 'prompt-edit']) {
      const form = new Element('form', `ai-workshop-${name}-form`); const event = value.root.fire('submit', { target: form }); assert.equal(event.prevented, true);
      const button = new Element('button'); button.type = 'submit'; form.append(button); assert.equal(value.root.fire('click', { target: button }).prevented, true);
    }
    assert.equal(value.root.fire('submit', { target: new Element('form', 'ai-workshop-history-form') }).prevented, false);
  });
  await check('backup permits read-only history refresh, model reload, camera controls and condition checks', () => {
    const value = fixture(); value.controller.enterBackup();
    for (const name of ['history-load', 'history-detail-refresh', 'history-next', 'viewer-reload', 'viewer-zoom-in', 'viewer-zoom-out', 'viewer-reset', 'viewer-touch', 'asset-refresh', 'demo-check']) {
      const button = new Element('button', `ai-workshop-${name}`); button.type = 'button'; assert.equal(value.root.fire('click', { target: button }).prevented, false, name);
    }
  });
  await check('exit removes only local backup interception and preserves user inputs and original disabled flags', () => {
    const value = fixture(); const button = new Element('button', 'ai-workshop-agent-start'); button.type = 'button'; button.disabled = true;
    value.get('brief').value = 'saved-user-brief'; value.controller.enterBackup(); value.controller.exit();
    assert.equal(value.controller.diagnostics().active, false); assert.equal(value.controller.diagnostics().backup, false); assert.equal(value.get('demo-content').hidden, true);
    assert.equal(value.root.fire('click', { target: button }).prevented, false); assert.equal(button.disabled, true); assert.equal(value.get('brief').value, 'saved-user-brief');
  });
  await check('a refreshed new guide instance starts exited without persistent mode restoration', () => {
    const old = fixture(); old.controller.enterBackup(); const fresh = fixture(); assert.equal(fresh.controller.diagnostics().active, false); assert.equal(fresh.controller.diagnostics().backup, false); assert.ok(fresh.get('demo-check-time').textContent.includes('未执行'));
  });
  await check('guide condition check is manual, error can be retried manually and stale completion cannot overwrite exit', async () => {
    let calls = 0; const value = fixture({ checkDemoConditions: async () => { if (++calls === 1) throw new Error('PRIVATE_SENTINEL'); return { checkedAt: 'offline', checks: [{ key: 'backend', label: '测试', state: 'ready', message: '恢复成功' }] }; } });
    assert.equal(calls, 0); await value.controller.check(); assert.ok(value.get('demo-check-time').textContent.includes('失败')); await value.controller.check(); assert.ok(value.get('demo-conditions').textContent.includes('恢复成功')); assert.equal(calls, 2);
    let resolve; const pending = fixture({ checkDemoConditions: () => new Promise((done) => { resolve = done; }) }); const request = pending.controller.check(); pending.controller.exit(); resolve({ checkedAt: 'stale', checks: [] }); await request;
    assert.equal(pending.get('demo-check').attributes['aria-busy'], 'false'); assert.ok(!pending.get('demo-check-time').textContent.includes('stale'));
  });
  await check('all diagnostic text uses safe DOM nodes even for an injected test message', async () => {
    const value = fixture({ checkDemoConditions: async () => ({ checkedAt: '<svg onload=alert(1)>', checks: [{ key: 'backend', label: '<script>', state: 'error', message: '<img onerror=alert(1)>' }] }) });
    await value.controller.check(); assert.ok(value.get('demo-conditions').textContent.includes('<img onerror=alert(1)>')); assert.equal(descendants(value.get('demo-conditions')).some((item) => ['SCRIPT', 'IMG', 'SVG'].includes(item.tagName)), false);
  });
  await check('guide and status source do not mutate APIs, store modes, fake answers or install a global fetch override', async () => {
    const ui = await readFile(new URL('js/ai-workshop/demo-guide.js', repo), 'utf8'); const transport = await readFile(new URL('js/ai-workshop/demo-status.js', repo), 'utf8');
    assert.ok(!/innerHTML|insertAdjacentHTML|localStorage|sessionStorage|EventSource\s*\(|setInterval\s*\(/.test(ui + transport));
    assert.ok(!/method:\s*['"](?:POST|PUT|PATCH|DELETE)['"]|\.submit\s*\(|\.requestSubmit\s*\(|globalThis\.fetch\s*=|window\.fetch\s*=/.test(ui + transport));
    assert.ok(!/startAgentWorkflow|confirmAgentWorkflow|cancelAgentWorkflow|askOperaQuestion|createCharacterAsset|submitModelTask/.test(ui + transport));
  });
  await check('new styling is isolated, responsive, keyboard visible and respects reduced motion', async () => {
    const css = await readFile(new URL('css/ai-workshop-demo.css', repo), 'utf8');
    assert.ok(css.includes('.ai-workshop-demo')); assert.ok(css.includes('@media (max-width: 480px)')); assert.ok(css.includes(':focus-visible')); assert.ok(css.includes('prefers-reduced-motion'));
  });
} finally { for (const [key, value] of Object.entries(saved)) { if (value === undefined) delete globalThis[key]; else globalThis[key] = value; } }
const report = { scope: 'WP3 offline contract/DOM/Fetch doubles; no paid API, real device, or GLB validation', timestamp: new Date().toISOString(), passed: results.filter((item) => item.passed).length, failed: results.filter((item) => !item.passed).length, skipped: 0, checks: results };
const outputIndex = process.argv.indexOf('--output'); if (outputIndex >= 0) { const output = process.argv[outputIndex + 1]; await mkdir(dirname(output), { recursive: true }); await writeFile(output, JSON.stringify(report, null, 2) + '\n'); }
console.log(JSON.stringify(report, null, 2)); if (report.failed) process.exitCode = 1;
