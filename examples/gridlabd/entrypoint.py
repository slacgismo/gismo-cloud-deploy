import logging
import subprocess
import os
import boto3

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
    # define model folder
    models_path = "/app/project/gridlabd-models"
    if os.path.isdir(models_path) is False:
        logger.info(f"Create local {models_path} path")
        os.mkdir(models_path)

    print("------------>>>> ")
    print(curr_process_file)
    break_file_path = curr_process_file.split("/")
    download_file = break_file_path[-1]
    print(download_file)
    # download file
    try:
        s3_client = boto3.client(
            "s3",
            region_name=aws_region,
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_access_key,
        )
        print(data_bucket)
        print(curr_process_file)
        local_file = models_path + "/" + download_file
        print(local_file)
        res = s3_client.download_file(
            data_bucket, curr_process_file, local_file)
        print(res)
    except Exception as e:
        logger.error(f"Download file error: {e}")

    command = f"gridlabd {local_file} 1>>data.csv 2>>gridlabd.log"
    print("------------>")
    print(f"command: {command}")
    print("------------>")

    returncode = subprocess.call(command, shell=True)

    if returncode != 0:
        errorObject = open("gridlabd.log", "r")
        error = errorObject.read()
        print(error)
        errorObject.close()
        raise Exception(f"Error run the {error}")
    fileObject = open("data.csv", "r")
    data = fileObject.read()
    print("------------>")
    print(f"data: {data}")
    print("------------>")
    fileObject.close()

    save_data = {"file": local_file, "data": data}
    # # ==================== Modify your code above ==================== ##
    return save_data

    # try:
    #     command = ["gridlabd", local_file]
    #     print(command)
    #     proc = subprocess.Popen(
    #         command, cwd="/usr/local/src/gridlabd", stdout=subprocess.PIPE
    #     )
    #     while True:
    #         line = proc.stdout.readline()
    #         if not line:
    #             break
    #         # the real code does filtering here
    #         print("run validate:", line.rstrip())
    # except KeyboardInterrupt as e:
    #     logger.error(f"Invoke k8s process file error: {e}")
    #     # res.terminate()
    #     proc.terminate()
    # if exists(local_file):
    #     os.remove(local_file)
    #     print(f"Delete {local_file} success")

    # save_data = {"data": "this gridlabd test_R2-12.47-1.glm"}
    # # # ==================== Modify your code above ==================== ##
    # return save_data
