"""Setup SQS FIFO queues for the event bus (works with LocalStack and real AWS)."""

import json
import os

import structlog

logger = structlog.get_logger()

QUEUE_NAME = "seller-autopilot-events.fifo"
DLQ_NAME = "seller-autopilot-events-dlq.fifo"
AWS_ENDPOINT_URL = os.getenv("AWS_ENDPOINT_URL", "http://localhost:4566")
AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")


async def setup_queues(sqs_client) -> tuple[str, str]:
    """Create the FIFO event queue and its DLQ. Returns (queue_url, dlq_url)."""

    # Create DLQ first
    try:
        dlq_response = await sqs_client.create_queue(
            QueueName=DLQ_NAME,
            Attributes={
                "FifoQueue": "true",
                "ContentBasedDeduplication": "false",
            },
        )
        dlq_url = dlq_response["QueueUrl"]
    except sqs_client.exceptions.QueueNameExists:
        dlq_response = await sqs_client.get_queue_url(QueueName=DLQ_NAME)
        dlq_url = dlq_response["QueueUrl"]

    # Get DLQ ARN
    dlq_attrs = await sqs_client.get_queue_attributes(
        QueueUrl=dlq_url, AttributeNames=["QueueArn"]
    )
    dlq_arn = dlq_attrs["Attributes"]["QueueArn"]

    # Create main FIFO queue with redrive policy
    redrive_policy = json.dumps({
        "deadLetterTargetArn": dlq_arn,
        "maxReceiveCount": "3",
    })

    try:
        queue_response = await sqs_client.create_queue(
            QueueName=QUEUE_NAME,
            Attributes={
                "FifoQueue": "true",
                "ContentBasedDeduplication": "false",
                "RedrivePolicy": redrive_policy,
                "VisibilityTimeout": "30",
            },
        )
        queue_url = queue_response["QueueUrl"]
    except sqs_client.exceptions.QueueNameExists:
        queue_response = await sqs_client.get_queue_url(QueueName=QUEUE_NAME)
        queue_url = queue_response["QueueUrl"]

    logger.info("sqs_queues_ready", queue_url=queue_url, dlq_url=dlq_url)
    return queue_url, dlq_url
