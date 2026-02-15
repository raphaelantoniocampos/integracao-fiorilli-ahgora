import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, AsyncMock, patch
from uuid import uuid4
from app.main import app
from app.core.database import get_db
from app.domain.entities import SyncJob, SyncLog

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
    mock_service.run_sync_background = AsyncMock()

    response = client.post("/api/sync/run")

    assert response.status_code == 200
    assert response.json()["id"] == str(job_id)
    mock_service.create_job.assert_called_once()


@patch("app.api.endpoints.SyncService")
def test_get_job_logs(mock_service_class, client):
    mock_service = mock_service_class.return_value
    job_id = uuid4()
    logs = [SyncLog(id=1, job_id=job_id, level="INFO", message="Test Log")]
    mock_service.get_job_logs = AsyncMock(return_value=logs)

    response = client.get(f"/api/sync/jobs/{job_id}/logs")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["message"] == "Test Log"
