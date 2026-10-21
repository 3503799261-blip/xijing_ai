// WP4 existing real GLBs, Chrome CDP touch emulation only; not a physical phone.
import { createRequire } from 'node:module';
import fs from 'node:fs/promises';
import path from 'node:path';
const { chromium } = createRequire(process.env.XIJING_PLAYWRIGHT_PACKAGE)('playwright');
const output = process.argv[2]; if (!output) throw new Error('New evidence output is required');
await fs.mkdir(output, { recursive: false });
const base = 'http://127.0.0.1:8000';
const models = [
  { name: 'realistic', id: '1fa0b519-caf4-4009-aec2-f20b0f9a3523', hash: '5a021ac6338009615e6ea232c5b9001eef6f4cc91d9d87c3eeeb5307526bdfd5', url: '/about.html?assetId=9e2b42e1-bbad-4a2f-ab1b-aeda18015dee#ai-workshop-model' },
  { name: 'internal-chibi', id: '3777a880-fc8c-4766-aade-948d20c6b8f0', hash: 'bf9c808c15dbf5464ee67df1cdb3f64f9b2c6b3cd4ee41ecb8a6470a0554654a', url: '/api/v1/assets/internal-models/3777a880-fc8c-4766-aade-948d20c6b8f0/viewer' }
];
const report = { startedAt: new Date().toISOString(), scope: 'WP4_REAL_GLB_CDP_TOUCH_WHEEL_ZOOM_RESET_AND_SYNTHETIC_FILE_FAILURE_RECOVERY', physicalPhone: 'NOT_TESTED', viewport: { width: 390, height: 844 }, tests: [], paidRequests: 0, supplierRequests: 0 };
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
const save = () => fs.writeFile(path.join(output, 'touch-result.json'), JSON.stringify(report, null, 2));
const safe = value => String(value).replace(/https?:\/\/[^\s"'<>]+/g, raw => { try { const u = new URL(raw); return u.origin + u.pathname; } catch { return '[URL]'; } }).slice(0, 600);
async function snap(page) {
  return page.evaluate(() => {
    const host = document.querySelector('#ai-workshop-viewer-host'), viewer = host?.querySelector('model-viewer'), d = window.xijingAssetViewerDiagnostics?.(), orbit = viewer?.getCameraOrbit?.();
    return { state: host?.dataset.viewerState, modelId: d?.modelId || document.querySelector('#ai-workshop-internal-root')?.dataset.modelId || null, modelHash: d?.modelHash || document.querySelector('.ai-workshop-internal-hash')?.textContent.match(/[a-f0-9]{64}/)?.[0] || null,
      degrees: Number(host?.dataset.observedDegrees || 0), userEventCount: Number(host?.dataset.userEventCount || 0), touchEnabled: document.querySelector('#ai-workshop-viewer-touch')?.getAttribute('aria-pressed'), orbit: orbit ? { theta: orbit.theta, phi: orbit.phi, radius: orbit.radius } : null,
      status: document.querySelector('#ai-workshop-viewer-status')?.textContent };
  });
}
async function ready(page) { await page.waitForFunction(() => document.querySelector('#ai-workshop-viewer-host')?.dataset.viewerState === 'ready', null, { timeout: 45000 }); await page.locator('#ai-workshop-viewer-host').scrollIntoViewIfNeeded(); await pause(500); }
async function touch(cdp, type, points) { await cdp.send('Input.dispatchTouchEvent', { type, touchPoints: points.map((p, id) => ({ x: p[0], y: p[1], id, radiusX: 5, radiusY: 5, force: 1 })) }); }
let browser;
try {
  browser = await chromium.launch({ executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: true, args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  report.chromeVersion = browser.version(); report.nodeVersion = process.version;
  for (const model of models) {
    const start = performance.now();
    const test = { name: model.name, modelId: model.id, status: 'FAIL', startedAt: new Date().toISOString(), requests: [], blockedWrites: [], blockedExternal: [], pageErrors: [], consoleErrors: [], fileRequests: [], stateHistory: [] };
    const context = await browser.newContext({ viewport: report.viewport, isMobile: true, hasTouch: true, serviceWorkers: 'block' });
    await context.route('**/*', route => { const req = route.request(), url = new URL(req.url()); test.requests.push({ method: req.method(), path: url.pathname }); if (!['GET','HEAD'].includes(req.method())) { test.blockedWrites.push({ method: req.method(), path: url.pathname }); return route.abort(); } if (['http:','https:'].includes(url.protocol) && url.origin !== base) { test.blockedExternal.push(url.origin); return route.abort(); } return route.continue(); });
    const page = await context.newPage();
    page.on('pageerror', error => test.pageErrors.push(safe(error.message)));
    page.on('console', msg => { if (msg.type() === 'error') test.consoleErrors.push(safe(msg.text())); });
    let fileFailure = false;
    await page.route(`**/api/v1/assets/models/${model.id}/file*`, async route => { test.fileRequests.push({ syntheticFailure: fileFailure }); if (fileFailure) { await pause(450); return route.fulfill({ status: 503, body: 'Explicit WP4 browser response double. Original file is unchanged.' }); } return route.continue(); });
    await page.addInitScript(() => {
      window.__wp4States = [];
      const capture = () => { const state = document.querySelector('#ai-workshop-viewer-host')?.dataset.viewerState; if (state && window.__wp4States.at(-1) !== state) window.__wp4States.push(state); };
      new MutationObserver(capture).observe(document, { subtree: true, childList: true, attributes: true, attributeFilter: ['data-viewer-state'] });
    });
    try {
      await page.goto(base + model.url, { waitUntil: 'domcontentloaded', timeout: 30000 }); await ready(page);
      await page.locator('#ai-workshop-viewer-touch').click(); await page.locator('#ai-workshop-viewer-host').scrollIntoViewIfNeeded();
      const cdp = await context.newCDPSession(page); test.initial = await snap(page); test.sweeps = [];
      for (let sweep = 0; sweep < 4 && (await snap(page)).degrees < 270; sweep++) {
        const b = await page.locator('#ai-workshop-viewer-host').boundingBox(), y = Math.min(b.y + b.height * 0.48, 780), startX = b.x + b.width * .78, endX = b.x + b.width * .22;
        await touch(cdp, 'touchStart', [[startX, y]]);
        for (let i = 1; i <= 30; i++) { await touch(cdp, 'touchMove', [[startX + (endX - startX) * i / 30, y]]); await pause(12); }
        await touch(cdp, 'touchEnd', []); await pause(650); test.sweeps.push(await snap(page));
      }
      test.rotated = await snap(page);
      const b = await page.locator('#ai-workshop-viewer-host').boundingBox(), cx = b.x + b.width * .5, cy = Math.min(b.y + b.height * .48, 780);
      await touch(cdp, 'touchStart', [[cx - 25, cy], [cx + 25, cy]]);
      for (let i = 1; i <= 25; i++) { const distance = 25 + i * 2.3; await touch(cdp, 'touchMove', [[cx - distance, cy], [cx + distance, cy]]); await pause(16); }
      await touch(cdp, 'touchEnd', []); await pause(700); test.pinched = await snap(page);
      await page.locator('#ai-workshop-viewer-reset').click(); await pause(500); test.reset = await snap(page);
      const vbox = await page.locator('#ai-workshop-viewer-host model-viewer').boundingBox();
      await page.mouse.move(vbox.x + vbox.width * .5, Math.min(vbox.y + vbox.height * .5, 780)); await page.mouse.wheel(0, -220); await pause(700); test.wheelZoom = await snap(page);
      await page.locator('#ai-workshop-viewer-reset').click(); await pause(500);
      await page.locator('#ai-workshop-viewer-zoom-in').click(); await pause(650); test.buttonZoomIn = await snap(page);
      await page.locator('#ai-workshop-viewer-zoom-out').click(); await pause(650); test.buttonZoomOut = await snap(page);
      await page.locator('#ai-workshop-viewer-reset').click(); await pause(500);
      await page.screenshot({ path: path.join(output, `${model.name}-mobile-ready.png`) });
      test.stateHistoryBeforeReload = await page.evaluate(() => window.__wp4States);
      fileFailure = true; await page.reload({ waitUntil: 'domcontentloaded' });
      await page.waitForFunction(() => document.querySelector('#ai-workshop-viewer-host')?.dataset.viewerState === 'error', null, { timeout: 20000 }); test.error = await snap(page);
      await page.screenshot({ path: path.join(output, `${model.name}-mobile-error.png`) });
      fileFailure = false; await page.locator('#ai-workshop-viewer-reload').click(); await ready(page); test.recovered = await snap(page);
      test.stateHistory = [...test.stateHistoryBeforeReload, ...await page.evaluate(() => window.__wp4States)];
      await page.screenshot({ path: path.join(output, `${model.name}-mobile-recovered.png`) });
      test.assertions = {
        exactRealModel: test.initial.modelId === model.id && test.initial.modelHash === model.hash,
        touchEnabled: test.initial.touchEnabled === 'true', continuousTouch260: test.rotated.degrees >= 260 && test.rotated.userEventCount > test.initial.userEventCount,
        pinchZoomIn: test.pinched.orbit.radius < test.rotated.orbit.radius,
        reset: Math.abs(test.reset.orbit.theta) < .02 && Math.abs(test.reset.orbit.phi - 75 * Math.PI / 180) < .02 && Math.abs(test.reset.orbit.radius - test.initial.orbit.radius) / test.initial.orbit.radius < .02,
        wheelZoomIn: test.wheelZoom.orbit.radius < test.reset.orbit.radius,
        zoomButtons: test.buttonZoomIn.orbit.radius < test.reset.orbit.radius && test.buttonZoomOut.orbit.radius > test.buttonZoomIn.orbit.radius,
        loadingReadyErrorObserved: ['loading','ready','error'].every(state => test.stateHistory.includes(state)),
        failedOriginalFileRecovered: test.error.state === 'error' && test.recovered.state === 'ready' && test.recovered.modelId === model.id && test.recovered.modelHash === model.hash,
        noWritesExternalOrPageErrors: test.blockedWrites.length === 0 && test.blockedExternal.length === 0 && test.pageErrors.length === 0
      };
      test.status = Object.values(test.assertions).every(Boolean) ? 'PASS' : 'FAIL';
    } catch (error) { test.failure = safe(error.message); }
    finally { test.finishedAt = new Date().toISOString(); test.elapsedMs = Math.round(performance.now() - start); report.tests.push(test); await save(); await context.close(); }
  }
} catch (error) { report.fatal = safe(error.message); }
finally {
  if (browser) await browser.close(); report.finishedAt = new Date().toISOString(); report.passed = report.tests.filter(test => test.status === 'PASS').length; report.failed = report.tests.filter(test => test.status === 'FAIL').length; report.skipped = 0;
  report.blockedWrites = report.tests.reduce((n,test) => n + test.blockedWrites.length, 0); report.blockedExternal = report.tests.reduce((n,test) => n + test.blockedExternal.length, 0);
  report.status = !report.fatal && report.passed === 2 && report.failed === 0 ? 'PASS' : 'FAIL'; await save(); console.log(JSON.stringify({ output, status: report.status, passed: report.passed, failed: report.failed, blockedWrites: report.blockedWrites, blockedExternal: report.blockedExternal, fatal: report.fatal })); if (report.status !== 'PASS') process.exitCode = 1;
}
