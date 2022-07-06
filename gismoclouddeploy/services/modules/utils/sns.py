from botocore.exceptions import ClientError
import logging
import botocore

logger = logging.getLogger()
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s: %(levelname)s: %(message)s"
)


def publish_message(message: str, topic_arn: str, sns_client):

    message_id = sns_client.publish(
        TopicArn=topic_arn,
        Message=message,
    )

    return message_id
