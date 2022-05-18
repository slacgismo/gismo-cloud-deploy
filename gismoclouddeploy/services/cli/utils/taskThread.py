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
    delete_queue_message
)

logger = logging.getLogger()
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s: %(levelname)s: %(message)s')

class taskThread (threading.Thread):
    def __init__(self, threadID:int, name:str, conuter:int, wait_time:int, sqs_url:str):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.wait_time = wait_time
        self.counter = conuter
        self.sqs_url = sqs_url



    def run(self):
      print ("Starting " + self.name)
      long_pulling_sqs(self.counter, self.wait_time, self.sqs_url)
      print ("Exiting " + self.name)


def long_pulling_sqs(counter:int,wait_time:int,sqs_url:str) -> bool:
    sqs_client = connect_aws_client('sqs')
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
            
            logger.info(f'Received and deleted message(s) from {sqs_url}.')
            return True
    return True