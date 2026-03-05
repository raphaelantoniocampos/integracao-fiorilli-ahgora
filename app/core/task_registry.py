import asyncio
import logging
import threading
from uuid import UUID

logger = logging.getLogger(__name__)


class TaskRegistry:
    """
    A simple registry to track active asyncio tasks for synchronization jobs.
    This allows us to cancel running jobs via the API.
    """

    _instance = None
    _tasks: dict[str, asyncio.Task] = {}
    _cancel_events: dict[str, "threading.Event"] = {}

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
        popped_task = self._tasks.pop(job_key, None)
        popped_event = self._cancel_events.pop(job_key, None)
        if popped_task or popped_event:
            logger.info(
                f"Unregistered task/event for job {job_key}. Total active tasks: {len(self._tasks)}"
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

    def register_cancel_event(self, job_id: UUID, event: threading.Event):
        job_key = str(job_id)
        self._cancel_events[job_key] = event
        logger.info(f"Registered cancel event for job {job_key}")

    def get_cancel_event(self, job_id: UUID) -> threading.Event | None:
        return self._cancel_events.get(str(job_id))


task_registry = TaskRegistry()
