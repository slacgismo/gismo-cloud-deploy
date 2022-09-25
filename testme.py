
import re
import logging
import pandas as pd
import logging
import boto3 
import os
from dotenv import load_dotenv

from mainmenu.classes.utilities.aws_utitlties import connect_aws_resource
load_dotenv()
# df = pd.read_csv("init_command_logs_644.csv")
# print(df["file_name"])

# import fnmatch
# files =['this.csv','LICENSE.txt', 'lines.txt', 'listwidget.ui', 'lo1.ui', 'lo2.ui', 'lo3.ui', 'logo.png', 'logo.svg', 'lw.ui']
# matching = fnmatch.fnmatch('htis.csv', '*.csv')
# print(matching)
# txt = "Power(W)"
# x = re.search("(W)$", txt)
# if (x):
#     print("Match")


AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION")

def connect_aws_client(client_name: str, key_id: str, secret: str, region: str):
    try:
        client = boto3.client(
            client_name,
            region_name=region,
            aws_access_key_id=key_id,
            aws_secret_access_key=secret,
        )
        return client
    except Exception as e:
        raise e
        

def read_column_from_csv_from_s3(
    bucket_name: str = None, file_path_name: str = None, s3_client: str = None
) -> pd.DataFrame:
    if bucket_name is None or file_path_name is None or s3_client is None:
        return

    response = s3_client.get_object(Bucket=bucket_name, Key=file_path_name)

    status = response.get("ResponseMetadata", {}).get("HTTPStatusCode")

    if status == 200:
        result_df = pd.read_csv(response.get("Body"), nrows=1)
    else:
        print(f"Unsuccessful S3 get_object response. Status - {status}")
    return result_df


def find_matched_column_name_set(
    columns_key: str,
    bucket_name: str,
    file_path_name: str,
    s3_client: "botocore.client.S3",
) :
    """
    Find the match column name from key word. if matched column has no value inside, it will be skipped.
    If this function find exactly match with key and column name , it return the the match column name in set.
    If no exactly match key was found, it return the partial match key with longest data set.
    """
    try:
        total_columns = read_column_from_csv_from_s3(
            bucket_name=bucket_name, file_path_name=file_path_name, s3_client=s3_client
        )
    except Exception as e:
        # logger.error(f"read column from s3 failed :{e}")
        raise e
    matched_column_set = set()
    # print(total_columns)

    for column in total_columns:
        
        match = re.search(columns_key, column)
        print(match,columns_key,column)
        if (match):
            print("match")
            matched_column_set.add(column)
        # for key in columns_key:
            # if key in column:
                
    return matched_column_set



# s3_clinet = connect_aws_client(
#     's3',
#     key_id= AWS_ACCESS_KEY_ID,
#     secret=AWS_SECRET_ACCESS_KEY,
#     region=AWS_DEFAULT_REGION
# )
# match_set= find_matched_column_name_set(
#     columns_key="^Pow",
#     bucket_name='pv.insight.nrel',
#     file_path_name='PVO/PVOutput/46851.csv',
#     s3_client=s3_clinet
# )

# print(match_set)

# is_csv = re.search('.csv', 'PVO/PVOutput/46851.csv')
# if not is_csv:
#     print("not match")
# else:
#     print("match")
# print(is_csv)

# from modules.utils.InputQuestions import InputQuestions

# print(InputQuestions.is_debug_mode_questions.value)


import paramiko
import os
from stat import S_ISDIR, S_ISREG    




def ssh_download_folder_from_ec2(
    user_name:str,
    instance_id:str,
    pem_location:str,
    ec2_resource,
    local_folder:str,
    remote_folder:str,
):
    instances = ec2_resource.instances.filter(Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
    print(instances)
    p2_instance = None
    for instance in instances:
        if (instance.id==instance_id):
            p2_instance=instance
            break

    if p2_instance is None:
        raise Exception(f"{instance_id} does not exist")

    ssh = paramiko.SSHClient()
    
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    privkey = paramiko.RSAKey.from_private_key_file(pem_location)
    ssh.connect(p2_instance.public_dns_name,username=user_name,pkey=privkey)
    # if use password
    # transport = paramiko.Transport((host, port))
    # transport.connect(username=username, password=password)
    # sftp = paramiko.SFTPClient.from_transport(transport)
    # sftp_get_recursive(remote_path, local_path, sftp)
    # sftp.close()
    logging.info(f"get recursive from {remote_folder} to {local_folder}")
    ftp_client=ssh.open_sftp()
    sftp_get_recursive(remote_folder, local_folder, ftp_client)
    ftp_client.close()

    logging.info(f"Download {remote_folder} to {local_folder} success!!!")
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
            print ('{} does not exist'.format(local_dir))
    else:
        print(f"{local_dir} doese not exist")
    return all_files


def sftp_get_recursive(path, dest, sftp):

    item_list = sftp.listdir_attr(path)
    dest = str(dest)
    if not os.path.isdir(dest):
        os.makedirs(dest, exist_ok=True)

    for item in item_list:
        print(f"download {item.filename}")
        mode = item.st_mode
        if S_ISDIR(mode):
            sftp_get_recursive(path + "/" + item.filename, dest + "/" + item.filename, sftp)
        else:
            sftp.get(path + "/" + item.filename, dest + "/" + item.filename)
    print(f"Download {path} success")

from pathlib import Path
home_dir = str(Path.home())  # ~/

pem_location = home_dir +"/.ssh/gcd-jimmy-cli.pem"

ec2_resource = connect_aws_resource(
    resource_name='ec2',
    key_id=AWS_ACCESS_KEY_ID,
    secret=AWS_SECRET_ACCESS_KEY,
    region=AWS_DEFAULT_REGION
)
base_path = os.getcwd()
ssh_download_folder_from_ec2(
    user_name="ec2-user",
    instance_id="i-08eadb78b12a3970b",
    pem_location=pem_location,
    ec2_resource=ec2_resource,
    local_folder=base_path +"/temp",
    remote_folder="/home/ec2-user/gismo-cloud-deploy/temp/solardatatools/results",

)

