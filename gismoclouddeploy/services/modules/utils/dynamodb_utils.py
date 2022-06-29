from .check_aws import connect_aws_resource, connect_aws_client
from boto3.dynamodb.conditions import Key, Attr
from .WORKER_CONFIG import WORKER_CONFIG
import pandas as pd
from io import StringIO
from typing import List, Set, Union
import os
import logging
import json
import time
from boto3.dynamodb.types import TypeDeserializer

logger = logging.getLogger()
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s: %(levelname)s: %(message)s"
)


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
        save_data_file_aws = (
            worker_config.saved_path_aws
            + "/"
            + worker_config.saved_data_target_filename
        )
        save_logs_file_aws = (
            worker_config.saved_path_aws
            + "/"
            + worker_config.saved_logs_target_filename
        )
        save_error_file_aws = (
            worker_config.saved_path_aws
            + "/"
            + worker_config.saved_error_target_filename
        )
        save_user_logs_data_from_dynamodb(
            table_name=worker_config.dynamodb_tablename,
            user_id=worker_config.user_id,
            saved_bucket=worker_config.saved_bucket,
            save_data_file=save_data_file_aws,
            save_logs_file=save_logs_file_aws,
            save_error_file=save_error_file_aws,
            aws_access_key=aws_access_key,
            aws_secret_key=aws_secret_key,
            aws_region=aws_region,
        )
    except Exception as e:
        raise Exception(f"Failed to save data and logs from dynamodb {e}")


def query_items_from_dynamodb_with_userid(
    aws_access_key: str = None,
    aws_secret_access_key: str = None,
    aws_region: str = None,
    table_name: str = None,
    user_id: str = None,
    save_data_file: str = None,
    save_logs_file: str = None,
    save_error_file: str = None,
    task_ids_set: Set[str] = None,
    previous_messages_time: time = None,
) -> Union[set, float]:
    dynamodb_resource = connect_aws_resource(
        resource_name="dynamodb",
        key_id=aws_access_key,
        secret=aws_secret_access_key,
        region=aws_region,
    )

    table = dynamodb_resource.Table(table_name)
    # response = table.query(KeyConditionExpression=Key("user_id").eq(user_id))
    response = table.query(KeyConditionExpression=Key("user_id").eq(user_id))
    dynamo_items = response["Items"]
    index = 0
    while "LastEvaluatedKey" in response:
        response = table.query(
            ExclusiveStartKey=response["LastEvaluatedKey"],
            KeyConditionExpression=Key("user_id").eq(user_id),
        )
        dynamo_items += response["Items"]
        print(f"Get first {len(dynamo_items)} itmes")
    print(f"Total items in dynamodb {len(dynamo_items)}")

    if len(dynamo_items) == 0:
        logger.info("No data in dynamodb yet!!")
        return task_ids_set, previous_messages_time

    save_data = []
    all_logs = []
    error_logs = []
    # # print(f"Load from db {response} -------> ")
    for i in dynamo_items:
        all_logs.append(i)
        # start_time = i['start_time']
        # end_time = i['end_time']
        alert_type = i["alert_type"]
        messages = i["messages"]
        task_id = i["task_id"]

        if alert_type == "SAVED_DATA":
            message_json = json.loads(messages)
            save_data.append(message_json)

        if alert_type == "SYSTEM_ERROR":
            error_logs.append(i)
        if task_id in task_ids_set:
            task_ids_set.remove(task_id)
            logger.info(f"{task_id} Completed")
            previous_messages_time = time.time()

    save_data_df = pd.json_normalize(save_data)
    save_data_df.to_csv(
        save_data_file, mode="a", header=not os.path.exists(save_data_file)
    )
    save_logs_df = pd.json_normalize(all_logs)
    save_logs_df.to_csv(
        save_logs_file, mode="a", header=not os.path.exists(save_logs_file)
    )
    if len(error_logs) > 0:
        save_error_df = pd.json_normalize(error_logs)
        save_error_df.to_csv(
            save_error_file, mode="a", header=not os.path.exists(save_error_file)
        )

    print(f"Save {len(dynamo_items)} completed")
    # remove data

    print(f"Deleting {len(dynamo_items)} items from dynamodb")
    try:
        index = 0
        with table.batch_writer() as batch:
            for each in dynamo_items:
                batch.delete_item(
                    Key={"user_id": each["user_id"], "timestamp": each["timestamp"]}
                )
                index += 1
                if index % 300 == 0:
                    print(f"First {index} itmes deleted")
        print(f"Remove {index} items of {user_id} from dynamodb completed")
    except Exception as e:
        raise Exception(f"Delete items from dynamodb failed{e}")

    return task_ids_set, previous_messages_time


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
) -> bool:

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
        return False

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


def retrive_all_item_from_dyanmodb(
    table_name: str, dynamo_client: "botocore.client.dynamo"
):

    deserializer = TypeDeserializer()
    items = []
    for item in scan_table(dynamo_client, TableName=table_name):
        deserialized_document = {
            k: deserializer.deserialize(v) for k, v in item.items()
        }
        items.append(deserialized_document)
    return items


def scan_table(dynamo_client, *, TableName, **kwargs):

    paginator = dynamo_client.get_paginator("scan")

    for page in paginator.paginate(TableName=TableName, **kwargs):
        yield from page["Items"]
