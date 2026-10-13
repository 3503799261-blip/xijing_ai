import { validateAssetModel } from './contracts.js?v=phase4-1';
import { initializeModelViewer } from './model-viewer-adapter.js?v=phase4-1';

// Reads one saved local artifact only. No supplier or generation capability.
const root = document.getElementById('ai-workshop-internal-root');
if (root) {
  const viewer = initializeModelViewer({ root });
  try {
    const id = root.dataset.modelId;
    if (!/^[a-f0-9-]{36}$/.test(id || '')) throw new Error('模型标识无效');
    const response = await fetch(`/api/v1/assets/models/${id}`, { cache: 'no-store', signal: AbortSignal.timeout(10000) });
    if (!response.ok) throw new Error('无法读取本地内部模型');
    const model = validateAssetModel(await response.json());
    if (model.origin !== 'neural4d_technical_test' || model.internalUseOnly !== true) throw new Error('不是内部技术验证模型');
    await viewer.load(model);
  } catch {
    root.querySelector('#ai-workshop-viewer-status').textContent = '模型读取失败';
    const error = root.querySelector('#ai-workshop-viewer-error');
    error.textContent = '请检查本地服务、内部访问条件和已保存模型。不会重新生成模型。';
    error.hidden = false;
  }
}
