import json

class WorkerStatus(object):

    def __init__(self,
                 host_name,
                 host_ip,
                 task_id,
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
            'function_name' : self.function_name,
            'action' : self.action,
            'time': self.time,
            'message': self.message,
            'filename': self.filename,
            'column_name': self.column_name
        }