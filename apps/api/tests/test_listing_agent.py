"""Listing Agent tests — 16 test cases covering generation, optimization,
constraint validation, and database proposal creation."""

import json
import os
import sys
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import NullPool, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.listing_agent import (
    MAX_BULLET_LENGTH,
    MAX_DESCRIPTION_LENGTH,
    MAX_TITLE_LENGTH,
    ListingAgent,
)

# ── Test constants ──
ADMIN_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://seller_autopilot:localdev@localhost:5432/seller_autopilot",
)
APP_DATABASE_URL = os.getenv(
    "APP_DATABASE_URL",
    "postgresql+asyncpg://app_user:app_user_pass@localhost:5432/seller_autopilot",
)

if ADMIN_DATABASE_URL.startswith("postgresql://"):
    ADMIN_DATABASE_URL = ADMIN_DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
if APP_DATABASE_URL.startswith("postgresql://"):
    APP_DATABASE_URL = APP_DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

TENANT_A_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
USER_A_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
TEST_ASIN = "B0EXAMPLE01"
TEST_MARKETPLACE = "ATVPDKIKX0DER"


def _valid_listing() -> dict:
    """Return a valid listing dict that passes all constraints."""
    return {
        "title": "Premium Stainless Steel Water Bottle 32oz Insulated Double Wall Vacuum Flask",
        "bullet_points": [
            "DOUBLE WALL VACUUM INSULATION - Keeps drinks cold 24 hours or hot 12 hours",
            "PREMIUM 18/8 STAINLESS STEEL - BPA-free, no metallic taste, rust-resistant",
            "LEAK-PROOF LID DESIGN - Silicone seal prevents spills during travel and commute",
            "WIDE MOUTH OPENING - Easy to fill with ice cubes, easy to clean by hand",
            "ECO-FRIENDLY CHOICE - Reusable alternative to single-use plastic bottles",
        ],
        "description": (
            "Stay hydrated with our premium stainless steel water bottle. "
            "Engineered with double wall vacuum insulation technology to maintain "
            "your beverage temperature for hours. The 32oz capacity is perfect for "
            "all-day hydration at the office, gym, or outdoors."
        ),
        "search_terms": "hydration thermos gym workout camping hiking portable durable",
        "reasoning": "Focused on key product differentiators and common search queries.",
        "confidence_score": 0.92,
    }


def _mock_claude_response(listing: dict | None = None) -> MagicMock:
    """Create a mock Anthropic messages.create response."""
    if listing is None:
        listing = _valid_listing()
    mock_message = MagicMock()
    mock_message.content = [MagicMock()]
    mock_message.content[0].text = json.dumps(listing)
    return mock_message


def _product_data() -> dict:
    """Sample product data for generation tests."""
    return {
        "name": "Stainless Steel Water Bottle",
        "brand": "HydroElite",
        "category": "Sports & Outdoors > Water Bottles",
        "features": [
            "32oz capacity",
            "Double wall vacuum insulation",
            "18/8 stainless steel",
            "BPA-free",
            "Leak-proof lid",
        ],
        "price": 24.99,
    }


# ── Fixtures ──

@pytest.fixture
def agent():
    """Create a ListingAgent instance with a fake API key."""
    return ListingAgent(api_key="test-api-key")


@pytest_asyncio.fixture
async def db_session():
    """Provide a per-test database session with seeded data for agent_action tests."""
    admin_engine = create_async_engine(ADMIN_DATABASE_URL, poolclass=NullPool)
    app_engine = create_async_engine(APP_DATABASE_URL, poolclass=NullPool)

    try:
        async with admin_engine.begin() as conn:
            # Clean up (FK order)
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

            # Seed tenant and user
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

        async with AsyncSession(app_engine, expire_on_commit=False) as session:
            # Set tenant context for RLS
            await session.execute(
                text("SELECT set_config('app.current_tenant', :tid, false)"),
                {"tid": str(TENANT_A_ID)},
            )
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


# ═══════════════════════════════════════════════════════════════════════
#  TEST GROUP 1: Constraint Validation (5 tests)
# ═══════════════════════════════════════════════════════════════════════

class TestConstraintValidation:
    """Tests for the validate() method."""

    def test_valid_listing_passes(self, agent):
        """A well-formed listing should produce zero validation errors."""
        listing = _valid_listing()
        errors = agent.validate(listing)
        assert errors == []

    def test_title_exceeds_max_length(self, agent):
        """Title longer than 200 characters should fail validation."""
        listing = _valid_listing()
        listing["title"] = "A" * (MAX_TITLE_LENGTH + 1)
        errors = agent.validate(listing)
        assert any("Title exceeds" in e for e in errors)

    def test_wrong_bullet_count(self, agent):
        """Listing with != 5 bullet points should fail validation."""
        listing = _valid_listing()
        listing["bullet_points"] = listing["bullet_points"][:3]
        errors = agent.validate(listing)
        assert any("bullet points" in e.lower() for e in errors)

    def test_bullet_exceeds_max_length(self, agent):
        """A single bullet point over 500 characters should fail validation."""
        listing = _valid_listing()
        listing["bullet_points"][0] = "B" * (MAX_BULLET_LENGTH + 1)
        errors = agent.validate(listing)
        assert any("Bullet point 1 exceeds" in e for e in errors)

    def test_search_terms_exceeds_max_bytes(self, agent):
        """Search terms over 250 bytes (UTF-8) should fail validation."""
        listing = _valid_listing()
        # Use multi-byte characters to test byte counting vs char counting
        listing["search_terms"] = "\u00e9" * 200  # é is 2 bytes in UTF-8, so 400 bytes
        errors = agent.validate(listing)
        assert any("Search terms exceed" in e for e in errors)


# ═══════════════════════════════════════════════════════════════════════
#  TEST GROUP 2: Banned Content Detection (4 tests)
# ═══════════════════════════════════════════════════════════════════════

class TestBannedContentDetection:
    """Tests for banned language, HTML, phone numbers, and URLs."""

    def test_banned_promotional_language(self, agent):
        """Listing containing banned words like 'best' or 'discount' should fail."""
        listing = _valid_listing()
        listing["title"] = "Best Premium Water Bottle on Sale Now"
        errors = agent.validate(listing)
        banned_errors = [e for e in errors if "Banned promotional language" in e]
        assert len(banned_errors) >= 1

    def test_html_tags_detected(self, agent):
        """HTML tags in any field should be flagged."""
        listing = _valid_listing()
        listing["description"] = "Great product <b>buy now</b> for hydration"
        errors = agent.validate(listing)
        assert any("HTML tags" in e for e in errors)

    def test_phone_number_detected(self, agent):
        """Phone numbers in listing content should be flagged."""
        listing = _valid_listing()
        listing["bullet_points"][2] = "Call us at +1-800-555-1234 for support"
        errors = agent.validate(listing)
        assert any("Phone number" in e for e in errors)

    def test_url_detected(self, agent):
        """URLs in listing content should be flagged."""
        listing = _valid_listing()
        listing["description"] = "Visit https://example.com for more info"
        errors = agent.validate(listing)
        assert any("URL detected" in e for e in errors)


# ═══════════════════════════════════════════════════════════════════════
#  TEST GROUP 3: Listing Generation (4 tests)
# ═══════════════════════════════════════════════════════════════════════

class TestListingGeneration:
    """Tests for the generate() method with mocked Claude API."""

    @pytest.mark.asyncio
    async def test_generate_returns_valid_listing(self, agent):
        """generate() should return a complete, valid listing structure."""
        with patch.object(agent.client.messages, "create", return_value=_mock_claude_response()):
            result = await agent.generate(
                asin=TEST_ASIN,
                product_data=_product_data(),
                marketplace_id=TEST_MARKETPLACE,
            )
        assert result["is_valid"] is True
        assert result["asin"] == TEST_ASIN
        assert len(result["listing"]["bullet_points"]) == 5
        assert result["confidence_score"] > 0

    @pytest.mark.asyncio
    async def test_generate_includes_reasoning(self, agent):
        """generate() should include reasoning from Claude's response."""
        with patch.object(agent.client.messages, "create", return_value=_mock_claude_response()):
            result = await agent.generate(
                asin=TEST_ASIN,
                product_data=_product_data(),
                marketplace_id=TEST_MARKETPLACE,
            )
        assert result["reasoning"] != ""
        assert isinstance(result["reasoning"], str)

    @pytest.mark.asyncio
    async def test_generate_auto_fix_on_violation(self, agent):
        """generate() should retry with constraint feedback when violations are detected."""
        # First response has a violation (title too long), second is valid
        bad_listing = _valid_listing()
        bad_listing["title"] = "A" * 250
        good_listing = _valid_listing()

        mock_create = MagicMock(
            side_effect=[_mock_claude_response(bad_listing), _mock_claude_response(good_listing)]
        )
        with patch.object(agent.client.messages, "create", mock_create):
            result = await agent.generate(
                asin=TEST_ASIN,
                product_data=_product_data(),
                marketplace_id=TEST_MARKETPLACE,
            )
        assert result["is_valid"] is True
        assert mock_create.call_count == 2

    @pytest.mark.asyncio
    async def test_generate_returns_errors_after_max_retries(self, agent):
        """generate() should return errors if violations persist after max retries."""
        bad_listing = _valid_listing()
        bad_listing["title"] = "A" * 250  # Always too long

        with patch.object(
            agent.client.messages, "create", return_value=_mock_claude_response(bad_listing)
        ):
            result = await agent.generate(
                asin=TEST_ASIN,
                product_data=_product_data(),
                marketplace_id=TEST_MARKETPLACE,
            )
        assert result["is_valid"] is False
        assert len(result["validation_errors"]) > 0


# ═══════════════════════════════════════════════════════════════════════
#  TEST GROUP 4: Listing Optimization (3 tests)
# ═══════════════════════════════════════════════════════════════════════

class TestListingOptimization:
    """Tests for the optimize() method with mocked Claude API."""

    @pytest.mark.asyncio
    async def test_optimize_returns_diff(self, agent):
        """optimize() should return a diff showing changes from original."""
        existing = _valid_listing()
        optimized = _valid_listing()
        optimized["title"] = "Ultra Premium Stainless Steel Water Bottle 32oz Vacuum Insulated Flask"

        with patch.object(
            agent.client.messages, "create", return_value=_mock_claude_response(optimized)
        ):
            result = await agent.optimize(
                asin=TEST_ASIN,
                existing_listing=existing,
                marketplace_id=TEST_MARKETPLACE,
            )
        assert "diff" in result
        assert "title" in result["diff"]
        assert result["diff"]["title"]["old"] == existing["title"]
        assert result["diff"]["title"]["new"] == optimized["title"]

    @pytest.mark.asyncio
    async def test_optimize_preserves_keywords(self, agent):
        """optimize() should track which keywords were requested to be preserved."""
        keywords = ["insulated", "stainless steel", "BPA-free"]
        with patch.object(
            agent.client.messages, "create", return_value=_mock_claude_response()
        ):
            result = await agent.optimize(
                asin=TEST_ASIN,
                existing_listing=_valid_listing(),
                marketplace_id=TEST_MARKETPLACE,
                keywords_to_preserve=keywords,
            )
        assert result["preserved_keywords"] == keywords

    @pytest.mark.asyncio
    async def test_optimize_returns_confidence_score(self, agent):
        """optimize() should return a confidence score between 0 and 1."""
        with patch.object(
            agent.client.messages, "create", return_value=_mock_claude_response()
        ):
            result = await agent.optimize(
                asin=TEST_ASIN,
                existing_listing=_valid_listing(),
                marketplace_id=TEST_MARKETPLACE,
            )
        assert 0.0 <= result["confidence_score"] <= 1.0


# ═══════════════════════════════════════════════════════════════════════
#  TEST GROUP 5: Database Proposal Creation (2 tests — requires DB)
# ═══════════════════════════════════════════════════════════════════════

class TestProposalCreation:
    """Tests for agent_action record creation in the database."""

    @pytest.mark.asyncio
    async def test_generate_creates_proposed_action(self, agent, db_session):
        """generate() with session should create an agent_action with status='proposed'."""
        with patch.object(
            agent.client.messages, "create", return_value=_mock_claude_response()
        ):
            await agent.generate(
                asin=TEST_ASIN,
                product_data=_product_data(),
                marketplace_id=TEST_MARKETPLACE,
                session=db_session,
                tenant_id=str(TENANT_A_ID),
            )

        # Verify agent_action was created
        row = await db_session.execute(
            text(
                "SELECT agent_type, action_type, target_asin, status, confidence_score "
                "FROM agent_actions WHERE tenant_id = :tid AND target_asin = :asin"
            ),
            {"tid": str(TENANT_A_ID), "asin": TEST_ASIN},
        )
        action = row.fetchone()
        assert action is not None
        assert action[0] == "listing"
        assert action[1] == "listing_generate"
        assert action[2] == TEST_ASIN
        assert action[3] == "proposed"
        assert action[4] is not None and action[4] > 0

    @pytest.mark.asyncio
    async def test_optimize_creates_proposed_action(self, agent, db_session):
        """optimize() with session should create an agent_action with status='proposed'."""
        with patch.object(
            agent.client.messages, "create", return_value=_mock_claude_response()
        ):
            await agent.optimize(
                asin=TEST_ASIN,
                existing_listing=_valid_listing(),
                marketplace_id=TEST_MARKETPLACE,
                session=db_session,
                tenant_id=str(TENANT_A_ID),
            )

        # Verify agent_action was created
        row = await db_session.execute(
            text(
                "SELECT agent_type, action_type, target_asin, status "
                "FROM agent_actions WHERE tenant_id = :tid AND action_type = :atype"
            ),
            {"tid": str(TENANT_A_ID), "atype": "listing_optimize"},
        )
        action = row.fetchone()
        assert action is not None
        assert action[0] == "listing"
        assert action[3] == "proposed"


# ═══════════════════════════════════════════════════════════════════════
#  TEST GROUP 6: Duplicate Keyword Detection (1 test)
# ═══════════════════════════════════════════════════════════════════════

class TestDuplicateKeywords:
    """Tests for duplicate keyword detection between search terms and visible fields."""

    def test_duplicate_keywords_in_search_terms(self, agent):
        """Search terms containing words already in title/bullets should be flagged."""
        listing = _valid_listing()
        # "insulated" appears in bullet_points[0] and "premium" in title
        listing["search_terms"] = "insulated premium water container flask"
        errors = agent.validate(listing)
        assert any("Duplicate keywords" in e for e in errors)
        # Verify specific duplicates are mentioned
        dup_error = [e for e in errors if "Duplicate keywords" in e][0]
        assert "insulated" in dup_error or "premium" in dup_error


# ═══════════════════════════════════════════════════════════════════════
#  TEST GROUP 7: Description Constraint (1 test)
# ═══════════════════════════════════════════════════════════════════════

class TestDescriptionConstraint:
    """Tests for description length validation."""

    def test_description_exceeds_max_length(self, agent):
        """Description longer than 2000 characters should fail validation."""
        listing = _valid_listing()
        listing["description"] = "D" * (MAX_DESCRIPTION_LENGTH + 1)
        errors = agent.validate(listing)
        assert any("Description exceeds" in e for e in errors)
