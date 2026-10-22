// WP4 local-only browser verification; explicit response doubles are never stored.
import { createRequire } from 'node:module';
import fs from 'node:fs/promises';
import path from 'node:path';
const { chromium } = createRequire(process.env.XIJING_PLAYWRIGHT_PACKAGE)('playwright');
const output = process.argv[2]; if (!output) throw new Error('New evidence directory required');
await fs.mkdir(output, { recursive: false });
const base = 'http://127.0.0.1:8000';
const task = 'ca7007e7-e535-4b1f-a9b6-1932f10e20b4';
const asset = '9e2b42e1-bbad-4a2f-ab1b-aeda18015dee';
const model = '1fa0b519-caf4-4009-aec2-f20b0f9a3523';
const report = { startedAt: new Date().toISOString(), scope: 'WP4_LOCAL_BROWSER_WITH_EXPLICIT_ISOLATED_RESPONSE_DOUBLES', tests: [], contexts: [], paidApiCalls: 0, supplierRequests: 0, physicalMobile: 'NOT_TESTED' };
const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
const ensure = (ok, message) => { if (!ok) throw new Error(message); };
const clean = value => String(value).replace(/https?:\/\/[^\s"'<>]+/g, u => { try { const x = new URL(u); return x.origin + x.pathname; } catch { return '[URL]'; } }).slice(0, 500);
let browser;
async function save() { await fs.writeFile(path.join(output, 'browser-result.json'), JSON.stringify(report, null, 2)); }
async function check(name, kind, work) { try { report.tests.push({ name, kind, passed: true, ...await work() }); } catch (e) { report.tests.push({ name, kind, passed: false, error: clean(e.message) }); } await save(); }
async function context(name, mobile = false) {
  const c = await browser.newContext({ viewport: mobile ? { width: 390, height: 844 } : { width: 1920, height: 1080 }, isMobile: mobile, hasTouch: mobile, serviceWorkers: 'block' });
  const log = { name, requests: [], blockedWrites: [], blockedExternal: [], pageErrors: [], consoleErrors: [], httpErrors: [], failedResources: [], syntheticRequests: [] };
  report.contexts.push(log);
  await c.route('**/*', route => {
    const r = route.request(), u = new URL(r.url()); log.requests.push({ method: r.method(), path: u.pathname });
    if (!['GET', 'HEAD'].includes(r.method())) { log.blockedWrites.push({ method: r.method(), path: u.pathname }); return route.abort(); }
    if (['http:', 'https:'].includes(u.protocol) && u.origin !== base) { log.blockedExternal.push(u.origin); return route.abort(); }
    return route.continue();
  });
  const p = await c.newPage();
  p.on('pageerror', e => log.pageErrors.push(clean(e.message)));
  p.on('console', m => { if (m.type() === 'error') log.consoleErrors.push(clean(m.text())); });
  p.on('response', r => { if (r.status() >= 400) log.httpErrors.push({ path: new URL(r.url()).pathname, status: r.status() }); });
  p.on('requestfailed', r => log.failedResources.push({ path: new URL(r.url()).pathname, error: r.failure()?.errorText }));
  return { c, p, log };
}
const fulfill = (route, body, status = 200) => route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
async function open(p, hash = 'demo') {
  await p.goto(`${base}/about.html#ai-workshop-${hash}`);
  await p.waitForFunction(() => document.querySelector('#ai-workshop-demo')?.dataset.mode === 'idle');
}
async function step(p, index) { await p.locator('#ai-workshop-demo-steps button').nth(index).click(); }
async function history(p) {
  await p.locator('#ai-workshop-history-task-id').fill(task);
  await p.locator('#ai-workshop-history-load').click();
  await p.locator(`[data-history-task-id="${task}"]`).waitFor();
}
async function ready(p) { await p.waitForFunction(() => document.querySelector('#ai-workshop-viewer-host')?.dataset.viewerState === 'ready', null, { timeout: 45000 }); }
async function snap(p) { return p.evaluate(() => { const h = document.querySelector('#ai-workshop-viewer-host'), v = h?.querySelector('model-viewer'), o = v?.getCameraOrbit?.(); return { state: h?.dataset.viewerState, modelId: window.xijingAssetViewerDiagnostics?.().modelId, degrees: Number(h?.dataset.observedDegrees || 0), orbit: o ? { theta: o.theta, phi: o.phi, radius: o.radius } : null }; }); }
try {
  browser = await chromium.launch({ executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: true, args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  report.chromeVersion = browser.version(); report.nodeVersion = process.version;
  await check('guide-six-steps-targets-exit-and-refresh', 'REAL_LOCAL', async () => {
    const { c, p, log } = await context('guide'); try {
      await open(p); await p.locator('nav.ai-workshop-nav [data-ai-workshop-target="qa"]').click(); await p.locator('#ai-workshop-question').fill('保留的用户问题，不发送'); await p.locator('nav.ai-workshop-nav [data-ai-workshop-target="create"]').click(); await p.locator('#ai-workshop-brief').fill('保留的用户角色需求，不提交'); await p.locator('a[href="#ai-workshop-demo"]').first().click();
      await p.locator('#ai-workshop-demo-start').click();
      ensure(await p.locator('#ai-workshop-demo-steps button').count() === 6, 'Six guide steps missing');
      const titles = [];
      for (let i = 0; i < 6; i++) { await step(p, i); titles.push(await p.locator('#ai-workshop-demo-title').innerText()); }
      ensure((await p.locator('#ai-workshop-question').inputValue()).includes('保留') && (await p.locator('#ai-workshop-brief').inputValue()).includes('保留'), 'Guide changed user input');
      await p.locator('#ai-workshop-demo-prev').click(); ensure((await p.locator('#ai-workshop-demo-title').innerText()).startsWith('5 /'), 'Previous step failed');
      const links = await p.locator('#ai-workshop-demo-links a').evaluateAll(es => es.map(e => ({ href: e.getAttribute('href'), target: e.target })));
      ensure(links.some(l => l.href.includes(asset)) && links.some(l => l.href.includes('3777a880')), 'Model links lost identities');
      await p.screenshot({ path: path.join(output, 'guide-desktop.png') });
      await p.locator('#ai-workshop-demo-skip').click(); ensure((await p.locator('#ai-workshop-demo-title').innerText()).startsWith('6 /'), 'Skip failed');
      await p.locator('#ai-workshop-demo-exit').click(); ensure(await p.locator('#ai-workshop-demo-content').isHidden(), 'Exit failed');
      await p.locator('#ai-workshop-demo-backup').click(); await p.reload();
      await p.waitForFunction(() => document.querySelector('#ai-workshop-demo')?.dataset.mode === 'idle');
      ensure(log.blockedWrites.length === 0, 'Guide attempted business write'); return { titles, modelLinks: links, refreshExited: true, inputsPreserved: true };
    } finally { await c.close(); }
  });
  await check('backup-guards-real-controls-and-manual-local-check', 'REAL_LOCAL', async () => {
    const { c, p, log } = await context('backup'); try {
      await open(p); await p.locator('#ai-workshop-demo-backup').click();
      const guarded = await p.evaluate(() => {
        const controls = ['send', 'retry-question', 'agent-start', 'agent-submit-retry', 'agent-confirm', 'agent-cancel', 'visual-accept', 'image-accept', 'model-submit'];
        return controls.map(name => { const button = document.querySelector('#ai-workshop-' + name); if (!button) return { name, exists: false }; const event = new MouseEvent('click', { bubbles: true, cancelable: true }); button.dispatchEvent(event); return { name, exists: true, prevented: event.defaultPrevented }; });
      });
      ensure(guarded.every(g => g.exists && g.prevented), 'Backup control guard incomplete');
      await p.locator('#ai-workshop-demo details').evaluate(e => e.open = true);
      await p.locator('#ai-workshop-demo-check').click();
      await p.waitForFunction(() => !document.querySelector('#ai-workshop-demo-check').disabled);
      const conditions = await p.locator('#ai-workshop-demo-conditions').innerText();
      ensure(conditions.includes('不代表') && conditions.includes('创建关闭') && conditions.includes('22'), 'Local diagnostic scope incorrect');
      await step(p, 3); await p.getByRole('button', { name: '填入绛绣历史ID（不自动读取）', exact: true }).click();
      ensure(await p.locator('#ai-workshop-history-task-id').inputValue() === task, 'History ID fill failed');
      ensure(!log.requests.some(r => r.path.startsWith('/api/v1/agent/history/')), 'Guide auto-read detail');
      await history(p); await p.locator(`[data-history-task-id="${task}"]`).click();
      await p.waitForFunction(() => document.querySelector('#ai-workshop-history-detail-content').textContent.includes('绛绣'));
      ensure((await p.locator('#ai-workshop-history-detail-content').textContent()).includes('文化审校'), 'Saved review missing');
      ensure(log.blockedWrites.length === 0, 'Backup reached write transport');
      await p.screenshot({ path: path.join(output, 'backup-history.png') }); return { guarded, conditions, realHistoryReadable: true };
    } finally { await c.close(); }
  });
  await check('mobile-guide-and-enterprise-layout', 'REAL_LOCAL_MOBILE_EMULATION', async () => {
    const { c, p } = await context('mobile-guide', true); try {
      await open(p); await p.locator('#ai-workshop-demo-start').click();
      ensure(!await p.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1), 'Mobile guide overflow');
      await p.screenshot({ path: path.join(output, 'guide-mobile.png') });
      await step(p, 5); await p.getByRole('button', { name: '定位企业需求入口（不带入、不提交）', exact: true }).click();
      await p.locator('#ai-workshop-asset-mode').selectOption('enterprise');
      ensure(await p.locator('#ai-workshop-enterprise-fields').isVisible(), 'Enterprise entry unavailable');
      ensure((await p.locator('#ai-workshop-enterprise-fields').innerText()).includes('没有真实企业客户'), 'Enterprise boundary missing');
      ensure(!await p.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1), 'Enterprise mobile overflow');
      return { viewport: { width: 390, height: 844 }, physicalDevice: false, enterpriseNotSubmitted: true };
    } finally { await c.close(); }
  });
  await check('diagnostics-degraded-and-recovered', 'SYNTHETIC_HTTP_FAULT_WITH_REAL_GET_RECOVERY', async () => {
    const { c, p } = await context('condition-fault'); try {
      let fail = true;
      await p.route('**/api/v1/health', route => fail ? fulfill(route, { error: { code: 'TEST_LOCAL_UNAVAILABLE', message: 'PRIVATE_SENTINEL' } }, 503) : route.continue());
      await open(p); await p.locator('#ai-workshop-demo details').evaluate(e => e.open = true);
      await p.locator('#ai-workshop-demo-check').click(); await p.waitForFunction(() => !document.querySelector('#ai-workshop-demo-check').disabled);
      const error = await p.locator('[data-demo-condition="backend"]').innerText();
      ensure(error.includes('尚未就绪') && !error.includes('PRIVATE_SENTINEL'), 'Diagnostic error leaked or unclear');
      fail = false; await p.locator('#ai-workshop-demo-check').click(); await p.waitForFunction(() => !document.querySelector('#ai-workshop-demo-check').disabled);
      ensure((await p.locator('[data-demo-condition="backend"]').innerText()).includes('资料12份'), 'Manual diagnostic recovery failed');
      return { fault: 'HTTP503 response double only', error, manualRecovery: true };
    } finally { await c.close(); }
  });
  await check('chat-response-faults-preserve-input-and-never-auto-repeat', 'SYNTHETIC_POST_RESPONSES_ONLY_NO_SERVER_POST', async () => {
    const cases = [];
    for (const mode of ['success', 'timeout504', 'network', 'authentication401', 'limited429', 'unavailable503', 'malformed']) {
      const { c, p, log } = await context('chat-double-' + mode); try {
        await p.route('**/api/v1/capabilities', route => fulfill(route, { questionAnswering: true, knowledgeSearch: true, agentWorkflow: true, conceptImage: false, imageToModel: false, assetManagement: true, modelViewer: true }));
        let count = 0;
        await p.route('**/api/v1/chat', route => {
          count++; log.syntheticRequests.push({ method: route.request().method(), path: '/api/v1/chat', mode });
          if (mode === 'network') return route.abort('internetdisconnected');
          if (mode === 'malformed') return fulfill(route, { invalid: true });
          if (mode === 'success') return fulfill(route, { answer: '【浏览器测试替身，非真实AI回答】仅验证显示。', citations: [{ id: 'browser-fixture', title: '明确测试资料', sourceId: 'test-source', locator: '测试位置', url: 'https://example.invalid/test', excerpt: '测试片段，不是京剧事实。', contentKind: 'original_fact_summary' }], uncertain: false, requestId: 'browser-fixture-request' });
          const code = mode === 'timeout504' ? 504 : mode === 'authentication401' ? 401 : mode === 'limited429' ? 429 : 503;
          return fulfill(route, { error: { code: mode === 'timeout504' ? 'LLM_TIMEOUT' : mode === 'authentication401' ? 'LLM_AUTHENTICATION_FAILED' : mode === 'limited429' ? 'LLM_RATE_LIMITED' : 'LLM_UNAVAILABLE', message: '浏览器测试替身：' + mode + '；请手动重试。', retryable: true }, requestId: 'browser-fixture-error' }, code);
        });
        await open(p, 'qa'); await p.waitForFunction(() => !document.querySelector('#ai-workshop-send').disabled);
        const question = '浏览器故障测试输入，禁止发送到真实服务'; await p.locator('#ai-workshop-question').fill(question); await p.locator('#ai-workshop-send').click();
        await p.waitForFunction(() => document.querySelector('#ai-workshop-qa-loading').hidden); await wait(250);
        ensure(count === 1, 'Chat automatically repeated after ' + mode);
        if (mode === 'success') ensure((await p.locator('#ai-workshop-messages').innerText()).includes('非真实AI回答'), 'Synthetic answer display missing');
        else ensure(await p.locator('#ai-workshop-question').inputValue() === question && await p.locator('#ai-workshop-qa-service-error').isVisible(), 'Failure lost input or stayed loading');
        ensure(log.blockedWrites.length === 0, 'Synthetic POST escaped interception');
        cases.push({ mode, syntheticPostCount: count, failedInputPreserved: mode === 'success' ? null : true, realServerPosts: 0 });
      } finally { await c.close(); }
    }
    return { cases, externalApiEvidence: false };
  });
  await check('history-empty-and-detail404-manual-recovery', 'SYNTHETIC_GET_FAULT_WITH_REAL_HISTORY_RECOVERY', async () => {
    const { c, p } = await context('history-fault'); try {
      await open(p, 'history'); let empty = true, missing = true;
      await p.route('**/api/v1/agent/history?*', route => empty ? fulfill(route, { items: [], page: 1, pageSize: 10, total: 0, totalPages: 0, availableStates: [], availableTaskTypes: [], source: { kind: 'persisted_history', readOnly: true, note: '浏览器空列表测试替身，不是真实生产任务。' }, requestId: 'test-empty' }) : route.continue());
      await p.locator('#ai-workshop-history-load').click(); await p.waitForFunction(() => !document.querySelector('#ai-workshop-history-load').disabled);
      ensure((await p.locator('#ai-workshop-history-status').innerText()).includes('没有符合'), 'Empty history not honest');
      empty = false; await history(p);
      await p.route('**/api/v1/agent/history/' + task + '?*', route => missing ? fulfill(route, { error: { code: 'AGENT_TASK_NOT_FOUND', message: 'test' }, requestId: 'test-missing' }, 404) : route.continue());
      await p.locator(`[data-history-task-id="${task}"]`).click(); await p.locator('#ai-workshop-history-detail-refresh').waitFor();
      ensure((await p.locator('#ai-workshop-history-detail-status').innerText()).includes('不存在'), 'Detail404 not shown');
      missing = false; await p.locator('#ai-workshop-history-detail-refresh').click();
      await p.waitForFunction(() => document.querySelector('#ai-workshop-history-detail-content').textContent.includes('绛绣'));
      return { emptyAnd404Explicit: true, savedResultRecoveredWithoutExecution: true };
    } finally { await c.close(); }
  });
  await check('asset-metadata-failure-reloads-original-id-only', 'SYNTHETIC_GET_FAULT_WITH_REAL_ASSET_RECOVERY', async () => {
    const { c, p, log } = await context('asset-fault'); try {
      let fail = true, count = 0;
      await p.route('**/api/v1/assets/characters/' + asset, route => { count++; return fail ? fulfill(route, { error: { code: 'ASSET_NOT_FOUND', message: '浏览器测试：私有资产暂缺', retryable: true }, requestId: 'fixture' }, 404) : route.continue(); });
      await p.goto(`${base}/about.html?assetId=${asset}#ai-workshop-model`);
      await p.waitForFunction(() => document.querySelector('#ai-workshop-asset-summary')?.dataset.metadataState === 'unavailable');
      ensure(count === 1 && (await p.locator('#ai-workshop-asset-feedback').innerText()).includes('原资产ID'), 'Initial failure auto-retried or no advice');
      fail = false; await p.locator('#ai-workshop-asset-refresh').click(); await ready(p);
      ensure(count === 2, 'Explicit refresh did not read exact old asset');
      fail = true; await p.locator('#ai-workshop-asset-refresh').click();
      await p.waitForFunction(() => document.querySelector('#ai-workshop-asset-summary').dataset.metadataState === 'stale');
      ensure((await snap(p)).state === 'ready' && (await p.locator('#ai-workshop-asset-feedback').innerText()).includes('快照'), 'Existing Viewer lost or stale mislabeled');
      ensure(log.blockedWrites.length === 0, 'Asset recovery attempted write');
      return { originalAssetId: asset, assetGetCalls: count, preservedReadyViewer: true };
    } finally { await c.close(); }
  });
  await check('real-glb-loading-error-and-explicit-reload', 'REAL_GLB_WITH_SYNTHETIC_FILE_HTTP_ERROR', async () => {
    const { c, p } = await context('glb-recovery'); try {
      let fail = true, fileCalls = 0;
      await p.route('**/api/v1/assets/models/' + model + '/file*', async route => { fileCalls++; if (fail) { await wait(500); return route.fulfill({ status: 503, body: 'Synthetic local file failure; no file altered.' }); } return route.continue(); });
      await p.goto(`${base}/about.html?assetId=${asset}#ai-workshop-model`);
      await p.waitForFunction(() => document.querySelector('#ai-workshop-viewer-host')?.dataset.viewerState === 'loading');
      await p.waitForFunction(() => document.querySelector('#ai-workshop-viewer-host')?.dataset.viewerState === 'error', null, { timeout: 20000 });
      ensure(await p.locator('#ai-workshop-viewer-reload').isVisible(), 'No manual original-file reload');
      await p.locator('#ai-workshop-viewer-host').scrollIntoViewIfNeeded(); await p.screenshot({ path: path.join(output, 'viewer-error.png') });
      fail = false; await p.locator('#ai-workshop-viewer-reload').click(); await ready(p);
      ensure((await snap(p)).modelId === model, 'Reload changed model identity');
      await p.screenshot({ path: path.join(output, 'viewer-recovered.png') }); return { loadingObserved: true, errorObserved: true, manualReadyRecovered: true, fileRequests: fileCalls, modelId: model };
    } finally { await c.close(); }
  });
} catch (e) { report.fatal = clean(e.message); }
finally {
  if (browser) await browser.close(); report.finishedAt = new Date().toISOString();
  report.passed = report.tests.filter(t => t.passed).length; report.failed = report.tests.filter(t => !t.passed).length; report.skipped = 0;
  report.blockedWrites = report.contexts.reduce((n, c) => n + c.blockedWrites.length, 0); report.blockedExternal = report.contexts.reduce((n, c) => n + c.blockedExternal.length, 0);
  await save(); console.log(JSON.stringify({ passed: report.passed, failed: report.failed, blockedWrites: report.blockedWrites, blockedExternal: report.blockedExternal, fatal: report.fatal, output }));
}
if (report.failed || report.fatal || report.blockedWrites || report.blockedExternal) process.exitCode = 1;
