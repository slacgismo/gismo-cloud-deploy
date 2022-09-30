# PVInsight Code Imports
from solardatatools import DataHandler
from solardatatools.dataio import get_pvdaq_data

import logging
from os.path import exists

logger = logging.getLogger()
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s: %(levelname)s: %(message)s"
)


def entrypoint(
    user_id: str = None,
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
    :param str curr_process_file: Current process file. This file name is one of the file name in logs file.()
    :param str curr_process_column: Current proccess column name. This column name is one of the column name in logs file.
    :param str aws_access_key:
    :param str aws_secret_access_key:
    :param str aws_region:
    :param str solver_name: The solver name that defined in config.yaml
    :param str solver_file: The solver file location inside worker. This file location is defined in config.yaml.
    :return dict json_message: Return a json format object contain user_id (This message is used to publish sns message and track logs in dynamodb)
    """

    ## ==================== Modify your code below ==================== ##
    logger.info(
        f"process file:{curr_process_file} , column:{curr_process_column}, solve: {solver_file}"
    )

    # check solver file exist: The download function is inside `check_and_download_solver` function ""
    if solver_name is not None and (exists(solver_file) is False):
        return Exception(f"solver_file:{solver_file} dose not exist")

    data_frame = get_pvdaq_data(sysid=34, year=range(2011, 2015), api_key="DEMO_KEY")[0]
    dh = DataHandler(data_frame)
    dh.run_pipeline(power_col="ac_power")
    dh.fit_statistical_clear_sky_model()
    save_data = {"deg_rate": dh.scsf.deg_rate}

    return save_data
