from genericpath import exists
from logging import Filter
import boto3
import os
import botocore
import logging

def check_aws_validity(key_id: str, secret: str) -> bool:
    try:
        client = boto3.client(
            "s3", aws_access_key_id=key_id, aws_secret_access_key=secret
        )
        client.list_buckets()
        return True

    except Exception as e:
        return False


# def check_environment_is_aws() -> bool:
#     my_user = os.environ.get("USER")
#     is_aws = True if "ec2" in my_user else False
#     return is_aws
def check_environment_is_aws() -> bool:
    datasource_file = "/var/lib/cloud/instance/datasource"
    if exists(datasource_file):
        return True
    else:
        return False
#     try:
#     with open(datasource_file) as f:
#         line = f.readlines()
#         print("I'm running on EC2!")
#         if "DataSourceEc2Local" in line[0]:
#             print("I'm running on EC2!")
# except FileNotFoundError:
#         print(f"{datasource_file} not found")

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


def check_bucket_exists_on_s3(s3_client, bucket_name:str) -> bool:
    try:
        buckets_list = s3_client.list_buckets()
        print(buckets_list)
        for bucket in buckets_list:
            if bucket_name == bucket:
                return True
            return False

    except Exception as e:
        raise Exception (f"List S3 bucket error: {e}")


    
def get_security_group_id_with_name(group_name:str, ec2_client) -> str:
    try:
        response= ec2_client.describe_security_groups(
            Filters=[
                dict(Name='group-name', Values=[group_name])
            ]
        )
        if len(response['SecurityGroups']) > 0:
            group_id = response['SecurityGroups'][0]['GroupId']
            return group_id
        else:
            return None
    except Exception as e:
        raise Exception(f"fn")


def get_default_vpc_id(ec2_client) -> str:
    try:
        response = ec2_client.describe_vpcs()
        if len(response.get('Vpcs', [{}])) > 0:
            vpc_id = response.get('Vpcs', [{}])[0].get('VpcId', '')
            return vpc_id
        else:
            return None
    except botocore.exceptions.ClientError as err:
        raise Exception(err)

def check_keypair_exist(ec2_client, keypair_anme) ->bool:
    try:
        keypairs = ec2_client.describe_key_pairs(
          KeyNames=[keypair_anme]
        )
        if len(keypairs) > 0 :
            return True
        else:
            return False
    except botocore.exceptions.ClientError as err:
        print(f"{keypair_anme} does not exist")
        return False


def get_ec2_instance_id_and_keypair_with_tags(ec2_client, tag_key_f,  tag_val_f) -> dict:
    try:
        # response = ec2_client.describe_instance_status(
        #     Filter =[
        #         [{'Name': 'tag:'+tag_key_f, 'Values': [tag_val_f]}]
        #     ]
        # )
        response = ec2_client.describe_instances(Filters=[{'Name': 'tag:'+tag_key_f, 'Values': [tag_val_f]}])

        print("---------------")
        Reservations = response['Reservations']
        # print(response['Reservations'])
        if len(Reservations)> 0:
            if 'Instances' in Reservations[0] and len(Reservations[0]['Instances']) > 0 :
                instance_id = Reservations[0]['Instances'][0]['InstanceId']
                KeyName =  Reservations[0]['Instances'][0]['KeyName']
                State = Reservations[0]['Instances'][0]['State']
                # print(Reservations[0]['Instances'][0])
                return {'InstanceId':instance_id,'KeyName':KeyName,'State':State}

        return None
    except botocore.exceptions.ClientError as err:
        raise Exception(err)

def get_default_vpc_id(ec2_client) -> str:
    logging.info("get default VPC id ")
    try:
        response = ec2_client.describe_vpcs()
        if len(response) > 0 :
            vpc_id = response.get('Vpcs', [{}])[0].get('VpcId', '')
            return vpc_id
        else:
            return None
    except Exception as e:
        raise Exception(f"Get default vpc id failed")

def check_vpc_id_exists(ec2_client,vpc_id:str) -> bool:
    try:
        response = ec2_client.describe_vpcs(
        Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
        )
        resp = response['Vpcs']
        if resp:
            return True
    except Exception as e:
        logging.error("FInd VPC id error")
    return False

def check_sg_group_name_exists_and_return_sg_id(ec2_client , group_name:str) -> str:
    logging.info("Check security group id ")
    try:
        response = ec2_client.describe_security_groups(
            GroupNames=[group_name],
        )
       
        if len(response['SecurityGroups']) > 0 :
             return (response['SecurityGroups'][0]['GroupId'])

    except Exception as e:
        logging.error(f"FInd security group error :{e}")
    return None



def check_keypair_name_exists(ec2_client ,keypair_name:str) -> bool:
    logging.info("Check key pairname ")
    try:
        response = ec2_client.describe_key_pairs(
            KeyNames=[keypair_name]
        )
        if len(response)> 0:
            logging.info(f" {keypair_name} exists")
            return True
    except Exception as e:
        logging.error(f"{keypair_name} does not exist")
        return False


def get_ec2_state_from_id(ec2_client, id) -> str:
    
    #check ec2 status
    response = ec2_client.describe_instance_status(
        InstanceIds=[id],
        IncludeAllInstances=True
    )
    print(f"response : {response}")
    state = None
    for instance in response['InstanceStatuses']:
        instance_id = instance['InstanceId']
        if instance_id == id:
        
            system_status = instance['SystemStatus']
            instance_status = instance['InstanceStatus']
            state = instance['InstanceState']
            return state
            # logging.info(f"system_status :{system_status}, instance_status:{instance_status},")
    return None
    # if  state is not None:
    #     logging.info(f"instance state : { state}")
    # else:
    #     raise Exception(f"Cannot find instance state from {self._ec2_instance_id}")