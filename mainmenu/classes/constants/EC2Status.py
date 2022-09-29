import enum



class EC2Status(enum.Enum):
    running = "running"
    stopped = "stopped"
    terminated = "terminated"
    