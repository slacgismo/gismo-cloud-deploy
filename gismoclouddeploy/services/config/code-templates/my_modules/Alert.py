import enum


"""
Constant for SNS
PROCESS_FILE_ERROR: Indicate process file error for debug purpose.
SYSTEM_ERROR: Indicate process file error for debug purpose.
TIMEOUT: Indicate timeout alert. It reovkes current task.
SAVED_DATA: Indicate save data alert. With this alert type, its contents are saved into save data file.
"""


class Alert(enum.Enum):
    PROCESS_FILE_ERROR = "PROCESS_FILE_ERROR"
    SYSTEM_ERROR = "SYSTEM_ERROR"
    TIMEOUT = "TIMEOUT"
    SAVED_DATA = "SAVED_DATA"
