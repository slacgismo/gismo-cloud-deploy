import enum


class WorkerState(enum.Enum):
    SUCCESS = "SUCCESS"
    PROGRESS = "PROGRESS"
    FAILED = "FAILED"
    REVOKED = "REVOKED"
