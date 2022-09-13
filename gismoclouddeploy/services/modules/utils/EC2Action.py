import enum



class EC2Action(enum.Enum):
    running = "running"
    stop = "stop"
    terminate = "terminate"
    create = "create"
    ssh = "ssh"
    ssh_create_eks = "ssh_create_eks"
    ssh_delete_eks = "ssh_delete_eks"


