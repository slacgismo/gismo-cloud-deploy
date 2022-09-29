import enum



class AWSActions(enum.Enum):
    get_default_vpc_id = "get_default_vpc_id"
    create_securitygroup = "create_securitygroup"
    delete_securitygroup = "delete_securitygroup"
    create_keypair = "create_keypair"
    delete_keypair = "delete_keypair"
    create_ec2_instance = "create_ec2_instance"
    check_ec2_exist = "check_ec2_exist"
