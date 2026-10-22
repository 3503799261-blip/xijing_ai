"""VS Code entry: validate existing resources, serve once, open after readiness.

No dependency installation, database creation, ingestion or vendor requests.
Uvicorn runs in this process so stopping the debugger leaves no child server.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import hashlib
import http.client
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import socket
import sqlite3
import struct
import sys
import threading
import time
import webbrowser

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / '.venv' / 'Scripts' / 'python.exe'
HOST, PORT = '127.0.0.1', 8000
WORKSHOP_URL = f'http://{HOST}:{PORT}/about.html#ai-workshop'
DEPENDENCIES = ('uvicorn', 'fastapi', 'pydantic_settings', 'httpx', 'portalocker',
                'sentence_transformers', 'qdrant_client', 'torch', 'PIL')


class LaunchError(Exception):
    """Only safe, deliberately authored Chinese messages reach the console."""


def say(message):
    print(f'[戏境 AI] {message}', flush=True)


def require_file(path, label):
    if not Path(path).is_file():
        raise LaunchError(f'缺少或无法读取{label}。请恢复原有资源或核对配置；启动器不会新建或重建。')


def read_json(path, label):
    require_file(path, label)
    try:
        value = Path(path).read_text(encoding='utf-8')
        return json.loads(value)
    except (OSError, ValueError):
        raise LaunchError(f'{label}无法读取或格式损坏。请保留原文件并检查备份；未执行修复。') from None


def read_database(path, label, query):
    require_file(path, label)
    try:
        with closing(sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True, timeout=2)) as db:
            db.execute('PRAGMA query_only=ON')
            if db.execute('PRAGMA quick_check(1)').fetchone() != ('ok',):
                raise sqlite3.DatabaseError('integrity')
            return query(db)
    except (sqlite3.Error, OSError):
        raise LaunchError(f'{label}不可读取、结构不完整或已损坏。未初始化、覆盖或重建，请核对原库后再启动。') from None


def check_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        try:
            # On Windows, avoid SO_REUSEADDR accepting an occupied listener.
            if os.name == 'nt':
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            probe.bind((HOST, PORT))
        except OSError:
            raise LaunchError('8000端口已被占用或不可用。若项目已运行，请先用原调试栏红色停止按钮停止；不会结束其他进程或自动换端口。') from None


def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def check_models(root, records):
    count = 0
    styles = set()
    for (raw,) in records:
        try:
            model = json.loads(raw)
            if model.get('origin') not in {'neural4d', 'neural4d_technical_test'}:
                continue
            key = model['storageKey']
            digest = model['hash']
            if not isinstance(key, str) or not re.fullmatch(r'[a-f0-9]{64}', digest):
                raise ValueError('metadata')
            original = root / key
            path = original.resolve()
            if (original.is_symlink() or not path.is_relative_to(root.resolve())
                    or not path.is_relative_to((root / 'models').resolve())):
                raise ValueError('path')
            require_file(path, '已登记的真实GLB模型')
            with path.open('rb') as source:
                header = source.read(12)
            if (len(header) != 12 or header[:4] != b'glTF'
                    or struct.unpack('<II', header[4:]) != (2, path.stat().st_size)
                    or path.stat().st_size != model['size'] or file_hash(path) != digest):
                raise ValueError('integrity')
            count += 1
            styles.add(model.get('styleMode'))
        except LaunchError:
            raise
        except (OSError, ValueError, TypeError, KeyError):
            raise LaunchError('已有模型记录、路径、GLB头或Hash不匹配。请恢复配套原资产；不会重新下载或建模。') from None
    if count < 2 or not {'chibi', 'realistic'}.issubset(styles):
        raise LaunchError('现有Q版或写实真实GLB登记不完整。请核对两个已验收模型的资产库与文件，不会使用测试模型冒充成品。')
    return count


def check_resources(settings, workspace_root):
    """Read metadata only; do not construct stores, providers or the app."""
    data = settings.rag_data_dir
    active = read_json(data / 'active.json', '活动知识版本清单')
    generation = active.get('generation_id') if isinstance(active, dict) else None
    if not isinstance(generation, str) or not re.fullmatch(r'gen-[A-Za-z0-9-]+', generation):
        raise LaunchError('活动知识版本标识无效；未改写active.json或新建知识库。')
    target = data / 'generations' / generation
    # Guard symlinks/junctions as well as lexical generation names.
    if not target.resolve().is_relative_to((data / 'generations').resolve()):
        raise LaunchError('活动知识版本路径异常，请核对原配置；未修改任何资源。')
    chunks = read_database(target / 'knowledge.sqlite3', '活动京剧知识数据库',
                           lambda db: db.execute('SELECT count(*) FROM chunks').fetchone()[0])
    metadata = read_json(target / 'qdrant' / 'meta.json', 'Qdrant集合元数据')
    if not isinstance(metadata, dict) or 'opera_chunks' not in metadata.get('collections', {}):
        raise LaunchError('已有Qdrant京剧集合缺失；不会创建空集合或自动重建索引。')
    require_file(target / 'qdrant' / 'collection' / 'opera_chunks' / 'storage.sqlite', 'Qdrant持久化数据')
    manifest = read_json(settings.embedding_model_path / 'model-manifest.json', 'BGE模型版本清单')
    if not isinstance(manifest, dict) or manifest.get('revision') != active.get('model_revision'):
        raise LaunchError('BGE模型版本与知识索引不匹配，请恢复配套缓存；不会下载模型。')
    require_file(settings.embedding_model_path / 'model.safetensors', 'BGE本地模型权重')
    if chunks < 1:
        raise LaunchError('活动知识库没有片段；请检查原资源，不会自动执行入库。')
    pending = read_database(data / 'agent-tasks.sqlite3', 'Agent历史数据库',
                            lambda db: db.execute("SELECT count(*) FROM agent_tasks WHERE state IN ('waiting','running')").fetchone()[0])
    if pending:
        raise LaunchError('存在尚未结束的Agent任务。为避免启动恢复改写旧记录，已停止；请先核查原任务，启动器不会重跑或取消。')
    scope = read_database(data / 'api-budget.sqlite3', '模型预算数据库',
                          lambda db: db.execute("SELECT budget_cny FROM budget_scopes WHERE name='phase3'").fetchone())
    if scope is None or not math.isclose(scope[0], settings.agent_test_budget_cny, rel_tol=0, abs_tol=1e-9):
        raise LaunchError('现有phase3预算范围与配置不一致。已停止，避免启动时新增或修改预算记录；请核查原配置。')
    if settings.neural4d_generation_enabled or settings.neural4d_protocol_verified:
        raise LaunchError('Neural4D创建或协议开关未关闭。请保留现有成果并关闭创建相关开关后再运行；启动器不会修改.env。')
    ledger = workspace_root / '.runtime' / 'neural4d-usage.sqlite3'
    def usage(db):
        policy = db.execute('SELECT max_attempts,historical_used,historical_verified_at FROM neural4d_usage_policy').fetchall()
        states = db.execute('SELECT state FROM neural4d_creation_attempts').fetchall()
        return policy, states
    policy, states = read_database(ledger, '全项目Neural4D额度账本', usage)
    if (len(policy) != 1 or policy[0][0] != 3 or policy[0][1] is None
            or not policy[0][2] or len(states) + policy[0][1] > 3):
        raise LaunchError('全项目额度历史未核实或不一致；未重置额度，真实创建继续关闭。')
    if any(state not in {'SUCCEEDED', 'FAILED'} for (state,) in states):
        raise LaunchError('存在未完成或状态未知的Neural4D任务。已停止，避免启动恢复修改历史；不会查询供应商或重新创建。')
    root = data / 'assets'
    records = read_database(root / 'catalog.sqlite3', '角色资产数据库',
                            lambda db: db.execute('SELECT content_json FROM asset_models').fetchall())
    models = check_models(root, records)
    return {'chunks': chunks, 'models': models, 'used': len(states) + policy[0][1]}


def health_ready():
    connection = http.client.HTTPConnection(HOST, PORT, timeout=1)
    try:
        connection.request('GET', '/api/v1/health')
        response = connection.getresponse()
        data = json.loads(response.read(128 * 1024))
        return bool(response.status == 200 and data.get('application', {}).get('available')
                    and data.get('knowledge') and data.get('databases', {}).get('agent', {}).get('available')
                    and data.get('databases', {}).get('budget', {}).get('available'))
    except (OSError, ValueError, http.client.HTTPException):
        return False
    finally:
        connection.close()


def open_when_ready(server, stopped, result, *, browser=True, timeout=120, opener=None):
    deadline = time.monotonic() + timeout
    while not stopped.wait(0.25):
        if server.started and health_ready():
            result['ready'] = True
            say(f'服务已就绪：{WORKSHOP_URL}')
            say('已载入本地知识库与历史档案；本地就绪不代表已验证外部API。')
            if browser:
                try:
                    opened = (opener or webbrowser.open)(WORKSHOP_URL, new=2)
                    if not opened:
                        say(f'浏览器未能自动打开。服务仍正常，可点击以上地址。')
                except Exception:
                    say('浏览器未能自动打开；请点击以上工坊地址。不会重新启动服务。')
            return
        if time.monotonic() >= deadline:
            result['error'] = '启动等待超时；本地模型或数据库未能就绪。请查看上方诊断并检查原资源，不要初始化或重建。'
            server.should_exit = True
            return


def main(argv=None):
    parser = argparse.ArgumentParser(description='戏境 AI 安全本地启动；不会安装、初始化或调用供应商。')
    parser.add_argument('--check', action='store_true', help='只读预检，不启动服务或浏览器')
    parser.add_argument('--no-browser', action='store_true', help='启动服务但不打开浏览器（测试用）')
    args = parser.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='replace')
    try:
        require_file(PYTHON, '项目.venv虚拟环境中的Python')
        if Path(sys.executable).resolve() != PYTHON.resolve():
            os.execv(str(PYTHON), [str(PYTHON), str(Path(__file__).resolve()), *(argv if argv is not None else sys.argv[1:])])
        os.chdir(ROOT)
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        missing = [name for name in DEPENDENCIES if importlib.util.find_spec(name) is None]
        if missing:
            raise LaunchError('现有.venv缺少依赖：' + '、'.join(missing) + '。请按原README修复环境；启动器不会自动安装。')
        # The existing embedding path is offline-only; these also prevent Hub probes.
        os.environ['HF_HUB_OFFLINE'] = '1'
        os.environ['TRANSFORMERS_OFFLINE'] = '1'
        os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
        sys.dont_write_bytecode = True
        try:
            from backend.app.config import Settings, WORKSPACE_ROOT
            settings = Settings()
        except Exception:
            raise LaunchError('现有私有配置无法读取或参数无效。请核对原.env的路径和配置格式；不输出配置内容，也不会覆盖文件。') from None
        check_port()
        stats = check_resources(settings, WORKSPACE_ROOT)
        say(f'只读预检通过：{stats["chunks"]}个知识片段、{stats["models"]}个真实模型；建模已用{stats["used"]}/3，创建关闭。')
        if args.check:
            return 0
        import uvicorn
        # No subprocess/reloader: VS Code stops exactly this serving process.
        server = uvicorn.Server(uvicorn.Config('backend.app.main:app', host=HOST, port=PORT,
                                             workers=1, access_log=False, log_level='info'))
        stopped, result = threading.Event(), {}
        watcher = threading.Thread(target=open_when_ready, args=(server, stopped, result),
                                   kwargs={'browser': not args.no_browser}, daemon=True)
        watcher.start()
        say('正在启动，请等待本地模型加载；不需要重复点击绿色按钮。停止请用调试栏红色方块。')
        try:
            server.run()
        finally:
            stopped.set()
            watcher.join(timeout=2)
        if result.get('error'):
            raise LaunchError(result['error'])
        if not result.get('ready'):
            raise LaunchError('服务未能就绪，已停止；请检查端口、原有资源及上方服务日志，不要重建数据库。')
        say('服务已停止，未重新提交AI或建模任务。')
        return 0
    except KeyboardInterrupt:
        say('已取消启动。')
        return 0
    except LaunchError as error:
        say('启动停止：' + str(error))
        return 1
    except Exception:
        say('启动失败：本地环境或资源出现异常。请查看local-run-setup报告；未执行安装、重建或付费重试。')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
