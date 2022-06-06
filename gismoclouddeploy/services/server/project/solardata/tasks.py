
from cmath import log
from celery import shared_task
from celery.utils.log import get_task_logger
from celery.result import AsyncResult
import os
from project.solardata.models.SolarParams import make_solardata_params_from_str
from project.solardata.models.WorkerStatus import WorkerStatus
from project.solardata.models.SNSSubjectsAlert import SNSSubjectsAlert
import time
import socket
from project.solardata.models.WorkerState import WorkerState
import json

logger = get_task_logger(__name__)


def track_logs( task_id:str,
                function_name:str,
                time:str, 
                action:str, 
                message:str,
                process_file_name:str,
                table_name:str,
                column_name:str,
                aws_access_key:str,
                aws_secret_access_key:str,
                aws_region:str
                ):


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

        put_item_to_dynamodb(table_name=table_name, 
                            workerstatus=start_status,
                            aws_access_key=aws_access_key,
                            aws_secret_access_key=aws_secret_access_key,
                            aws_region=aws_region
                            )


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
def process_data_task(self,table_name:str,
                     bucket_name:str,
                     file_path_name:str, 
                     column_name:str,
                     saved_bucket:str,
                     saved_file_path:str, 
                     saved_filename:str,
                     start_time:str,
                     solar_params_str:str,
                     aws_access_key:str,
                     aws_secret_access_key:str,
                     aws_region:str,
                     sns_topic:str) -> str:
    solar_params_obj = make_solardata_params_from_str(solar_params_str)
    task_id = self.request.id
    subject = task_id
    message = "init process_data_task"
    # self.update_state(state='STARTED', meta ={'start': i})

    from project import create_app
    from project.solardata.models import SolarData
    from project.solardata.utils import (
        publish_message_sns
    )
    from project.solardata.solardatatools import process_solardata_tools
    app = create_app()
    with app.app_context():
        try:
            process_file_task_id = str(self.request.id)
        
            startime = str(time.time())
            track_logs(task_id=process_file_task_id,
                        function_name="process_data_task",
                        time=startime,
                        action="idle-stop/busy-start", 
                        message=message,
                        table_name=table_name,
                        process_file_name=file_path_name,
                        column_name=column_name,
                        aws_access_key=aws_access_key,
                        aws_secret_access_key=aws_secret_access_key,
                        aws_region=aws_region
                        )
            self.update_state(state= WorkerState.PROGRESS.name, meta = {'start':startime})
            process_solardata_tools(  
                            task_id =process_file_task_id,
                            bucket_name=bucket_name ,
                            file_path_name=file_path_name,
                            column_name=column_name,
                            start_time=start_time,
                            saved_bucket=saved_bucket,
                            saved_file_path=saved_file_path,
                            saved_filename=saved_filename,
                            solarParams=solar_params_obj,
                            aws_access_key=aws_access_key,
                            aws_secret_access_key=aws_secret_access_key,
                            aws_region=aws_region 
                            )
            
            message = "end of process data task"
        except Exception as e:
            subject = SNSSubjectsAlert.PROCESS_FILE_ERROR.name
            message = f"error:{e}"
            logger.error(f'Error: {file_path_name} {column_name} :  {message} ')
            
        track_logs(task_id=process_file_task_id,
            function_name="process_data_task",
            action="busy-stop/idle-start",
            time=str(time.time()),
            message=message,
            table_name=table_name,
            process_file_name=file_path_name,
            column_name=column_name,
            aws_access_key=aws_access_key,
            aws_secret_access_key=aws_secret_access_key,
            aws_region=aws_region
            )

        # send message
        try:
            mesage_id = publish_message_sns(message=message,
                                            subject=subject, 
                                            topic_arn=sns_topic,
                                            aws_access_key=aws_access_key,
                                            aws_secret_access_key=aws_secret_access_key,
                                            aws_region=aws_region)
            logger.info(f' Send to SNS, message: {mesage_id}')
        except Exception as e:
            logger.error("Publish SNS Error")
            raise e
        

        if subject == SNSSubjectsAlert.PROCESS_FILE_ERROR.name:
            self.update_state(state=WorkerState.FAILED.name, meta = {'start':startime})
            return
            
        self.update_state(state=WorkerState.SUCCESS.name, meta = {'start':startime})

@shared_task(bind=True)
def loop_tasks_status_task( self,
                            delay,
                            interval_of_timeout,
                            task_ids,
                            bucket_name, 
                            source_folder,
                            target_folder,
                            target_filename,
                            table_name,
                            saved_log_file_path,
                            saved_log_file_name,
                            aws_access_key:str,
                            aws_secret_access_key:str,
                            aws_region:str,
                            sns_topic:str
                            ):
    interval_of_max_timeout = int(interval_of_timeout)
    task_id = self.request.id
    subject = task_id
    startime = str(time.time())
    message = "init loop_tasks_status_task"
    track_logs(task_id=task_id,
                    function_name="loop_tasks_status_task",
                    time=startime,
                    action="idle-stop/busy-start", 
                    message=message,
                    table_name=table_name,
                    process_file_name=None,
                    column_name=None,
                    aws_access_key=aws_access_key,
                    aws_secret_access_key=aws_secret_access_key,
                    aws_region=aws_region
                    )
    self.update_state(state=WorkerState.PROGRESS.name, meta = {'start':startime})
    
    from project import create_app
    from project.solardata.models import SolarData
    from project.solardata.utils import combine_files_to_file,save_logs_from_dynamodb_to_s3,remove_all_items_from_dynamodb,publish_message_sns
    app = create_app()
    with app.app_context():

        while len(task_ids) > 0 :
            for id in task_ids[:]:     
                res = AsyncResult(str(id))
                status = str(res.status)
                if res.info is None:
                    logger.info("no info")
                else:
                    try:
                        star_time = res.info['start']
                        curr_time = time.time()
                        duration  = int(curr_time - float(star_time))
                        # if the duration of task is over timeout stop 
                        if duration >= int(interval_of_max_timeout) :
                            # remove id to avoid duplicated sns message
                            task_ids.remove(id)
                            try:
                                data = {}
                                data['task_id'] = f"{id}"
                                mesage_id = publish_message_sns(message=json.dumps(data),
                                                    subject=SNSSubjectsAlert.TIMEOUT.name, 
                                                    topic_arn=sns_topic,
                                                    aws_access_key=aws_access_key,
                                                    aws_secret_access_key=aws_secret_access_key,
                                                    aws_region=aws_region)
                            except Exception as e:
                                logger.error(f"SYSTEM error :{e}")
                                raise e
                            logger.warning(f"====== Timeout {id} durtaion: {duration} send sns timeout alert ====== ")

                    except Exception as e:
                        logger.info("no start key in info")    
                    
                
                # if tasks success failed or revoked 
                if status == WorkerState.SUCCESS.name or status == WorkerState.FAILED.name or status == WorkerState.REVOKED.name :
                    logger.info(f"completed schedulers: id: {res.task_id} \n task status: {res.status} ")
                    # delete id from task_ids
                    task_ids.remove(id)
            time.sleep(int(delay))



        logger.info("------- start combine files, save logs , clean dynamodb items---------")
    
        message = "end loop_tasks_status_task"
        try:

            track_logs(task_id=self.request.id,
                    function_name="loop_tasks_status_task",
                    time=str(time.time()),
                    action="busy-stop/idle-start", 
                    message=message,
                    table_name=table_name,
                    process_file_name=None,
                    column_name=None,
                    aws_access_key=aws_access_key,
                    aws_secret_access_key=aws_secret_access_key,
                    aws_region=aws_region
                    )
       
            response = combine_files_to_file(bucket_name=bucket_name,
                                             source_folder=source_folder,
                                            target_folder=target_folder, 
                                            target_filename=target_filename,
                                            aws_access_key=aws_access_key,
                                            aws_secret_access_key=aws_secret_access_key,
                                            aws_region=aws_region)

            
            save_res = save_logs_from_dynamodb_to_s3(table_name=table_name,
                                            saved_bucket=bucket_name,
                                            saved_file_path=saved_log_file_path,
                                            saved_filename=saved_log_file_name,
                                           aws_access_key=aws_access_key,
                                           aws_secret_access_key=aws_secret_access_key,
                                           aws_region=aws_region)

            remov_res = remove_all_items_from_dynamodb( table_name=table_name,
                                                        aws_access_key=aws_access_key,
                                                        aws_secret_access_key=aws_secret_access_key,
                                                        aws_region=aws_region)

            logger.info(f"remov_res: {remov_res} save_res: {save_res}, response: {response}")
            subject = SNSSubjectsAlert.All_TASKS_COMPLETED.name
            message= SNSSubjectsAlert.All_TASKS_COMPLETED.name

        except Exception as e:
            subject = SNSSubjectsAlert.SYSTEM_ERROR.name
            message=f"Loop task error:{e}"
            logger.info(f'Error: {message} ')

        try:
            mesage_id = publish_message_sns(message=message,
                                            subject=subject, 
                                            topic_arn=sns_topic,
                                            aws_access_key=aws_access_key,
                                            aws_secret_access_key=aws_secret_access_key,
                                            aws_region=aws_region)
            logger.info(f' Send to SNS.----------> message: {mesage_id}')
        except Exception as e:
            raise e
    