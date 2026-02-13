from typing import List, Optional
from uuid import UUID
from datetime import datetime
from app.domain.entities import SyncJob, SyncStatus, SyncResult

class MemoryRepo:
    def __init__(self):
        self._jobs: dict[UUID, SyncJob] = {}

    def save_job(self, job: SyncJob) -> None:
        self._jobs[job.id] = job

    def get_job(self, job_id: UUID) -> Optional[SyncJob]:
        return self._jobs.get(job_id)

    def list_jobs(self) -> List[SyncJob]:
        # Return sorted by created_at desc
        return sorted(self._jobs.values(), key=lambda j: j.created_at, reverse=True)

    def update_job_status(self, job_id: UUID, status: SyncStatus, message: Optional[str] = None):
        if job := self.get_job(job_id):
            job.status = status
            if status == SyncStatus.RUNNING:
                job.started_at = datetime.now()
            elif status in [SyncStatus.SUCCESS, SyncStatus.FAILED]:
                job.finished_at = datetime.now()
            
            if message:
                job.error_message = message
            self.save_job(job)

# Global instance for simulation
repo = MemoryRepo()

def get_repo():
    return repo
