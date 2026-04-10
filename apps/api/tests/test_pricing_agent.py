"""Pricing Agent tests — 11 test cases covering price calculation, offer change
processing, Buy Box tracking, and price history."""

import os
import sys
import uuid
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
import redis.asyncio as aioredis
from sqlalchemy import NullPool, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.pricing_agent import PricingAgent
from core.event_bus import EventBus, EventType

# ── Test Configuration ────────────────────────────────────────────

ADMIN_DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://seller_autopilot:localdev@localhost:5432/seller_autopilot",
)
APP_DB_URL = os.getenv(
    "APP_DATABASE_URL",
    "postgresql+asyncpg://app_user:app_user_pass@localhost:5432/seller_autopilot",
)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

TENANT_A_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
USER_A_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")


# ── Fixtures ──────────────────────────────────────────────────────

@pytest.fixture
def pricing_agent():
    """Create a PricingAgent with no DB/Redis for pure calculation tests."""
    return PricingAgent(
        tenant_id=str(TENANT_A_ID),
        min_margin=Decimal("0.15"),
    )


@pytest.fixture
def mock_sp_api():
    """Mock SP-API connector."""
    mock = AsyncMock()
    mock.get_pricing = AsyncMock(return_value={"price": 24.99})
    return mock


@pytest_asyncio.fixture
async def redis_client():
    """Provide a real Redis client for tracking tests."""
    r = aioredis.from_url(REDIS_URL)
    yield r
    # Clean up test keys
    async for key in r.scan_iter(f"buybox:{TENANT_A_ID}:*"):
        await r.delete(key)
    async for key in r.scan_iter(f"price_history:{TENANT_A_ID}:*"):
        await r.delete(key)
    await r.aclose()


@pytest_asyncio.fixture
async def db_session():
    """Provide a DB session for proposal creation tests."""
    admin_engine = create_async_engine(ADMIN_DB_URL, poolclass=NullPool)
    app_engine = create_async_engine(APP_DB_URL, poolclass=NullPool)

    try:
        async with admin_engine.begin() as conn:
            # Clean up
            for table in ["approval_queue", "agent_actions", "notification_log",
                          "amazon_connections", "users"]:
                await conn.execute(
                    text(f"DELETE FROM {table} WHERE tenant_id = :tid"),
                    {"tid": str(TENANT_A_ID)},
                )
            await conn.execute(
                text("DELETE FROM audit_log WHERE tenant_id = :tid"),
                {"tid": str(TENANT_A_ID)},
            )
            await conn.execute(
                text("DELETE FROM tenants WHERE id = :tid"),
                {"tid": str(TENANT_A_ID)},
            )

            # Seed
            await conn.execute(text(
                "INSERT INTO tenants (id, name, slug, subscription_tier, status) "
                "VALUES (:id, 'Tenant A', 'tenant-a', 'starter', 'active')"),
                {"id": str(TENANT_A_ID)})
            await conn.execute(text(
                "INSERT INTO users (id, tenant_id, email, name, role, password_hash) "
                "VALUES (:id, :tid, 'alice@tenant-a.com', 'Alice', 'owner', '$2b$12$hash_a')"),
                {"id": str(USER_A_ID), "tid": str(TENANT_A_ID)})
            await conn.execute(
                text("DELETE FROM audit_log WHERE tenant_id = :tid"),
                {"tid": str(TENANT_A_ID)},
            )

        # Pin session to a single connection so set_config persists across commits
        async with app_engine.connect() as connection:
            await connection.execute(
                text("SELECT set_config('app.current_tenant', :tid, false)"),
                {"tid": str(TENANT_A_ID)},
            )
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
                await conn.execute(
                    text("DELETE FROM audit_log WHERE tenant_id = :tid"),
                    {"tid": str(TENANT_A_ID)},
                )
                await conn.execute(
                    text("DELETE FROM tenants WHERE id = :tid"),
                    {"tid": str(TENANT_A_ID)},
                )
        finally:
            await admin_engine.dispose()
            await app_engine.dispose()


class _FakeTenant:
    def __init__(self, tid):
        self.id = tid


@pytest.fixture
def tenant_a():
    return _FakeTenant(TENANT_A_ID)


@pytest.fixture
def event_bus():
    """Mock EventBus that collects published events."""
    bus = MagicMock(spec=EventBus)
    bus._subscribers: dict[str, list] = {}
    bus.publish = AsyncMock()

    def subscribe(event_type, handler):
        key = event_type if isinstance(event_type, str) else event_type.value
        bus._subscribers.setdefault(key, []).append(handler)

    bus.subscribe = subscribe
    return bus


# ═══════════════════════════════════════════════════════════════════
#  TEST GROUP 1: Price Calculation (5 tests)
# ═══════════════════════════════════════════════════════════════════

class TestPriceCalculation:

    @pytest.mark.asyncio
    async def test_calculates_optimal_price_to_win_buy_box(self, pricing_agent):
        """Given competitor prices, should suggest price that wins Buy Box."""
        competitor_offers = [
            {"price": 24.99, "shipping": 0, "is_buy_box": True, "seller_rating": 4.5},
            {"price": 26.50, "shipping": 3.99, "is_buy_box": False, "seller_rating": 4.2},
        ]
        our_cost = Decimal("12.00")
        result = await pricing_agent.calculate_optimal_price(
            asin="B08XYZ", competitor_offers=competitor_offers,
            our_cost=our_cost, current_price=Decimal("27.99")
        )
        # Should undercut Buy Box winner but maintain margin
        assert result["suggested_price"] <= 24.99
        assert result["suggested_price"] > float(our_cost * Decimal("1.15"))  # 15% min margin

    @pytest.mark.asyncio
    async def test_respects_minimum_margin(self, pricing_agent):
        """Should NEVER suggest price below minimum margin."""
        competitor_offers = [
            {"price": 13.50, "shipping": 0, "is_buy_box": True, "seller_rating": 4.8},
        ]
        our_cost = Decimal("12.00")
        result = await pricing_agent.calculate_optimal_price(
            asin="B08XYZ", competitor_offers=competitor_offers,
            our_cost=our_cost, current_price=Decimal("15.99")
        )
        min_price = float(our_cost * Decimal("1.15"))  # $13.80
        assert result["suggested_price"] >= min_price

    @pytest.mark.asyncio
    async def test_does_not_change_if_already_winning_buy_box(self, pricing_agent):
        """If we already own Buy Box, should suggest no change."""
        competitor_offers = [
            {"price": 24.99, "shipping": 0, "is_buy_box": False, "seller_rating": 4.2},
        ]
        result = await pricing_agent.calculate_optimal_price(
            asin="B08XYZ", competitor_offers=competitor_offers,
            our_cost=Decimal("12.00"), current_price=Decimal("23.99"),
            we_own_buy_box=True
        )
        assert result["action"] == "hold"
        assert result["suggested_price"] == 23.99

    @pytest.mark.asyncio
    async def test_suggests_price_increase_when_no_competition(self, pricing_agent):
        """When no close competitors, should suggest gradual price increase."""
        competitor_offers = [
            {"price": 49.99, "shipping": 5.99, "is_buy_box": False, "seller_rating": 3.8},
        ]
        result = await pricing_agent.calculate_optimal_price(
            asin="B08XYZ", competitor_offers=competitor_offers,
            our_cost=Decimal("12.00"), current_price=Decimal("24.99"),
            we_own_buy_box=True
        )
        assert result["action"] == "increase"
        assert result["suggested_price"] > 24.99

    @pytest.mark.asyncio
    async def test_uses_configurable_margin_per_tenant(self, pricing_agent):
        """Different tenants can have different minimum margins."""
        pricing_agent.min_margin = Decimal("0.25")  # 25% margin
        competitor_offers = [
            {"price": 15.00, "shipping": 0, "is_buy_box": True},
        ]
        result = await pricing_agent.calculate_optimal_price(
            asin="B08XYZ", competitor_offers=competitor_offers,
            our_cost=Decimal("12.00"), current_price=Decimal("16.99")
        )
        assert result["suggested_price"] >= float(Decimal("12.00") * Decimal("1.25"))  # $15.00


# ═══════════════════════════════════════════════════════════════════
#  TEST GROUP 2: Offer Change Processing (3 tests)
# ═══════════════════════════════════════════════════════════════════

class TestOfferChangeProcessing:

    @pytest.mark.asyncio
    async def test_processes_any_offer_changed_notification(self, pricing_agent, mock_sp_api):
        """Should process SP-API ANY_OFFER_CHANGED and create price proposal."""
        pricing_agent.sp_api = mock_sp_api
        notification = {
            "NotificationType": "ANY_OFFER_CHANGED",
            "Payload": {
                "ASIN": "B08XYZ",
                "BuyBoxPrice": {"Amount": 24.99, "CurrencyCode": "USD"},
                "Offers": [
                    {"SellerId": "COMPETITOR1", "Price": 24.99, "IsBuyBoxWinner": True},
                    {"SellerId": "OUR_ID", "Price": 27.99, "IsBuyBoxWinner": False},
                ]
            }
        }
        result = await pricing_agent.process_offer_change(notification)
        assert result is not None
        assert "suggested_price" in result

    @pytest.mark.asyncio
    async def test_creates_proposal_in_agent_actions(self, mock_sp_api, db_session, tenant_a):
        """Processing should create agent_action with status proposed."""
        agent = PricingAgent(
            sp_api_connector=mock_sp_api,
            db_session=db_session,
            tenant_id=str(tenant_a.id),
            min_margin=Decimal("0.15"),
        )
        notification = {
            "NotificationType": "ANY_OFFER_CHANGED",
            "Payload": {
                "ASIN": "B08XYZ",
                "BuyBoxPrice": {"Amount": 24.99},
                "Offers": [
                    {"SellerId": "COMPETITOR1", "Price": 24.99, "IsBuyBoxWinner": True},
                    {"SellerId": "OUR_ID", "Price": 27.99, "IsBuyBoxWinner": False},
                ],
            }
        }
        await agent.process_offer_change(notification)

        result = await db_session.execute(text(
            "SELECT * FROM agent_actions WHERE agent_type = 'pricing' "
            "AND target_asin = 'B08XYZ' ORDER BY created_at DESC LIMIT 1"
        ))
        action = result.fetchone()
        assert action is not None
        assert action.status == "proposed"
        assert action.agent_type == "pricing"

    @pytest.mark.asyncio
    async def test_publishes_event_on_proposal(self, mock_sp_api, event_bus):
        """Should publish AGENT_ACTION_PROPOSED event."""
        agent = PricingAgent(
            sp_api_connector=mock_sp_api,
            tenant_id=str(TENANT_A_ID),
            event_bus=event_bus,
            min_margin=Decimal("0.15"),
        )
        notification = {
            "NotificationType": "ANY_OFFER_CHANGED",
            "Payload": {
                "ASIN": "B08XYZ",
                "BuyBoxPrice": {"Amount": 24.99},
                "Offers": [
                    {"SellerId": "COMPETITOR1", "Price": 24.99, "IsBuyBoxWinner": True},
                    {"SellerId": "OUR_ID", "Price": 27.99, "IsBuyBoxWinner": False},
                ],
            }
        }
        await agent.process_offer_change(notification)
        event_bus.publish.assert_called_once()
        call_args = event_bus.publish.call_args[0][0]
        assert call_args.type == EventType.AGENT_ACTION_PROPOSED
        assert call_args.payload["agent_type"] == "pricing"


# ═══════════════════════════════════════════════════════════════════
#  TEST GROUP 3: Buy Box Tracking (2 tests)
# ═══════════════════════════════════════════════════════════════════

class TestBuyBoxTracking:

    @pytest.mark.asyncio
    async def test_tracks_buy_box_win_rate(self, redis_client):
        """Should maintain rolling Buy Box win rate in Redis."""
        agent = PricingAgent(
            tenant_id=str(TENANT_A_ID),
            redis_client=redis_client,
        )
        await agent.record_buy_box_check("B08XYZ", won=True)
        await agent.record_buy_box_check("B08XYZ", won=True)
        await agent.record_buy_box_check("B08XYZ", won=False)

        rate = await agent.get_buy_box_win_rate("B08XYZ")
        assert abs(rate - 66.67) < 1  # ~66.67%

    @pytest.mark.asyncio
    async def test_tracks_price_history(self, redis_client):
        """Should store price changes for charting."""
        agent = PricingAgent(
            tenant_id=str(TENANT_A_ID),
            redis_client=redis_client,
        )
        await agent.record_price_change("B08XYZ", Decimal("24.99"), Decimal("23.49"))
        await agent.record_price_change("B08XYZ", Decimal("23.49"), Decimal("22.99"))

        history = await agent.get_price_history("B08XYZ", limit=10)
        assert len(history) == 2
        assert history[0]["old_price"] == 23.49  # Most recent first (LPUSH)
        assert history[1]["old_price"] == 24.99
