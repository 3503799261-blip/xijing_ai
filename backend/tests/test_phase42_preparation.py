"""OFFLINE preparation safety: no real credentials, data, network or review."""
import ast
import asyncio
import copy
import inspect
import json
from types import SimpleNamespace
import pytest
from backend.app.errors import ServiceError
from backend.scripts import prepare_realistic_showcase as prep
from backend.tests.test_agent_roles import BRIEF, PLAN, EVIDENCE, DESIGN
from backend.app.agents.designer import validate_design


def data():
    evidence = [copy.deepcopy(EVIDENCE)]
    return {'image': {'sourceHash': 'a' * 64}, 'brief': copy.deepcopy(BRIEF),
            'plan': copy.deepcopy(PLAN), 'research': {'evidence': evidence, 'limitations': []},
            'design': validate_design(json.dumps(DESIGN), evidence)}


class OfflineProvider:
    """Explicit isolated test double; never reported as a real culture review."""
    calls = []
    error = False
    verified = True
    budget = 0.5
    def __init__(self, settings):
        self.ledger = SimpleNamespace(summary=lambda: {'calls': len(self.calls),
            'estimatedUpperCostCny': 0, 'budgetCny': self.budget,
            'activeScope': {'estimatedUpperCostCny': 0, 'budgetCny': self.budget}})
    async def generate(self, messages, request_id, max_output=None):
        self.calls.append({'requestId': request_id, 'maxOutput': max_output})
        if self.error:
            raise ServiceError('LLM_TIMEOUT', 'Offline timeout fixture.', 504)
        return {'content': json.dumps({'verdict': 'pass', 'issues': [], 'suggestions': [],
                    'checkedEvidenceIds': ['E1'], 'needsHumanReview': True}),
                'model': 'OFFLINE_TEST_DOUBLE', 'usage': {'total_tokens': 0}, 'elapsedSeconds': 0}


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    OfflineProvider.calls = []
    OfflineProvider.error = False
    OfflineProvider.verified = True
    OfflineProvider.budget = 0.5
    monkeypatch.setattr(prep, 'WORKSPACE_ROOT', tmp_path)
    monkeypatch.setattr(prep, 'DeepSeekProvider', OfflineProvider)
    return tmp_path


def test_no_paid_optin_means_no_provider_or_once_marker(isolated):
    receipt, review = asyncio.run(prep.review_once(data(), None, False))
    assert receipt['status'] == 'NOT_CALLED' and receipt['maxOutputTokens'] == 400
    assert review is None and OfflineProvider.calls == []
    assert not (isolated / '.runtime').exists()


def test_one_review_enforces_400_and_refuses_replay(isolated):
    receipt, review = asyncio.run(prep.review_once(data(), None, True))
    assert receipt['status'] == 'RETURNED_VALIDATED' and review['needsHumanReview'] is True
    assert OfflineProvider.calls[0]['maxOutput'] == 400
    with pytest.raises(ServiceError, match='REVIEW_ALREADY_CLAIMED'):
        asyncio.run(prep.review_once(data(), None, True))
    assert len(OfflineProvider.calls) == 1


def test_timeout_retains_claim_and_does_not_retry(isolated):
    OfflineProvider.error = True
    receipt, review = asyncio.run(prep.review_once(data(), None, True))
    assert receipt['status'] == 'STOPPED_NO_RETRY' and review is None
    with pytest.raises(ServiceError, match='REVIEW_ALREADY_CLAIMED'):
        asyncio.run(prep.review_once(data(), None, True))
    assert len(OfflineProvider.calls) == 1


@pytest.mark.parametrize('condition,code', [('unverified', 'REVIEW_PROVIDER_UNVERIFIED'), ('budget', 'REVIEW_BUDGET_BLOCKED')])
def test_gates_stop_before_claim_and_request(isolated, condition, code):
    if condition == 'unverified': OfflineProvider.verified = False
    else: OfflineProvider.budget = 0.0000001
    with pytest.raises(ServiceError, match=code):
        asyncio.run(prep.review_once(data(), None, True))
    assert OfflineProvider.calls == []
    assert list(isolated.rglob('reviewer-once-*')) == []


def test_preparation_has_no_model_submit_or_reservation_call():
    tree = ast.parse(inspect.getsource(prep))
    calls = {node.func.attr for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)}
    assert not calls.intersection({'create_once', 'submit', 'approve', 'approve_technical_candidate', 'reserve', 'refresh', 'read_operation'})
    assert 'Neural4DProvider' not in inspect.getsource(prep)
