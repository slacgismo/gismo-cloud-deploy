
from cmath import log
import logging

from pyparsing import col
from project import create_app, ext_celery
from flask.cli import FlaskGroup

import socket
from typing import List
from project.solardata.models.WorkerStatus import WorkerStatus
from project.solardata.models.SolarParams import SolarParams
from project.solardata.models.SolarParams import make_solardata_params_from_str
from project.solardata.models.Configure import Configure
from project.solardata.models.Configure import make_configure_from_str
from project.solardata.utils import (
    list_files_in_bucket,
    connect_aws_client,
    put_item_to_dynamodb,
    find_matched_column_name_set)

import click
import time
import os 

import re
from project.solardata.tasks import (

    process_data_task,
    combine_files_to_file_task,
    loop_tasks_status_task,

)

from project.solardata.utils import (get_process_filenamef_base_on_command)

app = create_app()
celery = ext_celery.celery

cli = FlaskGroup(create_app=create_app)

# logger config
logger = logging.getLogger()
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s: %(levelname)s: %(message)s')




@cli.command("combine_files")
@click.argument('bucket_name', nargs=1)
@click.argument('source_folder', nargs=1)
@click.argument('target_folder', nargs=1)
@click.argument('target_filename', nargs=1)

def combine_files(bucket_name, source_folder,target_folder,target_filename):
    print(f"bucket_name: {bucket_name} ,source_folder {source_folder} ,target_folder: {target_folder},target_filename: {target_filename}")
    task = combine_files_to_file_task.apply_async(
        [bucket_name,
        source_folder,
        target_folder,
        target_filename
        ])
    
# ***************************        
# Process first n files : first_n_files is integer
# Process all files  : first_n_files is 0 
# Process define files : first_n_files is None
# ***************************   
@cli.command("process_first_n_files")
@click.argument('config_params_str', nargs=1)
@click.argument('solardata_params_str', nargs=1)
@click.argument('first_n_files', nargs=1)
def process_first_n_files( config_params_str:str,
                    solardata_params_str:str,
                    first_n_files: str
                    ):
    # track scheduler status start    
    configure_obj = make_configure_from_str(config_params_str)


    s3_client = connect_aws_client(client_name='s3',
                                    key_id=configure_obj.aws_access_key,
                                    secret=configure_obj.aws_secret_access_key,
                                    region=configure_obj.aws_region)
    task_ids = []
    try:
       n_files =  get_process_filenamef_base_on_command(first_n_files=first_n_files,
                                             configure_obj = configure_obj,
                                             s3_client=s3_client)
    except Exception as e:
        logger.error(f"Get filenames error: {e}")
        return 
    
    for file in n_files:
         # implement partial match 
        matched_column_set = find_matched_column_name_set(bucket_name=configure_obj.bucket, 
                                                            columns_key=configure_obj.column_names, 
                                                            file_path_name=file,
                                                            s3_client=s3_client)
        for column in matched_column_set:
       
            path, filename = os.path.split(file)
            prefix = path.replace("/", "-")
            # remove special characters
            postfix = re.sub(r'[\\/*?:"<>|()]',"",column)
            temp_saved_filename = f"{prefix}-{postfix}-{filename}"
            start_time = time.time()
    
            task_id = process_data_task.apply_async([
                    configure_obj.dynamodb_tablename,
                    configure_obj.bucket,
                    file,
                    column,
                    configure_obj.saved_bucket,
                    configure_obj.saved_tmp_path,
                    temp_saved_filename,
                    start_time,
                    solardata_params_str,
                    configure_obj.aws_access_key,
                    configure_obj.aws_secret_access_key,
                    configure_obj.aws_region,
                    configure_obj.sns_topic
                    ])
            task_ids.append(str(task_id)) 

  
    # loop the task status in celery task
    loop_task = loop_tasks_status_task.apply_async([configure_obj.interval_of_check_task_status, 
                                                    configure_obj.interval_of_exit_check_status,
                                                    task_ids,
                                                    configure_obj.saved_bucket,
                                                    configure_obj.saved_tmp_path,
                                                    configure_obj.saved_target_path,
                                                    configure_obj.saved_target_filename,
                                                    configure_obj.dynamodb_tablename,
                                                    configure_obj.saved_logs_target_path,
                                                    configure_obj.saved_logs_target_filename,
                                                    configure_obj.aws_access_key,
                                                    configure_obj.aws_secret_access_key,
                                                    configure_obj.aws_region,
                                                    configure_obj.sns_topic
                                                    ])

  



@app.cli.command("celery_worker")
def celery_worker():
    from watchgod import run_process
    import subprocess

    def run_worker():
        subprocess.call(
            ["celery", "-A", "app.celery", "worker", "--loglevel=info"]
        )

    run_process("./project", run_worker)







if __name__ == '__main__':
    cli()