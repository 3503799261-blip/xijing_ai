import { validateHistoryId, validateHistoryList, validateHistoryDetail, HISTORY_TASK_STATES } from './history-contracts.js?v=phase5-wp2-1';

export class HistoryReadError extends Error {
  constructor(code, message) { super(message); this.name = 'HistoryReadError'; this.code = code; }
}
const allowedCodes = Object.freeze({ AGENT_TASK_NOT_FOUND: '历史任务不存在，请核对完整任务ID；不会重新创建任务。', AGENT_HISTORY_UNAVAILABLE: '历史数据库暂时无法读取，请检查后端后手动重试。', AGENT_HISTORY_CORRUPT: '历史记录结构不完整，暂时无法展示；不会自动补写记录。', INVALID_TASK_ID: '任务ID格式无效，请填写完整任务ID。' });
function historyBase() {
  const configured = globalThis.document?.querySelector('meta[name="ai-workshop-api-base"]')?.content?.trim() || '/api/v1';
  const origin = globalThis.location?.origin || 'http://127.0.0.1:8000';
  try {
    const base = new URL(configured, origin);
    if (!['https:', 'http:'].includes(base.protocol) || base.username || base.password || base.search || base.hash) throw new Error();
    return `${base.href.replace(/\/$/, '')}/agent/history`;
  } catch { throw new HistoryReadError('HISTORY_CONFIGURATION_INVALID', '历史服务地址配置无效，请检查后端地址。'); }
}
async function readHistory(url, validate, { signal, timeoutMs = 10000 } = {}) {
  const controller = new AbortController();
  const abort = () => controller.abort();
  if (signal?.aborted) abort(); else signal?.addEventListener('abort', abort, { once: true });
  const timeout = setTimeout(abort, timeoutMs);
  try {
    const response = await fetch(url, { method: 'GET', headers: { Accept: 'application/json' }, credentials: 'omit', cache: 'no-store', signal: controller.signal });
    let body;
    try { body = await response.json(); } catch { throw new HistoryReadError('HISTORY_INVALID_RESPONSE', '历史服务返回的数据格式异常，请手动重新读取。'); }
    if (!response.ok) {
      const code = typeof body?.error?.code === 'string' && /^[A-Z0-9_]{1,80}$/.test(body.error.code) ? body.error.code : 'HISTORY_READ_FAILED';
      throw new HistoryReadError(code, allowedCodes[code] || (response.status === 404 ? allowedCodes.AGENT_TASK_NOT_FOUND : `历史记录暂时无法读取（HTTP ${response.status}），请手动重新查询。`));
    }
    try { return validate(body); } catch { throw new HistoryReadError('HISTORY_INVALID_RESPONSE', '历史服务返回的数据格式异常，未展示未经校验的记录。请手动重新读取。'); }
  } catch (error) {
    if (signal?.aborted) throw new HistoryReadError('HISTORY_READ_CANCELLED', '已停止旧的历史读取。');
    if (controller.signal.aborted) throw new HistoryReadError('HISTORY_READ_TIMEOUT', '历史读取超时，请检查服务后手动重试；不会重新执行Agent。');
    if (error instanceof HistoryReadError) throw error;
    throw new HistoryReadError('HISTORY_NETWORK_ERROR', '无法连接历史服务，请确认后端已启动，再手动重新读取。');
  } finally { clearTimeout(timeout); signal?.removeEventListener('abort', abort); }
}
export function listAgentHistory({ page = 1, pageSize = 10, state = '', taskType = '', taskId = '' } = {}, options) {
  if (!Number.isSafeInteger(page) || page < 1 || !Number.isSafeInteger(pageSize) || pageSize < 1 || pageSize > 50
    || (state !== '' && !Object.hasOwn(HISTORY_TASK_STATES, state)) || !['', 'character_creation'].includes(taskType)) throw new HistoryReadError('HISTORY_INVALID_QUERY', '历史查询条件无效，请重新选择。');
  const query = new URLSearchParams({ page: String(page), pageSize: String(pageSize) });
  if (state) query.set('state', state);
  if (taskType) query.set('taskType', taskType);
  if (taskId) { try { query.set('taskId', validateHistoryId(taskId)); } catch { throw new HistoryReadError('INVALID_TASK_ID', allowedCodes.INVALID_TASK_ID); } }
  return readHistory(`${historyBase()}?${query}`, validateHistoryList, options);
}
export function getAgentHistoryDetail(taskId, { eventPage = 1, eventPageSize = 30, ...options } = {}) {
  try { validateHistoryId(taskId); } catch { throw new HistoryReadError('INVALID_TASK_ID', allowedCodes.INVALID_TASK_ID); }
  if (!Number.isSafeInteger(eventPage) || eventPage < 1 || !Number.isSafeInteger(eventPageSize) || eventPageSize < 1 || eventPageSize > 100) throw new HistoryReadError('HISTORY_INVALID_QUERY', '历史事件分页无效，请重新读取。');
  const query = new URLSearchParams({ eventPage: String(eventPage), eventPageSize: String(eventPageSize) });
  return readHistory(`${historyBase()}/${encodeURIComponent(taskId)}?${query}`, (body) => {
    const value = validateHistoryDetail(body);
    if (value.task.taskId !== taskId) throw new TypeError('Mismatched history task');
    return value;
  }, options);
}
