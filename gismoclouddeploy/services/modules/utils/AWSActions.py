import enum



class AWSActions(enum.Enum):
    get_default_vpc_id = "get_default_vpc_id"
    create_securitygroup = "create_securitygroup"
    delete_securitygroup = "delete_securitygroup"
    create_keypair = "create_keypair"
    delete_keypair = "delete_keypair"
