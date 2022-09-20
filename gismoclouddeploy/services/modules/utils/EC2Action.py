import enum



class EC2Action(enum.Enum):
    create = "create"
    start = "start"
    stop = "stop"
    terminate = "terminate"
    get_status = "get_status"
    get_public_ip = "get_public_ip"


