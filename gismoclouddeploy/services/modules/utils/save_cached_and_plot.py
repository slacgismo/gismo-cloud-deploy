from .WORKER_CONFIG import WORKER_CONFIG
from .command_utils import process_logs_and_plot
from .dynamodb_utils import download_logs_saveddata_from_dynamodb
from .modiy_config_parameters import modiy_config_parameters
from .check_aws import connect_aws_client

from .process_log import analyze_logs_files
import logging

logger = logging.getLogger()
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s: %(levelname)s: %(message)s"
)


def save_cached_and_plot(
    configfile: str = None,
    aws_access_key: str = None,
    aws_secret_access_key: str = None,
    aws_region: str = None,
    sqs_url: str = None,
    sns_topic: str = None,
    dlq_url: str = None,
    ecr_repo: str = None,
) -> None:

    config_json = modiy_config_parameters(
        configfile=configfile,
        nodesscale=None,
        aws_access_key=aws_access_key,
        aws_secret_access_key=aws_secret_access_key,
        aws_region=aws_region,
        sqs_url=sqs_url,
        sns_topic=sns_topic,
        dlq_url=dlq_url,
        ecr_repo=ecr_repo,
    )
    worker_config_obj = WORKER_CONFIG(config_json["worker_config"])
    is_log_saved = download_logs_saveddata_from_dynamodb(
        worker_config=worker_config_obj,
        aws_access_key=aws_access_key,
        aws_secret_key=aws_secret_access_key,
        aws_region=aws_region,
    )

    if is_log_saved is True:
        process_logs_and_plot(
            worker_config=worker_config_obj,
            aws_access_key=aws_access_key,
            aws_secret_access_key=aws_secret_access_key,
            aws_region=aws_region,
        )

        s3_client = connect_aws_client(
            client_name="s3",
            key_id=aws_access_key,
            secret=aws_secret_access_key,
            region=aws_region,
        )

        logs_file_path_name = (
            worker_config_obj.saved_path_local
            + "/"
            + worker_config_obj.saved_logs_target_filename
        )
        analyze_logs_files(
            bucket=worker_config_obj.saved_bucket,
            logs_file_path_name=logs_file_path_name,
            s3_client=s3_client,
            save_file_path_name=worker_config_obj.saved_performance_file,
        )
        return
    logger.info("No data in dynamodb")
    return
