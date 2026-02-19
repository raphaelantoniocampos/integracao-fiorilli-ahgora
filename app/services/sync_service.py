from datetime import datetime, timedelta
import asyncio
import logging
from typing import Optional, Dict, Any, List, Tuple
from uuid import UUID
import re
import unicodedata
from pathlib import Path
import pandas as pd
import numpy as np

from app.core.settings import settings
from app.domain.entities import SyncJob, SyncResult, SyncLog, AutomationTask, AutomationTaskType, AutomationTaskStatus
from app.domain.enums import SyncStatus
from app.infrastructure.automation.web.fiorilli_browser import FiorilliBrowser
from app.infrastructure.automation.web.ahgora_browser import AhgoraBrowser
from app.infrastructure.db.sqlalchemy_repo import SqlAlchemyRepo
from app.core.task_registry import task_registry
from app.core.file_manager import FileManager

FIORILLI_EMPLOYEES_COLUMNS = settings.FIORILLI_EMPLOYEES_COLUMNS
AHGORA_EMPLOYEES_COLUMNS = settings.AHGORA_EMPLOYEES_COLUMNS
COLUMNS_TO_VERIFY_CHANGE = settings.COLUMNS_TO_VERIFY_CHANGE
LEAVES_COLUMNS = settings.LEAVES_COLUMNS
UPLOAD_LEAVES_COLUMNS = settings.UPLOAD_LEAVES_COLUMNS
PT_MONTHS = settings.PT_MONTHS
EXCEPTIONS_AND_TYPOS = settings.EXCEPTIONS_AND_TYPOS

FIORILLI_DIR = FileManager.FIORILLI_DIR
AHGORA_DIR = FileManager.AHGORA_DIR
DATA_DIR = settings.DATA_DIR

logger = logging.getLogger(__name__)


class SyncService:
    MAX_JOB_RETRIES = 3

    def __init__(self, repo: SqlAlchemyRepo):
        self.repo = repo
        self._db_lock = asyncio.Lock()

    @staticmethod
    async def run_sync_task_standalone(job_id: UUID):
        """
        Static method to run a sync task with its own database session.
        This is used for background tasks to avoid session closure issues.
        """
        from app.core.database import async_session_factory

        async with async_session_factory() as session:
            repo = SqlAlchemyRepo(session)
            service = SyncService(repo)
            await service.run_sync_background(job_id)

    async def create_job(self, triggered_by: str = "api") -> SyncJob:
        job = SyncJob(triggered_by=triggered_by)
        async with self._db_lock:
            await self.repo.save_job(job)
        return job

    async def get_job(self, job_id: UUID) -> SyncJob:
        return await self.repo.get_job(job_id)

    async def list_jobs(self) -> list[SyncJob]:
        return await self.repo.list_jobs()

    async def get_job_logs(self, job_id: UUID) -> list[SyncLog]:
        return await self.repo.get_job_logs(job_id)

    async def get_automation_tasks(self, job_id: UUID) -> list[AutomationTask]:
        return await self.repo.get_automation_tasks_by_job(job_id)

    async def list_automation_tasks(
        self, status: Optional[AutomationTaskStatus] = None
    ) -> list[AutomationTask]:
        return await self.repo.get_all_automation_tasks(status)

    async def run_sync_background(self, job_id: UUID):
        job = await self.repo.get_job(job_id)
        if not job:
            logger.error(f"Job {job_id} not found for execution")
            return

        async with self._db_lock:
            await self.repo.update_job_status(job_id, SyncStatus.RUNNING)
        await self._log(job_id, "INFO", f"Started background sync for job {job_id}")

        # Register the current task
        current_task = asyncio.current_task()
        task_registry.register(job_id, current_task)

        try:
            # Execute sync logic (now properly async and handles its own threading)
            result = await self._execute_sync_logic(job_id)

            if result.success:
                async with self._db_lock:
                    await self.repo.update_job_status(job_id, SyncStatus.SUCCESS, result.message)
                await self._log(
                    job_id,
                    "INFO",
                    f"Job {job_id} finished successfully: {result.message}",
                )
            else:
                # If it failed, check if we should retry (job level)
                await self._handle_job_retry(job, error_msg=result.message)

        except asyncio.CancelledError:
            logger.info(f"Job {job_id} was cancelled")
            try:
                async with self._db_lock:
                    await self.repo.update_job_status(
                        job_id, SyncStatus.CANCELLED, "Job was cancelled by user"
                    )
                await self._log(job_id, "WARNING", "Job was cancelled")
            except Exception as e:
                logger.error(f"Failed to update status for cancelled job {job_id}: {e}")
            raise  # Re-raise to finalize task cancellation

        except Exception as e:
            logger.exception(f"Unhandled error in job {job_id}")
            # Ensure status is UPDATED even if something very bad happens
            try:
                # Handle retry even for unhandled errors
                await self._handle_job_retry(job, error_msg=str(e))
            except Exception as inner_e:
                logger.error(f"Failed to handle retry for job {job_id}: {inner_e}")
        finally:
            task_registry.unregister(job_id)

    async def _handle_job_retry(
        self, job: SyncJob, error_msg: Optional[str] = None
    ):
        """Calculates next retry and updates job if retries are available."""
        if job.retry_count >= self.MAX_JOB_RETRIES:
            final_msg = error_msg or "Max retries reached"
            async with self._db_lock:
                await self.repo.update_job_status(job.id, SyncStatus.FAILED, final_msg)
            await self._log(job.id, "ERROR", f"Sync failed permanently: {final_msg}")
            return

        # Exponential backoff: 5m, 30m, 2h
        backoffs = [
            timedelta(minutes=5),
            timedelta(minutes=30),
            timedelta(hours=2),
        ]

        delay = backoffs[job.retry_count]  # current retry_count is 0..2
        next_retry = datetime.now() + delay

        await self.repo.increment_job_retry(job.id, next_retry)
        await self._log(
            job.id,
            "WARNING",
            f"Job failed. Scaled retry {job.retry_count + 1}/{self.MAX_JOB_RETRIES} scheduled for {next_retry}",
        )

    async def kill_job(self, job_id: UUID) -> bool:
        """Cancels a running job and updates its status to CANCELLED."""
        logger.info(f"Attempting to kill job {job_id}...")
        task = task_registry.get_task(job_id)
        
        # Check if job exists in DB and is in a state that can be cancelled
        job = await self.repo.get_job(job_id)
        if not job:
            logger.warning(f"Kill failed: Job {job_id} not found in database")
            return False

        is_zombie = task is None and job.status == SyncStatus.RUNNING
        
        if not task and not is_zombie:
            active_tasks = task_registry.get_all_tasks()
            logger.warning(
                f"Kill skipped: Job {job_id} is {job.status} and not in registry. "
                f"Currently registered: {list(active_tasks.keys())}"
            )
            return False

        if is_zombie:
            logger.info(f"Cleaning up zombie job {job_id} (marked RUNNING in DB but missing from registry)")
        else:
            logger.info(f"Killing active task for job {job_id}")
            task.cancel()

        # Update the status to CANCELLED
        async with self._db_lock:
            await self.repo.update_job_status(
                job_id, SyncStatus.CANCELLED, "Termination requested by user"
            )
            await self._log(job_id, "WARNING", "Job was killed/cancelled by user request")

        return True

    async def kill_all_jobs(self) -> int:
        """Cancels all active sync jobs in memory and cleans up running jobs in DB."""
        # 1. Kill tasks in registry
        tasks = task_registry.get_all_tasks()
        logger.info(f"Attempting to kill all {len(tasks)} registered tasks: {list(tasks.keys())}")
        
        count = 0
        registry_job_ids = set()
        for job_id_str in tasks.keys():
            job_id = UUID(job_id_str)
            registry_job_ids.add(job_id)
            if await self.kill_job(job_id):
                count += 1

        # 2. Cleanup any other jobs marked as RUNNING in the database
        jobs = await self.repo.list_jobs()
        for job in jobs:
            if job.status == SyncStatus.RUNNING and job.id not in registry_job_ids:
                logger.info(f"Cleaning up untracked RUNNING job {job.id} from database")
                if await self.kill_job(job.id):
                    count += 1
        
        return count

    async def _log(self, job_id: UUID, level: str, message: str):
        # Log to standard logging
        log_func = getattr(logger, level.lower(), logger.info)
        log_func(f"Job {job_id}: {message}")

        # Persist to DB
        async with self._db_lock:
            await self.repo.add_log(job_id, level, message)

    async def _execute_sync_logic(self, job_id: UUID) -> SyncResult:
        async def run_download_task_with_retries(
            browser_class, method_name, description, max_retries=3
        ):
            last_error = None
            for attempt in range(1, max_retries + 1):
                await self._log(
                    job_id,
                    "INFO",
                    f"Starting {description} (Attempt {attempt}/{max_retries})",
                )

                def blocking_wrapper():
                    browser = browser_class()
                    try:
                        getattr(browser, method_name)()
                    finally:
                        browser.close_driver()

                try:
                    await asyncio.to_thread(blocking_wrapper)
                    await self._log(
                        job_id, "INFO", f"Completed {description} on attempt {attempt}"
                    )
                    return True  # Success
                except Exception as e:
                    last_error = e
                    await self._log(
                        job_id,
                        "WARNING",
                        f"Attempt {attempt}/{max_retries} for {description} failed: {str(e)}",
                    )
                    if attempt < max_retries:
                        await asyncio.sleep(2)  # Short wait before retry

            await self._log(
                job_id,
                "ERROR",
                f"All {max_retries} attempts failed for {description}: {str(last_error)}",
            )
            raise last_error

        try:
            if settings.HEADLESS_MODE:
                await self._log(
                    job_id, "INFO", "Running tasks concurrently (Headless Mode)"
                )
                await asyncio.gather(
                    run_download_task_with_retries(
                        FiorilliBrowser,
                        "download_employees",
                        "Fiorilli employees download",
                    ),
                    run_download_task_with_retries(
                        FiorilliBrowser, "download_leaves", "Fiorilli leaves download"
                    ),
                    run_download_task_with_retries(
                        AhgoraBrowser, "download_employees", "Ahgora employees download"
                    ),
                )
            else:
                await self._log(job_id, "INFO", "Running tasks sequentially (UI Mode)")
                await run_download_task_with_retries(
                    FiorilliBrowser, "download_employees", "Fiorilli employees download"
                )
                await run_download_task_with_retries(
                    FiorilliBrowser, "download_leaves", "Fiorilli leaves download"
                )
                await run_download_task_with_retries(
                    AhgoraBrowser, "download_employees", "Ahgora employees download"
                )

            # 5. Run analysis and create tasks
            await self._run_analysis_and_create_tasks(job_id)

            return SyncResult(
                success=True,
                status=SyncStatus.SUCCESS,
                message="Sync completed (Fiorilli & Ahgora)",
            )
        except Exception as e:
            logger.error(f"Sync failed after retries: {e}")
            return SyncResult(
                success=False,
                status=SyncStatus.FAILED,
                message=f"Sync failed: {str(e)}",
            )

    async def _run_analysis_and_create_tasks(self, job_id: UUID):
        try:
            await self._log(job_id, "INFO", "Starting data analysis and task creation")

            # 1. Process downloads (move files to expected locations)
            await self._log(job_id, "INFO", "Moving downloaded files to data directory...")
            await asyncio.to_thread(FileManager.move_downloads_to_data_dir)

            # 2. Get data
            await self._log(job_id, "INFO", "Loading employee data from files...")
            fiorilli_employees, ahgora_employees = await self._get_employees_data(job_id)
            
            await self._log(job_id, "INFO", "Loading leave data from files...")
            last_leaves, all_leaves = await self._get_leaves_data(job_id)

            leave_codes_path = DATA_DIR / "leave_codes.csv"
            if leave_codes_path.exists():
                await self._log(job_id, "INFO", "Enriching leave data with codes...")
                leave_codes = await asyncio.to_thread(
                    self._read_csv, leave_codes_path, columns=["cod", "desc"]
                )
                all_leaves = await self._get_view_leaves(
                    leaves_df=all_leaves,
                    fiorilli_employees=fiorilli_employees,
                    leave_codes=leave_codes,
                )

            # 3. Generate Task Dataframes
            await self._log(job_id, "INFO", "Generating task dataframes (comparing datasets)...")
            (
                new_employees_df,
                dismissed_employees_df,
                changed_employees_df,
                new_leaves_df,
            ) = await self._generate_tasks_dfs(
                job_id,
                fiorilli_employees=fiorilli_employees,
                ahgora_employees=ahgora_employees,
                last_leaves=last_leaves,
                all_leaves=all_leaves,
            )

            # 4. Create and persist AutomationTasks
            await self._log(job_id, "INFO", "Persisting automation tasks to database...")
            await self._create_automation_tasks(
                job_id,
                new_employees_df,
                dismissed_employees_df,
                changed_employees_df,
                new_leaves_df,
            )

            await self._log(job_id, "INFO", "Data analysis and task creation completed successfully")
        except Exception as e:
            error_msg = f"Critical error during analysis phase: {str(e)}"
            logger.error(error_msg, exc_info=True)
            await self._log(job_id, "ERROR", error_msg)
            raise

    async def _get_employees_data(self, job_id: UUID) -> Tuple[pd.DataFrame, pd.DataFrame]:
        try:
            raw_fiorilli_path = FIORILLI_DIR / "raw_employees.txt"
            raw_ahgora_path = AHGORA_DIR / "raw_employees.csv"

            if not raw_fiorilli_path.exists():
                await self._log(job_id, "WARNING", f"Fiorilli file not found: {raw_fiorilli_path}")
            if not raw_ahgora_path.exists():
                await self._log(job_id, "WARNING", f"Ahgora file not found: {raw_ahgora_path}")

            if not raw_fiorilli_path.exists() or not raw_ahgora_path.exists():
                return pd.DataFrame(), pd.DataFrame()

            fiorilli_employees = await asyncio.to_thread(self._read_csv, raw_fiorilli_path)
            ahgora_employees = await asyncio.to_thread(self._read_csv, raw_ahgora_path)

            await self._log(job_id, "INFO", f"Loaded {len(fiorilli_employees)} Fiorilli employees and {len(ahgora_employees)} Ahgora employees")
            return fiorilli_employees, ahgora_employees
        except Exception as e:
            await self._log(job_id, "ERROR", f"Error getting employee data: {str(e)}")
            return pd.DataFrame(), pd.DataFrame()

    async def _get_leaves_data(self, job_id: UUID) -> Tuple[pd.DataFrame, pd.DataFrame]:
        try:
            last_leaves_path = FIORILLI_DIR / "leaves.csv"
            raw_leaves_path = FIORILLI_DIR / "raw_leaves.txt"
            raw_vacations_path = FIORILLI_DIR / "raw_vacations.txt"

            last_leaves = pd.DataFrame()
            if last_leaves_path.exists():
                last_leaves = await asyncio.to_thread(self._read_csv, last_leaves_path)
                await self._log(job_id, "INFO", f"Loaded {len(last_leaves)} historical leaves")

            all_leaves_list = []
            if raw_vacations_path.exists():
                df_vac = await asyncio.to_thread(self._read_csv, raw_vacations_path)
                all_leaves_list.append(df_vac)
                await self._log(job_id, "INFO", f"Loaded {len(df_vac)} new vacations")
            
            if raw_leaves_path.exists():
                df_leaves = await asyncio.to_thread(self._read_csv, raw_leaves_path)
                all_leaves_list.append(df_leaves)
                await self._log(job_id, "INFO", f"Loaded {len(df_leaves)} new leaves/absences")

            all_leaves = pd.concat(all_leaves_list) if all_leaves_list else pd.DataFrame()
            if not all_leaves.empty:
                await self._log(job_id, "INFO", f"Total combined leaves for process: {len(all_leaves)}")
            
            return last_leaves, all_leaves
        except Exception as e:
            await self._log(job_id, "ERROR", f"Error getting leave data: {str(e)}")
            return pd.DataFrame(), pd.DataFrame()

    def _read_csv(
        self,
        path: Path,
        sep: str = ",",
        encoding: str = "utf-8",
        header: str | None = "infer",
        columns: list[str] = [],
    ) -> pd.DataFrame:
        df = pd.DataFrame()
        try:
            match path.name:
                case "raw_employees.txt":
                    df = pd.read_csv(
                        path,
                        sep="|",
                        encoding="latin1",
                        index_col=False,
                        header=None,
                    )
                    df = self._prepare_dataframe(df, columns=FIORILLI_EMPLOYEES_COLUMNS)

                case "raw_employees.csv":
                    df = pd.read_csv(path, index_col=False, header=None)
                    df = self._prepare_dataframe(df, columns=AHGORA_EMPLOYEES_COLUMNS)

                case "leaves.csv":
                    df = pd.read_csv(path, index_col=False, header=None)
                    df = self._prepare_dataframe(df, columns=LEAVES_COLUMNS)

                case "raw_vacations.txt" | "raw_leaves.txt":
                    df = pd.read_csv(path, index_col=False, header=None)
                    df = self._prepare_dataframe(df, columns=UPLOAD_LEAVES_COLUMNS)

                case _:
                    df = pd.read_csv(
                        path,
                        sep=sep,
                        encoding=encoding,
                        index_col=False,
                        header=header,
                    )
                    if columns:
                        df = self._prepare_dataframe(df, columns=columns)
        except Exception as e:
            logger.error(f"Error reading CSV {path}: {e}")
            return pd.DataFrame()

        return df

    def _prepare_dataframe(
        self,
        df: pd.DataFrame,
        columns: list[str] = [],
    ) -> pd.DataFrame:
        try:
            if columns:
                if len(df.columns) != len(columns):
                    logger.warning(f"Column mismatch: expected {len(columns)} got {len(df.columns)}")
                df.columns = columns[:len(df.columns)] # defensive

            for col in df.columns:
                if "date" in col:
                    df[col] = df[col].apply(self._convert_date)
                    df[col] = pd.to_datetime(
                        df[col],
                        dayfirst=True,
                        format="%d/%m/%Y",
                        errors="coerce",
                    )
                    df[col] = df[col].dt.strftime("%d/%m/%Y")

            if "cpf" in df.columns:
                df["cpf"] = df["cpf"].fillna("").astype(str).str.zfill(11)

            if "cod" in df.columns:
                df["cod"] = df["cod"].fillna("").astype(str).str.zfill(3)

            if "name" in df.columns:
                df["name"] = df["name"].str.strip().str.upper()

            if "id" in df.columns:
                df["id"] = df["id"].astype(str).str.zfill(6)

            return df
        except Exception as e:
            logger.error(f"Error preparing dataframe: {e}")
            raise

    def _convert_date(self, date_str: str):
        if pd.isna(date_str) or not isinstance(date_str, str) or date_str.strip() == "":
            return pd.NaT

        partes = date_str.split(", ")
        if len(partes) > 1:
            date_str = partes[1]

        for pt, en in PT_MONTHS.items():
            date_str = date_str.replace(f"{pt}/", f"{en}/")

        formats = ["%d/%b/%Y", "%d/%m/%Y", "%d/%b/%Y %H:%M"]
        for fmt in formats:
            try:
                return pd.to_datetime(date_str, format=fmt, errors="raise")
            except ValueError:
                continue

        return pd.to_datetime(date_str, format="ISO8601", errors="coerce")

    def _normalize_text(self, text):
        if pd.isna(text):
            return np.nan
        text = str(" ".join(re.split(r"\s+", text, flags=re.UNICODE)))
        normalized = (
            unicodedata.normalize("NFKD", text)
            .encode("ASCII", "ignore")
            .decode("ASCII")
        )
        normalized = EXCEPTIONS_AND_TYPOS.get(normalized, normalized)
        return normalized.lower().strip()

    async def _generate_tasks_dfs(
        self,
        job_id: UUID,
        fiorilli_employees: pd.DataFrame,
        ahgora_employees: pd.DataFrame,
        last_leaves: pd.DataFrame,
        all_leaves: pd.DataFrame,
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        if fiorilli_employees.empty:
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

        # Dismissed logic
        fiorilli_dismissed_df = fiorilli_employees[
            fiorilli_employees["dismissal_date"].notna()
        ]
        fiorilli_dismissed_ids = set(fiorilli_dismissed_df["id"])

        ahgora_dismissed_df = ahgora_employees[
            ahgora_employees["dismissal_date"].notna()
        ]
        ahgora_dismissed_ids = set(ahgora_dismissed_df["id"])

        dismissed_ids = ahgora_dismissed_ids | fiorilli_dismissed_ids

        fiorilli_active_employees = fiorilli_employees[
            ~fiorilli_employees["id"].isin(dismissed_ids)
        ]

        # New employees
        ahgora_ids = set(ahgora_employees["id"])
        new_employees_df = fiorilli_active_employees[
            ~fiorilli_active_employees["id"].isin(ahgora_ids)
        ]
        new_employees_df = new_employees_df[
            new_employees_df["binding"] != "AUXILIO RECLUSAO"
        ]

        # Dismissed employees
        dismissed_employees_df = ahgora_employees[
            ahgora_employees["id"].isin(fiorilli_dismissed_ids)
            & ~ahgora_employees["id"].isin(ahgora_dismissed_ids)
        ]
        if not dismissed_employees_df.empty:
            dismissed_employees_df = dismissed_employees_df.drop(columns=["dismissal_date"])
            dismissed_employees_df = dismissed_employees_df.merge(
                fiorilli_dismissed_df[["id", "dismissal_date"]],
                on="id",
                how="left",
            )
            dismissed_employees_df["dismissal_date_dt"] = pd.to_datetime(
                dismissed_employees_df["dismissal_date"],
                format="%d/%m/%Y",
            )
            today = datetime.now()
            dismissed_employees_df = dismissed_employees_df[
                dismissed_employees_df["dismissal_date_dt"] <= today
            ]
            dismissed_employees_df = dismissed_employees_df.drop(columns=["dismissal_date_dt"])

        # Changed employees
        changed_employees_df = await self._get_changed_employees_df(
            fiorilli_active_employees, ahgora_employees
        )

        # New leaves
        new_leaves_df = await self._get_new_leaves_df(last_leaves, all_leaves)

        return (
            new_employees_df,
            dismissed_employees_df,
            changed_employees_df,
            new_leaves_df,
        )

    async def _get_changed_employees_df(
        self,
        fiorilli_active_employees: pd.DataFrame,
        ahgora_employees: pd.DataFrame,
    ) -> pd.DataFrame:
        merged = fiorilli_active_employees.merge(
            ahgora_employees,
            on="id",
            suffixes=("_fiorilli", "_ahgora"),
            how="inner",
        )

        for col in COLUMNS_TO_VERIFY_CHANGE:
            if f"{col}_fiorilli" in merged:
                merged[f"{col}_fiorilli_norm"] = merged[f"{col}_fiorilli"].apply(
                    self._normalize_text
                )
            if f"{col}_ahgora" in merged:
                merged[f"{col}_ahgora_norm"] = merged[f"{col}_ahgora"].apply(
                    self._normalize_text
                )

        change_conditions = []
        placeholder = "___NULL___"
        for col in COLUMNS_TO_VERIFY_CHANGE:
            f_col = f"{col}_fiorilli_norm"
            a_col = f"{col}_ahgora_norm"
            if f_col in merged and a_col in merged:
                condition = merged[f_col].fillna(placeholder) != merged[a_col].fillna(
                    placeholder
                )
                change_conditions.append(condition)

        if not change_conditions:
            return pd.DataFrame()

        combined_condition = change_conditions[0]
        for cond in change_conditions[1:]:
            combined_condition |= cond

        return merged[combined_condition]

    async def _get_new_leaves_df(
        self,
        last_leaves: pd.DataFrame,
        all_leaves: pd.DataFrame,
    ) -> pd.DataFrame:
        if all_leaves.empty:
            return pd.DataFrame()

        for df in [last_leaves, all_leaves]:
            if df.empty:
                continue
            for col in ["start_date", "end_date"]:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], format="%d/%m/%Y", errors="coerce")
            
            # Apply normalize text for normalization
            for col in df.columns:
                if df[col].dtype == object:
                    df[col] = df[col].replace(EXCEPTIONS_AND_TYPOS)

        if last_leaves.empty:
            return all_leaves

        merged = pd.merge(
            last_leaves,
            all_leaves,
            how="outer",
            indicator=True,
        )
        return merged[merged["_merge"] == "right_only"].drop("_merge", axis=1)

    async def _get_view_leaves(
        self,
        leaves_df: pd.DataFrame,
        fiorilli_employees: pd.DataFrame,
        leave_codes: pd.DataFrame,
    ) -> pd.DataFrame:
        if leaves_df.empty:
            return leaves_df

        leaves_df["start_date_dt"] = pd.to_datetime(
            leaves_df["start_date"], format="%d/%m/%Y", errors="coerce"
        )
        leaves_df["end_date_dt"] = pd.to_datetime(
            leaves_df["end_date"], format="%d/%m/%Y", errors="coerce"
        )

        leaves_df = leaves_df.merge(
            fiorilli_employees[["id", "name"]], on="id", how="left"
        )
        leaves_df = leaves_df.merge(
            leave_codes[["cod", "desc"]], on="cod", how="left"
        ).rename(columns={"desc": "cod_name"})

        leaves_df["duration"] = (
            leaves_df["end_date_dt"] - leaves_df["start_date_dt"]
        ).dt.days + 1
        leaves_df["duration"] = leaves_df["duration"].clip(lower=1)

        # Ensure all columns exist
        for col in LEAVES_COLUMNS:
            if col not in leaves_df.columns:
                leaves_df[col] = None

        return leaves_df[LEAVES_COLUMNS]

    async def _create_automation_tasks(
        self,
        job_id: UUID,
        new_employees_df: pd.DataFrame,
        dismissed_employees_df: pd.DataFrame,
        changed_employees_df: pd.DataFrame,
        new_leaves_df: pd.DataFrame,
    ):
        tasks_to_create = []

        # Helper to create payload
        def df_to_payloads(df: pd.DataFrame) -> List[Dict[str, Any]]:
            return [row.to_dict() for _, row in df.iterrows()]

        if not new_employees_df.empty:
            for payload in df_to_payloads(new_employees_df):
                tasks_to_create.append(
                    AutomationTask(
                        job_id=job_id,
                        type=AutomationTaskType.ADD_EMPLOYEE,
                        payload=payload,
                    )
                )

        if not dismissed_employees_df.empty:
            for payload in df_to_payloads(dismissed_employees_df):
                tasks_to_create.append(
                    AutomationTask(
                        job_id=job_id,
                        type=AutomationTaskType.REMOVE_EMPLOYEE,
                        payload=payload,
                    )
                )

        if not changed_employees_df.empty:
            # We might want to filter only some columns for payload or keep all
            for payload in df_to_payloads(changed_employees_df):
                tasks_to_create.append(
                    AutomationTask(
                        job_id=job_id,
                        type=AutomationTaskType.UPDATE_EMPLOYEE,
                        payload=payload,
                    )
                )

        if not new_leaves_df.empty:
            for payload in df_to_payloads(new_leaves_df):
                tasks_to_create.append(
                    AutomationTask(
                        job_id=job_id,
                        type=AutomationTaskType.ADD_LEAVE,
                        payload=payload,
                    )
                )

        # Save all tasks
        for task in tasks_to_create:
            await self.repo.save_automation_task(task)

        await self._log(job_id, "INFO", f"Created {len(tasks_to_create)} automation tasks")

