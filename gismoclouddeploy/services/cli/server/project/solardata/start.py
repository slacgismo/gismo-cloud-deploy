# from project.solardatatools.models.SolarParams import SolarParams
# from project.solardatatools.models.SolarData import SolarData
import solardatatools
import socket
from datetime import datetime

# from project.utils.tasks_utils import (
#     save_solardata_to_file,
#     check_solver_licence,

# )
# from utils.aws_utils import (
#     read_csv_from_s3_with_column_and_time,
#     connect_aws_client,
# )
# import solardata_models
# import utils.aws_utils
# import project.utils.tasks_utils
from .solardata_models import SolarData, SolarParams
from utils import aws_utils
from project.tasks_utilities import tasks_utils
import logging
import time


# logger config
logger = logging.getLogger()
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s: %(levelname)s: %(message)s"
)


def entrypoint(
    task_id: str = None,
    bucket_name: str = None,
    file_path_name: str = None,
    column_name: str = None,
    start_time: str = None,
    saved_bucket: str = None,
    saved_file_path: str = None,
    saved_filename: str = None,
    solarParams: SolarParams = None,
    aws_access_key: str = None,
    aws_secret_access_key: str = None,
    aws_region: str = None,
) -> str:

    """
    Process solardatatools from file with specific column name
    :param : task id
    :param : bucket_name
    :param : file_path_name
    :param : column_name
    :param : start_time
    :param : saved_bucket
    :param : saved_file_path
    :param : saved_filename
    :param : solarParams. -> solardatatools parameters object
    :return: success messages.
    """
    if (
        bucket_name is None
        or file_path_name is None
        or column_name is None
        or saved_bucket is None
        or solarParams is None
    ):
        raise Exception("Input error")
    error_message = ""
    try:
        s3_client = aws_utils.connect_aws_client(
            client_name="s3",
            key_id=aws_access_key,
            secret=aws_secret_access_key,
            region=aws_region,
        )
    except Exception as e:
        logger.error(f"Connect to AWS error: {e}")
        raise e
    logger.info("----- implement code here")
    return
