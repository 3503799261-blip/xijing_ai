/** Read-only persisted snapshots; never infer executions or fill missing historical artifacts. */
export const HISTORY_TASK_STATES = Object.freeze({ waiting: '记录状态：等待调度', running: '记录状态：运行中（非实时监控）', awaiting_confirmation: '记录状态：等待用户确认', completed: '记录状态：已确认完成', failed: '记录状态：执行失败', cancelled: '记录状态：已取消', unknown: '记录状态：未知' });
export const HISTORY_AGENT_NAMES = Object.freeze({ planner: '任务规划Agent', researcher: '京剧研究Agent', designer: '角色设计Agent', reviewer: '文化审校Agent' });
const STEP_STATES = ['pending', 'running', 'completed', 'failed', 'awaiting_confirmation'];
const isObject = (value) => value !== null && typeof value === 'object' && !Array.isArray(value);
const isString = (value, max = 20000) => typeof value === 'string' && value.length <= max;
const optionalString = (value, max = 20000) => value === null || value === undefined || isString(value, max);
const natural = (value) => Number.isSafeInteger(value) && value >= 0;
const time = (value) => value === null || (isString(value, 80) && /^\d{4}-\d\d-\d\dT/.test(value) && Number.isFinite(Date.parse(value)));
const strings = (value, max = 200, length = 256) => Array.isArray(value) && value.length <= max && value.every((item) => isString(item, length));
export function validateHistoryId(value) {
  if (!isString(value, 36) || !/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i.test(value)) throw new TypeError('Invalid historical identifier');
  return value;
}
function validateSource(source) {
  if (!isObject(source) || source.kind !== 'persisted_history' || source.readOnly !== true || !isString(source.note, 2000)) throw new TypeError('Invalid history source');
}
function validateSummary(value) {
  if (!isObject(value)) throw new TypeError('Invalid history task');
  validateHistoryId(value.taskId);
  if (value.taskType !== 'character_creation' || !isString(value.title, 2000) || !Object.hasOwn(HISTORY_TASK_STATES, value.state)
    || !['createdAt', 'updatedAt', 'startedAt', 'finishedAt'].every((field) => time(value[field]))
    || !Array.isArray(value.executedAgents) || value.executedAgents.length > 4 || new Set(value.executedAgents).size !== value.executedAgents.length || value.executedAgents.some((id) => !Object.hasOwn(HISTORY_AGENT_NAMES, id))
    || !natural(value.completedSteps) || !natural(value.totalSteps) || value.completedSteps > value.totalSteps || value.totalSteps > 4
    || typeof value.resultReadable !== 'boolean' || typeof value.hasSavedResult !== 'boolean'
    || !natural(value.eventCount) || !natural(value.lastSequence) || !['complete', 'incomplete'].includes(value.historyCompleteness)
    || !strings(value.missingFields) || value.sourceType !== 'persisted_history' || !['model_metadata_recorded', 'unknown'].includes(value.executionType)) throw new TypeError('Invalid history task fields');
  return value;
}
function validatePage(page, pageSize, total, totalPages, maxSize) {
  if (!natural(page) || page < 1 || !natural(pageSize) || pageSize < 1 || pageSize > maxSize || !natural(total) || !natural(totalPages)
    || totalPages !== Math.ceil(total / pageSize)) throw new TypeError('Invalid history pagination');
}
export function validateHistoryList(value) {
  if (!isObject(value) || !Array.isArray(value.items)) throw new TypeError('Invalid history list');
  validateSource(value.source);
  validatePage(value.page, value.pageSize, value.total, value.totalPages, 50);
  if (value.items.length > value.pageSize || new Set(value.items.map((item) => item.taskId)).size !== value.items.length
    || !strings(value.availableStates, 7, 80) || value.availableStates.some((state) => !Object.hasOwn(HISTORY_TASK_STATES, state))
    || !strings(value.availableTaskTypes, 1, 80) || value.availableTaskTypes.some((type) => type !== 'character_creation') || !isString(value.requestId, 128)) throw new TypeError('Invalid history list metadata');
  value.items.forEach(validateSummary);
  return value;
}
/** A persisted JSON artifact is shown as bounded text, including incomplete historical structures. */
function artifact(value) {
  if (value === null) return true;
  if (!isObject(value)) return false;
  try { return JSON.stringify(value).length <= 300000; } catch { return false; }
}
export function safeHistoryCitationUrl(value) {
  try {
    if (!isString(value, 4000) || !value) return null;
    const url = new URL(value);
    if (!['https:', 'http:'].includes(url.protocol) || url.username || url.password || /[?&](?:token|signature|authorization|key|credential|x-amz-[^=]*|x-cos-[^=]*|q-signature)=/i.test(url.search)) return null;
    return url.href;
  } catch { return null; }
}
export function safeHistoryViewerUrl(value, assetId) {
  try {
    validateHistoryId(assetId);
    if (!isString(value, 500)) return null;
    const origin = globalThis.location?.origin || 'http://127.0.0.1:8000';
    const url = new URL(value, origin);
    if (url.origin !== origin || url.pathname !== '/about.html' || url.username || url.password || url.hash !== '#ai-workshop-model'
      || url.searchParams.size !== 1 || url.searchParams.get('assetId') !== assetId) return null;
    return url.href;
  } catch { return null; }
}
export function validateHistoryDetail(value) {
  if (!isObject(value)) throw new TypeError('Invalid history detail');
  validateSource(value.source); validateSummary(value.task);
  validatePage(value.eventPage, value.eventPageSize, value.eventTotal, value.eventTotalPages, 100);
  if (!Array.isArray(value.agents) || value.agents.length > 4 || !artifact(value.brief) || !artifact(value.result) || !artifact(value.culturalReview)
    || !Array.isArray(value.citations) || value.citations.length > 200 || !Array.isArray(value.events) || value.events.length > value.eventPageSize
    || !Array.isArray(value.assets) || value.assets.length > 100 || !['linked', 'not_linked', 'unavailable'].includes(value.assetAssociationStatus)
    || !strings(value.missingFields) || !time(value.snapshotAt) || value.snapshotAt === null || !isString(value.requestId, 128)
    || !isObject(value.humanConfirmation) || !artifact(value.humanConfirmation.record)
    || ![null, true, false].includes(value.humanConfirmation.userConfirmed) || ![null, true, false].includes(value.humanConfirmation.publicationAllowed)
    || !time(value.humanConfirmation.confirmedAt)) throw new TypeError('Invalid history detail fields');
  const ids = new Set();
  value.agents.forEach((agent) => {
    if (!isObject(agent) || !Object.hasOwn(HISTORY_AGENT_NAMES, agent.id) || ids.has(agent.id) || !isString(agent.name, 200)
      || (agent.state !== null && !STEP_STATES.includes(agent.state)) || !optionalString(agent.summary) || !time(agent.startedAt) || !time(agent.finishedAt)
      || !optionalString(agent.errorCode, 200) || agent.input !== null || !isString(agent.inputNote, 2000) || !artifact(agent.output)
      || !(agent.outputVersion === null || (natural(agent.outputVersion) && agent.outputVersion > 0)) || !optionalString(agent.outputHash, 128) || !time(agent.outputSavedAt) || !strings(agent.missingFields)) throw new TypeError('Invalid history agent');
    ids.add(agent.id);
  });
  value.citations.forEach((citation) => {
    if (!isObject(citation) || !isString(citation.id, 256) || !isString(citation.title, 2000) || !isString(citation.sourceId, 256)
      || !optionalString(citation.locator, 2000) || !optionalString(citation.excerpt, 40000) || !optionalString(citation.url, 4000)) throw new TypeError('Invalid history citation');
  });
  let sequence = 0;
  value.events.forEach((event) => {
    if (!isObject(event) || !natural(event.sequence) || event.sequence < 1 || event.sequence <= sequence
      || !(event.incomplete === true ? optionalString(event.summary, 20000) : isString(event.summary, 20000))
      || (event.incomplete !== true && (!isString(event.kind, 80) || !time(event.occurredAt) || event.occurredAt === null))
      || (event.agentId !== undefined && event.agentId !== null && !(event.incomplete === true ? isString(event.agentId, 256) : Object.hasOwn(HISTORY_AGENT_NAMES, event.agentId)))) throw new TypeError('Invalid history event');
    sequence = event.sequence;
  });
  value.assets.forEach((asset) => {
    if (!isObject(asset) || !isString(asset.name, 2000) || !['chibi', 'realistic'].includes(asset.styleMode) || !natural(asset.styleVersion)
      || !Array.isArray(asset.modelIds) || asset.modelIds.length > 100 || !safeHistoryViewerUrl(asset.viewerUrl, asset.assetId)) throw new TypeError('Invalid history asset');
    validateHistoryId(asset.assetId); validateHistoryId(asset.characterId); asset.modelIds.forEach(validateHistoryId);
    if (asset.models !== undefined) {
      if (!Array.isArray(asset.models) || asset.models.length > 100 || new Set(asset.models.map((model) => model?.modelId)).size !== asset.models.length) throw new TypeError('Invalid history model metadata');
      asset.models.forEach((model) => {
        if (!isObject(model) || !asset.modelIds.includes(model.modelId) || !optionalString(model.origin, 200) || !optionalString(model.format, 80) || !optionalString(model.title, 2000)) throw new TypeError('Invalid history model source');
        validateHistoryId(model.modelId);
      });
    }
  });
  return value;
}
