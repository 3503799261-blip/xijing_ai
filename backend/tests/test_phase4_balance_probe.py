"""Offline probes only; not supplier authentication evidence."""
import asyncio
import httpx
import pytest
from backend.app.config import Settings
from backend.app.assets.usage import UsageManager
from backend.app.errors import ServiceError
from backend.scripts.verify_neural4d_balance import probe


def test_readonly_probe_only_queries_balance_and_records_no_model(tmp_path):
    calls = []
    def handle(request):
        calls.append(request)
        assert request.url.path == '/api/queryPointsInfo'
        return httpx.Response(200, json={'statusType': 0, 'data': {'total_points': 42}})
    settings = Settings(_env_file=None, neural4d_api_key='offline-only-placeholder')
    usage = UsageManager(tmp_path / 'offline.sqlite3')
    value = asyncio.run(probe(settings, usage, httpx.MockTransport(handle)))
    assert value['authenticated'] and not value['modelSubmitted']
    assert len(calls) == 1 and usage.summary()['attemptStates'] == {}
    assert usage.summary()['mockHttpRequests'] == 1 and usage.summary()['realHttpRequests'] == 0


@pytest.mark.parametrize('body', [{'statusType': True, 'data': {'total_points': 42}},
                                 {'statusType': 0, 'data': {'total_points': -1}},
                                 {'statusType': 0, 'data': {'total_points': '42'}}])
def test_probe_rejects_invalid_balance_without_retry(tmp_path, body):
    calls = []
    def handle(request):
        calls.append(request)
        return httpx.Response(200, json=body)
    usage = UsageManager(tmp_path / 'offline.sqlite3')
    with pytest.raises(ServiceError, match='NEURAL4D_BALANCE_UNVERIFIED'):
        asyncio.run(probe(Settings(_env_file=None, neural4d_api_key='offline-only-placeholder'), usage, httpx.MockTransport(handle)))
    assert len(calls) == 1 and usage.summary()['attemptStates'] == {}


def test_probe_requires_real_creation_off_and_key_before_transport(tmp_path):
    def handle(request):
        raise AssertionError('No request allowed')
    usage = UsageManager(tmp_path / 'offline.sqlite3')
    with pytest.raises(ServiceError, match='VERIFY_REQUIRES_CREATION_OFF'):
        asyncio.run(probe(Settings(_env_file=None, neural4d_generation_enabled=True), usage, httpx.MockTransport(handle)))
    with pytest.raises(ServiceError, match='NEURAL4D_KEY_MISSING'):
        asyncio.run(probe(Settings(_env_file=None), usage, httpx.MockTransport(handle)))
    assert usage.summary()['realHttpRequests'] == usage.summary()['mockHttpRequests'] == 0
