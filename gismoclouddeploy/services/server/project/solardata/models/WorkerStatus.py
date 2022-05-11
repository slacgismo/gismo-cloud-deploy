import json

class WorkerStatus(object):

    def __init__(self,
                 host_name,
                 worker_ip,
                 task_id,
                 function_name,
                 action,
                 time,
                 message
                 ):

        self.host_name = host_name
        self.host_ip = worker_ip
        self.task_id = task_id
        self.function_name = function_name
        self.action = action
        self.time = time
        self.message = message
    
    
    def to_json(self):

        return {
            'host_name': self.host_name,
            'host_ip' : self.host_ip,
            'task_id': self.task_id,
            'function_name' : self.function_name,
            'action' : self.action,
            'time': self.time,
            'message': self.message,
        }