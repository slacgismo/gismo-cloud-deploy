import logging
from time import time
from .invoke_function import exec_eksctl_create_cluster,exec_eksctl_delete_cluster
from .modiy_config_parameters import modiy_config_parameters
from os.path import exists
import boto3
import botocore
import time
import os
import json
import paramiko

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

def create_ec2_bastion(config_file:str,pem_location:str,aws_access_key:str,aws_secret_access_key:str, aws_region:str) -> str:
    s3_client = connect_aws_client(
            client_name="s3",
            key_id=aws_access_key,
            secret=aws_secret_access_key,
            region=aws_region,
        )
    # ec2_client =  connect_aws_client(
    #         client_name="ec2",
    #         key_id=aws_access_key,
    #         secret=aws_secret_access_key,
    #         region=aws_region,
    # )
    # step 1 create vpc 
    # logger.info("Create VPC ")
    # subnetId = create_aws_vpc(ec2_client = ec2_client, tags = TAGS)
    # print(f"subnetId :{subnetId}")
    # step 2 create security group 

    # step 3 create policy
    # step 4 create assume role
    # step 5 create ec2 instance


    config_json = modiy_config_parameters(
            configfile=config_file,
            aws_access_key=aws_access_key,
            aws_secret_access_key=aws_secret_access_key,
            aws_region=aws_region,
            s3_client= s3_client,
        )
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



    ec2_client = connect_aws_client(
        client_name="ec2",
        key_id=aws_access_key,
        secret=aws_secret_access_key,
        region=aws_region,
    )
    tags = config_json['aws_config']['tags']    
    ec2_instance_id = config_json['aws_config']['ec2_instance_id']
    ec2_image_id = config_json['aws_config']['ec2_image_id']
    ec2_instance_type = config_json['aws_config']['ec2_instance_type']

    SecurityGroupIds = config_json['aws_config']['SecurityGroupIds']
    if SecurityGroupIds is None:
        logger.info(" Securtiy group ids is None, create security group ")
        # to be continue..
        res = create_security_group(ec2_client=ec2_client, tags=tags)
        print(res)
        return 

    # # stop_instance(instance_id="i-0a691aedf18d7aae9", ec2_client = ec2_client)
    # # time.sleep(5)
    # # terminate_instance(instance_id="i-0a691aedf18d7aae9", ec2_client = ec2_client)
    pem_path, pem_file = os.path.split(pem_location)
    key_pair_name, file_extenstion =pem_file.split(".") 
    # print(pem_path, key_pair_name)
    


    if ec2_instance_id is None:
        logger.info("No exist instance id , create new ec2 instance")
        ec2_instance_id = create_instance(     
            ImageId=ec2_image_id,
            InstanceType = ec2_instance_type,
            key_piar_name = key_pair_name,
            ec2_client=ec2_client,
            tags= tags,
            SecurityGroupIds = SecurityGroupIds

        )
    instance = check_if_ec2_ready(
        instance_id=ec2_instance_id,
        wait_time=60,
        delay=2

    )
    
    if instance is None:
        logger.info(f"Cannot find running instance :{ec2_instance_id}")
        logger.info(f"Please create a new ec2 instance or check aws account ")
        return

    public_id = get_public_ip(
        ec2_client=ec2_client,
        instance_id=ec2_instance_id
    )

    
    # instance = check_if_ec2_ready(instance_id=instance_id, wait_time=60, delay=5)

    # install eksctl 
    logger.info("=============================")
    logger.info("Start install eksctl ")
    command = f"curl --silent --location \"https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz\" | tar xz -C /tmp \n sudo mv /tmp/eksctl /usr/local/bin"
    run_command_in_ec2_ssh(
        user_name="ec2-user",
        instance_id=ec2_instance_id,
        command=command,
        pem_location=pem_location,
        ec2_client=ec2_client
    )
    
    logger.info("=============================")
    logger.info("Start install aws cli ")
    command = f"curl \"https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip\" -o \"awscliv2.zip\" \n unzip awscliv2.zip \n sudo ./aws/install"
    run_command_in_ec2_ssh(
        user_name="ec2-user",
        instance_id=ec2_instance_id,
        command=command,
        pem_location=pem_location,
        ec2_client=ec2_client
    )
    logger.info("=============================")
    logger.info("Start install kubectl ")
    command = f"export RELEASE=1.22.0 \n curl -LO https://storage.googleapis.com/kubernetes-release/release/v$RELEASE/bin/linux/amd64/kubectl \n chmod +x ./kubectl \n sudo mv ./kubectl /usr/local/bin/kubectl"
    run_command_in_ec2_ssh(
        user_name="ec2-user",
        instance_id=ec2_instance_id,
        command=command,
        pem_location=pem_location,
        ec2_client=ec2_client
    )
    logger.info("=============================")
    logger.info("Start install docker ")
    command = "amazon-linux-extras install docker -y \n  sudo service docker start \n sudo usermod -a -G docker ec2-user"
    run_command_in_ec2_ssh(
        user_name="ec2-user",
        instance_id=ec2_instance_id,
        command=command,
        pem_location=pem_location,
        ec2_client=ec2_client
    )
    logger.info("=============================")
    logger.info("Start install docker-compose ")

    command = " sudo curl -L https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m) -o /usr/local/bin/docker-compose \n sudo chmod +x /usr/local/bin/docker-compose"
    run_command_in_ec2_ssh(
        user_name="ec2-user",
        instance_id=ec2_instance_id,
        command=command,
        pem_location=pem_location,
        ec2_client=ec2_client
    )
    logger.info("=============================")
    # start docker server
    logger.info("git clone ")
    command = f"git clone https://github.com/slacgismo/gismo-cloud-deploy.git /home/ec2-user/gismo-cloud-deploy\n cd /home/ec2-user/gismo-cloud-deploy \n git fetch \n  git switch feature/namespace \n"
    # run installation 
    run_command_in_ec2_ssh(
        user_name="ec2-user",
        instance_id=ec2_instance_id,
        command=command,
        pem_location=pem_location,
        ec2_client=ec2_client
    )
    logger.info("=============================")
    logger.info("install python package ")
    command = f"python3.8 -m venv /home/ec2-user/gismo-cloud-deploy/gismoclouddeploy/services/venv \n source /home/ec2-user/gismo-cloud-deploy/gismoclouddeploy/services/venv/bin/activate \n pip install --upgrade pip \n pip install -r /home/ec2-user/gismo-cloud-deploy/gismoclouddeploy/services/requirements.txt"
    # run installation 
    run_command_in_ec2_ssh(
        user_name="ec2-user",
        instance_id=ec2_instance_id,
        command=command,
        pem_location=pem_location,
        ec2_client=ec2_client
    )
    logger.info("=============================")

    print("wait 5 sec")
    time.sleep(5)
    # upload solver 
    local_solver_file = "/Users/jimmyleu/Development/gismo/gismo-cloud-deploy/gismoclouddeploy/services/config/license/mosek.lic"
    remote_file="/home/ec2-user/gismo-cloud-deploy/gismoclouddeploy/services/config/license/mosek.lic"
    logger.info("-------------------")
    logger.info(f"upload solver")
    logger.info("-------------------")
 
    # # upload solver
    upload_file_to_sc2(
        user_name="ec2-user",
        instance_id=ec2_instance_id,
        pem_location=pem_location,
        ec2_client=ec2_client,
        local_file=local_solver_file,
        remote_file=remote_file,
    )
    logger.info("-------------------")
    logger.info(f"upload .env")
    logger.info("-------------------")
    # upload .env
    local_env = "/Users/jimmyleu/Development/gismo/gismo-cloud-deploy/gismoclouddeploy/services/.env"
    remote_env="/home/ec2-user/gismo-cloud-deploy/gismoclouddeploy/services/.env"
    upload_file_to_sc2(
        user_name="ec2-user",
        instance_id=instance_id,
        pem_location=pem_location,
        ec2_client=ec2_client,
        local_file=local_env,
        remote_file=remote_env,
    )
    logger.info("-------------------")
    logger.info(f"export aws credential from .env")
    logger.info("-------------------")
    # upload .env
    command = f"export $( grep -vE \"^(#.*|\s*)$\" .env )"
    # run installation 
    run_command_in_ec2_ssh(
        user_name="ec2-user",
        instance_id=ec2_instance_id,
        command=command,
        pem_location=pem_location,
        ec2_client=ec2_client
    )
    
    return 


def create_instance(
    ec2_client,
    ImageId :str,
    InstanceType:str,
    key_piar_name: str,
    tags:dict,
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
            # # install python 3.8
            sudo yum install -y amazon-linux-extras
            amazon-linux-extras install python3.8
            ''',
        TagSpecifications=[
                {
                    'ResourceType': 'instance',
                    'Tags':tags 
                }
        ],
        SecurityGroupIds=SecurityGroupIds,
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
            print(instance.get("PublicIpAddress"))


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

def stop_instance(instance_id,ec2_client):

    response = ec2_client.stop_instances(InstanceIds=[instance_id])
    print(response)

def terminate_instance(instance_id, ec2_client):

    response = ec2_client.terminate_instances(InstanceIds=[instance_id])
    print(response)



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

## Create EC2 key pair
def create_key_pair():
    print("I am inside key pair generation..")
    ec2_client = boto3.client("ec2", region_name="us-east-1")
    key_pair = ec2_client.create_key_pair(KeyName="ec2-key-pair")

    private_key = key_pair["KeyMaterial"]

    ## write private key to file with 400 permissions
    with os.fdopen(os.open("F:/RekhuAll/AWS/PythonAllAWS/aws_ec2_key.pem", os.O_WRONLY | os.O_CREAT, 0o400), "w+") as handle: handle.write(private_key)

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



def create_security_group(ec2_client, vpc_id:str = None, tags:list = None) -> str:
     #Create a security group and allow SSH inbound rule through the VPC
    response = ec2_client.describe_vpcs()
    if vpc_id is None:
        vpc_id = response.get('Vpcs', [{}])[0].get('VpcId', '')
    try:
        response = ec2_client.create_security_group(
            GroupName='SSH-ONLY', 
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
    except botocore.exceptions.ClientError as err:
        print(err)


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




def run_command_in_ec2_ssh(
    user_name:str,
    instance_id:str,
    pem_location:str,
    ec2_client,
    command:str,
    ):

    # user_name='ubuntu'
    # instance_id='i-08h873123123' #just an example
    # pem_addr='/Users/jimmyleu/Development/AWS/JL-gismo-mac13.pem' # folder path to aws instance key
    # aws_region='us-east-1' 

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


    (stdin, stdout, stderr) = ssh.exec_command(command)
    for line in stdout.readlines():
        print (line)

    for err in stderr.readlines():
        print(stderr)

    ssh.close()

def check_if_ec2_ready(instance_id, wait_time, delay) :
    ec2 = boto3.resource('ec2')
    instances = ec2.instances.filter(Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
    print(instances)
    p2_instance = None
    while wait_time > 0 or p2_instance is None:
        for instance in instances:
            if (instance.id==instance_id):
                p2_instance=instance
                return p2_instance
        wait_time -= delay
        time.sleep(delay)
        logger.info(f"Wait: {wait_time}...")
    logger.info(f"Cannot find running instance: {instance_id}")
    return None


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
            # echo 'install python3.8' ' >> /home/ec2-user/installation.txt

            # # install eksctl
            # curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
            # sudo mv /tmp/eksctl /usr/local/bin
            # echo 'install eksctl' ' >> /home/ec2-user/installation.txt
            # # install aws cli
            # curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
            # unzip awscliv2.zip
            # sudo ./aws/install
            # echo 'install aws cli' >> /home/ec2-user/installation.txt
            # # install kubectl
            # export RELEASE=1.22.0 # check AWS to get the latest kubectl version
            # curl -LO https://storage.googleapis.com/kubernetes-release/release/v$RELEASE/bin/linux/amd64/kubectl
            # chmod +x ./kubectl
            # sudo mv ./kubectl /usr/local/bin/kubectl
            # echo 'install kubectl' >> /home/ec2-user/installation.txt
            # # kubectl version --client  2>&1 | tee /home/ec2-user/installation.txt
            # # install docker
            # sudo amazon-linux-extras install docker -y
            # # start docker server
            # sudo service docker start
            # sudo usermod -a -G docker ec2-user
            # # check docker is on
            # sudo chkconfig docker on
            # # install docker-compose
            # sudo curl -L https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m) -o /usr/local/bin/docker-compose
            # sudo chmod +x /usr/local/bin/docker-compose
            # # check docker-compose verison
            # docker-compose version
            # echo 'install docker-compose' >> /home/ec2-user/installation.txt
            # # install gismo-cloud-deploy
            # git clone https://github.com/slacgismo/gismo-cloud-deploy.git /home/ec2-user/gismo-cloud-deploy
            # echo 'git clone gismo-cloud-deploy' >> /home/ec2-user/installation.txt
            # cd /home/ec2-user/gismo-cloud-deploy/gismoclouddeploy/services/
            # # create virtual environment 
            # python3.8 -m venv venv
            # echo 'create virtual environment' >> /home/ec2-user/installation.txt
            # source ./venv/bin/activate
            # pip install --upgrade pip
            # pip install -r requirements.txt
            # pip install .
            # echo 'run pip install' >> /home/ec2-user/installation.txt

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



def stop_ec2_bastion(config_file:str,pem_location:str,aws_access_key:str,aws_secret_access_key:str, aws_region:str) -> str:
    s3_client = connect_aws_client(
            client_name="s3",
            key_id=aws_access_key,
            secret=aws_secret_access_key,
            region=aws_region,
        )
    ec2 = boto3.resource('ec2')
    config_json = modiy_config_parameters(
            configfile=config_file,
            aws_access_key=aws_access_key,
            aws_secret_access_key=aws_secret_access_key,
            aws_region=aws_region,
            s3_client= s3_client,
        )
    ec2_instance_id = config_json['aws_config']['ec2_instance_id']
    res  = ec2.instances.filter(InstanceIds = [ec2_instance_id]).stop() #for stopping an ec2 instance
    print(f"stop {ec2_instance_id}: {res}")
    return 

def terminate_ec2_bastion(config_file:str,pem_location:str,aws_access_key:str,aws_secret_access_key:str, aws_region:str) -> str:
    s3_client = connect_aws_client(
            client_name="s3",
            key_id=aws_access_key,
            secret=aws_secret_access_key,
            region=aws_region,
        )
    ec2 = boto3.resource('ec2')
    config_json = modiy_config_parameters(
            configfile=config_file,
            aws_access_key=aws_access_key,
            aws_secret_access_key=aws_secret_access_key,
            aws_region=aws_region,
            s3_client= s3_client,
        )
    ec2_instance_id = config_json['aws_config']['ec2_instance_id']
    res_stop = ec2.instances.filter(InstanceIds = [ec2_instance_id]).stop() #for stopping an ec2 instance
    print(f"stop {ec2_instance_id}: {res_stop}")
    res_term  = ec2.instances.filter(InstanceIds = [ec2_instance_id]).terminate() #for terminate an ec2 instance
    print(f"terminate {ec2_instance_id}: {res_term}")
    return 

