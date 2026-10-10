"""Download one pinned public BGE snapshot; no duplicate PyTorch bin weight."""
import hashlib
import json
import time
from pathlib import Path
from datetime import datetime, timezone
from huggingface_hub import snapshot_download
from backend.app.config import Settings

def main():
    settings = Settings()
    started = time.perf_counter()
    revision = '7999e1d3359715c523056ef9478215996d62a620'
    target = settings.embedding_model_path
    snapshot_download(settings.embedding_model, revision=revision, local_dir=target, allow_patterns=['*.json', 'vocab.txt', 'tokenizer*', 'special_tokens_map.json', 'model.safetensors', '1_Pooling/config.json', 'README.md'])
    files = []
    for path in sorted(target.rglob('*')):
        if path.is_file() and '.cache' not in path.parts:
            files.append({'file': path.relative_to(target).as_posix(), 'bytes': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    report = {'model_id': settings.embedding_model, 'revision': revision, 'license': 'MIT', 'downloaded_at': datetime.now(timezone.utc).isoformat(), 'elapsed_seconds': round(time.perf_counter()-started, 3), 'files': files, 'source_url': 'https://huggingface.co/' + settings.embedding_model}
    (target / 'model-manifest.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=True))

if __name__ == '__main__': main()
