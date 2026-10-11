/**
 * 前端数据约定与真实后端响应校验；不生成执行记录或 AI 内容。
 * 状态只能由未来已验证的后端事件驱动，不能用计时器模拟工作流。
 */

export const AGENT_STATES = Object.freeze({
  PENDING: 'pending',
  RUNNING: 'running',
  COMPLETED: 'completed',
  FAILED: 'failed',
  AWAITING_CONFIRMATION: 'awaiting_confirmation',
});

export const AGENT_STATE_LABELS = Object.freeze({
  [AGENT_STATES.PENDING]: '待执行',
  [AGENT_STATES.RUNNING]: '运行中',
  [AGENT_STATES.COMPLETED]: '已完成',
  [AGENT_STATES.FAILED]: '执行失败',
  [AGENT_STATES.AWAITING_CONFIRMATION]: '等待用户确认',
});

export const SERVICE_CAPABILITIES = Object.freeze({
  questionAnswering: false,
  agentWorkflow: false,
  conceptImage: false,
  imageToModel: false,
  knowledgeSearch: false,
});

export const SERVICE_MESSAGES = Object.freeze({
  questionAnswering: '知识问答服务尚未就绪，请检查后端配置与知识库后重试。',
  agentWorkflow: '多Agent协作尚未接入；当前仅展示职责与流程，不执行真实任务。',
  conceptImage: 'AI概念图生成尚未接入；当前仅支持整理本页面内的用户需求草稿。',
  imageToModel: 'Neural4D图生3D尚未接入，模型生成、预览与下载暂未开放。',
});

/** @typedef {'pending'|'running'|'completed'|'failed'|'awaiting_confirmation'} AgentState */
/** @typedef {'questionAnswering'|'agentWorkflow'|'conceptImage'|'imageToModel'} Capability */

/**
 * @typedef {Object} UnavailableResult
 * @property {false} available
 * @property {'unavailable'} status
 * @property {Capability} capability
 * @property {string} message
 */

/**
 * 后续 RAG 返回的引用必须对应真实资料；前端不填充示例来源。
 * @typedef {Object} Citation
 * @property {string} id
 * @property {string} title
 * @property {string} sourceId
 * @property {string} [locator] 页码、章节或片段位置
 * @property {string} [url] 后端提供的可访问资料地址
 * @property {string} [excerpt]
 * @property {string} [contentKind] 入库事实笔记或获准资料摘录
 */

/**
 * @typedef {Object} QuestionRequest
 * @property {string} question
 * @property {string} [conversationId]
 */

/**
 * @typedef {Object} QuestionAnswer
 * @property {string} answer
 * @property {Citation[]} citations
 * @property {boolean} uncertain
 * @property {string} requestId
 */

/**
 * @typedef {Object} ServiceErrorResponse
 * @property {{code: string, message: string, retryable: boolean}} error
 * @property {string} requestId
 */

const isObject = (value) => value !== null && typeof value === 'object' && !Array.isArray(value);
const isText = (value, maximum) => typeof value === 'string' && value.trim().length > 0 && value.length <= maximum;
const optionalText = (value, maximum) => value === undefined || value === null || (typeof value === 'string' && value.length <= maximum);

/** 校验后端真实能力；图像和3D仍保持未接入。 */
export function validateCapabilities(value) {
  if (!isObject(value) || Object.keys(SERVICE_CAPABILITIES).some((key) => typeof value[key] !== 'boolean')) {
    throw new TypeError('Invalid capabilities response');
  }
  return Object.freeze({
    questionAnswering: value.questionAnswering,
    knowledgeSearch: value.knowledgeSearch,
    agentWorkflow: value.agentWorkflow,
    conceptImage: false,
    imageToModel: false,
  });
}

/** @returns {QuestionAnswer} */
export function validateQuestionAnswer(value) {
  if (!isObject(value) || !isText(value.answer, 16000) || !isText(value.requestId, 128)
      || typeof value.uncertain !== 'boolean' || !Array.isArray(value.citations) || value.citations.length > 12) {
    throw new TypeError('Invalid question answer response');
  }
  const seenIds = new Set();
  const citations = value.citations.map((citation) => {
    if (!isObject(citation) || !isText(citation.id, 128) || !isText(citation.title, 500)
        || !isText(citation.sourceId, 128) || !optionalText(citation.locator, 500)
        || !optionalText(citation.url, 2048) || !optionalText(citation.excerpt, 6000)
        || !optionalText(citation.contentKind, 100) || seenIds.has(citation.id)) {
      throw new TypeError('Invalid citation response');
    }
    seenIds.add(citation.id);
    return Object.freeze({
      id: citation.id,
      title: citation.title,
      sourceId: citation.sourceId,
      locator: citation.locator || '',
      url: citation.url || '',
      excerpt: citation.excerpt || '',
      contentKind: citation.contentKind || '',
    });
  });
  if (!value.uncertain && citations.length === 0) throw new TypeError('Missing evidence for a certain answer');
  return Object.freeze({ answer: value.answer, citations: Object.freeze(citations), uncertain: value.uncertain, requestId: value.requestId });
}

/** @returns {ServiceErrorResponse|null} */
export function validateServiceError(value) {
  if (!isObject(value) || !isObject(value.error) || !isText(value.error.code, 100)
      || !isText(value.error.message, 2000) || typeof value.error.retryable !== 'boolean'
      || !isText(value.requestId, 128)) return null;
  return { error: { code: value.error.code, message: value.error.message, retryable: value.error.retryable }, requestId: value.requestId };
}

/** 引用只接受绝对HTTP(S)网址，不接受可执行协议、用户凭证或相对服务器路径。 */
export function safeCitationUrl(value) {
  try {
    const url = new URL(value);
    if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password) return null;
    return url.href;
  } catch {
    return null;
  }
}

export const WORKFLOW_STATES = Object.freeze(['waiting', 'running', 'awaiting_confirmation', 'completed', 'failed', 'cancelled']);
export const WORKFLOW_STATE_LABELS = Object.freeze({ waiting: '等待调度', running: '协作运行中', awaiting_confirmation: '等待用户确认', completed: '已确认完成', failed: '执行失败', cancelled: '已取消' });
export const WORKFLOW_AGENT_IDS = Object.freeze(['planner', 'researcher', 'designer', 'reviewer']);
export const CREATION_STYLES = Object.freeze(['京剧写意', '国风幻想', '舞台角色']);
const isSequence = (value) => Number.isSafeInteger(value) && value >= 0;
const isIdentifier = (value) => isText(value, 128) && /^[A-Za-z0-9_-]{8,128}$/.test(value);
const isTime = (value) => value === null || value === undefined || (isText(value, 80) && Number.isFinite(Date.parse(value)));
const agentStateValues = Object.values(AGENT_STATES);
const textArray = (value, maximum = 1600, count = 24) => Array.isArray(value) && value.length <= count && value.every((item) => isText(item, maximum));
const idArray = (value, allowed = null) => textArray(value, 128, 24) && new Set(value).size === value.length && (!allowed || value.every((item) => allowed.has(item)));

/** URL path identifiers are validated before interpolation; task URLs from responses are never followed. */
export function validateWorkflowTaskId(value) {
  if (!isIdentifier(value)) throw new TypeError('Invalid workflow task identifier');
  return value;
}

export function validateWorkflowCreated(value) {
  if (!isObject(value) || !isIdentifier(value.taskId) || !isIdentifier(value.runId) || !WORKFLOW_STATES.includes(value.state)
      || !isSequence(value.sequence) || !isText(value.requestId, 128)) throw new TypeError('Invalid workflow creation response');
  return Object.freeze({ taskId: value.taskId, runId: value.runId, state: value.state, sequence: value.sequence, requestId: value.requestId });
}

/** Agent states and task states are separate; cancelled is never painted as an executed Agent. */
export function validateWorkflowStatus(value) {
  if (!isObject(value) || !isIdentifier(value.taskId) || !isIdentifier(value.runId) || !WORKFLOW_STATES.includes(value.state)
      || !isSequence(value.lastSequence) || !Number.isInteger(value.completedSteps) || value.completedSteps < 0 || value.completedSteps > 4
      || value.totalSteps !== 4 || !Array.isArray(value.agents) || value.agents.length !== 4
      || !Array.isArray(value.events) || value.events.length > 50 || typeof value.resultReady !== 'boolean'
      || typeof value.cancelRequested !== 'boolean' || !isText(value.requestId, 128)
      || (value.currentAgent !== null && value.currentAgent !== undefined && !WORKFLOW_AGENT_IDS.includes(value.currentAgent))) {
    throw new TypeError('Invalid workflow status response');
  }
  const ids = new Set();
  const agents = value.agents.map((agent) => {
    if (!isObject(agent) || !WORKFLOW_AGENT_IDS.includes(agent.id) || ids.has(agent.id) || !agentStateValues.includes(agent.state)
        || !optionalText(agent.summary, 3000) || !optionalText(agent.errorCode, 100) || !isTime(agent.startedAt) || !isTime(agent.finishedAt)) {
      throw new TypeError('Invalid workflow Agent response');
    }
    ids.add(agent.id);
    return Object.freeze({ ...agent, summary: agent.summary || '', errorCode: agent.errorCode || '' });
  });
  let previousSequence = 0;
  const events = value.events.map((event) => {
    if (!isObject(event) || event.runId !== value.runId || !isSequence(event.sequence) || event.sequence <= previousSequence
        || event.sequence > value.lastSequence || !isText(event.occurredAt, 80) || !isTime(event.occurredAt)
        || !optionalText(event.summary, 3000) || !optionalText(event.errorCode, 100)) throw new TypeError('Invalid workflow event response');
    if (event.kind === 'agent') {
      if (!WORKFLOW_AGENT_IDS.includes(event.agentId) || !agentStateValues.includes(event.state)) throw new TypeError('Invalid Agent event');
    } else if (event.kind === 'task') {
      if (!WORKFLOW_STATES.includes(event.taskState)) throw new TypeError('Invalid task event');
    } else throw new TypeError('Invalid workflow event kind');
    previousSequence = event.sequence;
    return Object.freeze({ ...event });
  });
  const confirmation = value.confirmation;
  if (confirmation !== null && confirmation !== undefined) {
    if (!isObject(confirmation) || !isIdentifier(confirmation.id) || !['final_acceptance', 'needs_revision', 'insufficient_evidence', 'clarification'].includes(confirmation.reason)
        || typeof confirmation.canAccept !== 'boolean' || (confirmation.canAccept && (value.state !== 'awaiting_confirmation' || confirmation.reason !== 'final_acceptance'))) {
      throw new TypeError('Invalid workflow confirmation');
    }
  }
  return Object.freeze({ ...value, agents: Object.freeze(agents), events: Object.freeze(events), confirmation: confirmation ? Object.freeze({ ...confirmation }) : null });
}

/** References in the design/review must be a subset of the real backend citation package. */
export function validateWorkflowResult(value) {
  if (!isObject(value) || !isIdentifier(value.taskId) || value.schemaVersion !== '1.0' || !isObject(value.design) || !isObject(value.review)
      || typeof value.uncertain !== 'boolean' || typeof value.publicationAllowed !== 'boolean' || typeof value.userConfirmed !== 'boolean'
      || !isText(value.knowledgeGeneration, 200) || !isObject(value.promptVersions) || !isText(value.requestId, 128)
      || !Array.isArray(value.citations) || value.citations.length > 12) throw new TypeError('Invalid workflow result response');
  // Reuse the Phase 2 citation validator without fabricating an answer or sources.
  const citations = validateQuestionAnswer({ answer: '资料包结构校验', citations: value.citations, uncertain: true, requestId: value.requestId }).citations;
  const allowedIds = new Set(citations.map((citation) => citation.id));
  const design = value.design;
  if (design.schemaVersion !== '1.0' || !isText(design.name, 200) || !isText(design.positioning, 2000) || !isText(design.visualPrompt, 6000)
      || !textArray(design.creativeElements) || !textArray(design.limitations) || !idArray(design.usedEvidenceIds, allowedIds)) throw new TypeError('Invalid character design');
  for (const field of ['costume', 'colors', 'visualElements']) {
    if (!Array.isArray(design[field]) || design[field].length > 16 || !design[field].every((item) => isObject(item)
        && isText(item.description, 2000) && ['evidence_based', 'creative'].includes(item.interpretation)
        && idArray(item.evidenceIds, allowedIds) && (item.interpretation !== 'evidence_based' || item.evidenceIds.length > 0)
        && item.evidenceIds.every((id) => design.usedEvidenceIds.includes(id)))) throw new TypeError('Invalid design evidence mapping');
  }
  const review = value.review;
  if (!['pass', 'needs_revision', 'insufficient_evidence'].includes(review.verdict) || !Array.isArray(review.issues) || review.issues.length > 24
      || !review.issues.every((issue) => isObject(issue) && isText(issue.field, 200) && isText(issue.reason, 2400) && idArray(issue.evidenceIds, allowedIds))
      || !textArray(review.suggestions) || !idArray(review.checkedEvidenceIds, allowedIds) || review.needsHumanReview !== true) throw new TypeError('Invalid culture review');
  if (value.publicationAllowed && (!value.userConfirmed || value.uncertain || review.verdict !== 'pass' || !citations.length)) {
    throw new TypeError('Unconfirmed or uncertain design cannot be published');
  }
  return Object.freeze({ ...value, citations });
}

/**
 * @typedef {Object} CreationBrief
 * @property {string} requirements 用户原始需求，不是 AI 设计说明
 * @property {string} style 风格选项值
 * @property {string} styleLabel 用户可见的风格名称
 */

/**
 * 后续事件必须携带运行标识及递增序号，以便处理断线重连和重复事件。
 * @typedef {Object} WorkflowEvent
 * @property {string} runId
 * @property {string} agentId
 * @property {number} sequence
 * @property {AgentState} state
 * @property {string} occurredAt 后端事件时间
 * @property {string} [summary] 真实执行摘要
 * @property {string} [confirmationId] 等待人工确认的任务标识
 * @property {string} [errorCode]
 */

/**
 * @typedef {Object} ModelTask
 * @property {string} taskId
 * @property {'queued'|'processing'|'succeeded'|'failed'} status
 * @property {number} [progress] 仅使用真实服务返回的进度
 * @property {string} [modelUrl]
 * @property {string} [downloadUrl]
 * @property {string} [errorCode]
 */
