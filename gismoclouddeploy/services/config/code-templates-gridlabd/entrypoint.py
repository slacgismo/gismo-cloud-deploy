import logging

from os.path import exists
from datetime import datetime
from .my_modules import read_csv_from_s3
import subprocess
import os

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
    models_path = "/app/project/gridlabd-models/gridlabd-4/taxonomy"

    # list all files in folder:
    glmfiles = []
    for _file in os.listdir(models_path):
        if _file.endswith(".glm"):
            # Prints only text file present in My Folder
            file = models_path + "/" + _file
            glmfiles.append(file)

    for _file in glmfiles:
        try:
            command = ["gridlabd", _file]
            print(command)
            proc = subprocess.Popen(
                command, cwd="/usr/local/src/gridlabd", stdout=subprocess.PIPE
            )
            while True:
                line = proc.stdout.readline()
                if not line:
                    break
                # the real code does filtering here
                print("run validate:", line.rstrip())
        except KeyboardInterrupt as e:
            logger.error(f"Invoke k8s process file error:{e}")
            # res.terminate()
            proc.terminate()

    save_data = {"data": "this gridlabd test_R2-12.47-1.glm"}
    # # ==================== Modify your code above ==================== ##
    return save_data
