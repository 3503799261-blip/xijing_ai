"""OFFLINE quota/crash/concurrency tests. No provider transport or model calls.

Synthetic credits and frozen hashes are test fixtures, never billing evidence.
"""
from concurrent.futures import ThreadPoolExecutor
import json
import sqlite3
import subprocess
import sys
from threading import Barrier

import pytest

from backend.app.assets.usage import UsageManager
from backend.app.errors import ServiceError


def payload(number=0):
    return {'modelCount': 1, 'imageHash': f'offline-image-{number}',
            'sourceResultHash': f'offline-character-{number}',
            'promptHash': f'offline-prompt-{number}',
            'parameters': {'mesh_quality': 'standard', 'faceNum': 100000}}


def manager(tmp_path, used=0):
    value = UsageManager(tmp_path / 'neural4d.sqlite3')
    value.initialize_history(used, '仅离线测试：人工核查模拟历史，不是真实账户用量。')
    return value


def approved(value, data=None, purpose='technical'):
    return value.approve(data or payload(), purpose, confirmed=True, estimated_credits=80)


def reserved(value, key='test-key', data=None, purpose='technical'):
    data = data or payload()
    approval = approved(value, data, purpose)
    return value.reserve(key, approval['approvalId'], data, purpose,
                         real_enabled=True, provider_verified=True)


def test_new_and_missing_ledger_have_unknown_history_not_free_quota(tmp_path):
    first = UsageManager(tmp_path / 'unknown.sqlite3')
    summary = first.summary()
    assert summary['historicalUsageVerified'] is False
    assert summary['used_attempts'] is None and summary['remaining_attempts'] is None
    approval = approved(first)
    with pytest.raises(ServiceError, match='NEURAL4D_HISTORY_UNVERIFIED'):
        first.reserve('unknown', approval['approvalId'], payload(), 'technical', True, True)
    assert first.summary()['attemptStates'] == {}


@pytest.mark.parametrize('used', [0, 1, 2, 3])
def test_fixed_three_cap_includes_verified_historical_attempts(tmp_path, used):
    value = manager(tmp_path, used)
    for number in range(3 - used):
        attempt = reserved(value, f'key-{number}', payload(number))
        assert attempt['state'] == 'RESERVED' and attempt['newlyReserved']
    final = value.summary()
    assert final['occupied_attempts'] == 3 and final['remaining_attempts'] == 0
    assert final['used_attempts'] + final['reserved_attempts'] == 3
    with pytest.raises(ServiceError, match='NEURAL4D_QUOTA_EXHAUSTED'):
        reserved(value, 'fourth', payload(4))
    assert value.summary() == final
    assert UsageManager(value.path).summary() == final


@pytest.mark.parametrize('count', [0, 2, 3, True, 1.0, None, '1'])
def test_model_count_must_be_explicit_integer_one(tmp_path, count):
    value = manager(tmp_path)
    with pytest.raises(ServiceError, match='NEURAL4D_MODEL_COUNT_INVALID'):
        approved(value, {**payload(), 'modelCount': count})
    assert value.summary()['occupied_attempts'] == 0


def test_approval_needs_explicit_confirmation_and_verified_credits(tmp_path):
    value = manager(tmp_path)
    with pytest.raises(ServiceError, match='NEURAL4D_CONFIRMATION_REQUIRED'):
        value.approve(payload(), 'technical', estimated_credits=80)
    for cost in (None, 0, -1, float('nan'), float('inf'), True, '80'):
        with pytest.raises(ServiceError, match='NEURAL4D_COST_UNVERIFIED'):
            value.approve(payload(), 'technical', confirmed=True, estimated_credits=cost)
    assert value.summary()['occupied_attempts'] == 0


def test_real_creation_defaults_closed_even_with_approved_payload(tmp_path):
    value = manager(tmp_path)
    approval = approved(value)
    with pytest.raises(ServiceError, match='NEURAL4D_GENERATION_DISABLED'):
        value.reserve('closed', approval['approvalId'], payload(), 'technical')
    with pytest.raises(ServiceError, match='NEURAL4D_PROVIDER_UNVERIFIED'):
        value.reserve('unverified', approval['approvalId'], payload(), 'technical', real_enabled=True)
    assert value.summary()['occupied_attempts'] == 0


def test_frozen_approval_rejects_changed_picture_character_prompt_params_or_purpose(tmp_path):
    value = manager(tmp_path)
    original = payload()
    approval = approved(value, original)
    for field in ('imageHash', 'sourceResultHash', 'promptHash'):
        with pytest.raises(ServiceError, match='NEURAL4D_APPROVAL_INVALID'):
            value.reserve(f'changed-{field}', approval['approvalId'], {**original, field: 'changed'}, 'technical', True, True)
    with pytest.raises(ServiceError, match='NEURAL4D_APPROVAL_INVALID'):
        value.reserve('changed-params', approval['approvalId'], {**original, 'parameters': {'faceNum': 200000}}, 'technical', True, True)
    with pytest.raises(ServiceError, match='NEURAL4D_APPROVAL_INVALID'):
        value.reserve('changed-purpose', approval['approvalId'], original, 'enterprise', True, True)
    assert value.summary()['occupied_attempts'] == 0


def test_expired_approval_never_reserves(tmp_path, monkeypatch):
    value = manager(tmp_path)
    approval = approved(value)
    monkeypatch.setattr('backend.app.assets.usage.time.time', lambda: approval['expiresAt'] + 1)
    with pytest.raises(ServiceError, match='NEURAL4D_APPROVAL_EXPIRED'):
        value.reserve('expired', approval['approvalId'], payload(), 'technical', True, True)
    assert value.summary()['occupied_attempts'] == 0


def test_same_key_replay_returns_existing_without_send_right(tmp_path):
    value = manager(tmp_path)
    approval = approved(value)
    first = value.reserve('repeat', approval['approvalId'], payload(), 'technical', True, True)
    second = value.reserve('repeat', approval['approvalId'], payload(), 'technical', True, True)
    assert first['attemptId'] == second['attemptId']
    assert first['newlyReserved'] is True and second['newlyReserved'] is False
    with pytest.raises(ServiceError, match='NEURAL4D_IDEMPOTENCY_CONFLICT'):
        value.reserve('repeat', approval['approvalId'], payload(2), 'technical', True, True)
    another_approval = approved(value)
    with pytest.raises(ServiceError, match='NEURAL4D_IDEMPOTENCY_CONFLICT'):
        value.reserve('repeat', another_approval['approvalId'], payload(), 'technical', True, True)
    assert value.summary()['occupied_attempts'] == 1


def test_switching_key_does_not_bypass_one_use_approval_or_duplicate_input(tmp_path):
    value = manager(tmp_path)
    approval = approved(value)
    value.reserve('original', approval['approvalId'], payload(), 'technical', True, True)
    with pytest.raises(ServiceError, match='NEURAL4D_APPROVAL_CONSUMED'):
        value.reserve('new-key', approval['approvalId'], payload(), 'technical', True, True)
    new_approval = approved(value)
    with pytest.raises(ServiceError, match='NEURAL4D_DUPLICATE_INPUT'):
        value.reserve('new-key-2', new_approval['approvalId'], payload(), 'technical', True, True)
    assert value.summary()['occupied_attempts'] == 1


@pytest.mark.parametrize('state', ['FAILED', 'UNKNOWN', 'PENDING_RECONCILIATION'])
def test_http_errors_timeouts_and_unknowns_never_refund(tmp_path, state):
    value = manager(tmp_path)
    attempt = reserved(value)
    value.mark_started(attempt['attemptId'])
    value.finish(attempt['attemptId'], state, error_code='OFFLINE_TIMEOUT_OR_FAILURE', http_status=503)
    summary = UsageManager(value.path).summary()
    assert summary['used_attempts'] == 1 and summary['remaining_attempts'] == 2
    assert summary['reserved_attempts'] == 0
    with pytest.raises(ServiceError, match='NEURAL4D_ATTEMPT_ALREADY_STARTED'):
        value.mark_started(attempt['attemptId'])
    if state != 'FAILED':
        with pytest.raises(ServiceError, match='NEURAL4D_DUPLICATE_INPUT'):
            reserved(value, 'new-confirmed-key')


def test_definite_failed_task_can_only_retry_with_new_approval_and_new_quota(tmp_path):
    value = manager(tmp_path)
    original = reserved(value)
    value.mark_started(original['attemptId'])
    value.finish(original['attemptId'], 'FAILED', error_code='OFFLINE_REJECTED', http_status=400)
    approval = approved(value)
    retry = value.reserve('explicitly-confirmed-recreation', approval['approvalId'], payload(), 'technical', True, True)
    assert retry['attemptId'] != original['attemptId']
    assert value.summary()['occupied_attempts'] == 2
    assert value.get_attempt(original['attemptId'])['state'] == 'FAILED'


@pytest.mark.parametrize('crash_phase', ['RESERVED', 'ATTEMPT_STARTED', 'UNKNOWN'])
def test_restart_or_success_before_failed_local_save_requires_reconciliation(tmp_path, crash_phase):
    value = manager(tmp_path)
    attempt = reserved(value)
    if crash_phase != 'RESERVED':
        value.mark_started(attempt['attemptId'])
    if crash_phase == 'UNKNOWN':
        value.finish(attempt['attemptId'], 'UNKNOWN', error_code='OFFLINE_SOCKET_TIMEOUT')
    # In ATTEMPT_STARTED case, a provider might already have returned a UUID but
    # a process crash prevented finish(); local storage must never presume no send.
    reopened = UsageManager(value.path)
    assert reopened.get_attempt(attempt['attemptId'])['state'] == crash_phase
    recovered = reopened.recover()
    assert recovered['recoveredAttempts'] == 1
    assert reopened.get_attempt(attempt['attemptId'])['state'] == 'PENDING_RECONCILIATION'
    assert reopened.summary()['occupied_attempts'] == 1
    assert reopened.recover()['recoveredAttempts'] == 0
    with pytest.raises(ServiceError, match='NEURAL4D_ATTEMPT_ALREADY_STARTED'):
        reopened.mark_started(attempt['attemptId'])
    with pytest.raises(ServiceError, match='NEURAL4D_DUPLICATE_INPUT'):
        reserved(reopened, 'unsafe-recreation')


def test_known_submitted_uuid_survives_recovery_and_repeated_query_completion(tmp_path):
    value = manager(tmp_path)
    attempt = reserved(value)
    value.mark_started(attempt['attemptId'])
    value.finish(attempt['attemptId'], 'SUBMITTED', provider_task_id='offline-task-uuid', http_status=200)
    reopened = UsageManager(value.path)
    assert reopened.recover()['recoveredAttempts'] == 0
    assert reopened.get_attempt(attempt['attemptId'])['providerTaskId'] == 'offline-task-uuid'
    reopened.finish(attempt['attemptId'], 'PROCESSING')
    reopened.finish(attempt['attemptId'], 'SUCCEEDED')
    reopened.finish(attempt['attemptId'], 'SUCCEEDED')
    assert reopened.summary()['occupied_attempts'] == 1
    with pytest.raises(ServiceError, match='NEURAL4D_DUPLICATE_INPUT'):
        reserved(reopened, 'duplicate-success')
    with pytest.raises(ServiceError, match='NEURAL4D_STATE_INVALID'):
        reopened.finish(attempt['attemptId'], 'FAILED')
    with pytest.raises(ServiceError, match='NEURAL4D_TASK_ID_CONFLICT'):
        reopened.finish(attempt['attemptId'], 'SUCCEEDED', provider_task_id='different-model')


def test_mark_started_is_atomic_even_when_two_workers_race(tmp_path):
    value = manager(tmp_path)
    attempt = reserved(value)
    barrier = Barrier(2)
    def claim():
        contender = UsageManager(value.path)
        barrier.wait()
        try:
            contender.mark_started(attempt['attemptId'])
            return 'sole-send-right'
        except ServiceError as error:
            return error.code
    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(lambda _: claim(), range(2)))
    assert results.count('sole-send-right') == 1
    assert results.count('NEURAL4D_ATTEMPT_ALREADY_STARTED') == 1
    assert value.summary()['occupied_attempts'] == 1


def test_four_concurrent_distinct_requests_cannot_reserve_four_slots(tmp_path):
    value = manager(tmp_path)
    approvals = [approved(value, payload(i)) for i in range(4)]
    barrier = Barrier(4)
    def reserve_number(number):
        contender = UsageManager(value.path)
        barrier.wait()
        try:
            return contender.reserve(f'concurrent-{number}', approvals[number]['approvalId'], payload(number), 'technical', True, True)['attemptId']
        except ServiceError as error:
            return error.code
    with ThreadPoolExecutor(max_workers=4) as workers:
        outcomes = list(workers.map(reserve_number, range(4)))
    assert outcomes.count('NEURAL4D_QUOTA_EXHAUSTED') == 1
    assert value.summary()['occupied_attempts'] == 3


def test_concurrent_same_key_reserves_once(tmp_path):
    value = manager(tmp_path)
    approval = approved(value)
    barrier = Barrier(2)
    def repeated():
        contender = UsageManager(value.path)
        barrier.wait()
        return contender.reserve('same-click', approval['approvalId'], payload(), 'technical', True, True)
    with ThreadPoolExecutor(max_workers=2) as workers:
        outcomes = list(workers.map(lambda _: repeated(), range(2)))
    assert len({r['attemptId'] for r in outcomes}) == 1
    assert sorted(r['newlyReserved'] for r in outcomes) == [False, True]


def test_separate_processes_compete_for_last_slot(tmp_path):
    value = manager(tmp_path, used=2)
    approvals = [approved(value, payload(i)) for i in range(2)]
    code = '''
import json, sys
from pathlib import Path
from backend.app.assets.usage import UsageManager
from backend.app.errors import ServiceError
data=json.loads(sys.argv[2])
try:
    value=UsageManager(Path(sys.argv[1]))
    result=value.reserve(data['key'],data['approvalId'],data['payload'],'technical',True,True)
    print(json.dumps({'state':result['state']}))
except ServiceError as error:
    print(json.dumps({'code':error.code}))
'''
    processes = [subprocess.Popen([sys.executable, '-c', code, str(value.path),
                                  json.dumps({'key': f'process-{i}', 'approvalId': approvals[i]['approvalId'], 'payload': payload(i)})],
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                 for i in range(2)]
    outcomes = []
    for process in processes:
        output, error = process.communicate(timeout=20)
        assert process.returncode == 0, error
        outcomes.append(json.loads(output))
    assert sum(r.get('state') == 'RESERVED' for r in outcomes) == 1
    assert sum(r.get('code') == 'NEURAL4D_QUOTA_EXHAUSTED' for r in outcomes) == 1
    assert value.summary()['occupied_attempts'] == 3


def test_history_cannot_reset_and_database_constraints_prevent_erasure(tmp_path):
    value = manager(tmp_path, used=1)
    attempt = reserved(value)
    before = value.summary()
    with pytest.raises(ServiceError, match='NEURAL4D_HISTORY_ALREADY_VERIFIED'):
        value.initialize_history(0, '禁止通过重新初始化退次')
    for query in ('DELETE FROM neural4d_creation_attempts',
                  'UPDATE neural4d_usage_policy SET historical_used=0',
                  'UPDATE neural4d_usage_policy SET max_attempts=4',
                  'DELETE FROM neural4d_usage_policy',
                  'DELETE FROM neural4d_attempt_events'):
        with sqlite3.connect(value.path) as db:
            with pytest.raises(sqlite3.IntegrityError):
                db.execute(query)
    assert value.summary() == before
    assert value.get_attempt(attempt['attemptId'])['state'] == 'RESERVED'


def test_corrupt_ledger_fails_closed_without_private_path_leak(tmp_path):
    path = tmp_path / 'secret-private-directory' / 'broken.sqlite3'
    path.parent.mkdir()
    path.write_bytes(b'not a database')
    with pytest.raises(ServiceError) as caught:
        UsageManager(path)
    assert caught.value.code == 'NEURAL4D_LEDGER_UNAVAILABLE'
    assert str(path) not in caught.value.message


def test_creation_halt_is_persistent_and_cannot_be_automatically_reset(tmp_path):
    value = manager(tmp_path)
    attempt = reserved(value)
    value.halt('OFFLINE_MULTIPLE_MODELS_RESPONSE')
    reopened = UsageManager(value.path)
    assert reopened.summary()['creationHalted'] is True
    with pytest.raises(ServiceError, match='NEURAL4D_CREATION_HALTED'):
        reopened.mark_started(attempt['attemptId'])
    with pytest.raises(ServiceError, match='NEURAL4D_CREATION_HALTED'):
        reserved(reopened, 'another', payload(2))
    with sqlite3.connect(value.path) as db:
        with pytest.raises(sqlite3.IntegrityError):
            db.execute('UPDATE neural4d_usage_policy SET creation_halted=0')
    assert reopened.summary()['occupied_attempts'] == 1


def test_operational_http_log_is_separate_from_creation_quota_and_mock_counts(tmp_path):
    value = manager(tmp_path)
    for operation in ('verify', 'preprocess', 'preprocess_status', 'query_model', 'download', 'convert_format'):
        value.record_request(operation, is_mock=True, http_status=200, duration_ms=5)
    assert value.summary()['mockHttpRequests'] == 6
    assert value.summary()['realHttpRequests'] == 0
    assert value.summary()['occupied_attempts'] == 0
    with pytest.raises(ServiceError, match='NEURAL4D_UNRESERVED_REQUEST'):
        value.record_request('create_model')
    attempt = reserved(value)
    with pytest.raises(ServiceError, match='NEURAL4D_UNRESERVED_REQUEST'):
        value.record_request('create_model', attempt_id=attempt['attemptId'])
    value.mark_started(attempt['attemptId'])
    # Synthetic metadata only: this unit test has no network transport.
    value.record_request('create_model', attempt_id=attempt['attemptId'], http_status=503, duration_ms=2, actual_credits=0)
    with pytest.raises(ServiceError, match='NEURAL4D_DUPLICATE_REQUEST'):
        value.record_request('create_model', attempt_id=attempt['attemptId'])
    assert value.summary()['occupied_attempts'] == 1
    assert value.summary()['realHttpRequests'] == 1


def test_missing_provider_id_never_becomes_success(tmp_path):
    value = manager(tmp_path)
    attempt = reserved(value)
    value.mark_started(attempt['attemptId'])
    with pytest.raises(ServiceError, match='NEURAL4D_TASK_ID_MISSING'):
        value.finish(attempt['attemptId'], 'SUBMITTED', http_status=200)
    assert value.get_attempt(attempt['attemptId'])['state'] == 'ATTEMPT_STARTED'
    assert value.summary()['occupied_attempts'] == 1


def test_approval_send_claim_and_request_audit_cannot_be_reset_in_database(tmp_path):
    value = manager(tmp_path)
    attempt = reserved(value)
    value.mark_started(attempt['attemptId'])
    value.record_request('create_model', attempt_id=attempt['attemptId'], http_status=200)
    value.finish(attempt['attemptId'], 'SUBMITTED', provider_task_id='offline-uuid')
    mutations = (
        'UPDATE neural4d_model_approvals SET consumed_attempt_id=NULL',
        "UPDATE neural4d_model_approvals SET payload_hash='unconfirmed-change'",
        'DELETE FROM neural4d_model_approvals',
        'UPDATE neural4d_creation_attempts SET started_at=NULL',
        "UPDATE neural4d_creation_attempts SET state='RESERVED'",
        "UPDATE neural4d_creation_attempts SET provider_task_id='another-model'",
        'DELETE FROM neural4d_operational_requests',
        'UPDATE neural4d_operational_requests SET is_mock=1',
    )
    for query in mutations:
        with sqlite3.connect(value.path) as db:
            with pytest.raises(sqlite3.IntegrityError):
                db.execute(query)
    assert value.get_attempt(attempt['attemptId'])['state'] == 'SUBMITTED'
    assert value.summary()['occupied_attempts'] == 1


def test_same_frozen_json_different_key_order_is_same_payload(tmp_path):
    value = manager(tmp_path)
    data = payload()
    approval = approved(value, data)
    first = value.reserve('canonical', approval['approvalId'], data, 'technical', True, True)
    second = value.reserve('canonical', approval['approvalId'], dict(reversed(list(data.items()))), 'technical', True, True)
    assert first['attemptId'] == second['attemptId'] and not second['newlyReserved']


def test_trusted_frozen_payload_is_hash_checked_copy_and_not_public_response(tmp_path):
    value = manager(tmp_path)
    original = payload()
    attempt = reserved(value, data=original)
    copy = value.frozen_payload(attempt['attemptId'])
    assert copy == original
    copy['parameters']['faceNum'] = 200000
    assert value.frozen_payload(attempt['attemptId']) == original
    public = value.get_attempt(attempt['attemptId'])
    assert 'payload' not in public and 'payload_json' not in public
    canonical = json.dumps(original, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    import hashlib
    assert public['payloadHash'] == hashlib.sha256(canonical.encode('utf-8')).hexdigest()
