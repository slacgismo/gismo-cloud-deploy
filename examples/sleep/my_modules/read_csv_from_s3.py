import pandas as pd
import boto3


def read_csv_from_s3(
    bucket_name: str = None,
    file_path_name: str = None,
    column_name: str = None,
    index_col: int = 0,
    parse_dates=[0],
    aws_access_key: str = None,
    aws_secret_access_key: str = None,
    aws_region: str = None,
) -> pd.DataFrame:
    """
    Read csv file from s3 bucket with defined column , and time column.
    :param : bucket_name
    :param : file_path_name
    :param : column_name
    :param : index_col, column of index
    :param : parse_dates, column of time
    :param : aws_access_key
    :param : aws_secret_access_key
    :param : aws_region
    :return: dataframe.
    """

    if (
        bucket_name is None
        or file_path_name is None
        or column_name is None
        or aws_access_key is None
        or aws_secret_access_key is None
        or aws_region is None
    ):
        return
    try:
        s3_client = boto3.client(
            "s3",
            region_name=aws_region,
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_access_key,
        )
        response = s3_client.get_object(Bucket=bucket_name, Key=file_path_name)

        status = response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        if status != 200:
            return Exception(f"Unsuccessful S3 get_object response. Status - {status}")

        result_df = pd.read_csv(
            response.get("Body"),
            index_col=index_col,
            parse_dates=parse_dates,
            usecols=["Time", column_name],
        )
        return result_df
    except Exception as e:
        raise Exception(f"Read csv fialed:{e}")
