class TasksPerformance(object):
    def __init__(
        self,
        total_task_duration: float = None,
        total_tasks: int = None,
        average_task_duration: float = None,
        shortest_task_duration: float = None,
        longest_task_duration: float = None,
        shortest_task: str = None,
        lognest_task: str = None,
        num_error_task: int = None,
        num_success_task: int = None,
    ):
        self.total_task_duration = total_task_duration
        self.total_tasks = total_tasks
        self.average_task_duration = average_task_duration
        self.shortest_task_duration = shortest_task_duration
        self.longest_task_duration = longest_task_duration
        self.shortest_task = shortest_task
        self.lognest_task = lognest_task
        self.num_error_task = num_error_task
        self.num_success_task = num_success_task
