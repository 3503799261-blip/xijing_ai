/** Local, static stage composition. No generation, animation, provider or DB calls. */
import * as THREE from '../vendor/three/three.module.js';
import { GLTFLoader } from '../vendor/three/GLTFLoader.js';
import { OrbitControls } from '../vendor/three/OrbitControls.js';
import { createOrbitTracker } from './model-viewer-adapter.js?v=phase4-1';

const validUrl = (value) => {
  const url = new URL(value, location.origin);
  if (url.origin !== location.origin || url.search || url.hash || url.username || url.password
      || !/^\/api\/v1\/stage\/files\/[a-z0-9][a-z0-9-]{0,63}$/.test(url.pathname)) throw new Error('模型地址不在本地戏台资源范围内。');
  return url.href;
};
function free(object) {
  const textures = new Set(), materials = new Set(), geometries = new Set();
  object?.traverse((node) => {
    if (node.geometry) geometries.add(node.geometry);
    for (const material of Array.isArray(node.material) ? node.material : [node.material]) {
      if (!material) continue;
      materials.add(material);
      for (const value of Object.values(material)) if (value?.isTexture) textures.add(value);
    }
  });
  for (const item of textures) item.dispose();
  for (const item of materials) item.dispose();
  for (const item of geometries) item.dispose();
}
function embeddedGlb(buffer) {
  const view = new DataView(buffer);
  if (buffer.byteLength < 20 || view.getUint32(0, true) !== 0x46546c67 || view.getUint32(4, true) !== 2
      || view.getUint32(8, true) !== buffer.byteLength || view.getUint32(16, true) !== 0x4e4f534a) throw new Error('模型文件不完整或格式不受支持。');
  const size = view.getUint32(12, true);
  if (size > buffer.byteLength - 20) throw new Error('模型结构不完整。');
  const data = JSON.parse(new TextDecoder().decode(new Uint8Array(buffer, 20, size)).trim());
  if ([...(data.images || []), ...(data.buffers || [])].some((entry) => entry.uri)) throw new Error('戏台模型需要内嵌贴图，不能请求外部资源。');
}

export function initializeStageViewer({ host, onState = () => {}, onCharacterPick = () => {} }) {
  let renderer;
  try { renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, powerPreference: 'high-performance' }); }
  catch { throw new Error('当前浏览器无法开启3D，请启用硬件加速或换用支持WebGL的浏览器。'); }
  renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 1.5));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.25;
  const canvas = renderer.domElement;
  canvas.className = 'ai-workshop-stage-canvas'; canvas.tabIndex = 0;
  canvas.setAttribute('aria-label', '数字戏台：拖拽旋转，滚轮或双指缩放，轻点人物查看介绍');
  host.append(canvas);
  const hotspots = document.createElement('div'); hotspots.className = 'ai-workshop-stage-hotspots';
  hotspots.setAttribute('aria-label', '人物近看入口'); hotspots.hidden = true; host.append(hotspots);
  const scene = new THREE.Scene(); scene.background = new THREE.Color('#eee4d3');
  const camera = new THREE.PerspectiveCamera(40, 1, 0.02, 300);
  const controls = new OrbitControls(camera, canvas);
  controls.enableDamping = false; controls.enablePan = false;
  controls.minPolarAngle = 0.15; controls.maxPolarAngle = Math.PI / 2 - 0.01;
  controls.minDistance = 3; controls.maxDistance = 40;
  controls.rotateSpeed = 0.8; controls.zoomSpeed = 0.8;
  controls.touches.ONE = THREE.TOUCH.ROTATE; controls.touches.TWO = THREE.TOUCH.DOLLY_ROTATE;
  scene.add(new THREE.HemisphereLight('#fff6e4', '#a69b8b', 2.4));
  const key = new THREE.DirectionalLight('#fff8ef', 3.2); key.position.set(6, 13, 14); scene.add(key);
  const fill = new THREE.DirectionalLight('#e8eef9', 1.8); fill.position.set(-9, 8, -4); scene.add(fill);
  const ground = new THREE.Mesh(new THREE.CircleGeometry(35, 64), new THREE.MeshStandardMaterial({ color: '#dacdb6', roughness: 1 }));
  ground.rotation.x = -Math.PI / 2; ground.position.y = -0.015; scene.add(ground);
  const raycaster = new THREE.Raycaster();
  const pointer = new THREE.Vector2();
  const loader = new GLTFLoader();
  const objects = new Map();
  const hotspotButtons = new Map();
  let stageObject = null, stageKey = '', stagePending = null, requestGeneration = 0, selected = null;
  let visible = true, disposed = false, state = 'idle', interacting = false;
  let frame = null, tracker = createOrbitTracker(), metadata = null, pointerDown = null, pickCount = 0;
  const activePointers = new Set();
  host.dataset.pickCount = '0';
  const activeFetches = new Set();
  const setState = (next, text) => { state = next; if (next !== 'ready') pointerDown = null; host.dataset.stageState = next; hotspots.hidden = next !== 'ready'; onState(next, text); };
  const render = () => { if (!disposed && visible) { renderer.render(scene, camera); positionHotspots(); } };
  function positionHotspots() {
    for (const [id, button] of hotspotButtons) {
      const object = objects.get(id); if (!object) { button.hidden = true; continue; }
      const bounds = new THREE.Box3().setFromObject(object), point = bounds.getCenter(new THREE.Vector3());
      point.y = bounds.max.y + 0.1; point.project(camera);
      button.hidden = point.z < -1 || point.z > 1 || Math.abs(point.x) > 1 || Math.abs(point.y) > 1;
      button.style.left = `${Math.max(65, Math.min(host.clientWidth - 65, (point.x + 1) / 2 * host.clientWidth))}px`;
      button.style.top = `${Math.max(8, (1 - point.y) / 2 * host.clientHeight - 42)}px`;
    }
  }
  function syncHotspots() {
    for (const [id, button] of hotspotButtons) if (!objects.has(id)) { button.remove(); hotspotButtons.delete(id); }
    for (const [id, object] of objects) {
      if (hotspotButtons.has(id)) continue;
      const button = document.createElement('button'); button.type = 'button';
      button.className = 'ai-workshop-stage-person-hotspot'; button.dataset.stagePerson = id;
      button.textContent = `${object.userData.characterName} · 近看`;
      button.setAttribute('aria-label', `近看${object.userData.characterName}`);
      // This is an explicit accessible selector, not a geometry/raycast hit.
      button.addEventListener('click', () => { if (state === 'ready') activateCharacter(id, 'name-button'); });
      hotspotButtons.set(id, button); hotspots.append(button);
    }
  }
  function resize() {
    if (disposed) return;
    const width = Math.max(1, host.clientWidth), height = Math.max(1, host.clientHeight);
    renderer.setSize(width, height, false); camera.aspect = width / height; camera.updateProjectionMatrix(); render();
  }
  const observer = new ResizeObserver(resize); observer.observe(host);
  controls.addEventListener('start', () => { interacting = true; });
  controls.addEventListener('end', () => { interacting = false; });
  controls.addEventListener('change', () => {
    tracker.add(controls.getAzimuthalAngle(), interacting ? 'user-interaction' : 'programmatic', controls.getDistance());
    host.dataset.continuousDegrees = tracker.snapshot().maxContinuousDegrees.toFixed(2); render();
  });
  async function load(entry) {
    if (entry.available === false) throw new Error('这个模型的本地文件暂不可用，请恢复已保存资源后重试。');
    const controller = new AbortController(); activeFetches.add(controller);
    const timer = setTimeout(() => controller.abort(), 90000);
    try {
      const response = await fetch(validUrl(entry.fileUrl), { signal: controller.signal, cache: 'no-store', credentials: 'same-origin' });
      if (!response.ok) throw new Error(response.status === 404 ? '模型文件未找到，请恢复已有资源。' : '暂时无法读取模型，请稍后手动重试。');
      const buffer = await response.arrayBuffer();
      if (buffer.byteLength > 160 * 1024 * 1024) throw new Error('模型过大，当前展示暂不支持。');
      embeddedGlb(buffer);
      const loaded = await loader.parseAsync(buffer, '');
      loaded.scene.traverse((node) => {
        if (node.isMesh) {
          if (!node.geometry.attributes.normal) node.geometry.computeVertexNormals();
          node.castShadow = false; node.receiveShadow = false;
        }
      });
      return loaded.scene;
    } finally { clearTimeout(timer); activeFetches.delete(controller); }
  }
  function arrangeStage(object, entry) {
    const box = new THREE.Box3().setFromObject(object), center = box.getCenter(new THREE.Vector3()), size = box.getSize(new THREE.Vector3());
    const scale = typeof entry.scale === 'number' ? entry.scale : 12 / Math.max(size.x, size.z);
    object.position.set(-center.x, -box.min.y, -center.z);
    const wrapper = new THREE.Group(); wrapper.add(object); wrapper.scale.setScalar(scale);
    wrapper.rotation.y = entry.rotationY ?? Math.PI / 2;
    if (Array.isArray(entry.position)) wrapper.position.fromArray(entry.position);
    return wrapper;
  }
  function arrangeCharacter(object, entry, floor) {
    const initial = new THREE.Box3().setFromObject(object), size = initial.getSize(new THREE.Vector3()), center = initial.getCenter(new THREE.Vector3());
    const scale = typeof entry.scale === 'number' ? entry.scale : 2.15 / Math.max(size.y, 0.001);
    object.position.set(-center.x, -initial.min.y, -center.z);
    const wrapper = new THREE.Group(); wrapper.add(object); wrapper.scale.setScalar(scale);
    wrapper.rotation.y = entry.rotationY || 0; wrapper.position.fromArray(entry.position || [0, floor, 1.6]);
    wrapper.userData.characterId = entry.id; wrapper.userData.characterName = entry.name; wrapper.userData.sourceSha = entry.sha256; wrapper.userData.defaultScale = scale;
    object.traverse((node) => { if (node.isMesh) node.userData.characterId = entry.id; });
    const ring = new THREE.Mesh(new THREE.RingGeometry(0.56, 0.61, 64), new THREE.MeshBasicMaterial({ color: '#bb8b34', side: THREE.DoubleSide, transparent: true, opacity: 0.9, depthWrite: false }));
    ring.rotation.x = -Math.PI / 2; ring.position.set(0, 0.012 / scale, 0); ring.name = 'selection-ring'; ring.visible = false; wrapper.add(ring);
    return wrapper;
  }
  function reset() {
    const target = metadata?.cameraTarget || metadata?.camera?.target || [0, 3.1, 0];
    const position = metadata?.cameraPosition || metadata?.camera?.position || [11.5, 7.5, 17.5];
    camera.position.fromArray(position); controls.target.fromArray(target); controls.update(); render();
    host.dataset.focusedCharacter = '';
    if (state === 'ready') setState('ready', '戏台已就绪 · 点击人物、姓名或左侧卡片近看');
  }
  function selectCharacter(id) {
    if (!objects.has(id)) return false;
    selected = id; host.dataset.selectedCharacter = id;
    for (const [key, value] of objects) { const ring = value.getObjectByName('selection-ring'); if (ring) ring.visible = key === id; }
    render(); return true;
  }
  function focusCharacter(id) {
    const object = objects.get(id);
    if (!object || state !== 'ready') return;
    const box = new THREE.Box3().setFromObject(object), center = box.getCenter(new THREE.Vector3());
    controls.target.copy(center); camera.position.copy(center).add(new THREE.Vector3(1.3, 0.8, 5.2)); controls.update(); render();
    host.dataset.focusedCharacter = id;
    setState('ready', `近看${object.userData.characterName} · 拖拽观察，重置视角返回戏台`);
  }
  function activateCharacter(id, source) {
    if (state !== 'ready' || !visible || !objects.has(id)) return;
    host.dataset.lastActivationSource = source;
    selectCharacter(id); focusCharacter(id); onCharacterPick(id);
  }
  async function loadScene({ stage, characters }) {
    const ticket = ++requestGeneration; metadata = stage;
    const created = new Set();
    const releaseCreated = () => { for (const object of created) free(object); created.clear(); };
    setState('loading', '正在布置戏台与人物……'); selected = null;
    host.dataset.selectedCharacter = ''; host.dataset.readyCharacters = '';
    try {
      const nextKey = `${stage.id}:${stage.sha256}`;
      if (stageKey !== nextKey || !stageObject) {
        if (!stagePending || stagePending.key !== nextKey) {
          stagePending = { key: nextKey, promise: load(stage).then((object) => arrangeStage(object, stage)) };
        }
        const value = await stagePending.promise;
        if (ticket !== requestGeneration || disposed) return false;
        if (stageObject && stageObject !== value) { scene.remove(stageObject); free(stageObject); }
        stageObject = value; stageKey = nextKey; scene.add(value); stagePending = null;
      }
      const next = new Map();
      for (const entry of characters) {
        const prior = objects.get(entry.id);
        const existing = prior?.userData.sourceSha === entry.sha256 ? prior : null;
        const object = existing || arrangeCharacter(await load(entry), entry, stage.floorY ?? 0.9);
        if (!existing) created.add(object);
        if (ticket !== requestGeneration || disposed) { releaseCreated(); return false; }
        object.position.fromArray(entry.position || [0, stage.floorY ?? 0.9, 1.6]);
        object.rotation.y = entry.rotationY || 0; object.scale.setScalar(entry.scale ?? object.userData.defaultScale);
        next.set(entry.id, object);
      }
      for (const [id, object] of objects) if (next.get(id) !== object) { scene.remove(object); free(object); }
      objects.clear(); for (const [id, object] of next) { objects.set(id, object); scene.add(object); }
      created.clear();
      syncHotspots();
      tracker = createOrbitTracker(); host.dataset.continuousDegrees = '0'; reset(); resize();
      host.dataset.readyCharacters = JSON.stringify([...objects.keys()]);
      setState('ready', '戏台已就绪 · 点击人物、姓名或左侧卡片近看'); render(); return true;
    } catch (error) {
      releaseCreated();
      if (ticket !== requestGeneration || disposed) return false;
      stagePending = null;
      setState('error', error?.name === 'AbortError' ? '模型读取超时，请检查本地资源后手动重试。' : error.message || '戏台暂时未能加载，请手动重试。');
      return false;
    }
  }
  function characterAt(x, y) {
    if (state !== 'ready') return null;
    camera.updateMatrixWorld();
    const box = canvas.getBoundingClientRect(); pointer.set((x - box.left) / box.width * 2 - 1, -(y - box.top) / box.height * 2 + 1);
    raycaster.setFromCamera(pointer, camera);
    const meshes = []; for (const object of objects.values()) object.traverse((node) => { if (node.isMesh && node.userData.characterId) meshes.push(node); });
    const hit = raycaster.intersectObjects(meshes, false)[0];
    const obstruction = hit && stageObject ? raycaster.intersectObject(stageObject, true)[0] : null;
    return hit && (!obstruction || obstruction.distance >= hit.distance - 0.025) ? hit.object.userData.characterId : null;
  }
  canvas.addEventListener('pointerdown', (event) => {
    activePointers.add(event.pointerId);
    if (activePointers.size !== 1 || event.button !== 0) { pointerDown = null; return; }
    // Resolve before OrbitControls moves the camera during a small finger jitter.
    pointerDown = { x: event.clientX, y: event.clientY, id: event.pointerId, limit: event.pointerType === 'touch' ? 12 : 7, hit: characterAt(event.clientX, event.clientY) };
  });
  canvas.addEventListener('pointermove', (event) => {
    if (pointerDown?.id === event.pointerId && Math.hypot(event.clientX - pointerDown.x, event.clientY - pointerDown.y) > pointerDown.limit) pointerDown = null;
  });
  canvas.addEventListener('pointerup', (event) => {
    const down = pointerDown; pointerDown = null; activePointers.delete(event.pointerId);
    if (state !== 'ready' || !down?.hit || down.id !== event.pointerId || activePointers.size || Math.hypot(event.clientX - down.x, event.clientY - down.y) > down.limit) return;
    pickCount++; host.dataset.pickCount = String(pickCount); host.dataset.pickedCharacter = down.hit;
    activateCharacter(down.hit, 'geometry');
  });
  canvas.addEventListener('pointercancel', (event) => { pointerDown = null; activePointers.delete(event.pointerId); });
  canvas.addEventListener('lostpointercapture', (event) => { pointerDown = null; activePointers.delete(event.pointerId); });
  canvas.addEventListener('webglcontextlost', (event) => { event.preventDefault(); setState('error', '3D显示连接已中断，请刷新页面恢复；不会重新生成模型。'); });
  const api = {
    loadScene, selectCharacter, focusCharacter, reset,
    zoom(factor) { if (!Number.isFinite(factor) || factor <= 0 || state !== 'ready') return; const vector = camera.position.clone().sub(controls.target); vector.setLength(THREE.MathUtils.clamp(vector.length() * factor, controls.minDistance, controls.maxDistance)); camera.position.copy(controls.target).add(vector); controls.update(); render(); },
    setVisible(value) { visible = Boolean(value); if (!visible) { pointerDown = null; activePointers.clear(); } if (visible) { cancelAnimationFrame(frame); frame = requestAnimationFrame(resize); } },
    snapshot() {
      const rect = canvas.getBoundingClientRect();
      return { state, selected, pickCount, readyCharacters: [...objects.keys()], camera: camera.position.toArray(), target: controls.target.toArray(), distance: controls.getDistance(), orbit: tracker.snapshot(), rendererTriangles: renderer.info.render.triangles,
        characterPoints: [...objects.entries()].map(([id, object]) => { const point = new THREE.Box3().setFromObject(object).getCenter(new THREE.Vector3()).project(camera); return { id, x: rect.left + (point.x + 1) / 2 * rect.width, y: rect.top + (1 - point.y) / 2 * rect.height }; }) };
    },
    dispose() { disposed = true; requestGeneration++; observer.disconnect(); controls.dispose(); for (const value of activeFetches) value.abort(); for (const value of objects.values()) free(value); free(stageObject); free(ground); renderer.dispose(); canvas.remove(); hotspots.remove(); hotspotButtons.clear(); cancelAnimationFrame(frame); },
  };
  host.stageViewer = api;
  resize(); return api;
}
