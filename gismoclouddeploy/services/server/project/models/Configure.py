import json


class Configure(object):
    def __init__(
        self,
        files,
        bucket,
        column_names,
        saved_bucket,
        saved_tmp_path,
        saved_target_path,
        dynamodb_tablename,
        saved_logs_target_path,
        saved_logs_target_filename,
        saved_target_filename,
        interval_of_check_task_status,
        interval_of_exit_check_status,
        aws_access_key,
        aws_secret_access_key,
        aws_region,
        sns_topic,
    ):

        self.files = files
        self.bucket = bucket
        self.column_names = column_names
        self.saved_bucket = saved_bucket
        self.saved_tmp_path = saved_tmp_path
        self.saved_target_path = saved_target_path
        self.saved_target_filename = saved_target_filename
        self.dynamodb_tablename = dynamodb_tablename
        self.saved_logs_target_path = saved_logs_target_path
        self.saved_logs_target_filename = saved_logs_target_filename
        self.interval_of_check_task_status = interval_of_check_task_status
        self.interval_of_exit_check_status = interval_of_exit_check_status
        self.aws_access_key = aws_access_key
        self.aws_secret_access_key = aws_secret_access_key
        self.aws_region = aws_region
        self.sns_topic = sns_topic


def make_configure_from_str(command_str: str) -> Configure:
    config_json = json.loads(command_str)

    files = json.loads(config_json["files"].replace("'", '"'))

    bucket = config_json["bucket"]
    column_names = json.loads(config_json["column_names"].replace("'", '"'))
    saved_bucket = config_json["saved_bucket"]
    saved_tmp_path = config_json["saved_tmp_path"]
    saved_target_path = config_json["saved_target_path"]

    saved_target_filename = config_json["saved_target_filename"]
    dynamodb_tablename = config_json["dynamodb_tablename"]
    saved_logs_target_path = config_json["saved_logs_target_path"]
    saved_logs_target_filename = config_json["saved_logs_target_filename"]
    interval_of_check_task_status = config_json["interval_of_check_task_status"]
    interval_of_exit_check_status = config_json["interval_of_exit_check_status"]

    aws_access_key = config_json["aws_access_key"]
    aws_secret_access_key = config_json["aws_secret_access_key"]
    aws_region = config_json["aws_region"]
    sns_topic = config_json["sns_topic"]

    config = Configure(
        files=files,
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
    )

    return config
