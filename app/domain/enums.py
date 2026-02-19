from enum import StrEnum, auto


class SyncStatus(StrEnum):
    PENDING = auto()
    RUNNING = auto()
    SUCCESS = auto()
    FAILED = auto()
    CANCELLED = auto()
    RETRYING = auto()


class AutomationTaskType(StrEnum):
    ADD_EMPLOYEE = auto()
    REMOVE_EMPLOYEE = auto()
    UPDATE_EMPLOYEE = auto()
    ADD_LEAVE = auto()


class AutomationTaskStatus(StrEnum):
    PENDING = auto()
    RUNNING = auto()
    SUCCESS = auto()
    FAILED = auto()
    CANCELLED = auto()
