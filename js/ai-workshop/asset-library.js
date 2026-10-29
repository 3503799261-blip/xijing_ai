import { listWorkbenchModels, listCharacterAssets, getConceptCandidate, ServiceError } from './services.js?v=phase4-1';
import { safeAssetFileUrl, validateAssetIdentifier } from './contracts.js?v=phase4-1';

const STORAGE_KEY = 'xijing.ai.workbench-model.v1';
const STYLES = { chibi: 'Q版卡通', realistic: '写实国风' };
const node = (tag, className, content = '') => { const el = document.createElement(tag); el.className = className; el.textContent = content; return el; };
export function safeCandidateFileUrl(id) {
  try {
    validateAssetIdentifier(id);
    const origin = globalThis.location?.origin || 'http://127.0.0.1:8000';
    const configured = globalThis.document?.querySelector('meta[name="ai-workshop-api-base"]')?.content?.trim() || '/api/v1';
    const base = new URL(configured, origin);
    if (!['http:', 'https:'].includes(base.protocol) || base.username || base.password || base.search || base.hash) return null;
    return `${base.href.replace(/\/$/, '')}/assets/candidates/${id}/file`;
  } catch { return null; }
}
const loopback = () => ['127.0.0.1', 'localhost', '[::1]', '::1'].includes(globalThis.location?.hostname || new URL(globalThis.location?.origin || 'http://127.0.0.1:8000').hostname);

/** Existing records only. No registration, prompt editing, generation or polling. */
export function initializeAssetLibrary({ root, onSelect, onPendingSelected }) {
  const list = root.querySelector('#ai-workshop-asset-library');
  if (!list) return null;
  const status = root.querySelector('#ai-workshop-library-status');
  const refreshButton = root.querySelector('#ai-workshop-library-refresh');
  const selectionStatus = root.querySelector('#ai-workshop-library-selection-status');
  let generation = 0, pending = false, selecting = false, selectedId = null, items = [], cards = new Map();
  let initialSelectionDone = false;
  const setStatus = (message) => { if (status) status.textContent = message; };
  function controls() {
    if (refreshButton) refreshButton.disabled = pending || selecting;
    for (const card of cards.values()) card.disabled = selecting;
  }
  function setSelected(modelId) {
    selectedId = modelId || null;
    for (const [id, card] of cards) card.setAttribute('aria-pressed', String(id === selectedId));
  }
  function remember(item) {
    try { if (item.model) globalThis.sessionStorage?.setItem(STORAGE_KEY, item.model.modelId); } catch { /* Optional identifier only. */ }
    try {
      const url = new URL(globalThis.location.href);
      if (item.model) url.searchParams.set('modelId', item.model.modelId); else url.searchParams.delete('modelId');
      if (item.asset?.assetId) url.searchParams.set('assetId', item.asset.assetId); else url.searchParams.delete('assetId');
      globalThis.window?.history?.replaceState(null, '', url);
    } catch { /* A failed URL preference never changes asset identity. */ }
  }
  async function select(item, explicit = false) {
    if (selecting) return false;
    selecting = true; controls();
    if (selectionStatus) { selectionStatus.hidden = false; selectionStatus.textContent = '正在读取所选资产……'; }
    try {
      const accepted = item.model ? await onSelect(item) : await onPendingSelected(item.asset);
      if (accepted === false) { if (selectionStatus) selectionStatus.textContent = '资产未能读取，请保留原文件并手动重试。'; return false; }
      setSelected(item.model?.modelId || item.asset.assetId);
      if (explicit) remember(item);
      if (selectionStatus) selectionStatus.textContent = item.model?.internalUseOnly
        ? '当前为Q版内部技术模型，仅限本机内部查看。'
        : item.model ? `当前查看：${item.title}` : '当前角色尚未生成对应模型。';
      return true;
    } catch (error) {
      if (selectionStatus) selectionStatus.textContent = error instanceof ServiceError ? error.message : '暂时无法选择该资产，请手动重试。';
      return false;
    } finally { selecting = false; controls(); }
  }
  function buildCard(item) {
    const button = node('button', 'ai-workshop-library-item'); button.type = 'button';
    const id = item.model?.modelId || item.asset.assetId;
    button.dataset.libraryId = id; button.dataset.styleMode = item.styleMode; button.setAttribute('aria-pressed', String(id === selectedId));
    if (item.model) { button.dataset.modelId = item.model.modelId; button.dataset.workbenchModelId = item.model.modelId; }
    else button.className += ' ai-workshop-library-pending';
    const preview = node('span', 'ai-workshop-library-thumbnail');
    if (item.imageUrl) {
      const image = document.createElement('img'); image.src = item.imageUrl; image.alt = `${item.title}的已登记概念图`; image.loading = 'lazy';
      image.addEventListener('error', () => preview.replaceChildren(node('span', 'ai-workshop-library-empty', '概念图暂不可用')));
      preview.append(image, node('span', 'ai-workshop-library-thumbnail-label', '概念图'));
    } else preview.append(node('span', 'ai-workshop-library-empty', '暂无概念图'));
    const copy = node('span', 'ai-workshop-library-item-copy');
    copy.append(node('strong', '', item.title), node('small', '', `${STYLES[item.styleMode] || '风格未标注'} · ${item.model ? '已有3D' : '尚无模型'}`));
    if (item.model?.internalUseOnly) copy.append(node('small', 'ai-workshop-library-internal', '内部技术验证 · 不公开分发'));
    button.append(preview, copy); button.addEventListener('click', () => void select(item, true)); cards.set(id, button); return button;
  }
  async function attachImage(item) {
    const model = item.model;
    if (!model) {
      const image = item.asset.images[0];
      if (image) { item.image = image; item.imageUrl = safeAssetFileUrl(image.fileUrl, 'images', image.imageId); }
      return item;
    }
    if (model.origin === 'neural4d_technical_test') {
      const candidate = await getConceptCandidate(model.candidateId);
      if (candidate.filesAvailable && candidate.hash === model.imageHash && candidate.sourceHash === model.sourceImageHash) {
        item.candidate = candidate; item.imageUrl = safeCandidateFileUrl(candidate.candidateId);
      }
    } else {
      const image = item.asset?.images.find((value) => value.imageId === model.imageId && value.hash === model.imageHash);
      if (image) { item.image = image; item.imageUrl = safeAssetFileUrl(image.fileUrl, 'images', image.imageId); }
    }
    return item;
  }
  async function refresh({ selectDefault = false, preferredAssetId = null } = {}) {
    if (pending || selecting) return;
    const ticket = ++generation; pending = true; controls(); setStatus('正在读取已有数字资产……');
    try {
      const includeInternal = loopback();
      const results = await Promise.allSettled([listWorkbenchModels({ includeInternal }), listCharacterAssets()]);
      if (ticket !== generation) return;
      if (results[0].status === 'rejected') throw results[0].reason;
      const assets = results[1].status === 'fulfilled' ? results[1].value : [];
      const models = results[0].value.models.filter((model) => ['neural4d', 'neural4d_technical_test', 'licensed_import'].includes(model.origin));
      let next = models.map((model) => {
        const asset = assets.find((value) => value.assetId === model.assetId) || null;
        return { model, asset, title: asset?.name || model.title || '已登记模型', styleMode: model.styleMode };
      }).sort((a, b) => Number(a.model.internalUseOnly === true) - Number(b.model.internalUseOnly === true));
      next.push(...assets.filter((asset) => !asset.models.length).map((asset) => ({ asset, model: null, title: asset.name, styleMode: asset.styleMode })));
      const prepared = await Promise.allSettled(next.map(attachImage));
      if (ticket !== generation) return;
      items = prepared.map((result, index) => result.status === 'fulfilled' ? result.value : next[index]);
      cards = new Map(); list.replaceChildren(...items.map(buildCard));
      if (!items.length) list.append(node('p', 'ai-workshop-library-empty', '暂无已登记资产，请从已确认角色开始。'));
      const notices = [];
      if (includeInternal && !results[0].value.internalIncluded) notices.push('请停止并重新启动本地服务，以载入内部模型列表。');
      if (results[1].status === 'rejected') notices.push('角色资料暂不可读，模型仍按实际记录显示。');
      if (prepared.some((result) => result.status === 'rejected')) notices.push('部分概念图未能读取，不影响选择原GLB。');
      setStatus(`${models.length}个已有模型${assets.filter((asset) => !asset.models.length).length ? '，另有待补充模型的角色' : ''}。${notices.join(' ')}`);
      let explicitModel = null;
      try { explicitModel = new URLSearchParams(globalThis.location?.search || '').get('modelId'); } catch { /* Optional deep link only. */ }
      if (selectDefault && !initialSelectionDone && (!selectedId || explicitModel)) {
        let linkedModel = null, linkedAsset = preferredAssetId, remembered = null;
        try { const query = new URLSearchParams(globalThis.location?.search || ''); linkedModel = query.get('modelId'); linkedAsset = query.get('assetId') || linkedAsset; remembered = globalThis.sessionStorage?.getItem(STORAGE_KEY); } catch { /* No hidden fallback creation. */ }
        const chosen = items.find((item) => item.model?.modelId === linkedModel)
          || items.find((item) => item.asset?.assetId === linkedAsset)
          || (!linkedAsset && items.find((item) => item.model?.modelId === remembered))
          || items.find((item) => item.model);
        initialSelectionDone = true;
        if (chosen) await select(chosen);
      }
      setSelected(selectedId);
    } catch (error) {
      setStatus(`${error instanceof ServiceError ? error.message : '资产库暂时无法读取。'}${items.length ? ' 目前仅保留上次读取的快照。' : ' 点击刷新重试，不会生成新模型。'}`);
    } finally { if (ticket === generation) { pending = false; controls(); } }
  }
  refreshButton?.addEventListener('click', () => void refresh());
  return { refresh, setSelected };
}
