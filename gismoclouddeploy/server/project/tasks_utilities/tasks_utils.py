

import logging
from botocore.exceptions import ClientError

# logger config
logger = logging.getLogger()
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s: %(levelname)s: %(message)s"
)


def make_response(subject: str = None, messages: str = None) -> dict:
    response = {"Subject": subject, "Messages": messages}
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
