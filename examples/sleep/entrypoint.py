import logging
import time
import numpy as np

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
    print("---------->")
    delay = 5
    start_time = float(time.time())
    start_ctime = time.ctime()
    i = 0
    is_end = False
    period = 0
    end_time = 0
    print("Start : %s" % start_ctime)

    while True:
        A = np.array([[4, 3, 2], [-2, 2, 3], [3, -5, 2]])
        B = np.array([25, -10, -4])
        answer = np.linalg.inv(A).dot(B)
        end_time = float(time.time())

        duration = int(end_time - start_time)
        if duration >= delay:
            break

    end_ctime = time.ctime()
    print("End : %s" % end_ctime)

    try:
        # ==================== PS:Save data in json format is required  ==================== ##

        save_data = {
            "bucket": data_bucket,
            "curr_process_file": curr_process_file,
            "curr_process_column": curr_process_column,
            "answer": str(answer),
            "delay": delay,
            "period": duration,
            "start_time": start_ctime,
            "end_time": end_ctime,
        }
    except Exception as e:
        raise Exception(f"Save data error: {e}")

    # # ==================== Modify your code above ==================== ##
    return save_data
