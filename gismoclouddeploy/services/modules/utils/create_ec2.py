
import logging
from time import time
from .invoke_function import exec_eksctl_create_cluster,exec_eksctl_delete_cluster
from .modiy_config_parameters import modiy_config_parameters, convert_yaml_to_json
from os.path import exists
import boto3
import botocore
import time
import os
import json
import paramiko
import yaml

from .check_aws import (
    connect_aws_client,
    check_environment_is_aws,
    connect_aws_resource,
)
# logger config
logger = logging.getLogger()
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s: %(levelname)s: %(message)s"
)

TAGS = [
    {'Key': 'Name', 'Value': 'gcd_eks_pvc'},
    {'Key': 'project', 'Value': 'pvinsight'},
    {'Key': 'managedBy', 'Value': 'boto3'}
]

def hand_ec2_bastion(config_file:str,aws_access_key:str,aws_secret_access_key:str, aws_region:str) -> str:
    s3_client = connect_aws_client(
            client_name="s3",
            key_id=aws_access_key,
            secret=aws_secret_access_key,
            region=aws_region,
        )

    config_json = modiy_config_parameters(
            configfile=config_file,
            aws_access_key=aws_access_key,
            aws_secret_access_key=aws_secret_access_key,
            aws_region=aws_region,
            s3_client= s3_client,
        )


    ec2_client = connect_aws_client(
        client_name="ec2",
        key_id=aws_access_key,
        secret=aws_secret_access_key,
        region=aws_region,
    )


    ec2_bastion_saved_config_file  = config_json['aws_config']['ec2_bastion_saved_config_file']

    # # ec2_config_yaml = f"./config/{configfile}"

    if exists(ec2_bastion_saved_config_file) is False:
        logger.error(
            f"{ec2_bastion_saved_config_file} not exist, use default config.yaml instead"
        )
        return 


    ec2_json = convert_yaml_to_json(yaml_file=ec2_bastion_saved_config_file)
    key_pair_name = ec2_json['key_pair_name']
    tags = ec2_json['tags']
    pem_location = ec2_json['pem_location']
    SecurityGroupIds = ec2_json['SecurityGroupIds']
    vpc_id = ec2_json['vpc_id']
    ec2_image_id = ec2_json['ec2_image_id']
    ec2_instance_type = ec2_json['ec2_instance_type']
    user_name = ec2_json['user_name']
    if pem_location is None or os.path.exists(pem_location) is None: 
        logger.error(f"{pem_location} does not exist")
        return 
    
    if key_pair_name is None:
        logger.error(f"{key_pair_name} does not exist. Please create key pair first")
        return 

    if len(SecurityGroupIds) == 0 :
        logger.info("Create security group")
        try:
            security_info_dict = create_security_group(
                ec2_client=ec2_client,
                vpc_id=vpc_id,
                tags=tags
            )
        except Exception as e:
            logger.info(f"Create Security group failed :{e}")
            raise e
        SecurityGroupIds = security_info_dict['security_group_id']
        vpc_id = security_info_dict['vpc_id']
        print(f"Create SecurityGroupIds : {SecurityGroupIds} in vpc_id:{vpc_id}")
   
    ec2_instance_id = create_instance(     
            ImageId=ec2_image_id,
            InstanceType = ec2_instance_type,
            key_piar_name = key_pair_name,
            ec2_client=ec2_client,
            tags= tags,
            SecurityGroupIds = SecurityGroupIds

    )
    pem_file=pem_location +"/"+key_pair_name+".pem"
    instance = check_if_ec2_ready_for_ssh(instance_id=ec2_instance_id, wait_time=60, delay=5, pem_location=pem_file,user_name="ec2-user")

    public_ip = get_public_ip(
            ec2_client=ec2_client,
            instance_id=ec2_instance_id
        )
    print(f"public_ip :{public_ip}")



    # upload install.sh
    logger.info("-------------------")
    logger.info(f"upload install.sh")
    logger.info("-------------------")
    # upload .env
    local_env = "./config/deploy/install.sh"
    remote_env="/home/ec2-user/install.sh"
    upload_file_to_sc2(
        user_name=user_name,
        instance_id=ec2_instance_id,
        pem_location=pem_file,
        ec2_client=ec2_client,
        local_file=local_env,
        remote_file=remote_env,
    )
    # run install.sh
    logger.info("=============================")
    logger.info("Run install.sh ")
    logger.info("=============================")
    command = f"bash /home/ec2-user/install.sh"
    run_command_in_ec2_ssh(
        user_name=user_name,
        instance_id=ec2_instance_id,
        command=command,
        pem_location=pem_file,
        ec2_client=ec2_client
    )

    remote_base_path = f"/home/{user_name}/gismo-cloud-deploy/gismoclouddeploy/services"
    # upload .env
    logger.info("-------------------")
    logger.info(f"upload .env")
    logger.info("-------------------")
    # upload .env
    local_env = ".env"
    
    remote_env=f"{remote_base_path}/.env"
    upload_file_to_sc2(
        user_name=user_name,
        instance_id=ec2_instance_id,
        pem_location=pem_file,
        ec2_client=ec2_client,
        local_file=local_env,
        remote_file=remote_env,
    )


    # upload solver
    local_solver_file = "./config/license/mosek.lic"
    remote_file=f"{remote_base_path}/config/license/mosek.lic"
    logger.info("-------------------")
    logger.info(f"upload solver")
    logger.info("-------------------")
 
    # # upload solver
    upload_file_to_sc2(
         user_name=user_name,
        instance_id=ec2_instance_id,
        pem_location=pem_file,
        ec2_client=ec2_client,
        local_file=local_solver_file,
        remote_file=remote_file,
    )

    logger.info("-------------------")
    logger.info(f"Export ec2 bastion setting to {ec2_bastion_saved_config_file}")
    logger.info("-------------------")

    # export ec2 bastion setting to yaml
    ec2_json['SecurityGroupIds'] = SecurityGroupIds
    ec2_json['vpc_id'] =vpc_id
    ec2_json['ec2_instance_id'] = ec2_instance_id
    ec2_json['public_ip'] = public_ip
    write_aws_setting_to_yaml(file=ec2_bastion_saved_config_file, setting=ec2_json)
   
    logger.info("-------------------")
    logger.info(f"Create ec2 bastion for EKS completed")
    logger.info("-------------------")

    return 

def create_instance(
    ec2_client,
    ImageId :str,
    InstanceType:str,
    key_piar_name: str,
    tags:dict,
    volume:int,
    SecurityGroupIds,
    ) -> str:

   
    # ec2_client = boto3.client("ec2", region_name="us-user-2")
   
    instances = ec2_client.run_instances(
        ImageId=ImageId,
        MinCount=1,
        MaxCount=1,
        InstanceType=InstanceType,
        KeyName=key_piar_name,
        UserData = '''
            #!/bin/bash
            sudo yum update -y
            sudo yum install git -y
            ''',
        TagSpecifications=[
                {
                    'ResourceType': 'instance',
                    'Tags':tags 
                }
        ],
        SecurityGroupIds=SecurityGroupIds,
        BlockDeviceMappings=[
        {
            'DeviceName': '/dev/xvda',
            'Ebs': {

                'DeleteOnTermination': True,
                'VolumeSize': int(volume),
                'VolumeType': 'gp2'
            },
        },
        ],
    )
    instancesID = instances["Instances"][0]["InstanceId"]
    print(instances["Instances"][0]["InstanceId"])
    
    return instancesID


def get_public_ip(
    ec2_client,
    instance_id:str):
    reservations = ec2_client.describe_instances(InstanceIds=[instance_id]).get("Reservations")

    for reservation in reservations:
        for instance in reservation['Instances']:
            return (instance.get("PublicIpAddress"))


def get_running_instances(ec2_client, ):
    reservations = ec2_client.describe_instances(Filters=[
        {
            "Name": "instance-state-name",
            "Values": ["running"],
        }
    ]).get("Reservations")

    for reservation in reservations:
        for instance in reservation["Instances"]:
            instance_id = instance["InstanceId"]
            instance_type = instance["InstanceType"]
            public_ip = instance["PublicIpAddress"]
            private_ip = instance["PrivateIpAddress"]
            print(f"{instance_id}, {instance_type}, {public_ip}, {private_ip}")






## Create EC2 key pair
def create_key_pair(ec2_client,keyname:str, file_location:str):
 
    try:
        key_pair = ec2_client.create_key_pair(KeyName=keyname)
    except Exception as e:
        logger.error(e)
        raise f"Create key pair: {keyname} Failed"


    private_key = key_pair["KeyMaterial"]
    check_if_path_exist_and_create(file_location)
    ## write private key to file with 400 permissions
    with os.fdopen(os.open(f"{file_location}/{keyname}.pem", os.O_WRONLY | os.O_CREAT, 0o400), "w+") as handle: handle.write(private_key)
    logger.info(f"Create {keyname} success, file location: {file_location}")
    return 



## Create VPC
def create_aws_vpc(ec2_client, tags:list) -> str:
    # ec2_client = boto3.client("ec2", region_name="us-east-2")
    vpc = ec2_client.create_vpc( CidrBlock='172.16.0.0/16' )
    # vpc.create_tags(Tags=[{"Key": "Name", "Value": "eks_vpc"},{"Key": "manageBy", "Value": "boto3"}])
    # vpc.wait_until_available()

    print ("Successfully created vpc details are -  {}".format(vpc))
    subnet = ec2_client.create_subnet(CidrBlock = '172.16.2.0/24', VpcId= vpc['Vpc']['VpcId'])
    print("Successfully created subnet details are -  {}".format(subnet))
    ec2_client.create_tags(Resources=[vpc['Vpc']['VpcId']], Tags=tags)
    
    return subnet['Subnet']['SubnetId']



def create_security_group(ec2_client, vpc_id:str = None, tags:list = None, group_name:str = 'SSH-ONLY') -> dict:
     #Create a security group and allow SSH inbound rule through the VPC
    response = ec2_client.describe_vpcs()
    if vpc_id is None or vpc_id == "None":
        vpc_id = response.get('Vpcs', [{}])[0].get('VpcId', '')
    try:
        response = ec2_client.create_security_group(
            GroupName=group_name, 
            Description='only allow SSH traffic', 
            VpcId=vpc_id,
            TagSpecifications=[
                {
                    'ResourceType': 'security-group',
                    'Tags':tags 
                }
            ],
        )
        security_group_id = response['GroupId']
        print('Security Group Created %s in vpc %s.' % (security_group_id, vpc_id))
        data = ec2_client.authorize_security_group_ingress(
            GroupId=security_group_id,
            IpPermissions=[
                {'IpProtocol': 'tcp',
                'FromPort': 22,
                'ToPort': 22,
                'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
            ]
        )
        print('Ingress Successfully Set %s' % data)
        # tag = security_group.create_tags(Tags=tags)
        return {
            'security_group_id':[security_group_id],
            'vpc_id':vpc_id

        }
    except botocore.exceptions.ClientError as err:
        print(err)






def run_command_in_ec2_ssh(
    user_name:str,
    instance_id:str,
    pem_location:str,
    ec2_client,
    command:str,
    ):

    ec2 = boto3.resource('ec2')
    instances = ec2.instances.filter(Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
  
    p2_instance = None
    for instance in instances:
        if (instance.id==instance_id):
            p2_instance=instance
            break;
    if p2_instance is None:
        print(f"{instance_id} is not ready")
        return 


    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    privkey = paramiko.RSAKey.from_private_key_file(pem_location)
    ssh.connect(p2_instance.public_dns_name,username=user_name,pkey=privkey)
    print('started...')
    stdin, stdout, stderr = ssh.exec_command(command, get_pty=True)

    for line in iter(stdout.readline, ""):
        print(line, end="")
    print('finished.')


    ssh.close()

def check_if_ec2_ready_for_ssh(instance_id, wait_time, delay, pem_location, user_name)  -> bool:
    ec2 = boto3.resource('ec2')
    instances = ec2.instances.filter(Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
    print(instances)
    
    p2_instance = None
    while wait_time > 0:
        for instance in instances:
            print(instance, instance_id)
            if (instance.id==instance_id):
                p2_instance=instance
                logger.info(f"{instance_id} is running")
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                privkey = paramiko.RSAKey.from_private_key_file(pem_location)
                try:
                    ssh.connect(p2_instance.public_dns_name,username=user_name,pkey=privkey)
                except Exception as e:
                    logger.warning(f"SSH to {instance_id} failed, try again")
                    continue

                logging.info(f"{instance_id} is ready to connect SSH")
                return True
        wait_time -= delay
        time.sleep(delay)
        logger.info(f"Wait: {wait_time}...")
    
       
    logger.info(f"Cannot find running instance: {instance_id}")

    # try ssh to 
    return False


def upload_file_to_sc2(    
    user_name:str,
    instance_id:str,
    pem_location:str,
    local_file:str,
    remote_file:str,
    ec2_client,):

    ec2 = boto3.resource('ec2')
    instances = ec2.instances.filter(Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
    print(instances)

    for instance in instances:
        if (instance.id==instance_id):
            p2_instance=instance
            break;

    # if not exists(local_file):
    #     raise Exception(f"{local_file} does not exist")

    # check if directory exist
    path, tail = os.path.split(remote_file)
    print(f"path :{path}")

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    privkey = paramiko.RSAKey.from_private_key_file(pem_location)
    ssh.connect(p2_instance.public_dns_name,username=user_name,pkey=privkey)

    command = f"if [ ! -d \"{path}\" ]; then \n echo {path} does not exist \n mkdir {path} \n echo create {path} \n fi"
    (stdin, stdout, stderr) = ssh.exec_command(command)
    for line in stdout.readlines():
        print (line)
    # local_solver_file = "/Users/jimmyleu/Development/gismo/gismo-cloud-deploy/gismoclouddeploy/services/config/license/mosek.lic"
    # remote_file="/home/ec2-user/gismo-cloud-deploy/gismoclouddeploy/services/config/license/mosek.lic"
    # upload file
    ftp_client=ssh.open_sftp()
    ftp_client.put(local_file,remote_file)
    ftp_client.close()
    print(f"Uplodate {local_file} to {remote_file} success")
    return 




def ssh_upload_folder_to_ec2(
    user_name:str,
    instance_id:str,
    pem_location:str,
    ec2_client,
    local_folder:str,
    remote_folder:str,
):

    ec2 = boto3.resource('ec2')
    instances = ec2.instances.filter(Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
    print(instances)

    for instance in instances:
        if (instance.id==instance_id):
            p2_instance=instance
            break;
    
    # check if directory exist
    local_files_list = get_all_files_in_local_dir(local_dir=local_folder)
    # print(local_files_list)
    # conver local files path to remote path 
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    privkey = paramiko.RSAKey.from_private_key_file(pem_location)
    ssh.connect(p2_instance.public_dns_name,username=user_name,pkey=privkey)
    
    # if folder exist 

    # command = f"if [ ! -d \"{path}\" ]; then \n echo {path} does not exist \n mkdir {path} \n echo create {path} \n fi"
    # (stdin, stdout, stderr) = ssh.exec_command(command)
    # for line in stdout.readlines():
    #     print (line)
    # ftp_client=ssh.open_sftp()
    # upload ./config/code-templates-solardatatools/requirements.txt to /home/ec2-user/gismo-cloud-deploy/gismoclouddeploy/services/config/code-templates-solardatatools//config/code-templates-solardatatools/requirements.txt
    # file ="./config/code-templates-solardatatools/requirements.txt"
    # remote_file = "/home/ec2-user/gismo-cloud-deploy/gismoclouddeploy/services/config/code-templates-solardatatools/requirements.txt"
    # upload_file_to_sc2(
    #         user_name=user_name,
    #         instance_id=instance_id,
    #         pem_location=pem_location,
    #         local_file=file,
    #         remote_file=remote_file,
    #         ec2_client=ec2_client
    #     )
    # check if remote dir exist, if it does not exist. Create a new directory.
    upload_local_to_remote_dict = {}
    for file in local_files_list:
        relative_path, filename = os.path.split(file)
        
        # remove ".""
        relative_path = relative_path.replace(".","") 
        print(f"relative_path :{relative_path} filename :{filename}")
        # print(f"relative_path: {relative_path}")
        # remote_file = remote_folder + "/" + relative_path  +"/" + filename
        remote_dir = remote_folder  + relative_path
        upload_local_to_remote_dict[file] = remote_dir  +"/" + filename
        # print("----------------------------")
        # print(upload_local_to_remote_dict[file] )
        # print("------------------------------")
        # print(f"upload {file} to {remote_file}")
        # print(f"remote_dir: {remote_dir}")

        command = f"if [ ! -d \"{remote_dir}\" ]; then \n echo {remote_dir} does not exist \n mkdir {remote_dir} \n echo create {remote_dir} \n fi"
        (stdin, stdout, stderr) = ssh.exec_command(command)
        for line in stdout.readlines():
            print (line)
        # print("----------------------------")

    ftp_client=ssh.open_sftp()
    for key,value in upload_local_to_remote_dict.items():
    
        try:
            ftp_client.put(key,value)
            logger.info(f"upload :{key} to {value} success")
        except Exception as e :
            logger.error(f"upload :{key} to {value} failed: {e}")
        # print(f"local :{key}")
        # print(f"value :{value}")
    ftp_client.close()
    logger.info(f"Uplodate {local_folder} to {remote_folder} success!!!")
    return 


def get_all_files_in_local_dir( local_dir:str) -> list:
    all_files = list()

    if os.path.exists(local_dir):
        files = os.listdir(local_dir)
        for x in files:
            filename = os.path.join(local_dir, x)
            print ("filename:" + filename)
            # isdir
            if os.path.isdir(filename):
                all_files.extend(get_all_files_in_local_dir(filename))
            else:
                all_files.append(filename)
        else:
            print ('-- {}does not exist'.format(local_dir))
    else:
        print(f"{local_dir} doese not exist")
    return all_files





def handle_ec2_bastion(config_file:str,aws_access_key:str,aws_secret_access_key:str, aws_region:str, action: str) -> str:
    s3_client = connect_aws_client(
            client_name="s3",
            key_id=aws_access_key,
            secret=aws_secret_access_key,
            region=aws_region,
        )
 
    config_json = modiy_config_parameters(
            configfile=config_file,
            aws_access_key=aws_access_key,
            aws_secret_access_key=aws_secret_access_key,
            aws_region=aws_region,
            s3_client= s3_client,
        )
    ec2_bastion_saved_config_file  = config_json['aws_config']['ec2_bastion_saved_config_file']

    # # ec2_config_yaml = f"./config/{configfile}"

    if exists(ec2_bastion_saved_config_file) is False:
        logger.error(
            f"{ec2_bastion_saved_config_file} not exist, use default config.yaml instead"
        )
        return 
    

    ec2_json = convert_yaml_to_json(yaml_file=ec2_bastion_saved_config_file)
    key_pair_name = ec2_json['key_pair_name']
    tags = ec2_json['tags']
    pem_location = ec2_json['pem_location']
    instance_id = ec2_json['ec2_instance_id']
    pem_file=pem_location +"/"+key_pair_name+".pem"
    user_name = ec2_json['user_name']
    action = action.upper()
    ec2 = boto3.resource('ec2')
    if action == "START":
        logger.info("start ec2")
        # check if instance id  exists
        res = ec2.instances.filter(InstanceIds = [instance_id]).start() #for start an ec2 instance
        instance = check_if_ec2_ready_for_ssh(instance_id=instance_id, wait_time=60, delay=5, pem_location=pem_file,user_name=user_name)

    elif action == "STOP":
        # check if instance id  exists
        logger.info("stop ec2")
        res = ec2.instances.filter(InstanceIds = [instance_id]).stop() #for stopping an ec2 instance

    elif action == "TERMINATE":
        # check if instance id  exists
        logger.info("terminate ec2")
        res = ec2.instances.filter(InstanceIds = [instance_id]).stop() #for stopping an ec2 instance
        res_term  = ec2.instances.filter(InstanceIds = [instance_id]).terminate() #for terminate an ec2 instance
    elif action == "LIST":
        # check if instance id  exists
        logger.info("list ec2")

    elif action == "CREATE":
        logger.info("create ec2")
        create_ec2_bastion(
            config_file=config_file,
            aws_access_key=aws_access_key,
            aws_secret_access_key=aws_secret_access_key,
            aws_region=aws_region
        )

    else:
        logger.info("Unknow action")
    return 



def create_ec2_keypair(
        keyname:str,
        file_location:str,
        aws_access_key:str,
        aws_secret_access_key:str,
        aws_region:str):

    ec2_client = connect_aws_client(
        client_name="ec2",
        key_id=aws_access_key,
        secret=aws_secret_access_key,
        region=aws_region,
    )
    create_key_pair(ec2_client=ec2_client, keyname=keyname, file_location=file_location)
    return 

def write_aws_setting_to_yaml(file:str,setting:dict):
    # check if directory exist
    check_if_path_exist_and_create(file)

    with open(file, 'w') as yaml_file:
        yaml.dump(setting, yaml_file, default_flow_style=False)


def check_if_path_exist_and_create(file:str):
    path, tail = os.path.split(file)
    local_path_isExist = os.path.exists(path)
    if local_path_isExist is False:
        print(f"{path} does not exist. Create path")
        os.mkdir(path)
        print(f"Create {path} success")
    


def create_iam_policy(PolicyName:str, policy_document:dict, iam_client):
    # Create IAM client


    # Create a policy
    # my_managed_policy = {
    #     "Version": "2012-10-17",
    #     "Statement": [
    #         {
    #             "Effect": "Allow",
    #             "Action": [
    #                 "dynamodb:GetItem",
    #                 "dynamodb:Scan",
    #             ],
    #             "Resource": "*"
    #         }
    #     ]
    # }
    response = iam_client.create_policy(
        PolicyName=PolicyName,
        PolicyDocument=json.dumps(policy_document)
    )
    print(response)

## Create IAM role policy
def CreateInstanceProfileRole():
    client = boto3.client('iam')
    assume_role_policy_document = json.dumps({ "Version": "2012-10-17","Statement": [{ "Effect": "Allow", "Principal": {"Service": "ec2.amazonaws.com"},"Action": "sts:AssumeRole"}
        ]
    })

    ## Create IAM role
    create_role_response = client.create_role(RoleName = "my-instance-role", AssumeRolePolicyDocument = assume_role_policy_document)
    print (create_role_response)
    
    ## Attach policies to above role
    ## AmazonEC2FullAccess
    ## 

    EKS_autoscaler_role_policy_document = json.dumps(
        {
            "Version": "2012-10-17","Statement": 
            [
                { 
                    "Effect": "Allow",
                    "Resource": "*", 
                    "Action":  [
                        "autoscaling:DescribeAutoScalingGroups",
                        "autoscaling:DescribeAutoScalingInstances",
                        "autoscaling:DescribeLaunchConfigurations",
                        "autoscaling:DescribeTags",
                        "autoscaling:SetDesiredCapacity",
                        "autoscaling:TerminateInstanceInAutoScalingGroup",
                        "ec2:DescribeLaunchTemplateVersions"
                    ]
                }
            ]
        }
    )

    


    roleEKSautoscalerpolicyAttachResponse = client.attach_role_policy(RoleName = "my-instance-role", PolicyDocument = EKS_autoscaler_role_policy_document)
    print (roleEKSautoscalerpolicyAttachResponse)


    #EKSAccess

    EKSAccess_role_policy_document = json.dumps(
       {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": "eks:*",
                    "Resource": "*"
                },
                {
                    "Action": [
                        "ssm:GetParameter",
                        "ssm:GetParameters"
                    ],
                    "Resource": "*",
                    "Effect": "Allow"
                }
            ]
        }
    )


    roleEKSAccesspolicyAttachResponse = client.attach_role_policy(RoleName = "my-instance-role", PolicyDocument = EKSAccess_role_policy_document)
    print (roleEKSAccesspolicyAttachResponse)
    
    
    #EKS limit access
    EKSLimitAccess_role_policy_document = json.dumps(
       {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "iam:CreateInstanceProfile",
                        "iam:DeleteInstanceProfile",
                        "iam:GetInstanceProfile",
                        "iam:RemoveRoleFromInstanceProfile",
                        "iam:GetRole",
                        "iam:CreateRole",
                        "iam:DeleteRole",
                        "iam:AttachRolePolicy",
                        "iam:PutRolePolicy",
                        "iam:ListInstanceProfiles",
                        "iam:AddRoleToInstanceProfile",
                        "iam:ListInstanceProfilesForRole",
                        "iam:PassRole",
                        "iam:DetachRolePolicy",
                        "iam:DeleteRolePolicy",
                        "iam:GetRolePolicy",
                        "iam:GetOpenIDConnectProvider",
                        "iam:CreateOpenIDConnectProvider",
                        "iam:DeleteOpenIDConnectProvider",
                        "iam:TagOpenIDConnectProvider",
                        "iam:ListAttachedRolePolicies",
                        "iam:TagRole",
                        "iam:GetPolicy",
                        "iam:CreatePolicy",
                        "iam:DeletePolicy",
                        "iam:ListPolicyVersions"
                    ],
                    "Resource": "*"
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "iam:GetRole"
                    ],
                    "Resource": "*"
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "iam:CreateServiceLinkedRole"
                    ],
                    "Resource": "*",
                    "Condition": {
                        "StringEquals": {
                            "iam:AWSServiceName": [
                                "eks.amazonaws.com",
                                "eks-nodegroup.amazonaws.com",
                                "eks-fargate.amazonaws.com"
                            ]
                        }
                    }
                }
            ]
        }
    )


    roleEKSLimitAccesspolicyAttachResponse = client.attach_role_policy(RoleName = "my-instance-role", PolicyDocument = EKSLimitAccess_role_policy_document)
    print (roleEKSLimitAccesspolicyAttachResponse)

    ## Attach policies to above role
    ## AmazonEC2FullAccess
    ## 
    roleEC2policyAttachResponse = client.attach_role_policy( RoleName='my-instance-role', PolicyArn='arn:aws:iam::aws:policy/AmazonEC2FullAccess')
    print (roleEC2policyAttachResponse)
    ## Attach policies to above role
    ## AmazonSQSFullAccess
    ## 
    roleSQSpolicyAttachResponse = client.attach_role_policy( RoleName='my-instance-role', PolicyArn='arn:aws:iam::aws:policy/AmazonSQSFullAccess')
    print (roleSQSpolicyAttachResponse)
    ## Attach policies to above role
    ## AmazonECRFullAccess
    ## 
    roleECRpolicyAttachResponse = client.attach_role_policy( RoleName='my-instance-role', PolicyArn='arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryFullAccess')
    print (roleECRpolicyAttachResponse)
    ## Attach policies to above role
    ## AmazonECSFullAccess
    ## 
    roleECSpolicyAttachResponse = client.attach_role_policy( RoleName='my-instance-role', PolicyArn='arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceAutoscaleRole')
    print (roleECSpolicyAttachResponse)
    ## Attach policies to above role
    ## AmazonEC2BuildImage
    ## 
    roleEC2BuildImagepolicyAttachResponse = client.attach_role_policy( RoleName='my-instance-role', PolicyArn='arn:aws:iam::aws:policy/EC2InstanceProfileForImageBuilderECRContainerBuilds')
    print (roleEC2BuildImagepolicyAttachResponse)
    ## Attach policies to above role
    ## AmazonCloudFormation
    ## 
    rolCloudFormationolicyAttachResponse = client.attach_role_policy( RoleName='my-instance-role', PolicyArn='arn:aws:iam::aws:policy/AWSCloudFormationFullAccess')
    print (rolCloudFormationolicyAttachResponse)

    
    roleSSMpolicyAttachResponse = client.attach_role_policy( RoleName='my-instance-role', PolicyArn='arn:aws:iam::aws:policy/AmazonEC2FullAccess')
    print (roleSSMpolicyAttachResponse)

    roleSSMpolicyAttachResponse = client.attach_role_policy( RoleName='my-instance-role', PolicyArn='arn:aws:iam::aws:policy/AmazonSSMFullAccess')
    print (roleSSMpolicyAttachResponse)
    ## Attach policies to above role
    roleS3policyAttachResponse = client.attach_role_policy( RoleName='my-instance-role', PolicyArn='arn:aws:iam::aws:policy/AmazonS3FullAccess')
    print (roleS3policyAttachResponse)

    ## Create instance profile
    instance_profile = client.create_instance_profile ( InstanceProfileName ='Test-instance-profile')
    print (instance_profile)
    ## Add roles
    response = client.add_role_to_instance_profile ( InstanceProfileName = 'Test-instance-profile', RoleName = 'my-instance-role')
    print (response)
    # EKSAutoscaler_role_policy_document ={
    #         "Version": "2012-10-17","Statement": 
    #         [
    #             { 
    #                 "Effect": "Allow",
    #                 "Resource": "*", 
    #                 "Action":  [
    #                     "autoscaling:DescribeAutoScalingGroups",
    #                     "autoscaling:DescribeAutoScalingInstances",
    #                     "autoscaling:DescribeLaunchConfigurations",
    #                     "autoscaling:DescribeTags",
    #                     "autoscaling:SetDesiredCapacity",
    #                     "autoscaling:TerminateInstanceInAutoScalingGroup",
    #                     "ec2:DescribeLaunchTemplateVersions"
    #                 ]
    #             }
    #         ]
    # }
    
    # iam_client = connect_aws_client(
    #         client_name="iam",
    #         key_id=aws_access_key,
    #         secret=aws_secret_access_key,
    #         region=aws_region,
    #     )
    # create_iam_policy(PolicyName="EKAAutoscler", policy_document=EKSAutoscaler_role_policy_document, iam_client=iam_client)
    # CreateInstanceProfileRole()

    # create_key_pair()

    # returnedsubnetid  = create_aws_vpc()

    # createdinstanceID = create_instance("subnet-3c845470")

    # get_running_instances()

    # get_public_ip("i-0705c070342b7b062")

    # runRemoteShellCommands("i-0705c070342b7b062")
    # cluster_file = config_json['aws_config']['cluster_file']

    # if not exists(cluster_file):
    #     logger.error(f"{cluster_file} does not exist")
    #     return 
    # res = exec_eksctl_create_cluster(cluster_file=cluster_file)
    # logger.info(res)



# # create an STS client object that represents a live connection to the 
# # STS service
# sts_client = boto3.client('sts')

# # Call the assume_role method of the STSConnection object and pass the role
# # ARN and a role session name.
# assumed_role_object=sts_client.assume_role(
#     RoleArn="arn:aws:iam::account-of-role-to-assume:role/name-of-role",
#     RoleSessionName="AssumeRoleSession1"
# )

# # From the response that contains the assumed role, get the temporary 
# # credentials that can be used to make subsequent API calls
# credentials=assumed_role_object['Credentials']

# # Use the temporary credentials that AssumeRole returns to make a 
# # connection to Amazon S3  
# s3_resource=boto3.resource(
#     's3',
#     aws_access_key_id=credentials['AccessKeyId'],
#     aws_secret_access_key=credentials['SecretAccessKey'],
#     aws_session_token=credentials['SessionToken'],
# )

# # Use the Amazon S3 resource object that is now configured with the 
# # credentials to access your S3 buckets. 
# for bucket in s3_resource.buckets.all():
#     print(bucket.name)

# export .env to environment virable
# export $( grep -vE "^(#.*|\s*)$" .env )

# aws configure get default.aws_access_key_id
# aws configure get default.aws_secret_access_key


## EC2 instance boto3
# def create_instance(subnet):
#     print("Create AWS instances..")
#     ec2_client = boto3.client("ec2", region_name="us-east-2")
#     instances = ec2_client.run_instances(ImageId="ami-0568773882d492fc8", MinCount=1, MaxCount=1, InstanceType="t2.micro",KeyName="JL-gismo-mac13", NetworkInterfaces=[{'DeviceIndex': 0,'SubnetId' : subnet, 'AssociatePublicIpAddress': True,}], IamInstanceProfile={'Name': "Test-instance-profile"} )
#     return instances["Instances"][0]["InstanceId"]

# ## How to get the public IP for a running EC2 instance
# def get_public_ip(instance_id):
#     ec2_client = boto3.client("ec2", region_name="us-east-2")
#     reservations = ec2_client.describe_instances(InstanceIds=[instance_id]).get("Reservations")

#     for reservation in reservations:
#         for instance in reservation['Instances']:
#             print(instance.get("PublicIpAddress"))

# ## How to list all running EC2 instances
# def get_running_instances():
#     ec2_client = boto3.client("ec2", region_name="us-east-2")
#     reservations = ec2_client.describe_instances(Filters=[
#         {
#             "Name": "instance-state-name",
#             "Values": ["running"],
#         }
#     ]).get("Reservations")

#     for reservation in reservations:
#         for instance in reservation["Instances"]:
#             instance_id = instance["InstanceId"]
#             instance_type = instance["InstanceType"]
#             public_ip = instance["PublicIpAddress"]
#             private_ip = instance["PrivateIpAddress"]
#             print(f"{instance_id}, {instance_type}, {public_ip}, {private_ip}")



# ## Run command against your linux VM
# def runRemoteShellCommands (InstanceId):
#     ssm_client = boto3.client('ssm', region_name="us-east-2") 
#     response = ssm_client.send_command( InstanceIds=[InstanceId], DocumentName="AWS-RunShellScript", Parameters={'commands':[ 'echo "hello world" echo "hello world2"']},)
#     command_id = response['Command']['CommandId']
#     output = ssm_client.get_command_invocation( CommandId=command_id, InstanceId=InstanceId)
#     while output['Status'] == "InProgress":   
#         output = ssm_client.get_command_invocation( CommandId=command_id, InstanceId=InstanceId) 
#     print(output['StandardOutputContent'])
