import { getServiceCapabilities, loadServiceCapabilities, requiresCapabilityRecheck, ServiceError } from './services.js?v=phase4-1';
import { initializeChat } from './chat-controller.js?v=product-1';
import { initializeAgentWorkflow } from './agent-workflow.js?v=phase4-1';

const PANEL_NAMES = ['overview', 'qa', 'agents', 'create', 'model', 'stage'];
const MAX_BRIEF_LENGTH = 1200;

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
  const qaStatus = required('#ai-workshop-qa-status');
  const qaServiceError = required('#ai-workshop-qa-service-error');
  const refreshServiceButton = required('#ai-workshop-refresh-service');
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
  let chatController = null;
  let capabilityLoading = false;
  let capabilityRefreshId = 0;
  let agentController = null;
  let assetController = null;
  let stageController = null;

  function updateScrollOffset() {
    const header = document.querySelector('.site-header');
    root.style.setProperty('--ai-workshop-scroll-offset', `${(header?.offsetHeight ?? 82) + 24}px`);
  }
  updateScrollOffset();
  window.addEventListener('resize', updateScrollOffset);

  const panelFromHash = () => {
    if (window.location.hash === '#ai-workshop-history') return 'agents';
    if (window.location.hash === '#ai-workshop-demo') { const guide = root.querySelector('#ai-workshop-demo-disclosure'); if (guide) guide.open = true; return 'qa'; }
    const match = window.location.hash.match(/^#ai-workshop-(overview|qa|agents|create|model|stage)$/);
    if (match) return match[1];
    if (!window.location.hash || window.location.hash === '#ai-workshop') return 'qa';
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
    const secondaryNavigation = root.querySelector('.ai-workshop-secondary-nav');
    if (secondaryNavigation) secondaryNavigation.open = false;
    void assetController?.setVisible(name === 'model');
    void stageController?.setVisible(name === 'stage');
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

  function setServiceState(state, text) {
    qaStatus.dataset.serviceState = state;
    qaStatus.textContent = text;
    qaStatus.hidden = false;
    root.dataset.questionServiceState = state;
  }

  function displayCapabilityState(capability, failed = false) {
    capabilityBadges.forEach((badge) => {
      badge.textContent = capability.questionAnswering ? '知识问答可用' : failed ? '暂时无法连接' : '问答暂不可用';
      badge.dataset.serviceState = capability.questionAnswering ? 'ready' : 'unavailable';
      badge.classList.toggle('ai-workshop-badge-unavailable', !capability.questionAnswering);
      badge.classList.toggle('ai-workshop-badge-ready', capability.questionAnswering);
    });
    heroServiceNote.textContent = capability.questionAnswering ? '以京剧资料为依据，让每一次探索有迹可循。' : '问一段京剧，或在数字戏台走近戏中人。';
    agentController?.setCapability(capability);
  }

  async function refreshCapabilities({ afterRequestFailure = false } = {}) {
    if (capabilityLoading && !afterRequestFailure) return;
    const refreshId = ++capabilityRefreshId;
    capabilityLoading = true;
    refreshServiceButton.disabled = true;
    refreshServiceButton.setAttribute('aria-busy', 'true');
    const canUpdateFeedback = () => !chatController?.isGenerating() && (qaServiceError.hidden || !qaServiceError.textContent);
    if (canUpdateFeedback()) setServiceState('checking', '正在检查知识服务状态……');
    try {
      const capability = await loadServiceCapabilities();
      if (refreshId !== capabilityRefreshId) return;
      displayCapabilityState(capability);
      if (canUpdateFeedback()) setServiceState(capability.questionAnswering ? 'ready' : 'unavailable', capability.questionAnswering
        ? '可以开始提问，也可选择历史会话继续。回答附有可展开的资料来源。'
        : capability.knowledgeSearch ? '资料检索可用，问答服务暂未就绪。可以稍后重试，或查看已保存的创作档案。'
          : '知识问答暂不可用，请检查本地服务与知识资源，或稍后重试。');
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

  chatController = initializeChat({ root, setServiceState, onServiceFailure(error) {
    if (requiresCapabilityRecheck(error)) { displayCapabilityState(getServiceCapabilities()); void refreshCapabilities({ afterRequestFailure: true }); }
  } });
  function prefillQuestion(question) {
    if (!chatController.prefill(question)) { notice.textContent = '当前回答仍在进行，请等它完成后再带入问题。'; notice.hidden = false; return false; }
    selectPanel('qa', true);
    if (window.location.hash !== '#ai-workshop-qa') window.history.pushState(null, '', '#ai-workshop-qa');
    return true;
  }
  const pendingNavigationKey = 'xijing.pending-navigation-question.v1';
  window.addEventListener('xijing:prefill-question', (event) => {
    if (prefillQuestion(event.detail?.question)) { try { sessionStorage.removeItem(pendingNavigationKey); } catch { /* Optional draft only. */ } }
  });
  try { const pending = sessionStorage.getItem(pendingNavigationKey); if (pending && prefillQuestion(pending)) sessionStorage.removeItem(pendingNavigationKey); } catch { /* Navigation must not depend on browser storage. */ }
  refreshServiceButton.addEventListener('click', () => { void refreshCapabilities(); void chatController.refresh(); });
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

  selectPanel(panelFromHash() || 'qa');
  root.classList.add('ai-workshop-ready');
  saveDraftButton.disabled = false;
  try {
    agentController = initializeAgentWorkflow({ root, selectPanel, refreshCapabilities });
  } catch {
    notice.textContent = 'Agent界面未能初始化，请刷新后重试。京剧问答和页面内草稿仍可使用。';
    notice.hidden = false;
  }
  // Historical snapshots are isolated from the live workflow controller and never restore an active task.
  void import('./demo-guide.js?v=phase5-wp3-1').then(({ initializeDemoGuide }) => {
    initializeDemoGuide({ root, selectPanel });
  }).catch(() => {
    const feedback = root.querySelector('#ai-workshop-demo-feedback');
    if (feedback) feedback.textContent = '演示导览未能加载，请刷新后重试；下方正常功能与静态说明仍可使用。';
  });
  void import('./agent-history.js?v=phase5-wp2-1').then(({ initializeAgentHistory }) => {
    initializeAgentHistory({ root });
  }).catch(() => {
    const historyStatus = root.querySelector('#ai-workshop-history-status');
    if (historyStatus) historyStatus.textContent = '历史档案暂时无法初始化，请刷新页面后重试；现有工作台不受影响。';
  });
  // Asset/viewer initialization failures are isolated from existing QA and Agent modules.
  void import('./digital-assets.js?v=phase4-1').then(({ initializeDigitalAssets }) => {
    assetController = initializeDigitalAssets({ root, selectPanel });
    return assetController?.setVisible(activePanel === 'model');
  }).catch(() => {
    const assetFeedback = root.querySelector('#ai-workshop-asset-feedback');
    if (assetFeedback) { assetFeedback.textContent = '数字资产界面暂时无法初始化，请刷新后重试。京剧问答和Agent工作台仍可使用。'; assetFeedback.classList.add('ai-workshop-feedback-error'); }
  });
  // Digital-stage reads and render failures never start a chat, Agent or model task.
  void import('./digital-stage.js?v=stage-1').then(({ initializeDigitalStage }) => {
    stageController = initializeDigitalStage({ root, onAskQuestion(question) {
      prefillQuestion(question);
    } });
    return stageController?.setVisible(activePanel === 'stage');
  }).catch(() => {
    const error = root.querySelector('#ai-workshop-stage-error');
    if (error) { error.textContent = '数字戏台暂时无法初始化，请刷新后重试。京剧问答与已有档案仍可使用。'; error.hidden = false; }
  });
  void refreshCapabilities();
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeWorkshop, { once: true });
} else {
  initializeWorkshop();
}
