import logging
import json
from typing import List

logger = logging.getLogger()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s: %(levelname)s: %(message)s",
)


class Configurations(object):
    def __init__(
        self,
        files: List[str] = None,
        selected_algorithm: str = None,
        bucket: str = None,
        column_names: List[str] = None,
        saved_bucket: str = None,
        saved_tmp_path: str = None,
        saved_target_path: str = None,
        saved_target_filename: str = None,
        dynamodb_tablename: str = None,
        saved_logs_target_path: str = None,
        saved_logs_target_filename: str = None,
        environment: str = None,
        container_type: str = None,
        container_name: str = None,
        interval_of_check_task_status: int = None,
        interval_of_exit_check_status: int = None,
        worker_replicas: int = None,
        interval_of_check_sqs_in_second: int = None,
        interval_of_total_wait_time_of_sqs: int = None,
        eks_nodes_number: int = None,
        scale_eks_nodes_wait_time: int = None,
        cluster_name: str = None,
        nodegroup_name: str = None,
        aws_access_key: str = None,
        aws_secret_access_key: str = None,
        aws_region: str = None,
        sns_topic: str = None,
        algorithms: dict = None,
    ):

        self.files = files
        self.selected_algorithm = selected_algorithm
        self.bucket = bucket
        self.column_names = column_names
        self.saved_bucket = saved_bucket
        self.saved_tmp_path = saved_tmp_path
        self.saved_target_path = saved_target_path
        self.saved_target_filename = saved_target_filename
        self.dynamodb_tablename = dynamodb_tablename
        self.saved_logs_target_path = saved_logs_target_path
        self.saved_logs_target_filename = saved_logs_target_filename
        self.environment = environment
        self.container_type = container_type
        self.container_name = container_name
        self.interval_of_check_task_status = interval_of_check_task_status
        self.interval_of_exit_check_status = interval_of_exit_check_status
        self.worker_replicas = worker_replicas
        self.interval_of_check_sqs_in_second = interval_of_check_sqs_in_second
        self.interval_of_total_wait_time_of_sqs = interval_of_total_wait_time_of_sqs
        self.eks_nodes_number = eks_nodes_number
        self.scale_eks_nodes_wait_time = scale_eks_nodes_wait_time
        self.cluster_name = cluster_name
        self.nodegroup_name = nodegroup_name
        self.aws_access_key = aws_access_key
        self.aws_secret_access_key = aws_secret_access_key
        self.aws_region = aws_region
        self.sns_topic = sns_topic
        self.algorithms = algorithms


def make_configurations_obj_from_str(command_str: str) -> Configurations:
    try:
        config_json = json.loads(command_str)
        general = config_json["general"]
        files_config = config_json["files_config"]
        output = config_json["output"]
        algorithms = config_json["algorithms"]

        files = files_config["files"]
        selected_algorithm = files_config["selected_algorithm"]

        bucket = files_config["bucket"]
        column_names = files_config["column_names"]
        saved_bucket = output["saved_bucket"]
        saved_tmp_path = output["saved_tmp_path"]
        saved_target_path = output["saved_target_path"]

        saved_target_filename = output["saved_target_filename"]

        dynamodb_tablename = output["dynamodb_tablename"]
        saved_logs_target_path = output["saved_logs_target_path"]
        saved_logs_target_filename = output["saved_logs_target_filename"]

        interval_of_check_task_status = int(general["interval_of_check_task_status"])
        interval_of_exit_check_status = int(general["interval_of_exit_check_status"])
        aws_access_key = config_json["aws_access_key"]
        aws_secret_access_key = config_json["aws_secret_access_key"]
        aws_region = config_json["aws_region"]
        sns_topic = config_json["sns_topic"]

        config = Configurations(
            files=files,
            selected_algorithm=selected_algorithm,
            bucket=bucket,
            column_names=column_names,
            saved_bucket=saved_bucket,
            saved_tmp_path=saved_tmp_path,
            saved_target_path=saved_target_path,
            saved_target_filename=saved_target_filename,
            dynamodb_tablename=dynamodb_tablename,
            saved_logs_target_path=saved_logs_target_path,
            saved_logs_target_filename=saved_logs_target_filename,
            interval_of_check_task_status=interval_of_check_task_status,
            interval_of_exit_check_status=interval_of_exit_check_status,
            aws_access_key=aws_access_key,
            aws_secret_access_key=aws_secret_access_key,
            aws_region=aws_region,
            sns_topic=sns_topic,
            algorithms=algorithms,
        )

        return config
    except Exception as e:
        raise e
