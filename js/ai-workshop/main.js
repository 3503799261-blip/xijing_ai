import { askOperaQuestion, getServiceCapabilities, loadServiceCapabilities, requiresCapabilityRecheck, ServiceError, createSubmissionKey } from './services.js?v=phase3-1';
import { safeCitationUrl } from './contracts.js?v=phase3-1';
import { initializeAgentWorkflow } from './agent-workflow.js?v=phase3-1';

const PANEL_NAMES = ['overview', 'qa', 'agents', 'create', 'model'];
const MAX_QUESTION_LENGTH = 600;
const MAX_BRIEF_LENGTH = 1200;
const MAX_QUESTION_TURNS = 12;

function initializeWorkshop() {
  const root = document.querySelector('#ai-workshop');
  if (!root) return;

  const required = (selector) => {
    const element = root.querySelector(selector);
    if (!element) throw new Error(`AI戏韵工坊缺少必要元素：${selector}`);
    return element;
  };

  // 先核对完整结构。模块无法正常初始化时，HTML 中的提交按钮仍保持禁用。
  const panels = PANEL_NAMES.map((name) => ({
    name,
    element: required(`[data-ai-workshop-panel="${name}"]`),
    heading: required(`[data-ai-workshop-panel="${name}"] h2[tabindex="-1"]`),
  }));
  const navigation = [...root.querySelectorAll('[data-ai-workshop-target]')];
  const questionForm = required('#ai-workshop-question-form');
  const question = required('#ai-workshop-question');
  const questionCount = required('#ai-workshop-question-count');
  const questionError = required('#ai-workshop-question-error');
  const sendButton = required('#ai-workshop-send');
  const messages = required('#ai-workshop-messages');
  const qaStatus = required('#ai-workshop-qa-status');
  const qaLoading = required('#ai-workshop-qa-loading');
  const qaServiceError = required('#ai-workshop-qa-service-error');
  const retryQuestionButton = required('#ai-workshop-retry-question');
  const refreshServiceButton = required('#ai-workshop-refresh-service');
  const citationsPanel = required('#ai-workshop-citations');
  const heroServiceNote = required('#ai-workshop-hero-service-note');
  const capabilityBadges = [...root.querySelectorAll('[data-ai-workshop-qa-capability]')];
  const creationForm = required('#ai-workshop-creation-form');
  const brief = required('#ai-workshop-brief');
  const style = required('#ai-workshop-style');
  const briefError = required('#ai-workshop-brief-error');
  const draftContent = required('#ai-workshop-draft-content');
  const draftStatus = required('#ai-workshop-draft-status');
  const saveDraftButton = required('#ai-workshop-save-draft');
  const resetDraftButton = required('#ai-workshop-reset-draft');
  const notice = required('#ai-workshop-notice');
  const initialDraftText = draftContent.textContent.trim();
  let activePanel = null;
  let pending = false;
  let capabilityLoading = false;
  let capabilityRefreshId = 0;
  let lastFailedTurn = null;
  let agentController = null;
  const turns = [];

  function updateScrollOffset() {
    const header = document.querySelector('.site-header');
    root.style.setProperty('--ai-workshop-scroll-offset', `${(header?.offsetHeight ?? 82) + 24}px`);
  }
  updateScrollOffset();
  window.addEventListener('resize', updateScrollOffset);

  const panelFromHash = () => {
    const match = window.location.hash.match(/^#ai-workshop-(overview|qa|agents|create|model)$/);
    if (match) return match[1];
    if (!window.location.hash || window.location.hash === '#ai-workshop') return 'overview';
    return null;
  };

  function selectPanel(name, focusHeading = false) {
    if (!PANEL_NAMES.includes(name)) return;
    panels.forEach((panel) => {
      panel.element.hidden = panel.name !== name;
    });
    navigation.forEach((link) => {
      const isCurrent = link.dataset.aiWorkshopTarget === name;
      link.classList.toggle('ai-workshop-is-active', isCurrent);
      if (isCurrent) link.setAttribute('aria-current', 'page');
      else link.removeAttribute('aria-current');
    });
    root.dataset.activePanel = name;
    activePanel = name;
    if (focusHeading) panels.find((panel) => panel.name === name).heading.focus();
    if (name === 'qa' && !getServiceCapabilities().questionAnswering) void refreshCapabilities();
  }

  navigation.forEach((link) => {
    link.addEventListener('click', (event) => {
      // 保留浏览器在新标签页打开链接的标准操作。
      if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      const name = link.dataset.aiWorkshopTarget;
      if (!PANEL_NAMES.includes(name)) return;
      event.preventDefault();
      selectPanel(name, true);
      const hash = `#ai-workshop-${name}`;
      if (window.location.hash !== hash) window.history.pushState(null, '', hash);
    });
  });

  function restorePanel() {
    const name = panelFromHash();
    // 回顶与其他原生锚点保持浏览器的滚动习惯；只有明确面板入口转移焦点。
    const isPanelAnchor = /^#ai-workshop-/.test(window.location.hash);
    if (name && name !== activePanel) selectPanel(name, isPanelAnchor);
  }
  window.addEventListener('popstate', restorePanel);
  window.addEventListener('hashchange', restorePanel);

  function clearError(input, error) {
    input.removeAttribute('aria-invalid');
    error.textContent = '';
    error.hidden = true;
  }

  function validate(input, error, maximum, fieldName) {
    const value = input.value.trim();
    let message = '';
    if (!value) message = `请先填写${fieldName}，不能只输入空格。`;
    else if (input.value.length > maximum) message = `${fieldName}最多${maximum}字，请缩短后重试。`;
    if (message) {
      input.setAttribute('aria-invalid', 'true');
      error.textContent = message;
      error.hidden = false;
      input.focus();
      return null;
    }
    clearError(input, error);
    return value;
  }

  function updateQuestionCount() {
    questionCount.textContent = `${question.value.length} / ${MAX_QUESTION_LENGTH} 字`;
  }
  question.addEventListener('input', () => {
    updateQuestionCount();
    clearError(question, questionError);
  });
  root.querySelectorAll('[data-ai-workshop-question]').forEach((button) => {
    button.addEventListener('click', () => {
      question.value = button.dataset.aiWorkshopQuestion;
      updateQuestionCount();
      clearError(question, questionError);
      question.focus();
    });
  });

  function textElement(tag, className, text) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    element.textContent = text;
    return element;
  }

  function setServiceState(state, text) {
    qaStatus.dataset.serviceState = state;
    qaStatus.textContent = text;
    qaStatus.hidden = false;
    root.dataset.questionServiceState = state;
  }

  function displayCapabilityState(capability, failed = false) {
    capabilityBadges.forEach((badge) => {
      badge.textContent = capability.questionAnswering ? '京剧RAG问答已就绪' : failed ? '后端连接不可用' : '问答服务未就绪';
      badge.dataset.serviceState = capability.questionAnswering ? 'ready' : 'unavailable';
      badge.classList.toggle('ai-workshop-badge-unavailable', !capability.questionAnswering);
      badge.classList.toggle('ai-workshop-badge-ready', capability.questionAnswering);
    });
    heroServiceNote.textContent = [capability.questionAnswering ? '京剧RAG问答已就绪' : failed ? '后端暂时无法连接' : '京剧问答尚未就绪',
      capability.agentWorkflow ? 'Agent协作已就绪' : 'Agent协作尚未就绪', '概念图与图生3D待接入'].join(' · ');
    agentController?.setCapability(capability);
  }

  async function refreshCapabilities({ afterRequestFailure = false } = {}) {
    if (capabilityLoading && !afterRequestFailure) return;
    const refreshId = ++capabilityRefreshId;
    capabilityLoading = true;
    refreshServiceButton.disabled = true;
    refreshServiceButton.setAttribute('aria-busy', 'true');
    const canUpdateFeedback = () => !pending && (qaServiceError.hidden || !qaServiceError.textContent);
    if (canUpdateFeedback()) setServiceState('checking', '正在检查知识服务状态……');
    try {
      const capability = await loadServiceCapabilities();
      if (refreshId !== capabilityRefreshId) return;
      displayCapabilityState(capability);
      if (canUpdateFeedback()) setServiceState(capability.questionAnswering ? 'ready' : 'unavailable', capability.questionAnswering
        ? '京剧RAG知识问答已就绪。每次提问独立检索，引用对应真实入库资料。'
        : capability.knowledgeSearch ? '检索服务已就绪，真实AI问答尚未就绪。请检查模型配置及连通检查，再重新检查服务。'
          : '后端已连接，知识问答尚未就绪。请检查知识库、检索模型与模型配置，再重新检查服务。');
    } catch (error) {
      if (refreshId !== capabilityRefreshId) return;
      displayCapabilityState(getServiceCapabilities(), true);
      if (canUpdateFeedback()) setServiceState('unavailable', error instanceof ServiceError ? error.message : '暂时无法检查知识服务，请确认后端已启动，再重新检查服务。');
    } finally {
      if (refreshId === capabilityRefreshId) {
        capabilityLoading = false;
        refreshServiceButton.disabled = false;
        refreshServiceButton.removeAttribute('aria-busy');
      }
    }
  }

  function resetReferencePanel(text) {
    citationsPanel.replaceChildren(textElement('p', 'ai-workshop-reference-empty', text));
    delete citationsPanel.dataset.requestId;
  }

  function citationDetails(citation) {
    const details = document.createElement('details');
    details.className = 'ai-workshop-citation';
    details.dataset.citationId = citation.id;
    details.append(textElement('summary', '', citation.title));
    const body = document.createElement('div');
    body.className = 'ai-workshop-citation-body';
    const kind = citation.contentKind === 'original_fact_summary' ? '本项目原创事实摘要（据所列来源核对）'
      : citation.contentKind === 'reviewed_fact_note' ? '已核查事实笔记'
        : citation.contentKind === 'source_excerpt' ? '获准资料摘录' : '入库知识片段';
    body.append(textElement('p', 'ai-workshop-citation-meta', `${kind} · 来源ID：${citation.sourceId}`));
    if (citation.locator) body.append(textElement('p', 'ai-workshop-citation-meta', `位置：${citation.locator}`));
    if (citation.excerpt) body.append(textElement('blockquote', 'ai-workshop-citation-excerpt', citation.excerpt));
    const safeUrl = safeCitationUrl(citation.url);
    if (safeUrl) {
      const link = textElement('a', 'ai-workshop-text-link', '查看来源网页 ↗');
      link.href = safeUrl;
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      body.append(link);
    }
    details.append(body);
    return details;
  }

  function showReferences(turn) {
    const result = turn.response;
    if (!result) return;
    const heading = textElement('p', 'ai-workshop-reference-question', `对应提问：${turn.question}`);
    const request = textElement('p', 'ai-workshop-citation-meta', `请求ID：${result.requestId}`);
    const items = result.citations.map(citationDetails);
    if (items.length === 0) items.push(textElement('p', 'ai-workshop-reference-empty', '此次回答没有可引用的有效资料。系统已说明资料不足。'));
    citationsPanel.replaceChildren(heading, request, ...items);
    citationsPanel.dataset.requestId = result.requestId;
  }

  function messageArticle(role, label, value) {
    const article = document.createElement('article');
    article.className = `ai-workshop-message ai-workshop-message--${role}`;
    article.dataset.messageRole = role;
    article.append(textElement('p', 'ai-workshop-message-label', label), textElement('p', 'ai-workshop-message-content', value));
    return article;
  }

  function addQuestionTurn(value) {
    const element = document.createElement('div');
    element.className = 'ai-workshop-turn';
    const turn = { element, question: value, idempotencyKey: createSubmissionKey(), response: null, failure: null };
    element.dataset.turnId = turn.idempotencyKey;
    element.append(messageArticle('user', '你的提问', value));
    messages.append(element);
    turns.push(turn);
    while (turns.length > MAX_QUESTION_TURNS) turns.shift().element.remove();
    return turn;
  }

  function appendAnswer(turn, result) {
    const article = messageArticle('assistant', result.citations.length ? '京剧AI助手 · 基于检索证据' : '知识服务 · 资料不足说明', result.answer);
    article.dataset.requestId = result.requestId;
    if (result.uncertain) article.append(textElement('p', 'ai-workshop-uncertain', '资料不足或仅部分支持：请结合引用查看回答适用范围。'));
    const references = document.createElement('details');
    references.className = 'ai-workshop-answer-references';
    references.append(textElement('summary', '', `本次参考资料（${result.citations.length}）`));
    result.citations.forEach((citation) => references.append(citationDetails(citation)));
    if (!result.citations.length) references.append(textElement('p', 'ai-workshop-reference-empty', '没有足以支撑此问题的有效资料。'));
    article.append(references);
    const referenceButton = textElement('button', 'ai-workshop-text-link', '在资料区查看本次依据');
    referenceButton.type = 'button';
    referenceButton.addEventListener('click', () => showReferences(turn));
    article.append(referenceButton, textElement('small', 'ai-workshop-request-id', `请求ID：${result.requestId}`));
    turn.element.append(article);
    showReferences(turn);
  }

  function setPending(value) {
    pending = value;
    sendButton.disabled = value;
    retryQuestionButton.disabled = value;
    questionForm.setAttribute('aria-busy', String(value));
    messages.setAttribute('aria-busy', String(value));
    qaLoading.hidden = !value;
    if (value) setServiceState('loading', '已提交问题，正在等待知识服务。请勿重复发送。');
  }

  async function sendQuestion(turn) {
    if (pending) return;
    setPending(true);
    qaServiceError.hidden = true;
    retryQuestionButton.hidden = true;
    lastFailedTurn = null;
    turn.failure?.remove();
    turn.failure = null;
    resetReferencePanel('本次问题正在处理，尚无返回的资料。历史回答的依据可在各回合内展开。');
    messages.scrollTop = messages.scrollHeight;
    try {
      const result = await askOperaQuestion({ question: turn.question }, { idempotencyKey: turn.idempotencyKey });
      turn.response = result;
      appendAnswer(turn, result);
      setServiceState(result.uncertain ? 'uncertain' : 'answered', result.uncertain
        ? '此次问题资料不足或仅获得部分支持，请查看回答中的限制与真实依据。'
        : '此次问答已返回。可展开本回合资料，也可在资料区查看依据。');
      if (question.value.trim() === turn.question) {
        question.value = '';
        updateQuestionCount();
      }
    } catch (error) {
      const failure = error instanceof ServiceError ? error : new ServiceError('PAGE_ERROR', '本次问答未能完成，请检查服务后重试。', true);
      const requestInfo = failure.requestId ? `（请求ID：${failure.requestId}）` : '';
      qaServiceError.textContent = `${failure.message}${requestInfo}`;
      qaServiceError.hidden = false;
      turn.failure = messageArticle('notice', '请求未完成 · 非AI回答', failure.message);
      turn.element.append(turn.failure);
      resetReferencePanel('此次请求未返回可展示的回答或引用。历史依据仍保留在对应回合。');
      setServiceState('error', '此次请求未完成；页面不会自动重发或生成替代答案。');
      if (failure.retryable) {
        lastFailedTurn = turn;
        retryQuestionButton.hidden = false;
      }
      if (requiresCapabilityRecheck(failure)) {
        displayCapabilityState(getServiceCapabilities());
        void refreshCapabilities({ afterRequestFailure: true });
      }
    } finally {
      setPending(false);
      messages.scrollTop = messages.scrollHeight;
    }
  }

  questionForm.addEventListener('submit', (event) => {
    event.preventDefault();
    if (pending) return;
    const value = validate(question, questionError, MAX_QUESTION_LENGTH, '京剧问题');
    if (value !== null) void sendQuestion(addQuestionTurn(value));
  });
  retryQuestionButton.addEventListener('click', () => {
    if (!pending && lastFailedTurn) void sendQuestion(lastFailedTurn);
  });
  refreshServiceButton.addEventListener('click', () => void refreshCapabilities());
  window.addEventListener('online', () => void refreshCapabilities());

  brief.addEventListener('input', () => clearError(brief, briefError));
  creationForm.addEventListener('submit', (event) => {
    event.preventDefault();
    const requirements = validate(brief, briefError, MAX_BRIEF_LENGTH, '角色创作需求');
    if (requirements === null) return;
    const selected = style.options[style.selectedIndex];
    const draft = {
      requirements,
      style: style.value,
      styleLabel: selected ? selected.textContent.trim() : '未选择风格',
    };
    const list = document.createElement('dl');
    list.className = 'ai-workshop-draft-list';
    [['用户需求', draft.requirements], ['选择的风格', draft.styleLabel]].forEach(([label, value]) => {
      const term = document.createElement('dt');
      term.textContent = label;
      const description = document.createElement('dd');
      description.textContent = value;
      list.append(term, description);
    });
    draftContent.replaceChildren(list);
    draftStatus.textContent = '已在当前页面整理需求草稿。此内容由你输入，未进行AI设计，刷新页面后不会保留。';
    draftStatus.hidden = false;
  });

  resetDraftButton.addEventListener('click', () => {
    creationForm.reset();
    clearError(brief, briefError);
    draftContent.textContent = initialDraftText;
    draftStatus.textContent = '本页面的需求草稿已清空。';
    draftStatus.hidden = false;
    brief.focus();
  });

  root.querySelectorAll('[data-ai-workshop-notice]').forEach((button) => {
    button.addEventListener('click', () => {
      notice.textContent = button.dataset.aiWorkshopNotice;
      notice.hidden = false;
      notice.scrollIntoView({ block: 'nearest' });
    });
  });

  updateQuestionCount();
  selectPanel(panelFromHash() || 'overview');
  root.classList.add('ai-workshop-ready');
  sendButton.disabled = false;
  saveDraftButton.disabled = false;
  try {
    agentController = initializeAgentWorkflow({ root, selectPanel, refreshCapabilities });
  } catch {
    notice.textContent = 'Agent界面未能初始化，请刷新后重试。京剧问答和页面内草稿仍可使用。';
    notice.hidden = false;
  }
  void refreshCapabilities();
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeWorkshop, { once: true });
} else {
  initializeWorkshop();
}
