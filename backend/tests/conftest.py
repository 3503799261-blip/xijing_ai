"""All app factories in OFFLINE tests use an isolated quota ledger.

Production does not expose an environment variable to select/reset this path.
No test may recover or consume the project's real ledger.
"""
import pytest
import httpx


@pytest.fixture(autouse=True)
def isolated_app_usage_path(tmp_path, monkeypatch):
    import backend.app.main as main
    from backend.app.assets.neural_service import ModelService
    monkeypatch.setattr(main, 'USAGE_LEDGER_PATH', tmp_path / 'isolated-neural4d-usage.sqlite3')

    def unexpected_provider_request(request):
        raise AssertionError('Offline app test attempted an unplanned supplier request.')

    def offline_model_service(settings, assets, usage):
        return ModelService(settings, assets, usage, httpx.MockTransport(unexpected_provider_request))

    # Production still constructs only its default real HTTP provider against
    # the canonical ledger. Test factories inject an explicit refusing mock;
    # temporary paths cannot silently become another real creation budget.
    monkeypatch.setattr(main, 'ModelService', offline_model_service)
