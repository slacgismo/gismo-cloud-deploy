import pytest

from sqs import MySQSClient


@pytest.fixture
def queue_name():
    return "my-test-queue"


@pytest.fixture
def sqs_test(sqs_client, queue_name):
    sqs_client.create_queue(QueueName=queue_name)
    yield


def test_get_queue_url(sqs_client, sqs_test):
    sqs_client = MySQSClient()
    queue_url = sqs_client.get_queue_url(queue_name="my-test-queue")
    assert "my-test-queue" in queue_url


def test_receive_message(sqs_client, sqs_test):
    client = MySQSClient()
    queue_url = client.get_queue_url(queue_name="blah")

    sqs_client.send_message(
        QueueUrl=queue_url,
        MessageBody="derp"
    )

    response = client.receive_message(queue_url=queue_url)
    assert response["Messages"][0]["Body"] == "derp"
