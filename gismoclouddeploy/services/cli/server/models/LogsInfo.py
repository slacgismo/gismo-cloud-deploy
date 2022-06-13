import enum


class LogsInfo(object):
    def __init__(
        self,
        host_name,
        host_ip,
        task_id,
        pid,
        function_name,
        action,
        time,
        message="",
        filename="",
        column_name="",
    ):

        self.host_name = host_name
        self.host_ip = host_ip
        self.task_id = task_id
        self.pid = pid
        self.function_name = function_name
        self.action = action
        self.time = time
        self.message = message
        self.filename = filename
        self.column_name = column_name

    def to_json(self):

        return {
            "host_name": self.host_name,
            "host_ip": self.host_ip,
            "task_id": self.task_id,
            "pid": self.pid,
            "function_name": self.function_name,
            "action": self.action,
            "time": self.time,
            "message": self.message,
            "filename": self.filename,
            "column_name": self.column_name,
        }

    # key for process logs
    # def get_host_name_key() -> str:
    #     return "host_name"
    # def get_host_ip_key() -> str:
    #     return "host_ip"
    # def get_task_id_key() -> str:
    #     return "task_id"
    # def get_pid_key() -> str:
    #     return "pid"
    # def get_function_name_key() -> str:
    #     return "function_name"
    # def get_action_key() -> str:
    #     return "action"
    # def get_time_key() -> str:
    #     return "time"
    # def get_message_key() -> str:
    #     return "message"
    # def get_filename_key()-> str:
    #     return "filename"
    # def get_column_name_key() -> str:
    #     return "column_name"


def make_logsinfo_object_from_dataframe(dataframe):
    worker_list = []
    for row in dataframe.itertuples(index=True, name="Pandas"):
        if row.task_id == "":
            row.task_id = "scheduler"

        worker = LogsInfo(
            host_name=row.host_name,
            host_ip=row.host_ip,
            task_id=row.task_id,
            pid=row.pid,
            function_name=row.function_name,
            action=row.action,
            time=row.timestamp,
            message=row.message,
            filename=row.filename,
            column_name=row.column_name,
        )
        worker_list.append(worker)
    return worker_list