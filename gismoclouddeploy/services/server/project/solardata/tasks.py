
from celery import shared_task
from celery.utils.log import get_task_logger
from celery.result import AsyncResult
import os
from project.solardata.models.SolarParams import make_solardata_params_from_str
from project.solardata.models.WorkerStatus import WorkerStatus

import time
import socket

logger = get_task_logger(__name__)
SNS_TOPIC = os.environ.get('SNS_TOPIC')

def track_logs( task_id:str,
                function_name:str,
                time:str, 
                action:str, 
                message:str,
                process_file_name:str,
                table_name:str,
                column_name:str):


    from project import create_app
    from project.solardata.models import SolarData
    from project.solardata.utils import (
        put_item_to_dynamodb,
    )
    app = create_app()
    with app.app_context():
        hostname = socket.gethostname()
        host_ip = socket.gethostbyname(hostname)      
        pid = os.getpid()
        start_status = WorkerStatus(  host_name=hostname,
                                        task_id=task_id,
                                        host_ip=host_ip, 
                                        pid = str(pid),
                                        function_name=function_name,
                                        action=action, 
                                        time=time,
                                        message=message,
                                        filename=process_file_name,
                                        column_name = column_name
                                        )
        put_item_to_dynamodb(table_name=table_name, workerstatus=start_status)


@shared_task()
def plot_gantt_chart_from_log_files_task(bucket, file_path_name, saved_image_name):
    print(f"start process file from {bucket}, {file_path_name} to {saved_image_name} ")
    from project import create_app
    from project.solardata.utils import plot_gantt_chart
    app = create_app()
    with app.app_context():
        res = plot_gantt_chart(bucket,file_path_name,saved_image_name)
        print(res)

@shared_task()
def combine_files_to_file_task(bucket_name,source_folder,target_folder,target_filename):

    from project import create_app
    from project.solardata.models import SolarData
    from project.solardata.utils import combine_files_to_file
    app = create_app()
    with app.app_context():
        response = combine_files_to_file(bucket_name, source_folder, target_folder, target_filename)
        return response




@shared_task(bind=True)
def process_data_task(self,table_name, bucket_name,file_path_name, column_name,saved_bucket, saved_file_path, saved_filename,start_time,solar_params_str:str) -> str:
    solar_params_obj = make_solardata_params_from_str(solar_params_str)
    task_id = self.request.id
    subject = task_id
    message = "init process_data_task"

    from project import create_app
    from project.solardata.models import SolarData
    from project.solardata.utils import (
        publish_message_sns
    )
    from project.solardata.solardatatools import process_solardata_tools
    app = create_app()
    with app.app_context():
        try:
            track_logs(task_id=self.request.id,
                        function_name="process_data_task",
                        time=str(time.time()),
                        action="idle-stop/busy-start", 
                        message=message,
                        table_name=table_name,
                        process_file_name=file_path_name,
                        column_name=column_name
                        )
            process_solardata_tools(  
                            task_id =self.request.id,
                            bucket_name=bucket_name ,
                            file_path_name=file_path_name,
                            column_name=column_name,
                            start_time=start_time,
                            saved_bucket=saved_bucket,
                            saved_file_path=saved_file_path,
                            saved_filename=saved_filename,
                            solarParams=solar_params_obj 
                            )
            
            message = "end of process data task"
        except Exception as e:
            subject = "ProcessFileError"
            message = f"task_id: {task_id} filename: {file_path_name},column: {column_name},error:{e}"
            logger.info(f'Error: {e} ')

        # send message
        try:
            mesage_id = publish_message_sns(message=message,subject=subject, topic_arn=SNS_TOPIC)
            logger.info(f' Send to SNS.----------> message: {mesage_id}')
        except Exception as e:
            raise e

        track_logs(task_id=self.request.id,
            function_name="process_data_task",
            action="busy-stop/idle-start",
            time=str(time.time()),
            message=message,
            table_name=table_name,
            process_file_name=file_path_name,
            column_name=column_name
            )

@shared_task(bind=True)
def loop_tasks_status_task( self,
                            delay,
                            count,
                            task_ids,
                            bucket_name, 
                            source_folder,
                            target_folder,
                            target_filename,
                            table_name,
                            saved_log_file_path,
                            saved_log_file_name
                            ):
    counter = int(count)
    task_id = self.request.id
    subject = task_id
    message = "init loop_tasks_status_task"
    track_logs(task_id=task_id,
                    function_name="loop_tasks_status_task",
                    time=str(time.time()),
                    action="idle-stop/busy-start", 
                    message=message,
                    table_name=table_name,
                    process_file_name=None,
                    column_name=None
                    )

    
    while counter > 0:
        # check the task status
        time.sleep(int(delay))
        num_completed_task =0
        for id in task_ids:
            res = AsyncResult(str(id))
            status = str(res.status)
           
            if status != "PENDING":
                print(f"completed schedulers: id: {res.task_id} \n task status: {res.status}")
                num_completed_task += 1
        if num_completed_task == len(task_ids):
            print(f"num_success_task: {num_completed_task}")
            break 
        counter -= 1
        print(f"Time: {time.ctime(time.time())}")

    logger.info("------- start combine files, save logs , clean dynamodb items---------")
    
    from project import create_app
    from project.solardata.models import SolarData
    from project.solardata.utils import combine_files_to_file,save_logs_from_dynamodb_to_s3,remove_all_items_from_dynamodb,publish_message_sns
    app = create_app()
    with app.app_context():
        message = "end loop_tasks_status_task"
        try:
            track_logs(task_id=self.request.id,
                    function_name="loop_tasks_status_task",
                    time=str(time.time()),
                    action="busy-stop/idle-start", 
                    message=message,
                    table_name=table_name,
                    process_file_name=None,
                    column_name=None
                    )
       
            response = combine_files_to_file(bucket_name, source_folder, target_folder, target_filename)
            save_res = save_logs_from_dynamodb_to_s3(table_name=table_name,
                                            saved_bucket=bucket_name,
                                            saved_file_path=saved_log_file_path,
                                            saved_filename=saved_log_file_name )
            remov_res = remove_all_items_from_dynamodb(table_name)
            print(f"remov_res: {remov_res} save_res: {save_res}, response: {response}")
            subject = "AllTaskCompleted"
            message="AllTaskCompleted"

        except Exception as e:
            subject = "Error"
            message=f"Loop task error:{e}"
            logger.info(f'Error: {message} ')

        try:
            mesage_id = publish_message_sns(message=message,subject=subject, topic_arn=SNS_TOPIC)
            logger.info(f' Send to SNS.----------> message: {mesage_id}')
        except Exception as e:
            raise e
    