// Private, read-only real Chrome/GLB verification. Never sends a paid request.
import { createRequire } from 'node:module';
import fs from 'node:fs/promises';
import path from 'node:path';
const require = createRequire('C:/Users/35037/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/package.json');
const { chromium } = require('playwright');
const args = Object.fromEntries(process.argv.slice(2).map(x => { const i = x.indexOf('='); return [x.slice(0, i), x.slice(i + 1)]; }));
const modelId = args['--model'];
if (!/^[a-f0-9-]{36}$/i.test(modelId || '')) throw new Error('Pass --model=<existing registered model UUID>. No creation is supported.');
const assetId = '9e2b42e1-bbad-4a2f-ab1b-aeda18015dee';
const base = 'http://127.0.0.1:8000';
const output = 'D:/京剧/.runtime/phase4-final-browser';
const resultFile = 'phase4-final-browser-result.json';
await fs.mkdir(output, { recursive: true });
const result = { startedAt: new Date().toISOString(), modelId, assetId, browser: 'Real installed Google Chrome, headless Chromium automation', mobile: 'CDP emulation, not a physical mobile device', paidCallsAllowed: false, tests: {}, contexts: [] };
let browser;
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
const summary = obj => ({ state: obj.state, modelId: obj.modelId, modelHash: obj.modelHash, touchEnabled: obj.touchEnabled, lastError: obj.lastError, orbit: obj.orbit, maxContinuousDegrees: obj.maxContinuousDegrees, userEventCount: obj.userEventCount });
const cleanConsole = text => String(text).replace(/https?:\/\/[^\s"'<>]+/g, value => { try { const url = new URL(value); return `${url.origin}${url.pathname}`; } catch { return '[URL redacted]'; } }).slice(0, 1200);
async function diag(page) { return page.evaluate(() => {
  if (window.xijingAssetViewerDiagnostics) return window.xijingAssetViewerDiagnostics();
  const host = document.querySelector('#ai-workshop-viewer-host');
  const root = document.querySelector('#ai-workshop-internal-root');
  const viewer = host?.querySelector('model-viewer');
  const orbit = viewer?.getCameraOrbit?.();
  return { state: host?.dataset.viewerState, modelId: root?.dataset.modelId, modelHash: document.querySelector('.ai-workshop-internal-hash')?.textContent.match(/[a-f0-9]{64}/)?.[0], touchEnabled: document.querySelector('#ai-workshop-viewer-touch')?.getAttribute('aria-pressed') === 'true', lastError: document.querySelector('#ai-workshop-viewer-error')?.textContent, orbit: orbit ? { ...orbit } : null, maxContinuousDegrees: Number(host?.dataset.observedDegrees || 0), userEventCount: Number(host?.dataset.userEventCount || 0) };
}); }
async function contextFor(name, mobile = false, intercept = null, storedAssetId = assetId) {
  const context = await browser.newContext({ viewport: mobile ? { width: 390, height: 844 } : { width: 1920, height: 1080 }, deviceScaleFactor: 1, isMobile: mobile, hasTouch: mobile, serviceWorkers: 'block' });
  const log = { name, pageErrors: [], console: [], failedResources: [], httpErrors: [], assetReads: [], blockedMutations: [], blockedExternal: [], stateHistory: [] };
  result.contexts.push(log);
  await context.addInitScript(id => { try { localStorage.clear(); sessionStorage.clear(); if (id !== null) sessionStorage.setItem('xijing.ai.asset.v1', id); } catch {} }, storedAssetId);
  await context.route('**/*', async route => {
    const request = route.request(); const url = new URL(request.url());
    if (!['GET', 'HEAD'].includes(request.method())) { log.blockedMutations.push({ method: request.method(), path: url.pathname }); return route.abort('blockedbyclient'); }
    if (['http:', 'https:'].includes(url.protocol) && url.origin !== base) { log.blockedExternal.push({ origin: url.origin, path: url.pathname }); return route.abort('blockedbyclient'); }
    if (url.pathname.startsWith('/api/v1/assets/characters/')) log.assetReads.push(url.pathname);
    if (intercept && url.pathname.includes(`/models/${modelId}/`) && /\.(glb|gltf)$/.test(url.pathname) === false) {
      // Actual controlled endpoint is /models/{uuid}/file; route scope is exact model ID.
      if (url.pathname.endsWith('/file')) return intercept(route);
    }
    return route.continue();
  });
  const page = await context.newPage();
  page.on('console', message => { if (['error', 'warning'].includes(message.type()) && log.console.length < 200) { const location = message.location(); log.console.push({ type: message.type(), text: cleanConsole(message.text()), path: location.url ? cleanConsole(location.url) : '', line: location.lineNumber }); } });
  page.on('pageerror', e => log.pageErrors.push(String(e.message).slice(0, 500)));
  page.on('requestfailed', r => { try { const u = new URL(r.url()); log.failedResources.push({ path: u.pathname, error: r.failure()?.errorText }); } catch {} });
  page.on('response', r => { if (r.status() >= 400) { try { log.httpErrors.push({ path: new URL(r.url()).pathname, status: r.status() }); } catch {} } });
  return { context, page, log };
}
async function openViewer(page, expected = 'ready') {
  await page.goto(`${base}/about.html#ai-workshop-model`, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForFunction(expected => document.querySelector('#ai-workshop-viewer-host')?.dataset.viewerState === expected, expected, { timeout: 45000 });
  if (expected === 'ready') {
    await page.locator('#ai-workshop-viewer-host').scrollIntoViewIfNeeded(); await pause(600);
    const value = await diag(page);
    if (value.modelId !== modelId) throw new Error(`Wrong model loaded: ${value.modelId}`);
  }
}
async function shot(page, name) { await page.screenshot({ path: path.join(output, name), fullPage: false }); }
async function dragMouse(page) {
  const v = page.locator('#ai-workshop-viewer-host model-viewer');
  await v.scrollIntoViewIfNeeded();
  let attempts = 0;
  while ((await diag(page)).maxContinuousDegrees < 270 && attempts < 8) {
    const b = await v.boundingBox(); if (!b) throw new Error('Viewer has no layout box');
    const y = b.y + b.height * 0.55, start = b.x + b.width * 0.82, end = b.x + b.width * 0.18;
    await page.mouse.move(start, y); await page.mouse.down();
    for (let i = 1; i <= 45; i++) { await page.mouse.move(start + (end - start) * i / 45, y); await pause(8); }
    await page.mouse.up(); await pause(550); attempts++;
  }
  const value = await diag(page);
  return { pass: value.maxContinuousDegrees >= 260, attempts, ...summary(value) };
}
async function desktopTest() {
  const { context, page, log } = await contextFor('desktop-real-glb');
  try {
    await openViewer(page); const initial = await diag(page);
    result.tests.desktopLoaded = { pass: initial.state === 'ready' && initial.modelId === modelId, ...summary(initial) };
    await shot(page, '01-desktop-front.png');
    result.tests.mouseRotation = await dragMouse(page);
    await shot(page, '02-desktop-rotated.png');
    const b = await page.locator('#ai-workshop-viewer-host').boundingBox();
    const beforeWheel = (await diag(page)).orbit.radius;
    await page.mouse.move(b.x + b.width * 0.5, b.y + b.height * 0.5); await page.mouse.wheel(0, -400); await pause(900);
    const afterWheel = (await diag(page)).orbit.radius;
    result.tests.wheelZoom = { pass: afterWheel < beforeWheel, beforeRadius: beforeWheel, afterRadius: afterWheel };
    await page.locator('#ai-workshop-viewer-reset').click(); await pause(500);
    const beforeButton = (await diag(page)).orbit.radius;
    await page.locator('#ai-workshop-viewer-zoom-in').click(); await pause(800); const zoomed = (await diag(page)).orbit.radius;
    await page.locator('#ai-workshop-viewer-zoom-out').click(); await pause(800); const zoomOut = (await diag(page)).orbit.radius;
    result.tests.buttonZoom = { pass: zoomed < beforeButton && zoomOut > zoomed, beforeRadius: beforeButton, inRadius: zoomed, outRadius: zoomOut };
    await page.locator('#ai-workshop-viewer-reset').click(); await pause(500); const reset = await diag(page);
    result.tests.reset = { pass: Math.abs(reset.orbit.theta) < 0.02 && Math.abs(reset.orbit.phi - 75 * Math.PI / 180) < 0.02 && Math.abs(reset.orbit.radius - initial.orbit.radius) / initial.orbit.radius < 0.02, initialOrbit: initial.orbit, resetOrbit: reset.orbit };
    // Programmatic positioning is ONLY for visual front/back inspection and is not rotation evidence.
    for (const [name, degrees] of [['03-side-90.png', 90], ['04-back-180.png', 180], ['05-side-270.png', 270]]) {
      await page.evaluate(d => { const v = document.querySelector('#ai-workshop-viewer-host model-viewer'); v.cameraOrbit = `${d}deg 75deg auto`; v.jumpCameraToGoal(); }, degrees);
      await pause(500); await shot(page, name);
    }
    log.stateHistory = await page.locator('#ai-workshop-viewer-host').getAttribute('data-state-history');
    result.tests.realGenerateDisabled = await page.locator('#ai-workshop-model-submit').isDisabled();
  } finally { await context.close(); }
}
async function touchEvent(cdp, type, points) { await cdp.send('Input.dispatchTouchEvent', { type, touchPoints: points.map((p, i) => ({ x: p[0], y: p[1], id: i, radiusX: 5, radiusY: 5, force: 1 })) }); }
async function mobileTest() {
  const { context, page, log } = await contextFor('emulated-mobile-real-glb', true);
  try {
    await openViewer(page); await page.locator('#ai-workshop-viewer-touch').click();
    await page.locator('#ai-workshop-viewer-host').scrollIntoViewIfNeeded();
    const cdp = await context.newCDPSession(page); const b = await page.locator('#ai-workshop-viewer-host').boundingBox();
    const y = Math.min(b.y + b.height * .48, 780), start = b.x + b.width * .78, end = b.x + b.width * .22;
    const before = await diag(page);
    await touchEvent(cdp, 'touchStart', [[start, y]]);
    for (let i = 1; i <= 30; i++) { await touchEvent(cdp, 'touchMove', [[start + (end - start) * i / 30, y]]); await pause(12); }
    await touchEvent(cdp, 'touchEnd', []); await pause(650); const after = await diag(page);
    result.tests.touchRotate = { pass: after.userEventCount > before.userEventCount && Math.abs(after.orbit.theta - before.orbit.theta) > .2, before: summary(before), after: summary(after) };
    const cx = b.x + b.width / 2, cy = y, radiusBefore = after.orbit.radius;
    await touchEvent(cdp, 'touchStart', [[cx - 25, cy], [cx + 25, cy]]);
    for (let i = 1; i <= 25; i++) { const d = 25 + i * 2.3; await touchEvent(cdp, 'touchMove', [[cx - d, cy], [cx + d, cy]]); await pause(16); }
    await touchEvent(cdp, 'touchEnd', []); await pause(800); const radiusAfter = (await diag(page)).orbit.radius;
    result.tests.pinchZoom = { pass: radiusAfter < radiusBefore, beforeRadius: radiusBefore, afterRadius: radiusAfter, method: 'Chrome CDP two simultaneous touch contacts' };
    await page.locator('#ai-workshop-viewer-reset').click(); await pause(500);
    const reset = await diag(page); result.tests.mobileReset = { pass: Math.abs(reset.orbit.theta) < .02 && Math.abs(reset.orbit.phi - 75 * Math.PI / 180) < .02, orbit: reset.orbit };
    await page.locator('#ai-workshop-viewer-host').scrollIntoViewIfNeeded(); await shot(page, '06-mobile-390x844.png');
    result.tests.mobileLayout = await page.evaluate(() => ({ viewport: innerWidth, documentWidth: document.documentElement.scrollWidth, viewerWidth: document.querySelector('#ai-workshop-viewer-host').getBoundingClientRect().width, bodyOverflow: document.documentElement.scrollWidth > innerWidth + 1 }));
    log.stateHistory = await page.locator('#ai-workshop-viewer-host').getAttribute('data-state-history');
  } finally { await context.close(); }
}
async function stateTest() {
  let released = false;
  const loading = await contextFor('loading-real-resource-delayed', false, async route => { await pause(2000); released = true; return route.continue(); });
  try {
    await loading.page.goto(`${base}/about.html#ai-workshop-model`, { waitUntil: 'domcontentloaded' });
    await loading.page.waitForFunction(() => document.querySelector('#ai-workshop-viewer-host')?.dataset.viewerState === 'loading', null, { timeout: 15000 });
    result.tests.loading = { pass: !released, text: await loading.page.locator('#ai-workshop-viewer-status').innerText(), delayedOnlyOriginalGlb: true };
    await loading.page.locator('#ai-workshop-viewer-host').scrollIntoViewIfNeeded(); await shot(loading.page, '07-loading.png');
    await loading.page.waitForFunction(() => document.querySelector('#ai-workshop-viewer-host')?.dataset.viewerState === 'ready', null, { timeout: 45000 });
    result.tests.loadingThenReady = { pass: (await diag(loading.page)).state === 'ready' };
  } finally { await loading.context.close(); }
  const error = await contextFor('error-original-resource-aborted', false, route => route.abort('failed'));
  try {
    await openViewer(error.page, 'error'); await error.page.locator('#ai-workshop-viewer-host').scrollIntoViewIfNeeded();
    result.tests.error = { pass: await error.page.locator('#ai-workshop-viewer-error').isVisible(), ...summary(await diag(error.page)), originalResourceAbortOnly: true, reloadOriginalVisible: await error.page.locator('#ai-workshop-viewer-reload').isVisible() };
    await shot(error.page, '08-error.png');
  } finally { await error.context.close(); }
}
async function regression() {
  const { context, page, log } = await contextFor('eight-static-pages-regression'); const pages = [];
  try {
    for (const filename of ['index.html', 'history.html', 'roles.html', 'facial.html', 'music.html', 'gallery.html', 'video.html', 'about.html']) {
      const response = await page.goto(`${base}/${filename}`, { waitUntil: 'networkidle', timeout: 30000 });
      const check = await page.evaluate(() => ({ title: document.title, brokenImages: [...document.images].filter(i => i.currentSrc && i.complete && i.naturalWidth === 0).map(i => new URL(i.currentSrc).pathname), workshopNavigation: [...document.querySelectorAll('a[href]')].some(a => a.getAttribute('href')?.includes('about.html') && a.textContent.includes('AI戏韵工坊')), horizontalOverflow: document.documentElement.scrollWidth > innerWidth + 1 }));
      pages.push({ filename, status: response.status(), ...check });
      if (filename === 'index.html') await shot(page, '09-home-1920x1080.png');
    }
    result.tests.eightPages = { pass: pages.every(p => p.status === 200 && p.brokenImages.length === 0 && p.workshopNavigation), pages };
    log.stateHistory = 'not applicable, static navigation only';
  } finally { await context.close(); }
}
async function styleTest() {
  const { context, page, log } = await contextFor('same-character-style-switch-read-only');
  try {
    await openViewer(page); const before = await diag(page);
    const originalCharacter = await page.locator('#ai-workshop-asset-summary').getAttribute('data-character-id');
    await page.locator('#ai-workshop-asset-style').selectOption('chibi');
    await page.waitForFunction(() => document.querySelector('#ai-workshop-viewer-status')?.textContent.includes('当前风格尚未生成3D模型'), null, { timeout: 15000 });
    await pause(250);
    const absent = await diag(page);
    const absence = { state: absent.state, modelId: absent.modelId, statusText: await page.locator('#ai-workshop-viewer-status').innerText(), selectorValue: await page.locator('#ai-workshop-style-model-select').inputValue(), viewerElementCount: await page.locator('#ai-workshop-viewer-host model-viewer').count() };
    result.tests.chibiNotFaked = { pass: absent.state === 'idle' && absent.modelId === null && absence.selectorValue === '' && absence.viewerElementCount === 0, before: summary(before), absent: absence };
    await page.locator('#ai-workshop-viewer-host').scrollIntoViewIfNeeded(); await shot(page, '10-chibi-style-missing.png');
    await page.locator('#ai-workshop-asset-style').selectOption('realistic');
    await page.waitForFunction(id => window.xijingAssetViewerDiagnostics?.()?.state === 'ready' && window.xijingAssetViewerDiagnostics?.()?.modelId === id, modelId, { timeout: 45000 });
    const restored = await diag(page); const restoredCharacter = await page.locator('#ai-workshop-asset-summary').getAttribute('data-character-id');
    result.tests.realisticRestored = { pass: restored.modelId === modelId && restoredCharacter === originalCharacter && restored.modelHash === before.modelHash, characterId: restoredCharacter, ...summary(restored) };
    await page.locator('#ai-workshop-viewer-host').scrollIntoViewIfNeeded(); await shot(page, '11-realistic-style-restored.png');
    log.stateHistory = await page.locator('#ai-workshop-viewer-host').getAttribute('data-state-history');
  } finally { await context.close(); }
}
async function mobileRangeTest() {
  const { context, page, log } = await contextFor('emulated-mobile-continuous-range', true);
  try {
    await openViewer(page); await page.locator('#ai-workshop-viewer-touch').click();
    await page.locator('#ai-workshop-viewer-host').scrollIntoViewIfNeeded();
    const cdp = await context.newCDPSession(page);
    const initial = await diag(page); const sweeps = [];
    for (let n = 0; n < 3 && (await diag(page)).maxContinuousDegrees < 270; n++) {
      const b = await page.locator('#ai-workshop-viewer-host').boundingBox();
      const y = Math.min(b.y + b.height * .48, 780), start = b.x + b.width * .78, end = b.x + b.width * .22;
      await touchEvent(cdp, 'touchStart', [[start, y]]);
      for (let i = 1; i <= 30; i++) { await touchEvent(cdp, 'touchMove', [[start + (end - start) * i / 30, y]]); await pause(12); }
      await touchEvent(cdp, 'touchEnd', []); await pause(650);
      sweeps.push(summary(await diag(page)));
    }
    const final = await diag(page);
    result.tests.mobileContinuous260 = { pass: final.maxContinuousDegrees >= 260 && final.modelId === modelId, method: 'Real Chrome CDP emulated single-touch gestures, repeated same direction, not physical phone', initial: summary(initial), sweeps, final: summary(final) };
    await shot(page, '12-mobile-over260.png');
    log.stateHistory = await page.locator('#ai-workshop-viewer-host').getAttribute('data-state-history');
  } finally { await context.close(); }
}
async function errorRecoveryTest() {
  let faultEnabled = true, aborted = 0, allowedOriginal = 0;
  const { context, page, log } = await contextFor('one-abort-then-reload-original-glb', false, route => {
    if (faultEnabled && aborted === 0) { aborted++; return route.abort('failed'); }
    allowedOriginal++; return route.continue();
  });
  try {
    await openViewer(page, 'error'); const failed = await diag(page);
    const errorVisible = await page.locator('#ai-workshop-viewer-error').isVisible();
    // Disable only injected fault. The same strict GET/local-origin guard remains active.
    faultEnabled = false;
    await page.locator('#ai-workshop-viewer-reload').click();
    await page.waitForFunction(id => window.xijingAssetViewerDiagnostics?.()?.state === 'ready' && window.xijingAssetViewerDiagnostics?.()?.modelId === id, modelId, { timeout: 45000 });
    await page.locator('#ai-workshop-viewer-host').scrollIntoViewIfNeeded(); await pause(500);
    const ready = await diag(page);
    result.tests.reloadOriginalAfterError = { pass: errorVisible && failed.state === 'error' && ready.state === 'ready' && ready.modelId === failed.modelId && ready.modelHash === failed.modelHash && aborted === 1 && allowedOriginal >= 1, faultDisabledBeforeClick: true, aborted, allowedOriginal, before: summary(failed), after: summary(ready), noModelCreationPossible: true };
    await shot(page, '13-error-recovered-original.png');
    log.stateHistory = await page.locator('#ai-workshop-viewer-host').getAttribute('data-state-history');
  } finally { await context.close(); }
}
async function reviewLinkTest() {
  const conflicting = '11111111-1111-4111-8111-111111111111';
  const cases = [
    { name: 'valid-link-empty-storage', storage: null, linked: assetId, expectedReady: true },
    { name: 'valid-link-overrides-conflicting-storage', storage: conflicting, linked: assetId, expectedReady: true },
    { name: 'invalid-link-safe-storage-fallback', storage: assetId, linked: '../../invalid', expectedReady: true },
    { name: 'invalid-link-no-storage-no-asset-get', storage: null, linked: '../../invalid', expectedReady: false },
  ];
  for (const item of cases) {
    const { context, page, log } = await contextFor(item.name, false, null, item.storage);
    try {
      await page.goto(`${base}/about.html?assetId=${encodeURIComponent(item.linked)}#ai-workshop-model`, { waitUntil: 'domcontentloaded', timeout: 30000 });
      if (item.expectedReady) {
        await page.waitForFunction(id => window.xijingAssetViewerDiagnostics?.()?.state === 'ready' && window.xijingAssetViewerDiagnostics?.()?.modelId === id, modelId, { timeout: 45000 });
        const value = await diag(page);
        const registeredId = await page.locator('#ai-workshop-asset-summary').getAttribute('data-asset-id');
        result.tests[item.name] = { pass: registeredId === assetId && value.modelId === modelId && value.modelHash === '5a021ac6338009615e6ea232c5b9001eef6f4cc91d9d87c3eeeb5307526bdfd5' && log.assetReads.length === 1 && log.assetReads[0] === `/api/v1/assets/characters/${assetId}`, assetId: registeredId, storageBefore: item.storage, assetReads: [...log.assetReads], ...summary(value) };
        if (item.name === 'valid-link-empty-storage') { await page.locator('#ai-workshop-viewer-host').scrollIntoViewIfNeeded(); await shot(page, '14-direct-review-link-empty-storage.png'); }
      } else {
        await page.waitForFunction(() => window.xijingAssetViewerDiagnostics?.()?.state === 'idle' && document.querySelector('#ai-workshop-asset-refresh')?.disabled === false, null, { timeout: 15000 });
        await pause(500); const value = await diag(page);
        result.tests[item.name] = { pass: value.state === 'idle' && value.modelId === null && log.assetReads.length === 0, assetReads: [...log.assetReads], ...summary(value) };
      }
      result.tests[item.name].realGenerateDisabled = await page.locator('#ai-workshop-model-submit').isDisabled();
      log.stateHistory = await page.locator('#ai-workshop-viewer-host').getAttribute('data-state-history');
    } finally { await context.close(); }
  }
}
const internalModelId = '3777a880-fc8c-4766-aade-948d20c6b8f0';
const internalExpectedHash = 'bf9c808c15dbf5464ee67df1cdb3f64f9b2c6b3cd4ee41ecb8a6470a0554654a';
async function openInternal(page) {
  await page.goto(`${base}/api/v1/assets/internal-models/${internalModelId}/viewer`, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForFunction(() => document.querySelector('#ai-workshop-viewer-host')?.dataset.viewerState === 'ready', null, { timeout: 45000 });
  await page.locator('#ai-workshop-viewer-host').scrollIntoViewIfNeeded(); await pause(600);
  const value = await diag(page);
  if (value.modelId !== internalModelId || value.modelHash !== internalExpectedHash) throw new Error('Internal technical GLB identifier or hash mismatch');
}
async function internalDesktopTest() {
  const { context, page, log } = await contextFor('first-internal-model-desktop-only');
  try {
    await openInternal(page); const initial = await diag(page);
    const notice = await page.locator('.ai-workshop-internal-notice').innerText();
    result.tests.firstInternalScope = { pass: notice.includes('非正式角色资产') && notice.includes('不公开展示或分发'), notice, formalCharacterAsset: false, sameCharacterChibiAsset: false, ...summary(initial) };
    await shot(page, '15-first-internal-front.png');
    result.tests.firstInternalMouse260 = await dragMouse(page);
    await shot(page, '16-first-internal-rotated.png');
    const b = await page.locator('#ai-workshop-viewer-host').boundingBox(); const beforeWheel = (await diag(page)).orbit.radius;
    await page.mouse.move(b.x + b.width * .5, b.y + b.height * .5); await page.mouse.wheel(0, -350); await pause(700); const afterWheel = (await diag(page)).orbit.radius;
    await page.locator('#ai-workshop-viewer-reset').click(); await pause(400);
    const beforeButton = (await diag(page)).orbit.radius;
    await page.locator('#ai-workshop-viewer-zoom-in').click(); await pause(650); const inside = (await diag(page)).orbit.radius;
    await page.locator('#ai-workshop-viewer-zoom-out').click(); await pause(650); const outside = (await diag(page)).orbit.radius;
    await page.locator('#ai-workshop-viewer-reset').click(); await pause(400); const reset = await diag(page);
    result.tests.firstInternalZoomReset = { pass: afterWheel < beforeWheel && inside < beforeButton && outside > inside && Math.abs(reset.orbit.theta) < .02 && Math.abs(reset.orbit.phi - 75 * Math.PI / 180) < .02 && Math.abs(reset.orbit.radius - initial.orbit.radius) / initial.orbit.radius < .02, beforeWheel, afterWheel, beforeButton, inside, outside, initial: initial.orbit, reset: reset.orbit };
    log.stateHistory = await page.locator('#ai-workshop-viewer-host').getAttribute('data-state-history');
  } finally { await context.close(); }
}
async function internalMobileTest() {
  const { context, page, log } = await contextFor('first-internal-model-emulated-mobile', true);
  try {
    await openInternal(page); await page.locator('#ai-workshop-viewer-touch').click();
    await page.locator('#ai-workshop-viewer-host').scrollIntoViewIfNeeded(); const cdp = await context.newCDPSession(page);
    const initial = await diag(page); const sweeps = [];
    for (let n = 0; n < 4 && (await diag(page)).maxContinuousDegrees < 270; n++) {
      const b = await page.locator('#ai-workshop-viewer-host').boundingBox(); const y = Math.min(b.y + b.height * .48, 780), start = b.x + b.width * .78, end = b.x + b.width * .22;
      await touchEvent(cdp, 'touchStart', [[start, y]]);
      for (let i = 1; i <= 30; i++) { await touchEvent(cdp, 'touchMove', [[start + (end - start) * i / 30, y]]); await pause(12); }
      await touchEvent(cdp, 'touchEnd', []); await pause(600); sweeps.push(summary(await diag(page)));
    }
    const rotated = await diag(page); const b = await page.locator('#ai-workshop-viewer-host').boundingBox(); const cx = b.x + b.width * .5, cy = Math.min(b.y + b.height * .48, 780), beforePinch = rotated.orbit.radius;
    await touchEvent(cdp, 'touchStart', [[cx - 25, cy], [cx + 25, cy]]);
    for (let i = 1; i <= 25; i++) { const d = 25 + i * 2.3; await touchEvent(cdp, 'touchMove', [[cx - d, cy], [cx + d, cy]]); await pause(16); }
    await touchEvent(cdp, 'touchEnd', []); await pause(700); const afterPinch = (await diag(page)).orbit.radius;
    await page.locator('#ai-workshop-viewer-reset').click(); await pause(400); const reset = await diag(page);
    result.tests.firstInternalMobile260ZoomReset = { pass: rotated.maxContinuousDegrees >= 260 && afterPinch < beforePinch && Math.abs(reset.orbit.theta) < .02 && Math.abs(reset.orbit.phi - 75 * Math.PI / 180) < .02, method: 'Chrome CDP emulation, not physical mobile, first internal GLB kept separate from formal character', initial: summary(initial), sweeps, continuousDegrees: rotated.maxContinuousDegrees, beforePinch, afterPinch, reset: reset.orbit };
    await page.locator('#ai-workshop-viewer-host').scrollIntoViewIfNeeded(); await shot(page, '17-first-internal-mobile.png');
    log.stateHistory = await page.locator('#ai-workshop-viewer-host').getAttribute('data-state-history');
  } finally { await context.close(); }
}
try {
  browser = await chromium.launch({ executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: true, args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  result.chromeVersion = browser.version();
  const selectedTests = [['desktop', desktopTest], ['mobile', mobileTest], ['mobileRange', mobileRangeTest], ['states', stateTest], ['errorRecovery', errorRecoveryTest], ['style', styleTest], ['regression', regression], ['reviewLink', reviewLinkTest], ['internalDesktop', internalDesktopTest], ['internalMobile', internalMobileTest]];
  for (const [name, fn] of selectedTests) {
    try { await fn(); } catch (e) { result.tests[`${name}Failure`] = { pass: false, message: String(e.message).slice(0, 800) }; }
    await fs.writeFile(path.join(output, resultFile), JSON.stringify(result, null, 2));
  }
} catch (e) { result.fatal = String(e.message).slice(0, 1000); }
finally {
  if (browser) await browser.close(); result.finishedAt = new Date().toISOString();
  result.blockedMutations = result.contexts.reduce((sum, c) => sum + c.blockedMutations.length, 0);
  result.noPaidRequestsSent = true;
  await fs.writeFile(path.join(output, resultFile), JSON.stringify(result, null, 2));
  console.log(JSON.stringify({ output, tests: result.tests, blockedMutations: result.blockedMutations, fatal: result.fatal }, null, 2));
}
