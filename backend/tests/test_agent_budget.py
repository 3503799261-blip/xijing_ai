"""Offline budget and shared-provider concurrency checks; no real model calls.

Synthetic usage/HTTP fixtures verify accounting, never cultural answer quality.
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
import sqlite3
from threading import Barrier

import httpx
from pydantic import SecretStr, ValidationError
import pytest

from backend.app.config import Settings
from backend.app.errors import ServiceError
from backend.app.providers.budget import BudgetLedger
from backend.app.providers.llm import DeepSeekProvider


def configuration(tmp_path, **overrides):
    return Settings(_env_file=None, deepseek_api_key=SecretStr('offline-test-only'),
                    rag_data_dir=tmp_path / 'runtime',
                    embedding_model_path=tmp_path / 'unused-model', **overrides)


def response():
    return httpx.Response(200, json={
        'model': 'deepseek-flash',
        'choices': [{'message': {'content': '{"offline":"fixture"}'}, 'finish_reason': 'stop'}],
        'usage': {'prompt_tokens': 100, 'completion_tokens': 40, 'total_tokens': 140},
    })


def test_phase2_rows_survive_migration_and_do_not_consume_incremental_budget(tmp_path):
    path = tmp_path / 'budget.sqlite3'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE calls (request_id TEXT PRIMARY KEY, created_at TEXT, status TEXT, reserved REAL, cost REAL, usage_json TEXT)')
        db.execute('INSERT INTO calls VALUES (?,?,?,?,?,?)', ('phase2-call', '2026-10-10', 'success', 0.02, 0.01, '{}'))
    ledger = BudgetLedger(path, 3, scope='phase3', scope_limit=0.5)
    assert ledger.summary()['estimatedUpperCostCny'] == 0.01
    assert ledger.summary()['activeScope']['calls'] == 0
    ledger.reserve('phase3-task.planner', [], 256)
    ledger.finish('phase3-task.planner', {'prompt_tokens': 100, 'completion_tokens': 40}, 'success')
    records = {r['requestId']: r for r in ledger.records()}
    assert records['phase2-call']['scope'] is None
    assert records['phase2-call']['estimatedUpperCny'] == 0.01
    assert records['phase3-task.planner']['scope'] == 'phase3'
    assert ledger.summary()['activeScope']['estimatedUpperCostCny'] == pytest.approx(0.00052)
    assert ledger.summary()['estimatedUpperCostCny'] == pytest.approx(0.01052)


def test_unknown_reservation_and_scope_limit_persist_across_restarts(tmp_path):
    path = tmp_path / 'budget.sqlite3'
    first = BudgetLedger(path, 3, scope='phase3', scope_limit=0.001)
    first.reserve('unknown-call', [], 1)
    first.finish('unknown-call', None, 'cancelled_unknown')
    before = first.summary()['activeScope']
    restarted = BudgetLedger(path, 3, scope='phase3', scope_limit=0.5)
    assert restarted.summary()['activeScope'] == before
    assert before['budgetCny'] == 0.001
    with pytest.raises(ServiceError) as caught:
        restarted.reserve('would-exceed', [], 1)
    assert caught.value.code == 'PHASE_BUDGET_EXCEEDED'
    assert restarted.summary()['calls'] == 1


def test_total_budget_still_includes_prior_phase2_usage(tmp_path):
    path = tmp_path / 'budget.sqlite3'
    old = BudgetLedger(path, 0.001)
    old.reserve('phase2-unknown', [], 1)
    new = BudgetLedger(path, 0.001, scope='phase3', scope_limit=0.5)
    with pytest.raises(ServiceError) as caught:
        new.reserve('phase3-blocked', [], 1)
    assert caught.value.code == 'TEST_BUDGET_EXCEEDED'
    assert new.summary()['activeScope']['calls'] == 0
    assert new.summary()['calls'] == 1


def test_concurrent_reservations_cannot_overspend_scope(tmp_path):
    path = tmp_path / 'budget.sqlite3'
    a = BudgetLedger(path, 3, scope='phase3', scope_limit=0.0008)
    b = BudgetLedger(path, 3, scope='phase3', scope_limit=0.0008)
    barrier = Barrier(2)

    def reserve(ledger, request_id):
        barrier.wait()
        try:
            ledger.reserve(request_id, [], 1)
            return 'reserved'
        except ServiceError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda args: reserve(*args), [(a, 'parallel-a'), (b, 'parallel-b')]))
    assert sorted(results) == ['PHASE_BUDGET_EXCEEDED', 'reserved']
    assert a.summary()['activeScope']['calls'] == 1


def test_invalid_boolean_usage_does_not_release_unknown_reservation(tmp_path):
    ledger = BudgetLedger(tmp_path / 'budget.sqlite3', 3, scope='phase3', scope_limit=0.5)
    ledger.reserve('bad-usage', [], 1)
    ledger.finish('bad-usage', {'prompt_tokens': True, 'completion_tokens': 4}, 'success')
    assert ledger.records()[0]['estimatedUpperCny'] is None
    assert ledger.summary()['activeScope']['estimatedUpperCostCny'] > 0


def test_model_scope_is_enforced_before_any_outbound_request(tmp_path):
    called = []
    provider = DeepSeekProvider(configuration(tmp_path, agent_test_budget_cny=0.000001),
                                transport=httpx.MockTransport(lambda request: called.append(request)))
    with pytest.raises(ServiceError) as caught:
        asyncio.run(provider.generate([], 'over-budget'))
    assert caught.value.code == 'PHASE_BUDGET_EXCEEDED'
    assert called == []
    assert provider.ledger.summary()['calls'] == 0


def test_chat_and_agent_calls_share_two_slots_and_waiting_cancellation_is_free(tmp_path):
    async def scenario():
        started, release = asyncio.Event(), asyncio.Event()
        current, peak, calls = 0, 0, 0

        async def handler(request):
            nonlocal current, peak, calls
            current += 1
            calls += 1
            peak = max(peak, current)
            if calls == 2:
                started.set()
            try:
                await release.wait()
                return response()
            finally:
                current -= 1

        provider = DeepSeekProvider(configuration(tmp_path), transport=httpx.MockTransport(handler))
        first = asyncio.create_task(provider.generate([], 'chat-request'))
        second = asyncio.create_task(provider.generate([], 'agent-request.planner'))
        await asyncio.wait_for(started.wait(), timeout=1)
        waiting = asyncio.create_task(provider.generate([], 'agent-request.designer'))
        await asyncio.sleep(0.02)
        waiting.cancel()
        with pytest.raises(asyncio.CancelledError):
            await waiting
        assert provider.ledger.summary()['calls'] == 2
        release.set()
        await asyncio.gather(first, second)
        await provider.generate([], 'agent-request.reviewer')
        assert peak == 2 and calls == 3
        assert provider.ledger.summary()['activeScope']['calls'] == 3

    asyncio.run(scenario())


def test_busy_model_returns_bounded_error_without_reserving(tmp_path):
    async def scenario():
        provider = DeepSeekProvider(configuration(tmp_path))
        provider.capacity_wait_seconds = 0.01
        await provider.capacity.acquire()
        await provider.capacity.acquire()
        try:
            with pytest.raises(ServiceError) as caught:
                await provider.generate([], 'not-admitted')
            assert caught.value.code == 'LLM_BUSY'
            assert caught.value.retryable is True
            assert provider.ledger.summary()['calls'] == 0
        finally:
            provider.capacity.release()
            provider.capacity.release()

    asyncio.run(scenario())


def test_inflight_cancellation_retains_unknown_reservation_and_releases_slot(tmp_path):
    async def scenario():
        started = asyncio.Event()

        async def handler(request):
            started.set()
            await asyncio.Event().wait()

        provider = DeepSeekProvider(configuration(tmp_path), transport=httpx.MockTransport(handler))
        task = asyncio.create_task(provider.generate([], 'cancelled-inflight'))
        await asyncio.wait_for(started.wait(), timeout=1)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        record = provider.ledger.records()[0]
        assert record['status'] == 'cancelled_unknown'
        assert record['estimatedUpperCny'] is None
        assert provider.ledger.summary()['activeScope']['estimatedUpperCostCny'] > 0
        assert provider.verified is False
        # Both slots are available again, despite the conservative reservation.
        await asyncio.wait_for(provider.capacity.acquire(), timeout=0.1)
        await asyncio.wait_for(provider.capacity.acquire(), timeout=0.1)
        provider.capacity.release()
        provider.capacity.release()

    asyncio.run(scenario())


@pytest.mark.parametrize('overrides', [
    {'agent_test_budget_cny': 0.6}, {'agent_test_budget_cny': 0},
    {'agent_queue_limit': -1}, {'agent_queue_limit': 6},
    {'agent_workflow_timeout_seconds': 59}, {'agent_workflow_timeout_seconds': 181},
])
def test_agent_settings_reject_unapproved_budget_and_capacity_bounds(tmp_path, overrides):
    with pytest.raises(ValidationError):
        configuration(tmp_path, **overrides)
