import enum


class ActionState(enum.Enum):
    ACTION_START = "idle-stop/busy-start"
    ACTION_STOP = "busy-stop/idle-start"
