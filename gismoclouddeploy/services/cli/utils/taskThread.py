import threading
import time
import logging
# logger config
import json
from models.Config import Config
from utils.aws_utils import(
    connect_aws_client,
    check_environment_is_aws,

)

from utils.invoke_function import(
    invoke_eksctl_scale_node
)
from utils.sqs import (
    receive_queue_message,
    delete_queue_message,
    purge_queue,
    send_queue_message
)
from typing import List


from utils.eks_utils import (
    scale_nodes_and_wait
)

from utils.process_log import (
    process_logs_from_s3
)


logger = logging.getLogger()
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s: %(levelname)s: %(message)s')


class taskThread (threading.Thread):
    def __init__(self, threadID:int, name:str, counter:int, wait_time:int, sqs_url:str, num_task:int, config_params_obj:Config, delete_nodes_after_processing:bool, dlq_url:str, key_id:str, secret_key:str, aws_region:str):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.wait_time = wait_time
        self.counter = counter
        self.sqs_url = sqs_url
        self.num_task = num_task
        self.config_params_obj = config_params_obj
        self.delete_nodes_after_processing = delete_nodes_after_processing
        self.dlq_url = dlq_url
        self.key_id = key_id
        self.secret_key = secret_key
        self.aws_region = aws_region 
    def run(self):
      print ("Starting " + self.name)
      long_pulling_sqs( counter=self.counter, 
                        wait_time=self.wait_time, 
                        sqs_url=self.sqs_url, 
                        num_task=self.num_task, 
                        config_params_obj= self.config_params_obj,
                         delete_nodes_after_processing=self.delete_nodes_after_processing, 
                         dlq_url = self.dlq_url, 
                         key_id=self.key_id,
                         secret_key=self.secret_key,
                         aws_region=self.aws_region)
      print ("Exiting " + self.name)


def send_mesage_to_DLQ(subject:str, message:str, dlq_url:str,sqs_client:'botocore.client.SQS'):
     #  move message to deal letter queue
    MSG_ATTRIBUTES = {
        'Title': {
            'DataType': 'String',
            'StringValue': subject
        }
    }
    MSG_BODY = message
    try:
        dlq_res = send_queue_message(queue_url=dlq_url, msg_attributes= MSG_ATTRIBUTES, msg_body=MSG_BODY, sqs_client=sqs_client)
        logger.info(f" ==== DLG  ========\n {dlq_res}")
    except Exception as e:
        raise e


def long_pulling_sqs(counter:int,
                        wait_time:int,
                        sqs_url:str,
                        num_task:int, 
                        config_params_obj:Config, 
                        delete_nodes_after_processing:bool,
                        dlq_url:str,
                        key_id:str,
                        secret_key:str,
                        aws_region:str,
                        ) -> List[str]:
    sqs_client = connect_aws_client(client_name='sqs',key_id=key_id, secret=secret_key, region=aws_region)
    tasks = []
    num_task_completed = 0
    while counter:
        time.sleep(wait_time)
        messages = receive_queue_message(sqs_url, sqs_client, MaxNumberOfMessages=1,wait_time=wait_time)
        logger.info(f"waiting ....counter: {counter - wait_time} Time: {time.ctime(time.time())}")
        counter -= int(wait_time)
        if 'Messages' in messages :
            for msg in messages['Messages']:
                msg_body = json.loads(msg['Body'])
                # msg_body = msg['Body']
                receipt_handle = msg['ReceiptHandle']
                subject  = msg_body['Subject']
                message_text = msg_body['Message']
                logger.info(f'The subject : {subject}')
                logger.info(f'The message : {message_text}')
                # logger.info('Deleting message from the queue...')
                delete_queue_message(sqs_url, receipt_handle, sqs_client)
                tasks.append(message_text)
                num_task_completed += 1
                if subject == "ProcessFileError" or subject == "Error":

                    send_mesage_to_DLQ(subject=subject, message=message_text, dlq_url=dlq_url, sqs_client=sqs_client)

                if subject == "AllTaskCompleted" or subject == "Error":

                    logger.info(f"subject:{subject} message: {message_text}")
                    s3_client = connect_aws_client(client_name='s3',key_id=key_id, secret=secret_key, region=aws_region)
                    logs_full_path_name = config_params_obj.saved_logs_target_path + "/" + config_params_obj.saved_logs_target_filename

                    process_logs_from_s3(config_params_obj.saved_bucket, logs_full_path_name, "results/runtime.png", s3_client)

                    if check_environment_is_aws() and delete_nodes_after_processing:
                        logger.info("Delete node after processing")
                        scale_nodes_and_wait(scale_node_num=0, counter=60, delay=1, config_params_obj = config_params_obj)
                    try:
                        purge_queue(queue_url=sqs_url, sqs_client=sqs_client)
                    except Exception as e:
                        logger.error(f"Cannot purge queue :{e}")
                    return tasks
                logger.info(f'Received and deleted message(s) from {sqs_url}.')
            print(f"num_task_completed {num_task_completed}, target num_task :{num_task}")
        
    return tasks


    