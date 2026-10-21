"""OFFLINE API fault injection. No real knowledge model, key, or paid calls."""
import asyncio
import json
from pathlib import Path
import threading
import types
from unittest.mock import AsyncMock
import uuid

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr, ValidationError

from backend.app.config import PROJECT_ROOT, Settings
from backend.app.errors import ServiceError
from backend.app.main import create_app
from backend.app.providers.llm import DeepSeekProvider
from backend.app.schemas import QuestionRequest
from backend.app.services.runtime import Runtime
from backend.tests.conftest import initialized_settings


def settings_for_test(tmp_path: Path, **overrides):
    values = dict(_env_file=None, deepseek_api_key=SecretStr(""), rag_data_dir=tmp_path / "runtime", embedding_model_path=tmp_path / "fake-model")
    values.update(overrides)
    return initialized_settings(Settings(**values))


EVIDENCE = [{"id": "unit_chunk", "title": "单元测试资料", "sourceId": "unit_source", "locator": "单元测试位置", "url": "https://example.invalid/unit-only", "excerpt": "此为离线故障注入文本。", "contentKind": "original_fact_summary"}]


class FakeSearch:
    def __init__(self, uncertain=False):
        self.uncertain = uncertain
        self.calls = []

    def search(self, question, *args):
        self.calls.append(question)
        return {"question": question, "uncertain": self.uncertain, "evidence": [] if self.uncertain else EVIDENCE, "retrievalMode": "offline-test-double"}


class FakeProvider:
    configured = verified = True

    def __init__(self, ledger, started=None, release=None):
        self.ledger = ledger
        self.started, self.release = started, release
        self.calls = []

    async def generate(self, messages, request_id):
        self.calls.append(request_id)
        if self.started:
            self.started.set()
        if self.release:
            await self.release.wait()
        return {"content": json.dumps({"answer": "单元测试假回答，不代表文化知识。", "usedCitationIds": ["E1"], "uncertain": False})}


def fake_ready(runtime, uncertain=False, started=None, release=None):
    runtime.search_service = FakeSearch(uncertain)
    provider = FakeProvider(runtime.provider.ledger, started, release)
    runtime.provider = provider
    return provider


def test_health_uninitialized_and_all_future_capabilities_disabled(tmp_path):
    app = create_app(settings_for_test(tmp_path))
    with TestClient(app) as client:
        health = client.get("/api/v1/health")
        assert health.status_code == 200
        assert health.json()["status"] == "degraded"
        assert health.json()["diagnostic"] == "KNOWLEDGE_NOT_INITIALIZED"
        assert health.json()["knowledge"] is False
        assert health.json()["llmConfigured"] is False
        capabilities = client.get("/api/v1/capabilities").json()
        for field in ("questionAnswering", "knowledgeSearch", "agentWorkflow", "conceptImage", "imageToModel"):
            assert capabilities[field] is False
        for endpoint in ("/api/v1/knowledge/search", "/api/v1/chat"):
            response = client.post(endpoint, json={"question": "单元测试"})
            assert response.status_code == 503
            assert response.json()["error"]["code"] == "KNOWLEDGE_NOT_INITIALIZED"


@pytest.mark.parametrize("path", ["/.env", "/.env.example", "/.git/config", "/backend/app/config.py", "/docs/reports/phase-01.md", "/README.md", "/knowledge/documents/unit.json", "/images/%2e%2e/.env", "/css/%2e%2e/backend/app/main.py", "/images/..%5c.env"])
def test_static_private_and_traversal_paths_are_refused(tmp_path, path):
    app = create_app(settings_for_test(tmp_path))
    with TestClient(app) as client:
        response = client.get(path)
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "NOT_FOUND"
        assert str(PROJECT_ROOT) not in response.text


def test_original_eight_pages_and_public_module_still_load(tmp_path):
    app = create_app(settings_for_test(tmp_path))
    with TestClient(app) as client:
        for page in ("index", "history", "roles", "facial", "music", "video", "gallery", "about"):
            response = client.get(f"/{page}.html")
            assert response.status_code == 200
            assert "text/html" in response.headers["content-type"]
            assert "梨园风华" in response.text
            assert response.headers["cache-control"] == "no-store"
        for path in ("/css/ai-workshop.css", "/js/ai-workshop/main.js", "/js/ai-workshop/services.js", "/js/ai-workshop/contracts.js"):
            response = client.get(path)
            assert response.status_code == 200
            assert response.headers["x-content-type-options"] == "nosniff"


def test_cors_allows_only_explicit_local_origin_and_required_headers(tmp_path):
    app = create_app(settings_for_test(tmp_path))
    with TestClient(app) as client:
        headers = {"Origin": "http://127.0.0.1:8877", "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type,x-idempotency-key"}
        good = client.options("/api/v1/chat", headers=headers)
        assert good.status_code == 200
        assert good.headers["access-control-allow-origin"] == headers["Origin"]
        allowed = good.headers["access-control-allow-headers"].lower()
        assert "content-type" in allowed and "x-idempotency-key" in allowed
        assert "access-control-allow-credentials" not in good.headers
        headers["Origin"] = "https://unapproved.example.invalid"
        bad = client.options("/api/v1/chat", headers=headers)
        assert bad.status_code == 400
        assert "access-control-allow-origin" not in bad.headers


@pytest.mark.parametrize("question", ["", "  ", "京" * 601, "😀" * 301, "bad\u0000input"])
def test_empty_overlong_utf16_and_control_input_rejected(tmp_path, question):
    app = create_app(settings_for_test(tmp_path))
    with TestClient(app) as client:
        response = client.post("/api/v1/chat", json={"question": question})
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "INVALID_REQUEST"
        assert "input" not in response.json()["error"]


def test_exact_utf16_boundary_and_unpaired_surrogates():
    assert QuestionRequest(question="😀" * 300).question == "😀" * 300
    with pytest.raises(ValidationError):
        QuestionRequest(question="\ud800")


def test_oversized_body_returns_request_identifier_without_internal_details(tmp_path):
    app = create_app(settings_for_test(tmp_path))
    with TestClient(app) as client:
        response = client.post("/api/v1/chat", content=b"x" * 8193, headers={"Content-Type": "application/json"})
        assert response.status_code == 413
        assert response.json()["error"]["code"] == "BODY_TOO_LARGE"
        uuid.UUID(response.json()["requestId"])
        assert response.headers["X-Request-ID"] == response.json()["requestId"]


def test_ready_retrieval_without_key_returns_honest_error_and_no_cost(tmp_path):
    app = create_app(settings_for_test(tmp_path))
    with TestClient(app) as client:
        app.state.runtime.search_service = FakeSearch()
        response = client.post("/api/v1/chat", json={"question": "单元测试"})
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "LLM_KEY_MISSING"
        assert app.state.runtime.provider.ledger.summary()["calls"] == 0


def test_insufficient_retrieval_does_not_require_model_key(tmp_path):
    app = create_app(settings_for_test(tmp_path))
    with TestClient(app) as client:
        app.state.runtime.search_service = FakeSearch(uncertain=True)
        response = client.post("/api/v1/chat", json={"question": "单元测试资料外问题"})
        assert response.status_code == 200
        assert response.json()["uncertain"] is True and response.json()["citations"] == []
        assert app.state.runtime.provider.ledger.summary()["calls"] == 0


def test_completed_idempotency_key_reuses_one_call_and_rejects_conflicting_question(tmp_path):
    app = create_app(settings_for_test(tmp_path))
    with TestClient(app) as client:
        provider = fake_ready(app.state.runtime)
        headers = {"X-Idempotency-Key": "unit-one"}
        one = client.post("/api/v1/chat", json={"question": "单元测试一"}, headers=headers)
        two = client.post("/api/v1/chat", json={"question": "单元测试一"}, headers=headers)
        assert one.status_code == two.status_code == 200
        assert one.json() == two.json()
        assert len(provider.calls) == 1
        assert one.json()["citations"] == EVIDENCE
        conflict = client.post("/api/v1/chat", json={"question": "单元测试二"}, headers=headers)
        assert conflict.status_code == 409
        assert conflict.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"


@pytest.mark.parametrize("key", ["bad key", "x" * 129, "../../config"])
def test_invalid_idempotency_key_rejected_before_any_model_call(tmp_path, key):
    app = create_app(settings_for_test(tmp_path))
    with TestClient(app) as client:
        provider = fake_ready(app.state.runtime)
        response = client.post("/api/v1/chat", json={"question": "单元测试"}, headers={"X-Idempotency-Key": key})
        assert response.status_code == 400
        assert provider.calls == []


def test_in_progress_duplicate_key_and_third_concurrent_request_are_blocked(tmp_path):
    async def scenario():
        app = create_app(settings_for_test(tmp_path))
        runtime = app.state.runtime
        started, release = asyncio.Event(), asyncio.Event()
        provider = fake_ready(runtime, started=started, release=release)
        tasks = []
        try:
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://unit.test") as client:
                tasks.append(asyncio.create_task(client.post("/api/v1/chat", json={"question": "单元测试一"}, headers={"X-Idempotency-Key": "unit-pending"})))
                await asyncio.wait_for(started.wait(), 2)
                duplicate = await client.post("/api/v1/chat", json={"question": "单元测试一"}, headers={"X-Idempotency-Key": "unit-pending"})
                assert duplicate.status_code == 409
                assert duplicate.json()["error"]["code"] == "REQUEST_IN_PROGRESS"
                started.clear()
                tasks.append(asyncio.create_task(client.post("/api/v1/chat", json={"question": "单元测试二"}, headers={"X-Idempotency-Key": "unit-second"})))
                await asyncio.wait_for(started.wait(), 2)
                third = await client.post("/api/v1/chat", json={"question": "单元测试三"}, headers={"X-Idempotency-Key": "unit-third"})
                assert third.status_code == 429
                assert third.json()["error"]["code"] == "CHAT_BUSY"
                release.set()
                finished = await asyncio.gather(*tasks)
                assert all(response.status_code == 200 for response in finished)
                assert len(provider.calls) == 2
        finally:
            release.set()
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            await runtime.close()

    asyncio.run(scenario())


@pytest.mark.parametrize("endpoint", ["/api/v1/knowledge/search", "/api/v1/chat"])
def test_total_request_timeout_is_a_controlled_504(tmp_path, endpoint):
    app = create_app(settings_for_test(tmp_path))
    with TestClient(app) as client:
        fake_ready(app.state.runtime)
        app.state.runtime.knowledge = AsyncMock(side_effect=TimeoutError("offline-timeout"))
        response = client.post(endpoint, json={"question": "单元测试"})
        assert response.status_code == 504
        assert "TIMEOUT" in response.json()["error"]["code"]


def test_failed_model_fixture_does_not_expose_raw_upstream_information(tmp_path):
    configuration = settings_for_test(tmp_path, deepseek_api_key=SecretStr("test-only"))
    app = create_app(configuration)
    with TestClient(app) as client:
        app.state.runtime.search_service = FakeSearch()
        app.state.runtime.provider = DeepSeekProvider(configuration, transport=httpx.MockTransport(lambda request: httpx.Response(401, json={"message": "unit-only-private-upstream"})))
        response = client.post("/api/v1/chat", json={"question": "单元测试"})
        assert response.status_code == 502
        assert response.json()["error"]["code"] == "LLM_AUTH_FAILED"
        assert "unit-only-private" not in response.text


def test_source_endpoint_only_displays_public_metadata(tmp_path):
    app = create_app(settings_for_test(tmp_path))
    with TestClient(app) as client:
        runtime = app.state.runtime
        fake_ready(runtime)
        source = {
            "source_id": "unit_source", "title": "单元测试资料", "category": "history",
            "source_url": "https://example.invalid/unit-only", "license_status": "unit-fixture-only",
            "local_file_path": "unit-only-private-file", "private_note": "unit-only-private-note",
        }
        runtime.store = types.SimpleNamespace(sources=lambda: [source], close=lambda: None)
        response = client.get("/api/v1/knowledge/sources")
        assert response.status_code == 200
        public = response.json()["sources"][0]
        assert public["source_id"] == "unit_source"
        assert public["source_url"] == source["source_url"]
        assert "local_file_path" not in public and "private_note" not in public


def test_empty_search_category_is_validated_before_retrieval(tmp_path):
    app = create_app(settings_for_test(tmp_path))
    with TestClient(app) as client:
        fake_ready(app.state.runtime)
        response = client.post("/api/v1/knowledge/search", json={"question": "单元测试", "category": "   "})
        assert response.status_code == 422


def test_cancelled_request_retains_executor_slot_until_worker_finishes(tmp_path):
    async def scenario():
        runtime = Runtime(settings_for_test(tmp_path))
        runtime.search_service = FakeSearch()
        started, release = threading.Event(), threading.Event()
        tasks = []

        def worker():
            started.set()
            release.wait(timeout=3)
            return "offline-work"

        try:
            first = asyncio.create_task(runtime.knowledge(worker))
            tasks.append(first)
            assert await asyncio.to_thread(started.wait, 2)
            first.cancel()
            await asyncio.gather(first, return_exceptions=True)
            assert runtime.inflight == 1
            second = asyncio.create_task(runtime.knowledge(lambda: "second"))
            tasks.append(second)
            await asyncio.sleep(0)
            assert runtime.inflight == 2
            with pytest.raises(ServiceError) as caught:
                await runtime.knowledge(lambda: "third")
            assert caught.value.code == "KNOWLEDGE_BUSY"
            release.set()
            assert await second == "second"
            await asyncio.sleep(0)
            assert runtime.inflight == 0
        finally:
            release.set()
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            await runtime.close()

    asyncio.run(scenario())
