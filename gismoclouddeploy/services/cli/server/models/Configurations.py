import json
from typing import List
import yaml


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
        saved_rumtime_image_name_aws: str = None,
        saved_rumtime_image_name_local: str = None,
        interval_of_check_task_status: int = None,
        interval_of_exit_check_status: int = None,
        deployment_services_list: List[str] = None,
        interval_of_check_sqs_in_second: int = None,
        interval_of_total_wait_time_of_sqs: int = None,
        interval_of__wait_pod_ready: int = None,
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
        self.saved_rumtime_image_name_aws = saved_rumtime_image_name_aws
        self.saved_rumtime_image_name_local = saved_rumtime_image_name_local
        self.interval_of_check_task_status = interval_of_check_task_status
        self.interval_of_exit_check_status = interval_of_exit_check_status
        self.deployment_services_list = deployment_services_list
        self.interval_of_check_sqs_in_second = interval_of_check_sqs_in_second
        self.interval_of_total_wait_time_of_sqs = interval_of_total_wait_time_of_sqs
        self.interval_of__wait_pod_ready = interval_of__wait_pod_ready
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
        saved_rumtime_image_name_aws = output["saved_rumtime_image_name_aws"]
        saved_rumtime_image_name_local = output["saved_rumtime_image_name_local"]
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
            saved_rumtime_image_name_aws=saved_rumtime_image_name_aws,
            saved_rumtime_image_name_local=saved_rumtime_image_name_local,
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


def import_yaml_and_convert_to_json_str(
    yaml_file: str,
    aws_access_key: str,
    aws_secret_access_key: str,
    aws_region: str,
    sns_topic: str,
) -> str:
    try:
        with open(yaml_file, "r") as stream:
            temp_json = yaml.safe_load(stream)

        # temp_json = read_yaml(yaml_file)
        temp_json["aws_access_key"] = aws_access_key
        temp_json["aws_secret_access_key"] = aws_secret_access_key
        temp_json["aws_region"] = aws_region
        temp_json["sns_topic"] = sns_topic
        return json.dumps(temp_json)
    except Exception as e:
        raise e


def make_config_obj_from_yaml(
    yaml_file: str,
    aws_access_key: str,
    aws_secret_access_key: str,
    aws_region: str,
    sns_topic: str,
) -> Configurations:

    try:
        with open(yaml_file, "r") as stream:
            config_params = yaml.safe_load(stream)

    except IOError as e:
        raise f"I/O error:{e}"
    try:
        config = Configurations(
            files=config_params["files_config"]["files"],
            selected_algorithm=config_params["files_config"]["selected_algorithm"],
            bucket=config_params["files_config"]["bucket"],
            column_names=config_params["files_config"]["column_names"],
            saved_bucket=config_params["output"]["saved_bucket"],
            saved_tmp_path=config_params["output"]["saved_tmp_path"],
            saved_target_path=config_params["output"]["saved_target_path"],
            saved_target_filename=config_params["output"]["saved_target_filename"],
            dynamodb_tablename=config_params["output"]["dynamodb_tablename"],
            saved_logs_target_path=config_params["output"]["saved_logs_target_path"],
            saved_logs_target_filename=config_params["output"][
                "saved_logs_target_filename"
            ],
            saved_rumtime_image_name_aws=config_params["output"][
                "saved_rumtime_image_name_aws"
            ],
            saved_rumtime_image_name_local=config_params["output"][
                "saved_rumtime_image_name_local"
            ],
            interval_of_check_task_status=config_params["general"][
                "interval_of_check_task_status"
            ],
            interval_of_exit_check_status=config_params["general"][
                "interval_of_exit_check_status"
            ],
            deployment_services_list=config_params["k8s_config"][
                "deployment_services_list"
            ],
            interval_of_check_sqs_in_second=int(
                config_params["aws_config"]["interval_of_check_sqs_in_second"]
            ),
            interval_of_total_wait_time_of_sqs=int(
                config_params["aws_config"]["interval_of_total_wait_time_of_sqs"]
            ),
            interval_of__wait_pod_ready=int(
                config_params["aws_config"]["interval_of__wait_pod_ready"]
            ),
            cluster_name=config_params["aws_config"]["cluster_name"],
            nodegroup_name=config_params["aws_config"]["nodegroup_name"],
            eks_nodes_number=config_params["aws_config"]["eks_nodes_number"],
            scale_eks_nodes_wait_time=config_params["aws_config"][
                "scale_eks_nodes_wait_time"
            ],
            # aws credentail from environment in main
            aws_access_key=aws_access_key,
            aws_secret_access_key=aws_secret_access_key,
            aws_region=aws_region,
            sns_topic=sns_topic,
        )
        return config
    except Exception as e:
        raise f"solardata parameters format in {yaml_file} file is incorrect: {e}"
