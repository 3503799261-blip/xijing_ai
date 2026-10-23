// Private local browser audit. GET/HEAD only, no business mutations/provider calls.
import { createRequire } from 'node:module';
import fs from 'node:fs/promises';
import path from 'node:path';
const req = createRequire(process.env.XIJING_PLAYWRIGHT_PACKAGE);
const { chromium } = req('playwright');
const output = process.argv[2];
if (!output || !path.resolve(output).startsWith('D:\\京剧\\.runtime\\productization-')) throw new Error('Fresh private output required');
await fs.mkdir(output, { recursive: false });
const base = 'http://127.0.0.1:8000';
const result = { kind: 'REAL_BROWSER_READ_ONLY_NAV_AND_LAYOUT', startedAt: new Date().toISOString(), phase: process.argv[3] || 'before', realPaidCalls: 0, neural4dCalls: 0, contexts: [], tests: [], screenshots: [], physicalPhone: 'NOT_TESTED' };
const cleanPath = value => { try { return new URL(value).pathname; } catch { return '[invalid]'; } };
let browser;
try {
 browser = await chromium.launch({ channel: 'chrome', headless: true });
 for (const viewport of [{width:1920,height:1080},{width:1024,height:768},{width:390,height:844}]) {
  const context = await browser.newContext({ viewport, serviceWorkers: 'block' });
  const log = { viewport, pageErrors: [], consoleErrors: [], blockedMutations: [], blockedExternal: [], httpErrors: [], failedResources: [] };
  result.contexts.push(log);
  await context.route('**/*', async route => {
   const r = route.request(), u = new URL(r.url());
   if (!['GET','HEAD'].includes(r.method())) { log.blockedMutations.push({method:r.method(),path:u.pathname}); return route.abort('blockedbyclient'); }
   if (['http:','https:'].includes(u.protocol) && u.origin !== base) { log.blockedExternal.push({origin:u.origin,path:u.pathname}); return route.abort('blockedbyclient'); }
   return route.continue();
  });
  const page = await context.newPage();
  page.on('pageerror', e => log.pageErrors.push(e.message.slice(0,300)));
  page.on('console', m => { if (m.type() === 'error') log.consoleErrors.push(m.text().replace(/https?:\/\/[^\s"']+/g,cleanPath).slice(0,300)); });
  page.on('response', r => { if(r.status()>=400) log.httpErrors.push({path:cleanPath(r.url()),status:r.status()}); });
  page.on('requestfailed', r => log.failedResources.push({path:cleanPath(r.url()),error:r.failure()?.errorText}));
  for (const file of ['index.html','history.html','roles.html','facial.html','music.html','gallery.html','video.html','about.html']) {
   const response = await page.goto(`${base}/${file}`,{waitUntil:'domcontentloaded',timeout:30000});
   await page.waitForFunction(() => [...document.images].every(i => i.complete),null,{timeout:15000});
   await page.waitForTimeout(file==='about.html'?1500:150);
   const observed = await page.evaluate(() => {
    const rect = selector => { const e=document.querySelector(selector); if(!e)return null; const r=e.getBoundingClientRect(),s=getComputedStyle(e); return { x:r.x,y:r.y,width:r.width,height:r.height,gap:s.gap,padding:s.padding,fontSize:s.fontSize,display:s.display }; };
    return { title:document.title, navWrap:rect('.nav-wrap'), navList:rect('.nav-list'), firstNavLink:rect('.nav-list a'), navLinks:[...document.querySelectorAll('.nav-list a')].map(a=>({text:a.textContent.trim(),href:a.getAttribute('href'),width:a.getBoundingClientRect().width,scrollWidth:a.scrollWidth,clientWidth:a.clientWidth})), horizontalOverflow:document.documentElement.scrollWidth>innerWidth+1, brokenImages:[...document.images].filter(i=>(i.currentSrc||i.src)&&i.naturalWidth===0).map(i=>new URL(i.currentSrc||i.src).pathname), visiblePanels:[...document.querySelectorAll('[data-ai-workshop-panel]')].filter(e=>!e.hidden).map(e=>e.dataset.aiWorkshopPanel), messageArea:rect('#ai-workshop-messages'), inputArea:rect('#ai-workshop-question-form') };
   });
   result.tests.push({ file, viewport, status:response.status(), ...observed, pass:response.status()===200&&observed.brokenImages.length===0&&observed.navLinks.length===8&&!observed.horizontalOverflow });
   if(['index.html','about.html'].includes(file)) { const name=`${file.replace('.html','')}-${viewport.width}x${viewport.height}.png`; await page.screenshot({path:path.join(output,name),fullPage:false}); result.screenshots.push(name); }
  }
  await context.close();
 }
} catch(error) { result.error=error.message.slice(0,500); }
finally {
 if(browser)await browser.close();
 result.completedAt=new Date().toISOString(); result.passed=result.tests.filter(t=>t.pass).length; result.failed=result.tests.filter(t=>!t.pass).length; result.skipped=0; result.conclusion=!result.error&&result.failed===0&&result.tests.length===24?'PASS':'FAIL';
 await fs.writeFile(path.join(output,'browser-nav-result.json'),JSON.stringify(result,null,2)+'\n');
 console.log(JSON.stringify({conclusion:result.conclusion,passed:result.passed,failed:result.failed,error:result.error,navs:result.tests.filter(t=>t.file==='about.html').map(t=>({viewport:t.viewport,navWrap:t.navWrap.width,navList:t.navList.width}))}));
}
if(result.conclusion!=='PASS')process.exitCode=1;
