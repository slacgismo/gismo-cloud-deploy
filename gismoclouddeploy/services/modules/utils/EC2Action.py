import enum



class EC2Action(enum.Enum):
    running = "running"
    start = "start"
    stop = "stop"
    terminate = "terminate"
    create = "create"
    ssh = "ssh"


