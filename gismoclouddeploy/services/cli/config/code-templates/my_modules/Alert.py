import enum


class Alert(enum.Enum):
    PROCESS_FILE_ERROR = "PROCESS_FILE_ERROR"
    SYSTEM_ERROR = "SYSTEM_ERROR"
    TIMEOUT = "TIMEOUT"
    SAVED_DATA = "SAVED_DATA"
