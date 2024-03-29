import yaml


def convert_yaml_to_json(yaml_file: str = None) -> dict:
    """
    Convert yaml file to dictionary format

    Returns
    -------
    :return: a diction format
    """

    try:
        with open(yaml_file, "r") as stream:
            config_json = yaml.safe_load(stream)
        return config_json
    except IOError as e:
        raise f"I/O error:{e}"
