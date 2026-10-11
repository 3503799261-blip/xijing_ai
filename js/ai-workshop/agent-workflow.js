import { AGENT_STATE_LABELS, WORKFLOW_STATE_LABELS, WORKFLOW_AGENT_IDS, safeCitationUrl, validateWorkflowTaskId } from './contracts.js?v=phase3-1';
import { startAgentWorkflow, getAgentWorkflowStatus, getAgentWorkflowResult, confirmAgentWorkflow, cancelAgentWorkflow, createSubmissionKey, getServiceCapabilities, requiresCapabilityRecheck, ServiceError } from './services.js?v=phase3-1';

const STORAGE_KEY = 'xijing.ai.agent.task.v1';
const ACTIVE_STATES = new Set(['waiting', 'running']);
const POLL_INTERVAL_MS = 1000;
const MAX_AUTOMATIC_QUERIES = 180;
const MAX_POLL_DURATION_MS = 240000;
const REASONS = { final_acceptance: '审校已通过，请阅读方案和资料后确认。', needs_revision: '文化审校提出修订要求。请调整需求后明确提交新创作。', insufficient_evidence: '当前知识资料不足以支持创作。请补充或调整需求后明确提交新创作。', clarification: '规划需要更明确的创作目标。请补充需求后明确提交新创作。' };

const text = (tag, className, value) => {
  const element = document.createElement(tag);
  if (className) element.className = className;
  element.textContent = value;
  return element;
};

/** This renders verified public artifacts, never a model's hidden reasoning or simulated progress. */
export function renderWorkflowResult(container, result) {
  const fragment = document.createElement('div');
  fragment.className = 'ai-workshop-agent-result-body';
  const design = result.design;
  fragment.append(text('span', 'ai-workshop-badge', result.publicationAllowed ? '用户已确认 · 角色文字方案' : '待确认草案 · 不可作为最终方案'),
    text('h3', '', design.name), text('p', 'ai-workshop-result-positioning', design.positioning));
  for (const [field, label] of [['costume', '服饰设计'], ['colors', '颜色设计'], ['visualElements', '视觉元素']]) {
    const section = document.createElement('section');
    section.className = 'ai-workshop-design-section';
    section.append(text('h4', '', label));
    const list = document.createElement('ul');
    for (const element of design[field]) {
      const item = document.createElement('li');
      item.append(text('span', 'ai-workshop-design-kind', element.interpretation === 'evidence_based' ? '据资料设计' : '原创演绎'),
        text('p', '', element.description));
      if (element.evidenceIds.length) item.append(text('small', 'ai-workshop-citation-meta', `依据：${element.evidenceIds.join('、')}`));
      list.append(item);
    }
    if (!design[field].length) list.append(text('li', '', '本次方案未提供此项。'));
    section.append(list);
    fragment.append(section);
  }
  for (const [label, values] of [['原创表达', design.creativeElements], ['适用范围与限制', design.limitations]]) {
    if (!values.length) continue;
    const section = document.createElement('section');
    section.className = 'ai-workshop-design-section';
    section.append(text('h4', '', label));
    const list = document.createElement('ul');
    values.forEach((value) => list.append(text('li', '', value)));
    section.append(list); fragment.append(section);
  }
  const prompt = document.createElement('details');
  prompt.className = 'ai-workshop-details';
  prompt.append(text('summary', '', '查看角色视觉提示词（文字，尚未生成图片）'), text('p', 'ai-workshop-result-prompt', design.visualPrompt));
  fragment.append(prompt);
  const review = document.createElement('section');
  review.className = 'ai-workshop-review-panel';
  const verdict = { pass: '辅助审校通过', needs_revision: '需要修订', insufficient_evidence: '资料不足' };
  review.append(text('h4', '', `文化审校：${verdict[result.review.verdict]}`),
    text('p', '', '这是AI辅助审校，仍需要你结合资料核查；不代表专业人员审核。'));
  result.review.issues.forEach((issue) => review.append(text('p', 'ai-workshop-feedback-error', `${issue.field}：${issue.reason}`)));
  result.review.suggestions.forEach((suggestion) => review.append(text('p', '', suggestion)));
  if (result.uncertain) review.append(text('p', 'ai-workshop-feedback-error', '当前草案存在不确定性，不能导出为已确认的最终方案。'));
  fragment.append(review);
  const sources = document.createElement('details');
  sources.className = 'ai-workshop-answer-references';
  sources.append(text('summary', '', `本次文化依据（${result.citations.length}）`));
  result.citations.forEach((citation) => {
    const details = document.createElement('details');
    details.className = 'ai-workshop-citation';
    details.dataset.citationId = citation.id;
    details.append(text('summary', '', citation.title));
    const body = document.createElement('div');
    body.className = 'ai-workshop-citation-body';
    body.append(text('p', 'ai-workshop-citation-meta', `项目入库事实摘要 · 证据ID：${citation.id} · 来源ID：${citation.sourceId}`));
    if (citation.locator) body.append(text('p', 'ai-workshop-citation-meta', `位置：${citation.locator}`));
    if (citation.excerpt) body.append(text('blockquote', 'ai-workshop-citation-excerpt', citation.excerpt));
    const url = safeCitationUrl(citation.url);
    if (url) {
      const link = text('a', 'ai-workshop-text-link', '查看来源网页 ↗');
      link.href = url; link.target = '_blank'; link.rel = 'noopener noreferrer'; body.append(link);
    }
    details.append(body); sources.append(details);
  });
  if (!result.citations.length) sources.append(text('p', '', '本次没有可展示的资料依据。'));
  fragment.append(sources, text('small', 'ai-workshop-citation-meta', `任务：${result.taskId} · 知识版本：${result.knowledgeGeneration}`));
  container.replaceChildren(fragment);
}

/** Failure to bind this optional feature must not interrupt Phase 2 question answering. */
export function initializeAgentWorkflow({ root, selectPanel, refreshCapabilities }) {
  const element = (id) => root.querySelector(`#ai-workshop-${id}`);
  const start = element('agent-start');
  if (!start) return null;
  const requiredNames = ['agent-submit-retry', 'agent-submit-error', 'agent-service-state', 'agent-task-state', 'agent-task-id', 'agent-progress', 'agent-feedback', 'agent-query', 'agent-service-refresh', 'agent-cancel', 'agent-new', 'agent-confirmation', 'agent-confirm-reason', 'agent-confirm', 'agent-result', 'agent-result-content', 'agent-download', 'agent-events', 'brief', 'style', 'brief-error'];
  const elements = Object.fromEntries(requiredNames.map((name) => {
    const value = element(name);
    if (!value) throw new Error(`缺少Agent界面元素：${name}`);
    return [name, value];
  }));
  const cards = WORKFLOW_AGENT_IDS.map((id) => {
    const card = root.querySelector(`[data-agent-id="${id}"]`);
    const status = card?.querySelector('[data-agent-status]');
    const summary = card?.querySelector('[data-agent-summary]');
    const timing = card?.querySelector('[data-agent-timing]');
    if (!card || !status || !summary || !timing) throw new Error(`缺少Agent卡片：${id}`);
    return { id, card, status, summary, timing };
  });
  const badges = [...root.querySelectorAll('[data-ai-workshop-agent-capability]')];
  let capable = false;
  let taskId = null;
  let runId = null;
  let snapshot = null;
  let result = null;
  let resultSequence = -1;
  let eventCursor = 0;
  let generation = 0;
  let timer = null;
  let queryPending = false;
  let resultPending = false;
  let mutationPending = false;
  let submissionPending = false;
  let pendingSubmission = null;
  let queryCount = 0;
  let pollStartedAt = 0;
  const seenEvents = new Set();

  const stopTimer = () => { if (timer !== null) clearTimeout(timer); timer = null; };
  const setFeedback = (message, error = false) => {
    elements['agent-feedback'].textContent = message;
    elements['agent-feedback'].classList.toggle('ai-workshop-feedback-error', error);
  };
  function updateControls() {
    const active = !!snapshot && ACTIVE_STATES.has(snapshot.state);
    const allStagesCompleted = snapshot?.completedSteps === 4 && snapshot.agents.every((agent) => agent.state === 'completed');
    start.disabled = !capable || submissionPending || !!pendingSubmission || active || mutationPending || queryPending || resultPending;
    start.setAttribute('aria-busy', String(submissionPending));
    elements['agent-submit-retry'].disabled = submissionPending;
    elements['agent-query'].disabled = !taskId || queryPending || mutationPending;
    elements['agent-cancel'].disabled = !snapshot || mutationPending || queryPending || snapshot.cancelRequested || ['completed', 'failed', 'cancelled'].includes(snapshot.state);
    elements['agent-confirm'].disabled = !snapshot?.confirmation?.canAccept || !allStagesCompleted || !result || result.review.verdict !== 'pass' || result.uncertain || mutationPending || queryPending || resultPending;
    elements['agent-download'].disabled = !result?.publicationAllowed || !result?.userConfirmed || snapshot?.state !== 'completed' || !allStagesCompleted;
    elements['agent-new'].disabled = active || submissionPending || mutationPending || queryPending || resultPending || !!pendingSubmission;
  }
  function setCapability(value) {
    capable = value.agentWorkflow === true;
    elements['agent-service-state'].textContent = capable ? '协作服务已就绪' : '协作服务尚未就绪';
    elements['agent-service-state'].dataset.serviceState = capable ? 'ready' : 'unavailable';
    badges.forEach((badge) => {
      badge.textContent = capable ? 'Agent协作已就绪' : '协作服务尚未就绪';
      badge.classList.toggle('ai-workshop-badge-ready', capable);
      badge.classList.toggle('ai-workshop-badge-unavailable', !capable);
    });
    updateControls();
  }
  const saveTask = () => {
    try { if (taskId) globalThis.sessionStorage?.setItem(STORAGE_KEY, taskId); }
    catch { /* Storage may be disabled. The visible task ID remains available. */ }
  };
  function scheduleQuery() {
    stopTimer();
    if (!snapshot || !ACTIVE_STATES.has(snapshot.state) || document.hidden || queryPending || mutationPending) return;
    if (queryCount >= MAX_AUTOMATIC_QUERIES || Date.now() - pollStartedAt >= MAX_POLL_DURATION_MS) {
      setFeedback('自动查询已达到时限。任务状态以最后一次后端返回为准，可点击“重新查询任务”继续查看。');
      return;
    }
    timer = setTimeout(() => { timer = null; void queryStatus(); }, POLL_INTERVAL_MS);
  }
  function displayEvents(events) {
    events.forEach((event) => {
      const key = `${event.runId}:${event.sequence}`;
      eventCursor = Math.max(eventCursor, event.sequence);
      if (seenEvents.has(key)) return;
      seenEvents.add(key);
      const label = event.kind === 'agent' ? `${event.agentId} · ${AGENT_STATE_LABELS[event.state]}` : WORKFLOW_STATE_LABELS[event.taskState];
      const item = text('li', '', `#${event.sequence} · ${label} · ${event.summary || '状态已更新'} · ${event.occurredAt}`);
      item.dataset.sequence = String(event.sequence);
      elements['agent-events'].append(item);
      while (elements['agent-events'].children.length > 50) elements['agent-events'].children[0].remove();
    });
  }
  function applyStatus(value) {
    if (value.taskId !== taskId || (runId && value.runId !== runId) || (snapshot && value.lastSequence < snapshot.lastSequence)) return false;
    runId = value.runId;
    snapshot = value;
    elements['agent-task-id'].textContent = `任务ID：${taskId}`;
    elements['agent-task-state'].textContent = WORKFLOW_STATE_LABELS[value.state];
    elements['agent-task-state'].dataset.taskState = value.state;
    elements['agent-progress'].textContent = `真实已完成阶段：${value.completedSteps} / ${value.totalSteps}`;
    cards.forEach(({ id, card, status, summary, timing }) => {
      const agent = value.agents.find((item) => item.id === id);
      status.dataset.state = agent.state;
      status.textContent = AGENT_STATE_LABELS[agent.state];
      summary.textContent = agent.summary || '暂无执行摘要。';
      timing.textContent = [agent.startedAt ? `开始：${agent.startedAt}` : '', agent.finishedAt ? `结束：${agent.finishedAt}` : '', agent.errorCode ? `错误：${agent.errorCode}` : ''].filter(Boolean).join(' · ') || '尚无执行时间。';
      card.dataset.current = String(value.state === 'running' && value.currentAgent === id);
    });
    displayEvents(value.events);
    elements['agent-confirmation'].hidden = !value.confirmation;
    if (value.confirmation) elements['agent-confirm-reason'].textContent = REASONS[value.confirmation.reason];
    elements['agent-confirm'].hidden = !value.confirmation?.canAccept;
    updateControls();
    return true;
  }
  async function loadResult(capturedGeneration) {
    if (!snapshot?.resultReady || resultPending || resultSequence === snapshot.lastSequence) return;
    const requestedTaskId = taskId;
    const requestedSequence = snapshot.lastSequence;
    resultPending = true; updateControls();
    try {
      const value = await getAgentWorkflowResult(requestedTaskId);
      if (generation !== capturedGeneration || requestedTaskId !== taskId || value.taskId !== taskId) return;
      result = value; resultSequence = requestedSequence;
      renderWorkflowResult(elements['agent-result-content'], result);
      elements['agent-result'].hidden = false;
    } catch (error) {
      if (generation === capturedGeneration) setFeedback(`任务状态已读取，方案暂时无法展示：${error instanceof ServiceError ? error.message : '请重新查询。'}`, true);
    } finally { resultPending = false; updateControls(); }
  }
  async function queryStatus({ manual = false } = {}) {
    if (!taskId || queryPending || mutationPending || document.hidden) return;
    stopTimer();
    if (manual) { queryCount = 0; pollStartedAt = Date.now(); }
    queryPending = true; queryCount += 1; updateControls();
    const capturedGeneration = generation;
    const requestedTaskId = taskId;
    let succeeded = false;
    try {
      const value = await getAgentWorkflowStatus(requestedTaskId, { afterSequence: eventCursor });
      if (generation !== capturedGeneration || requestedTaskId !== taskId) return;
      if (applyStatus(value)) {
        succeeded = true;
        setFeedback(value.cancelRequested ? '取消请求已记录，正在等待当前阶段真实收尾；已发生的模型费用仍保留。'
          : value.state === 'failed' ? '任务执行失败。请查看已返回的阶段摘要；不会自动重发付费请求。'
            : value.state === 'cancelled' ? '任务已取消，未继续启动后续阶段。'
              : value.state === 'completed' ? '你已确认最终文字方案。可以下载角色JSON，概念图和3D仍未开放。'
                : value.state === 'awaiting_confirmation' ? REASONS[value.confirmation?.reason] || '任务需要你确认或补充。'
                  : '正在读取后端真实执行状态；进度仅在阶段返回后更新。');
        await loadResult(capturedGeneration);
      }
    } catch (error) {
      if (generation !== capturedGeneration) return;
      if (error instanceof ServiceError && error.code === 'AGENT_TASK_NOT_FOUND') {
        const missingId = taskId;
        taskId = null; runId = null; snapshot = null; result = null; resultSequence = -1;
        elements['agent-task-id'].textContent = `失效的任务ID：${missingId}`;
        elements['agent-task-state'].textContent = '任务记录未找到';
        elements['agent-result'].hidden = true; elements['agent-confirmation'].hidden = true;
        try { globalThis.sessionStorage?.removeItem?.(STORAGE_KEY); } catch { /* Ignore storage restrictions. */ }
        setFeedback('保存的任务记录已失效，未自动重建。可检查协作服务后明确提交一次新创作。', true);
      } else setFeedback(`暂时无法获取任务状态。已显示的Agent状态保持上次后端结果：${error instanceof ServiceError ? error.message : '请重新查询。'}`, true);
      setCapability(getServiceCapabilities());
      if (requiresCapabilityRecheck(error)) void refreshCapabilities({ afterRequestFailure: true });
    } finally {
      queryPending = false; updateControls();
      if (succeeded && generation === capturedGeneration) scheduleQuery();
    }
  }
  async function submit(savedSubmission) {
    if (submissionPending) return;
    submissionPending = true; pendingSubmission = savedSubmission;
    elements['agent-submit-error'].hidden = true;
    elements['agent-submit-retry'].hidden = true;
    updateControls();
    try {
      const created = await startAgentWorkflow(savedSubmission.brief, { idempotencyKey: savedSubmission.key });
      stopTimer(); generation += 1;
      taskId = created.taskId; runId = created.runId; snapshot = null; result = null; resultSequence = -1;
      eventCursor = 0; seenEvents.clear(); elements['agent-events'].replaceChildren();
      elements['agent-result'].hidden = true; elements['agent-confirmation'].hidden = true;
      pendingSubmission = null; saveTask();
      elements['agent-task-id'].textContent = `任务ID：${taskId}`;
      elements['agent-task-state'].textContent = WORKFLOW_STATE_LABELS[created.state];
      elements['agent-task-state'].dataset.taskState = created.state;
      selectPanel('agents', true);
      const hash = '#ai-workshop-agents';
      if (window.location.hash !== hash) window.history.pushState(null, '', hash);
      setFeedback('任务已由后端创建，正在读取实际调度与执行状态。');
      queryCount = 0; pollStartedAt = Date.now();
      await queryStatus();
    } catch (error) {
      const failure = error instanceof ServiceError ? error : new ServiceError('PAGE_ERROR', '任务提交未能完成，请检查后重试。', true);
      elements['agent-submit-error'].textContent = `${failure.message}${failure.requestId ? `（请求ID：${failure.requestId}）` : ''}`;
      elements['agent-submit-error'].hidden = false;
      // An unreadable creation response can also hide a successfully created task.
      const mayHaveCreated = failure.retryable || failure.code === 'INVALID_WORKFLOW_RESPONSE';
      elements['agent-submit-retry'].hidden = !mayHaveCreated;
      if (!mayHaveCreated) pendingSubmission = null;
      setCapability(getServiceCapabilities());
      if (requiresCapabilityRecheck(failure)) void refreshCapabilities({ afterRequestFailure: true });
    } finally { submissionPending = false; updateControls(); }
  }
  start.addEventListener('click', () => {
    if (start.disabled || submissionPending || pendingSubmission) return;
    const requirements = elements.brief.value.trim();
    if (!requirements || elements.brief.value.length > 1200) {
      elements['brief-error'].textContent = '请填写不超过1200字的创作需求，不能只输入空格。';
      elements['brief-error'].hidden = false; elements.brief.setAttribute('aria-invalid', 'true'); elements.brief.focus(); return;
    }
    elements['brief-error'].hidden = true; elements.brief.removeAttribute('aria-invalid');
    const brief = { requirements, style: elements.style.value };
    if (taskId) brief.parentTaskId = taskId;
    void submit({ brief, key: createSubmissionKey() });
  });
  elements['agent-submit-retry'].addEventListener('click', () => { if (pendingSubmission && !submissionPending) void submit(pendingSubmission); });
  elements['agent-query'].addEventListener('click', () => void queryStatus({ manual: true }));
  elements['agent-service-refresh'].addEventListener('click', () => void refreshCapabilities());
  elements['agent-new'].addEventListener('click', () => { selectPanel('create', true); window.history.pushState(null, '', '#ai-workshop-create'); elements.brief.focus(); });
  async function mutate(action) {
    if (!snapshot || mutationPending || queryPending || (action === 'confirm' && elements['agent-confirm'].disabled)) return;
    stopTimer(); mutationPending = true; updateControls();
    const capturedGeneration = generation;
    try {
      const value = action === 'confirm'
        ? await confirmAgentWorkflow(taskId, { confirmationId: snapshot.confirmation.id, expectedSequence: snapshot.lastSequence })
        : await cancelAgentWorkflow(taskId, { expectedSequence: snapshot.lastSequence });
      if (generation !== capturedGeneration || !applyStatus(value)) return;
      setFeedback(action === 'confirm' ? '已收到后端确认结果。正在读取最终方案。' : value.cancelRequested ? '已请求取消。当前阶段收尾后停止后续调用，已发生费用不会撤回。' : '任务已取消。');
      await loadResult(capturedGeneration);
    } catch (error) {
      if (generation === capturedGeneration) setFeedback(`操作未获确认，请先重新查询任务；不会自动重发：${error instanceof ServiceError ? error.message : '请稍后重试。'}`, true);
    } finally { mutationPending = false; updateControls(); scheduleQuery(); }
  }
  elements['agent-confirm'].addEventListener('click', () => { if (!elements['agent-confirm'].disabled) void mutate('confirm'); });
  elements['agent-cancel'].addEventListener('click', () => { if (!elements['agent-cancel'].disabled) void mutate('cancel'); });
  elements['agent-download'].addEventListener('click', () => {
    if (elements['agent-download'].disabled || !result?.publicationAllowed || !result.userConfirmed || snapshot?.state !== 'completed') return;
    const exported = { schemaVersion: result.schemaVersion, taskId: result.taskId, design: result.design, review: result.review, citations: result.citations, uncertain: result.uncertain, publicationAllowed: result.publicationAllowed, userConfirmed: result.userConfirmed, knowledgeGeneration: result.knowledgeGeneration, promptVersions: result.promptVersions };
    const url = URL.createObjectURL(new Blob([JSON.stringify(exported, null, 2)], { type: 'application/json;charset=utf-8' }));
    const link = document.createElement('a'); link.href = url; link.download = `xijing-character-${result.taskId}.json`; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    setFeedback('已下载本次确认后的角色文字方案JSON。没有生成图片或3D模型。');
  });
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) stopTimer();
    else if (taskId) void queryStatus();
  });
  window.addEventListener('pagehide', stopTimer);
  setCapability(getServiceCapabilities());
  try { const saved = globalThis.sessionStorage?.getItem(STORAGE_KEY); if (saved) taskId = validateWorkflowTaskId(saved); }
  catch { /* Corrupt/blocked storage does not break QA or create a replacement task. */ }
  if (taskId) { pollStartedAt = Date.now(); setFeedback('正在查询本页面保存的任务标识；不会重新创建或调用模型。'); void queryStatus(); }
  return { setCapability };
}
