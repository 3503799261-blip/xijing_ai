"""One supervised creator, bounded persistent queue, no paid automatic retry."""
import asyncio
import portalocker
import sqlite3
import logging
from ..errors import ServiceError
from .store import TaskStore, TASK_DATABASE_MESSAGE

class Supervisor:
    def __init__(self, runtime, runner=None):
        self.runtime = runtime
        self.store_path = runtime.settings.rag_data_dir / 'agent-tasks.sqlite3'
        self.store = None
        self.database_error = None
        try:
            self.store = TaskStore(self.store_path)
        except (ServiceError, OSError, sqlite3.Error):
            self.database_error = ServiceError('AGENT_DATABASE_UNAVAILABLE', TASK_DATABASE_MESSAGE, 503)
            logging.getLogger('xijing.requests').warning('component=agent_database status=unavailable code=AGENT_DATABASE_UNAVAILABLE')
        self.runner = runner
        self.wakeup = asyncio.Event()
        self.worker = None
        self.ready = False
        self.current_task = None
        self.owner_lock = None
        self.diagnostic = self.database_error.code if self.database_error else None

    def require_database(self):
        if self.database_error is not None:
            raise self.database_error
        try:
            # Revalidate the configured existing file, never reconnect with a
            # creating mode if it disappears or is replaced after startup.
            TaskStore(self.store_path)
        except (ServiceError, OSError, sqlite3.Error):
            self.database_error = ServiceError('AGENT_DATABASE_UNAVAILABLE', TASK_DATABASE_MESSAGE, 503)
            self.diagnostic = self.database_error.code
            raise self.database_error from None
        return self.store

    def database_status(self):
        try:
            self.require_database()
            return {'available': True, 'diagnostic': None}
        except ServiceError as error:
            return {'available': False, 'diagnostic': error.code, 'message': error.message}

    async def start(self):
        if self.database_error is not None:
            self.ready = False
            return
        if self.worker and not self.worker.done():
            return
        self.ready = False
        if self.owner_lock:
            self.owner_lock.release()
            self.owner_lock = None
        lock = portalocker.Lock(str(self.runtime.settings.rag_data_dir / 'agent-tasks-owner.lock'), timeout=0)
        try:
            lock.acquire()
        except portalocker.exceptions.LockException:
            # An unavailable second process must never "recover" live tasks
            # owned by the first application, even if its RAG lock also fails.
            self.diagnostic = 'AGENT_TASKS_LOCKED'
            return
        except OSError:
            self.diagnostic = 'AGENT_TASKS_LOCK_UNAVAILABLE'
            return
        self.owner_lock = lock
        try:
            self.store.recover()
            self.worker = asyncio.create_task(self._work(), name='opera-agent-supervisor')
            self.ready = True
            self.diagnostic = None
        except (ServiceError, OSError, sqlite3.Error):
            self.owner_lock.release()
            self.owner_lock = None
            self.worker = None
            self.database_error = ServiceError('AGENT_DATABASE_UNAVAILABLE', TASK_DATABASE_MESSAGE, 503)
            self.diagnostic = self.database_error.code
            return
        except BaseException:
            self.owner_lock.release()
            self.owner_lock = None
            self.worker = None
            raise

    async def close(self):
        self.ready = False
        try:
            if self.worker:
                self.worker.cancel()
                await asyncio.gather(self.worker, return_exceptions=True)
        finally:
            self.worker = None
            if self.owner_lock:
                self.owner_lock.release()
                self.owner_lock = None

    def available(self):
        if self.database_error is not None or self.store is None:
            return False
        try:
            self.require_database()
        except ServiceError:
            return False
        if not self.ready or not self.worker or self.worker.done() or not self.runtime.settings.agent_workflow_enabled:
            return False
        if not self.runtime.search_service or not self.runtime.provider.verified:
            return False
        try:
            budget = self.runtime.provider.ledger.summary()
        except (ServiceError, OSError, sqlite3.Error, AttributeError):
            return False
        scope = budget.get('activeScope')
        return budget['estimatedUpperCostCny'] < budget['budgetCny'] and (not scope or scope['estimatedUpperCostCny'] < scope['budgetCny'])

    def create(self, brief, key):
        self.require_database()
        existing = self.store.existing(key, brief)
        if existing:
            return existing
        if not self.available():
            raise ServiceError('AGENT_SERVICE_UNAVAILABLE', 'Agent服务未就绪，请检查知识库、模型验证与应用预算。', 503, True)
        task_id, created = self.store.create(brief, key, self.runtime.settings.agent_queue_limit)
        if created:
            self.wakeup.set()
        return task_id

    async def _work(self):
        while True:
            task_id = self.store.next_waiting()
            if task_id is None:
                self.wakeup.clear()
                await self.wakeup.wait()
                continue
            if not self.store.start(task_id):
                continue
            self.current_task = task_id
            try:
                if self.runner is None:
                    from .workflow import run_workflow
                    runner = run_workflow
                else:
                    runner = self.runner
                async def emit(agent_id, state, summary='', artifact=None, error_code=None):
                    self.store.emit(task_id, agent_id, state, summary, artifact, error_code)
                async with asyncio.timeout(self.runtime.settings.agent_workflow_timeout_seconds):
                    result = await runner(self.runtime, task_id, self.store.brief(task_id), emit,
                                          lambda: self.store.cancelled(task_id))
                self.store.finish(task_id, result)
            except asyncio.CancelledError:
                self.store.fail(task_id, ServiceError('WORKFLOW_INTERRUPTED', '服务停止导致任务中断，已保存完成阶段；未自动付费重试。', 503, True))
                raise
            except TimeoutError:
                self.store.fail(task_id, ServiceError('WORKFLOW_TIMEOUT', '协作任务超时，已停止后续调用；未知模型费用保留预留。', 504, True))
            except ServiceError as error:
                if error.code == 'WORKFLOW_CANCELLED':
                    self.store.complete_cancel(task_id)
                else:
                    self.store.fail(task_id, error)
            except Exception:
                self.store.fail(task_id, ServiceError('WORKFLOW_ERROR', '协作出现内部错误，未展示未经校验的结果；请稍后手动重新创作。', 500, True))
            finally:
                self.current_task = None
