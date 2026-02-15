import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from app.domain.entities import SyncJob, SyncResult
from app.domain.enums import SyncStatus
from app.services.sync_service import SyncService


@pytest.mark.asyncio
async def test_create_job():
    repo = MagicMock()
    repo.save_job = AsyncMock()
    service = SyncService(repo=repo)

    job = await service.create_job(triggered_by="test")

    assert job.triggered_by == "test"
    assert job.status == SyncStatus.PENDING
    repo.save_job.assert_called_once()


@pytest.mark.asyncio
async def test_run_sync_background_success():
    repo = MagicMock()
    job_id = uuid4()
    job = SyncJob(id=job_id)
    repo.get_job = AsyncMock(return_value=job)
    repo.update_job_status = AsyncMock()
    repo.add_log = AsyncMock()

    service = SyncService(repo=repo)

    # Mock _execute_sync_logic as an AsyncMock
    with patch.object(
        service,
        "_execute_sync_logic",
        new_callable=AsyncMock,
        return_value=SyncResult(success=True, status=SyncStatus.SUCCESS, message="OK"),
    ):
        await service.run_sync_background(job_id)

    repo.update_job_status.assert_any_call(job_id, SyncStatus.RUNNING)
    repo.update_job_status.assert_any_call(job_id, SyncStatus.SUCCESS, "OK")
    assert repo.add_log.call_count >= 2


@pytest.mark.asyncio
async def test_run_sync_background_failure():
    repo = MagicMock()
    job_id = uuid4()
    job = SyncJob(id=job_id)
    repo.get_job = AsyncMock(return_value=job)
    repo.update_job_status = AsyncMock()
    repo.add_log = AsyncMock()

    service = SyncService(repo=repo)

    with patch.object(
        service,
        "_execute_sync_logic",
        new_callable=AsyncMock,
        side_effect=Exception("Browser Error"),
    ):
        await service.run_sync_background(job_id)

    repo.update_job_status.assert_any_call(job_id, SyncStatus.FAILED, "Browser Error")
