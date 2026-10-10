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

/** 校验后端真实能力；本阶段不会因服务器意外开启而显示其他三项已接入。 */
export function validateCapabilities(value) {
  if (!isObject(value) || Object.keys(SERVICE_CAPABILITIES).some((key) => typeof value[key] !== 'boolean')) {
    throw new TypeError('Invalid capabilities response');
  }
  return Object.freeze({
    questionAnswering: value.questionAnswering,
    knowledgeSearch: value.knowledgeSearch,
    agentWorkflow: false,
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
