"""Startup failure releases resources; fake startup does not prove live AI."""
import asyncio
import pytest
from backend.app.main import create_app
from backend.app.config import Settings
from backend.tests.conftest import initialized_settings

@pytest.mark.parametrize('failure_stage', ['runtime', 'supervisor'])
def test_startup_failure_always_closes_resources(tmp_path, failure_stage):
    app = create_app(initialized_settings(Settings(_env_file=None, rag_data_dir=tmp_path)))
    closed = []
    async def runtime_start():
        if failure_stage == 'runtime': raise RuntimeError('test startup failed')
    async def supervisor_start():
        if failure_stage == 'supervisor': raise RuntimeError('test startup failed')
    async def runtime_close(): closed.append('runtime')
    async def supervisor_close(): closed.append('supervisor')
    app.state.runtime.start, app.state.runtime.close = runtime_start, runtime_close
    app.state.agent_supervisor.start, app.state.agent_supervisor.close = supervisor_start, supervisor_close
    async def run():
        with pytest.raises(RuntimeError, match='test startup failed'):
            async with app.router.lifespan_context(app): pass
    asyncio.run(run())
    assert closed == ['supervisor', 'runtime']
