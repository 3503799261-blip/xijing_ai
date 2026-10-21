// WP4: read-only, local browser regression. No provider or business mutation requests.
import { createRequire } from 'node:module';
import fs from 'node:fs/promises';
import path from 'node:path';
const { chromium } = createRequire(process.env.XIJING_PLAYWRIGHT_PACKAGE)('playwright');
const output = process.argv[2];
if (!output) throw new Error('A new evidence directory is required');
await fs.mkdir(output, { recursive: false });
const base = 'http://127.0.0.1:8000';
const files = ['index.html', 'history.html', 'roles.html', 'facial.html', 'music.html', 'gallery.html', 'video.html', 'about.html'];
const sizes = [{ width: 1920, height: 1080 }, { width: 768, height: 1024 }, { width: 390, height: 844 }];
const report = { startedAt: new Date().toISOString(), scope: 'WP4_24_REAL_LOCAL_PAGE_VIEWPORT_PAIRS_GET_HEAD_ONLY', cases: [], paidRequests: 0, supplierRequests: 0, physicalMobile: 'NOT_TESTED', serviceWorkers: 'blocked' };
const clean = value => String(value).replace(/https?:\/\/[^\s"'<>]+/g, raw => { try { const u = new URL(raw); return u.origin + u.pathname; } catch { return '[URL]'; } }).slice(0, 600);
const save = () => fs.writeFile(path.join(output, 'layout-matrix-result.json'), JSON.stringify(report, null, 2));
let browser;
try {
  browser = await chromium.launch({ executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: true, args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  report.chromeVersion = browser.version(); report.nodeVersion = process.version;
  for (const viewport of sizes) for (const file of files) {
    const startedAt = new Date().toISOString(), start = performance.now();
    const entry = { file, viewport, startedAt, status: 'FAIL', requests: [], blockedWrites: [], blockedExternal: [], pageErrors: [], consoleErrors: [], httpErrors: [], failedResources: [] };
    const context = await browser.newContext({ viewport, isMobile: viewport.width === 390, hasTouch: viewport.width <= 768, serviceWorkers: 'block' });
    await context.route('**/*', route => {
      const req = route.request(), url = new URL(req.url());
      entry.requests.push({ method: req.method(), path: url.pathname, resourceType: req.resourceType() });
      if (!['GET', 'HEAD'].includes(req.method())) { entry.blockedWrites.push({ method: req.method(), path: url.pathname }); return route.abort('blockedbyclient'); }
      if (['http:', 'https:'].includes(url.protocol) && url.origin !== base) { entry.blockedExternal.push({ origin: url.origin, path: url.pathname }); return route.abort('blockedbyclient'); }
      return route.continue();
    });
    const page = await context.newPage();
    page.on('pageerror', err => entry.pageErrors.push(clean(err.message)));
    page.on('console', msg => { if (msg.type() === 'error') entry.consoleErrors.push(clean(msg.text())); });
    page.on('response', res => { if (res.status() >= 400) entry.httpErrors.push({ path: new URL(res.url()).pathname, status: res.status() }); });
    page.on('requestfailed', req => entry.failedResources.push({ path: new URL(req.url()).pathname, resourceType: req.resourceType(), error: req.failure()?.errorText }));
    try {
      const response = await page.goto(`${base}/${file}`, { waitUntil: 'load', timeout: 30000 });
      await page.waitForFunction(() => [...document.images].every(img => img.complete), null, { timeout: 15000 });
      await page.evaluate(() => document.fonts.ready);
      await page.waitForTimeout(150);
      await page.waitForFunction(() => [...document.querySelectorAll('audio,video')].every(media => media.readyState >= 1 || media.error), null, { timeout: 10000 });
      entry.httpStatus = response.status();
      entry.observed = await page.evaluate(() => {
        const h = document.querySelector('h1'), bounds = h?.getBoundingClientRect();
        return {
          title: document.title.trim(), h1: h?.textContent.trim(), h1Visible: Boolean(bounds && bounds.width > 0 && bounds.height > 0), mainTextLength: document.querySelector('main')?.textContent.trim().length || 0,
          nav: [...document.querySelectorAll('nav[aria-label="主导航"] .nav-list a')].map(a => ({ label: a.textContent.trim(), href: a.getAttribute('href'), path: new URL(a.href).pathname, origin: new URL(a.href).origin })),
          stylesheets: [...document.querySelectorAll('link[rel="stylesheet"]')].map(link => ({ path: new URL(link.href).pathname, loaded: Boolean(link.sheet) })),
          scripts: [...document.querySelectorAll('script[src]')].map(script => ({ path: new URL(script.src).pathname, type: script.type })),
          media: [...document.querySelectorAll('audio,video')].map(media => ({ tag: media.tagName, path: new URL(media.currentSrc || media.src || media.querySelector('source')?.src).pathname, readyState: media.readyState, networkState: media.networkState, error: media.error ? { code: media.error.code, message: media.error.message } : null, duration: Number.isFinite(media.duration) ? media.duration : null })),
          brokenImages: [...document.images].filter(img => (img.currentSrc || img.src) && img.naturalWidth === 0).map(img => new URL(img.currentSrc || img.src).pathname),
          imageCount: document.images.length,
          horizontalOverflow: document.documentElement.scrollWidth > innerWidth + 1,
          scrollWidth: document.documentElement.scrollWidth, innerWidth,
          workshopPresent: Boolean(document.querySelector('#ai-workshop'))
        };
      });
      const toggle = page.locator('#nav-toggle');
      if (await toggle.count() && await page.locator('label[for="nav-toggle"]').isVisible()) {
        const before = await toggle.isChecked();
        await page.locator('label[for="nav-toggle"]').click();
        const opened = await toggle.isChecked();
        await page.locator('label[for="nav-toggle"]').click();
        entry.navToggle = { before, opened, after: await toggle.isChecked() };
      } else entry.navToggleNotApplicable = 'Desktop uses the visible navigation; the collapsible trigger is intentionally hidden.';
      const screenshot = `${viewport.width}x${viewport.height}-${file.replace('.html','')}.png`;
      await page.screenshot({ path: path.join(output, screenshot), fullPage: false });
      entry.screenshot = screenshot;
      const o = entry.observed;
      entry.mediaProbes = await page.evaluate(async paths => Promise.all(paths.map(async pathname => {
        const response = await fetch(pathname, { method: 'GET', headers: { Range: 'bytes=0-0' }, cache: 'no-store', credentials: 'omit', redirect: 'error' });
        const sampleBytes = response.status === 206 ? (await response.arrayBuffer()).byteLength : null;
        if (response.status !== 206) await response.body?.cancel();
        return { path: pathname, status: response.status, contentType: response.headers.get('content-type'), contentRange: response.headers.get('content-range'), length: response.headers.get('content-length'), sampleBytes };
      })), [...new Set(o.media.map(media => media.path))]);
      await page.waitForTimeout(100);
      entry.expectedMediaCancellations = entry.failedResources.filter(failure => failure.resourceType === 'media' && failure.error === 'net::ERR_ABORTED' && o.media.some(media => media.path === failure.path && media.readyState >= 1 && !media.error) && entry.mediaProbes.some(probe => probe.path === failure.path && probe.status === 206 && probe.sampleBytes === 1));
      entry.blockingFailedResources = entry.failedResources.filter(failure => !entry.expectedMediaCancellations.includes(failure));
      const exactNav = o.nav.length === 8 && files.every(name => o.nav.some(link => link.path === '/' + name && link.origin === base));
      entry.assertions = {
        http200: entry.httpStatus === 200, meaningfulContent: Boolean(o.title && o.h1 && o.h1Visible && o.mainTextLength > 100), exactEightLocalNavigationLinks: exactNav,
        stylesheetsLoaded: o.stylesheets.length > 0 && o.stylesheets.every(css => css.loaded), imagesLoaded: o.brokenImages.length === 0,
        noHorizontalOverflow: !o.horizontalOverflow, noBlockingJavascriptErrors: entry.pageErrors.length === 0,
        noConsoleErrors: entry.consoleErrors.length === 0, noHttpErrors: entry.httpErrors.length === 0, noBlockingFailedResources: entry.blockingFailedResources.length === 0,
        mediaMetadataAndFilesAvailable: o.media.every(media => media.readyState >= 1 && !media.error && media.duration > 0) && entry.mediaProbes.every(probe => probe.status === 206 && probe.sampleBytes === 1),
        noWriteOrExternalRequests: entry.blockedWrites.length === 0 && entry.blockedExternal.length === 0,
        navOpenCloseWorks: !entry.navToggle || entry.navToggle.before === false && entry.navToggle.opened === true && entry.navToggle.after === false,
        workshopIfExpected: file !== 'about.html' || o.workshopPresent
      };
      entry.status = Object.values(entry.assertions).every(Boolean) ? 'PASS' : 'FAIL';
    } catch (error) { entry.error = clean(error.message); }
    finally {
      entry.finishedAt = new Date().toISOString(); entry.elapsedMs = Math.round(performance.now() - start);
      report.cases.push(entry); await save(); await context.close();
    }
  }
} catch (error) { report.fatal = clean(error.message); }
finally {
  if (browser) await browser.close();
  report.finishedAt = new Date().toISOString();
  report.passed = report.cases.filter(item => item.status === 'PASS').length;
  report.failed = report.cases.filter(item => item.status === 'FAIL').length;
  report.skipped = 0; report.expectedCases = 24;
  report.blockedWrites = report.cases.reduce((n, item) => n + item.blockedWrites.length, 0);
  report.blockedExternal = report.cases.reduce((n, item) => n + item.blockedExternal.length, 0);
  report.status = !report.fatal && report.passed === 24 && report.failed === 0 ? 'PASS' : 'FAIL';
  await save();
  console.log(JSON.stringify({ output, status: report.status, passed: report.passed, failed: report.failed, blockedWrites: report.blockedWrites, blockedExternal: report.blockedExternal, fatal: report.fatal }));
  if (report.status !== 'PASS') process.exitCode = 1;
}
