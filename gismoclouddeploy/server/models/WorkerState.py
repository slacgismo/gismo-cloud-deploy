import enum


class WorkerState(enum.Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    RECEIVED = "RECEIVED"
