import { askOperaQuestion, createConversation, listConversations, getConversation, createSubmissionKey, ServiceError } from './services.js?v=phase4-1';
import { safeCitationUrl } from './contracts.js?v=phase4-1';

const SELECTED_KEY = 'xijing-selected-chat-v1'; // Identifier only; messages stay on the server.
const node = (tag, className, text = '') => {
  const result = document.createElement(tag); result.className = className; result.textContent = text; return result;
};
export function initializeChat({ root, setServiceState, onServiceFailure }) {
  const byId = (id) => {
    const element = root.querySelector(`#ai-workshop-${id}`);
    if (!element) throw new Error(`缺少问答元素：${id}`);
    return element;
  };
  const form = byId('question-form'), input = byId('question'), send = byId('send');
  const messages = byId('messages'), errorBox = byId('qa-service-error'), retry = byId('retry-question');
  const validation = byId('question-error'), count = byId('question-count'), loading = byId('qa-loading');
  const list = byId('conversations'), listStatus = byId('conversation-status'), more = byId('more-conversations');
  const newButton = byId('new-conversation'), heading = byId('current-conversation'), references = byId('citations');
  const suggestions = root.querySelector('.ai-workshop-suggestions');
  let current = null, busy = false, historyBusy = false, failedTurn = null, offset = 0, generation = 0;
  let startupComplete = false, pendingPrefill = null;
  const drafts = new Map();
  function remember(id) { try { localStorage.setItem(SELECTED_KEY, id); } catch { /* Optional preference only. */ } }
  function selected() { try { return localStorage.getItem(SELECTED_KEY); } catch { return null; } }
  function feedback(error) {
    errorBox.textContent = error instanceof ServiceError ? error.message : '请求暂时未能完成，请手动重试。'; errorBox.hidden = false;
  }
  function updateInput() { count.textContent = `${input.value.length} / 600 字`; }
  function flushPrefill() {
    if (!startupComplete || busy || historyBusy || pendingPrefill === null) return;
    input.value = pendingPrefill; pendingPrefill = null;
    input.dispatchEvent(new Event('input', { bubbles: true })); input.focus();
  }
  function prefill(value) {
    if (typeof value !== 'string' || !value.trim() || value.length > 600 || busy) return false;
    pendingPrefill = value; flushPrefill(); return true;
  }
  function controls() {
    const locked = busy || historyBusy;
    send.disabled = locked; newButton.disabled = locked; more.disabled = locked;
    list.querySelectorAll('button').forEach((button) => { button.disabled = locked; });
    retry.disabled = locked; form.setAttribute('aria-busy', String(busy)); messages.setAttribute('aria-busy', String(locked));
    loading.hidden = !busy;
  }
  function clearFeedback() { errorBox.hidden = true; retry.hidden = true; failedTurn = null; }
  function citation(cite) {
    const details = node('details', 'ai-workshop-citation'); details.dataset.citationId = cite.id;
    details.append(node('summary', '', cite.title));
    const body = node('div', 'ai-workshop-citation-body');
    if (cite.locator) body.append(node('p', 'ai-workshop-citation-meta', cite.locator));
    if (cite.contentKind === 'original_fact_summary') body.append(node('p', 'ai-workshop-citation-meta', '据来源核对的事实摘要'));
    body.append(node('blockquote', 'ai-workshop-citation-excerpt', cite.excerpt));
    const url = safeCitationUrl(cite.url);
    if (url) { const link = node('a', 'ai-workshop-text-link', '查看来源网页 ↗'); link.href = url; link.target = '_blank'; link.rel = 'noopener noreferrer'; body.append(link); }
    details.append(body); return details;
  }
  function message(role, label, content) {
    const article = node('article', `ai-workshop-message ai-workshop-message--${role}`); article.dataset.messageRole = role;
    article.append(node('p', 'ai-workshop-message-label', label), node('p', 'ai-workshop-message-content', content)); return article;
  }
  function answer(turn, result) {
    const article = message('assistant', '戏韵 · 京剧知识助手', result.answer);
    article.dataset.requestId = result.requestId;
    if (result.uncertain) article.append(node('p', 'ai-workshop-uncertain', '现有资料不足或仅部分支持，请结合来源理解。'));
    const details = node('details', 'ai-workshop-answer-references');
    details.append(node('summary', '', `参考来源（${result.citations.length}）`));
    result.citations.forEach((cite) => details.append(citation(cite)));
    if (!result.citations.length) details.append(node('p', 'ai-workshop-reference-empty', '本次没有足够的可引用资料。'));
    article.append(details); turn.element.append(article);
    references.replaceChildren(...result.citations.map(citation)); references.dataset.requestId = result.requestId;
    if (!result.citations.length) references.append(node('p', 'ai-workshop-reference-empty', '本次没有可引用资料。'));
  }
  function addTurn(question, key = createSubmissionKey()) {
    const element = node('div', 'ai-workshop-turn'); element.dataset.turnId = key;
    element.append(message('user', '你', question)); messages.append(element);
    if (suggestions) suggestions.hidden = true;
    return { question, idempotencyKey: key, element, failure: null };
  }
  function empty() {
    if (suggestions) suggestions.hidden = false;
    messages.replaceChildren(message('assistant', '戏韵', '想了解京剧的哪一面？从行当、脸谱、服饰或经典剧目开始，也可以围绕一个话题继续追问。'));
    references.replaceChildren(node('p', 'ai-workshop-reference-empty', '回答后可展开每条消息中的参考来源。'));
  }
  function renderConversation(value) {
    current = value; heading.textContent = value.title; messages.replaceChildren(); clearFeedback();
    references.replaceChildren(node('p', 'ai-workshop-reference-empty', '展开回答下方的参考来源。'));
    for (const saved of value.turns) {
      const turn = addTurn(saved.question, saved.idempotencyKey);
      if (saved.status === 'completed') answer(turn, saved.answer);
      else {
        const unknown = ['unknown', 'pending'].includes(saved.status);
        const text = unknown ? '这次请求的结果尚未确认。请重新读取会话核对；不会自动再次调用模型。' : saved.error?.message || '这次请求未完成。';
        turn.failure = message('notice', '请求未完成', text); turn.element.append(turn.failure);
        if (!unknown && saved.error?.retryable && saved === value.turns.at(-1)) { failedTurn = turn; retry.hidden = false; }
      }
    }
    if (!value.turns.length) empty();
    input.value = drafts.get(value.id) || ''; updateInput(); remember(value.id);
    list.querySelectorAll('button[data-conversation-id]').forEach((button) => button.setAttribute('aria-current', button.dataset.conversationId === value.id ? 'true' : 'false'));
    messages.scrollTop = messages.scrollHeight;
  }
  async function choose(id) {
    if (busy || historyBusy) return;
    if (current) drafts.set(current.id, input.value);
    historyBusy = true; controls(); listStatus.textContent = '正在读取会话……';
    const ticket = ++generation;
    try {
      const value = await getConversation(id);
      if (ticket !== generation) return;
      renderConversation(value); listStatus.textContent = '会话已恢复';
      setServiceState('history', '会话已恢复。实时回复以当前服务状态为准。');
    } catch (error) { feedback(error); listStatus.textContent = '会话读取失败，请重新选择。'; }
    finally { historyBusy = false; controls(); flushPrefill(); }
  }
  function row(item) {
    const button = node('button', 'ai-workshop-conversation'); button.type = 'button'; button.dataset.conversationId = item.id;
    button.setAttribute('aria-current', String(current?.id === item.id));
    button.append(node('span', 'ai-workshop-conversation-title', item.title));
    const time = node('time', 'ai-workshop-conversation-time', new Date(item.updatedAt).toLocaleString('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' })); time.dateTime = item.updatedAt; button.append(time);
    button.addEventListener('click', () => void choose(item.id)); return button;
  }
  async function loadList(append = false) {
    if (historyBusy) return;
    historyBusy = true; controls(); listStatus.textContent = '正在读取历史会话……';
    try {
      const result = await listConversations(append ? offset : 0);
      if (!append) { list.replaceChildren(); offset = 0; }
      result.items.forEach((item) => list.append(row(item))); offset += result.items.length;
      const selectedItem = result.items.find((item) => item.id === current?.id);
      if (selectedItem) heading.textContent = selectedItem.title;
      more.hidden = !result.hasMore; listStatus.textContent = offset ? '仅显示本机保存的问答会话' : '还没有历史会话，开始一个新话题吧。';
      more.textContent = '更多会话';
      return result;
    } catch (error) { listStatus.textContent = '暂时无法读取历史会话。'; feedback(error); more.hidden = false; more.textContent = '重新读取'; }
    finally { historyBusy = false; controls(); flushPrefill(); }
  }
  async function fresh() {
    if (busy || historyBusy) return;
    if (current) drafts.set(current.id, input.value);
    historyBusy = true; controls(); clearFeedback();
    try { renderConversation(await createConversation()); }
    catch (error) { feedback(error); }
    finally { historyBusy = false; controls(); flushPrefill(); }
    await loadList(); input.focus();
  }
  async function sendTurn(turn) {
    if (busy || historyBusy) return;
    busy = true; controls(); clearFeedback(); turn.failure?.remove();
    setServiceState('loading', '正在检索资料并整理回答……');
    const conversation = current;
    try {
      const result = await askOperaQuestion({ question: turn.question, conversationId: conversation.id }, { idempotencyKey: turn.idempotencyKey });
      answer(turn, result);
      setServiceState(result.uncertain ? 'uncertain' : 'answered', result.uncertain ? '目前资料有限，可以换个角度继续提问。' : '回答已保存，可继续追问。');
      if (input.value.trim() === turn.question) { input.value = ''; drafts.delete(conversation.id); updateInput(); }
    } catch (error) {
      feedback(error); turn.failure = message('notice', '请求未完成', errorBox.textContent); turn.element.append(turn.failure);
      setServiceState('error', '内容已保留，请检查提示后手动操作。');
      if (error instanceof ServiceError && error.retryable) { failedTurn = turn; retry.hidden = false; }
      onServiceFailure(error);
    } finally { busy = false; controls(); messages.scrollTop = messages.scrollHeight; await loadList(); }
  }
  async function submit() {
    if (busy || historyBusy) return;
    const value = input.value.trim();
    if (!value || input.value.length > 600) {
      validation.textContent = !value ? '请先写下你的京剧问题。' : '问题最多600字，请缩短后发送。'; validation.hidden = false; input.setAttribute('aria-invalid', 'true'); input.focus(); return;
    }
    if (!current) {
      historyBusy = true; controls();
      try { current = await createConversation(); heading.textContent = current.title; remember(current.id); }
      catch (error) { feedback(error); return; }
      finally { historyBusy = false; controls(); }
    }
    if (current.turns.length === 0 && !messages.querySelector('.ai-workshop-turn')) messages.replaceChildren();
    await sendTurn(addTurn(value));
  }
  form.addEventListener('submit', (event) => { event.preventDefault(); void submit(); });
  input.addEventListener('input', () => { validation.hidden = true; input.removeAttribute('aria-invalid'); updateInput(); });
  input.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && !event.shiftKey && !event.isComposing && !event.ctrlKey && !event.metaKey && !event.altKey) { event.preventDefault(); form.requestSubmit(); }
  });
  root.querySelectorAll('[data-ai-workshop-question]').forEach((button) => button.addEventListener('click', () => { input.value = button.dataset.aiWorkshopQuestion; updateInput(); input.focus(); }));
  newButton.addEventListener('click', () => void fresh()); more.addEventListener('click', () => void loadList(offset > 0 && more.textContent !== '重新读取'));
  retry.addEventListener('click', () => { if (failedTurn) void sendTurn(failedTurn); });
  const sidebar = root.querySelector('#ai-workshop-conversation-sidebar');
  if (sidebar && globalThis.matchMedia?.('(max-width: 760px)').matches) sidebar.open = false;
  empty(); updateInput(); controls();
  void loadList().then(async (result) => {
    if (!result?.items.length) return;
    const preferred = selected(); const id = result.items.find((item) => item.id === preferred)?.id || result.items[0].id; await choose(id);
  }).finally(() => { startupComplete = true; flushPrefill(); });
  return { isBusy: () => busy || historyBusy, isGenerating: () => busy, hasError: () => !errorBox.hidden, refresh: () => loadList(), prefill };
}
