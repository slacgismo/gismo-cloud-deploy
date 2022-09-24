import enum



class EC2Actions(enum.Enum):
    create = "create"
    start = "start"
    stop = "stop"
    terminate = "terminate"
    get_status = "get_status"
    get_public_ip = "get_public_ip"



