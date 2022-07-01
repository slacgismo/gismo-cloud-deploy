from botocore.exceptions import ClientError
import logging
import time
import botocore
import json

logger = logging.getLogger()
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s: %(levelname)s: %(message)s"
)
# SQS


def create_standard_queue(
    queue_name: str,
    delay_seconds: int,
    visiblity_timeout: int,
    sqs_resource: "botocore.resource.SQS",
):
    """
    Create a standard SQS queue
    """
    try:
        response = sqs_resource.create_queue(
            QueueName=queue_name,
            Attributes={
                "DelaySeconds": delay_seconds,
                "VisibilityTimeout": visiblity_timeout,
            },
        )
    except ClientError:
        logger.exception(f"Could not create SQS queue - {queue_name}.")
        raise
    else:
        return response


def create_fifo_queue(queue_name, delay_seconds, visiblity_timeout, sqs_resource):
    """
    Create a First In First Out (FIFO) SQS queue
    """

    try:
        response = sqs_resource.create_queue(
            QueueName=queue_name,
            Attributes={
                "DelaySeconds": delay_seconds,
                "VisibilityTimeout": visiblity_timeout,
                "FifoQueue": "true",
            },
        )
    except ClientError as e:
        logger.exception(f"Could not create SQS queue - {queue_name}.")
        raise e

    return response


def list_queues(sqs_resource):
    """
    Creates an iterable of all Queue resources in the collection.
    """
    try:
        sqs_queues = []
        for queue in sqs_resource.queues.all():
            sqs_queues.append(queue)
            print(queue)
    except ClientError:
        logger.exception("Could not list queues.")
        raise
    else:

        return sqs_queues


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


def delete_queue(queue_name: str, sqs_client: "botocore.client.SQS"):
    """
    Deletes the queue specified by the QueueUrl.
    """

    try:
        response = sqs_client.delete_queue(QueueUrl=queue_name)

    except ClientError:
        logger.exception(f"Could not delete the {queue_name} queue.")
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


def send_queue_message(queue_url, msg_attributes, msg_body, sqs_client):
    """
    Sends a message to the specified queue.
    """
    try:
        response = sqs_client.send_message(
            QueueUrl=queue_url, MessageAttributes=msg_attributes, MessageBody=msg_body
        )
    except ClientError:
        logger.exception(f"Could not send meessage to the - {queue_url}.")
        raise
    else:
        return response


def enable_existing_queue_long_pulling(
    queue_url: str, msg_rcv_wait_time: int, sqs_client: "botocore.client.SQS"
):
    """
    Configure queue to for long polling.
    """
    try:
        response = sqs_client.set_queue_attributes(
            QueueUrl=queue_url,
            Attributes={"ReceiveMessageWaitTimeSeconds": msg_rcv_wait_time},
        )
    except ClientError:
        logger.exception(f"Could not configure long polling on - {queue_url}.")
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


def read_from_sqs_queue(queue_url: str, sqs_client: "botocore.client.SQS"):

    messages = sqs_client.receive_message(
        QueueUrl=queue_url,
        MaxNumberOfMessages=1,
    )

    return messages


def configure_queue_long_polling(
    queue_url: str, msg_rcv_wait_time: int, sqs_client: "botocore.client.SQS"
):
    """
    Configure queue to for long polling.
    """
    try:
        response = sqs_client.set_queue_attributes(
            QueueUrl=queue_url,
            Attributes={"ReceiveMessageWaitTimeSeconds": msg_rcv_wait_time},
        )
    except ClientError:
        logger.exception(f"Could not configure long polling on - {queue_url}.")
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
                # msg_body = msg["Body"]
                msg_body = json.loads(msg["Body"])
                # logger.info(f"msg_body {msg_body}")
                receipt_handle = msg["ReceiptHandle"]
                subject = (
                    msg_body["Subject"].strip("'<>() ").replace("'", '"').strip("\n")
                )
                if subject == user_id:
                    logger.info(f"Delete {index} message")
                    index += 1
                    delete_queue_message(sqs_url, receipt_handle, sqs_client)
                # try:
                #     subject_info = json.loads(subject)
                #     sns_user_id = subject_info["user_id"]
                #     if sns_user_id == user_id:
                #         delete_queue_message(sqs_url, receipt_handle, sqs_client)

                # except Exception as e:
                #     logger.warning(
                #         f"Delet this {subject} !!, This subject is not json format {e}"
                #     )

        else:
            logger.info("Clean previous message completed")
            return

        counter -= 1
        time.sleep(delay)
