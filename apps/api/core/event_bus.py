"""Event bus using Amazon SQS FIFO with idempotent processing via Redis."""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional

import structlog

logger = structlog.get_logger()


class EventType(str, Enum):
    AGENT_ACTION_PROPOSED = "agent_action_proposed"
    AGENT_ACTION_APPROVED = "agent_action_approved"
    AGENT_ACTION_REJECTED = "agent_action_rejected"
    AGENT_ACTION_EXECUTING = "agent_action_executing"
    AGENT_ACTION_COMPLETED = "agent_action_completed"
    AGENT_ACTION_FAILED = "agent_action_failed"
    NOTIFICATION_CREATED = "notification_created"
    SP_API_SYNC_REQUESTED = "sp_api_sync_requested"
    PRICE_CHANGE_DETECTED = "price_change_detected"


@dataclass
class Event:
    type: EventType
    tenant_id: uuid.UUID
    payload: dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    dedup_id: Optional[str] = None

    def to_json(self) -> str:
        return json.dumps({
            "event_id": self.event_id,
            "type": self.type.value,
            "tenant_id": str(self.tenant_id),
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
            "dedup_id": self.dedup_id,
        })

    @classmethod
    def from_json(cls, data: str) -> "Event":
        d = json.loads(data)
        return cls(
            event_id=d["event_id"],
            type=EventType(d["type"]),
            tenant_id=uuid.UUID(d["tenant_id"]),
            payload=d["payload"],
            timestamp=datetime.fromisoformat(d["timestamp"]),
            dedup_id=d.get("dedup_id"),
        )


class EventBus:
    """SQS FIFO event bus with Redis-based idempotent processing."""

    def __init__(self, sqs_client, queue_url: str, dlq_url: str, redis_client=None):
        self._sqs = sqs_client
        self.queue_url = queue_url
        self.dlq_url = dlq_url
        self._redis = redis_client
        self._handlers: dict[EventType, list[Callable]] = {}

    def subscribe(self, event_type: EventType, handler: Callable) -> None:
        """Register an async handler for an event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    async def publish(self, event: Event) -> str:
        """Publish an event to the SQS FIFO queue. Returns the SQS MessageId."""
        dedup_id = event.dedup_id or event.event_id
        response = await self._sqs.send_message(
            QueueUrl=self.queue_url,
            MessageBody=event.to_json(),
            MessageGroupId=str(event.tenant_id),
            MessageDeduplicationId=dedup_id,
        )
        message_id = response["MessageId"]
        logger.info("event_published", event_type=event.type.value,
                     tenant_id=str(event.tenant_id), message_id=message_id)
        return message_id

    async def process_one(self, override_handler: Callable | None = None) -> bool:
        """Receive and process one message from the queue.

        Returns True if a message was processed, False if queue was empty.
        """
        response = await self._sqs.receive_message(
            QueueUrl=self.queue_url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=1,
            AttributeNames=["All"],
        )
        messages = response.get("Messages", [])
        if not messages:
            return False

        msg = messages[0]
        receipt_handle = msg["ReceiptHandle"]
        event = Event.from_json(msg["Body"])

        # Idempotency check via Redis
        if self._redis:
            idempotency_key = f"event:processed:{event.event_id}"
            was_set = await self._redis.set(idempotency_key, "1", nx=True, ex=86400)
            if not was_set:
                # Already processed — delete and skip
                await self._sqs.delete_message(
                    QueueUrl=self.queue_url, ReceiptHandle=receipt_handle
                )
                logger.info("event_deduplicated", event_id=event.event_id)
                return True

        try:
            if override_handler:
                await override_handler(event)
            else:
                handlers = self._handlers.get(event.type, [])
                for handler in handlers:
                    await handler(event)

            # Success — delete from queue
            await self._sqs.delete_message(
                QueueUrl=self.queue_url, ReceiptHandle=receipt_handle
            )
            logger.info("event_processed", event_type=event.type.value,
                         event_id=event.event_id)
            return True
        except Exception as exc:
            # Don't delete — let SQS retry / move to DLQ
            logger.error("event_processing_failed", event_id=event.event_id,
                          error=str(exc))
            raise
