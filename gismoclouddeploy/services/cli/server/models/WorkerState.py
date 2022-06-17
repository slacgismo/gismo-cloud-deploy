import enum


class WorkerState(enum.Enum):
    SUCCESS = "SUCCESS"
    PROCESS = "PROCESS"
    FAILED = "FAILED"
    REVOKED = "REVOKED"
