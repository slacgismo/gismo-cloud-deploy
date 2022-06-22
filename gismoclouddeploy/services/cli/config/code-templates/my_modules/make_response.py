from .Alert import Alert


def make_response(subject: str = None, messages: dict = None) -> dict:
    if subject is None:
        subject = Alert.SYSTEM_ERROR.name
        messages = "No subject in sns message"
        raise Exception("Message Input Error")
    if not isinstance(messages, dict):
        raise Exception("messages is not a json object")
    response = {"Subject": subject, "Messages": messages}
    return response
