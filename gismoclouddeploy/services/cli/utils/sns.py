import boto3
#  SNS

def create_sns_topic(name, sns_resource):
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


def publish_message_to_sns(message: str, topic_arn:str,sns_client):


    message_id = sns_client.publish(
        TopicArn=topic_arn,
        Message=message,
    )

    return message_id


def subscribe(topic, protocol, endpoint):
    """
    Subscribes an endpoint to the topic. Some endpoint types, such as email,
    must be confirmed before their subscriptions are active. When a subscription
    is not confirmed, its Amazon Resource Number (ARN) is set to
    'PendingConfirmation'.

    :param topic: The topic to subscribe to.
    :param protocol: The protocol of the endpoint, such as 'sms' or 'email'.
    :param endpoint: The endpoint that receives messages, such as a phone number
                      or an email address.
    :return: The newly added subscription.
    """
    subscription = topic.subscribe(Protocol=protocol, Endpoint=endpoint, ReturnSubscriptionArn=True)
    return subscription