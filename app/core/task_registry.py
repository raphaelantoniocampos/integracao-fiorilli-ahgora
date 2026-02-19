import asyncio
from uuid import UUID
import logging

logger = logging.getLogger(__name__)

class TaskRegistry:
    """
    A simple registry to track active asyncio tasks for synchronization jobs.
    This allows us to cancel running jobs via the API.
    """
    _instance = None
    _tasks: dict[UUID, asyncio.Task] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TaskRegistry, cls).__new__(cls)
        return cls._instance

    def register(self, job_id: UUID, task: asyncio.Task):
        self._tasks[job_id] = task
        logger.debug(f"Registered task for job {job_id}")

    def unregister(self, job_id: UUID):
        if job_id in self._tasks:
            del self._tasks[job_id]
            logger.debug(f"Unregistered task for job {job_id}")

    def get_task(self, job_id: UUID) -> asyncio.Task | None:
        return self._tasks.get(job_id)

    def get_all_tasks(self) -> dict[UUID, asyncio.Task]:
        return self._tasks.copy()

task_registry = TaskRegistry()
