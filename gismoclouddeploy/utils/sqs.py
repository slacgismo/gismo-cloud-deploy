from botocore.exceptions import ClientError
import logging
import time
import botocore
import json
import re
logger = logging.getLogger()
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s: %(levelname)s: %(message)s"
)
# SQS

def create_queue(queue_name:str = None, delay_seconds:int = 1, visiblity_timeout:int = 60, sqs_resource:str = None, tags:dict = None):
    """
    Create a standard SQS queue
    """
    try:
        response = sqs_resource.create_queue(QueueName=queue_name,
                                            Attributes={
                                                 'DelaySeconds': delay_seconds,
                                                 'VisibilityTimeout': visiblity_timeout
                                             },
                                            tags=tags
                                            )
    except ClientError:
        logger.exception(f'Could not create SQS queue - {queue_name}.')
        raise
    else:
        return response

# def send_queue_message(queue_name, msg_attributes, msg_body,sqs_client):
#     """
#     Sends a message to the specified queue.
#     """
#     try:
#         queue = sqs_client.get_queue_url(QueueName=queue_name)
#         queue_url=queue['QueueUrl']
#         response = sqs_client.send_message(QueueUrl=queue_url,
#                                            MessageAttributes=msg_attributes,
#                                            MessageBody=msg_body)
#     except ClientError:
#         logger.exception(f'Could not send meessage to the - {queue_url}.')
#         raise
#     else:
#         return response


def send_queue_message(queue_url, msg_attributes, msg_body,sqs_client):
    """
    Sends a message to the specified queue.
    """
    try:
        response = sqs_client.send_message(QueueUrl=queue_url,
                                           MessageAttributes=msg_attributes,
                                           MessageBody=msg_body)
    except ClientError:
        logger.exception(f'Could not send meessage to the - {queue_url}.')
        raise
    else:
        return response

def get_queue(queue_name: str, sqs_client: "botocore.client.SQS"):
    """
    Returns the URL of an existing Amazon SQS queue.
    """
    try:
        response = sqs_client.get_queue_url(QueueName=queue_name)["QueueUrl"]

    except ClientError:
        logger.exception(f"Could not get the {queue_name} queue.")
        raise
    else:
        return response


def delete_queue(queue_url: str, sqs_client: "botocore.client.SQS"):
    """
    Deletes the queue specified by the QueueUrl.
    """

    try:
        response = sqs_client.delete_queue(QueueUrl=queue_url)

    except ClientError:
        logger.exception(f"Could not delete the {queue_url} queue.")
        raise
    else:
        return response


def purge_queue(queue_url, sqs_client):
    """
    Deletes the messages in a specified queue
    """
    try:
        response = sqs_client.purge_queue(QueueUrl=queue_url)
        logger.info(f"Purge QUEUE {queue_url} ")
    except ClientError:
        logger.exception(f"Could not purge the queue - {queue_url}.")
        raise
    else:
        return response


def receive_queue_message(
    queue_url: str, sqs_client, MaxNumberOfMessages: int = 1, wait_time: int = 0
):
    """
    Retrieves one or more messages (up to 10), from the specified queue.
    """
    try:
        response = sqs_client.receive_message(
            QueueUrl=queue_url,
            AttributeNames=["SentTimestamp"],
            MaxNumberOfMessages=MaxNumberOfMessages,
            MessageAttributeNames=["All"],
            WaitTimeSeconds=wait_time,
        )
    except ClientError:
        logger.exception(f"Could not receive the message from the - {queue_url}.")
        raise
    else:
        return response


def delete_queue_message(
    queue_url: str, receipt_handle: str, sqs_client: "botocore.client.SQS"
):
    """
    Deletes the specified message from the specified queue.
    """
    try:
        response = sqs_client.delete_message(
            QueueUrl=queue_url, ReceiptHandle=receipt_handle
        )
    except ClientError:
        logger.exception(f"Could not delete the meessage from the - {queue_url}.")
        raise
    else:
        return response


def clean_user_previous_sqs_message(
    sqs_url: str,
    sqs_client: "botocore.client.SQS",
    wait_time: int,
    counter: int,
    delay: int,
    user_id: str,
):
    index = 0
    while counter:
        messages = receive_queue_message(
            queue_url=sqs_url,
            MaxNumberOfMessages=10,
            sqs_client=sqs_client,
            wait_time=wait_time,
        )
        # print(messages)
        if "Messages" in messages:
            for msg in messages["Messages"]:
                msg_body = msg["Body"]
                
                # print(msg_body)
                MessageAttributes = msg['MessageAttributes']
                # body = msg["Body"].strip("\'<>() ").replace("'", '"').strip("\n")
                # msg_body = json.loads( msg["Body"])
                # logger.info(f"msg_body {msg_body}")
                # print("------------")
                # # # print(json_obj)
                # json_obj  = json.loads(msg_body)
                # print(json_obj)
                # # data =json_obj['data']
                # # error = json_obj['error']
                # # print(data)
                # print(error)
                receive_message_user_id = MessageAttributes['user_id']['StringValue']
                # print(user_id)
                # print("------------")
                receipt_handle = msg["ReceiptHandle"]
                # subject = (
                #     msg_body["Subject"].strip("'<>() ").replace("'", '"').strip("\n")
                # )
                if receive_message_user_id == user_id:
                    logger.info(f"Delete {index} message")
                    index += 1
                    delete_queue_message(sqs_url, receipt_handle, sqs_client)

        else:
            logger.info("Clean previous message completed")
            return

        counter -= 1
        time.sleep(delay)


def list_queues(sqs_resource, queue_prefix ):
    """
    Creates an iterable of all Queue resources in the collection.
    """
    try:
        sqs_queues = []
        for queue in sqs_resource.queues.filter(QueueNamePrefix=queue_prefix):
        # for queue in sqs_resource.queues.all():
            sqs_queues.append(queue)
    except ClientError:
        logger.exception('Could not list queues.')
        raise
    else:
        return sqs_queues
