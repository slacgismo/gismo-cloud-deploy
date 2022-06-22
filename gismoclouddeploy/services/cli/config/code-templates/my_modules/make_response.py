from .Alert import Alert


# def make_response(subject: str = None, messages: dict = None) -> dict:
#     if subject is None:
#         subject = Alert.SYSTEM_ERROR.name
#         messages = "No subject in sns message"
#         raise Exception("Message Input Error")
#     if not isinstance(messages, dict):
#         raise Exception("messages is not a json object")
#     response = {"Subject": subject, "Messages": messages}
#     return response
def make_response(
    alert_type: str = None, messages: dict = None, user_id: str = None
) -> dict:
    subject = {"alert_type": alert_type, "user_id": user_id}
    messages["user_id"] = user_id

    if alert_type is None or user_id is None:
        subject["alert_type"] = Alert.SYSTEM_ERROR.name
        messages["messages"] = "No alert_type or  user_id in sns message"
        # subject = Alert.SYSTEM_ERROR.name
        # messages = "No subject or user id in sns message"
        raise Exception("Message Input Error")

    if not isinstance(messages, dict):
        raise Exception("messages is not a json object")

    response = {"Subject": subject, "Messages": messages}
    return response
