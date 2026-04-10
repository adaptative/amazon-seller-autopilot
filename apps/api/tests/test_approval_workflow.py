"""Approval Workflow Engine tests — 13 test cases covering state machine,
auto-approval, bulk operations, and expiration."""

import json
import os
import sys
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy import NullPool, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.event_bus import EventBus, EventType
from services.workflow_engine import InvalidTransitionError, WorkflowEngine

# ── Test Configuration ────────────────────────────────────────────

ADMIN_DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://seller_autopilot:localdev@localhost:5432/seller_autopilot",
)
APP_DB_URL = os.getenv(
    "APP_DATABASE_URL",
    "postgresql+asyncpg://app_user:app_user_pass@localhost:5432/seller_autopilot",
)

TENANT_A_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
USER_A_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")


class _FakeTenant:
    def __init__(self, tid):
        self.id = tid


# ── Fixtures ──────────────────────────────────────────────────────

@pytest.fixture
def tenant_a():
    return _FakeTenant(TENANT_A_ID)


@pytest_asyncio.fixture
async def db_session():
    """Provide a DB session with seeded tenant data."""
    admin_engine = create_async_engine(ADMIN_DB_URL, poolclass=NullPool)
    app_engine = create_async_engine(APP_DB_URL, poolclass=NullPool)

    try:
        async with admin_engine.begin() as conn:
            for table in ["approval_queue", "agent_actions", "notification_log",
                          "amazon_connections", "users"]:
                await conn.execute(
                    text(f"DELETE FROM {table} WHERE tenant_id = :tid"),
                    {"tid": str(TENANT_A_ID)},
                )
            await conn.execute(text("DELETE FROM audit_log WHERE tenant_id = :tid"),
                               {"tid": str(TENANT_A_ID)})
            await conn.execute(text("DELETE FROM tenants WHERE id = :tid"),
                               {"tid": str(TENANT_A_ID)})

            await conn.execute(text(
                "INSERT INTO tenants (id, name, slug, subscription_tier, status) "
                "VALUES (:id, 'Tenant A', 'tenant-a', 'starter', 'active')"),
                {"id": str(TENANT_A_ID)})
            await conn.execute(text(
                "INSERT INTO users (id, tenant_id, email, name, role, password_hash) "
                "VALUES (:id, :tid, 'alice@test.com', 'Alice', 'owner', '$2b$12$hash')"),
                {"id": str(USER_A_ID), "tid": str(TENANT_A_ID)})
            await conn.execute(text("DELETE FROM audit_log WHERE tenant_id = :tid"),
                               {"tid": str(TENANT_A_ID)})

        # Pin session to a single connection so set_config persists across commits
        async with app_engine.connect() as connection:
            await connection.execute(text("SELECT set_config('app.current_tenant', :tid, false)"),
                                     {"tid": str(TENANT_A_ID)})
            async with AsyncSession(bind=connection, expire_on_commit=False) as session:
                yield session

    finally:
        try:
            async with admin_engine.begin() as conn:
                for table in ["approval_queue", "agent_actions", "notification_log",
                              "amazon_connections", "users"]:
                    await conn.execute(
                        text(f"DELETE FROM {table} WHERE tenant_id = :tid"),
                        {"tid": str(TENANT_A_ID)},
                    )
                await conn.execute(text("DELETE FROM audit_log WHERE tenant_id = :tid"),
                                   {"tid": str(TENANT_A_ID)})
                await conn.execute(text("DELETE FROM tenants WHERE id = :tid"),
                                   {"tid": str(TENANT_A_ID)})
        finally:
            await admin_engine.dispose()
            await app_engine.dispose()


@pytest_asyncio.fixture
async def workflow_engine(db_session):
    """WorkflowEngine with real DB session."""
    mock_agent = MagicMock()
    mock_agent.execute = AsyncMock(return_value={"success": True, "sp_api_response": {}})
    return WorkflowEngine(
        db_session=db_session,
        agent_registry={"listing": mock_agent, "pricing": mock_agent},
    )


@pytest_asyncio.fixture
async def proposed_action(db_session, tenant_a):
    """Create a proposed agent_action and return its data."""
    action_id = str(uuid.uuid4())
    await db_session.execute(
        text(
            "INSERT INTO agent_actions "
            "(id, tenant_id, agent_type, action_type, target_asin, status, "
            "proposed_change, reasoning, confidence_score) "
            "VALUES (:id, :tid, 'listing', 'listing_optimize', 'B08XYZ', 'proposed', "
            ":change, 'Test reasoning', 0.88)"
        ),
        {
            "id": action_id,
            "tid": str(tenant_a.id),
            "change": json.dumps({"title": "Optimized title"}),
        },
    )
    await db_session.commit()

    class _Action:
        def __init__(self, aid):
            self.id = aid
    return _Action(action_id)


@pytest.fixture
def mock_listing_agent(workflow_engine):
    return workflow_engine.agents["listing"]


@pytest.fixture
def event_bus():
    bus = MagicMock(spec=EventBus)
    bus._subscribers: dict = {}
    bus.publish = AsyncMock()

    def subscribe(event_type, handler):
        key = event_type if isinstance(event_type, str) else event_type.value
        bus._subscribers.setdefault(key, []).append(handler)
    bus.subscribe = subscribe
    return bus


# ═══════════════════════════════════════════════════════════════════
#  TEST GROUP 1: Approval State Machine (8 tests)
# ═══════════════════════════════════════════════════════════════════

class TestApprovalStateMachine:

    @pytest.mark.asyncio
    async def test_approve_transitions_to_executing(self, workflow_engine, proposed_action, db_session, tenant_a):
        """Approving a proposed action should transition to executing."""
        result = await workflow_engine.approve(proposed_action.id, approved_by=USER_A_ID)
        # With agent registered, it goes to completed
        assert result["status"] in ("executing", "completed")

        await db_session.execute(text("SELECT set_config('app.current_tenant', :tid, false)"),
                                 {"tid": str(tenant_a.id)})
        row = await db_session.execute(
            text("SELECT status, approved_at, approved_by FROM agent_actions WHERE id = :id"),
            {"id": proposed_action.id},
        )
        action = row.fetchone()
        assert action.status in ("executing", "completed")
        assert action.approved_at is not None

    @pytest.mark.asyncio
    async def test_reject_transitions_to_rejected(self, workflow_engine, proposed_action):
        result = await workflow_engine.reject(proposed_action.id, reason="Too aggressive")
        assert result["status"] == "rejected"

    @pytest.mark.asyncio
    async def test_cannot_approve_already_rejected(self, workflow_engine, proposed_action):
        await workflow_engine.reject(proposed_action.id, reason="No")
        with pytest.raises(InvalidTransitionError, match="Invalid transition"):
            await workflow_engine.approve(proposed_action.id, approved_by=USER_A_ID)

    @pytest.mark.asyncio
    async def test_cannot_reject_already_approved(self, workflow_engine, proposed_action):
        await workflow_engine.approve(proposed_action.id, approved_by=USER_A_ID)
        with pytest.raises(InvalidTransitionError, match="Invalid transition"):
            await workflow_engine.reject(proposed_action.id, reason="Too late")

    @pytest.mark.asyncio
    async def test_execution_publishes_event(self, proposed_action, db_session, event_bus):
        engine = WorkflowEngine(db_session=db_session, event_bus=event_bus)
        await engine.approve(proposed_action.id, approved_by=USER_A_ID)
        event_bus.publish.assert_called_once()
        call_args = event_bus.publish.call_args[0][0]
        assert call_args.type == EventType.AGENT_ACTION_APPROVED

    @pytest.mark.asyncio
    async def test_execution_calls_agent_execute(self, workflow_engine, proposed_action, mock_listing_agent):
        await workflow_engine.approve(proposed_action.id, approved_by=USER_A_ID)
        mock_listing_agent.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_execution_success_transitions_to_completed(self, workflow_engine, proposed_action, mock_listing_agent):
        mock_listing_agent.execute.return_value = {"success": True, "sp_api_response": {}}
        result = await workflow_engine.approve(proposed_action.id, approved_by=USER_A_ID)
        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_execution_failure_transitions_to_failed(self, workflow_engine, proposed_action, mock_listing_agent):
        mock_listing_agent.execute.side_effect = Exception("SP-API error")
        result = await workflow_engine.approve(proposed_action.id, approved_by=USER_A_ID)
        assert result["status"] == "failed"
        assert "SP-API error" in result["error"]


# ═══════════════════════════════════════════════════════════════════
#  TEST GROUP 2: Auto-Approval (2 tests)
# ═══════════════════════════════════════════════════════════════════

class TestAutoApproval:

    @pytest.mark.asyncio
    async def test_auto_approves_high_confidence_actions(self, workflow_engine, db_session, tenant_a):
        """Actions with confidence >= 0.95 and auto_approve_eligible should auto-approve."""
        action_id = await workflow_engine.create_proposal(
            tenant_id=tenant_a.id, agent_type="pricing",
            action_type="price_match", proposed_change={"new_price": 24.99},
            confidence=0.97, auto_approve_eligible=True,
        )
        await db_session.execute(text("SELECT set_config('app.current_tenant', :tid, false)"),
                                 {"tid": str(tenant_a.id)})
        result = await db_session.execute(
            text("SELECT status FROM agent_actions WHERE id = :id"),
            {"id": action_id},
        )
        assert result.fetchone().status in ("executing", "completed")

    @pytest.mark.asyncio
    async def test_does_not_auto_approve_low_confidence(self, workflow_engine, db_session, tenant_a):
        """Actions with confidence < 0.95 should remain proposed."""
        action_id = await workflow_engine.create_proposal(
            tenant_id=tenant_a.id, agent_type="pricing",
            action_type="price_match", proposed_change={"new_price": 24.99},
            confidence=0.80, auto_approve_eligible=True,
        )
        await db_session.execute(text("SELECT set_config('app.current_tenant', :tid, false)"),
                                 {"tid": str(tenant_a.id)})
        result = await db_session.execute(
            text("SELECT status FROM agent_actions WHERE id = :id"),
            {"id": action_id},
        )
        assert result.fetchone().status == "proposed"


# ═══════════════════════════════════════════════════════════════════
#  TEST GROUP 3: Bulk Operations (2 tests)
# ═══════════════════════════════════════════════════════════════════

class TestBulkOperations:

    @pytest.mark.asyncio
    async def test_bulk_approve_by_confidence_threshold(self, workflow_engine, tenant_a, db_session):
        for conf in [0.92, 0.87, 0.74]:
            await workflow_engine.create_proposal(
                tenant_id=tenant_a.id, agent_type="pricing",
                action_type="reprice", proposed_change={}, confidence=conf,
            )
        result = await workflow_engine.bulk_approve(
            tenant_id=tenant_a.id, min_confidence=0.85, approved_by=USER_A_ID,
        )
        assert result["approved_count"] == 2  # 0.92 and 0.87

    @pytest.mark.asyncio
    async def test_list_pending_returns_only_proposed(self, workflow_engine, tenant_a):
        await workflow_engine.create_proposal(
            tenant_id=tenant_a.id, agent_type="pricing",
            action_type="reprice", proposed_change={}, confidence=0.85,
        )
        pending = await workflow_engine.list_pending(tenant_id=tenant_a.id)
        assert all(a["status"] == "proposed" for a in pending)


# ═══════════════════════════════════════════════════════════════════
#  TEST GROUP 4: Expiration (1 test)
# ═══════════════════════════════════════════════════════════════════

class TestExpiration:

    @pytest.mark.asyncio
    async def test_expired_actions_auto_reject(self, workflow_engine, db_session, tenant_a):
        """Actions past their expires_at should be auto-rejected."""
        action_id = await workflow_engine.create_proposal(
            tenant_id=tenant_a.id, agent_type="pricing",
            action_type="reprice", proposed_change={}, confidence=0.85,
            expires_in_minutes=0,  # Already expired
        )
        await workflow_engine.cleanup_expired()
        await db_session.execute(text("SELECT set_config('app.current_tenant', :tid, false)"),
                                 {"tid": str(tenant_a.id)})
        result = await db_session.execute(
            text("SELECT status FROM agent_actions WHERE id = :id"),
            {"id": action_id},
        )
        assert result.fetchone().status == "rejected"
