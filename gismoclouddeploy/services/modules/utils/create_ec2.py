import logging
from time import time
from .invoke_function import exec_eksctl_create_cluster,exec_eksctl_delete_cluster
from .modiy_config_parameters import modiy_config_parameters
from os.path import exists
import boto3
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

def create_ec2_bastion(config_file:str, aws_access_key:str,aws_secret_access_key:str, aws_region:str) -> str:
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


    # config_json = modiy_config_parameters(
    #         configfile=config_file,
    #         aws_access_key=aws_access_key,
    #         aws_secret_access_key=aws_secret_access_key,
    #         aws_region=aws_region,
    #         s3_client= s3_client,
    #     )
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
    tags = [
        {"Key": "Name", "Value": "GCD_bastion_boto3-5"}, 
        {"Key": "project", "Value": "pvinsight"},
        {"Key": "manageBy", "Value": "boto3"}
    ]
    SecurityGroupIds = [
            'sg-0009d2a9a2498f600',
        ]
    # # stop_instance(instance_id="i-0a691aedf18d7aae9", ec2_client = ec2_client)
    # # time.sleep(5)
    # # terminate_instance(instance_id="i-0a691aedf18d7aae9", ec2_client = ec2_client)

    # instance_id = create_instance(
        
    #     ImageId="ami-0568773882d492fc8",
    #     InstanceType = "t2.large",
    #     key_piar_name = "JL-gismo-mac13",
    #     ec2_client=ec2_client,
    #     tags= tags,
    #     SecurityGroupIds = SecurityGroupIds

    # )
    # print(f"instance_id :{instance_id}")
    # print("wait 10 sec")
    # time.sleep(10)
 
    # instance_id = "i-0443c269cef18d87b"
    # public_id = get_public_ip(
    #     ec2_client=ec2_client,
    #     instance_id=instance_id
    # )
    pem_location='/Users/jimmyleu/Development/AWS/JL-gismo-mac13.pem' # folder path to aws instance key
    run_command_in_ec2_ssh(
        user_name="ec2-user",
        instance_id="i-0443c269cef18d87b",
        pem_location=pem_location,
        ec2_client=ec2_client
    )


    # print(public_id)
    # get_running_instances(ec2_client=ec2_client)
    # i-0a691aedf18d7aae9
    # return public_id


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
            # amazon-linux-extras install python3.8
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
def create_aws_vpc(ec2_client, tags) -> str:
    # ec2_client = boto3.client("ec2", region_name="us-east-2")
    vpc = ec2_client.create_vpc( CidrBlock='172.16.0.0/16' )
    # vpc.create_tags(Tags=[{"Key": "Name", "Value": "eks_vpc"},{"Key": "manageBy", "Value": "boto3"}])
    # vpc.wait_until_available()

    print ("Successfully created vpc details are -  {}".format(vpc))
    subnet = ec2_client.create_subnet(CidrBlock = '172.16.2.0/24', VpcId= vpc['Vpc']['VpcId'])
    print("Successfully created subnet details are -  {}".format(subnet))
    ec2_client.create_tags(Resources=[vpc['Vpc']['VpcId']], Tags=tags)
    
    return subnet['Subnet']['SubnetId']




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
    ):

    # user_name='ubuntu'
    # instance_id='i-08h873123123' #just an example
    # pem_addr='/Users/jimmyleu/Development/AWS/JL-gismo-mac13.pem' # folder path to aws instance key
    # aws_region='us-east-1' 

    ec2 = boto3.resource('ec2')
    instances = ec2.instances.filter(Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
    print(instances)

    for instance in instances:
        if (instance.id==instance_id):
            p2_instance=instance
            break;



    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    privkey = paramiko.RSAKey.from_private_key_file(pem_location)
    ssh.connect(p2_instance.public_dns_name,username=user_name,pkey=privkey)


    # cmd_to_run='dropbox start && source /home/ubuntu/anaconda3/bin/activate py36 && cd /home/ubuntu/xx/yy/ && python3 func1.py' #you can seperate two shell commands by && or ;

    command = f"git clone https://github.com/slacgismo/gismo-cloud-deploy.git /home/ec2-user/gismo-cloud-deploy;cd /home/ec2-user/gismo-cloud-deploy"
    (stdin, stdout, stderr) = ssh.exec_command(command)
    for line in stdout.readlines():
        print (line)
    # stdin4, stdout4, stderr4 = ssh.exec_command(cmd_to_run,timeout=None, get_pty=False)
    # print("------")
    # print(stdout4)

    ssh.close()

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