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
        self.interval_of_check_task_status = interval_of_check_task_status
        self.interval_of_exit_check_status = interval_of_exit_check_status

    # def to_json(self):
    #     return {
    #         'files': self.id,
    #         'bucket': self.task_id,
    #         'process_all_files': self.bucket_name,
    #         'column_names': self.file_path,
    #         'saved_bucket': self.file_name,
    #         'saved_tmp_path': self.column_name,
    #         'saved_target_path': self.process_time,
    #         'saved_target_filename': self.power_units,
    #         'interval_of_check_task_status': self.length,
    #         'interval_of_exit_check_status': self.capacity_estimate
    #     }

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
    interval_of_check_task_status = config_json['interval_of_check_task_status']
    interval_of_exit_check_status = config_json['interval_of_exit_check_status']

    config = Configure(
        files,
        bucket,
        process_all_files,
        column_names,
        saved_bucket,
        saved_tmp_path,
        saved_target_path,
        saved_target_filename,
        interval_of_check_task_status,
        interval_of_exit_check_status
    )

    return config