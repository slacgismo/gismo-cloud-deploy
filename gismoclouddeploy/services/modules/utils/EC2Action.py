import enum



class EC2Action(enum.Enum):
    start = "start"
    activate_from_existing = "activate_from_existing"
    cleanup_resources = "cleanup_resource"
    ssh = "ssh"
    # running = "running"
    # stop = "stop"
    # terminate = "terminate"
    # create = "create"
    # ssh = "ssh"
    # ssh_create_eks = "ssh_create_eks"
    # ssh_delete_eks = "ssh_delete_eks"


