from email.mime import base
import logging

from solardatatools.data_handler import DataHandler

from os.path import exists
from datetime import datetime
from .pipeline.run import run
import os
import json

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

    Parameters
    ----------
    :param str user_id: This user_id is generated in cli command and pass to here(worker). This user id is required to used in sns, dynamodb and sqs services
    :param str data_bucket: This data_bucket is the s3 bucket that contains data files.
    :param str curr_process_file: Current process file. This file name is one of the file name in logs file.()
    :param str curr_process_column: Current proccess column name. This column name is one of the column name in logs file.
    :param str aws_access_key:
    :param str aws_secret_access_key:
    :param str aws_region:
    :param str solver_name: The solver name that defined in config.yaml
    :param str solver_file: The solver file location inside worker. This file location is defined in config.yaml.

    Returns
    -------
    :return dict key value pairs: Return a json format object
    """

    ## ==================== Modify your code below ==================== ##
    # curr_process_file = "PVO/PVOutput/10284.csv"
    # curr_process_column = "Power(W)"
    logger.info(
        f"process file:{curr_process_file} , column:{curr_process_column}, solve: {solver_file}"
    )

    # check solver file exist:
    if solver_name is not None and (exists(solver_file) is False):
        raise Exception(f"solver_file:{solver_file} dose not exist")
    output_file = "output.txt"
    base_path = os.getcwd()
    output_absolute_file = base_path + f"/{output_file}"

    try:
        run(
            input_file=[curr_process_file],
            solver=solver_name,
            output_file=output_absolute_file,
            process_column=curr_process_column,
            data_bucket=data_bucket,
            aws_access_key=aws_access_key,
            aws_secret_access_key=aws_secret_access_key,
            aws_region=aws_region,
        )

        if os.path.exists(output_absolute_file):
            with open(output_absolute_file) as f:
                data = f.read()
                js = json.loads(data)

                return js
    except Exception as e:
        raise e
