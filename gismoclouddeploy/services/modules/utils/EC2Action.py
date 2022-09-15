import enum



class EC2Action(enum.Enum):
    create_new = "create_new"
    start_from_existing = "start_from_existing"
    cleanup_resources = "cleanup_resource"
    ssh = "ssh"
    # running = "running"
    # stop = "stop"
    # terminate = "terminate"
    # create = "create"
    # ssh = "ssh"
    # ssh_create_eks = "ssh_create_eks"
    # ssh_delete_eks = "ssh_delete_eks"


