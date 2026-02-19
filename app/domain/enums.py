from enum import StrEnum, auto


class SyncStatus(StrEnum):
    PENDING = auto()
    RUNNING = auto()
    SUCCESS = auto()
    FAILED = auto()
    CANCELLED = auto()
    RETRYING = auto()
