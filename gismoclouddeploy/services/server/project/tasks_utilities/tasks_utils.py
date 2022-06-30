from matplotlib import use
from utils.aws_utils import (
    connect_aws_client,
    download_solver_licence_from_s3_and_save,
)

from os.path import exists
import logging

# logger config
logger = logging.getLogger()
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s: %(levelname)s: %(message)s"
)


def publish_message_sns(
    message: str,
    subject: str,
    topic_arn: str,
    aws_access_key: str,
    aws_secret_access_key: str,
    aws_region: str,
) -> str:
    logger.info("---------------")
    try:
        sns_client = connect_aws_client(
            client_name="sns",
            key_id=aws_access_key,
            secret=aws_secret_access_key,
            region=aws_region,
        )
        message_res = sns_client.publish(
            TopicArn=topic_arn,
            Subject=subject,
            Message=message,
        )
        message_id = message_res["MessageId"]
        logger.info(f"----- Publish subject {subject} message {message}")
        return message_id
    except Exception as e:
        logger.error(f"publish message fail : {e}")
        raise e


def check_and_download_solver(
    solver_name: str = None,
    slover_lic_file_name: str = None,
    solver_lic_target_path: str = None,
    saved_solver_bucket: str = None,
    saved_temp_path_in_bucket: str = None,
    aws_access_key: str = None,
    aws_secret_access_key: str = None,
    aws_region: str = None,
) -> None:
    if solver_name is None:
        logger.info("No solver name is specified")
        return
    # check if the file is exist in local directory
    local_solver_file = solver_lic_target_path + "/" + slover_lic_file_name
    if exists(local_solver_file) is False:
        logger.info(
            f"No solver in worker image. Download MOSEK Licence from {saved_solver_bucket} {saved_temp_path_in_bucket}"
        )
        try:
            s3_client = connect_aws_client(
                "s3",
                key_id=aws_access_key,
                secret=aws_secret_access_key,
                region=aws_region,
            )
            file_path_name = saved_temp_path_in_bucket + "/" + slover_lic_file_name
            download_solver_licence_from_s3_and_save(
                s3_client=s3_client,
                bucket_name=saved_solver_bucket,
                file_path_name=file_path_name,
                saved_file_path=solver_lic_target_path,
                saved_file_name=slover_lic_file_name,
            )
            logger.info("=========== Download solver success ============== ")
            return
        except Exception as e:
            logger.error(
                f"Cannot download solver{solver_name} from {saved_solver_bucket}::{saved_temp_path_in_bucket}/{slover_lic_file_name}"
            )
            raise f"Cannot download solver{solver_name} from {saved_solver_bucket}::{saved_temp_path_in_bucket}/{slover_lic_file_name}"
    logger.info(f"{local_solver_file} exists")
    return
    #


def make_response(subject: str = None, messages: str = None) -> dict:
    response = {"Subject": subject, "Messages": messages}
    return response
