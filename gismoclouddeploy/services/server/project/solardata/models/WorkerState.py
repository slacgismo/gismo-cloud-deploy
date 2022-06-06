import enum
from sre_constants import SUCCESS


class WorkerState(enum.Enum):
    SUCCESS = "SUCCESS"
    PROGRESS = "PROGRESS"
    FAILED = "FAILED"
    REVOKED = "REVOKED"
