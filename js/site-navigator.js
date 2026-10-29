/** Free local content navigation. No API, generated answer or business submission. */
export const PENDING_QUESTION_KEY = 'xijing.pending-navigation-question.v1';
const LAST_QUERY = 'xijing.navigation-query.v1';
const topic = (id, title, href, aliases, bind = null) => ({ id, title, href, aliases, bind });
export const TOPICS = [
  topic('history', '京剧发展历史', 'history.html', ['发展历史', '京剧历史', '京剧起源', '起源', '诞生', '历史']),
  topic('origin', '徽班进京', 'history.html#site-origin', ['徽班进京', '徽班', '四大徽班'], { heading: '徽班进京' }),
  topic('mei', '梅兰芳', 'history.html#site-mei', ['梅兰芳', '梅派'], { heading: '梅兰芳' }),
  topic('cheng', '程砚秋', 'history.html#site-cheng', ['程砚秋', '程派'], { heading: '程砚秋' }),
  topic('tan', '谭鑫培', 'history.html#site-tan', ['谭鑫培', '谭派'], { heading: '谭鑫培' }),
  topic('roles', '生旦净丑与行当', 'roles.html', ['生旦净丑', '行当', '角色分类']),
  topic('sheng', '生行：老生、小生、武生', 'roles.html#sheng', ['生', '生角', '生行', '老生', '小生', '武生']),
  topic('dan', '旦行：青衣、花旦、武旦', 'roles.html#dan', ['旦', '旦角', '旦行', '青衣', '花旦', '武旦', '老旦', '刀马旦']),
  topic('jing', '净行与花脸', 'roles.html#jing', ['净', '净角', '净行', '花脸', '铜锤花脸', '架子花脸']),
  topic('chou', '丑行与诙谐表演', 'roles.html#chou', ['丑', '丑角', '丑行', '文丑', '武丑', '小花脸']),
  topic('facial', '脸谱艺术与颜色', 'facial.html', ['脸谱', '脸谱颜色', '脸谱寓意', '脸谱含义', '红脸', '黑脸', '白脸']),
  topic('music', '唱腔与乐器', 'music.html', ['唱腔', '声腔', '乐器', '伴奏', '音乐']),
  topic('xipi', '西皮唱腔', 'music.html#site-xipi', ['西皮'], { heading: '西皮' }),
  topic('erhuang', '二黄唱腔', 'music.html#site-erhuang', ['二黄'], { heading: '二黄' }),
  topic('jinghu', '京胡', 'music.html#site-jinghu', ['京胡'], { heading: '京胡 · 一弓一弦托唱腔' }),
  topic('percussion', '锣鼓与武场节奏', 'music.html#site-percussion', ['锣鼓', '锣鼓经', '打击乐', '武场'], { selector: '.percussion' }),
  topic('audio', '京剧唱段欣赏', 'music.html#site-audio', ['听京剧', '听唱段', '听歌', '音频', '唱段欣赏'], { selector: 'audio', closest: 'section' }),
  topic('video', '视频欣赏', 'video.html', ['视频', '看戏', '演出录像', '唱段视频']),
  topic('gallery', '艺术画廊', 'gallery.html', ['艺术画廊', '画廊', '图片', '相册']),
  topic('costume', '戏服与扮相', 'gallery.html#costumes', ['服饰', '服装', '戏服', '水袖', '凤冠', '头饰', '盔头', '刺绣']),
  topic('photos', '名家照片', 'gallery.html#actors', ['演员照片', '名家照片', '演员风采']),
  topic('stage', '数字戏台 · 交互3D', 'about.html#ai-workshop-stage', ['数字戏台', '3d舞台', '3d模型', '数字人物', '数字模型', '三维', '舞台', '3d', '模型']),
  topic('duliniang', '数字戏台 · 杜丽娘', 'about.html?stageGroup=mudanting#ai-workshop-stage', ['杜丽娘', '牡丹亭']),
  topic('muguiying', '数字戏台 · 穆桂英', 'about.html?stageGroup=muguiying#ai-workshop-stage', ['穆桂英', '挂帅', '杨家将']),
  topic('zhouyu', '数字戏台 · 周瑜', 'about.html?stageGroup=qunyinghui#ai-workshop-stage', ['周瑜', '群英会']),
  topic('qa', '京剧知识问答', 'about.html#ai-workshop-qa', ['京剧问答', '智能问答', '问答', '聊天', '提问', 'ai工坊', 'ai戏韵工坊']),
  topic('home', '认识京剧', 'index.html#culture', ['首页', '京剧', '文化介绍', '认识京剧']),
];
export function findDestinations(value) {
  if (typeof value !== 'string' || value.trim().length > 120) return [];
  const query = value.normalize('NFKC').toLowerCase().replace(/[\s\p{P}\p{S}]/gu, '');
  if (!query) return [];
  return TOPICS.map((entry) => {
    let score = 0;
    for (const text of entry.aliases) {
      const alias = text.normalize('NFKC').toLowerCase();
      if (query === alias) score = Math.max(score, 100 + alias.length);
      else if (alias.length >= 2 && query.includes(alias)) score = Math.max(score, alias.length * 10);
    }
    const exact = entry.aliases.some((value) => value.normalize('NFKC').toLowerCase() === query);
    if (!exact && ['home', 'roles', 'music', 'gallery', 'stage'].includes(entry.id)) score *= 0.5;
    return { ...entry, score };
  }).filter((item) => item.score).sort((a, b) => b.score - a.score);
}
const element = (tag, text = '', className = '') => { const node = document.createElement(tag); node.textContent = text; node.className = className; return node; };
function stored(key) { try { return sessionStorage.getItem(key); } catch { return null; } }
function store(key, value) { try { sessionStorage.setItem(key, value); } catch { /* Optional local draft only. */ } }
function locateAnchors() {
  const current = location.pathname.split('/').pop() || 'index.html';
  for (const entry of TOPICS) {
    const target = new URL(entry.href, location.href);
    if (!entry.bind || target.pathname.split('/').pop() !== current || !target.hash) continue;
    const id = target.hash.slice(1); if (document.getElementById(id)) continue;
    let found = entry.bind.selector ? document.querySelector(entry.bind.selector) : [...document.querySelectorAll('main h2, main h3')].find((node) => node.textContent.replace(/\s+/g, ' ').trim() === entry.bind.heading);
    if (found && entry.bind.closest) found = found.closest(entry.bind.closest);
    if (found) { found.id = id; found.classList.add('xijing-navigation-target'); }
  }
}
export function initializeSiteNavigator() {
  if (document.querySelector('#xijing-direct-nav')) return;
  locateAnchors();
  const dock = element('aside', '', 'xijing-direct-nav'); dock.id = 'xijing-direct-nav'; dock.setAttribute('aria-label', '站内内容直达');
  const form = element('form', '', 'xijing-direct-form'); form.setAttribute('role', 'search');
  const label = element('label', '想了解什么？'); label.htmlFor = 'xijing-direct-query';
  const input = element('input'); input.id = 'xijing-direct-query'; input.type = 'search'; input.maxLength = 120;
  input.placeholder = '输入脸谱、武生、周瑜…按回车前往'; input.autocomplete = 'off'; input.value = stored(LAST_QUERY) || '';
  input.setAttribute('aria-describedby', 'xijing-direct-feedback');
  const submit = element('button', '前往'); submit.type = 'submit';
  const feedback = element('div', '', 'xijing-direct-feedback'); feedback.id = 'xijing-direct-feedback'; feedback.hidden = true; feedback.setAttribute('role', 'status'); feedback.setAttribute('aria-live', 'polite');
  const message = element('p'); const alternatives = element('div', '', 'xijing-direct-alternatives');
  const ask = element('button', '去京剧问答'); ask.type = 'button';
  function jump(entry) {
    const target = new URL(entry.href, location.href);
    if (target.origin !== location.origin || !/\/(?:index|history|roles|facial|music|video|gallery|about)\.html$/.test(target.pathname)) return;
    location.assign(target.href);
    if (target.pathname === location.pathname && target.search === location.search) requestAnimationFrame(scrollToTarget);
  }
  function sendToQuestion() {
    const question = input.value.trim(); if (!question || question.length > 120) return;
    store(PENDING_QUESTION_KEY, question);
    const target = new URL('about.html#ai-workshop-qa', location.href);
    if (location.pathname === target.pathname) {
      location.hash = target.hash;
      window.dispatchEvent(new CustomEvent('xijing:prefill-question', { detail: { question } }));
      feedback.hidden = false; message.textContent = '问题已带入问答输入框，请确认后自行发送。'; alternatives.replaceChildren();
    } else location.assign(target.href);
  }
  ask.addEventListener('click', sendToQuestion);
  form.addEventListener('submit', (event) => {
    event.preventDefault(); const query = input.value.trim(); alternatives.replaceChildren();
    if (!query) { feedback.hidden = false; message.textContent = '请先输入想了解的内容。'; input.focus(); return; }
    if (query.length > 120) { feedback.hidden = false; message.textContent = '请缩短到120字以内。'; return; }
    store(LAST_QUERY, query);
    const matches = findDestinations(query), first = matches[0];
    if (first && (!matches[1] || first.score > matches[1].score)) { jump(first); return; }
    feedback.hidden = false;
    message.textContent = first ? '找到了几个相关位置，请选择：' : '没有找到明确栏目。可试试“脸谱”“京胡”“周瑜”，或将问题带入京剧问答。';
    for (const item of matches.slice(0, 4)) { const button = element('button', item.title); button.type = 'button'; button.addEventListener('click', () => jump(item)); alternatives.append(button); }
    alternatives.append(ask);
  });
  input.addEventListener('input', () => { feedback.hidden = true; });
  input.addEventListener('keydown', (event) => { if (event.key === 'Escape') { feedback.hidden = true; input.blur(); } });
  form.append(label, input, submit); feedback.append(message, alternatives); dock.append(feedback, form); document.body.append(dock); document.body.classList.add('xijing-has-direct-nav');
  const measure = () => document.documentElement.style.setProperty('--xijing-header-height', `${document.querySelector('.site-header')?.getBoundingClientRect().height || 82}px`);
  measure(); const header = document.querySelector('.site-header'); if (header && globalThis.ResizeObserver) new ResizeObserver(measure).observe(header);
  function scrollToTarget() {
    if (!location.hash || location.hash.startsWith('#ai-workshop')) return;
    let id; try { id = decodeURIComponent(location.hash.slice(1)); } catch { return; }
    const target = document.getElementById(id);
    if (target) { target.classList.add('xijing-navigation-target'); measure(); target.scrollIntoView({ block: 'start', behavior: 'instant' }); }
  }
  window.addEventListener('hashchange', scrollToTarget); requestAnimationFrame(scrollToTarget);
}
if (typeof document !== 'undefined') {
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initializeSiteNavigator, { once: true });
  else initializeSiteNavigator();
}
