import logging

from os.path import exists
from datetime import datetime
from .my_modules import read_csv_from_s3
import subprocess
import os
import boto3
from genericpath import exists
import pandas as pd
import shutil
from subprocess import run, PIPE

logger = logging.getLogger()
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s: %(levelname)s: %(message)s"
)


def entrypoint(
    data_bucket: str = None,
    curr_process_file: str = None,
    curr_process_column: str = None,
    aws_access_key: str = None,
    aws_secret_access_key: str = None,
    aws_region: str = None,
    solver_name: str = None,
    solver_file: str = None,
) -> dict:
    """
    Entrypoint function to wrap your code
    :param str user_id: This user_id is generated in cli command and pass to here(worker). This user id is required to used in sns, dynamodb and sqs services
    :param str data_bucket: This data_bucket is the s3 bucket that contains data files.
    :param str curr_process_file: Current process file. This file name is one of the column name in logs file.()
    :param str curr_process_column: Current proccess column name. This column name is one of the column name in logs file.
    :param str aws_access_key:
    :param str aws_secret_access_key:
    :param str aws_region:
    :param str solver_name: The solver name that defined in config.yaml
    :param str solver_file: The solver file location inside worker. This file location is defined in config.yaml.
    :return dict json_message: Return a json format object
    """

    ## ==================== Modify your code below ==================== ##
    print("=========================================")
    print(f"curr_process_file : {curr_process_file}")
    print("=========================================")

    break_file_path = curr_process_file.split("/")
    target_process_file = break_file_path[-1]
    project_folder = "/app/project"
    # target_save_file = project_folder + download_file

    # download process files
    try:
        s3_client = boto3.client(
            "s3",
            region_name=aws_region,
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_access_key,
        )
        s3_resource = boto3.resource(
            "s3",
            region_name=aws_region,
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_access_key,
        )
        # res = s3_client.download_file(data_bucket, curr_process_file, save_file)
        # print(res)
    except Exception as e:
        logger.error(f"AwS credentials failed: {e}")

    # change current folder to app/project
    os.chdir("/app/project/")
    cwd = os.getcwd()
    print(f"cwd: {cwd}")

    download_necessary_folder = ["load_shape_2018_forecast", "weather_data"]
    # download necessary files
    for folder in download_necessary_folder:
        downloadDirectoryFroms3(
            bucketName=data_bucket, remoteDirectoryName=folder, s3_resource=s3_resource
        )
    # load_shape_2018_forecast

    # download files list:
    # download_necessary_files_lists = [ "hosting_capacity.py",,, target_process_file]
    # try:
    #     for d_file in download_necessary_files_lists:
    #         _target_loaction_file = project_folder + "/" + d_file
    #         res = s3_client.download_file(data_bucket, curr_process_file, _target_loaction_file)
    #         print(f"Download {d_file} success")
    # except Exception as e:
    #     raise Exception(f"download {d_file} error: {e}")

    process_file = project_folder + "/" + target_process_file
    command = f"gridlabd {process_file} config.glm hosting_capacity.glm 1>>hosting_capacity.csv 2>>gridlabd.log"
    print("------------>")
    print(f"command: {command}")
    print("------------>")
    returncode = subprocess.call(command, shell=True)
    if returncode != 0:
        raise Exception(f"Error run the {command}")

    try:
        result_df = pd.read_csv("hosting_capacity.csv")
        print("--- result ===")
        print(result_df.head())
        print("--- end result ===")
    except Exception as e:
        logger.error(e)

    save_data = {"data": "this gridlabd test_R2-12.47-1.glm"}
    # # ==================== Modify your code above ==================== ##
    return save_data


def downloadDirectoryFroms3(bucketName, remoteDirectoryName, s3_resource):

    bucket = s3_resource.Bucket(bucketName)
    for obj in bucket.objects.filter(Prefix=remoteDirectoryName):
        if not os.path.exists(os.path.dirname(obj.key)):
            os.makedirs(os.path.dirname(obj.key))
        bucket.download_file(obj.key, obj.key)  # save to same path
