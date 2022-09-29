import enum



class EKSActions(enum.Enum):
    create = "create"
    delete = "delete"
    list = "list"
    scaledownzero = "scaledownzero"
    check_cluster_exist = "check_cluster_exist"
