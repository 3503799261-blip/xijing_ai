"""Register a licensed existing test GLB locally; never call any provider."""
import json
import sys
from pathlib import Path
from ..app.config import Settings, PROJECT_ROOT
from ..app.agents.store import TaskStore
from ..app.assets.service import AssetService


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    settings = Settings()
    service = AssetService(settings, TaskStore(settings.rag_data_dir / 'agent-tasks.sqlite3'))
    fixture = PROJECT_ROOT / 'backend/tests/fixtures/phase4/Duck.glb'
    model = service.register_fixture(fixture.read_bytes(),
        'Khronos glTF-Sample-Assets Duck；©2006 Sony；SCEA Shared Source License1.0。完整许可位于backend/tests/fixtures/phase4/SCEA-LICENSE.txt。仅Viewer验证，非Neural4D/京剧角色。',
        'Duck · 合法已有GLB交互测试（非Neural4D生成）')
    print(json.dumps(model, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
