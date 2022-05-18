import threading
import time
import logging
# logger config
import json

from utils.aws_utils import(
    connect_aws_client,
)
from utils.sqs import (
    receive_queue_message,
    delete_queue_message,
    purge_queue
)
from typing import List
logger = logging.getLogger()
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s: %(levelname)s: %(message)s')

import typing
class taskThread (threading.Thread):
    def __init__(self, threadID:int, name:str, conuter:int, wait_time:int, sqs_url:str, num_task:int):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.wait_time = wait_time
        self.counter = conuter
        self.sqs_url = sqs_url
        self.num_task = num_task



    def run(self):
      print ("Starting " + self.name)
      long_pulling_sqs(self.counter, self.wait_time, self.sqs_url, self.num_task)
      print ("Exiting " + self.name)


def long_pulling_sqs(counter:int,wait_time:int,sqs_url:str,num_task:int) -> List[str]:
    sqs_client = connect_aws_client('sqs')
    tasks = []
    num_task_completed = 0
    while counter:
        time.sleep(wait_time)
        messages = receive_queue_message(sqs_url, sqs_client, wait_time=wait_time)
        print(f"waiting ....counter: {counter - wait_time} Time: {time.ctime(time.time())}")
        counter -= int(wait_time)
        if 'Messages' in messages :
            for msg in messages['Messages']:
                msg_body = json.loads(msg['Body'])
                # msg_body = msg['Body']
                receipt_handle = msg['ReceiptHandle']
                Subject  = msg_body['Subject']
                message_text = msg_body['Message']
                logger.info(f'The subject : {Subject}')
                logger.info(f'The message : {message_text}')
                # logger.info('Deleting message from the queue...')
                delete_queue_message(sqs_url, receipt_handle, sqs_client)
                tasks.append(message_text)
                num_task_completed += 1
            logger.info(f'Received and deleted message(s) from {sqs_url}.')
            # return True
        print(f"num_task_completed {num_task_completed}, num_task:{num_task}")
        if num_task_completed == int(num_task):
            logger.info("All task completed")
            return tasks
    # purge queue at end of task
    purge_queue(queue_url=sqs_url, sqs_client=sqs_client)
    return tasks