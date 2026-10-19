import { HISTORY_TASK_STATES, HISTORY_AGENT_NAMES, safeHistoryCitationUrl, safeHistoryViewerUrl } from './history-contracts.js?v=phase5-wp2-1';
import { listAgentHistory, getAgentHistoryDetail, HistoryReadError } from './history-services.js?v=phase5-wp2-1';

const MISSING = '历史记录未保存该信息';
const AGENT_STATES = Object.freeze({ pending: '待执行', running: '记录状态：运行中（非实时监控）', completed: '已完成', failed: '执行失败', awaiting_confirmation: '等待用户确认' });
const MODEL_ORIGINS = Object.freeze({ neural4d: 'Neural4D真实生成（已保存来源）', neural4d_technical_test: 'Neural4D内部技术验证（非正式角色资产）', local_test_fixture: '本地测试夹具（非真实AI生成）', legal_fixture: '合法测试夹具（非真实AI生成）', licensed_test_fixture: '获许可测试夹具（非真实AI生成）', licensed_import: '合法导入模型（不代表平台AI生成）' });
const LIMIT = 16000;
const node = (tag, value = '', className = '') => {
  const element = document.createElement(tag);
  element.textContent = String(value);
  if (className) element.className = className;
  return element;
};
const labelTime = (value) => typeof value === 'string' && value ? value.replace('T', ' ') : MISSING;
function boundedText(value, limit = LIMIT) {
  const content = typeof value === 'string' ? value : JSON.stringify(value, null, 2);
  return content.length > limit ? `${content.slice(0, limit)}\n……界面仅展示前${limit}字，原始持久化记录未修改。` : content;
}
function folded(label, value) {
  const details = node('details', '', 'ai-workshop-details');
  details.append(node('summary', label), node('pre', value === null || value === undefined ? MISSING : boundedText(value), 'ai-workshop-history-json'));
  return details;
}
function group(title) {
  const section = node('section', '', 'ai-workshop-history-group');
  section.append(node('h5', title));
  return section;
}
function missingFields(container, fields) {
  if (fields.length) container.append(node('p', `记录不完整：${fields.join('；')}。缺失信息不会自动重建。`, 'ai-workshop-feedback'));
}
function stateBadge(state) {
  const badge = node('span', HISTORY_TASK_STATES[state], 'ai-workshop-status');
  badge.dataset.state = state;
  return badge;
}
/** Only persistent public artifacts are rendered; this does not restore the live controller or replay SSE. */
export function renderHistoryDetail(container, detail, { onEventPage = () => {}, onRefresh = () => {} } = {}) {
  const content = node('div');
  content.dataset.historySource = 'persisted_history';
  const task = detail.task;
  content.append(node('p', '真实持久化记录 · 只读快照 · 本页不会执行Agent', 'ai-workshop-history-source-note'), node('h4', task.title || '角色创作任务'), stateBadge(task.state));
  content.append(node('code', `任务ID：${task.taskId}`, 'ai-workshop-history-id'));
  content.append(node('p', `创建：${labelTime(task.createdAt)}；开始：${labelTime(task.startedAt)}；结束：${labelTime(task.finishedAt)}`));
  content.append(node('p', `最后持久化更新时间：${labelTime(task.updatedAt)}；本次读取时间：${labelTime(detail.snapshotAt)}`));
  content.append(node('p', task.executionType === 'model_metadata_recorded' ? '已保存模型调用元数据；本页仅展示历史，不发起模型请求。' : '历史记录未保存完整执行类型信息，不能据此判断每个阶段的供应商调用。'));
  content.append(node('p', `已保存完成阶段：${task.completedSteps} / ${task.totalSteps}；事件记录：${task.eventCount}条。这里不播放任务进度。`));
  const refresh = node('button', '重新读取这份历史快照', 'ai-workshop-text-link');
  refresh.type = 'button'; refresh.id = 'ai-workshop-history-detail-refresh';
  refresh.addEventListener('click', onRefresh); content.append(refresh);
  missingFields(content, [...new Set([...task.missingFields, ...detail.missingFields])]);
  content.append(folded('查看已保存的创作需求', detail.brief));

  const agents = group('Agent执行顺序与公开阶段产物');
  if (!detail.agents.length) agents.append(node('p', MISSING));
  detail.agents.forEach((agent, index) => {
    const step = node('details', '', 'ai-workshop-details'); step.dataset.historyAgent = agent.id;
    step.append(node('summary', `${index + 1}. ${HISTORY_AGENT_NAMES[agent.id]} · ${AGENT_STATES[agent.state] || MISSING}`));
    step.append(node('p', agent.summary ? boundedText(agent.summary) : MISSING), node('p', `开始：${labelTime(agent.startedAt)}；结束：${labelTime(agent.finishedAt)}`));
    step.append(node('p', `历史输入：${agent.inputNote || MISSING}`));
    if (agent.errorCode) step.append(node('p', `已保存错误代码：${agent.errorCode}`, 'ai-workshop-feedback-error'));
    step.append(folded('查看已保存的公开输出（不含模型隐藏思维）', agent.output));
    step.append(node('p', `产物版本：${agent.outputVersion ?? MISSING}；保存时间：${labelTime(agent.outputSavedAt)}`));
    if (agent.outputHash) step.append(node('code', `产物Hash：${agent.outputHash}`, 'ai-workshop-history-id'));
    missingFields(step, agent.missingFields); agents.append(step);
  });
  content.append(agents);

  const sources = group('历史RAG研究依据');
  sources.append(node('p', '以下是任务当时保存的资料引用，不重新运行RAG研究；入库事实摘要不等同原网页全文。'));
  if (!detail.citations.length) sources.append(node('p', MISSING));
  detail.citations.forEach((citation) => {
    const reference = node('details', '', 'ai-workshop-details');
    reference.append(node('summary', boundedText(citation.title, 2000)));
    reference.append(node('p', `证据ID：${citation.id}；来源ID：${citation.sourceId}`), node('p', `定位：${citation.locator || MISSING}`));
    reference.append(node('blockquote', citation.excerpt ? boundedText(citation.excerpt) : MISSING));
    const href = safeHistoryCitationUrl(citation.url);
    if (href) {
      const link = node('a', '查看当时登记的来源网页 ↗', 'ai-workshop-text-link');
      link.href = href; link.target = '_blank'; link.rel = 'noopener noreferrer'; reference.append(link);
    } else reference.append(node('p', '未保存可安全打开的来源网址。'));
    sources.append(reference);
  });
  content.append(sources);

  const results = group('角色JSON、文化审校与人工确认');
  const resultName = detail.result?.design?.name;
  if (typeof resultName === 'string') results.append(node('p', `已保存角色名称：${boundedText(resultName, 2000)}。角色定位以已保存JSON为准，不据名称推断传统历史人物。`));
  results.append(folded('查看已保存的角色与结果JSON', detail.result));
  const verdict = detail.culturalReview?.verdict;
  results.append(node('p', `文化审校：${({ pass: 'AI辅助审校通过', needs_revision: '需要修订', insufficient_evidence: '资料不足' })[verdict] || MISSING}。AI辅助审校不代表专业人员审核。`));
  results.append(folded('查看已保存的文化审校', detail.culturalReview));
  const confirmation = detail.humanConfirmation;
  results.append(node('p', `人工确认：${confirmation.userConfirmed === null ? MISSING : confirmation.userConfirmed ? '已保存用户接受记录' : '未确认'}；确认时间：${labelTime(confirmation.confirmedAt)}`));
  results.append(node('p', `当时保存的发布许可状态：${confirmation.publicationAllowed === null ? MISSING : confirmation.publicationAllowed ? '允许展示该角色文字方案，不扩展第三方素材许可' : '不可作为已确认最终文字方案'}`));
  results.append(folded('查看已保存的人工确认记录', confirmation.record)); content.append(results);

  const assets = group('已有资产关联（只读）');
  assets.append(node('p', '只依据已保存的角色与资产ID关联；查看链接不会生成或重新登记资产。没有3D模型时不会自动建模。'));
  if (!detail.assets.length) assets.append(node('p', detail.assetAssociationStatus === 'unavailable' ? '资产关联暂时无法读取，未推断关联关系。' : '未建立关联。'));
  const list = node('ul', '', 'ai-workshop-history-assets');
  detail.assets.forEach((asset) => {
    const item = node('li');
    item.append(node('p', `${asset.name} · ${asset.styleMode === 'chibi' ? 'Q版卡通' : '写实国风'} · 风格版本${asset.styleVersion}`), node('code', `资产ID：${asset.assetId}；角色ID：${asset.characterId}`, 'ai-workshop-history-id'));
    item.append(node('p', asset.modelIds.length ? `已关联模型ID：${asset.modelIds.join('、')}` : '当前风格尚未生成3D模型。'));
    asset.modelIds.forEach((modelId) => {
      const model = asset.models?.find((entry) => entry.modelId === modelId);
      item.append(node('p', `模型${modelId} · 来源：${MODEL_ORIGINS[model?.origin] || '历史记录未保存或无法识别模型来源，不作真实生成判断'}${model?.format ? ` · 格式：${model.format}` : ''}`));
    });
    const href = safeHistoryViewerUrl(asset.viewerUrl, asset.assetId);
    if (href) { const link = node('a', '只读查看已有资产与Viewer →', 'ai-workshop-text-link'); link.href = href; item.append(link); }
    list.append(item);
  });
  assets.append(list); content.append(assets);

  const events = group('已保存事件时间线');
  events.append(node('p', '按原事件序号展示持久化状态，不是实时执行，不进行历史动画回放。'));
  if (!detail.events.length) events.append(node('p', MISSING));
  const timeline = node('ol', '', 'ai-workshop-history-events');
  detail.events.forEach((event) => {
    const item = node('li');
    const eventState = event.taskState ? HISTORY_TASK_STATES[event.taskState] : AGENT_STATES[event.state];
    item.append(node('strong', `#${event.sequence} · ${event.agentId ? HISTORY_AGENT_NAMES[event.agentId] || MISSING : '任务事件'}${eventState ? ` · ${eventState}` : ''}`));
    item.append(node('p', `记录时间：${labelTime(event.occurredAt)}`), node('p', typeof event.summary === 'string' ? boundedText(event.summary) : MISSING));
    if (event.incomplete === true) item.append(node('p', '该历史事件不完整，只展示保存内容，不重建状态或时间。', 'ai-workshop-feedback'));
    timeline.append(item);
  }); events.append(timeline);
  const pages = node('div', '', 'ai-workshop-history-pagination');
  const previous = node('button', '上一页事件', 'ai-workshop-text-link'); previous.id = 'ai-workshop-history-events-prev'; previous.type = 'button'; previous.disabled = detail.eventPage <= 1;
  previous.addEventListener('click', () => onEventPage(detail.eventPage - 1));
  const next = node('button', '下一页事件', 'ai-workshop-text-link'); next.id = 'ai-workshop-history-events-next'; next.type = 'button'; next.disabled = detail.eventPage >= detail.eventTotalPages;
  next.addEventListener('click', () => onEventPage(detail.eventPage + 1));
  pages.append(previous, node('span', `事件第${detail.eventPage}页 / ${detail.eventTotalPages || 0}页，共${detail.eventTotal}条`), next); events.append(pages); content.append(events);
  container.replaceChildren(content);
}

/** Explicit manual GETs only. No storage, intervals, EventSource, or live workflow mutation methods. */
export function initializeAgentHistory({ root, services = { listAgentHistory, getAgentHistoryDetail } }) {
  const names = ['history-form', 'history-state', 'history-type', 'history-task-id', 'history-load', 'history-status', 'history-list', 'history-prev', 'history-next', 'history-page', 'history-detail', 'history-detail-status', 'history-detail-content'];
  if (!root.querySelector('#ai-workshop-history')) return null;
  const elements = Object.fromEntries(names.map((name) => {
    const element = root.querySelector(`#ai-workshop-${name}`);
    if (!element) throw new Error('历史档案缺少必要界面元素。');
    return [name, element];
  }));
  let listSnapshot = null;
  let selectedTaskId = null;
  let filters = null;
  let listGeneration = 0;
  let detailGeneration = 0;
  let listAbort = null;
  let detailAbort = null;
  let listPending = false;
  let detailPending = false;
  function updateControls() {
    elements['history-load'].disabled = listPending;
    elements['history-prev'].disabled = listPending || !listSnapshot || listSnapshot.page <= 1;
    elements['history-next'].disabled = listPending || !listSnapshot || listSnapshot.page >= listSnapshot.totalPages;
    elements['history-list'].setAttribute('aria-busy', String(listPending));
    elements['history-detail-content'].setAttribute('aria-busy', String(detailPending));
  }
  function feedback(element, message, error = false) {
    element.textContent = message; element.classList.toggle('ai-workshop-feedback-error', error);
  }
  function clearDetail() {
    detailGeneration += 1; detailAbort?.abort(); detailAbort = null; selectedTaskId = null; detailPending = false;
    elements['history-detail'].hidden = true; elements['history-detail-content'].replaceChildren();
  }
  function renderList(value) {
    const entries = [];
    value.items.forEach((task) => {
      const entry = node('article', '', 'ai-workshop-history-entry');
      entry.dataset.historyTask = task.taskId;
      entry.dataset.selected = String(task.taskId === selectedTaskId);
      entry.append(node('h4', boundedText(task.title || '角色创作任务', 2000)), stateBadge(task.state), node('code', task.taskId, 'ai-workshop-history-id'));
      entry.append(node('p', `创建：${labelTime(task.createdAt)}；开始：${labelTime(task.startedAt)}；结束：${labelTime(task.finishedAt)}`));
      entry.append(node('p', `实际已保存执行阶段：${task.executedAgents.map((id) => HISTORY_AGENT_NAMES[id]).join(' → ') || MISSING}`));
      entry.append(node('p', `记录完整性：${task.historyCompleteness === 'complete' ? '事件序列与阶段记录完整（其他字段见详情）' : '不完整，详见缺失说明'}；已保存事件${task.eventCount}条；${task.resultReadable ? '结果可读取' : task.hasSavedResult ? '存在部分保存结果，详情按实展示' : '未保存完整结果'}`));
      const button = node('button', '查看只读详情', 'ai-workshop-text-link');
      button.type = 'button'; button.dataset.historyTaskId = task.taskId;
      button.addEventListener('click', () => { void loadDetail(task.taskId); });
      entry.append(button); entries.push(entry);
    });
    elements['history-list'].replaceChildren(...entries);
    elements['history-page'].textContent = `第${value.page}页 / ${value.totalPages || 0}页，共${value.total}条`;
  }
  function updateStateOptions(value) {
    const selected = elements['history-state'].value;
    const states = [...new Set([...value.availableStates, ...(selected ? [selected] : [])])];
    const options = [node('option', '全部状态')]; options[0].value = '';
    states.forEach((state) => { const option = node('option', HISTORY_TASK_STATES[state]); option.value = state; options.push(option); });
    elements['history-state'].replaceChildren(...options); elements['history-state'].value = selected;
  }
  async function loadList(page = 1, { readFilters = page === 1 } = {}) {
    const generation = ++listGeneration;
    listAbort?.abort(); listAbort = new AbortController();
    clearDetail(); listPending = true; updateControls();
    feedback(elements['history-status'], '正在只读查询已保存任务……不会执行Agent。');
    elements['history-list'].replaceChildren();
    try {
      if (readFilters || !filters) filters = { state: elements['history-state'].value, taskType: elements['history-type'].value, taskId: elements['history-task-id'].value.trim() };
      const value = await services.listAgentHistory({ ...filters, page, pageSize: 10 }, { signal: listAbort.signal });
      if (generation !== listGeneration) return;
      listSnapshot = value; updateStateOptions(value); renderList(value);
      feedback(elements['history-status'], value.items.length ? `已读取${value.items.length}条真实持久化记录，只读快照；不会实时刷新或自动执行。` : '没有符合条件的历史任务。可调整筛选后重新读取；不会创建测试或演示任务。');
    } catch (error) {
      if (generation !== listGeneration) return;
      listSnapshot = null; elements['history-page'].textContent = '尚无有效分页';
      feedback(elements['history-status'], error instanceof HistoryReadError ? error.message : '历史记录暂时无法读取，请手动重新查询。', true);
    } finally { if (generation === listGeneration) { listPending = false; updateControls(); } }
  }
  async function loadDetail(taskId, eventPage = 1) {
    const generation = ++detailGeneration;
    detailAbort?.abort(); detailAbort = new AbortController(); selectedTaskId = taskId; detailPending = true;
    elements['history-detail'].hidden = false; elements['history-detail-content'].replaceChildren(); updateControls();
    if (listSnapshot) renderList(listSnapshot);
    feedback(elements['history-detail-status'], '正在只读读取任务详情和已保存事件……');
    try {
      const value = await services.getAgentHistoryDetail(taskId, { eventPage, eventPageSize: 30, signal: detailAbort.signal });
      if (generation !== detailGeneration) return;
      renderHistoryDetail(elements['history-detail-content'], value, { onEventPage: (page) => { void loadDetail(taskId, page); }, onRefresh: () => { void loadDetail(taskId, eventPage); } });
      feedback(elements['history-detail-status'], value.task.historyCompleteness === 'incomplete' || value.missingFields.length ? '历史记录不完整，以下只展示当时保存的字段；缺失信息不自动补全。' : '历史详情已读取；这是持久化快照，不是实时监控。');
    } catch (error) {
      if (generation !== detailGeneration) return;
      feedback(elements['history-detail-status'], error instanceof HistoryReadError ? error.message : '历史详情暂时无法读取，请手动重试。', true);
      const retry = node('button', '重新读取这份历史快照', 'ai-workshop-text-link'); retry.type = 'button'; retry.id = 'ai-workshop-history-detail-refresh';
      retry.addEventListener('click', () => { void loadDetail(taskId, eventPage); }); elements['history-detail-content'].append(retry);
    } finally { if (generation === detailGeneration) { detailPending = false; updateControls(); } }
  }
  elements['history-form'].addEventListener('submit', (event) => { event.preventDefault(); void loadList(1); });
  elements['history-prev'].addEventListener('click', () => { if (listSnapshot && !listPending) void loadList(listSnapshot.page - 1, { readFilters: false }); });
  elements['history-next'].addEventListener('click', () => { if (listSnapshot && !listPending) void loadList(listSnapshot.page + 1, { readFilters: false }); });
  updateControls();
  return { loadList, loadDetail, diagnostics: () => ({ listPending, detailPending, selectedTaskId, page: listSnapshot?.page ?? null, source: 'persisted_history', readOnly: true }) };
}
