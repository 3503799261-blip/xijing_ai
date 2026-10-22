"""Offline launcher tests; every database and synthetic GLB stays in a temp dir.

The tiny GLB fixtures only exercise launcher metadata/header validation. They are
explicit test data, not rendered models or evidence of real model generation.
No app import, production store, external HTTP request, or browser is used.
"""
from __future__ import annotations

from contextlib import closing
import hashlib
import importlib.util
import json
from pathlib import Path
import socket
import sqlite3
import struct
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


SPEC = importlib.util.spec_from_file_location(
    'run_local_test_subject', Path(__file__).resolve().parents[1] / 'run_local.py')
launcher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(launcher)


class LocalRunTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='xijing-launcher-test-')
        self.addCleanup(self.temporary.cleanup)
        self.workspace = Path(self.temporary.name)
        self.data = self.workspace / 'private-data'
        self.embedding = self.workspace / 'embedding'
        self.settings = SimpleNamespace(
            rag_data_dir=self.data,
            embedding_model_path=self.embedding,
            agent_test_budget_cny=0.5,
            neural4d_generation_enabled=False,
            neural4d_protocol_verified=False,
        )
        self.asset_root = self.data / 'assets'
        self.agent = self.data / 'agent-tasks.sqlite3'
        self.budget = self.data / 'api-budget.sqlite3'
        self.usage = self.workspace / '.runtime' / 'neural4d-usage.sqlite3'
        self.catalog = self.asset_root / 'catalog.sqlite3'
        self.records = []

    def write_json(self, path, content):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(content), encoding='utf-8')

    def database(self, path, sql, rows=()):
        path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(path)) as db, db:
            db.executescript(sql)
            for query, parameters in rows:
                db.execute(query, parameters)

    def model_record(self, style, *, key=None):
        key = key or f'models/{style}/viewer.glb'
        path = self.asset_root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = b'test-only-' + style.encode('ascii')
        content = b'glTF' + struct.pack('<II', 2, 12 + len(payload)) + payload
        path.write_bytes(content)
        return {
            'origin': 'neural4d_technical_test' if style == 'chibi' else 'neural4d',
            'storageKey': key,
            'hash': hashlib.sha256(content).hexdigest(),
            'size': len(content),
            'styleMode': style,
        }

    def fixture(self):
        generation = self.data / 'generations' / 'gen-test-1'
        self.write_json(self.data / 'active.json', {
            'generation_id': 'gen-test-1', 'model_revision': 'fixture-revision'})
        self.database(generation / 'knowledge.sqlite3',
                      'CREATE TABLE chunks(content TEXT); INSERT INTO chunks VALUES (\'测试片段\');')
        self.write_json(generation / 'qdrant' / 'meta.json', {
            'collections': {'opera_chunks': {}}})
        qdrant = generation / 'qdrant' / 'collection' / 'opera_chunks' / 'storage.sqlite'
        qdrant.parent.mkdir(parents=True, exist_ok=True)
        qdrant.write_bytes(b'explicit metadata-only test fixture')
        self.write_json(self.embedding / 'model-manifest.json', {'revision': 'fixture-revision'})
        (self.embedding / 'model.safetensors').write_bytes(b'explicit test-only weight placeholder')
        self.database(self.agent, 'CREATE TABLE agent_tasks(state TEXT);')
        self.database(self.budget,
                      'CREATE TABLE budget_scopes(name TEXT, budget_cny REAL);', [
                          ('INSERT INTO budget_scopes VALUES (?,?)', ('phase3', 0.5))])
        self.database(self.usage, '''
            CREATE TABLE neural4d_usage_policy(max_attempts INTEGER, historical_used INTEGER,
                                               historical_verified_at TEXT);
            CREATE TABLE neural4d_creation_attempts(state TEXT);
            INSERT INTO neural4d_usage_policy VALUES (3,0,'test-only');
            INSERT INTO neural4d_creation_attempts VALUES ('SUCCEEDED');
            INSERT INTO neural4d_creation_attempts VALUES ('SUCCEEDED');
        ''')
        self.records = [self.model_record('chibi'), self.model_record('realistic')]
        self.database(self.catalog, 'CREATE TABLE asset_models(content_json TEXT);', [
            ('INSERT INTO asset_models VALUES (?)', (json.dumps(record),)) for record in self.records])

    def preflight(self):
        return launcher.check_resources(self.settings, self.workspace)

    def test_occupied_port_refuses_without_closing_existing_listener(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as existing:
            existing.bind(('127.0.0.1', 0))
            existing.listen(1)
            host, port = existing.getsockname()
            with patch.object(launcher, 'HOST', host), patch.object(launcher, 'PORT', port):
                with self.assertRaisesRegex(launcher.LaunchError, '端口已被占用'):
                    launcher.check_port()
            # The existing listener remains reachable; the launcher never kills it.
            with socket.create_connection((host, port), timeout=1):
                accepted, _ = existing.accept()
                accepted.close()

    def test_missing_database_does_not_create_file_or_parent(self):
        missing = self.workspace / 'missing-parent' / 'nested' / 'business.sqlite3'
        with self.assertRaisesRegex(launcher.LaunchError, '不会新建或重建'):
            launcher.read_database(missing, '测试数据库', lambda db: db.execute('SELECT 1'))
        self.assertFalse(missing.exists())
        self.assertFalse(missing.parent.exists())

    def test_corrupt_database_bytes_preserved(self):
        corrupt = self.workspace / 'corrupt.sqlite3'
        original = b'not a sqlite database; preserve these bytes'
        corrupt.write_bytes(original)
        with self.assertRaisesRegex(launcher.LaunchError, '未初始化、覆盖或重建'):
            launcher.read_database(corrupt, '测试数据库', lambda db: db.execute('SELECT 1'))
        self.assertEqual(corrupt.read_bytes(), original)
        self.assertEqual(sorted(path.name for path in self.workspace.iterdir()), ['corrupt.sqlite3'])

    def test_valid_two_style_fixture_checks_readonly_and_returns_counts(self):
        self.fixture()
        before = {path: path.read_bytes() for path in self.workspace.rglob('*') if path.is_file()}
        self.assertEqual(self.preflight(), {'chunks': 1, 'models': 2, 'used': 2})
        self.assertEqual({path: path.read_bytes() for path in self.workspace.rglob('*') if path.is_file()}, before)

    def test_missing_agent_database_not_created(self):
        self.fixture()
        self.agent.unlink()
        with self.assertRaisesRegex(launcher.LaunchError, 'Agent历史数据库'):
            self.preflight()
        self.assertFalse(self.agent.exists())

    def test_unfinished_agent_states_block_without_updating_rows(self):
        for state in ('waiting', 'running'):
            with self.subTest(state=state):
                # Each subcase owns an independent temporary fixture.
                with tempfile.TemporaryDirectory(dir=self.workspace) as nested:
                    path = Path(nested) / 'agent.sqlite3'
                    self.database(path, 'CREATE TABLE agent_tasks(state TEXT);', [
                        ('INSERT INTO agent_tasks VALUES (?)', (state,))])
                    before = path.read_bytes()
                    self.fixture() if not self.agent.exists() else None
                    self.agent.write_bytes(before)
                    with self.assertRaisesRegex(launcher.LaunchError, '尚未结束的Agent任务'):
                        self.preflight()
                    self.assertEqual(self.agent.read_bytes(), before)

    def test_budget_scope_mismatch_blocks_without_adjustment(self):
        self.fixture()
        self.settings.agent_test_budget_cny = 0.4
        before = self.budget.read_bytes()
        with self.assertRaisesRegex(launcher.LaunchError, '预算范围与配置不一致'):
            self.preflight()
        self.assertEqual(self.budget.read_bytes(), before)

    def test_unknown_model_task_blocks_without_recovery_or_refund(self):
        self.fixture()
        with closing(sqlite3.connect(self.usage)) as db, db:
            db.execute("UPDATE neural4d_creation_attempts SET state='UNKNOWN' WHERE rowid=1")
        before = self.usage.read_bytes()
        with self.assertRaisesRegex(launcher.LaunchError, '未完成或状态未知'):
            self.preflight()
        self.assertEqual(self.usage.read_bytes(), before)

    def test_unverified_usage_history_blocks_without_mutation(self):
        self.fixture()
        with closing(sqlite3.connect(self.usage)) as db, db:
            db.execute('UPDATE neural4d_usage_policy SET historical_used=NULL')
        before = self.usage.read_bytes()
        with self.assertRaisesRegex(launcher.LaunchError, '额度历史未核实'):
            self.preflight()
        self.assertEqual(self.usage.read_bytes(), before)

    def test_creation_switches_must_both_be_closed(self):
        self.fixture()
        for name in ('neural4d_generation_enabled', 'neural4d_protocol_verified'):
            with self.subTest(name=name):
                setattr(self.settings, name, True)
                with self.assertRaisesRegex(launcher.LaunchError, '开关未关闭'):
                    self.preflight()
                setattr(self.settings, name, False)

    def test_missing_realistic_style_cannot_be_replaced_by_second_chibi(self):
        first = self.model_record('chibi')
        second = self.model_record('chibi', key='models/chibi/second.glb')
        with self.assertRaisesRegex(launcher.LaunchError, 'Q版或写实真实GLB登记不完整'):
            launcher.check_models(self.asset_root, [(json.dumps(first),), (json.dumps(second),)])

    def test_fixture_model_is_not_counted_as_real_asset(self):
        records = [self.model_record('chibi'), self.model_record('realistic')]
        records[1]['origin'] = 'test_fixture'
        with self.assertRaisesRegex(launcher.LaunchError, 'Q版或写实真实GLB登记不完整'):
            launcher.check_models(self.asset_root, [(json.dumps(record),) for record in records])

    def test_model_path_escape_rejected(self):
        model = self.model_record('chibi', key='../outside.glb')
        with self.assertRaisesRegex(launcher.LaunchError, '路径、GLB头或Hash不匹配'):
            launcher.check_models(self.asset_root, [(json.dumps(model),)])

    def test_model_inside_asset_root_but_outside_models_rejected(self):
        model = self.model_record('chibi', key='other/viewer.glb')
        with self.assertRaisesRegex(launcher.LaunchError, '路径、GLB头或Hash不匹配'):
            launcher.check_models(self.asset_root, [(json.dumps(model),)])

    def test_model_hash_mismatch_rejected(self):
        model = self.model_record('chibi')
        model['hash'] = '0' * 64
        with self.assertRaisesRegex(launcher.LaunchError, 'Hash不匹配'):
            launcher.check_models(self.asset_root, [(json.dumps(model),)])

    def test_model_declared_size_mismatch_rejected(self):
        model = self.model_record('chibi')
        model['size'] += 1
        with self.assertRaisesRegex(launcher.LaunchError, 'GLB头或Hash不匹配'):
            launcher.check_models(self.asset_root, [(json.dumps(model),)])

    def test_waiter_does_not_open_before_readiness_and_opens_once(self):
        server = SimpleNamespace(started=True, should_exit=False)
        stopped, result = Mock(), {}
        stopped.wait.side_effect = [False, False, False]
        opener = Mock(return_value=True)
        with patch.object(launcher, 'health_ready', side_effect=[False, True]) as ready, \
                patch.object(launcher.time, 'monotonic', return_value=0), patch.object(launcher, 'say'):
            launcher.open_when_ready(server, stopped, result, opener=opener)
        self.assertEqual(ready.call_count, 2)
        opener.assert_called_once_with(launcher.WORKSHOP_URL, new=2)
        self.assertTrue(result['ready'])
        self.assertFalse(server.should_exit)

    def test_waiter_never_polls_or_opens_when_server_not_started(self):
        server = SimpleNamespace(started=False, should_exit=False)
        stopped, result = Mock(), {}
        stopped.wait.side_effect = [False, True]
        opener = Mock()
        with patch.object(launcher, 'health_ready') as ready, \
                patch.object(launcher.time, 'monotonic', return_value=0):
            launcher.open_when_ready(server, stopped, result, opener=opener)
        ready.assert_not_called()
        opener.assert_not_called()
        self.assertNotIn('ready', result)

    def test_timeout_requests_server_exit_without_browser(self):
        server = SimpleNamespace(started=False, should_exit=False)
        stopped, result = Mock(), {}
        stopped.wait.return_value = False
        opener = Mock()
        with patch.object(launcher.time, 'monotonic', side_effect=[0, 121]):
            launcher.open_when_ready(server, stopped, result, timeout=120, opener=opener)
        self.assertTrue(server.should_exit)
        self.assertIn('超时', result['error'])
        opener.assert_not_called()

    def test_no_browser_mode_still_reports_ready(self):
        server = SimpleNamespace(started=True, should_exit=False)
        stopped, result = Mock(), {}
        stopped.wait.return_value = False
        opener = Mock()
        with patch.object(launcher, 'health_ready', return_value=True), patch.object(launcher, 'say'):
            launcher.open_when_ready(server, stopped, result, browser=False, opener=opener)
        self.assertTrue(result['ready'])
        opener.assert_not_called()

    def test_browser_failure_does_not_restart_or_repeat_open(self):
        server = SimpleNamespace(started=True, should_exit=False)
        stopped, result = Mock(), {}
        stopped.wait.return_value = False
        opener = Mock(side_effect=OSError('test browser unavailable'))
        with patch.object(launcher, 'health_ready', return_value=True), patch.object(launcher, 'say') as say:
            launcher.open_when_ready(server, stopped, result, opener=opener)
        opener.assert_called_once()
        self.assertTrue(result['ready'])
        self.assertFalse(server.should_exit)
        self.assertTrue(any('浏览器未能自动打开' in str(call) for call in say.call_args_list))


if __name__ == '__main__':
    unittest.main(verbosity=2)
