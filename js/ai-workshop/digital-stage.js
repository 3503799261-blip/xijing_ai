import { safeCitationUrl } from './contracts.js?v=phase4-1';

const LABELS = { idle: '尚未加载', loading: '正在加载', ready: '可以交互', error: '暂不可用' };
const IDENTIFIER = /^[A-Za-z0-9_-]{1,80}$/;
const validId = (value) => typeof value === 'string' && IDENTIFIER.test(value);
const node = (tag, className, text = '') => { const el = document.createElement(tag); el.className = className; el.textContent = text; return el; };

function apiBase() {
  const configured = globalThis.document?.querySelector('meta[name="ai-workshop-api-base"]')?.content?.trim() || '/api/v1';
  const base = new URL(configured, globalThis.location?.origin || 'http://127.0.0.1:8000');
  if (!['http:', 'https:'].includes(base.protocol) || base.username || base.password || base.search || base.hash) throw new Error('戏台服务地址配置无效，请检查页面配置。');
  return base;
}

/** The renderer only receives the exact ID-based file endpoint from this API. */
export function safeStageFileUrl(value, id) {
  if (typeof value !== 'string' || !validId(id)) return null;
  try {
    const base = apiBase();
    const expected = new URL(`${base.href.replace(/\/$/, '')}/stage/files/${id}`);
    const actual = new URL(value, base.origin);
    if (actual.href !== expected.href || actual.username || actual.password || actual.search || actual.hash) return null;
    return actual.href;
  } catch { return null; }
}

export function validateStageCatalog(body) {
  if (!body || typeof body !== 'object' || !Array.isArray(body.characters) || !Array.isArray(body.groups)
      || body.characters.length > 50 || body.groups.length > 50) throw new Error('戏台资料格式不正确，请重新读取或检查本地资源。');
  const groups = body.groups.map((item) => {
    if (!item || !validId(item.id) || typeof item.name !== 'string' || !item.name.trim() || item.name.length > 160) throw new Error('戏台分类资料不完整。');
    return { id: item.id, name: item.name, description: typeof item.description === 'string' ? item.description.slice(0, 1200) : '' };
  });
  if (new Set(groups.map((group) => group.id)).size !== groups.length) throw new Error('戏台分类标识重复，请检查资料。');
  const cleanFile = (item, kind) => {
    if (!item || !validId(item.id) || typeof item.name !== 'string' || !item.name.trim() || item.name.length > 160 || typeof item.available !== 'boolean') throw new Error('戏台模型资料不完整。');
    const url = item.fileUrl ? safeStageFileUrl(item.fileUrl, item.id) : null;
    if (item.available && !url) throw new Error('戏台模型地址未通过安全检查。');
    return { ...item, fileUrl: url, kind };
  };
  const stage = body.stage ? cleanFile(body.stage, 'stage') : null;
  const characters = body.characters.map((item) => {
    const result = cleanFile(item, 'character');
    if (typeof item.groupId !== 'string' || !groups.some((group) => group.id === item.groupId)) throw new Error('人物所属分类不存在，请检查戏台资料。');
    return { ...result, description: typeof item.description === 'string' ? item.description.slice(0, 4000) : '',
      question: typeof item.question === 'string' ? item.question.slice(0, 600) : `请介绍${item.name}的戏曲文化背景，并说明资料来源。`,
      citations: Array.isArray(item.citations) ? item.citations.slice(0, 12).filter((cite) => cite && typeof cite.title === 'string').map((cite) => ({ title: cite.title.slice(0, 300), url: safeCitationUrl(cite.url), excerpt: typeof cite.excerpt === 'string' ? cite.excerpt.slice(0, 2000) : '' })) : [] };
  });
  if (new Set(characters.map((item) => item.id)).size !== characters.length) throw new Error('戏台人物标识重复，请检查资料。');
  return { ...body, stage, groups, characters };
}

/** Free local GET only. No paid provider, generation, task creation or polling. */
export async function loadStageCatalog() {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);
  try {
    const base = apiBase();
    const response = await fetch(`${base.href.replace(/\/$/, '')}/stage/catalog`, { method: 'GET', headers: { Accept: 'application/json' }, credentials: 'omit', cache: 'no-store', signal: controller.signal });
    let body;
    try { body = await response.json(); }
    catch { throw new Error('戏台服务返回了无法读取的资料，请手动重试。'); }
    if (!response.ok) throw new Error(response.status === 404 ? '戏台资源尚未就绪，请确认已启动最新版本服务。' : response.status === 503 ? '本地戏台资源尚未准备好，请按运行说明恢复资源后重试。' : `戏台暂时无法读取（HTTP ${response.status}），请稍后手动重试。`);
    return validateStageCatalog(body);
  } catch (error) {
    if (controller.signal.aborted) throw new Error('读取戏台资料超时，请检查本地服务后手动重试。');
    if (error instanceof TypeError) throw new Error('暂时无法连接本地戏台，请确认项目已经启动。');
    throw error;
  } finally { clearTimeout(timeout); }
}

/** UI and renderer are isolated from chat and the existing asset-creation path. */
export function initializeDigitalStage({ root, onAskQuestion, catalogLoader = loadStageCatalog,
  viewerLoader = () => import('./stage-viewer.js?v=stage-1') }) {
  const byId = (name) => root.querySelector(`#ai-workshop-stage-${name}`);
  const host = byId('host');
  if (!host) return null;
  const elements = Object.fromEntries(['group', 'group-description', 'characters', 'viewer-title', 'state', 'status', 'error', 'refresh', 'reload', 'zoom-in', 'zoom-out', 'reset', 'character-name', 'character-group', 'character-description', 'ask', 'question-note', 'citations'].map((id) => [id, byId(id)]));
  let catalog = null, renderer = null, selectedId = null, groupId = null, visible = false, catalogPending = false, scenePending = false, ticket = 0;
  let state = 'idle', sceneSignature = null;
  const selected = () => catalog?.characters.find((character) => character.id === selectedId);
  const groupCharacters = () => catalog?.characters.filter((character) => character.groupId === groupId) || [];
  function controls() {
    const busy = catalogPending || scenePending;
    elements.refresh.disabled = busy; elements.group.disabled = busy || !catalog?.groups.length;
    elements.characters.querySelectorAll('button').forEach((button) => { button.disabled = busy; });
    ['zoom-in', 'zoom-out', 'reset'].forEach((name) => { elements[name].disabled = state !== 'ready' || busy; });
    elements.ask.disabled = !selected() || typeof onAskQuestion !== 'function';
    elements.reload.disabled = busy;
  }
  function renderState(value, message = '') {
    state = Object.hasOwn(LABELS, value) ? value : 'error';
    host.dataset.stageState = state;
    elements.state.textContent = LABELS[state]; elements.state.dataset.state = state;
    host.setAttribute('aria-busy', String(state === 'loading'));
    elements.status.textContent = message || (state === 'ready' ? '舞台已就绪，拖动旋转或点击人物。' : state === 'loading' ? '正在加载舞台与人物，请稍候……' : '选择分类开始查看。');
    elements.error.hidden = state !== 'error';
    elements.error.textContent = state === 'error' ? (message || '场景加载未完成，请检查已有模型文件后重试。') : '';
    elements.reload.hidden = state !== 'error';
    controls();
  }
  function showCharacter(id, focusInScene = true) {
    const character = catalog?.characters.find((item) => item.id === id && item.groupId === groupId);
    if (!character) return;
    selectedId = character.id;
    elements['character-name'].textContent = character.name;
    elements['character-group'].textContent = catalog.groups.find((group) => group.id === character.groupId)?.name || '待分类';
    elements['viewer-title'].textContent = `${elements['character-group'].textContent} · ${character.name}`;
    elements['character-description'].textContent = character.description || '暂未登记人物介绍。可以进入京剧问答，依据资料进一步了解。';
    elements['question-note'].textContent = `带入问题：${character.question}`;
    elements.citations.replaceChildren(...character.citations.map((cite) => {
      const item = node('article', 'ai-workshop-stage-source'); item.append(node('strong', '', cite.title));
      if (cite.excerpt) item.append(node('p', '', cite.excerpt));
      if (cite.url) { const link = node('a', '', '查看来源 ↗'); link.href = cite.url; link.target = '_blank'; link.rel = 'noopener noreferrer'; item.append(link); }
      return item;
    }));
    if (!character.citations.length) elements.citations.append(node('p', 'ai-workshop-stage-muted', '暂未登记可核查来源；人物名称按用户提供文件记录，造型不作为文化事实依据。'));
    elements.characters.querySelectorAll('button').forEach((button) => button.setAttribute('aria-pressed', String(button.dataset.stageCharacterId === id)));
    if (focusInScene && character.available && renderer) renderer.selectCharacter(id);
    controls();
  }
  function populateCharacters() {
    const characters = groupCharacters();
    elements.characters.replaceChildren(...characters.map((character) => {
      const button = node('button', 'ai-workshop-stage-character'); button.type = 'button'; button.dataset.stageCharacterId = character.id;
      button.setAttribute('aria-pressed', String(selectedId === character.id));
      const copy = node('span', ''); copy.append(node('strong', '', character.name), node('small', '', character.available ? '已保存的3D人物' : '模型资源暂不可用'));
      button.append(node('span', '', character.name.slice(0, 1)), copy);
      button.addEventListener('click', () => { showCharacter(character.id); if (!character.available) renderState('error', '这位人物的本地模型暂不可用，请恢复对应已有文件后重新读取。'); });
      return button;
    }));
    if (!characters.length) elements.characters.append(node('p', 'ai-workshop-stage-muted', '此分类暂无已登记人物。'));
    elements['group-description'].textContent = catalog?.groups.find((group) => group.id === groupId)?.description || '';
    const character = characters.find((item) => item.id === selectedId) || characters.find((item) => item.available) || characters[0];
    if (character) showCharacter(character.id, false);
    else { selectedId = null; elements['character-name'].textContent = '暂无人物'; elements['character-group'].textContent = ''; elements['character-description'].textContent = '此分类尚无已保存人物，请选择其他分类。'; elements.citations.replaceChildren(); controls(); }
  }
  async function showScene({ force = false } = {}) {
    if (!visible || !catalog) return;
    const current = ++ticket;
    const characters = groupCharacters().filter((item) => item.available);
    if (!catalog.stage?.available) { scenePending = false; renderState('error', '舞台模型暂不可用，请恢复已转换的舞台文件后重新读取。'); return; }
    if (!characters.length) { scenePending = false; renderState('error', '此分类暂无可加载的人物模型，请选择其他分类。'); return; }
    const signature = JSON.stringify([catalog.stage.id, catalog.stage.sha256, characters.map((item) => [item.id, item.sha256])]);
    if (!force && sceneSignature === signature && state === 'ready' && renderer) { renderer.setVisible?.(visible); if (selectedId) renderer.selectCharacter(selectedId); return; }
    scenePending = true; renderState('loading', '正在加载舞台与人物，首次读取需要一点时间……');
    try {
      if (!renderer) {
        const module = await viewerLoader();
        if (current !== ticket) return;
        renderer = module.initializeStageViewer({ host, onState(value, message) { renderState(value, message); }, onCharacterPick(id) { showCharacter(id, false); } });
      }
      renderer.setVisible?.(visible);
      await renderer.loadScene({ stage: catalog.stage, characters });
      if (current !== ticket) return;
      sceneSignature = signature;
      if (selectedId) renderer.selectCharacter(selectedId);
    } catch (error) {
      if (current === ticket) renderState('error', '场景加载未完成。请检查本地模型与浏览器3D支持，再手动重试。');
    } finally { if (current === ticket) { scenePending = false; controls(); } }
  }
  async function refresh() {
    if (catalogPending || scenePending) return;
    catalogPending = true; renderState('loading', '正在读取已有戏台与人物资料……');
    try {
      const next = await catalogLoader();
      catalog = next;
      const prior = groupId;
      const requested = new URLSearchParams(globalThis.location?.search || '').get('stageGroup');
      groupId = next.groups.some((group) => group.id === prior) ? prior : next.groups.some((group) => group.id === requested) ? requested : next.groups[0]?.id || null;
      elements.group.replaceChildren(...next.groups.map((group) => { const option = node('option', '', group.name); option.value = group.id; return option; }));
      if (!next.groups.length) { const option = node('option', '', '暂无分类'); option.value = ''; elements.group.append(option); }
      elements.group.value = groupId || '';
      populateCharacters();
      await showScene({ force: true });
    } catch (error) { renderState('error', error instanceof Error ? error.message : '戏台资料暂时无法读取，请手动重试。'); }
    finally { catalogPending = false; controls(); }
  }
  elements.group.addEventListener('change', () => { groupId = elements.group.value; selectedId = null; populateCharacters(); void showScene(); });
  elements.refresh.addEventListener('click', () => void refresh());
  elements.reload.addEventListener('click', () => { if (catalog) void showScene({ force: true }); else void refresh(); });
  elements['zoom-in'].addEventListener('click', () => { if (state === 'ready') renderer?.zoom(0.8); });
  elements['zoom-out'].addEventListener('click', () => { if (state === 'ready') renderer?.zoom(1.25); });
  elements.reset.addEventListener('click', () => { if (state === 'ready') renderer?.reset(); });
  elements.ask.addEventListener('click', () => { const character = selected(); if (character && typeof onAskQuestion === 'function') onAskQuestion(character.question); });
  return {
    async setVisible(value) { visible = Boolean(value); renderer?.setVisible?.(visible); if (!visible) return; if (!catalog) await refresh(); else if (!scenePending && !catalogPending) await showScene(); },
    refresh,
  };
}
