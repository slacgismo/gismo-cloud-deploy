import json

class Configure(object):

    def __init__(self,
                 files,
                 bucket,
                 process_all_files,
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
                 ):

        self.files = files
        self.bucket = bucket
        self.process_all_files = process_all_files
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

def make_configure_from_str(command_str:str) -> Configure:
    config_json = json.loads(command_str)
    files  = json.loads(config_json["files"].replace("\'", "\""))
    
    bucket = config_json['bucket']
    process_all_files = config_json['process_all_files']
    column_names = json.loads(config_json["column_names"].replace("\'", "\""))
    saved_bucket = config_json['saved_bucket']
    saved_tmp_path = config_json['saved_tmp_path']
    saved_target_path = config_json['saved_target_path']



    saved_target_filename= config_json['saved_target_filename']
    dynamodb_tablename = config_json['dynamodb_tablename']
    saved_logs_target_path = config_json['saved_logs_target_path']
    saved_logs_target_filename = config_json['saved_logs_target_filename']
    interval_of_check_task_status = config_json['interval_of_check_task_status']
    interval_of_exit_check_status = config_json['interval_of_exit_check_status']

    config = Configure(
        files = files,
        bucket = bucket,
        process_all_files = process_all_files,
        column_names= column_names,
        saved_bucket= saved_bucket,
        saved_tmp_path= saved_tmp_path,
        saved_target_path = saved_target_path,
        saved_target_filename = saved_target_filename,
        dynamodb_tablename = dynamodb_tablename,
        saved_logs_target_path = saved_logs_target_path,
        saved_logs_target_filename = saved_logs_target_filename,
        interval_of_check_task_status = interval_of_check_task_status,
        interval_of_exit_check_status = interval_of_exit_check_status
    )

    return config