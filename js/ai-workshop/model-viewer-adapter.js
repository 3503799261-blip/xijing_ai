import { safeAssetFileUrl } from './contracts.js?v=phase4-1';

let viewerModule;
const DEFAULT_ORBIT = '0deg 75deg auto';
const DEFAULT_FOV = '35deg';
const TAU = Math.PI * 2;

/** Unwrap a real camera angle; a change crossing 0 degrees must not erase a turn. */
export function unwrapTheta(previous, current) {
  let delta = current - previous;
  while (delta > Math.PI) delta -= TAU;
  while (delta < -Math.PI) delta += TAU;
  return delta;
}

/** Only monotonic, user-interaction camera changes contribute to the continuous range. */
export function createOrbitTracker() {
  let previous = null;
  let direction = 0;
  let run = 0;
  let largest = 0;
  let eventCount = 0;
  let userEventCount = 0;
  const samples = [];
  return {
    add(theta, source, radius = null) {
      if (!Number.isFinite(theta)) return;
      eventCount += 1;
      if (source !== 'user-interaction') { previous = null; direction = 0; run = 0; return; }
      userEventCount += 1;
      if (previous !== null) {
        const delta = unwrapTheta(previous, theta);
        // Zoom-only events do not break a rotation, but a direction reversal does.
        if (Math.abs(delta) > 0.0001) {
          const nextDirection = Math.sign(delta);
          if (direction && nextDirection !== direction) run = 0;
          direction = nextDirection;
          run += Math.abs(delta);
          largest = Math.max(largest, run);
        }
      }
      previous = theta;
      samples.push({ theta, radius: Number.isFinite(radius) ? radius : null, source });
      if (samples.length > 200) samples.shift();
    },
    snapshot: () => ({ eventCount, userEventCount, maxContinuousDegrees: largest * 180 / Math.PI, samples: samples.map((sample) => ({ ...sample })) }),
  };
}

async function ensureViewer() {
  if (globalThis.customElements?.get('model-viewer')) return;
  if (!viewerModule) viewerModule = import('../vendor/model-viewer/model-viewer.min.js').catch((error) => { viewerModule = null; throw error; });
  await viewerModule;
  if (!globalThis.customElements?.get('model-viewer')) throw new Error('Viewer component unavailable');
}

/** Existing GLB only: this adapter has no generation or provider API dependency. */
export function initializeModelViewer({ root, loader = ensureViewer }) {
  const find = (name) => root.querySelector(`#ai-workshop-${name}`);
  const host = find('viewer-host');
  const status = find('viewer-status');
  const errorMessage = find('viewer-error');
  if (!host || !status || !errorMessage) return null;
  const zoomIn = find('viewer-zoom-in');
  const zoomOut = find('viewer-zoom-out');
  const reset = find('viewer-reset');
  const touch = find('viewer-touch');
  const reload = find('viewer-reload');
  const interactionHelp = find('viewer-help');
  let state = 'idle';
  let element = null;
  let activeModel = null;
  let generation = 0;
  let timeout = null;
  let touchEnabled = false;
  let tracker = createOrbitTracker();
  let lastError = '';
  const cancelTimeout = () => { if (timeout !== null) clearTimeout(timeout); timeout = null; };
  function setState(value, message) {
    state = value;
    host.dataset.viewerState = value;
    host.setAttribute('aria-busy', String(value === 'loading'));
    status.dataset.viewerState = value;
    status.textContent = message;
    [zoomIn, zoomOut, reset, touch].forEach((button) => { if (button) button.disabled = value !== 'ready'; });
    errorMessage.hidden = value !== 'error';
    if (reload) reload.hidden = value !== 'error' || !activeModel;
    if (element) element.hidden = value === 'error';
  }
  function publishCamera() {
    if (!element?.getCameraOrbit) return;
    const orbit = element.getCameraOrbit();
    const tracked = tracker.snapshot();
    if (Number.isFinite(orbit.theta)) host.dataset.cameraTheta = orbit.theta.toFixed(6);
    if (Number.isFinite(orbit.phi)) host.dataset.cameraPhi = orbit.phi.toFixed(6);
    if (Number.isFinite(orbit.radius)) host.dataset.cameraRadius = orbit.radius.toFixed(6);
    host.dataset.observedDegrees = tracked.maxContinuousDegrees.toFixed(1);
    host.dataset.userEventCount = String(tracked.userEventCount);
  }
  function fail(message) {
    cancelTimeout(); lastError = message; errorMessage.textContent = message;
    setState('error', '模型加载失败');
  }
  const diagnostics = () => ({ state, modelId: activeModel?.modelId || null, modelHash: activeModel?.hash || null,
    touchEnabled, lastError, orbit: element?.getCameraOrbit ? { ...element.getCameraOrbit() } : null, ...tracker.snapshot() });

  async function load(model) {
    const safeUrl = safeAssetFileUrl(model?.fileUrl, 'models', model?.modelId);
    if (!safeUrl || model?.format !== 'glb') { fail('模型资源未通过受控GLB路径检查，请重新选择已登记模型。'); return; }
    generation += 1;
    const currentGeneration = generation;
    cancelTimeout(); activeModel = model; tracker = createOrbitTracker(); lastError = '';
    host.dataset.observedDegrees = '0'; host.dataset.userEventCount = '0';
    delete host.dataset.cameraTheta; delete host.dataset.cameraPhi; delete host.dataset.cameraRadius;
    touchEnabled = false;
    if (touch) { touch.textContent = '进入触摸交互'; touch.setAttribute('aria-pressed', 'false'); }
    host.replaceChildren(); element = null;
    setState('loading', '正在加载真正的3D模型……');
    timeout = setTimeout(() => { if (currentGeneration === generation && state === 'loading') fail('模型加载超时，请检查本地服务或文件资源后点击重新加载。不会重新生成模型。'); }, 30000);
    try {
      await loader();
      if (currentGeneration !== generation) return;
      const viewer = document.createElement('model-viewer');
      element = viewer;
      viewer.className = 'ai-workshop-model-viewer';
      viewer.setAttribute('alt', `${model.title || model.name || '已登记模型'}，真实交互3D模型`);
      viewer.setAttribute('camera-controls', '');
      viewer.setAttribute('touch-action', 'pan-y');
      viewer.setAttribute('camera-orbit', DEFAULT_ORBIT);
      viewer.setAttribute('field-of-view', DEFAULT_FOV);
      // auto keeps the horizontal azimuth unconstrained; vertical motion stays useful.
      viewer.setAttribute('min-camera-orbit', 'auto 15deg auto');
      viewer.setAttribute('max-camera-orbit', 'auto 165deg auto');
      viewer.setAttribute('shadow-intensity', '0.7');
      viewer.setAttribute('exposure', '1');
      viewer.setAttribute('interaction-prompt', 'none');
      viewer.setAttribute('loading', 'eager');
      viewer.setAttribute('tabindex', '0');
      viewer.addEventListener('load', () => {
        if (currentGeneration !== generation) return;
        cancelTimeout();
        setState('ready', '模型加载完成 · 拖拽旋转，滚轮缩放');
        publishCamera();
      });
      viewer.addEventListener('error', () => { if (currentGeneration === generation) fail('模型加载失败，请检查资源是否完整或浏览器是否支持WebGL。可重新加载原文件，不会提交建模。'); });
      viewer.addEventListener('progress', (event) => {
        if (currentGeneration !== generation || state !== 'loading') return;
        const value = event.detail?.totalProgress;
        if (Number.isFinite(value) && value >= 0 && value <= 1) status.textContent = `正在加载真正的3D模型……${Math.round(value * 100)}%`;
      });
      viewer.addEventListener('camera-change', (event) => {
        if (currentGeneration !== generation || state !== 'ready') return;
        const orbit = viewer.getCameraOrbit();
        tracker.add(orbit.theta, event.detail?.source, orbit.radius);
        publishCamera();
      });
      host.append(viewer);
      viewer.src = safeUrl;
    } catch { if (currentGeneration === generation) fail('3D查看器组件无法加载，请检查本地组件资源与浏览器支持后重试。'); }
  }
  function zoom(factor) {
    if (state !== 'ready' || !element?.getCameraOrbit) return;
    const orbit = element.getCameraOrbit();
    element.cameraOrbit = `${orbit.theta}rad ${orbit.phi}rad ${orbit.radius * factor}m`;
  }
  zoomIn?.addEventListener('click', () => zoom(0.8));
  zoomOut?.addEventListener('click', () => zoom(1.25));
  reset?.addEventListener('click', () => {
    if (state !== 'ready') return;
    element.cameraOrbit = DEFAULT_ORBIT; element.fieldOfView = DEFAULT_FOV;
    element.jumpCameraToGoal?.();
  });
  touch?.addEventListener('click', () => {
    if (state !== 'ready') return;
    touchEnabled = !touchEnabled;
    element.setAttribute('touch-action', touchEnabled ? 'none' : 'pan-y');
    touch.setAttribute('aria-pressed', String(touchEnabled));
    touch.textContent = touchEnabled ? '退出触摸交互' : '进入触摸交互';
    if (interactionHelp) interactionHelp.textContent = touchEnabled
      ? '交互已开启：单指旋转，双指缩放。退出后可在模型区域上下滑动页面。'
      : '桌面拖拽旋转、滚轮缩放；手机点击“进入触摸交互”后可自由拖拽和双指缩放。';
  });
  reload?.addEventListener('click', () => { if (activeModel && state === 'error') void load(activeModel); });
  setState('idle', '选择一个已登记的GLB模型开始查看');
  function clear(message = '当前风格尚未生成3D模型') {
    generation += 1; cancelTimeout(); host.replaceChildren(); element = null; activeModel = null;
    tracker = createOrbitTracker();
    host.dataset.observedDegrees = '0'; host.dataset.userEventCount = '0';
    delete host.dataset.cameraTheta; delete host.dataset.cameraPhi; delete host.dataset.cameraRadius;
    setState('idle', message);
  }
  return { load, diagnostics, clear, dispose() { clear('3D查看器已关闭'); } };
}
