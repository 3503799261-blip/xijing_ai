/** Manual, same-origin, read-only local diagnostics. No provider requests or model execution. */
export const DEMO_IDENTITIES = Object.freeze({
  taskId: 'ca7007e7-e535-4b1f-a9b6-1932f10e20b4',
  assetId: '9e2b42e1-bbad-4a2f-ab1b-aeda18015dee',
  realisticModelId: '1fa0b519-caf4-4009-aec2-f20b0f9a3523',
  internalModelId: '3777a880-fc8c-4766-aade-948d20c6b8f0',
});
const isObject = (value) => value !== null && typeof value === 'object' && !Array.isArray(value);
const natural = (value) => Number.isSafeInteger(value) && value >= 0;
const hash = (value) => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
const messages = Object.freeze({
  401: '读取权限不足，请检查本地服务权限；不会改用生成接口。',
  403: '当前访问被拒绝，请检查本地访问条件；不会绕过访问限制。',
  404: '对应的本地记录不存在，请核对私有资源与原资产记录。',
  429: '本地服务当前请求受限，请稍后手动重新检查。',
  503: '本地服务尚未就绪，请检查启动状态后手动重试。',
});
function apiBase() {
  const origin = globalThis.location?.origin || 'http://127.0.0.1:8000';
  const configured = globalThis.document?.querySelector('meta[name="ai-workshop-api-base"]')?.content?.trim() || '/api/v1';
  const base = new URL(configured, origin);
  if (!['http:', 'https:'].includes(base.protocol) || base.origin !== origin || base.username || base.password || base.search || base.hash) throw new TypeError('Invalid demo API configuration');
  return base.href.replace(/\/$/, '');
}
const checks = Object.freeze([
  { key: 'backend', label: '本地后端与知识检索条件', path: '/health', inspect(value) {
    if (!isObject(value) || !['ready', 'degraded'].includes(value.status) || ['knowledge', 'embedding', 'llmConfigured', 'llmVerified'].some((key) => typeof value[key] !== 'boolean')
      || !natural(value.documents) || !natural(value.chunks) || !isObject(value.agents) || typeof value.agents.supervisorReady !== 'boolean'
      || !(value.agents.activeTaskId === null || typeof value.agents.activeTaskId === 'string')) throw new TypeError();
    const knowledge = value.knowledge && value.embedding;
    return { state: knowledge ? 'ready' : 'warning', message: `${knowledge ? `本地知识检索条件可用，资料${value.documents}份、片段${value.chunks}条。` : '本地知识库或Embedding尚未就绪，可先查看文化页面及已有资产。'}${value.agents.activeTaskId ? '后台记录存在活动任务；导览不会停止或重新执行它。' : '此快照未记录正在执行的Agent任务。'}LLM配置及既有验证状态不代表今日DeepSeek网络连通性，本次未调用模型。` };
  } },
  { key: 'history', label: '已保存Agent历史记录', path: '/agent/history?page=1&pageSize=1', inspect(value) {
    if (!isObject(value) || !Array.isArray(value.items) || value.items.length > 1 || !natural(value.total) || value.page !== 1 || value.pageSize !== 1
      || !isObject(value.source) || value.source.kind !== 'persisted_history' || value.source.readOnly !== true
      || value.items.some((item) => !isObject(item) || typeof item.taskId !== 'string' || item.sourceType !== 'persisted_history')) throw new TypeError();
    return { state: value.total > 0 ? 'ready' : 'warning', message: value.total > 0 ? `可只读查询${value.total}条持久化历史。打开历史档案后仍需手动读取；这不是新Agent执行。` : '当前没有可读取的持久化历史，不使用测试夹具代替真实任务。' };
  } },
  { key: 'model', label: '已有写实模型登记信息', path: `/assets/models/${DEMO_IDENTITIES.realisticModelId}`, inspect(value) {
    if (!isObject(value) || value.modelId !== DEMO_IDENTITIES.realisticModelId || value.assetId !== DEMO_IDENTITIES.assetId || value.origin !== 'neural4d'
      || value.format !== 'glb' || !hash(value.hash) || !natural(value.size) || value.size < 20) throw new TypeError();
    return { state: 'ready', message: '“绛绣·戏韵”的历史真实GLB登记可读取。本项未下载或检查GLB渲染；实际加载与交互以Viewer当前状态为准。' };
  } },
  { key: 'quota', label: 'Neural4D额度台账与创建状态', path: '/assets/usage', inspect(value) {
    if (!isObject(value) || value.max_calls !== 3 || typeof value.history_verified !== 'boolean' || typeof value.realEnabled !== 'boolean'
      || ![value.used_calls, value.remaining_calls].every((item) => item === null || (natural(item) && item <= 3))
      || (value.history_verified && (value.used_calls === null || value.remaining_calls !== 3 - value.used_calls))) throw new TypeError();
    if (!value.history_verified || value.used_calls === null || value.remaining_calls === null) return { state: 'warning', message: '历史额度尚不能核实，不推断使用次数。导览不会修改配额或发起建模。' };
    if (value.realEnabled || value.used_calls !== 2 || value.remaining_calls !== 1) return { state: 'warning', message: `当前只读台账：已用${value.used_calls}/3、剩余${value.remaining_calls}次，创建${value.realEnabled ? '未显示关闭' : '关闭'}，与已验收基线需人工核对。不得继续创建模型。` };
    return { state: 'ready', message: '全局已用2/3、剩余1次未使用，真实创建关闭。用户已取消第三次建模；本次不提交任务、不修改次数。' };
  } },
]);
async function checkOne(check, base, { fetchImpl, signal, timeoutMs }) {
  const controller = new AbortController();
  const abort = () => controller.abort();
  if (signal?.aborted) abort(); else signal?.addEventListener('abort', abort, { once: true });
  const timer = setTimeout(abort, timeoutMs);
  try {
    if (controller.signal.aborted) throw new Error('Cancelled');
    const response = await fetchImpl(`${base}${check.path}`, { method: 'GET', headers: { Accept: 'application/json' }, credentials: 'omit', cache: 'no-store', redirect: 'error', signal: controller.signal });
    if (!response.ok) return { key: check.key, label: check.label, state: 'error', message: messages[response.status] || '本地只读接口暂时无法完成检查，请手动重试。' };
    let value;
    try { value = await response.json(); } catch { return { key: check.key, label: check.label, state: 'error', message: '本地接口返回的数据格式异常，未据此判断可用状态。' }; }
    try { return { key: check.key, label: check.label, ...check.inspect(value) }; }
    catch { return { key: check.key, label: check.label, state: 'error', message: '返回记录缺少必要字段或关联不符，未展示未经核对的可用状态。' }; }
  } catch {
    return { key: check.key, label: check.label, state: 'error', message: signal?.aborted ? '本轮只读检查已停止。' : controller.signal.aborted ? '本地只读检查超时，请手动重试；不会自动调用模型。' : '无法连接本地服务，请确认后端已启动；可使用只读备用演示。' };
  } finally { clearTimeout(timer); signal?.removeEventListener('abort', abort); }
}
/** Four independent GET checks are initiated only by an explicit caller action. */
export async function checkDemoConditions({ fetchImpl = globalThis.fetch, signal, timeoutMs = 10000 } = {}) {
  let base;
  try { base = apiBase(); } catch {
    return { checkedAt: new Date().toISOString(), checks: checks.map(({ key, label }) => ({ key, label, state: 'error', message: '导览只接受当前站点的本地后端地址，请检查页面配置。' })), paidCalls: 0 };
  }
  const results = await Promise.all(checks.map((check) => checkOne(check, base, { fetchImpl, signal, timeoutMs })));
  return { checkedAt: new Date().toISOString(), checks: results, paidCalls: 0 };
}
