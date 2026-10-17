import { createRequire } from 'node:module';
import fs from 'node:fs/promises';
const require = createRequire('C:/Users/35037/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/package.json');
const { chromium } = require('playwright');
const output = 'D:/京剧/.runtime/phase4-final-internal-states';
const origin = 'http://127.0.0.1:8000';
const modelId = '3777a880-fc8c-4766-aade-948d20c6b8f0';
const filePath = `/api/v1/assets/models/${modelId}/file`;
await fs.mkdir(output, { recursive: true });
const result = { startedAt: new Date().toISOString(), modelId, paidCallsAllowed: false, physicalMobileTested: false, tests: {}, requests: [], pageErrors: [] };
const browser = await chromium.launch({ executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: true, args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
result.chromeVersion = browser.version();
async function setup(intercept) {
  const context = await browser.newContext({ viewport: { width: 1920, height: 1080 }, serviceWorkers: 'block' });
  await context.route('**/*', async route => {
    const req = route.request(), url = new URL(req.url());
    result.requests.push({ method: req.method(), path: url.pathname });
    if (!['GET', 'HEAD'].includes(req.method()) || (['http:', 'https:'].includes(url.protocol) && url.origin !== origin)) throw new Error('Only local GET/HEAD allowed');
    if (url.pathname === filePath) return intercept(route);
    return route.continue();
  });
  const page = await context.newPage(); page.on('pageerror', e => result.pageErrors.push(e.message));
  return { page, context };
}
try {
  let release;
  const pending = new Promise(resolve => { release = resolve; });
  const {page, context} = await setup(async route => { await pending; return route.continue(); });
  try {
    await page.goto(`${origin}/api/v1/assets/internal-models/${modelId}/viewer`, {waitUntil: 'domcontentloaded'});
    await page.waitForFunction(() => document.querySelector('#ai-workshop-viewer-host')?.dataset.viewerState === 'loading');
    result.tests.loading = { pass: true, text: await page.locator('#ai-workshop-viewer-status').innerText(), delayedOnlyOriginalGlb: true };
    await page.locator('#ai-workshop-viewer-host').scrollIntoViewIfNeeded(); await page.screenshot({path: `${output}/18-first-internal-loading.png`});
    release();
    await page.waitForFunction(() => document.querySelector('#ai-workshop-viewer-host')?.dataset.viewerState === 'ready', null, {timeout: 45000});
    const text = await page.locator('body').innerText();
    result.tests.postFixHint = { pass: text.includes('人工验收结论以项目阶段报告为准') && !text.includes('人工验收尚未完成'), change: 'Neutral report-based acceptance guidance; internal-only scope preserved' };
    result.tests.loadingToReady = {pass: true};
    await page.screenshot({path: `${output}/19-first-internal-ready-after-hint-fix.png`});
  } finally { release(); await context.close(); }
  let fail = true;
  const second = await setup(route => fail ? route.abort('failed') : route.continue());
  try {
    await second.page.goto(`${origin}/api/v1/assets/internal-models/${modelId}/viewer`, {waitUntil: 'domcontentloaded'});
    await second.page.waitForFunction(() => document.querySelector('#ai-workshop-viewer-host')?.dataset.viewerState === 'error');
    result.tests.error = { pass: await second.page.locator('#ai-workshop-viewer-error').isVisible(), text: await second.page.locator('#ai-workshop-viewer-error').innerText(), injectedFailure: true };
    await second.page.locator('#ai-workshop-viewer-host').scrollIntoViewIfNeeded(); await second.page.screenshot({path: `${output}/20-first-internal-error.png`});
    fail = false;
    await second.page.locator('#ai-workshop-viewer-reload').click();
    await second.page.waitForFunction(() => document.querySelector('#ai-workshop-viewer-host')?.dataset.viewerState === 'ready', null, {timeout: 45000});
    result.tests.recovery = { pass: true, reloadedOriginalOnly: true, noNewModelCreated: true };
    await second.page.screenshot({path: `${output}/21-first-internal-error-recovered.png`});
  } finally { await second.context.close(); }
} catch(e) { result.fatal = String(e.message); }
finally {
  await browser.close(); result.finishedAt = new Date().toISOString();
  result.allPassed = !result.fatal && result.pageErrors.length === 0 && Object.values(result.tests).every(v => v.pass);
  result.onlyLocalGetHead = result.requests.every(v => ['GET','HEAD'].includes(v.method));
  await fs.writeFile(`${output}/post-hint-internal-browser.json`, JSON.stringify(result, null, 2));
  console.log(JSON.stringify({allPassed: result.allPassed, tests: result.tests, fatal: result.fatal, onlyLocalGetHead: result.onlyLocalGetHead}, null, 2));
  if (!result.allPassed) process.exitCode = 1;
}
