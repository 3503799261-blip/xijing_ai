"""Explicit local manifest preparation; never initializes any business database."""
import argparse
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description='从已转换模型生成数字戏台只读资源清单，不调用供应商。')
    parser.add_argument('--assets-dir', type=Path, default=ROOT.parent / '.runtime/digital-stage/assets')
    args = parser.parse_args()
    output = args.assets_dir.resolve()
    conversion = json.loads((output / 'manifest-conversion.json').read_text(encoding='utf-8'))
    template = json.loads((ROOT / 'stage/catalog.json').read_text(encoding='utf-8'))
    source_records = {entry['id']: entry for entry in conversion['characters']}
    source_records['stage-main'] = conversion['stage']
    for entry in [template['stage'], *template['characters']]:
        original = source_records[entry['id']]
        path = output / entry['file']
        with path.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        if digest != original['sha256'] or path.stat().st_size != original['sizeBytes']:
            raise SystemExit('派生模型与转换记录不一致，未创建清单：' + entry['id'])
        entry.update(sha256=digest, sizeBytes=path.stat().st_size,
                     attribution='用户提供的3D素材，经确定性格式与贴图适配；并非本轮平台AI生成。',
                     licenseNote='用户声明：公开资源，仅供比赛使用，不做商用。', purpose='competition_only_noncommercial')
    bounds = conversion['stage']['bounds']
    size = [b - a for a, b in zip(bounds['min'], bounds['max'])]
    scale = 12 / max(size[0], size[2])
    floor = (1041.3968505859375 - bounds['min'][1]) * scale
    template['stage'].update(scale=scale, floorY=floor, bounds=bounds)
    for entry in template['characters']:
        entry['position'][1] = floor
    content = json.dumps(template, ensure_ascii=False, indent=2) + '\n'
    target = output / 'manifest.json'
    if target.exists() and target.read_text(encoding='utf-8') == content:
        print('数字戏台清单未变化，保留当前版本。')
        return
    if target.exists():
        history = output / 'versions'
        history.mkdir(exist_ok=True)
        raw = target.read_bytes()
        old = history / ('manifest-' + hashlib.sha256(raw).hexdigest() + '.json')
        if not old.exists():
            old.write_bytes(raw)
    temporary = output / 'manifest.json.pending'
    temporary.write_text(content, encoding='utf-8')
    os.replace(temporary, target)
    print('数字戏台清单已准备：1个舞台、3个人物；没有注册新资产或调用API。')


if __name__ == '__main__':
    main()
