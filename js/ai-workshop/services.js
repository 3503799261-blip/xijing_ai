import { SERVICE_CAPABILITIES, SERVICE_MESSAGES, CREATION_STYLES, validateCapabilities, validateQuestionAnswer, validateServiceError, validateWorkflowCreated, validateWorkflowStatus, validateWorkflowResult, validateWorkflowTaskId } from './contracts.js?v=phase3-1';

const CHAT_TIMEOUT_MS = 55000;
const CAPABILITY_TIMEOUT_MS = 8000;
const WORKFLOW_TIMEOUT_MS = 10000;
let capabilities = SERVICE_CAPABILITIES;
let capabilityRequest = null;
let capabilityGeneration = 0;

export class ServiceError extends Error {
  constructor(code, message, retryable = false, requestId = '') {
    super(message);
    this.name = 'ServiceError';
    this.code = code;
    this.retryable = retryable;
    this.requestId = requestId;
  }
}

/** 同步只读缓存；是否可用以实际后端检查为准，初始全部false。 */
export function getServiceCapabilities() {
  return capabilities;
}

/** 免费重查能力所需的连接/模型错误，不触发聊天或供应商重试。 */
export function requiresCapabilityRecheck(error) {
  return error instanceof ServiceError && (['NETWORK_ERROR', 'REQUEST_TIMEOUT', 'SEARCH_TIMEOUT', 'SERVICE_ERROR'].includes(error.code) || error.code.startsWith('LLM_'));
}

function invalidateCapabilities() {
  capabilityGeneration += 1;
  capabilities = SERVICE_CAPABILITIES;
}

/** 客户端提交标识仅用于幂等控制，不伪装成服务器requestId。 */
export function createSubmissionKey() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  return `submit-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 14)}`;
}

function apiUrl(path) {
  const configured = globalThis.document?.querySelector('meta[name="ai-workshop-api-base"]')?.content?.trim() || '/api/v1';
  const origin = globalThis.location?.origin || 'http://127.0.0.1:8000';
  let base;
  try {
    base = new URL(configured, origin);
    if (!['http:', 'https:'].includes(base.protocol) || base.username || base.password || base.search || base.hash) throw new Error();
  } catch {
    throw new ServiceError('API_CONFIGURATION_INVALID', '知识服务地址配置无效，请检查页面的后端地址配置。');
  }
  return `${base.href.replace(/\/$/, '')}/${path}`;
}

async function requestJson(path, options, timeoutMs) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(apiUrl(path), { ...options, signal: controller.signal, credentials: 'omit' });
    let body;
    try {
      body = await response.json();
    } catch {
      if (controller.signal.aborted) throw new ServiceError('REQUEST_TIMEOUT', '知识服务响应超时。请确认服务状态后手动重试，页面不会自动重复调用模型。', true);
      throw new ServiceError('INVALID_RESPONSE', '知识服务返回了无法读取的数据，请检查后端后重试。', true);
    }
    if (!response.ok) {
      const validated = validateServiceError(body);
      if (validated) throw new ServiceError(validated.error.code, validated.error.message, validated.error.retryable, validated.requestId);
      throw new ServiceError('SERVICE_ERROR', `知识服务暂时无法完成请求（HTTP ${response.status}），请检查后端后重试。`, response.status >= 500 || response.status === 429);
    }
    return body;
  } catch (error) {
    if (error instanceof ServiceError) throw error;
    if (controller.signal.aborted) throw new ServiceError('REQUEST_TIMEOUT', '知识服务响应超时。请确认服务状态后手动重试，页面不会自动重复调用模型。', true);
    throw new ServiceError('NETWORK_ERROR', '无法连接知识服务。请确认后端已启动、网络正常，再手动重试。', true);
  } finally {
    clearTimeout(timeout);
  }
}

/** 显式查询真实服务状态；同时查询合并，不轮询或调用付费模型。 */
export async function loadServiceCapabilities() {
  if (capabilityRequest?.generation === capabilityGeneration) return capabilityRequest.promise;
  const generation = capabilityGeneration;
  const request = (async () => {
    try {
      const body = await requestJson('capabilities', { method: 'GET', headers: { Accept: 'application/json' } }, CAPABILITY_TIMEOUT_MS);
      let validated;
      try {
        validated = validateCapabilities(body);
      } catch {
        throw new ServiceError('INVALID_RESPONSE', '知识服务能力信息无效，请检查后端后重试。', true);
      }
      // 连接失败前发出的检查不能将已失效的缓存重新写为就绪。
      if (generation === capabilityGeneration) capabilities = validated;
      return capabilities;
    } catch (error) {
      if (generation === capabilityGeneration) capabilities = SERVICE_CAPABILITIES;
      throw error;
    }
  })();
  capabilityRequest = { generation, promise: request };
  try {
    return await request;
  } finally {
    if (capabilityRequest?.promise === request) capabilityRequest = null;
  }
}

/**
 * @param {import('./contracts.js').QuestionRequest} request
 * @param {{idempotencyKey: string}} options 同一逻辑问题手动重试时沿用同一标识
 * @returns {Promise<import('./contracts.js').QuestionAnswer>}
 */
export async function askOperaQuestion(request, { idempotencyKey = createSubmissionKey() } = {}) {
  if (!request || typeof request.question !== 'string' || !request.question.trim() || request.question.length > 600) {
    throw new ServiceError('INVALID_QUESTION', '请填写不超过600字的京剧问题，不能只输入空格。');
  }
  if (typeof idempotencyKey !== 'string' || !/^[A-Za-z0-9_-]{8,128}$/.test(idempotencyKey)) {
    throw new ServiceError('INVALID_REQUEST_ID', '本次提交标识无效，请重新发送问题。');
  }
  const payload = { question: request.question.trim() };
  if (request.conversationId !== undefined) {
    if (typeof request.conversationId !== 'string' || request.conversationId.length > 128) throw new ServiceError('INVALID_CONVERSATION', '会话标识无效，请刷新后重试。');
    payload.conversationId = request.conversationId;
  }
  let body;
  try {
    body = await requestJson('chat', {
      method: 'POST',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json', 'X-Idempotency-Key': idempotencyKey },
      body: JSON.stringify(payload),
    }, CHAT_TIMEOUT_MS);
  } catch (error) {
    if (requiresCapabilityRecheck(error)) invalidateCapabilities();
    throw error;
  }
  try {
    return validateQuestionAnswer(body);
  } catch {
    throw new ServiceError('INVALID_RESPONSE', '知识服务回答或引用校验失败，未展示未经验证的回答。请检查后端后重试。', true);
  }
}

/** @param {import('./contracts.js').Capability} capability */
function unavailable(capability) {
  return Object.freeze({ available: false, status: 'unavailable', capability, message: SERVICE_MESSAGES[capability] });
}

function workflowIdentifier(value) {
  try { return validateWorkflowTaskId(value); }
  catch { throw new ServiceError('INVALID_TASK_ID', '任务标识无效，请重新提交或检查本页面保存的任务。'); }
}

async function workflowRequest(path, options, validator) {
  let body;
  try { body = await requestJson(`agent/${path}`, options, WORKFLOW_TIMEOUT_MS); }
  catch (error) {
    if (requiresCapabilityRecheck(error)) invalidateCapabilities();
    throw error;
  }
  try { return validator(body); }
  catch { throw new ServiceError('INVALID_WORKFLOW_RESPONSE', '协作服务返回的任务结构或证据未通过校验。页面保留上次状态，请重新查询。', true); }
}

/** A POST creates a persistent task. A manual retry of this logical submission must reuse its key and body. */
export async function startAgentWorkflow(brief, { idempotencyKey = createSubmissionKey() } = {}) {
  if (!brief || typeof brief.requirements !== 'string' || !brief.requirements.trim() || brief.requirements.length > 1200
      || !CREATION_STYLES.includes(brief.style)) throw new ServiceError('INVALID_CREATION_BRIEF', '请填写不超过1200字的创作需求，并选择现有风格。');
  if (typeof idempotencyKey !== 'string' || !/^[A-Za-z0-9_-]{8,128}$/.test(idempotencyKey)) throw new ServiceError('INVALID_REQUEST_ID', '本次提交标识无效，请明确开始一次新创作。');
  const payload = { requirements: brief.requirements.trim(), style: brief.style };
  if (brief.parentTaskId !== undefined) payload.parentTaskId = workflowIdentifier(brief.parentTaskId);
  return workflowRequest('create', {
    method: 'POST', headers: { Accept: 'application/json', 'Content-Type': 'application/json', 'X-Idempotency-Key': idempotencyKey }, body: JSON.stringify(payload),
  }, validateWorkflowCreated);
}

export async function getAgentWorkflowStatus(taskId, { afterSequence = 0 } = {}) {
  if (!Number.isSafeInteger(afterSequence) || afterSequence < 0) throw new ServiceError('INVALID_TASK_SEQUENCE', '任务查询序号无效，请重新查询。');
  return workflowRequest(`status/${workflowIdentifier(taskId)}?afterSequence=${afterSequence}`, {
    method: 'GET', headers: { Accept: 'application/json' },
  }, validateWorkflowStatus);
}

export async function getAgentWorkflowResult(taskId) {
  return workflowRequest(`result/${workflowIdentifier(taskId)}`, { method: 'GET', headers: { Accept: 'application/json' } }, validateWorkflowResult);
}

export async function confirmAgentWorkflow(taskId, { confirmationId, expectedSequence } = {}) {
  if (!Number.isSafeInteger(expectedSequence) || expectedSequence < 0) throw new ServiceError('INVALID_TASK_SEQUENCE', '任务已变化，请先重新查询再确认。');
  return workflowRequest(`confirm/${workflowIdentifier(taskId)}`, {
    method: 'POST', headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
    body: JSON.stringify({ confirmationId: workflowIdentifier(confirmationId), expectedSequence, action: 'accept' }),
  }, validateWorkflowStatus);
}

export async function cancelAgentWorkflow(taskId, { expectedSequence } = {}) {
  if (!Number.isSafeInteger(expectedSequence) || expectedSequence < 0) throw new ServiceError('INVALID_TASK_SEQUENCE', '任务已变化，请先重新查询再取消。');
  return workflowRequest(`cancel/${workflowIdentifier(taskId)}`, {
    method: 'POST', headers: { Accept: 'application/json', 'Content-Type': 'application/json' }, body: JSON.stringify({ expectedSequence }),
  }, validateWorkflowStatus);
}

/** @param {import('./contracts.js').CreationBrief} _brief */
export async function generateConceptImage(_brief) { return unavailable('conceptImage'); }

/** @param {{imageId: string}} _request */
export async function submitModelTask(_request) { return unavailable('imageToModel'); }
