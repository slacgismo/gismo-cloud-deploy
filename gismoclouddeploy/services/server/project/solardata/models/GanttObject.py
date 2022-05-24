class GanttObject(object):
    def __init__(   self,
                    host_ip,
                    task,
                    filename,
                    column_name,
                    start_time,
                    end_time,
                    ):
        self.host_ip = host_ip
        self.task = task
        self.filename = filename
        self.column_name = column_name
        self.start_time = start_time
        self.end_time = end_time