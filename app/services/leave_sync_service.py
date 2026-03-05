import asyncio
import logging
import tempfile
from pathlib import Path
from uuid import UUID

import pandas as pd

from app.core.settings import settings
from app.domain.enums import AutomationTaskStatus
from app.infrastructure.automation.web.ahgora_browser import AhgoraBrowser
from app.infrastructure.db.sqlalchemy_repo import SqlAlchemyRepo

logger = logging.getLogger(__name__)


class LeaveSyncService:
    def __init__(self, repo: SqlAlchemyRepo):
        self.repo = repo

    async def execute_leaves_batch(self, job_id: UUID) -> None:
        """
        Executes all pending ADD_LEAVE tasks as a single batch using the Ahgora file importer.
        """
        logger.info(f"Starting batched leaf upload for job {job_id}")

        # 1. Fetch pending tasks
        tasks = await self.repo.get_automation_tasks_by_job(job_id)
        leave_tasks = [
            t
            for t in tasks
            if str(t.type).upper().endswith("ADD_LEAVE")
            and t.status
            in [
                AutomationTaskStatus.PENDING,
                AutomationTaskStatus.FAILED,
                AutomationTaskStatus.CANCELLED,
            ]
        ]

        if not leave_tasks:
            logger.info("No pending ADD_LEAVE tasks found.")
            return

        for t in leave_tasks:
            await self.repo.update_task_status(t.id, AutomationTaskStatus.RUNNING)
            await self.repo.add_log(
                job_id, "INFO", "Iniciando batch import de afastamento", task_id=t.id
            )

        # Build DataFrame from task payloads
        payloads = [t.payload for t in leave_tasks]
        df = pd.DataFrame(payloads)

        # 2. Run browser automation in thread
        loop = asyncio.get_running_loop()
        log_lock = asyncio.Lock()
        try:
            results = await asyncio.to_thread(
                self._run_browser_batch_import, df, job_id, loop, log_lock
            )

            # Analyze results and update task statuses
            # results is a list of dicts: [{'payload': {...}, 'status': 'success' or 'error', 'message': '...', 'index': 0}]

            for i, task in enumerate(leave_tasks):
                task_result = results[i]
                if task_result["status"] == "success":
                    await self.repo.update_task_status(
                        task.id,
                        AutomationTaskStatus.SUCCESS,
                        message=task_result["message"],
                    )
                    await self.repo.add_log(
                        job_id,
                        "INFO",
                        "Afastamento importado com sucesso",
                        task_id=task.id,
                    )
                else:
                    await self.repo.update_task_status(
                        task.id,
                        AutomationTaskStatus.FAILED,
                        message=task_result["message"],
                    )
                    await self.repo.add_log(
                        job_id,
                        "ERROR",
                        f"Falha na importação: {task_result['message']}",
                        task_id=task.id,
                    )

        except Exception as e:
            logger.exception(f"Batched leaf sync failed catastrophically: {e}.")
            for t in leave_tasks:
                await self.repo.update_task_status(
                    t.id, AutomationTaskStatus.FAILED, message=str(e)
                )
                await self.repo.add_log(
                    job_id, "ERROR", f"Falha crítica no lote: {str(e)}", task_id=t.id
                )

        await self.repo.evaluate_and_update_job_status(job_id)

    def _run_browser_batch_import(
        self,
        df: pd.DataFrame,
        job_id: UUID,
        loop: asyncio.AbstractEventLoop,
        log_lock: asyncio.Lock,
    ) -> list[dict]:
        """
        Sync execution of the browser automation for leaves batch.
        """

        async def safe_log(level: str, msg: str):
            async with log_lock:
                await self.repo.add_log(job_id, level, msg)

        def log_cb(level: str, msg: str):
            asyncio.run_coroutine_threadsafe(safe_log(level, msg), loop)

        results = []
        for i, row in df.iterrows():
            results.append(
                {
                    "payload": row.to_dict(),
                    "status": "success",
                    "message": "",
                    "index": i,
                }
            )

        browser = AhgoraBrowser(
            log_callback=log_cb, headless=settings.HEADLESS_MODE_TASKS
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                temp_path = Path(temp_dir)

                initial_file = temp_path / "upload_leaves_initial.csv"
                final_file = temp_path / "upload_leaves_final.csv"

                # Ensure required columns exist, mapping from payload back to UPLOAD_LEAVES_COLUMNS
                upload_cols = settings.UPLOAD_LEAVES_COLUMNS

                # Filter/Map columns
                export_df = df.copy()
                for col in upload_cols:
                    if col not in export_df.columns:
                        export_df[col] = ""
                    if col in ["start_date", "end_date"]:
                        export_df[col] = pd.to_datetime(
                            export_df[col], format="mixed", dayfirst=True
                        )
                        export_df[col] = export_df[col].dt.strftime("%d/%m/%Y")

                # 1. Generate initial CSV
                export_df[upload_cols].to_csv(
                    initial_file, index=False, header=False, sep=","
                )

                # 2. Upload initial CSV
                browser.upload_leaves_file(str(initial_file))

                # 3. Extract errors
                import_errors = browser.extract_import_errors()

                # import_errors format: [{'row': 10, 'error': 'Intersecção...'}]
                error_rows = {err["row"] for err in import_errors}

                # Mark errors in results
                # Note: Ahgora row errors are 1-indexed.
                for err in import_errors:
                    idx = err["row"] - 1
                    if 0 <= idx < len(results):
                        results[idx]["status"] = "error"
                        results[idx]["message"] = err["error"]

                # 4. Filter DF
                # Drop rows that had errors (1-indexed matching)
                valid_indices = [
                    i for i in range(len(export_df)) if (i + 1) not in error_rows
                ]

                if not valid_indices:
                    log_cb("INFO", "No leaves to import")
                    for result in results:
                        result["status"] = "success"
                    return results

                final_df = export_df.iloc[valid_indices]

                # 5. Generate final CSV
                final_df[upload_cols].to_csv(
                    final_file, index=False, header=False, sep=","
                )

                # 6. Upload final CSV and Confirm
                browser.upload_leaves_file(str(final_file))

                # Optionally wait, then confirm
                browser.confirm_import()

                # Update leaves results
                for result in results:
                    if (
                        "Intersecção com afastamento existente no registro".lower().strip()
                        in result["message"].lower().strip()
                    ):
                        result["status"] = "success"

                return results

            except Exception as e:
                log_cb("ERROR", f"Batch import process failed: {e}")
                for result in results:
                    result["status"] = "failed"
                raise e
            finally:
                browser.close_driver()
