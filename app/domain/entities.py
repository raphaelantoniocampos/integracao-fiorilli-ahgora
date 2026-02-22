from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID, uuid4

from .enums import SyncStatus, AutomationTaskType, AutomationTaskStatus


@dataclass
class SyncJob:
    id: UUID = field(default_factory=uuid4)
    status: SyncStatus = field(default=SyncStatus.PENDING)
    triggered_by: str = field(default="system")
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    next_retry_at: Optional[datetime] = None


@dataclass
class SyncResult:
    success: bool
    status: SyncStatus
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SyncLog:
    id: Optional[int]
    job_id: UUID
    level: str
    message: str
    task_id: Optional[UUID] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class AutomationTask:
    job_id: UUID
    type: AutomationTaskType
    id: UUID = field(default_factory=uuid4)
    status: AutomationTaskStatus = field(default=AutomationTaskStatus.PENDING)
    payload: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0
