import boto3


class MySQSClient:
    def __init__(self, region_name="us-east-1"):
        self.client = boto3.client("sqs", region_name=region_name)

    def get_queue_url(self, queue_name):
        response = self.client.create_queue(QueueName=queue_name)
        return response["QueueUrl"]

    def receive_message(self, queue_url):
        return self.client.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=1,
        )
