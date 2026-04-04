"""
Event Bus & Notification Infrastructure tests — 9 test cases.
Uses LocalStack for SQS and real PostgreSQL + Redis.
"""

import json
import os
import sys
import uuid
from pathlib import Path

import pytest
import pytest_asyncio
import aioboto3
import redis.asyncio as aioredis
from sqlalchemy import NullPool, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.event_bus import Event, EventBus, EventType
from services.notification_service import NotificationService

AWS_ENDPOINT = os.getenv("AWS_ENDPOINT_URL", "http://localhost:4566")
AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
ADMIN_DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://seller_autopilot:localdev@localhost:5432/seller_autopilot",
)

TENANT_A_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
TENANT_B_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


@pytest_asyncio.fixture
async def sqs_client():
    session = aioboto3.Session()
    async with session.client(
        "sqs",
        endpoint_url=AWS_ENDPOINT,
        region_name=AWS_REGION,
        aws_access_key_id="test",
        aws_secret_access_key="test",
    ) as client:
        yield client


@pytest_asyncio.fixture
async def redis_client():
    r = aioredis.from_url(REDIS_URL)
    yield r
    await r.aclose()


@pytest_asyncio.fixture
async def event_bus(sqs_client, redis_client):
    """Create event bus with fresh queues per test."""
    # Use unique queue names per test to avoid interference
    suffix = uuid.uuid4().hex[:8]
    dlq_name = f"test-dlq-{suffix}.fifo"
    queue_name = f"test-events-{suffix}.fifo"

    # Create DLQ
    dlq_resp = await sqs_client.create_queue(
        QueueName=dlq_name,
        Attributes={"FifoQueue": "true", "ContentBasedDeduplication": "false"},
    )
    dlq_url = dlq_resp["QueueUrl"]

    # Get DLQ ARN
    dlq_attrs = await sqs_client.get_queue_attributes(
        QueueUrl=dlq_url, AttributeNames=["QueueArn"]
    )
    dlq_arn = dlq_attrs["Attributes"]["QueueArn"]

    # Create main queue with redrive
    import json as _json
    queue_resp = await sqs_client.create_queue(
        QueueName=queue_name,
        Attributes={
            "FifoQueue": "true",
            "ContentBasedDeduplication": "false",
            "RedrivePolicy": _json.dumps({
                "deadLetterTargetArn": dlq_arn,
                "maxReceiveCount": "3",
            }),
            "VisibilityTimeout": "0",  # Instant retry for tests
        },
    )
    queue_url = queue_resp["QueueUrl"]

    bus = EventBus(sqs_client, queue_url, dlq_url, redis_client)
    yield bus

    # Cleanup
    try:
        await sqs_client.delete_queue(QueueUrl=queue_url)
        await sqs_client.delete_queue(QueueUrl=dlq_url)
    except Exception:
        pass


@pytest_asyncio.fixture
async def dlq_url(event_bus):
    return event_bus.dlq_url


@pytest_asyncio.fixture
async def db_engine():
    eng = create_async_engine(ADMIN_DB_URL, poolclass=NullPool)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    async with AsyncSession(db_engine, expire_on_commit=False) as session:
        yield session


@pytest_asyncio.fixture
async def tenant_a(db_engine):
    """Ensure tenant A exists."""
    async with db_engine.begin() as conn:
        await conn.execute(text(
            "INSERT INTO tenants (id, name, slug, subscription_tier, status) "
            "VALUES (:id, 'Event Tenant A', 'event-tenant-a', 'starter', 'active') "
            "ON CONFLICT (id) DO NOTHING"),
            {"id": str(TENANT_A_ID)})

    class T:
        id = TENANT_A_ID
    yield T()

    async with db_engine.begin() as conn:
        await conn.execute(text("DELETE FROM notification_log WHERE tenant_id = :tid"),
                           {"tid": str(TENANT_A_ID)})
        await conn.execute(text("DELETE FROM audit_log WHERE tenant_id = :tid"),
                           {"tid": str(TENANT_A_ID)})


@pytest_asyncio.fixture
async def tenant_b(db_engine):
    """Ensure tenant B exists."""
    async with db_engine.begin() as conn:
        await conn.execute(text(
            "INSERT INTO tenants (id, name, slug, subscription_tier, status) "
            "VALUES (:id, 'Event Tenant B', 'event-tenant-b', 'growth', 'active') "
            "ON CONFLICT (id) DO NOTHING"),
            {"id": str(TENANT_B_ID)})

    class T:
        id = TENANT_B_ID
    yield T()

    async with db_engine.begin() as conn:
        await conn.execute(text("DELETE FROM notification_log WHERE tenant_id = :tid"),
                           {"tid": str(TENANT_B_ID)})
        await conn.execute(text("DELETE FROM audit_log WHERE tenant_id = :tid"),
                           {"tid": str(TENANT_B_ID)})


@pytest_asyncio.fixture
async def notification_service(db_engine, event_bus):
    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    return NotificationService(db_session_factory=factory, event_bus=event_bus)


# ── TestEventPublishing ───────────────────────────────────────────


class TestEventPublishing:

    @pytest.mark.asyncio
    async def test_publish_sends_to_sqs_fifo(self, event_bus, sqs_client):
        event = Event(
            type=EventType.AGENT_ACTION_PROPOSED,
            tenant_id=uuid.uuid4(),
            payload={"agent": "pricing", "action": "reduce_price", "asin": "B08XYZ"},
        )
        message_id = await event_bus.publish(event)
        assert message_id is not None

        response = await sqs_client.receive_message(
            QueueUrl=event_bus.queue_url, MaxNumberOfMessages=1, WaitTimeSeconds=5
        )
        messages = response.get("Messages", [])
        assert len(messages) == 1
        body = json.loads(messages[0]["Body"])
        assert body["type"] == "agent_action_proposed"
        assert body["payload"]["asin"] == "B08XYZ"

    @pytest.mark.asyncio
    async def test_fifo_deduplication(self, event_bus):
        event = Event(
            type=EventType.AGENT_ACTION_PROPOSED,
            tenant_id=uuid.uuid4(),
            payload={"action": "test"},
            dedup_id="dedup-123",
        )
        id1 = await event_bus.publish(event)
        id2 = await event_bus.publish(event)
        assert id1 == id2

    @pytest.mark.asyncio
    async def test_message_group_id_is_tenant_id(self, event_bus, sqs_client):
        tenant_id = uuid.uuid4()
        event = Event(
            type=EventType.AGENT_ACTION_PROPOSED,
            tenant_id=tenant_id,
            payload={"action": "test"},
        )
        await event_bus.publish(event)
        response = await sqs_client.receive_message(
            QueueUrl=event_bus.queue_url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=5,
            AttributeNames=["MessageGroupId"],
        )
        group_id = response["Messages"][0]["Attributes"]["MessageGroupId"]
        assert group_id == str(tenant_id)

    @pytest.mark.asyncio
    async def test_failed_messages_go_to_dlq(self, event_bus, sqs_client, dlq_url):
        # Use a bus without Redis to avoid idempotency blocking retries
        bus_no_redis = EventBus(sqs_client, event_bus.queue_url, dlq_url, redis_client=None)

        event = Event(
            type=EventType.AGENT_ACTION_PROPOSED,
            tenant_id=uuid.uuid4(),
            payload={"_poison": True},
        )
        await bus_no_redis.publish(event)

        async def failing_handler(e):
            raise ValueError("Poison message")

        # Process 4 times — after maxReceiveCount=3 SQS moves to DLQ
        for _ in range(4):
            try:
                await bus_no_redis.process_one(failing_handler)
            except Exception:
                pass

        import asyncio
        await asyncio.sleep(2)

        dlq_response = await sqs_client.receive_message(
            QueueUrl=dlq_url, MaxNumberOfMessages=1, WaitTimeSeconds=5
        )
        assert len(dlq_response.get("Messages", [])) >= 1


# ── TestEventSubscription ─────────────────────────────────────────


class TestEventSubscription:

    @pytest.mark.asyncio
    async def test_subscribe_handler_receives_events(self, event_bus):
        received = []

        async def handler(event):
            received.append(event)

        event_bus.subscribe(EventType.AGENT_ACTION_APPROVED, handler)

        event = Event(
            type=EventType.AGENT_ACTION_APPROVED,
            tenant_id=uuid.uuid4(),
            payload={"action_id": "act-123"},
        )
        await event_bus.publish(event)
        await event_bus.process_one()

        assert len(received) == 1
        assert received[0].payload["action_id"] == "act-123"

    @pytest.mark.asyncio
    async def test_handler_only_receives_subscribed_type(self, event_bus):
        received = []

        async def handler(event):
            received.append(event)

        event_bus.subscribe(EventType.AGENT_ACTION_APPROVED, handler)

        await event_bus.publish(Event(
            type=EventType.AGENT_ACTION_PROPOSED,
            tenant_id=uuid.uuid4(),
            payload={"wrong_type": True},
        ))
        await event_bus.process_one()

        assert len(received) == 0


# ── TestIdempotency ───────────────────────────────────────────────


class TestIdempotency:

    @pytest.mark.asyncio
    async def test_idempotent_processing(self, event_bus, redis_client):
        call_count = 0

        async def counting_handler(event):
            nonlocal call_count
            call_count += 1

        event_bus.subscribe(EventType.AGENT_ACTION_APPROVED, counting_handler)

        fixed_event_id = f"fixed-{uuid.uuid4().hex[:8]}"
        event = Event(
            type=EventType.AGENT_ACTION_APPROVED,
            tenant_id=uuid.uuid4(),
            payload={"action_id": "act-456"},
            event_id=fixed_event_id,
        )
        # Publish twice with different dedup IDs but same event_id
        event.dedup_id = f"dedup-a-{uuid.uuid4().hex[:8]}"
        await event_bus.publish(event)
        event.dedup_id = f"dedup-b-{uuid.uuid4().hex[:8]}"
        await event_bus.publish(event)

        await event_bus.process_one()
        await event_bus.process_one()

        assert call_count == 1


# ── TestNotificationService ───────────────────────────────────────


class TestNotificationService:

    @pytest.mark.asyncio
    async def test_creates_notification_in_db(self, notification_service, db_session, tenant_a):
        await notification_service.notify(
            tenant_id=tenant_a.id,
            type="agent_alert",
            title="Buy Box won!",
            body="Your pricing agent matched the competitor on B08XYZ",
            severity="success",
        )
        result = await db_session.execute(
            text("SELECT title, severity FROM notification_log WHERE tenant_id = :tid ORDER BY created_at DESC LIMIT 1"),
            {"tid": str(tenant_a.id)},
        )
        row = result.fetchone()
        assert row is not None
        assert row.title == "Buy Box won!"
        assert row.severity == "success"

    @pytest.mark.asyncio
    async def test_notification_respects_rls(self, notification_service, db_engine, tenant_a, tenant_b):
        await notification_service.notify(
            tenant_id=tenant_a.id, type="alert", title="A-only", body="", severity="info"
        )
        # Query as app_user (RLS enforced) for tenant B
        app_db_url = os.getenv(
            "APP_DATABASE_URL",
            "postgresql+asyncpg://app_user:app_user_pass@localhost:5432/seller_autopilot",
        )
        app_engine = create_async_engine(app_db_url, poolclass=NullPool)
        try:
            async with AsyncSession(app_engine) as session:
                await session.execute(
                    text("SELECT set_config('app.current_tenant', :tid, false)"),
                    {"tid": str(tenant_b.id)},
                )
                result = await session.execute(text("SELECT COUNT(*) FROM notification_log"))
                count = result.scalar()
                assert count == 0
        finally:
            await app_engine.dispose()
