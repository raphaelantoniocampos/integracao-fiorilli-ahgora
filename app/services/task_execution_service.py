import logging
import asyncio
from uuid import UUID


from app.domain.enums import (
    AutomationTaskType as TaskType,
    AutomationTaskStatus as TaskStatus,
)
from app.infrastructure.db.sqlalchemy_repo import SqlAlchemyRepo
from app.infrastructure.automation.web.ahgora_browser import AhgoraBrowser

logger = logging.getLogger(__name__)


class TaskExecutionService:
    def __init__(self, repo: SqlAlchemyRepo):
        self.repo = repo

    async def execute_task(self, task_id: UUID) -> bool:
        """
        Executes a single automation task.
        Returns True if successful, False otherwise.
        """
        task = await self.repo.get_task(task_id)
        if not task:
            logger.error(f"Task {task_id} not found.")
            return False

        if task.status in [TaskStatus.SUCCESS, TaskStatus.RUNNING]:
            logger.warning(f"Task {task_id} is already completed or running.")
            return False

        await self.repo.update_task_status(task_id, TaskStatus.RUNNING)
        await self.repo.add_log(
            task.job_id,
            "INFO",
            f"Iniciando automação web (Selenium) para tarefa {task.type}",
            task_id=task_id,
        )

        success = False
        error_msg = None

        try:
            # We run the browser automation in a separate thread so we don't block the async loop
            loop = asyncio.get_running_loop()
            success = await asyncio.to_thread(
                self._run_browser_automation,
                task.type,
                task.payload,
                task.job_id,
                task_id,
                loop,
            )
        except Exception as e:
            logger.exception(f"Error executing task {task_id}")
            error_msg = str(e)
            await self.repo.add_log(
                task.job_id,
                "ERROR",
                f"Falha na automação: {error_msg}",
                task_id=task_id,
            )

        if success:
            await self.repo.update_task_status(task_id, TaskStatus.SUCCESS)
            await self.repo.add_log(
                task.job_id,
                "INFO",
                "Automação concluída com sucesso.",
                task_id=task_id,
            )
            # Update Ahgora model state based on task success
            await self._update_ahgora_state(task.type, task.payload)
        else:
            if not error_msg:
                # If error wasn't raised but automation returned False
                await self.repo.add_log(
                    task.job_id,
                    "WARNING",
                    "Automação finalizou sem sucesso, mas sem lançar exceção.",
                    task_id=task_id,
                )

            await self.repo.update_task_status(
                task_id, TaskStatus.FAILED, message=error_msg
            )

        return success

    async def execute_batch(self, job_id: UUID, task_type: str) -> None:
        """
        Executes all pending or failed tasks of a certain type for a given job.
        Runs sequentially to respect browser limitations.
        """
        from app.domain.enums import AutomationTaskStatus

        logger.info(f"Starting batch execution for job {job_id}, type {task_type}")

        # We need a custom repo method or we fetch all and filter
        tasks = await self.repo.get_automation_tasks_by_job(job_id)
        batch = [
            t
            for t in tasks
            if (
                t.type.value == task_type
                or t.type.name == task_type
                or str(t.type) == task_type
            )
            and t.status in [AutomationTaskStatus.PENDING, AutomationTaskStatus.FAILED]
        ]

        for t in batch:
            await self.execute_task(t.id)

    async def cancel_task(self, task_id: UUID) -> bool:
        """
        Cancels a single automation task if it is pending or running.
        Returns True if cancelled successfully.
        """
        from app.domain.enums import AutomationTaskStatus

        task = await self.repo.get_task(task_id)
        if not task:
            logger.error(f"Task {task_id} not found.")
            return False

        if task.status not in [
            AutomationTaskStatus.PENDING,
            AutomationTaskStatus.RUNNING,
        ]:
            logger.warning(
                f"Task {task_id} cannot be cancelled in state {task.status}."
            )
            return False

        await self.repo.update_task_status(task_id, AutomationTaskStatus.CANCELLED)
        await self.repo.add_log(
            task.job_id,
            "WARNING",
            f"Tarefa {task.type} cancelada pelo usuário.",
            task_id=task_id,
        )
        return True

    async def cancel_batch(self, job_id: UUID, task_type: str) -> None:
        """
        Cancels all pending or running tasks of a certain type for a given job.
        Note: If a browser is currently driving a task, it might finish unless hard-killed,
        but we can at least mark pending ones as cancelled.
        """
        from app.domain.enums import AutomationTaskStatus

        logger.info(f"Cancelling batch execution for job {job_id}, type {task_type}")

        tasks = await self.repo.get_automation_tasks_by_job(job_id)
        batch = [
            t
            for t in tasks
            if (
                t.type.value == task_type
                or t.type.name == task_type
                or str(t.type) == task_type
            )
            and t.status in [AutomationTaskStatus.PENDING, AutomationTaskStatus.RUNNING]
        ]

        for t in batch:
            await self.cancel_task(t.id)

    def _run_browser_automation(
        self,
        task_type: TaskType,
        payload: dict,
        job_id: UUID,
        task_id: UUID,
        loop: asyncio.AbstractEventLoop,
    ) -> bool:
        """
        Runs the actual Selenium browser automation based on task type.
        This runs in a sync thread.
        """

        def log_cb(level: str, msg: str):
            asyncio.run_coroutine_threadsafe(
                self.repo.add_log(job_id, level, msg, task_id=task_id), loop
            )

        browser = AhgoraBrowser(log_callback=log_cb)
        try:
            match task_type:
                case TaskType.ADD_EMPLOYEE:
                    browser.add_employee(payload)
                case TaskType.UPDATE_EMPLOYEE:
                    browser.update_employee(payload)
                case TaskType.REMOVE_EMPLOYEE:
                    browser.remove_employee(payload)
                case TaskType.ADD_LEAVE:
                    logger.warning("Add leave automation not fully implemented yet.")
                case _:
                    logger.error(f"Unsupported task type for automation: {task_type}")
                    return False
            return True
        except Exception as e:
            logger.error(f"Browser automation failed: {str(e)}")
            raise e
        finally:
            browser.close_driver()

        return False

    async def _update_ahgora_state(self, task_type: TaskType, payload: dict):
        """
        Updates the local database Ahgora state after a successful task.
        """
        try:
            # Reconstruct Ahgora state from payload
            if task_type in [
                TaskType.ADD_EMPLOYEE,
                TaskType.UPDATE_EMPLOYEE,
                TaskType.REMOVE_EMPLOYEE,
            ]:
                emp_data = {
                    "id": str(payload.get("id")),
                    "name": payload.get("name"),
                    "position": payload.get("position"),
                    "department": payload.get("department"),
                    "admission_date": payload.get("admission_date"),
                }
                if task_type == TaskType.REMOVE_EMPLOYEE:
                    emp_data["dismissal_date"] = payload.get("dismissal_date")

                await self.repo.save_ahgora_employees_batch([emp_data])
                logger.info(
                    f"Updated Ahgora DB state for employee ID: {emp_data['id']}"
                )
            else:
                logger.info("Task type does not require Ahgora employee state update.")
        except Exception as e:
            logger.error(f"Failed to update Ahgora state: {str(e)}")
