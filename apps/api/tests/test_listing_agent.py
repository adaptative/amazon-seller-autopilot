"""Tests for the Listing Agent — AI content generation and optimization."""

import uuid
from collections import namedtuple
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import NullPool, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.listing_agent import ListingAgent

# ── Fixed IDs for deterministic testing ────────────────────────
TENANT_A_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
USER_A_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")

ADMIN_DATABASE_URL = "postgresql+asyncpg://seller_autopilot:localdev@localhost:5432/seller_autopilot"

# ── Mock Claude API Responses ──────────────────────────────────

MOCK_CLAUDE_RESPONSE_VALID = {
    "title": "Wireless Bluetooth Earbuds with Active Noise Cancelling, 30H Playtime, IPX5 Waterproof, Touch Controls, USB-C Fast Charging, Deep Bass, Bluetooth 5.3 Headphones for iPhone Android",
    "bullets": [
        "Premium Active Noise Cancellation Technology: Experience immersive sound with advanced ANC that reduces ambient noise by up to 35dB, letting you focus on your music, podcasts, or calls without distraction in any environment",
        "Extended 30-Hour Battery Life: Get up to 8 hours of playback per charge with an additional 22 hours from the compact charging case, keeping you powered through long commutes, workouts, and travel days",
        "IPX5 Waterproof and Sweat Resistant: Engineered to withstand intense workouts and rainy conditions, these earbuds feature a durable waterproof coating that protects internal components from moisture damage",
        "Intuitive Touch Controls and Seamless Connectivity: Tap to play, pause, skip tracks, adjust volume, and answer calls effortlessly with responsive touch sensors on each earbud, paired with Bluetooth 5.3 for stable connection",
        "Ergonomic Comfort Fit Design: Includes 3 sizes of soft silicone ear tips for a secure and comfortable fit that stays in place during running, gym sessions, and everyday activities without causing ear fatigue",
    ],
    "description": (
        "Elevate your audio experience with these premium wireless Bluetooth earbuds featuring cutting-edge "
        "Active Noise Cancellation technology. Designed for music lovers, commuters, and fitness enthusiasts, "
        "these earbuds deliver crystal-clear sound with deep, rich bass powered by 13mm dynamic drivers. "
        "The Bluetooth 5.3 chipset ensures a stable, low-latency connection within a 50-foot range, "
        "compatible with all smartphones, tablets, and laptops. With a total of 30 hours of battery life "
        "and USB-C fast charging that provides 2 hours of playback from just a 10-minute charge, you never "
        "have to worry about running out of power. The IPX5 waterproof rating protects against sweat and rain, "
        "making them your perfect workout companion. Three sizes of ultra-soft silicone ear tips ensure a "
        "personalized, secure fit for all-day comfort. Package includes: 1x Earbuds, 1x Charging Case, "
        "3x Ear Tips (S/M/L), 1x USB-C Cable, 1x User Manual."
    ),
    "search_terms": "wireless earbuds bluetooth headphones noise cancelling waterproof earphones gym running workout charging case",
    "reasoning": "Optimized title with primary keywords front-loaded for search visibility. Bullets structured to highlight key differentiators with specific metrics. Description provides comprehensive product details for conversion.",
    "confidence": 0.92,
}

MOCK_CLAUDE_RESPONSE_OPTIMIZED = {
    "title": "Wireless Earbuds Bluetooth 5.3, Active Noise Cancelling Headphones with 30H Battery, IPX5 Waterproof, Touch Controls, Deep Bass Earphones for iPhone Android",
    "bullets": [
        "Advanced Bluetooth 5.3 with Active Noise Cancelling: Upgraded chipset delivers faster pairing and stable connection up to 50ft while ANC blocks up to 35dB of ambient noise for uninterrupted listening anywhere",
        "All-Day 30H Battery with Fast Charging: Enjoy 8 hours per charge plus 22 hours from the case with USB-C fast charging providing 2 hours playback from a quick 10-minute charge when you need power in a hurry",
        "IPX5 Waterproof for Active Lifestyles: Sealed acoustic chambers and nano-coated circuits protect against sweat and rain during intense gym sessions, outdoor runs, and unexpected weather conditions",
        "Responsive Touch Controls and Clear Calls: Smart touch panels on each earbud let you manage music, calls, and voice assistants with simple taps while dual microphones with ENC ensure crystal-clear call quality",
        "Comfortable Ergonomic Fit with Deep Bass: 13mm oversized drivers deliver powerful low-frequency response while three sizes of memory foam tips create a secure seal for noise isolation and extended wearing comfort",
    ],
    "description": (
        "Transform your daily audio with these upgraded Wireless Bluetooth 5.3 Earbuds featuring professional-grade "
        "Active Noise Cancellation. Whether you are commuting, working out, or relaxing at home, the 13mm dynamic "
        "drivers deliver audiophile-quality sound with deep, impactful bass and crisp highs. The latest Bluetooth 5.3 "
        "technology provides instant pairing, rock-solid stability, and ultra-low latency for seamless video and gaming. "
        "Built tough with IPX5 waterproofing, these earbuds handle anything from intense HIIT sessions to unexpected "
        "rain showers. The ergonomic design with three sizes of memory foam tips ensures a comfortable, secure fit "
        "for hours of continuous wear. A massive 30-hour total battery life means you can go days between charges, "
        "and when you do need power, USB-C fast charging delivers 2 hours of music in just 10 minutes. Package includes: "
        "Earbuds, Charging Case, Memory Foam Tips (S/M/L), USB-C Cable, Quick Start Guide."
    ),
    "search_terms": "wireless earbuds bluetooth 5.3 noise cancelling headphones waterproof earphones gym running workout case",
    "reasoning": (
        "Preserved high-performing keywords 'wireless earbuds', 'bluetooth 5.3', and 'noise cancelling' in prominent "
        "positions. Moved Bluetooth version to title for better search matching. Enhanced bullet structure with "
        "specific technical metrics. Added memory foam tips as a differentiator. Improved description flow for "
        "better conversion. Search terms deduplicated and focused on high-volume terms."
    ),
    "confidence": 0.88,
    "diff": {
        "title": {
            "old": "Wireless Earbuds Bluetooth 5.3",
            "new": "Wireless Earbuds Bluetooth 5.3, Active Noise Cancelling Headphones with 30H Battery, IPX5 Waterproof, Touch Controls, Deep Bass Earphones for iPhone Android",
        },
        "bullets_changed": [0, 1, 2, 3, 4],
    },
}

MOCK_CLAUDE_RESPONSE_TOO_LONG = {
    **MOCK_CLAUDE_RESPONSE_VALID,
    "title": "A" * 250,  # Exceeds 200-char limit
}


# ── Fixtures ───────────────────────────────────────────────────

@pytest.fixture
def mock_claude():
    """Mock the Claude API client."""
    client = AsyncMock()
    return client


@pytest.fixture
def mock_sp_api():
    """Mock SP-API connector."""
    connector = AsyncMock()
    connector.get_listing.return_value = None
    connector.get_competitive_pricing.return_value = []
    return connector


@pytest.fixture
def listing_agent(mock_claude, mock_sp_api):
    """Create a ListingAgent with mocked dependencies (no DB)."""
    return ListingAgent(
        claude_client=mock_claude,
        sp_api_connector=mock_sp_api,
        db_session=None,
        tenant_id=TENANT_A_ID,
    )


Tenant = namedtuple("Tenant", ["id"])


@pytest.fixture
def tenant_a():
    return Tenant(id=TENANT_A_ID)


@pytest_asyncio.fixture
async def listing_agent_with_db(mock_claude, mock_sp_api):
    """ListingAgent wired to a real DB session for proposal tests."""
    engine = create_async_engine(ADMIN_DATABASE_URL, poolclass=NullPool)
    try:
        async with engine.begin() as conn:
            # Clean existing test data (FK order)
            await conn.execute(
                text("DELETE FROM agent_actions WHERE tenant_id = :tid"),
                {"tid": str(TENANT_A_ID)},
            )
            await conn.execute(
                text("DELETE FROM users WHERE tenant_id = :tid"),
                {"tid": str(TENANT_A_ID)},
            )
            await conn.execute(
                text("DELETE FROM tenants WHERE id = :tid"),
                {"tid": str(TENANT_A_ID)},
            )
            # Seed tenant
            await conn.execute(text(
                "INSERT INTO tenants (id, name, slug, subscription_tier, status) "
                "VALUES (:id, 'Tenant A', 'tenant-a-listing', 'starter', 'active') "
                "ON CONFLICT (id) DO NOTHING"),
                {"id": str(TENANT_A_ID)},
            )
        async with AsyncSession(engine, expire_on_commit=False) as session:
            agent = ListingAgent(
                claude_client=mock_claude,
                sp_api_connector=mock_sp_api,
                db_session=session,
                tenant_id=TENANT_A_ID,
            )
            yield agent, session, mock_claude
    finally:
        async with engine.begin() as conn:
            await conn.execute(
                text("DELETE FROM agent_actions WHERE tenant_id = :tid"),
                {"tid": str(TENANT_A_ID)},
            )
            await conn.execute(
                text("DELETE FROM users WHERE tenant_id = :tid"),
                {"tid": str(TENANT_A_ID)},
            )
            await conn.execute(
                text("DELETE FROM tenants WHERE id = :tid"),
                {"tid": str(TENANT_A_ID)},
            )
        await engine.dispose()


# ── Test Classes ───────────────────────────────────────────────


class TestListingGeneration:

    @pytest.mark.asyncio
    async def test_generates_complete_listing(self, listing_agent, mock_claude):
        """Agent should return title, 5 bullets, description, and search terms."""
        mock_claude.messages.create.return_value = _make_claude_response(MOCK_CLAUDE_RESPONSE_VALID)
        result = await listing_agent.generate(
            asin="B08XYZ123",
            product_data={"name": "Wireless Bluetooth Earbuds", "category": "Electronics", "features": ["Noise cancelling", "30h battery"]},
            marketplace_id="ATVPDKIKX0DER",
        )
        assert "title" in result
        assert "bullets" in result
        assert len(result["bullets"]) == 5
        assert "description" in result
        assert "search_terms" in result

    @pytest.mark.asyncio
    async def test_title_under_200_chars(self, listing_agent, mock_claude):
        """Generated title must be <= 200 characters."""
        mock_claude.messages.create.return_value = _make_claude_response(MOCK_CLAUDE_RESPONSE_VALID)
        result = await listing_agent.generate(
            asin="B08XYZ123",
            product_data={"name": "Ultra Long Product Name That Goes On Forever", "category": "Electronics"},
            marketplace_id="ATVPDKIKX0DER",
        )
        assert len(result["title"]) <= 200

    @pytest.mark.asyncio
    async def test_exactly_5_bullets(self, listing_agent, mock_claude):
        """Must generate exactly 5 bullet points."""
        mock_claude.messages.create.return_value = _make_claude_response(MOCK_CLAUDE_RESPONSE_VALID)
        result = await listing_agent.generate(
            asin="B08XYZ123", product_data={"name": "Product"}, marketplace_id="ATVPDKIKX0DER",
        )
        assert len(result["bullets"]) == 5

    @pytest.mark.asyncio
    async def test_each_bullet_under_500_chars(self, listing_agent, mock_claude):
        mock_claude.messages.create.return_value = _make_claude_response(MOCK_CLAUDE_RESPONSE_VALID)
        result = await listing_agent.generate(
            asin="B08XYZ123", product_data={"name": "Product"}, marketplace_id="ATVPDKIKX0DER",
        )
        for i, bullet in enumerate(result["bullets"]):
            assert len(bullet) <= 500, f"Bullet {i+1} exceeds 500 chars: {len(bullet)}"

    @pytest.mark.asyncio
    async def test_description_under_2000_chars(self, listing_agent, mock_claude):
        mock_claude.messages.create.return_value = _make_claude_response(MOCK_CLAUDE_RESPONSE_VALID)
        result = await listing_agent.generate(
            asin="B08XYZ123", product_data={"name": "Product"}, marketplace_id="ATVPDKIKX0DER",
        )
        assert len(result["description"]) <= 2000

    @pytest.mark.asyncio
    async def test_search_terms_under_250_bytes(self, listing_agent, mock_claude):
        """Search terms must be <= 250 BYTES (UTF-8 encoded), not characters."""
        mock_claude.messages.create.return_value = _make_claude_response(MOCK_CLAUDE_RESPONSE_VALID)
        result = await listing_agent.generate(
            asin="B08XYZ123", product_data={"name": "Product"}, marketplace_id="ATVPDKIKX0DER",
        )
        assert len(result["search_terms"].encode("utf-8")) <= 250

    @pytest.mark.asyncio
    async def test_no_promotional_language(self, listing_agent, mock_claude):
        """Title and bullets must not contain banned promotional words."""
        mock_claude.messages.create.return_value = _make_claude_response(MOCK_CLAUDE_RESPONSE_VALID)
        result = await listing_agent.generate(
            asin="B08XYZ123", product_data={"name": "Product"}, marketplace_id="ATVPDKIKX0DER",
        )
        banned = ["best", "cheapest", "sale", "discount", "free", "#1", "guaranteed", "top rated"]
        all_text = (result["title"] + " " + " ".join(result["bullets"])).lower()
        for word in banned:
            assert word not in all_text, f"Banned word '{word}' found in listing"


class TestListingOptimization:

    @pytest.mark.asyncio
    async def test_optimize_preserves_existing_keywords(self, listing_agent, mock_claude):
        """Optimization should keep high-performing keywords from the existing listing."""
        existing = {
            "title": "Wireless Earbuds Bluetooth 5.3",
            "bullets": ["Noise cancelling", "30h battery", "IPX5 waterproof", "Touch controls", "Fast charging"],
            "high_performing_keywords": ["wireless earbuds", "bluetooth 5.3", "noise cancelling"],
        }
        mock_claude.messages.create.return_value = _make_claude_response(MOCK_CLAUDE_RESPONSE_OPTIMIZED)
        result = await listing_agent.optimize(
            asin="B08XYZ123", existing_listing=existing, marketplace_id="ATVPDKIKX0DER",
        )
        result_text = (result["title"] + " " + " ".join(result["bullets"])).lower()
        for kw in existing["high_performing_keywords"]:
            assert kw in result_text, f"High-performing keyword '{kw}' was removed!"

    @pytest.mark.asyncio
    async def test_returns_diff(self, listing_agent, mock_claude):
        """Optimization should return a diff showing what changed."""
        mock_claude.messages.create.return_value = _make_claude_response(MOCK_CLAUDE_RESPONSE_OPTIMIZED)
        result = await listing_agent.optimize(
            asin="B08XYZ123",
            existing_listing={"title": "Old Title", "bullets": ["B1", "B2", "B3", "B4", "B5"]},
            marketplace_id="ATVPDKIKX0DER",
        )
        assert "diff" in result
        assert "title" in result["diff"]

    @pytest.mark.asyncio
    async def test_returns_reasoning(self, listing_agent, mock_claude):
        """Agent must explain WHY it made changes."""
        mock_claude.messages.create.return_value = _make_claude_response(MOCK_CLAUDE_RESPONSE_OPTIMIZED)
        result = await listing_agent.optimize(
            asin="B08XYZ123",
            existing_listing={"title": "Old Title", "bullets": ["B1", "B2", "B3", "B4", "B5"]},
            marketplace_id="ATVPDKIKX0DER",
        )
        assert "reasoning" in result
        assert len(result["reasoning"]) > 50

    @pytest.mark.asyncio
    async def test_returns_confidence_score(self, listing_agent, mock_claude):
        mock_claude.messages.create.return_value = _make_claude_response(MOCK_CLAUDE_RESPONSE_OPTIMIZED)
        result = await listing_agent.optimize(
            asin="B08XYZ123",
            existing_listing={"title": "Title", "bullets": ["B1", "B2", "B3", "B4", "B5"]},
            marketplace_id="ATVPDKIKX0DER",
        )
        assert "confidence" in result
        assert 0.0 <= result["confidence"] <= 1.0


class TestConstraintValidation:

    def test_validator_rejects_long_title(self, listing_agent):
        """Validator should reject titles over 200 chars."""
        listing = {"title": "A" * 201, "bullets": ["b"] * 5, "description": "d", "search_terms": "st"}
        errors = listing_agent.validate(listing)
        assert any("title" in e.lower() for e in errors)

    def test_validator_rejects_wrong_bullet_count(self, listing_agent):
        listing = {"title": "OK", "bullets": ["b"] * 3, "description": "d", "search_terms": "st"}
        errors = listing_agent.validate(listing)
        assert any("bullet" in e.lower() for e in errors)

    def test_validator_rejects_oversized_search_terms(self, listing_agent):
        listing = {"title": "OK", "bullets": ["b"] * 5, "description": "d", "search_terms": "a " * 200}
        errors = listing_agent.validate(listing)
        assert any("search" in e.lower() or "byte" in e.lower() for e in errors)

    @pytest.mark.asyncio
    async def test_agent_auto_fixes_constraint_violations(self, listing_agent, mock_claude):
        """If Claude returns content that violates constraints, agent should auto-fix."""
        # First call returns too-long title, second call returns valid response
        mock_claude.messages.create.side_effect = [
            _make_claude_response(MOCK_CLAUDE_RESPONSE_TOO_LONG),
            _make_claude_response(MOCK_CLAUDE_RESPONSE_VALID),
        ]
        result = await listing_agent.generate(
            asin="B08XYZ123", product_data={"name": "Product"}, marketplace_id="ATVPDKIKX0DER",
        )
        assert len(result["title"]) <= 200


class TestProposalCreation:

    @pytest.mark.asyncio
    async def test_creates_agent_action_proposal(self, listing_agent_with_db):
        """Generating a listing should create an agent_action in 'proposed' status."""
        agent, session, mock_claude = listing_agent_with_db
        mock_claude.messages.create.return_value = _make_claude_response(MOCK_CLAUDE_RESPONSE_VALID)

        await agent.generate(
            asin="B08XYZ123",
            product_data={"name": "Product"},
            marketplace_id="ATVPDKIKX0DER",
        )

        result = await session.execute(
            text(
                "SELECT agent_type, action_type, status, target_asin, confidence_score "
                "FROM agent_actions WHERE tenant_id = :tid ORDER BY created_at DESC LIMIT 1"
            ),
            {"tid": str(TENANT_A_ID)},
        )
        action = result.fetchone()
        assert action is not None
        assert action.status == "proposed"
        assert action.agent_type == "listing"
        assert action.action_type == "generate"
        assert action.target_asin == "B08XYZ123"


# ── Helpers ────────────────────────────────────────────────────

def _make_claude_response(data: dict):
    """Build a mock Anthropic Messages API response object."""
    import json

    content_block = MagicMock()
    content_block.type = "text"
    content_block.text = json.dumps(data)

    response = MagicMock()
    response.content = [content_block]
    response.stop_reason = "end_turn"
    response.usage = MagicMock(input_tokens=500, output_tokens=800)
    return response
