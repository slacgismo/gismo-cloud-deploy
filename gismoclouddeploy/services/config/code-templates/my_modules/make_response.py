from .Alert import Alert


def make_response(
    alert_type: str = None, messages: dict = None, user_id: str = None
) -> dict:
    """
    Make json message for SNS
    :param str alert_type: The alert types in Subject of SNS message.
    :param dict messages: The message contents of SNS message.
    :param str user_id: The user id generated from CLI. This used id is attached into Message and Subject of SNS message.
    """
    subject = {"alert_type": alert_type, "user_id": user_id}
    messages["user_id"] = user_id

    if alert_type is None or user_id is None:
        subject["alert_type"] = Alert.SYSTEM_ERROR.name
        messages["messages"] = "No alert_type or  user_id in sns message"
        raise Exception("Message Input Error")

    if not isinstance(messages, dict):
        raise Exception("messages is not a json object")

    response = {"Subject": subject, "Messages": messages}
    return response
