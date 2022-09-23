import enum



class EKSAction(enum.Enum):
    create = "create"
    delete = "delete"
    list = "list"
    scaledownzero = "scaledownzero"
