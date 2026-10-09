import { askOperaQuestion } from './services.js';

const PANEL_NAMES = ['overview', 'qa', 'agents', 'create', 'model'];
const MAX_QUESTION_LENGTH = 600;
const MAX_BRIEF_LENGTH = 1200;
const MAX_USER_MESSAGES = 12;

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

  function appendUserQuestion(value) {
    const message = document.createElement('article');
    message.className = 'ai-workshop-message ai-workshop-message--user';
    message.dataset.messageRole = 'user';
    const label = document.createElement('p');
    label.className = 'ai-workshop-message-label';
    label.textContent = '你的提问';
    const content = document.createElement('p');
    content.className = 'ai-workshop-message-content';
    content.textContent = value;
    message.append(label, content);
    messages.append(message);
    while (messages.querySelectorAll('[data-message-role="user"]').length > MAX_USER_MESSAGES) {
      messages.querySelector('[data-message-role="user"]').remove();
    }
    messages.scrollTop = messages.scrollHeight;
  }

  questionForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    const value = validate(question, questionError, MAX_QUESTION_LENGTH, '京剧问题');
    if (value === null) return;
    appendUserQuestion(value);
    // 未发出网络请求，因此没有虚构的加载动画、回答或知识引用。
    qaLoading.hidden = true;
    qaServiceError.hidden = true;
    try {
      const result = await askOperaQuestion({ question: value });
      qaStatus.textContent = result.message;
      qaStatus.hidden = false;
    } catch {
      qaServiceError.textContent = '页面服务状态读取失败，请刷新页面后重试。AI问答仍未接入。';
      qaServiceError.hidden = false;
    }
  });

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
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeWorkshop, { once: true });
} else {
  initializeWorkshop();
}
