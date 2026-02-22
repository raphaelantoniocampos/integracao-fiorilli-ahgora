import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, AsyncMock, patch
from uuid import uuid4
from app.main import app
from app.core.database import get_db
from app.api.endpoints import get_service, get_execution_service
from app.domain.entities import SyncJob, SyncLog, AutomationTask
from app.domain.enums import AutomationTaskStatus, AutomationTaskType

# Mock database dependency
mock_db = MagicMock()


@pytest.fixture
def client():
    # Override get_db dependency
    app.dependency_overrides[get_db] = lambda: mock_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@patch("app.api.endpoints.SyncService")
def test_run_sync_job(mock_service_class, client):
    mock_service = mock_service_class.return_value
    job_id = uuid4()
    mock_service.create_job = AsyncMock(
        return_value=SyncJob(id=job_id, triggered_by="api")
    )
    # mock background task isn't strictly necessary for the service mock,
    # but the endpoint triggers BackgroundTasks.add_task

    # Override get_service dependency specially to inject the mock instance
    app.dependency_overrides[get_service] = lambda: mock_service

    response = client.post("/api/sync/run")
    assert response.status_code == 200
    assert response.json()["id"] == str(job_id)
    mock_service.create_job.assert_called_once()

    app.dependency_overrides.pop(get_service, None)


@patch("app.api.endpoints.SyncService")
def test_list_jobs(mock_service_class, client):
    mock_service = mock_service_class.return_value
    job_id = uuid4()
    mock_service.list_jobs = AsyncMock(
        return_value=[SyncJob(id=job_id, triggered_by="api")]
    )
    app.dependency_overrides[get_service] = lambda: mock_service

    response = client.get("/api/sync/jobs")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == str(job_id)

    app.dependency_overrides.pop(get_service, None)


@patch("app.api.endpoints.SyncService")
def test_kill_job_success(mock_service_class, client):
    mock_service = mock_service_class.return_value
    job_id = uuid4()
    mock_service.kill_job = AsyncMock(return_value=True)
    app.dependency_overrides[get_service] = lambda: mock_service

    response = client.post(f"/api/sync/jobs/{job_id}/kill")
    assert response.status_code == 200
    assert "Kill signal sent" in response.json()["message"]

    app.dependency_overrides.pop(get_service, None)


@patch("app.api.endpoints.SyncService")
def test_kill_job_not_found(mock_service_class, client):
    mock_service = mock_service_class.return_value
    job_id = uuid4()
    mock_service.kill_job = AsyncMock(return_value=False)
    app.dependency_overrides[get_service] = lambda: mock_service

    response = client.post(f"/api/sync/jobs/{job_id}/kill")
    assert response.status_code == 404

    app.dependency_overrides.pop(get_service, None)


@patch("app.api.endpoints.SyncService")
def test_get_job_logs(mock_service_class, client):
    mock_service = mock_service_class.return_value
    job_id = uuid4()
    logs = [SyncLog(id=1, job_id=job_id, level="INFO", message="Test Log")]
    mock_service.get_job_logs = AsyncMock(return_value=logs)
    app.dependency_overrides[get_service] = lambda: mock_service

    response = client.get(f"/api/sync/jobs/{job_id}/logs")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["message"] == "Test Log"

    app.dependency_overrides.pop(get_service, None)


@patch("app.api.endpoints.SyncService")
def test_get_automation_tasks(mock_service_class, client):
    mock_service = mock_service_class.return_value
    job_id = uuid4()
    task = AutomationTask(
        id=uuid4(),
        job_id=job_id,
        type=AutomationTaskType.ADD_EMPLOYEE,
        status=AutomationTaskStatus.PENDING,
        payload={},
    )
    mock_service.get_automation_tasks = AsyncMock(return_value=[task])
    app.dependency_overrides[get_service] = lambda: mock_service

    response = client.get(f"/api/sync/jobs/{job_id}/tasks")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["type"] == AutomationTaskType.ADD_EMPLOYEE.value

    app.dependency_overrides.pop(get_service, None)


@patch("app.api.endpoints.SyncService")
def test_list_automation_tasks(mock_service_class, client):
    mock_service = mock_service_class.return_value
    task = AutomationTask(
        id=uuid4(),
        job_id=uuid4(),
        type=AutomationTaskType.ADD_EMPLOYEE,
        status=AutomationTaskStatus.PENDING,
        payload={},
    )
    mock_service.list_automation_tasks = AsyncMock(return_value=[task])
    app.dependency_overrides[get_service] = lambda: mock_service

    response = client.get("/api/sync/tasks")
    assert response.status_code == 200
    assert len(response.json()) == 1

    app.dependency_overrides.pop(get_service, None)


@patch("app.api.endpoints.task_registry")
@patch("asyncio.Task")
def test_get_registry_diagnostics(mock_task, mock_registry, client):
    mock_registry.get_all_tasks.return_value = {uuid4(): mock_task}

    response = client.get("/api/sync/diagnostics/registry")
    assert response.status_code == 200
    assert response.json()["active_task_count"] == 1


@patch("app.api.endpoints.TaskExecutionService")
def test_execute_task(mock_exec_service_class, client):
    mock_exec_service = mock_exec_service_class.return_value
    task_id = uuid4()

    app.dependency_overrides[get_execution_service] = lambda: mock_exec_service

    response = client.post(f"/api/sync/tasks/{task_id}/execute")
    assert response.status_code == 200
    assert "triggered" in response.json()["message"]

    # Ensure it's passed off to background tasks; since we mock the service, the background
    # task will just try to call mock_exec_service.execute_task(task_id).

    app.dependency_overrides.pop(get_execution_service, None)


@patch("app.api.endpoints.TaskExecutionService")
def test_execute_batch_tasks(mock_exec_service_class, client):
    mock_exec_service = mock_exec_service_class.return_value
    job_id = uuid4()
    task_type = "ADD_EMPLOYEE"

    app.dependency_overrides[get_execution_service] = lambda: mock_exec_service

    response = client.post(
        "/api/sync/tasks/batch/execute",
        params={"job_id": str(job_id), "task_type": task_type},
    )
    assert response.status_code == 200, response.json()
    assert task_type in response.json()["message"]

    app.dependency_overrides.pop(get_execution_service, None)


@patch("app.api.endpoints.TaskExecutionService")
def test_cancel_task_success(mock_exec_service_class, client):
    mock_exec_service = mock_exec_service_class.return_value
    task_id = uuid4()
    mock_exec_service.cancel_task = AsyncMock(return_value=True)

    app.dependency_overrides[get_execution_service] = lambda: mock_exec_service

    response = client.post(f"/api/sync/tasks/{task_id}/cancel")
    assert response.status_code == 200
    assert "sucesso" in response.json()["message"]

    app.dependency_overrides.pop(get_execution_service, None)


@patch("app.api.endpoints.TaskExecutionService")
def test_cancel_task_failure(mock_exec_service_class, client):
    mock_exec_service = mock_exec_service_class.return_value
    task_id = uuid4()
    mock_exec_service.cancel_task = AsyncMock(return_value=False)

    app.dependency_overrides[get_execution_service] = lambda: mock_exec_service

    response = client.post(f"/api/sync/tasks/{task_id}/cancel")
    assert response.status_code == 400

    app.dependency_overrides.pop(get_execution_service, None)


@patch("app.api.endpoints.TaskExecutionService")
def test_cancel_batch_tasks(mock_exec_service_class, client):
    mock_exec_service = mock_exec_service_class.return_value
    job_id = uuid4()
    task_type = "ADD_EMPLOYEE"
    mock_exec_service.cancel_batch = AsyncMock()

    app.dependency_overrides[get_execution_service] = lambda: mock_exec_service

    response = client.post(
        "/api/sync/tasks/batch/cancel",
        params={"job_id": str(job_id), "task_type": task_type},
    )
    assert response.status_code == 200, response.json()
    assert task_type in response.json()["message"]
    mock_exec_service.cancel_batch.assert_called_once_with(job_id, task_type)

    app.dependency_overrides.pop(get_execution_service, None)
