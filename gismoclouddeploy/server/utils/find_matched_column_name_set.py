from .aws_utils import (
    read_column_from_csv_from_s3,
)
from typing import List, Set
import logging
import re

# logger config
logger = logging.getLogger()
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s: %(levelname)s: %(message)s"
)


def find_matched_column_name_set(
    columns_key: str = None,
    bucket_name: str = None,
    file_path_name: str = None,
    s3_client: "botocore.client.S3" = None,
    file_extension: str = ".csv",
) -> Set[set]:
    """
    Find the match column name from key word. if matched column has no value inside, it will be skipped.
    If this function find exactly match with key and column name , it return the the match column name in set.
    If no exactly match key was found, it return the partial match key with longest data set.
    """
    # check if file has .csv type , if not return "None"
    is_csv = re.search(file_extension, file_path_name)
    if not is_csv:
        return set()
    try:
        total_columns = read_column_from_csv_from_s3(
            bucket_name=bucket_name, file_path_name=file_path_name, s3_client=s3_client
        )
    except Exception as e:
        # logger.error(f"read column from s3 failed :{e}")
        raise e
    matched_column_set = set()
    for column in total_columns:
        match = re.search(columns_key, column)
        if match:
            matched_column_set.add(column)
    return matched_column_set
