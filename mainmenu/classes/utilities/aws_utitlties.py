from genericpath import exists
from stat import S_ISDIR
import boto3
from mypy_boto3_ec2.client import EC2Client
from mypy_boto3_s3.client import S3Client
from mypy_boto3_sts.client import STSClient
from mypy_boto3_ec2.service_resource import EC2ServiceResource
from os.path import basename
import os
import botocore
import logging
import paramiko
import time
from pathlib import Path
from .convert_yaml import check_if_path_exist_and_create
from .update_sshconfig import add_public_ip_to_sshconfig
from asyncio import exceptions
import re


def check_aws_validity(key_id: str, secret: str) -> bool:
    try:
        client = boto3.client(
            "s3", aws_access_key_id=key_id, aws_secret_access_key=secret
        )
        client.list_buckets()
        return True

    except Exception as e:
        return False


def check_environment_is_aws() -> bool:
    datasource_file = "/var/lib/cloud/instance/datasource"
    if exists(datasource_file):
        return True
    else:
        return False


def connect_aws_client(client_name: str, key_id: str, secret: str, region: str):
    try:
        client = boto3.client(
            client_name,
            region_name=region,
            aws_access_key_id=key_id,
            aws_secret_access_key=secret,
        )
        return client

    except Exception:
        raise Exception("AWS Validation Error")


def connect_aws_resource(resource_name: str, key_id: str, secret: str, region: str):
    try:
        resource = boto3.resource(
            resource_name,
            region_name=region,
            aws_access_key_id=key_id,
            aws_secret_access_key=secret,
        )
        return resource
    except Exception:
        raise Exception("AWS Validation Error")


def check_bucket_exists_on_s3(s3_client: S3Client, bucket_name: str) -> bool:
    try:
        buckets_list = s3_client.list_buckets()
        print(buckets_list)
        for bucket in buckets_list:
            if bucket_name == bucket:
                return True
            return False

    except Exception as e:
        raise Exception(f"List S3 bucket error: {e}")


def get_security_group_id_with_name(group_name: str, ec2_client) -> str:
    if group_name is None:
        raise ValueError("group_name is None")
    try:
        response = ec2_client.describe_security_groups(
            Filters=[dict(Name="group-name", Values=[group_name])]
        )
        if len(response["SecurityGroups"]) > 0:
            group_id = response["SecurityGroups"][0]["GroupId"]
            return group_id
        else:
            return None
    except Exception as e:
        raise Exception(f"{e}")


def get_default_vpc_id(ec2_client: EC2Client) -> str:
    try:
        response = ec2_client.describe_vpcs()
        if len(response.get("Vpcs", [{}])) > 0:
            vpc_id = response.get("Vpcs", [{}])[0].get("VpcId", "")
            return vpc_id
        else:
            return None
    except botocore.exceptions.ClientError as err:
        raise Exception(err)


def check_keypair_exist(ec2_client: EC2Client, keypair_anme: str) -> bool:

    logging.info("Check keypair exist")
    try:
        keypairs = ec2_client.describe_key_pairs(KeyNames=[keypair_anme])
        if len(keypairs) > 0:
            return True
        else:
            return False
    except botocore.exceptions.ClientError as err:
        print(f"{keypair_anme} does not exist")
        return False


def get_ec2_instance_id_and_keypair_with_tags(
    ec2_client: EC2Client, tag_key_f: str, tag_val_f: str
) -> dict:
    try:

        response = ec2_client.describe_instances(
            Filters=[{"Name": "tag:" + tag_key_f, "Values": [tag_val_f]}]
        )
        Reservations = response["Reservations"]
        # print(response['Reservations'])
        if len(Reservations) > 0:
            if "Instances" in Reservations[0] and len(Reservations[0]["Instances"]) > 0:
                instance_id = Reservations[0]["Instances"][0]["InstanceId"]
                KeyName = Reservations[0]["Instances"][0]["KeyName"]
                State = Reservations[0]["Instances"][0]["State"]
                # print(Reservations[0]['Instances'][0])
                return {"InstanceId": instance_id, "KeyName": KeyName, "State": State}

        return None
    except botocore.exceptions.ClientError as err:
        raise Exception(err)


def get_default_vpc_id(ec2_client: EC2Client) -> str:
    logging.info("get default VPC id ")
    try:
        response = ec2_client.describe_vpcs()
        if len(response) > 0:
            vpc_id = response.get("Vpcs", [{}])[0].get("VpcId", "")
            return vpc_id
        else:
            return None
    except Exception as e:
        raise Exception(f"Get default vpc id failed")


def check_vpc_id_exists(ec2_client: EC2Client, vpc_id: str) -> bool:
    try:
        response = ec2_client.describe_vpcs(
            Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
        )
        resp = response["Vpcs"]
        if resp:
            return True
    except Exception as e:
        logging.error("FInd VPC id error")
    return False


def check_sg_group_name_exists_and_return_sg_id(
    ec2_client: EC2Client, group_name: str
) -> str:
    logging.info("Check security group id ")
    try:
        response = ec2_client.describe_security_groups(
            GroupNames=[group_name],
        )

        if len(response["SecurityGroups"]) > 0:
            return response["SecurityGroups"][0]["GroupId"]

    except Exception as e:
        logging.error(f"FInd security group error :{e}")
    return None


def check_keypair_name_exists(ec2_client: EC2Client, keypair_name: str) -> bool:
    logging.info("Check key pairname ")
    try:
        response = ec2_client.describe_key_pairs(KeyNames=[keypair_name])
        if len(response) > 0:
            logging.info(f" {keypair_name} exists")
            return True
    except Exception as e:
        logging.error(f"{keypair_name} does not exist")
        return False


def get_ec2_state_from_id(ec2_client: EC2Client, id: str) -> str:
    """
    Get ec2 state from instacne id

    Parameters
    ----------
    :params ec2_client: boto3 EC2 client object
    :params str id: ec2 instance id

    Return
    ------
    :return str -> ec2 state
    """
    # check ec2 status
    response = ec2_client.describe_instance_status(
        InstanceIds=[id], IncludeAllInstances=True
    )
    # print(f"response : {response}")
    state = None
    for instance in response["InstanceStatuses"]:
        instance_id = instance["InstanceId"]
        if instance_id == id:
            # system_status = instance["SystemStatus"]
            # instance_status = instance["InstanceStatus"]
            state = instance["InstanceState"]["Name"]
            return state
    return None


def get_iam_user_name(sts_client: STSClient) -> str:
    """
    Get iam user name and remove special characters

    Parameters
    ----------
    :params sts_client: boto3 STS client object

    Return
    ------
    :return str -> iam user name
    """
    try:
        response = sts_client.get_caller_identity()
        if "Arn" in response:
            # print('Arn:', response['Arn'])
            arn = response["Arn"]
            base, _user_name = arn.split("/")
            # remove special charaters
            username = re.sub("[^A-Za-z0-9]+", "", _user_name)
            return username
        return None
    except botocore.exceptions.ClientError as err:
        raise Exception(err)


def delete_security_group(ec2_client: EC2Client, group_id: str):
    try:
        delete_sg = ec2_client.delete_security_group(GroupId=group_id)
        logging.info("SG Deleted")
    except botocore.exceptions.ClientError as err:
        raise Exception(err)


def delete_key_pair(ec2_client: EC2Client, key_name: str):
    """
    Delete key pair of AWS

    Parameters
    ----------
    :params ec2_client: boto3 EC2 client object
    :params str key_name: key name

    """
    try:
        ec2_client.delete_key_pair(KeyName=key_name)
        logging.info("Key pair deleted")
    except botocore.exceptions.ClientError as err:
        raise Exception(err)


def check_if_ec2_ready_for_ssh(
    instance_id: str = None,
    wait_time: int = 60,
    delay: int = 3,
    pem_location: str = None,
    user_name: str = None,
    ec2_resource: EC2ServiceResource = None,
) -> bool:
    """
    Check ec2 state from instance id. If the ec2 state is not running, waking up ec2, and try ssh connection.

    Parameters
    ----------
    :params ec2_resource: boto3 EC2 resource object
    :params str user_name: ec2 login user
    :params str pem_location: local key file
    :params str instance_id: EC2 instance id
    :params str wait_time: Total wait time of waking up ec2 instance
    :params str delay: Interval of wait time

    Return
    ------
    return bool : If ssh connection failed, return False, else return True
    """
    instances = ec2_resource.instances.filter(
        Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
    )

    p2_instance = None
    while wait_time > 0:
        for instance in instances:

            if instance.id == instance_id:
                p2_instance = instance
                logging.info(f"{instance_id} is running")
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                privkey = paramiko.RSAKey.from_private_key_file(pem_location)
                try:
                    ssh.connect(
                        p2_instance.public_dns_name, username=user_name, pkey=privkey
                    )
                except Exception as e:
                    logging.warning(f"SSH to {instance_id} failed, try again")
                    continue

                logging.info(f"{instance_id} is ready to connect SSH")
                return True
        wait_time -= delay
        time.sleep(delay)
        logging.info(f"Wait: {wait_time}...")

    return False


def create_instance(
    ec2_client: EC2Client,
    ImageId: str,
    InstanceType: str,
    key_piar_name: str,
    tags: dict,
    volume: int,
    SecurityGroupIds: list,
) -> str:
    """
    Create an EC2 instance from boto3 client
    :param ec2_client:          the boto3 ec2 client
    :param ImageId:             the aws ec2 instance image id
    :param InstanceType:        the instance type: You havce to use at least t2.medium to run this application
    :param key_piar_name:       the key pair name
    :param tags:                the tages in ec2
    :param volume:              the ec2 stoarge
    :param SecurityGroupIds:    the security group ids
    """
    instances = ec2_client.run_instances(
        ImageId=ImageId,
        MinCount=1,
        MaxCount=1,
        InstanceType=InstanceType,
        KeyName=key_piar_name,
        UserData="""
            #!/bin/bash
            sudo yum update -y
            sudo yum install git -y
            """,
        TagSpecifications=[{"ResourceType": "instance", "Tags": tags}],
        SecurityGroupIds=SecurityGroupIds,
        BlockDeviceMappings=[
            {
                "DeviceName": "/dev/xvda",
                "Ebs": {
                    "DeleteOnTermination": True,
                    "VolumeSize": int(volume),
                    "VolumeType": "gp2",
                },
            },
        ],
    )
    instancesID = instances["Instances"][0]["InstanceId"]
    print(instances["Instances"][0]["InstanceId"])

    return instancesID


def get_public_ip(ec2_client: EC2Client, instance_id: str):
    reservations = ec2_client.describe_instances(InstanceIds=[instance_id]).get(
        "Reservations"
    )

    for reservation in reservations:
        for instance in reservation["Instances"]:

            return instance.get("PublicIpAddress")


def run_command_in_ec2_ssh(
    user_name: str,
    instance_id: str,
    pem_location: str,
    ec2_resource,
    command: str,
):
    """
    Check if AWS security group with name, if the security group with name does not exist, it create a new one.
    :param user_name:       the login user of ec2
    :param instance_id:     the instance id of ec2
    :param pem_location:    the pem file path
    :param ec2_resource:    the boto3 resource
    :param command:         the ssh command
    """
    # ec2 = boto3.resource('ec2')
    instances = ec2_resource.instances.filter(
        Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
    )

    p2_instance = None
    for instance in instances:
        if instance.id == instance_id:
            p2_instance = instance
            break
    if p2_instance is None:
        raise Exception(f"ssh: {instance_id} is not found")

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    privkey = paramiko.RSAKey.from_private_key_file(pem_location)
    ssh.connect(p2_instance.public_dns_name, username=user_name, pkey=privkey)
    print("started...")
    stdin, stdout, stderr = ssh.exec_command(command, get_pty=True)

    for line in iter(stdout.readline, ""):
        print(line, end="")
    if stdout.channel.recv_exit_status() != 0:
        raise Exception(f"exec ssh command failed {stderr}")
    print("finished.")
    ssh.close()


def create_security_group(
    ec2_client: EC2Client,
    vpc_id: str = None,
    tags: list = None,
    group_name: str = "SSH-ONLY",
) -> dict:
    """
    Check if AWS security group with name, if the security group with name does not exist, it create a new one.
    :param vpc_id:      the vpc id of security group
    :param tags:        the tags in security group
    :param group_name:  the name of security group
    """
    try:
        response = ec2_client.create_security_group(
            GroupName=group_name,
            Description="only allow SSH traffic",
            VpcId=vpc_id,
            TagSpecifications=[{"ResourceType": "security-group", "Tags": tags}],
        )
        security_group_id = response["GroupId"]
        print("Security Group Created %s in vpc %s." % (security_group_id, vpc_id))
        data = ec2_client.authorize_security_group_ingress(
            GroupId=security_group_id,
            IpPermissions=[
                {
                    "IpProtocol": "tcp",
                    "FromPort": 22,
                    "ToPort": 22,
                    "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                }
            ],
        )
        print("Ingress Successfully Set %s" % data)
        # tag = security_group.create_tags(Tags=tags)
        return {"security_group_id": [security_group_id], "vpc_id": vpc_id}
    except botocore.exceptions.ClientError as err:
        print(err)


def create_key_pair(ec2_client: EC2Client, keyname: str, file_location: str):
    """
    create ec2 keypair and download pem file
    :param ec2_client:       boto3 ec2 client object
    :param keyname:          keypair name
    :param file_location     keypair pem file download local path
    """
    try:
        key_pair = ec2_client.create_key_pair(KeyName=keyname)
    except Exception as e:
        logging.error(e)
        raise f"Create key pair: {keyname} Failed"

    private_key = key_pair["KeyMaterial"]
    check_if_path_exist_and_create(file_location)
    ## write private key to file with 400 permissions
    with os.fdopen(
        os.open(f"{file_location}/{keyname}.pem", os.O_WRONLY | os.O_CREAT, 0o400), "w+"
    ) as handle:
        handle.write(private_key)
    logging.info(f"Create {keyname} success, file location: {file_location}")
    return


def ssh_upload_folder_to_ec2(
    user_name: str,
    instance_id: str,
    pem_location: str,
    ec2_resource: EC2ServiceResource,
    local_project_path_base: str,
    remote_project_path_base: str,
):
    """
    Upload local temp project folder  to remote temp project folder
    1. list all files in local path
    2. check if relative folder exists on remote path
    3. if not exist, create a new remote path
    4. upload all files to remote folder

    Params
    ----------------------------------------------------------
    :param user_name:          login user of ec2
    :param instance_id:         EC2 instance id
    :param pem_location:        local pem file
    :param ec2_resource:        Boto3 ec2 resource
    :param local_project_path_base:         loca project path folder : /Users/<local-username>/Development/gismo/gismo-cloud-deploy/temp/solardatatools
    :param remote_project_path_base:        remote project path folder: /home/{user_name}/gismo-cloud-deploy/temp/solardatatools
    """

    # ec2 = boto3.resource('ec2')
    instances = ec2_resource.instances.filter(
        Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
    )
    print(instances)
    p2_instance = None
    for instance in instances:
        if instance.id == instance_id:
            p2_instance = instance
            break

    if p2_instance is None:
        raise Exception(f"{instance_id} does not exist")

    # check if directory exist
    local_files_list = get_all_files_in_local_dir(local_dir=local_project_path_base)
    # print(local_files_list)
    # conver local files path to remote path
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    privkey = paramiko.RSAKey.from_private_key_file(pem_location)
    ssh.connect(p2_instance.public_dns_name, username=user_name, pkey=privkey)

    path_set = set()
    upload_local_to_remote_dict = {}

    # replcae local path to remote path
    for file in local_files_list:
        path, filename = os.path.split(file)
        print(f"path: {path}, filename:{filename}")

        relative = Path(path).relative_to(Path(local_project_path_base))
        new_path = remote_project_path_base
        if str(relative) == ".":
            upload_local_to_remote_dict[file] = (
                remote_project_path_base + f"/{filename}"
            )
        else:
            upload_local_to_remote_dict[file] = (
                remote_project_path_base + f"/{relative}/{filename}"
            )
            new_path = remote_project_path_base + f"/{relative}"
        path_set.add(new_path)

    # check if path exist, if not create path
    for folder in path_set:
        # remote_dir = remote_folder + "/"+ folder
        print(f"remote_dir: {folder}")
        command = f'if [ ! -d "{folder}" ]; then \n  mkdir -p {folder} \n echo ssh: create {folder}  \n fi'
        (_, stdout, _) = ssh.exec_command(command)
        for line in stdout.readlines():
            logging.info(line)
    logging.info(f"Create folder :{folder} success")

    # uplaod file
    ftp_client = ssh.open_sftp()
    for key, value in upload_local_to_remote_dict.items():
        try:
            ftp_client.put(key, value)
            logging.info(f"upload :{key} to {value} success")
        except Exception as e:
            logging.error(f"upload :{key} to {value} failed: {e}")
    ftp_client.close()
    logging.info(
        f"Uplodate {local_project_path_base} to {remote_project_path_base} success!!!"
    )
    return


def get_all_files_in_local_dir(local_dir: str) -> list:
    """
    list all files in local directory

    Parameters
    ----------
    :param str local_dir: local directory

    Returns
    -------
    :return list of files
    """
    all_files = list()

    if os.path.exists(local_dir):
        files = os.listdir(local_dir)
        for x in files:
            filename = os.path.join(local_dir, x)
            print("filename:" + filename)
            # isdir
            if os.path.isdir(filename):
                all_files.extend(get_all_files_in_local_dir(filename))
            else:
                all_files.append(filename)
        else:
            print("{} does not exist".format(local_dir))
    else:
        print(f"{local_dir} doese not exist")
    return all_files


def upload_file_to_ec2(
    user_name: str,
    instance_id: str,
    pem_location: str,
    local_file: str,
    remote_file: str,
    ec2_resource: EC2ServiceResource,
):
    """
    Upload sinlge file to remote AWS EC2

    Parameters
    ----------
    :param str user_name: ec2 login user
    :param str instance_id: ec2 instance id
    :param str pem_location: keypair path and name
    :param str local_file: local file path and name
    :param str remote_file: remote file path and name
    :param EC2ServiceResource ec2_resource: boto3. ec2 resource object
    """

    instances = ec2_resource.instances.filter(
        Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
    )
    print(instances)

    for instance in instances:
        if instance.id == instance_id:
            p2_instance = instance
            break

    # check if directory exist
    path, tail = os.path.split(remote_file)
    print(f"path :{path}")

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    privkey = paramiko.RSAKey.from_private_key_file(pem_location)
    ssh.connect(p2_instance.public_dns_name, username=user_name, pkey=privkey)

    folder = f"/home/{user_name}/gismo-cloud-deploy/created_resources_history"
    logging.info(f"Crete{folder}")
    command = f'if [ ! -d "{folder}" ]; then \n echo ssh: {folder} does not exist \n mkdir {folder} \n echo ssh: create {folder}  \n fi'
    (_, stdout, _) = ssh.exec_command(command)
    for line in stdout.readlines():
        print(line)

    command = f'if [ ! -d "{path}" ]; then \n echo {path} does not exist \n mkdir {path} \n echo create {path} \n fi'
    (_, stdout, _) = ssh.exec_command(command)
    for line in stdout.readlines():
        print(line)

    # upload file
    ftp_client = ssh.open_sftp()
    ftp_client.put(local_file, remote_file)
    ftp_client.close()
    print(f"Uplodate {local_file} to {remote_file} success")
    return


def ssh_download_folder_from_ec2(
    user_name: str,
    instance_id: str,
    pem_location: str,
    local_folder: str,
    remote_folder: str,
    ec2_resource: EC2ServiceResource,
):
    """
    Download a folder from AWS EC2 to local folder

    Parameters
    ----------
    :param str user_name: ec2 login user
    :param str instance_id: ec2 instance id
    :param str pem_location: keypair path and name
    :param str local_folder: local folder path
    :param str remote_folder: remote folder path
    :param EC2ServiceResource ec2_resource: boto3. ec2 resource object
    """
    instances = ec2_resource.instances.filter(
        Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
    )
    print(instances)
    p2_instance = None
    for instance in instances:
        if instance.id == instance_id:
            p2_instance = instance
            break

    if p2_instance is None:
        raise Exception(f"{instance_id} does not exist")

    ssh = paramiko.SSHClient()

    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    privkey = paramiko.RSAKey.from_private_key_file(pem_location)
    ssh.connect(p2_instance.public_dns_name, username=user_name, pkey=privkey)
    logging.info(f"get recursive from {remote_folder} to {local_folder}")
    ftp_client = ssh.open_sftp()
    sftp_get_recursive(remote_folder, local_folder, ftp_client)
    ftp_client.close()

    logging.info(f"Download {remote_folder} to {local_folder} success!!!")
    return


def sftp_get_recursive(path: str, dest: str, sftp: paramiko.SSHClient):
    logging.info("Download files recursive!!")
    item_list = sftp.listdir_attr(path)
    dest = str(dest)
    if not os.path.isdir(dest):
        os.makedirs(dest, exist_ok=True)

    for item in item_list:
        logging.info(f"download {item.filename}")
        mode = item.st_mode
        if S_ISDIR(mode):
            sftp_get_recursive(
                path + "/" + item.filename, dest + "/" + item.filename, sftp
            )
        else:
            sftp.get(path + "/" + item.filename, dest + "/" + item.filename)
    logging.info(f"Download {path} success")


def get_public_ip_and_update_sshconfig(
    wait_time: int = 90,
    delay: int = 5,
    ec2_instance_id: str = None,
    ec2_client: EC2Client = None,
    system_id: str = None,
    login_user: str = None,
    keypair_name: str = None,
    local_pem_path: str = None,
):
    """
    Get ec2 public and update local .ssh/config file

    Parameters
    ----------
    :param int wait_time:       total wait time of fetching public ip of ec2
    :param int delay:           interval of fetching public ip of ec2
    :param str ec2_instance_id: ec2 instance id
    :param str ec2_client:      boto3 client object
    :param str system_id:       system id
    :param str login_user:      ec2 login user
    :param str keypair_name:    ec2 keypair name
    :param str local_pem_path:  local pem file path
    """
    ec2_public_ip = None

    while wait_time > 0 and ec2_public_ip is None:
        ec2_public_ip = get_public_ip(
            ec2_client=ec2_client, instance_id=ec2_instance_id
        )
        wait_time -= delay
        time.sleep(delay)
        logging.info(f"Waiting {wait_time}... public ip:{ec2_public_ip}")
    if wait_time <= 0:
        raise Exception("Get public ip wait overtime")

    add_public_ip_to_sshconfig(
        public_ip=ec2_public_ip,
        host=system_id,
        login_user=login_user,
        key_pair_name=keypair_name,
        local_pem_path=local_pem_path,
    )


def check_eks_cluster_with_name_exist(
    eks_client=None, cluster_name: str = None
) -> bool:
    """
    search eks cluster with name. If the name is found, return True, else return False

    Parameters
    ----------
    :param int eks_client:  bot3 eks client object
    :param str cluster_name:  EKS cluster name

    Returns
    -------
    :return boolen: Retrun True if found else return False.
    """
    try:
        response = eks_client.list_clusters()
        if len(response) == 0:
            raise Exception("EKS Resposse has no data")

        if "clusters" in response:
            cluster_list = response["clusters"]
            for name in cluster_list:
                if name == cluster_name:
                    return True
                else:
                    logging.warning(f"Other eks cluster: {name}")

        return False
    except Exception as e:
        raise Exception(f"Check eks name failed :{e}")
