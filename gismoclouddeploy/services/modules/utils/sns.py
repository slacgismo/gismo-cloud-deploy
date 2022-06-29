from botocore.exceptions import ClientError
import logging
import botocore

logger = logging.getLogger()
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s: %(levelname)s: %(message)s"
)


def create_sns_topic(name: str, sns_resource):
    """
    Creates a notification topic.

    :param name: The name of the topic to create.
    :return: The newly created topic.
    """

    topic = sns_resource.create_topic(Name=name)

    return topic


def list_topics(sns_resource):
    """
    Lists topics for the current account.

    :return: An iterator that yields the topics.
    """

    topics_iter = sns_resource.topics.all()
    return topics_iter


def publish_message(message: str, topic_arn: str, sns_client):

    message_id = sns_client.publish(
        TopicArn=topic_arn,
        Message=message,
    )

    return message_id


def delete_topic(topic_arn, sns_client: "botocore.client.SNS"):
    """
    Delete a SNS topic.
    """
    try:
        response = sns_client.delete_topic(TopicArn=topic_arn)
    except ClientError:
        logger.exception("Could not delete a SNS topic.")
        raise
    else:
        return response


def sns_subscribe_sqs(topic: str, endpoint: str, sns_client):
    """
    Subscribe to a topic using endpoint as email OR SMS
    """
    try:
        subscription = sns_client.subscribe(
            TopicArn=topic,
            Protocol="sqs",
            Endpoint=endpoint,
            ReturnSubscriptionArn=True,
        )["SubscriptionArn"]
    except ClientError:
        logger.exception("Couldn't subscribe {protocol} {endpoint} to topic {topic}.")
        raise
    else:
        return subscription


def list_sns(sns_resource):
    # topic= create_sns_topic('gismo-cloud-deploy-sns')
    # list_topic= list_topics()
    for topic in list_topics(sns_resource):
        print(topic)
    # print(f"start sns {list_topic}")
