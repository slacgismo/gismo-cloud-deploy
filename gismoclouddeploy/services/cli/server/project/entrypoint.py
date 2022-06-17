import logging
import json

logger = logging.getLogger()
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s: %(levelname)s: %(message)s"
)

import enum


class Alert(enum.Enum):
    PROCESS_FILE_ERROR = "PROCESS_FILE_ERROR"
    SYSTEM_ERROR = "SYSTEM_ERROR"
    TIMEOUT = "TIMEOUT"
    SAVED_DATA = "SAVED_DATA"


def make_response(subject: str = None, messages: dict = None) -> dict:
    if subject is None:
        subject = Alert.SYSTEM_ERROR.name
        messages = "No subject in sns message"
        raise Exception("Message Input Error")

    if not isinstance(messages, dict):
        raise Exception("messages is not a json object")
    response = {"Subject": subject, "Messages": messages}
    return response


def entrypoint(*args, **kwargs) -> str:
    logging.info("----- This is template code , replaced this function")
    messages = {"solardatatools": "templates data"}
    # raise Exception("fake alert")
    return make_response(subject=Alert.SAVED_DATA.name, messages=messages)
