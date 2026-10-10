import { SERVICE_CAPABILITIES, SERVICE_MESSAGES, validateCapabilities, validateQuestionAnswer, validateServiceError } from './contracts.js?v=phase2-1';

const CHAT_TIMEOUT_MS = 55000;
const CAPABILITY_TIMEOUT_MS = 8000;
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

/** @param {import('./contracts.js').CreationBrief} _brief */
export async function startAgentWorkflow(_brief) { return unavailable('agentWorkflow'); }

/** @param {import('./contracts.js').CreationBrief} _brief */
export async function generateConceptImage(_brief) { return unavailable('conceptImage'); }

/** @param {{imageId: string}} _request */
export async function submitModelTask(_request) { return unavailable('imageToModel'); }
