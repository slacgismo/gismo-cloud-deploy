import imp
from .check_aws import connect_aws_resource, connect_aws_client
from boto3.dynamodb.conditions import Key, Attr
from .WORKER_CONFIG import WORKER_CONFIG
import pandas as pd
from io import StringIO


def remove_all_user_items_from_dynamodb(
    table_name: str,
    aws_access_key: str,
    aws_secret_access_key: str,
    aws_region: str,
    user_id: str,
):
    dynamodb_resource = connect_aws_resource(
        resource_name="dynamodb",
        key_id=aws_access_key,
        secret=aws_secret_access_key,
        region=aws_region,
    )

    # table = dynamodb_resource.Table(table_name)
    # response = table.query(KeyConditionExpression=Key("user_id").eq(user_id))
    table = dynamodb_resource.Table(table_name)
    # response = table.query(KeyConditionExpression=Key("user_id").eq(user_id))
    response = table.query(KeyConditionExpression=Key("user_id").eq(user_id))
    data = response["Items"]

    while "LastEvaluatedKey" in response:
        response = table.query(
            ExclusiveStartKey=response["LastEvaluatedKey"],
            KeyConditionExpression=Key("user_id").eq(user_id),
        )
        data += response["Items"]
    print(f"Total items in dynamodb {len(data)}")
    # delete dynamodb items
    try:
        with table.batch_writer() as batch:
            for each in data:
                batch.delete_item(
                    Key={"user_id": each["user_id"], "timestamp": each["timestamp"]}
                )
        print(f"remove all items of {user_id} from dynamodb completed")
    except Exception as e:
        raise Exception(f"Delete items from dynamodb failed{e}")
    return


def download_logs_saveddata_from_dynamodb(
    worker_config: WORKER_CONFIG = None,
    aws_access_key: str = None,
    aws_secret_key: str = None,
    aws_region: str = None,
) -> None:
    try:
        save_data_file = (
            worker_config.saved_path + "/" + worker_config.saved_data_target_filename
        )
        save_logs_file = (
            worker_config.saved_path + "/" + worker_config.saved_logs_target_filename
        )
        save_error_file = (
            worker_config.saved_path + "/" + worker_config.saved_error_target_filename
        )
        save_user_logs_data_from_dynamodb(
            table_name=worker_config.dynamodb_tablename,
            user_id=worker_config.user_id,
            saved_bucket=worker_config.saved_bucket,
            save_data_file=save_data_file,
            save_logs_file=save_logs_file,
            save_error_file=save_error_file,
            aws_access_key=aws_access_key,
            aws_secret_key=aws_secret_key,
            aws_region=aws_region,
        )
    except Exception as e:
        raise Exception(f"Failed to save data and logs from dynamodb {e}")


def save_user_logs_data_from_dynamodb(
    table_name: str = None,
    user_id: str = None,
    saved_bucket: str = None,
    save_data_file: str = None,
    save_logs_file: str = None,
    save_error_file: str = None,
    aws_access_key: str = None,
    aws_secret_key: str = None,
    aws_region: str = None,
) -> None:

    dynamodb_resource = connect_aws_resource(
        resource_name="dynamodb",
        key_id=aws_access_key,
        secret=aws_secret_key,
        region=aws_region,
    )

    table = dynamodb_resource.Table(table_name)
    # response = table.query(KeyConditionExpression=Key("user_id").eq(user_id))
    response = table.query(KeyConditionExpression=Key("user_id").eq(user_id))
    data = response["Items"]
    index = 0
    while "LastEvaluatedKey" in response:
        response = table.query(
            ExclusiveStartKey=response["LastEvaluatedKey"],
            KeyConditionExpression=Key("user_id").eq(user_id),
        )
        data += response["Items"]
        print(f"Get first {len(data)} itmes")
    print(f"Total items in dynamodb {len(data)}")

    if len(data) == 0:
        print("No data in dynamodb")
        return
    save_data = []
    all_logs = []
    error_logs = []
    # # print(f"Load from db {response} -------> ")
    for i in data:
        all_logs.append(i)
        # print(i)
        if i["alert_type"] == "SAVED_DATA":
            save_data.append(i["messages"])
        if i["alert_type"] == "SYSTEM_ERROR":
            error_logs.append(i)

    try:
        # save data
        save_data_df = pd.json_normalize(save_data)
        save_dataframe_csv_on_s3(
            dataframe=save_data_df,
            saved_bucket=saved_bucket,
            saved_file=save_data_file,
            aws_access_key=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            aws_region=aws_region,
        )
        # save logs
        logs_df = pd.json_normalize(all_logs)
        # print(f"---> logs_df {logs_df}")
        save_dataframe_csv_on_s3(
            dataframe=logs_df,
            saved_bucket=saved_bucket,
            saved_file=save_logs_file,
            aws_access_key=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            aws_region=aws_region,
        )
        # save error
        if len(error_logs) > 0:
            error_df = pd.json_normalize(error_logs)

            save_dataframe_csv_on_s3(
                dataframe=error_df,
                saved_bucket=saved_bucket,
                saved_file=save_error_file,
                aws_access_key=aws_access_key,
                aws_secret_access_key=aws_secret_key,
                aws_region=aws_region,
            )
    except Exception as e:
        raise Exception(f"Save data to s3 failed{e}")
    # delete dynamodb items
    print(f"Deleting dyanmodb items")
    try:
        index = 0
        with table.batch_writer() as batch:
            for each in data:
                batch.delete_item(
                    Key={"user_id": each["user_id"], "timestamp": each["timestamp"]}
                )
                index += 1
                if index % 500 == 0:
                    print(f"First {index} itmes deleted")
        print(f"Remove all items of {user_id} from dynamodb completed")
    except Exception as e:
        raise Exception(f"Delete items from dynamodb failed{e}")
    return


def save_dataframe_csv_on_s3(
    dataframe: pd,
    saved_bucket: str,
    saved_file: str,
    aws_access_key: str,
    aws_secret_access_key: str,
    aws_region: str,
) -> None:
    csv_buffer = StringIO()
    dataframe.to_csv(csv_buffer)
    content = csv_buffer.getvalue()
    # remove preivous logs.csv
    s3_client = connect_aws_client(
        client_name="s3",
        key_id=aws_access_key,
        secret=aws_secret_access_key,
        region=aws_region,
    )
    try:
        s3_client.put_object(Bucket=saved_bucket, Key=saved_file, Body=content)
    except Exception as e:
        raise f"Save dataframe to s3 failed:{e}"

    return
