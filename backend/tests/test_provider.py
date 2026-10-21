"""OFFLINE fault injection: MockTransport and test-only credentials, no API cost.

These fixtures are not model responses, cultural evidence, or acceptance data.
"""
import asyncio
import json
from pathlib import Path

import httpx
import pytest
from pydantic import SecretStr, ValidationError

from backend.app.config import Settings
from backend.app.errors import ServiceError
from backend.app.providers.budget import BudgetLedger
from backend.app.providers.llm import DeepSeekProvider
from backend.app.services.chat import grounded_answer, validated_answer
from backend.tests.conftest import initialized_settings


def settings_for_test(tmp_path: Path, **overrides):
    values = dict(
        _env_file=None,
        deepseek_api_key=SecretStr("test-only"),
        rag_data_dir=tmp_path / "runtime",
        embedding_model_path=tmp_path / "fake-model",
    )
    values.update(overrides)
    return initialized_settings(Settings(**values))


def envelope(content="unit test text", usage=None, **choice_updates):
    return {
        "model": "deepseek-flash",
        "choices": [{"message": {"content": content}, "finish_reason": "stop", **choice_updates}],
        "usage": usage if usage is not None else {"prompt_tokens": 100, "completion_tokens": 40, "total_tokens": 140},
    }


def evidence():
    return [{"id": "unit_chunk", "title": "单元测试资料", "sourceId": "unit_source", "locator": "单元测试定位", "url": "https://example.invalid/unit-only", "excerpt": "单元测试合成文本，不代表文化知识。", "contentKind": "original_fact_summary"}]


@pytest.mark.parametrize("status,code,retryable", [(400, "LLM_PARAMETERS", False), (401, "LLM_AUTH_FAILED", False), (402, "LLM_BALANCE", False), (404, "LLM_MODEL", False), (429, "LLM_RATE_LIMIT", True), (500, "LLM_UPSTREAM", True), (502, "LLM_UPSTREAM", True), (503, "LLM_UPSTREAM", True)])
def test_http_failures_are_sanitized_and_never_automatically_retried(tmp_path, status, code, retryable):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(status, json={"error": {"message": "unit-only-private-upstream-details"}})

    provider = DeepSeekProvider(settings_for_test(tmp_path), transport=httpx.MockTransport(handler))
    with pytest.raises(ServiceError) as caught:
        asyncio.run(provider.generate([{"role": "user", "content": "单元测试"}], "unit-http"))
    error = caught.value
    assert error.code == code
    assert error.status == (429 if status == 429 else 502)
    assert error.retryable is retryable
    assert "unit-only-private" not in json.dumps(error.public("unit-request"))
    assert len(calls) == 1
    assert provider.ledger.summary()["calls"] == 1
    if status in (400, 401, 402, 404, 429):
        assert provider.ledger.records()[0]["estimatedUpperCny"] == 0


@pytest.mark.parametrize("exception,code", [(httpx.ReadTimeout("offline timeout"), "LLM_TIMEOUT"), (httpx.ConnectError("offline connection failure"), "LLM_NETWORK")])
def test_transport_failure_keeps_conservative_reservation(tmp_path, exception, code):
    calls = []

    def handler(request):
        calls.append(request)
        raise exception

    provider = DeepSeekProvider(settings_for_test(tmp_path), transport=httpx.MockTransport(handler))
    with pytest.raises(ServiceError) as caught:
        asyncio.run(provider.generate([], "unit-transport"))
    assert caught.value.code == code
    assert len(calls) == 1
    assert provider.ledger.records()[0]["estimatedUpperCny"] is None
    assert provider.ledger.summary()["estimatedUpperCostCny"] > 0


@pytest.mark.parametrize("body", [[], 123, "invalid envelope", {}, {"choices": []}, envelope(""), envelope("  "), envelope("truncated", finish_reason="length"), envelope(usage=["invalid usage"]), envelope(usage=123)])
def test_malformed_response_returns_controlled_error(tmp_path, body):
    provider = DeepSeekProvider(settings_for_test(tmp_path), transport=httpx.MockTransport(lambda request: httpx.Response(200, json=body)))
    with pytest.raises(ServiceError) as caught:
        asyncio.run(provider.generate([], "unit-malformed"))
    assert caught.value.status == 502
    assert caught.value.code == "LLM_INVALID_RESPONSE"


def test_invalid_http_json_returns_controlled_error(tmp_path):
    provider = DeepSeekProvider(settings_for_test(tmp_path), transport=httpx.MockTransport(lambda request: httpx.Response(200, content=b"{not-json")))
    with pytest.raises(ServiceError) as caught:
        asyncio.run(provider.generate([], "unit-json"))
    assert caught.value.code == "LLM_INVALID_RESPONSE"


@pytest.mark.parametrize("usage", [
    {}, {"prompt_tokens": "100", "completion_tokens": 40, "total_tokens": 140},
    {"prompt_tokens": 100, "completion_tokens": -1, "total_tokens": 99},
    {"prompt_tokens": True, "completion_tokens": 40, "total_tokens": 41},
])
def test_invalid_usage_values_keep_reservation_and_return_controlled_error(tmp_path, usage):
    provider = DeepSeekProvider(settings_for_test(tmp_path), transport=httpx.MockTransport(lambda request: httpx.Response(200, json=envelope(usage=usage))))
    with pytest.raises(ServiceError) as caught:
        asyncio.run(provider.generate([], "unit-invalid-usage"))
    assert caught.value.code == "LLM_INVALID_RESPONSE"
    assert provider.ledger.summary()["estimatedUpperCostCny"] > 0
    assert provider.ledger.records()[0]["estimatedUpperCny"] is None


@pytest.mark.parametrize("model", ["deepseek-v4-pro", "deepseek-chat", "", "deepseek-flash "])
def test_configuration_rejects_models_outside_approved_budget(tmp_path, model):
    with pytest.raises(ValidationError):
        settings_for_test(tmp_path, deepseek_model=model)


@pytest.mark.parametrize("model", ["deepseek-v4-pro", "unapproved", None, 123])
def test_returned_model_mismatch_is_not_verified_as_success(tmp_path, model):
    body = envelope()
    body["model"] = model
    provider = DeepSeekProvider(settings_for_test(tmp_path), transport=httpx.MockTransport(lambda request: httpx.Response(200, json=body)))
    with pytest.raises(ServiceError) as caught:
        asyncio.run(provider.generate([], "unit-model-mismatch"))
    assert caught.value.code == "LLM_MODEL_MISMATCH"
    assert provider.verified is False
    assert provider.ledger.records()[0]["status"] == "invalid_model"


def test_missing_key_does_not_reserve_or_call(tmp_path):
    calls = []
    provider = DeepSeekProvider(settings_for_test(tmp_path, deepseek_api_key=SecretStr("")), transport=httpx.MockTransport(lambda request: calls.append(request)))
    with pytest.raises(ServiceError) as caught:
        asyncio.run(provider.generate([], "unit-no-key"))
    assert caught.value.code == "LLM_KEY_MISSING"
    assert calls == []
    assert provider.ledger.summary()["calls"] == 0


@pytest.mark.parametrize("limit", [0, -1, 801, True])
def test_call_cannot_bypass_output_budget_limit(tmp_path, limit):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=envelope())

    provider = DeepSeekProvider(settings_for_test(tmp_path), transport=httpx.MockTransport(handler))
    with pytest.raises((ServiceError, ValueError)):
        asyncio.run(provider.generate([], "unit-output-limit", max_output=limit))
    assert calls == []
    assert provider.ledger.summary()["calls"] == 0


def test_valid_payload_disables_thinking_and_records_only_final_output(tmp_path):
    payloads = []

    def handler(request):
        assert str(request.url) == "https://api.deepseek.com/chat/completions"
        assert request.headers["Authorization"] == "Bearer test-only"
        payloads.append(json.loads(request.content))
        return httpx.Response(200, json=envelope())

    provider = DeepSeekProvider(settings_for_test(tmp_path), transport=httpx.MockTransport(handler))
    result = asyncio.run(provider.generate([], "unit-success"))
    assert payloads[0]["thinking"] == {"type": "disabled"}
    assert payloads[0]["stream"] is False
    assert payloads[0]["max_tokens"] == 800
    assert payloads[0]["response_format"] == {"type": "json_object"}
    assert result["content"] == "unit test text"
    assert "reasoning_content" not in result
    assert provider.verified is True
    assert provider.ledger.records()[0]["estimatedUpperCny"] == pytest.approx(0.00052)


@pytest.mark.parametrize("failure,code,expected_status", [
    (401, "LLM_AUTH_FAILED", "http_401"),
    (httpx.ConnectError("offline reconnect failure"), "LLM_NETWORK", "transport_unknown"),
    (httpx.ReadTimeout("offline timeout after success"), "LLM_TIMEOUT", "timeout_unknown"),
])
def test_success_then_failure_invalidates_readiness_without_retry(tmp_path, failure, code, expected_status):
    calls = []

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(200, json=envelope())
        if isinstance(failure, int):
            return httpx.Response(failure, json={"error": "offline fault"})
        raise failure

    configuration = settings_for_test(tmp_path)
    provider = DeepSeekProvider(configuration, transport=httpx.MockTransport(handler))
    asyncio.run(provider.generate([], "unit-readiness-success"))
    assert provider.verified is True
    with pytest.raises(ServiceError) as caught:
        asyncio.run(provider.generate([], "unit-readiness-failure"))
    assert caught.value.code == code
    assert provider.verified is False
    assert DeepSeekProvider(configuration, transport=httpx.MockTransport(handler)).verified is False
    assert len(calls) == 2
    assert provider.ledger.summary()["calls"] == 2
    records = {item["requestId"]: item for item in provider.ledger.records()}
    assert records["unit-readiness-success"]["status"] == "success"
    assert records["unit-readiness-success"]["estimatedUpperCny"] == pytest.approx(0.00052)
    assert records["unit-readiness-failure"]["status"] == expected_status
    if isinstance(failure, int):
        assert records["unit-readiness-failure"]["estimatedUpperCny"] == 0
        assert provider.ledger.summary()["estimatedUpperCostCny"] == pytest.approx(0.00052)
    else:
        assert records["unit-readiness-failure"]["estimatedUpperCny"] is None
        assert provider.ledger.summary()["estimatedUpperCostCny"] > 0.00052


def test_unexpected_reasoning_is_not_labeled_success(tmp_path):
    body = envelope()
    body["choices"][0]["message"]["reasoning_content"] = "offline hidden reasoning fixture"
    provider = DeepSeekProvider(settings_for_test(tmp_path), transport=httpx.MockTransport(lambda request: httpx.Response(200, json=body)))
    with pytest.raises(ServiceError) as caught:
        asyncio.run(provider.generate([], "unit-thinking-mismatch"))
    assert caught.value.code == "LLM_MODE_MISMATCH"
    assert provider.verified is False
    assert provider.ledger.records()[0]["status"] != "success"


def test_budget_prevents_a_call_before_transport_and_persists(tmp_path):
    calls = []
    configuration = settings_for_test(tmp_path, rag_test_budget_cny=0.000001)
    provider = DeepSeekProvider(configuration, transport=httpx.MockTransport(lambda request: calls.append(request)))
    with pytest.raises(ServiceError) as caught:
        asyncio.run(provider.generate([], "unit-budget"))
    assert caught.value.code == "TEST_BUDGET_EXCEEDED"
    assert calls == []
    assert BudgetLedger(configuration.rag_data_dir / "api-budget.sqlite3", 0.000001).summary()["calls"] == 0
    with pytest.raises(ValidationError):
        settings_for_test(tmp_path, rag_test_budget_cny=3.1)


@pytest.mark.parametrize("content", ["{}", "{bad-json", json.dumps({"answer": "单元测试", "usedCitationIds": ["unknown"], "uncertain": False}), json.dumps({"answer": "单元测试", "usedCitationIds": [], "uncertain": False}), json.dumps({"answer": "   ", "usedCitationIds": ["unit_chunk"], "uncertain": False})])
def test_model_answer_rejects_missing_or_illegal_evidence_and_blank_text(content):
    with pytest.raises(ServiceError) as caught:
        validated_answer(content, evidence(), "unit-request")
    assert caught.value.code == "ANSWER_EVIDENCE_INVALID"


def test_citations_are_canonical_and_uncertainty_can_be_explicit():
    answer = validated_answer(json.dumps({"answer": "单元测试结果", "usedCitationIds": ["unit_chunk", "unit_chunk"], "uncertain": False}), evidence(), "unit-request")
    assert answer["citations"] == evidence()
    partial = validated_answer(json.dumps({"answer": "单元测试资料不足", "usedCitationIds": [], "uncertain": True}), evidence(), "unit-uncertain")
    assert partial["uncertain"] is True and partial["citations"] == []


def test_retrieval_insufficiency_never_calls_model():
    class NeverProvider:
        async def generate(self, *_):
            raise AssertionError("Insufficient evidence must not make a model request")

    result = asyncio.run(grounded_answer("单元测试资料外问题", {"uncertain": True, "evidence": []}, NeverProvider(), "unit-no-evidence"))
    assert result["uncertain"] is True
    assert result["citations"] == []


class RecordingAliasProvider:
    """Offline response stub, never an HTTP or real model call."""

    def __init__(self, aliases, uncertain=False):
        self.aliases = aliases
        self.uncertain = uncertain
        self.calls = []

    async def generate(self, messages, request_id):
        self.calls.append({"messages": messages, "requestId": request_id})
        return {"content": json.dumps({"answer": "单元测试合成回复。", "usedCitationIds": self.aliases, "uncertain": self.uncertain})}


def hashed_evidence(count=1):
    fixtures = []
    for index in range(count):
        fixture = {**evidence()[0], "id": "chunk_" + str(index) * 64}
        fixture["chunkId"] = fixture["id"]
        fixture["sectionId"] = "unit_section_" + str(index)
        fixtures.append(fixture)
    return fixtures


def test_grounded_answer_alias_maps_to_canonical_citation_and_payload_omits_hash():
    fixtures = hashed_evidence()
    provider = RecordingAliasProvider(["E1", "E1"])
    answer = asyncio.run(grounded_answer("单元测试问题", {"uncertain": False, "evidence": fixtures}, provider, "unit-alias"))
    assert len(provider.calls) == 1
    payload = json.loads(provider.calls[0]["messages"][1]["content"])
    assert payload["EVIDENCE"][0] == {"id": "E1", "title": fixtures[0]["title"], "locator": fixtures[0]["locator"], "excerpt": fixtures[0]["excerpt"]}
    serialized_messages = json.dumps(provider.calls[0]["messages"], ensure_ascii=False)
    assert fixtures[0]["id"] not in serialized_messages
    assert fixtures[0]["sourceId"] not in serialized_messages
    assert fixtures[0]["sectionId"] not in serialized_messages
    assert answer["citations"] == [{key: fixtures[0][key] for key in ("id", "title", "sourceId", "locator", "url", "excerpt", "contentKind")}]
    assert answer["requestId"] == "unit-alias"
    assert answer["uncertain"] is False
    assert "E1" not in answer["answer"] and fixtures[0]["id"] not in answer["answer"]


@pytest.mark.parametrize("alias", ["E0", "E2", "E6", "e1", "unit_chunk", "chunk_" + "0" * 64])
def test_grounded_answer_rejects_unknown_or_canonical_id_in_alias_response(alias):
    provider = RecordingAliasProvider([alias])
    with pytest.raises(ServiceError) as caught:
        asyncio.run(grounded_answer("单元测试问题", {"uncertain": False, "evidence": hashed_evidence()}, provider, "unit-unknown-alias"))
    assert caught.value.code == "ANSWER_EVIDENCE_INVALID"
    assert len(provider.calls) == 1


def test_grounded_answer_limits_alias_evidence_to_five_and_keeps_uncertainty():
    fixtures = hashed_evidence(6)
    provider = RecordingAliasProvider(["E5"], uncertain=True)
    answer = asyncio.run(grounded_answer("单元测试多子项问题", {"uncertain": False, "evidence": fixtures}, provider, "unit-five-aliases"))
    payload = json.loads(provider.calls[0]["messages"][1]["content"])
    assert [item["id"] for item in payload["EVIDENCE"]] == ["E1", "E2", "E3", "E4", "E5"]
    assert fixtures[5]["id"] not in json.dumps(provider.calls[0]["messages"])
    assert answer["citations"][0]["id"] == fixtures[4]["id"]
    assert answer["uncertain"] is True
