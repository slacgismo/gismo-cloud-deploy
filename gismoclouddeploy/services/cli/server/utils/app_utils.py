from .aws_utils import (
    read_column_from_csv_from_s3,
    read_csv_from_s3_with_column_name,
    list_files_in_bucket,
)
from typing import List, Set
import logging

# logger config
logger = logging.getLogger()
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s: %(levelname)s: %(message)s"
)


def find_matched_column_name_set(
    columns_key: str,
    bucket_name: str,
    file_path_name: str,
    s3_client: "botocore.client.S3",
) -> Set[set]:
    """
    Find the match column name from key word. if matched column has no value inside, it will be skipped.
    If this function find exactly match with key and column name , it return the the match column name in set.
    If no exactly match key was found, it return the partial match key with longest data set.
    """
    try:
        total_columns = read_column_from_csv_from_s3(
            bucket_name=bucket_name, file_path_name=file_path_name, s3_client=s3_client
        )
    except Exception as e:
        # logger.error(f"read column from s3 failed :{e}")
        raise e
    matched_column_set = set()
    for column in total_columns:
        for key in columns_key:
            if key in column:
                matched_column_set.add(column)
    # validated_column_set = set()
    # for key in matched_column_set:
    #     # check if column has value.
    #     try:
    #         tmp_df = read_csv_from_s3_with_column_name(
    #             bucket_name=bucket_name,
    #             file_path_name=file_path_name,
    #             column_name=key,
    #             s3_client=s3_client,
    #         )
    #     except Exception as e:
    #         # logger.error(f"read csv from s3 failed :{e}")
    #         raise e
    #     if len(tmp_df) == 0:
    #         # logger.info(f" ==== > {key} has no value === ")
    #         continue
    #     validated_column_set.add(key)
    return matched_column_set


def get_process_filename_base_on_command(
    first_n_files: str,
    bucket: str,
    default_files: List[str],
    s3_client: "botocore.client.S3",
) -> List[str]:

    n_files = []
    files_dict = list_files_in_bucket(bucket_name=bucket, s3_client=s3_client)

    if first_n_files == "None":
        n_files = default_files
    else:
        try:
            if int(first_n_files) == 0:
                logger.info(f"Process all files in {bucket}")
                for file in files_dict:
                    n_files.append(file["Key"])
            else:
                logger.info(f"Process first {first_n_files} files")
                for file in files_dict[0 : int(first_n_files)]:
                    n_files.append(file["Key"])
        except Exception as e:
            logger.error(f"Input {first_n_files} is not an integer")
            raise e
    return n_files
