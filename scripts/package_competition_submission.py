"""Copy reviewed competition materials; never start the app or package private stores.

Requires a clean committed source tree. Output is ignored by Git. Existing output
is refused, so a later run cannot overwrite a user video or reviewed submission.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
from datetime import datetime, timezone, timedelta
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = [re.compile(rb'\bsk-(?:proj-|ant-)?[A-Za-z0-9_-]{20,}'),
            re.compile(rb'\b(?:ghp_|github_pat_)[A-Za-z0-9_]{20,}'),
            re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----')]


def git(*args, **kwargs):
    return subprocess.run(['git', *args], cwd=ROOT, check=True, capture_output=True, **kwargs).stdout


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for data in iter(lambda: handle.read(4 * 1024 * 1024), b''):
            h.update(data)
    return h.hexdigest()


def check_history():
    """Scan all reachable text versions, printing no matched credential values."""
    entries = {}
    suffixes = {'.md', '.py', '.js', '.mjs', '.json', '.txt', '.css', '.html', '.toml', '.ini', '.yml', '.yaml', '.xml', '.example'}
    for line in git('rev-list', '--objects', 'HEAD').decode('utf-8').splitlines():
        oid, _, name = line.partition(' ')
        if name and (Path(name).suffix.lower() in suffixes or Path(name).name in {'LICENSE', '.gitignore'}):
            entries[oid] = name
    process = subprocess.run(['git', 'cat-file', '--batch'], cwd=ROOT,
                             input=('\n'.join(entries) + '\n').encode('ascii'), capture_output=True, check=True)
    stream = io.BytesIO(process.stdout)
    findings = []
    count = 0
    for expected_oid, name in entries.items():
        oid, kind, size = stream.readline().decode('ascii').strip().split()
        assert oid == expected_oid and kind == 'blob'
        data = stream.read(int(size)); assert stream.read(1) == b'\n'
        count += 1
        if any(pattern.search(data) for pattern in PATTERNS):
            findings.append({'objectId': oid, 'file': name})
    return {'textVersionsChecked': count, 'findings': findings,
            'scope': 'All reachable text blobs at HEAD; pattern scan only, no secret values printed or saved.'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--client-date', default=datetime.now(timezone(timedelta(hours=8))).date().isoformat())
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    output = (args.output or ROOT/'output/competition-submission'/('最终提交版-'+args.client_date)).resolve()
    if not output.is_relative_to(ROOT/'output'):
        raise SystemExit('交付目录必须位于本项目output中。')
    if output.exists():
        raise SystemExit('交付目录已存在，保留用户文件；请指定新的output子目录，不会覆盖。')
    if git('status', '--porcelain').strip():
        raise SystemExit('工作区尚未干净，未打包；先核对并保存所有本轮修改。')
    history = check_history()
    if history['findings']:
        raise SystemExit('历史文本疑似敏感信息，已阻止打包；未记录匹配值。需人工复核。')
    head = git('rev-parse', 'HEAD').decode().strip()
    branch = git('branch', '--show-current').decode().strip()
    if not branch:
        raise SystemExit('需要明确的当前分支，未切换或创建分支。')
    folders = ['01-项目源码与Git历史','02-技术文档','03-演示视频-待用户录制',
               '04-开发记录与测试证据','05-手动验收与提交清单','06-本机演示资源索引-不直接公开']
    for name in folders:
        (output/name).mkdir(parents=True)
    code, pdf, video, evidence, checks, private = [output/name for name in folders]
    def text(path, content): path.write_text(content.strip()+'\n', encoding='utf-8-sig')
    def cp(source, target): shutil.copyfile(ROOT/source, target)
    git('archive','--format=zip','--prefix=xijing-ai/','--output='+str(code/'xijing-ai-source.zip'),'HEAD')
    git('bundle','create',str(code/'xijing-ai-history.bundle'),'HEAD','refs/heads/'+branch)
    bundle_check = git('bundle','verify',str(code/'xijing-ai-history.bundle')).decode('utf-8',errors='replace')
    text(code/'使用说明.md',f'''# 当前源码与真实历史

源码版本：{head}
分支：{branch}

`xijing-ai-source.zip`是当前版本，不包含.git。
`xijing-ai-history.bundle`保留此版本的完整真实Git历史，不伪造或压缩提交。
如需从历史包恢复独立源码目录，可使用：

```text
git clone -b {branch} xijing-ai-history.bundle xijing-ai
```

不要解压覆盖当前原项目。源码不包含私有数据库、BGE/Qdrant缓存、.env和成品GLB。
本脚本仅打包，不执行推送；已经完成的Public仓库、默认分支与远端版本核验见交付根目录GitHub上传校验.json。
''')
    cp('output/pdf/xijing-ai-technical-report.pdf',pdf/'戏境AI-技术文档-9页.pdf')
    cp('docs/evidence/test-results/digital-stage-delivery/pdf-validation.json',pdf/'PDF校验记录.json')
    cp('docs/reports/phase-05-demo-script.md',video/'参考演示讲稿.md')
    text(video/'视频请录好后放这里.md','''# 待用户自行录制

按用户要求，本轮没有录视频，没有空白或占位MP4。
完成后将最终成片放到这个目录。

- MP4，5～8分钟，分辨率不低于1080p。
- 普通话讲解，可配字幕，包含项目介绍、核心功能和AI技术亮点。
- 真实AI协作片段可从已有Prompt、Git和失败修复证据选取，不必重新付费生成。
- 历史任务明确说历史，用户提供的舞台/人物不说成平台当场生成。
- 原内部Q素材不要混入公开录屏；参赛范围按素材声明和清单核对。
''')
    names = git('ls-files','-z','--','docs').decode('utf-8').split('\0')
    with zipfile.ZipFile(evidence/'xijing-ai-docs-and-evidence.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for name in names:
            if name and (ROOT/name).is_file(): archive.write(ROOT/name,name)
    text(evidence/'先读这两份.md','''# 索引

解压证据包后：
1. docs/reports/digital-stage-delivery.md：本轮实现、实际测试、失败和限制。
2. docs/evidence/test-results/digital-stage-delivery/README.md：JUnit、浏览器、资源Hash等原始证据。
3. docs/reports/phase-05-evidence-index.md：历史阶段证据。
4. docs/prompts/：真实开发Prompt及演进。

不同阶段和重复专项不相加成独立测试总量。私有截图仅记录Hash，不在此公开像素。
''')
    for source in ['docs/reports/submission-manual-check.md','docs/reports/phase-05-submission-checklist.md',
                   'docs/reports/digital-stage-delivery.md','docs/reports/phase-05-requirements-evidence-map.md']:
        cp(source,checks/Path(source).name)
    text(private/'本机资源位置.md',f'''# 本机演示资源索引（不含资源正文）

原项目：{ROOT}
新源素材：项目下“中式古戏台SU模型”“3D人物模型”；没有搬动。
新派生舞台/人物GLB及manifest：{ROOT.parent / '.runtime/digital-stage/assets'}
既有真实GLB、输入图与资产catalog：{ROOT.parent / '.runtime/xijing-ai/assets'}
Agent数据库、预算、活动知识索引：{ROOT.parent / '.runtime/xijing-ai'}
BGE本地模型：{ROOT.parent / '.runtime/models/bge-small-zh-v1.5'}
Neural4D真实额度台账：{ROOT.parent / '.runtime/neural4d-usage.sqlite3'}

这些资源原位保留，没有复制到源码包。不含真实.env、API Key或历史业务库正文。
新模型仅比赛非商用；原内部Q仅内部，不能因此公开全部原模型或商用。
完整跨机恢复未验证；不要用空初始化/重建覆盖真实数据。
正常启动用现有VS Code“戏境 AI：一键运行”，无需转换/安装/建库。
''')
    for source in ['docs/evidence/test-results/digital-stage-delivery/source-invariants.json',
                   'docs/evidence/test-results/digital-stage-delivery/existing-resource-comparison.json',
                   'docs/evidence/test-results/digital-stage-delivery/business-invariants.json']:
        cp(source,private/Path(source).name)
    cp('docs/reports/submission-manual-check.md',output/'先看这里-分类与手动检查.md')
    text(output/'阅读顺序.txt','先看这里-分类与手动检查.md\n先启动网页亲自检查，再看02技术PDF；把你录好的视频放入03。\n此目录不是已经上传的赛事提交；06只供本机恢复，不要无差别公开整个工作目录。')
    for path in output.rglob('*.zip'):
        with zipfile.ZipFile(path) as archive:
            if archive.testzip() is not None: raise SystemExit('ZIP完整性校验失败。')
            bad=[name for name in archive.namelist() if Path(name).name=='.env' or '/.venv/' in name or '/.runtime/' in name or '/3D人物模型/' in name or '/中式古戏台SU模型/' in name]
            if bad: raise SystemExit('ZIP包含不应打包的本机资源，已停止。')
    files=[{'file':path.relative_to(output).as_posix(),'bytes':path.stat().st_size,'sha256':digest(path)}
           for path in sorted(output.rglob('*')) if path.is_file()]
    manifest={'createdAtUtc':datetime.now(timezone.utc).isoformat(),'clientDate':args.client_date,
              'branch':branch,'head':head,'workingTreeBefore':'clean','workingTreeAfter':git('status','--porcelain').decode('utf-8'),
              'gitLog':git('log','-8','--format=%H %s').decode('utf-8').splitlines(),
              'historyCredentialPatternScan':history,'gitBundleVerify':bundle_check,
              'paidApiCalls':0,'neural4dCalls':0,'video':'USER_WILL_RECORD; NO_MP4_GENERATED',
              'excluded':'Real .env, venv, private databases, BGE/Qdrant data, raw/private 3D model assets',
              'files':files,'zipIntegrity':'PASS','submissionStatus':'WAITING_USER_REVIEW; no push/upload'}
    (output/'最终版本与文件Hash.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'output':str(output),'head':head,'files':len(files),'zipIntegrity':'PASS',
                      'historicalTextBlobsChecked':history['textVersionsChecked'],'findings':0},ensure_ascii=True))


if __name__=='__main__': main()
