import { createCharacterAsset, getCharacterAsset, approveVisualPrompt, uploadAssetImage, acceptAssetImage,
  listCharacterAssets, createPromptVersion, listAssetModels, getAssetUsage, importLicensedModel, ServiceError } from './services.js?v=phase4-1';
import { safeAssetFileUrl, safeCitationUrl, validateAssetIdentifier } from './contracts.js?v=phase4-1';
import { initializeModelViewer } from './model-viewer-adapter.js?v=phase4-1';
import { initializeAssetLibrary } from './asset-library.js?v=workbench-1';

const ASSET_STORAGE_KEY = 'xijing.ai.asset.v1';
const STYLE_LABELS = { chibi: 'Q版卡通', realistic: '写实国风' };
const text = (tag, className, value) => {
  const node = document.createElement(tag); if (className) node.className = className; node.textContent = value; return node;
};

export function enterpriseRequirements(brief) {
  const labels = { organizationType: '机构类型', audience: '受众', useCase: '使用场景', designGoal: '设计目标', culturalBoundaries: '文化边界', deliveryScope: '交付范围', licenseStatus: '授权状态' };
  const enums = { game: '游戏公司', tourism: '文旅机构', ip_design: 'IP设计服务', other: '其他机构', unverified: '商用授权待核查', user_authorized: '用户确认自有授权（供应商许可仍需核查）' };
  const value = Object.entries(labels).map(([key, label]) => `${label}：${enums[brief[key]] || brief[key]?.trim() || ''}`).join('\n');
  if (!value.trim() || value.length > 1200) throw new TypeError('企业需求超过1200字，请缩短后再交给Agent。');
  return value;
}

/** Local asset operations only. Provider verification, model creation, polling and download creation never run here. */
export function initializeDigitalAssets({ root, selectPanel }) {
  const find = (name) => root.querySelector(`#ai-workshop-${name}`);
  const form = find('asset-form');
  if (!form) return null;
  const feedback = find('asset-feedback');
  const sourceTask = find('asset-source-task');
  const mode = find('asset-mode');
  const styleMode = find('asset-style');
  const styleState = find('style-state');
  const styleModels = find('style-model-select');
  const styleVersions = find('style-version-select');
  const promptEdit = find('prompt-edit-form');
  const enterpriseFields = find('enterprise-fields');
  const summary = find('asset-summary');
  const prompt = find('asset-prompt');
  const visualAccept = find('visual-accept');
  const imageForm = find('asset-image-form');
  const imageFile = find('asset-image-file');
  const imageLicense = find('asset-image-license');
  const imageRights = find('asset-image-rights');
  const imageProvenance = find('asset-image-provenance');
  const imagePreview = find('asset-image-preview');
  const imageAccept = find('image-accept');
  const modelSelector = find('model-select');
  const modelInfo = find('model-info');
  const download = find('model-download');
  const quota = find('asset-quota');
  const approval = find('model-approval-summary');
  const submit = find('model-submit');
  const modelForm = find('model-import-form');
  const viewer = initializeModelViewer({ root });
  let asset = null;
  let library = null;
  let technicalSelection = null;
  let selectedImage = null;
  let imageVisible = false;
  let localPreviewUrl = null;
  let models = [];
  let usage = null;
  let pending = false;
  let refreshPending = false;
  let visible = false;
  let selectedModelId = null;
  let familyGeneration = 0;
  let registeredVersions = [];
  const enterpriseNames = ['organizationType', 'audience', 'useCase', 'designGoal', 'culturalBoundaries', 'deliveryScope', 'licenseStatus'];

  const say = (message, isError = false) => {
    feedback.textContent = message;
    feedback.classList.toggle('ai-workshop-feedback-error', isError);
  };
  function resetUploadDrafts() {
    if (localPreviewUrl) { URL.revokeObjectURL(localPreviewUrl); localPreviewUrl = null; }
    imageFile.value = ''; imageLicense.value = ''; imageRights.checked = false;
    find('model-import-file').value = ''; find('model-import-license').value = '';
  }
  function updateControls() {
    form.querySelector('[type="submit"]').disabled = pending;
    mode.disabled = pending; styleMode.disabled = pending; sourceTask.disabled = pending;
    find('style-query').disabled = pending;
    styleVersions.disabled = pending; styleModels.disabled = pending; modelSelector.disabled = pending;
    find('prompt-edit-save').disabled = pending || !asset;
    visualAccept.disabled = pending || !asset || asset.visualPrompt.approved || asset.culturalReviewRequired === true;
    imageForm.querySelector('[type="submit"]').disabled = pending || !localPreviewUrl || !imageFile.files?.length || !asset?.visualPrompt.approved || asset.culturalReviewRequired === true;
    imageAccept.disabled = pending || Boolean(localPreviewUrl) || !selectedImage || !imageVisible || selectedImage.accepted || asset?.culturalReviewRequired === true;
    modelForm.querySelector('[type="submit"]').disabled = pending || !asset || asset.culturalReviewRequired === true;
    find('asset-refresh').disabled = pending || refreshPending;
    // Both accepted model results are retained; the user cancelled the third creation.
    submit.disabled = true;
    submit.setAttribute('aria-disabled', 'true');
  }
  async function action(operation, success) {
    if (pending) return;
    pending = true; updateControls(); say('正在处理本地资产记录……');
    try { await operation(); if (success) say(success); }
    catch (error) { say(error instanceof ServiceError ? error.message : error.message || '操作未完成，请检查本地服务。', true); }
    finally { pending = false; updateControls(); void library?.refresh(); }
  }
  function enterpriseBrief() {
    return Object.fromEntries(enterpriseNames.map((name) => [name, root.querySelector(`[data-ai-workshop-enterprise="${name}"]`).value.trim()]));
  }
  function updateMode() { enterpriseFields.hidden = mode.value !== 'enterprise'; }
  mode.addEventListener('change', updateMode);
  updateMode();

  function renderApproval() {
    const used = usage?.used_calls === null || !usage ? '历史待核实' : `${usage.used_calls} / 3`;
    const remaining = usage?.remaining_calls === null || !usage ? '待核实，创建锁定' : `${usage.remaining_calls} 次`;
    const entries = [
      ['角色', asset?.name || (technicalSelection ? '内部技术验证，未关联正式角色' : '尚未选择已确认角色')],
      ['风格与版本', asset ? `${STYLE_LABELS[asset.styleMode]} · 风格版本${asset.styleVersion}` : `${STYLE_LABELS[styleMode.value]} · 尚未登记`],
      ['概念图', technicalSelection ? '历史技术验证输入，非角色图片确认' : selectedImage?.accepted ? '已人工接受实际图片' : '尚未接受图片'],
      ['图片SHA-256', technicalSelection?.model.imageHash || selectedImage?.hash || '暂无图片Hash'],
      ['生成参数', `modelCount=1；mesh_quality=standard；faceNum=${(asset?.styleMode || styleMode.value) === 'chibi' ? 100000 : 500000}；disablePbr=0；onlyGenerateMesh=false；enableImageEnhancement=false（预留配置；建模已关闭）`],
      ['预计Credit', '本轮不创建模型，未查询新任务报价；历史费用不是实时价格'],
      ['历史费用', '验收归档记录：前两次合计60积分；不是当前账户余额或新任务报价'],
      ['已占用提交次数', used], ['剩余额度', remaining],
      ['本次用途', technicalSelection ? technicalSelection.model.purpose || '内部非公开技术验证' : asset?.purpose || find('asset-purpose').value.trim() || '尚未填写'],
      ['真实建模门禁', '保留两个已有真实模型成果；用户已取消第三次建模，创建入口保持关闭'],
    ];
    const list = document.createElement('dl'); list.className = 'ai-workshop-task-info ai-workshop-approval-info';
    entries.forEach(([label, value]) => { const item = document.createElement('div'); item.append(text('dt', '', label), text('dd', '', value)); list.append(item); });
    approval.replaceChildren(list);
    if (selectedImage?.accepted) {
      const img = document.createElement('img'); img.className = 'ai-workshop-approval-image';
      img.src = safeAssetFileUrl(selectedImage.fileUrl, 'images', selectedImage.imageId);
      img.alt = `${asset.name}已接受的概念图，供逐次建模确认`; approval.prepend(img);
    }
    quota.textContent = usage ? `全项目新建模型提交硬上限：3次 · 已占用：${used} · 剩余：${remaining}。失败或结果未知也不自动返还次数。`
      : '全项目新建模型HTTP提交尝试最多3次；当前历史与额度状态尚未读取，真实创建保持锁定。';
    quota.dataset.historyVerified = String(usage?.history_verified === true);
  }
  function renderAsset(value) {
    if (technicalSelection || asset?.assetId !== value.assetId) resetUploadDrafts();
    asset = value;
    technicalSelection = null;
    savedAssetId = null;
    summary.dataset.metadataState = 'saved_snapshot';
    summary.dataset.metadataReadAt = new Date().toISOString();
    registeredVersions = registeredVersions.filter((item) => item.characterId === asset.characterId && item.styleMode === asset.styleMode && item.mode === asset.mode && item.assetId !== asset.assetId);
    registeredVersions.push(asset);
    const emptyVersion = document.createElement('option'); emptyVersion.value = ''; emptyVersion.textContent = '请选择该风格已保存版本';
    styleVersions.replaceChildren(emptyVersion);
    registeredVersions.sort((a, b) => b.styleVersion - a.styleVersion).forEach((item) => {
      const option = document.createElement('option'); option.value = item.assetId;
      option.textContent = `${STYLE_LABELS[item.styleMode]} v${item.styleVersion} · ${item.culturalReviewRequired ? '编辑草稿待文化复核' : '保留已审校文化依据'} · ${item.purpose}`;
      styleVersions.append(option);
    });
    styleVersions.value = asset.assetId;
    sourceTask.value = asset.sourceTaskId; mode.value = asset.mode; styleMode.value = asset.styleMode; updateMode();
    find('asset-purpose').value = asset.purpose;
    if (asset.enterpriseBrief) enterpriseNames.forEach((name) => {
      const input = root.querySelector(`[data-ai-workshop-enterprise="${name}"]`);
      if (typeof asset.enterpriseBrief[name] === 'string') input.value = asset.enterpriseBrief[name];
    });
    summary.dataset.characterId = asset.characterId; summary.dataset.styleMode = asset.styleMode;
    summary.dataset.styleVersion = String(asset.styleVersion); summary.dataset.assetId = asset.assetId;
    try { globalThis.sessionStorage?.setItem(ASSET_STORAGE_KEY, asset.assetId); } catch { /* Visible IDs remain usable without storage. */ }
    const detail = document.createElement('div');
    detail.append(text('span', 'ai-workshop-badge ai-workshop-badge-ready', '服务器核验的已确认角色快照'),
      text('h3', '', asset.name), text('p', '', asset.characterSnapshot.positioning || ''),
      text('small', 'ai-workshop-citation-meta', `角色：${asset.characterId} · ${STYLE_LABELS[asset.styleMode]}版本${asset.styleVersion}\n资产：${asset.assetId} · 源任务：${asset.sourceTaskId}`));
    const evidence = document.createElement('details'); evidence.className = 'ai-workshop-details';
    evidence.append(text('summary', '', `文化来源与原创边界（${asset.citationSnapshot.length}项）`));
    asset.citationSnapshot.forEach((citation) => {
      const item = document.createElement('div'); item.className = 'ai-workshop-citation-body';
      item.append(text('strong', '', citation.title), text('p', 'ai-workshop-citation-meta', `${citation.sourceId} · ${citation.locator || '资料定位见源任务'}`));
      const url = safeCitationUrl(citation.url);
      if (url) { const link = text('a', 'ai-workshop-text-link', '核对来源 ↗'); link.href = url; link.target = '_blank'; link.rel = 'noopener noreferrer'; item.append(link); }
      evidence.append(item);
    });
    for (const field of ['costume', 'colors', 'visualElements']) {
      (asset.characterSnapshot[field] || []).forEach((item) => evidence.append(text('p', '', `${item.interpretation === 'creative' ? '原创演绎' : '据资料设计'}：${item.description}`)));
    }
    detail.append(evidence); summary.replaceChildren(detail);
    prompt.textContent = `${asset.visualPrompt.imagePrompt}\n\n画面约束：${asset.visualPrompt.negativePrompt}\n\n模板：${asset.visualPrompt.templateVersion}\nSHA-256：${asset.visualPrompt.promptHash}`;
    find('prompt-edit-text').value = asset.visualPrompt.imagePrompt;
    find('prompt-edit-negative').value = asset.visualPrompt.negativePrompt;
    styleState.textContent = asset.culturalReviewRequired ? '此编辑版本等待文化复核，视觉确认、图片及模型生成保持锁定。旧版本与素材保留。'
      : `${STYLE_LABELS[asset.styleMode]}已登记，概念图与模型仅属于该角色风格版本。`;
    visualAccept.textContent = asset.visualPrompt.approved ? '视觉Prompt已确认' : '核查并确认此视觉Prompt';
    // Backend lists most recent images first; never silently approve an older image after upload.
    selectedImage = asset.images[0] || null;
    renderImage(); renderStyleModels(); updateControls(); renderApproval();
  }
  function renderImage() {
    if (localPreviewUrl) { URL.revokeObjectURL(localPreviewUrl); localPreviewUrl = null; }
    imageVisible = false;
    if (!selectedImage) { imagePreview.replaceChildren(text('p', '', '尚无登记概念图；上传不会调用图像生成或3D建模API。')); imageAccept.textContent = '核查并接受此概念图'; return; }
    const img = document.createElement('img'); img.className = 'ai-workshop-concept-image';
    const currentImageId = selectedImage.imageId;
    img.addEventListener('load', () => { if (selectedImage?.imageId === currentImageId) { imageVisible = true; updateControls(); } });
    img.addEventListener('error', () => { if (selectedImage?.imageId === currentImageId) { imageVisible = false; updateControls(); say('登记概念图无法加载。请核查原文件与本地服务，不能在未看到图片时接受概念图。', true); } });
    img.src = safeAssetFileUrl(selectedImage.fileUrl, 'images', selectedImage.imageId);
    img.alt = `${asset.name}的实际导入概念图，${selectedImage.provenance === 'imported_ai_image' ? '由外部AI工具生成' : '用户授权素材'}`;
    const detail = text('p', 'ai-workshop-citation-meta', `${selectedImage.width}×${selectedImage.height} · ${selectedImage.provenance === 'imported_ai_image' ? '外部AI概念图导入' : '授权图片导入'} · ${selectedImage.accepted ? '已接受' : '待人工核查'}\nSHA-256：${selectedImage.hash}\n许可：${selectedImage.licenseNote}`);
    imagePreview.replaceChildren(img, detail);
    imageAccept.textContent = selectedImage.accepted ? '概念图已人工接受' : '核查并接受此概念图';
  }
  function renderModels(values) {
    // Global fixture selection is deliberately separated from character/style assets.
    models = values.filter((model) => ['local_test_fixture', 'legal_fixture', 'licensed_test_fixture'].includes(model.origin));
    const initial = document.createElement('option'); initial.value = ''; initial.textContent = '请选择已有合法GLB测试模型';
    modelSelector.replaceChildren(initial);
    models.forEach((model) => {
      const option = document.createElement('option'); option.value = model.modelId;
      option.textContent = `${model.title || model.name || model.modelId} · ${model.origin === 'neural4d' ? '真实Neural4D资产' : '合法导入，非Neural4D生成'}`;
      modelSelector.append(option);
    });
    if (selectedModelId && models.some((model) => model.modelId === selectedModelId)) modelSelector.value = selectedModelId;
    else { selectedModelId = null; modelSelector.value = ''; }
    if (!models.length && !asset?.models.length) modelInfo.textContent = '当前风格尚未生成3D模型；概念图不能代替真正的3D模型。';
  }
  function modelHeading(model, title, subtitle) {
    const heading = find('selected-model-title'); const note = find('selected-model-subtitle');
    if (heading) heading.textContent = model ? title : '选择一个数字资产';
    if (note) note.textContent = subtitle || '从右侧资产库选择已有模型。';
  }
  function showModel(model, isFixture, { internal = false } = {}) {
    if (!model) { download.hidden = true; selectedModelId = null; library?.setSelected(null); modelHeading(null); viewer?.clear('请选择当前风格模型或独立测试素材'); return; }
    selectedModelId = model.modelId;
    const title = internal ? model.title || 'Q版内部技术验证' : isFixture ? model.title : asset.name;
    const styleLabel = internal ? STYLE_LABELS.chibi : isFixture ? '独立校验素材' : STYLE_LABELS[asset.styleMode];
    modelHeading(model, title, `${styleLabel} · ${internal ? '内部技术验证，仅本机查看，不公开分发' : isFixture ? '合法导入，非角色模型' : '已保存的真实3D资产'}`);
    library?.setSelected(model.modelId);
    find('viewer-host').dataset.contentMode = internal ? 'internal_technical_test' : isFixture ? 'legal_test_fixture' : 'character_style_asset';
    find('viewer-host').dataset.styleMode = internal ? 'chibi' : isFixture ? 'not_character_asset' : asset.styleMode;
    modelInfo.textContent = `${title} · ${styleLabel} · ${(model.size / 1024 / 1024).toFixed(1)}MB\n${internal ? '真实Neural4D技术模型，非正式角色资产，不公开展示或分发。' : isFixture ? '独立合法GLB测试素材，非角色模型、非Neural4D生成。' : model.origin === 'neural4d' ? '真实Neural4D模型。' : '合法导入模型，非Neural4D生成。'}\n许可：${model.licenseNote}\nSHA-256：${model.hash}`;
    download.href = safeAssetFileUrl(model.downloadUrl, 'models', model.modelId, 'download');
    download.hidden = internal; // Internal viewing does not add a public distribution action.
    return viewer?.load(model);
  }
  function chooseModel() {
    if (pending) return;
    const model = models.find((item) => item.modelId === modelSelector.value);
    if (technicalSelection) clearCurrentStyle('独立GLB校验素材，不关联当前角色或技术概念图。');
    styleModels.value = '';
    technicalSelection = null; renderApproval();
    showModel(model, true);
  }
  function chooseStyleModel() {
    if (pending && !asset) return;
    modelSelector.value = '';
    showModel(asset?.models.find((item) => item.modelId === styleModels.value), false);
  }
  function renderStyleModels() {
    const initial = document.createElement('option'); initial.value = ''; initial.textContent = '当前风格尚未生成3D模型';
    styleModels.replaceChildren(initial);
    (asset?.models || []).forEach((model) => {
      const option = document.createElement('option'); option.value = model.modelId;
      option.textContent = `${STYLE_LABELS[asset.styleMode]}版本${asset.styleVersion} · ${model.origin === 'neural4d' ? '真实生成模型' : '授权GLB导入'}`;
      styleModels.append(option);
    });
    if (asset?.models.length) { styleModels.value = asset.models[0].modelId; chooseStyleModel(); }
    else {
      styleModels.value = ''; modelSelector.value = ''; selectedModelId = null; download.hidden = true;
      library?.setSelected(null); modelHeading(null, '', '当前角色的这个风格尚无模型，可从资产库选择其他已保存资产。');
      find('viewer-host').dataset.contentMode = 'style_asset_missing';
      find('viewer-host').dataset.styleMode = styleMode.value;
      viewer?.clear('当前风格尚未生成3D模型');
      modelInfo.textContent = `${STYLE_LABELS[styleMode.value]}当前版本尚无3D模型。下方测试素材独立提供，不属于此角色风格。`;
    }
  }
  function clearCurrentStyle(message, { modelStateUnknown = false } = {}) {
    resetUploadDrafts();
    asset = null; technicalSelection = null; selectedImage = null; imageVisible = false;
    savedAssetId = null;
    summary.dataset.metadataState = 'unavailable';
    delete summary.dataset.metadataReadAt;
    try { globalThis.sessionStorage?.removeItem?.(ASSET_STORAGE_KEY); } catch { /* Switching an absent style must not silently restore another style. */ }
    summary.replaceChildren(text('p', '', message));
    delete summary.dataset.characterId; delete summary.dataset.styleVersion; delete summary.dataset.assetId;
    summary.dataset.styleMode = styleMode.value;
    prompt.textContent = '当前风格尚未登记视觉Prompt。请明确点击“核验并登记角色资产”。';
    find('prompt-edit-text').value = ''; find('prompt-edit-negative').value = '';
    styleState.textContent = message;
    registeredVersions = []; const emptyVersion = document.createElement('option'); emptyVersion.value = ''; emptyVersion.textContent = '当前风格尚无已登记版本'; styleVersions.replaceChildren(emptyVersion);
    renderImage(); renderStyleModels();
    if (modelStateUnknown) {
      find('viewer-host').dataset.contentMode = 'style_asset_unknown';
      viewer?.clear(message);
      modelInfo.textContent = message;
      if (styleModels.children[0]) styleModels.children[0].textContent = '已有模型状态尚待核实';
      if (styleVersions.children[0]) styleVersions.children[0].textContent = '已有风格版本尚待核实';
    }
    renderApproval(); updateControls();
  }
  async function readSelectedStyle() {
    if (pending) return;
    const requestedTask = sourceTask.value.trim();
    const requestedMode = mode.value;
    const requestedStyle = styleMode.value;
    const currentGeneration = ++familyGeneration;
    clearCurrentStyle(`正在读取${STYLE_LABELS[requestedStyle]}已有登记记录；是否存在3D模型尚待核实。`, { modelStateUnknown: true });
    if (!requestedTask) {
      clearCurrentStyle('尚未选择角色，请先带入已确认任务ID；未发送查询，模型状态待核实。', { modelStateUnknown: true });
      return;
    }
    try {
      const family = await listCharacterAssets({ sourceTaskId: requestedTask, mode: requestedMode });
      if (currentGeneration !== familyGeneration || sourceTask.value.trim() !== requestedTask || mode.value !== requestedMode || styleMode.value !== requestedStyle) return;
      registeredVersions = family.filter((item) => item.styleMode === requestedStyle).sort((a, b) => b.styleVersion - a.styleVersion);
      const matched = registeredVersions[0];
      if (matched) renderAsset(matched);
      else clearCurrentStyle(`${STYLE_LABELS[requestedStyle]}尚未登记，当前风格尚未生成3D模型。若需要，请明确登记新风格；不会自动生成。`);
    } catch (error) {
      if (currentGeneration === familyGeneration) {
        const message = `${STYLE_LABELS[requestedStyle]}已有资产未能读取，模型状态未知。请检查本地服务后点击“读取当前角色的已登记风格”，不会重新生成模型。`;
        clearCurrentStyle(message, { modelStateUnknown: true });
        say(message, true);
      }
    }
  }
  async function readExistingAsset(assetId) {
    if (pending) return false;
    pending = true; updateControls();
    summary.dataset.metadataState = 'loading';
    say('正在只读读取已登记资产……不会登记资产或生成模型。');
    try {
      const value = await getCharacterAsset(assetId);
      renderAsset(value);
      say('已只读恢复登记资产快照。图片与模型仍为原有文件，没有重新生成。');
      return true;
    } catch (error) {
      // Retain the exact failed ID for an explicit manual GET retry. Never
      // replace it with a create request or clear an already loaded image/GLB.
      savedAssetId = assetId;
      summary.dataset.metadataState = asset ? 'stale' : 'unavailable';
      const message = asset
        ? '最新资产元数据读取失败；当前仅保留已加载快照、原图与Viewer，不表示服务当前在线。请点击“刷新本地资产”手动重读。'
        : '尚未读取到这份登记资产，未生成或登记替代内容。请点击“刷新本地资产”手动重读原资产ID。';
      styleState.textContent = message;
      if (!asset) summary.replaceChildren(text('p', '', message));
      say(`${message}${error instanceof ServiceError ? ` ${error.message}` : ''}`, true);
      return false;
    } finally { pending = false; updateControls(); }
  }
  async function refreshLocal({ readAsset = false } = {}) {
    if (refreshPending) return;
    refreshPending = true; find('asset-refresh').disabled = true;
    try {
      const results = await Promise.allSettled([listAssetModels(), getAssetUsage()]);
      const failures = [];
      if (results[0].status === 'fulfilled') renderModels(results[0].value);
      else {
        const message = results[0].reason instanceof ServiceError ? results[0].reason.message : '模型列表暂时无法读取。';
        if (!asset) modelInfo.textContent = message;
        failures.push(message);
      }
      if (results[1].status === 'fulfilled') usage = results[1].value;
      else { usage = null; failures.push(results[1].reason instanceof ServiceError ? results[1].reason.message : '额度记录暂时无法读取，创建锁定。'); }
      const requestedAsset = savedAssetId || asset?.assetId;
      if (readAsset && requestedAsset && !pending) await readExistingAsset(requestedAsset);
      renderApproval();
      if (failures.length) say(`最新本地状态未能完整读取；${asset ? '当前图片与Viewer仅为已加载快照，不表示服务当前在线。' : '尚未取得完整资产状态，未生成替代内容。'} ${failures.join(' ')}`, true);
    } finally { refreshPending = false; updateControls(); }
  }
  form.addEventListener('submit', (event) => {
    event.preventDefault(); if (pending) return;
    void action(async () => {
      familyGeneration += 1;
      const request = { sourceTaskId: sourceTask.value.trim(), mode: mode.value, styleMode: styleMode.value, purpose: find('asset-purpose').value.trim() };
      if (mode.value === 'enterprise') request.enterpriseBrief = enterpriseBrief();
      renderAsset(await createCharacterAsset(request));
    }, '角色资产已登记，文化依据和源任务已冻结。请核查视觉Prompt。');
  });
  promptEdit.addEventListener('submit', (event) => {
    event.preventDefault(); if (pending || !asset) return;
    const imagePrompt = find('prompt-edit-text').value.trim(); const negativePrompt = find('prompt-edit-negative').value.trim();
    if (imagePrompt === asset.visualPrompt.imagePrompt && negativePrompt === asset.visualPrompt.negativePrompt) { say('视觉Prompt尚未变化，未新增空版本。'); return; }
    void action(async () => renderAsset(await createPromptVersion(asset.assetId, { expectedPromptHash: asset.visualPrompt.promptHash, imagePrompt, negativePrompt })),
      '修改已保存为独立的待复核版本；没有覆盖原资产或自动调用Agent、图像、建模。');
  });
  visualAccept.addEventListener('click', () => { if (!asset || visualAccept.disabled) return; void action(async () => renderAsset(await approveVisualPrompt(asset.assetId, asset.visualPrompt.promptHash)), '视觉Prompt已确认。可以导入实际概念图，仍不会自动建模。'); });
  imageForm.addEventListener('submit', (event) => {
    event.preventDefault(); if (pending || !asset?.visualPrompt.approved || asset.culturalReviewRequired === true) return;
    if (!imageRights.checked) { say('请先确认图片来源与使用权，并填写真实许可说明。', true); imageRights.focus(); return; }
    void action(async () => {
      await uploadAssetImage({ assetId: asset.assetId, file: imageFile.files[0], provenance: imageProvenance.value, licenseNote: imageLicense.value.trim() });
      imageFile.value = '';
      renderAsset(await getCharacterAsset(asset.assetId));
    }, '实际图片已保存。请检查人物、服饰和构件，再接受此概念图。');
  });
  imageFile.addEventListener('change', () => {
    if (pending) return;
    const file = imageFile.files?.[0];
    renderImage();
    if (!file) { updateControls(); return; }
    if (!['image/png', 'image/jpeg', 'image/webp'].includes(file.type) || file.size < 1 || file.size > 10 * 1024 * 1024) {
      say('请选择不超过10MB的PNG、JPEG或WEBP图片。原登记图片未改变。', true); updateControls(); return;
    }
    localPreviewUrl = URL.createObjectURL(file);
    const image = document.createElement('img'); image.className = 'ai-workshop-concept-image'; image.src = localPreviewUrl;
    image.alt = '本地选择的待保存概念图';
    const token = localPreviewUrl;
    image.addEventListener('error', () => { if (localPreviewUrl === token) say('所选图片无法预览，请选择有效图片；未上传或保存。', true); });
    imagePreview.replaceChildren(image, text('p', 'ai-workshop-citation-meta', '本地预览 · 尚未保存，当前3D仍为原资产。只有你明确保存后才会上传，不会调用图像生成或建模。'));
    updateControls();
  });
  imageAccept.addEventListener('click', () => { if (imageAccept.disabled || !selectedImage) return; void action(async () => { await acceptAssetImage(selectedImage.imageId, selectedImage.hash); renderAsset(await getCharacterAsset(asset.assetId)); }, '概念图已接受。真实建模需要单独授权，当前不会提交。'); });
  modelForm.addEventListener('submit', (event) => {
    event.preventDefault(); if (pending || !asset || asset.culturalReviewRequired === true) return;
    void action(async () => {
      const model = await importLicensedModel({ assetId: asset.assetId, file: find('model-import-file').files[0], licenseNote: find('model-import-license').value.trim() });
      renderAsset(await getCharacterAsset(asset.assetId)); await refreshLocal();
      styleModels.value = model.modelId; chooseStyleModel();
    }, '合法GLB已检查并登记。本次是导入，未调用Neural4D建模。');
  });
  modelSelector.addEventListener('change', chooseModel);
  styleModels.addEventListener('change', chooseStyleModel);
  styleVersions.addEventListener('change', () => {
    if (pending || !styleVersions.value) return;
    const requested = registeredVersions.find((item) => item.assetId === styleVersions.value);
    if (!requested) return;
    void action(async () => renderAsset(await getCharacterAsset(requested.assetId)), '已读取保留的风格版本，未重新生成任何资产。');
  });
  styleMode.addEventListener('change', () => void readSelectedStyle());
  mode.addEventListener('change', () => void readSelectedStyle());
  sourceTask.addEventListener('change', () => void readSelectedStyle());
  find('style-query').addEventListener('click', () => void readSelectedStyle());
  find('asset-refresh').addEventListener('click', () => { if (!pending) void refreshLocal({ readAsset: true }); });
  find('enterprise-to-agent').addEventListener('click', () => {
    try {
      const brief = enterpriseRequirements(enterpriseBrief());
      find('brief').value = brief;
      selectPanel('create', true); window.history.pushState(null, '', '#ai-workshop-create'); find('brief').focus();
      say('企业需求已带入角色创作；需你再点击提交Agent创作，不会自动执行。');
    } catch (error) { say(error.message, true); }
  });
  root.addEventListener('ai-workshop-character-selected', (event) => {
    try { sourceTask.value = validateAssetIdentifier(event.detail?.taskId); }
    catch { return; }
    selectPanel('model', true); window.history.pushState(null, '', '#ai-workshop-model');
    say('已带入任务ID。请选择个人/企业用途并明确登记；后端将再次核验真实确认记录。');
    void readSelectedStyle();
  });
  // Diagnostics expose registered file hashes and actual interaction measurements, never credentials.
  if (globalThis.window) window.xijingAssetViewerDiagnostics = () => viewer?.diagnostics() || { state: 'unavailable' };
  updateControls(); renderApproval();
  let savedAssetId = null;
  try { const saved = globalThis.sessionStorage?.getItem(ASSET_STORAGE_KEY); if (saved) savedAssetId = validateAssetIdentifier(saved); } catch { /* Corrupt IDs never cause a replacement create request. */ }
  // A review link selects an existing local asset, never a generation action.
  try {
    const linked = new URLSearchParams(globalThis.location?.search || '').get('assetId');
    if (linked) savedAssetId = validateAssetIdentifier(linked);
  } catch { /* Invalid review links keep the existing safe storage fallback. */ }
  library = initializeAssetLibrary({ root,
    async onSelect(item) {
      if (pending) return false;
      const selectionGeneration = ++familyGeneration;
      if (item.model.origin === 'neural4d_technical_test') {
        pending = true; updateControls();
        try {
        sourceTask.value = ''; styleMode.value = 'chibi';
        clearCurrentStyle('Q版内部技术验证素材，未关联正式角色；不会借用其他角色的文化确认。');
        technicalSelection = item;
        summary.replaceChildren(text('h3', '', item.title), text('p', '', '技术验证用，非正式角色资产。仅限内部查看，不公开分发。'));
        summary.dataset.metadataState = 'internal_technical_snapshot';
        styleState.textContent = 'Q版内部技术模型 · 无正式角色关联；风格切换不会生成模型。';
        prompt.textContent = item.candidate?.promptSnapshot?.text || '历史Prompt见技术验证记录。没有新建或修改Prompt版本。';
        if (item.candidate && item.imageUrl) {
          const image = document.createElement('img'); image.className = 'ai-workshop-concept-image'; image.src = item.imageUrl;
          image.alt = 'Q版技术验证的原登记概念图，仅供内部查看';
          const note = text('p', 'ai-workshop-citation-meta', `历史技术验证输入 · 概念图，不是模型截图\nSHA-256：${item.candidate.hash}`);
          image.addEventListener('error', () => say('原概念图暂时无法读取，已有GLB仍可独立查看。', true));
          imagePreview.replaceChildren(image, note);
        }
        renderApproval(); updateControls(); await showModel(item.model, false, { internal: true });
        say('已选择保存的Q版内部技术模型。仅限内部查看；没有创建或修改任何资产。');
        return selectionGeneration === familyGeneration && selectedModelId === item.model.modelId;
        } finally { pending = false; updateControls(); }
      }
      if (asset?.assetId !== item.model.assetId || !asset.models.some((model) => model.modelId === item.model.modelId)) {
        if (!item.model.assetId || !await readExistingAsset(item.model.assetId)) return false;
      }
      const model = asset.models.find((value) => value.modelId === item.model.modelId);
      if (!model) { say('这份模型与当前角色记录的关联尚未核实，已停止切换。', true); return false; }
      if (selectionGeneration !== familyGeneration) return false;
      pending = true; updateControls();
      try {
      resetUploadDrafts();
      selectedImage = asset.images.find((image) => image.imageId === model.imageId && image.hash === model.imageHash) || null;
      renderImage(); renderApproval();
      modelSelector.value = ''; styleModels.value = model.modelId;
      if (viewer?.diagnostics().modelId !== model.modelId || viewer?.diagnostics().modelHash !== model.hash) await showModel(model, false);
      else selectedModelId = model.modelId;
      return selectionGeneration === familyGeneration && selectedModelId === model.modelId;
      } finally { pending = false; updateControls(); }
    },
    async onPendingSelected(value) { familyGeneration += 1; return await readExistingAsset(value.assetId); },
  });
  return {
    async setVisible(value) {
      if (visible === value) return;
      visible = value;
      if (!value) return;
      await refreshLocal();
      const requestedAsset = savedAssetId;
      if (requestedAsset && !asset && !pending) await readExistingAsset(requestedAsset);
      await library?.refresh({ selectDefault: !requestedAsset || Boolean(asset), preferredAssetId: asset?.assetId || requestedAsset });
    },
  };
}
