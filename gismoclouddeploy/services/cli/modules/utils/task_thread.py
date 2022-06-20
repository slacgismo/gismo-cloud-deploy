import threading
import time
import logging
import json
import botocore
import boto3
from server.models.Configurations import AWS_CONFIG, WORKER_CONFIG
import pandas as pd
from io import StringIO
import re
from server.utils.aws_utils import (
    connect_aws_client,
    check_environment_is_aws,
    save_logs_from_dynamodb_to_s3,
    remove_all_items_from_dynamodb,
    delete_ecr_image,
)

from server.models import SNSSubjectsAlert

from .invoke_function import (
    invoke_docekr_exec_revoke_task,
    invoke_ks8_exec_revoke_task,
    invoke_docker_compose_down_and_remove,
    invoke_kubectl_delete_all_deployment,
    invoke_kubectl_delete_all_services,
)
from modules.utils.sqs import (
    receive_queue_message,
    delete_queue_message,
    purge_queue,
    send_queue_message,
)
from typing import List
from .command_utils import combine_files_to_file

from modules.utils.eks_utils import scale_eks_nodes_and_wait
from modules.utils.process_log import process_logs_from_s3


logger = logging.getLogger()
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s: %(levelname)s: %(message)s"
)


class TaskThread(threading.Thread):
    def __init__(
        self,
        threadID: int,
        name: str,
        counter: int,
        wait_time: int,
        sqs_url: str,
        num_task: int,
        aws_config: AWS_CONFIG,
        worker_config: WORKER_CONFIG,
        delete_nodes_after_processing: bool,
        is_docker: bool,
        dlq_url: str,
        key_id: str,
        secret_key: str,
        aws_region: str,
    ):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.wait_time = wait_time
        self.counter = counter
        self.sqs_url = sqs_url
        self.num_task = num_task
        self.aws_config = aws_config
        self.worker_config = worker_config
        self.delete_nodes_after_processing = delete_nodes_after_processing
        self.is_docker = is_docker
        self.dlq_url = dlq_url
        self.key_id = key_id
        self.secret_key = secret_key
        self.aws_region = aws_region

    def run(self):
        print("Starting " + self.name)
        long_pulling_sqs(
            counter=self.counter,
            wait_time=self.wait_time,
            sqs_url=self.sqs_url,
            num_task=self.num_task,
            aws_config=self.aws_config,
            worker_config=self.worker_config,
            delete_nodes_after_processing=self.delete_nodes_after_processing,
            is_docker=self.is_docker,
            dlq_url=self.dlq_url,
            key_id=self.key_id,
            secret_key=self.secret_key,
            aws_region=self.aws_region,
        )
        print("Exiting " + self.name)


def send_mesage_to_DLQ(
    subject: str, message: str, dlq_url: str, sqs_client: "botocore.client.SQS"
):
    #  move message to deal letter queue
    MSG_ATTRIBUTES = {"Title": {"DataType": "String", "StringValue": subject}}
    MSG_BODY = message
    try:
        dlq_res = send_queue_message(
            queue_url=dlq_url,
            msg_attributes=MSG_ATTRIBUTES,
            msg_body=MSG_BODY,
            sqs_client=sqs_client,
        )
        logger.info(f" ==== DLG  ========\n {dlq_res}")
    except Exception as e:
        raise e


def long_pulling_sqs(
    counter: int,
    wait_time: int,
    sqs_url: str,
    num_task: int,
    worker_config: WORKER_CONFIG,
    aws_config: AWS_CONFIG,
    delete_nodes_after_processing: bool,
    is_docker: bool,
    dlq_url: str,
) -> List[str]:
    sqs_client = connect_aws_client(
        client_name="sqs",
        key_id=aws_config.aws_access_key,
        secret=aws_config.aws_secret_access_key,
        region=aws_config.aws_region,
    )
    tasks = []
    num_task_completed = 0
    while counter:
        time.sleep(wait_time)
        messages = receive_queue_message(
            sqs_url, sqs_client, MaxNumberOfMessages=1, wait_time=wait_time
        )
        logger.info(
            f"waiting ....counter: {counter - wait_time} \
            Time: {time.ctime(time.time())}"
        )
        counter -= int(wait_time)
        if "Messages" in messages:
            for msg in messages["Messages"]:
                msg_body = json.loads(msg["Body"])
                # msg_body = msg['Body']
                receipt_handle = msg["ReceiptHandle"]
                subject = msg_body["Subject"]
                message_text = msg_body["Message"]
                logger.info(f"The subject : {subject}")
                logger.info(f"The message : {message_text}")
                if subject == SNSSubjectsAlert.SAVED_DATA.name:

                    temp_str = message_text.replace("'", '"')
                    json_obj = json.loads(temp_str)
                    file_name = json_obj["file"]
                    prefix = file_name.replace("/", "-")
                    column = json_obj["column"]
                    postfix = re.sub(r'[\\/*?:"<>|()]', "", column)
                    temp_filenmae = f"{prefix}-{postfix}"
                    temp_file_name = (
                        worker_config.saved_tmp_path + "/" + f"{temp_filenmae}.csv"
                    )

                    save_messages_to_s3(
                        messages=message_text,
                        save_bucket=worker_config.saved_bucket,
                        saved_file_path_and_name=temp_file_name,
                        aws_access_key=aws_config.aws_access_key,
                        aws_secret_access_key=aws_config.aws_secret_access_key,
                        aws_region=aws_config.aws_region,
                    )

                delete_queue_message(sqs_url, receipt_handle, sqs_client)
                tasks.append(message_text)
                num_task_completed += 1
                if subject == SNSSubjectsAlert.TIMEOUT.name:
                    logger.info(f"======> force {message_text} to reovke ")
                    task_id_dict = json.loads(message_text)
                    if "task_id" in task_id_dict:
                        task_id = task_id_dict["task_id"]
                        if is_docker:
                            logger.info("reovk docker task")
                            revoke_resp = invoke_docekr_exec_revoke_task(
                                image_name="server", task_id=task_id
                            )
                        else:
                            logger.info("reovk k8s task")
                            revoke_resp = invoke_ks8_exec_revoke_task(
                                pod_name="server", task_id=task_id
                            )
                if (
                    subject == SNSSubjectsAlert.PROCESS_FILE_ERROR.name
                    or subject == SNSSubjectsAlert.SYSTEM_ERROR.name
                ):
                    # send error message to DLQ ,
                    send_mesage_to_DLQ(
                        subject=subject,
                        message=message_text,
                        dlq_url=dlq_url,
                        sqs_client=sqs_client,
                    )

                if (
                    subject
                    == SNSSubjectsAlert.All_TASKS_COMPLETED.name
                    # or subject == SNSSubjectsAlert.SYSTEM_ERROR.name
                ):
                    # close program after tasks complete or system error
                    logger.info(f"subject:{subject} message: {message_text}")
                    return
                logger.info(f"Received and deleted message(s) from {sqs_url}.")
            print(
                f"num_task_completed {num_task_completed},\
                target num_task :{num_task}"
            )

    return tasks


def save_messages_to_s3(
    messages: str = None,
    save_bucket: str = None,
    saved_file_path_and_name: str = None,
    aws_access_key: str = None,
    aws_secret_access_key: str = None,
    aws_region: str = None,
) -> None:

    """
    Save json data format to S3 bucket in a temporary file path and name.
    :param number saved_data: saved data in json object format
    :param number save_bucket: saved bucket is S3 (If you would like to modify bucket, )
    :param number saved_file_path_and_name: save temp file
    :param number aws_access_key:
    :param number aws_secret_access_key:
    :param number aws_region:
    """
    if (
        messages is None
        or save_bucket is None
        or saved_file_path_and_name is None
        or aws_access_key is None
        or aws_secret_access_key is None
        or aws_region is None
    ):
        raise Exception("Input Error")
    try:
        str = messages.replace("'", '"')
        json_obj = json.loads(str)
        df = pd.json_normalize(json_obj)
        csv_buffer = StringIO()
        df.to_csv(csv_buffer)
        content = csv_buffer.getvalue()
        s3_client = connect_aws_client(
            "s3", key_id=aws_access_key, secret=aws_secret_access_key, region=aws_region
        )

        s3_client.put_object(
            Bucket=save_bucket, Key=saved_file_path_and_name, Body=content
        )

        logger.info(f"save_bucket:{save_bucket} {saved_file_path_and_name} success")
        return True
    except Exception as e:
        logger.error(f"save to s3 error ---> {e}")
        raise e
