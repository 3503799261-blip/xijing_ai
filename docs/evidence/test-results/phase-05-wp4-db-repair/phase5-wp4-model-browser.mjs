// Phase 5 WP4: local GET/HEAD-only smoke, never creates tasks or calls providers.
import { createRequire } from 'node:module';
import fs from 'node:fs/promises';
import path from 'node:path';
const require = createRequire(process.env.XIJING_PLAYWRIGHT_PACKAGE);
const { chromium } = require('playwright');
const output = process.argv[2] || 'D:/京剧/.runtime/phase5-wp4-model-browser-01';
const base = 'http://127.0.0.1:8000';
const assetId = '9e2b42e1-bbad-4a2f-ab1b-aeda18015dee';
const second = { id: '1fa0b519-caf4-4009-aec2-f20b0f9a3523', hash: '5a021ac6338009615e6ea232c5b9001eef6f4cc91d9d87c3eeeb5307526bdfd5' };
const first = { id: '3777a880-fc8c-4766-aade-948d20c6b8f0', hash: 'bf9c808c15dbf5464ee67df1cdb3f64f9b2c6b3cd4ee41ecb8a6470a0554654a' };
const result = { startedAt: new Date().toISOString(), scope: 'WP4_NECESSARY_LOCAL_SMOKE', paidApiRequests: 0, supplierRequests: 0, mobile: 'NOT_TESTED_PHYSICAL_OR_EMULATED_IN_THIS_SMOKE', tests: {}, contexts: [], limitations: ['No paid RAG or Agent execution', 'No physical phone test', 'Not the full WP4 regression suite'] };
let browser;
const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
const clean = text => String(text).replace(/https?:\/\/[^\s"'<>]+/g, value => { try { const u = new URL(value); return `${u.origin}${u.pathname}`; } catch { return '[URL redacted]'; } }).slice(0, 800);
async function save() { await fs.writeFile(path.join(output, 'smoke-result.json'), JSON.stringify(result, null, 2)); }
async function newContext(name) {
  const context = await browser.newContext({ viewport: { width: 1920, height: 1080 }, serviceWorkers: 'block' });
  const log = { name, consoleErrors: [], pageErrors: [], failedResources: [], httpErrors: [], blockedMutations: [], blockedExternal: [], modelReads: [] };
  result.contexts.push(log);
  await context.addInitScript(() => { try { sessionStorage.clear(); localStorage.clear(); } catch {} });
  await context.route('**/*', async route => {
    const request = route.request();
    let url;
    try { url = new URL(request.url()); } catch { return route.abort('blockedbyclient'); }
    if (!['GET', 'HEAD'].includes(request.method())) { log.blockedMutations.push({ method: request.method(), path: url.pathname }); return route.abort('blockedbyclient'); }
    if (['http:', 'https:'].includes(url.protocol) && url.origin !== base) { log.blockedExternal.push({ origin: url.origin, path: url.pathname }); return route.abort('blockedbyclient'); }
    if (url.pathname.startsWith('/api/v1/assets/models/')) log.modelReads.push(url.pathname);
    return route.continue();
  });
  const page = await context.newPage();
  page.on('console', message => { if (message.type() === 'error') log.consoleErrors.push(clean(message.text())); });
  page.on('pageerror', error => log.pageErrors.push(clean(error.message)));
  page.on('requestfailed', request => { try { log.failedResources.push({ path: new URL(request.url()).pathname, error: request.failure()?.errorText }); } catch {} });
  page.on('response', response => { if (response.status() >= 400) log.httpErrors.push({ path: new URL(response.url()).pathname, status: response.status() }); });
  return { context, page, log };
}
async function viewerSnapshot(page) {
  return page.evaluate(() => {
    const host = document.querySelector('#ai-workshop-viewer-host');
    const viewer = host?.querySelector('model-viewer');
    const diagnostics = window.xijingAssetViewerDiagnostics?.();
    const radius = viewer?.getCameraOrbit?.();
    return { state: host?.dataset.viewerState, srcPath: viewer?.src ? new URL(viewer.src).pathname : null, modelId: diagnostics?.modelId || document.querySelector('#ai-workshop-internal-root')?.dataset.modelId || null,
      modelHash: diagnostics?.modelHash || document.querySelector('.ai-workshop-internal-hash')?.textContent?.match(/[a-f0-9]{64}/)?.[0] || null,
      orbit: radius ? { theta: radius.theta, phi: radius.phi, radius: radius.radius } : null, observedDegrees: Number(host?.dataset.observedDegrees || 0), userEventCount: Number(host?.dataset.userEventCount || 0),
      status: document.querySelector('#ai-workshop-viewer-status')?.textContent, renderElements: host?.querySelectorAll('model-viewer').length || 0 };
  });
}
async function ready(page) {
  await page.waitForFunction(() => document.querySelector('#ai-workshop-viewer-host')?.dataset.viewerState === 'ready', null, { timeout: 45000 });
  await page.locator('#ai-workshop-viewer-host').scrollIntoViewIfNeeded();
  await wait(650);
}
async function inspectInteraction(page, expected, name) {
  await ready(page);
  const initial = await viewerSnapshot(page);
  const box = await page.locator('#ai-workshop-viewer-host model-viewer').boundingBox();
  if (!box) throw new Error('No real Viewer bounding box');
  const y = box.y + box.height * 0.52, start = box.x + box.width * 0.82, end = box.x + box.width * 0.18;
  await page.mouse.move(start, y); await page.mouse.down();
  for (let i = 1; i <= 45; i++) { await page.mouse.move(start + (end - start) * i / 45, y); await wait(8); }
  await page.mouse.up(); await wait(700);
  const dragged = await viewerSnapshot(page);
  await page.locator('#ai-workshop-viewer-zoom-in').click(); await wait(700);
  const zoomed = await viewerSnapshot(page);
  await page.locator('#ai-workshop-viewer-reset').click(); await wait(550);
  const reset = await viewerSnapshot(page);
  const pass = initial.state === 'ready' && initial.modelId === expected.id && initial.modelHash === expected.hash && initial.srcPath === `/api/v1/assets/models/${expected.id}/file`
    && dragged.userEventCount > 0 && dragged.observedDegrees >= 260 && zoomed.orbit.radius < dragged.orbit.radius && Math.abs(reset.orbit.theta) < .02 && Math.abs(reset.orbit.radius - initial.orbit.radius) / initial.orbit.radius < .02;
  await page.screenshot({ path: path.join(output, `${name}-ready.png`), fullPage: false });
  return { pass, initial, dragged, zoomed, reset, scope: 'Real GLB Ready, single mouse drag, zoom-in, reset; no fault injection or mobile tests in WP4' };
}
async function eightPages() {
  const { context, page } = await newContext('eight-page-smoke');
  const pages = [];
  try {
    for (const file of ['index.html', 'history.html', 'roles.html', 'facial.html', 'music.html', 'gallery.html', 'video.html', 'about.html']) {
      const response = await page.goto(`${base}/${file}`, { waitUntil: 'domcontentloaded', timeout: 30000 });
      await page.waitForFunction(() => [...document.images].every(i => i.complete), null, { timeout: 15000 });
      const observed = await page.evaluate(() => ({ title: document.title,
        brokenImages: [...document.images].filter(i => (i.currentSrc || i.src) && i.naturalWidth === 0).map(i => { try { return new URL(i.currentSrc || i.src).pathname; } catch { return '[invalid image URL]'; } }),
        workshopLinks: [...document.querySelectorAll('a[href]')].filter(a => a.textContent.includes('AI戏韵工坊')).map(a => a.getAttribute('href')),
        horizontalOverflow: document.documentElement.scrollWidth > innerWidth + 1 }));
      pages.push({ file, status: response.status(), ...observed });
      if (file === 'index.html') await page.screenshot({ path: path.join(output, 'home-1920.png'), fullPage: false });
    }
    return { pass: pages.every(p => p.status === 200 && p.brokenImages.length === 0 && p.workshopLinks.some(h => h?.includes('about.html')) && !p.horizontalOverflow), pages };
  } finally { await context.close(); }
}
async function secondModel() {
  const { context, page } = await newContext('second-realistic-and-style-switch');
  try {
    await page.goto(`${base}/about.html?assetId=${assetId}#ai-workshop-model`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    result.tests.secondRealistic = await inspectInteraction(page, second, 'second-realistic');
    const creationDisabled = await page.locator('#ai-workshop-model-submit').isDisabled();
    await page.locator('#ai-workshop-asset-style').selectOption('chibi');
    await page.waitForFunction(() => document.querySelector('#ai-workshop-viewer-host')?.dataset.viewerState === 'idle' && document.querySelector('#ai-workshop-viewer-status')?.textContent.includes('当前风格尚未生成3D模型'), null, { timeout: 15000 });
    const absent = await viewerSnapshot(page);
    await page.screenshot({ path: path.join(output, 'same-character-chibi-missing.png'), fullPage: false });
    await page.locator('#ai-workshop-asset-style').selectOption('realistic'); await ready(page);
    const restored = await viewerSnapshot(page);
    result.tests.styleSwitch = { pass: absent.state === 'idle' && absent.modelId === null && absent.renderElements === 0 && restored.modelId === second.id && restored.modelHash === second.hash, absent, restored, creationDisabledBeforeAndAfter: creationDisabled && await page.locator('#ai-workshop-model-submit').isDisabled() };
  } finally { await context.close(); }
}
async function firstModel() {
  const { context, page } = await newContext('first-internal-model');
  try {
    await page.goto(`${base}/api/v1/assets/internal-models/${first.id}/viewer`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    result.tests.firstInternal = await inspectInteraction(page, first, 'first-internal');
    const notice = await page.locator('.ai-workshop-internal-notice').innerText();
    result.tests.firstInternal.scopeNotice = notice;
    result.tests.firstInternal.pass &&= notice.includes('不公开展示或分发') && notice.includes('非正式角色资产');
  } finally { await context.close(); }
}
await fs.mkdir(output, { recursive: true });
await fs.access(path.join(output, 'smoke-result.json')).then(() => { throw new Error('Refusing to overwrite an existing smoke result'); }, () => {});
try {
  browser = await chromium.launch({ executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: true, args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  result.chromeVersion = browser.version(); result.nodeVersion = process.version;
  for (const [name, fn] of [['eightPages', eightPages], ['secondAndStyles', secondModel], ['firstModel', firstModel]]) {
    try { const value = await fn(); if (value) result.tests[name] = value; } catch (error) { result.tests[name] = { pass: false, error: clean(error.message) }; }
    await save();
  }
} catch (error) { result.fatal = clean(error.message); }
finally {
  if (browser) await browser.close();
  result.finishedAt = new Date().toISOString();
  result.blockedMutations = result.contexts.reduce((n, c) => n + c.blockedMutations.length, 0);
  result.blockedExternal = result.contexts.reduce((n, c) => n + c.blockedExternal.length, 0);
  result.noPaidRequestsSent = true;
  result.conclusion = !result.fatal && Object.values(result.tests).every(t => t.pass === true) && result.tests.styleSwitch?.creationDisabledBeforeAndAfter === true ? 'PASS' : 'PARTIAL';
  await save();
  console.log(JSON.stringify({ output, conclusion: result.conclusion, tests: Object.fromEntries(Object.entries(result.tests).map(([k,v])=>[k,v.pass])), blockedMutations: result.blockedMutations, blockedExternal: result.blockedExternal, chromeVersion: result.chromeVersion, fatal: result.fatal }));
}
