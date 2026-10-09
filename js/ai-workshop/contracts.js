/**
 * 前端数据约定。这里只定义未来服务的数据形状，不生成执行记录或 AI 内容。
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
});

export const SERVICE_MESSAGES = Object.freeze({
  questionAnswering: '京剧AI知识问答正在建设中，将在Phase 2接入私有知识库。',
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
