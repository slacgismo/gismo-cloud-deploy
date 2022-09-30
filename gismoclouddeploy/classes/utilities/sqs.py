from botocore.exceptions import ClientError
import logging
import botocore
from mypy_boto3_sqs.service_resource import SQSServiceResource
from mypy_boto3_sqs.client import SQSClient

logger = logging.getLogger()
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s: %(levelname)s: %(message)s"
)
# SQS


def create_queue(
    queue_name: str = None,
    delay_seconds: int = 1,
    visiblity_timeout: int = 60,
    sqs_resource: SQSServiceResource = None,
    tags: dict = None,
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
            tags=tags,
        )
    except ClientError:
        logger.exception(f"Could not create SQS queue - {queue_name}.")
        raise
    else:
        return response


def send_queue_message(
    queue_url: str, msg_attributes: dict, msg_body: dict, sqs_client: SQSClient
):
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


def get_queue(queue_name: str, sqs_client: SQSClient):
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


def delete_queue(queue_url: str, sqs_client: SQSClient):
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


def purge_queue(queue_url: str, sqs_client: SQSClient) -> str:
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
    queue_url: str,
    sqs_client: SQSClient,
    MaxNumberOfMessages: int = 1,
    wait_time: int = 0,
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


def delete_queue_message(queue_url: str, receipt_handle: str, sqs_client: SQSClient):
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
