import json
import pandas as pd
class WorkerStatus(object):

    def __init__(self,
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
            'host_name': self.host_name,
            'host_ip' : self.host_ip,
            'task_id': self.task_id,
            'pid': self.pid,
            'function_name' : self.function_name,
            'action' : self.action,
            'time': self.time,
            'message': self.message,
            'filename': self.filename,
            'column_name': self.column_name
        }

def make_worker_object_from_dataframe(dataframe):
    worker_list = []
    for row in dataframe.itertuples(index=True, name='Pandas'):
        task_id = row.task_id
        if pd.isnull(row.task_id):
            task_id = "scheduler"
        # print(row.timestamp, row.host_ip)
        worker = WorkerStatus(host_name=row.host_name,
                        host_ip=row.host_ip,
                        task_id = task_id,
                        pid = row.pid,
                        function_name = row.function_name,
                        action = row.action,
                        time = row.timestamp,
                        message = row.message,
                        filename = row.filename,
                        column_name = row.column_name
                        )
        worker_list.append(worker)
    return worker_list