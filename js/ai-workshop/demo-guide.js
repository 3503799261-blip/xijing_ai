import { checkDemoConditions, DEMO_IDENTITIES } from './demo-status.js?v=phase5-wp3-1';

const node = (tag, text = '', className = '') => {
  const element = document.createElement(tag); element.textContent = text;
  if (className) element.className = className;
  return element;
};
const STEPS = Object.freeze([
  { title: '认识戏境AI', panel: 'overview', description: '从8个京剧文化页面走进AI工坊：文化检索、四Agent文字创作、人工核查与已有数字资产互相衔接。先理解流程，再选择查看内容。', source: '产品介绍。下一步只切换页面区域，不会自动生成问答、角色或模型。' },
  { title: '京剧问答与资料引用', panel: 'qa', description: '阅读问答区域的知识来源说明与推荐问题。新发送或重试问题会调用后端LLM，必须另有付费授权；导览不会代填或发送问题。备用模式请改看已保存Agent研究依据。', source: '当前问答区是交互入口，不是新的AI回答。此导览不生成或填充示例答案。' },
  { title: '真实Agent历史', panel: 'agents', target: 'ai-workshop-history', description: '进入WP2历史档案，手动读取持久化任务，查看Planner、Research、Designer及Reviewer当时保存的摘要、产物和事件。这里只展示记录，不重跑Agent。', source: '真实持久化记录 · 只读快照。历史中的“运行中”不是本页实时执行。' },
  { title: '角色JSON、审校与人审', panel: 'agents', target: 'ai-workshop-history', description: '选择“绛绣·戏韵”原任务，展开已保存角色JSON、文化资料、AI辅助审校及用户确认记录。未保存字段明确留空；原创京剧风格角色不冒称历史人物。', source: '已保存的真实任务及人工确认记录。不自动接受方案，也不把新角色套用已有模型。' },
  { title: '已有真实3D模型', panel: 'model', description: '写实主展示与Q版内部技术模型来自两次历史Neural4D任务。打开原模型后手动拖拽、缩放和重置；GLB加载情况以Viewer当前状态为准。它们不属于同一角色的两个风格版本。', source: '历史真实生成资产。Q版仅限内部非公开技术验证；公开演示优先使用写实主模型。没有新建模。' },
  { title: '企业应用方向与交付边界', panel: 'model', target: 'ai-workshop-asset-form', description: '企业入口可说明机构、受众、用途与文化边界，共用文化研究和人工核查机制。请手动选择企业模式再阅读表单；当前没有真实企业商用交付案例，不强制绑定Q版或写实风格。', source: '已实现企业需求入口，企业商用交付仍是应用方向。缺少商业许可或模型时不会补造交付成果。' },
]);
const MUTATION_IDS = new Set(['ai-workshop-new-conversation', 'ai-workshop-send', 'ai-workshop-retry-question', 'ai-workshop-agent-start', 'ai-workshop-agent-submit', 'ai-workshop-agent-submit-retry', 'ai-workshop-agent-confirm', 'ai-workshop-agent-cancel', 'ai-workshop-visual-accept', 'ai-workshop-image-accept', 'ai-workshop-model-submit', 'ai-workshop-prompt-edit-save']);
function localLoopback() {
  return ['127.0.0.1', 'localhost', '[::1]', '::1'].includes(globalThis.location?.hostname || '127.0.0.1');
}
/** An optional local guide, isolated from workflow state and server generation configuration. */
export function initializeDemoGuide({ root, selectPanel, services = { checkDemoConditions } }) {
  const names = ['demo', 'demo-start', 'demo-backup', 'demo-exit', 'demo-prev', 'demo-next', 'demo-skip', 'demo-content', 'demo-steps', 'demo-title', 'demo-description', 'demo-source', 'demo-links', 'demo-feedback', 'demo-check', 'demo-conditions', 'demo-check-time'];
  if (!root.querySelector('#ai-workshop-demo')) return null;
  const elements = Object.fromEntries(names.map((name) => {
    const element = root.querySelector(`#ai-workshop-${name}`);
    if (!element) throw new Error('演示导览缺少必要界面元素。');
    return [name, element];
  }));
  let active = false;
  let backup = false;
  let current = 0;
  let checking = false;
  let checkGeneration = 0;
  let checkAbort = null;
  const buttons = STEPS.map((step, index) => {
    const item = node('li'); const button = node('button', `${index + 1}. ${step.title}`, 'ai-workshop-demo-step');
    button.type = 'button'; button.dataset.demoStep = String(index);
    button.addEventListener('click', () => setStep(index)); item.append(button); elements['demo-steps'].append(item);
    return button;
  });
  function feedback(message) { elements['demo-feedback'].textContent = message; }
  function renderMode() {
    elements.demo.dataset.mode = backup ? 'backup' : active ? 'guide' : 'idle';
    elements['demo-content'].hidden = !active;
    elements['demo-exit'].hidden = !active;
    elements['demo-prev'].disabled = !active || current === 0;
    elements['demo-next'].disabled = !active || current === STEPS.length - 1;
    elements['demo-skip'].disabled = !active || current === STEPS.length - 1;
    elements['demo-backup'].setAttribute('aria-pressed', String(backup));
    buttons.forEach((button, index) => { if (active && index === current) button.setAttribute('aria-current', 'step'); else button.removeAttribute('aria-current'); });
  }
  function navigate(step) {
    selectPanel(step.panel);
    const target = step.target ? root.querySelector(`#${step.target}`) : root.querySelector(`#ai-workshop-${step.panel}`);
    target?.scrollIntoView?.({ block: 'start', behavior: 'auto' });
  }
  function action(label, handler) {
    const button = node('button', label, 'ai-workshop-text-link'); button.type = 'button'; button.addEventListener('click', handler); return button;
  }
  function historyLinks() {
    const target = node('a', '进入历史档案，手动读取记录 →', 'ai-workshop-text-link'); target.href = '#ai-workshop-history';
    target.addEventListener('click', (event) => { event.preventDefault(); selectPanel('agents'); root.querySelector('#ai-workshop-history')?.scrollIntoView?.({ block: 'start' }); });
    const fill = action('填入绛绣历史ID（不自动读取）', () => {
      const input = root.querySelector('#ai-workshop-history-task-id');
      if (!input) { feedback('历史筛选输入暂时不可用，可手动进入历史档案；没有创建任务。'); return; }
      input.value = DEMO_IDENTITIES.taskId;
      const state = root.querySelector('#ai-workshop-history-state'); const type = root.querySelector('#ai-workshop-history-type');
      if (state) state.value = ''; if (type) type.value = '';
      selectPanel('agents'); root.querySelector('#ai-workshop-history')?.scrollIntoView?.({ block: 'start' });
      feedback(`${backup ? '备用模式：' : ''}已按你的点击填入原任务ID并清除组合筛选，请在历史档案手动点击“读取历史记录”；未发送查询或执行请求。`);
    });
    return [target, fill];
  }
  function renderStep() {
    const step = STEPS[current];
    elements['demo-title'].textContent = `${current + 1} / ${STEPS.length} · ${step.title}`;
    elements['demo-description'].textContent = step.description;
    elements['demo-source'].textContent = step.source;
    const links = [action('前往这一步对应的功能 →', () => navigate(step))];
    if (current === 1 || current === 2 || current === 3) links.push(...historyLinks());
    if (current === 4) {
      const realistic = node('a', '已保存真实资产：“绛绣·戏韵”（新页） →', 'ai-workshop-text-link');
      realistic.href = `about.html?assetId=${DEMO_IDENTITIES.assetId}#ai-workshop-model`;
      // A new tab keeps the current backup guard active here; no cross-tab state is claimed.
      realistic.target = '_blank'; realistic.rel = 'noopener noreferrer'; links.push(realistic);
      if (localLoopback()) {
        const internal = node('a', '内部非公开：Q版技术验证Viewer（本机回环，新页） →', 'ai-workshop-text-link');
        internal.href = `/api/v1/assets/internal-models/${DEMO_IDENTITIES.internalModelId}/viewer`; internal.target = '_blank'; internal.rel = 'noopener noreferrer'; links.push(internal);
      } else links.push(node('p', 'Q版内部Viewer仅允许本机回环访问，不扩大非公开资产的访问范围。'));
      links.push(node('p', '备用保护仅在当前页面生效，刷新或新页面默认退出；原备用页仍可返回。新页不继承本页保护，请只查看已有Viewer，不提交问答、Agent或资产登记。', 'ai-workshop-demo-boundary'));
    }
    if (current === 5) links.push(action('定位企业需求入口（不带入、不提交）', () => { selectPanel('model'); root.querySelector('#ai-workshop-asset-form')?.scrollIntoView?.({ block: 'start' }); feedback('已定位既有角色资产表单；请自行查看个人/企业选项。没有改动输入、登记资产或启动Agent。'); }));
    elements['demo-links'].replaceChildren(...links);
    renderMode();
  }
  function setStep(index) {
    if (!Number.isSafeInteger(index) || index < 0 || index >= STEPS.length) return;
    active = true; current = index; renderStep(); selectPanel(STEPS[current].panel);
  }
  function start() { backup = false; current = 0; active = true; renderStep(); selectPanel(STEPS[0].panel); feedback('导览已开始，仅负责定位与说明，不会自动发送问题、执行Agent或生成模型。需要只读保护时请切换“备用演示”。'); }
  function enterBackup() { backup = true; active = true; renderStep(); selectPanel(STEPS[current].panel); feedback('备用演示模式：当前页面仅允许只读浏览，生成、确认、取消与登记操作将被拦截。它不改变服务器配置，也不会停止已经存在的后台任务；刷新页面后退出。'); }
  function exit() {
    if (checking) {
      elements['demo-check-time'].textContent = '已停止本轮只读条件检查；未据此更新可用状态。';
      elements['demo-conditions'].replaceChildren(node('li', '本轮检查已停止，可在需要时手动重新检查。'));
    }
    active = false; backup = false; checkGeneration += 1; checkAbort?.abort(); checking = false; elements['demo-check'].disabled = false; elements['demo-check'].setAttribute('aria-busy', 'false');
    renderMode(); feedback('已退出导览与本页备用保护；已有输入和记录保留。服务器真实建模创建仍由原有配置与授权机制控制。');
    elements['demo-start'].focus?.();
  }
  function blockMutation(event) {
    if (!backup) return;
    const target = event.target;
    let blocked = false;
    if (event.type === 'submit') blocked = target?.id !== 'ai-workshop-history-form';
    else {
      const button = target?.closest?.('button, input[type="submit"], input[type="image"], [role="button"]');
      if (button) {
        const form = button.closest?.('form');
        blocked = MUTATION_IDS.has(button.id) || (!!form && form.id !== 'ai-workshop-history-form' && ((button.getAttribute?.('type') || button.type || '').toLowerCase() === 'submit'));
      }
    }
    if (blocked) {
      event.preventDefault(); event.stopImmediatePropagation();
      feedback('备用演示模式已拦截这次生成或写入操作。可继续读取历史、浏览原模型与操作Viewer；不会停止已存在的后台任务。');
    }
  }
  root.addEventListener('submit', blockMutation, true);
  root.addEventListener('click', blockMutation, true);
  function unchecked() {
    elements['demo-conditions'].replaceChildren(node('li', '尚未检查。请手动点击“检查演示条件”；只读取本地后端、历史、写实登记与额度状态。'));
    elements['demo-check-time'].textContent = '未执行本轮条件检查；没有模型连通性或GLB加载结论。';
  }
  async function check() {
    const generation = ++checkGeneration; checkAbort?.abort(); checkAbort = new AbortController(); checking = true;
    elements['demo-check'].disabled = true; elements['demo-check'].setAttribute('aria-busy', 'true');
    elements['demo-check-time'].textContent = '正在进行4项独立的本地只读检查……不调用模型供应商。';
    elements['demo-conditions'].replaceChildren(node('li', '正在读取本轮条件；不沿用上一次的可用结论。'));
    try {
      const report = await services.checkDemoConditions({ signal: checkAbort.signal });
      if (generation !== checkGeneration) return;
      const items = report.checks.map((item) => {
        const element = node('li', '', 'ai-workshop-demo-condition'); element.dataset.demoCondition = item.key; element.dataset.state = item.state;
        element.append(node('strong', `${item.label} · ${{ ready: '可读取', warning: '需留意', error: '未就绪' }[item.state] || '未知'}`), node('p', item.message));
        return element;
      });
      elements['demo-conditions'].replaceChildren(...items); elements['demo-check-time'].textContent = `本轮读取时间：${report.checkedAt}。状态为只读快照；不等同当天付费API或Viewer渲染验证。`;
    } catch {
      if (generation !== checkGeneration) return;
      elements['demo-conditions'].replaceChildren(node('li', '本轮条件检查未完成，可手动重新检查或使用备用演示；不会自动重试生成。'));
      elements['demo-check-time'].textContent = '本轮检查失败，未据此报告服务可用。';
    } finally {
      if (generation === checkGeneration) { checking = false; elements['demo-check'].disabled = false; elements['demo-check'].setAttribute('aria-busy', 'false'); }
    }
  }
  elements['demo-start'].addEventListener('click', start); elements['demo-backup'].addEventListener('click', enterBackup); elements['demo-exit'].addEventListener('click', exit);
  elements['demo-prev'].addEventListener('click', () => { if (active && current > 0) setStep(current - 1); });
  elements['demo-next'].addEventListener('click', () => { if (active && current < STEPS.length - 1) setStep(current + 1); });
  elements['demo-skip'].addEventListener('click', () => { if (active) setStep(STEPS.length - 1); });
  elements['demo-check'].addEventListener('click', () => { if (!checking) void check(); });
  unchecked(); renderMode();
  return { start, setStep, enterBackup, exit, check, diagnostics: () => ({ active, backup, step: current, checking, paidCalls: 0, serverConfigurationChanged: false }) };
}
