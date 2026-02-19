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
    _tasks: dict[str, asyncio.Task] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TaskRegistry, cls).__new__(cls)
        return cls._instance

    def register(self, job_id: UUID, task: asyncio.Task):
        job_key = str(job_id)
        self._tasks[job_key] = task
        logger.info(
            f"Registered task for job {job_key}. Total active tasks: {len(self._tasks)}"
        )

    def unregister(self, job_id: UUID):
        job_key = str(job_id)
        if job_key in self._tasks:
            del self._tasks[job_key]
            logger.info(
                f"Unregistered task for job {job_key}. Total active tasks: {len(self._tasks)}"
            )
        else:
            logger.warning(
                f"Attempted to unregister non-existent task for job {job_key}"
            )

    def get_task(self, job_id: UUID) -> asyncio.Task | None:
        job_key = str(job_id)
        task = self._tasks.get(job_key)
        if task:
            logger.debug(f"Task found for job {job_key}")
        else:
            logger.debug(
                f"No task found for job {job_key} in registry (Keys: {list(self._tasks.keys())})"
            )
        return task

    def get_all_tasks(self) -> dict[str, asyncio.Task]:
        return self._tasks.copy()


task_registry = TaskRegistry()
