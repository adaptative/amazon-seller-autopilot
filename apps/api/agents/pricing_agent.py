"""Pricing Agent — Game-theory repricing with Buy Box optimization."""

import json
import time
import uuid
from decimal import Decimal, ROUND_HALF_UP

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.event_bus import Event, EventBus, EventType

logger = structlog.get_logger()

# Default constants
DEFAULT_MIN_MARGIN = Decimal("0.15")
UNDERCUT_RANGE_MIN = Decimal("0.01")
UNDERCUT_RANGE_MAX = Decimal("0.50")
INCREASE_STEP_MIN = Decimal("0.02")  # 2%
INCREASE_STEP_MAX = Decimal("0.05")  # 5%
CLOSE_COMPETITOR_THRESHOLD = Decimal("0.20")  # 20% above us
BUY_BOX_TRACKING_WINDOW = 100


class PricingAgent:
    """AI agent that calculates optimal prices using game-theory repricing
    and tracks Buy Box ownership."""

    def __init__(
        self,
        sp_api_connector=None,
        db_session: AsyncSession | None = None,
        tenant_id: str | None = None,
        event_bus: EventBus | None = None,
        redis_client=None,
        min_margin: Decimal | float = DEFAULT_MIN_MARGIN,
    ):
        self.sp_api = sp_api_connector
        self.db_session = db_session
        self.tenant_id = tenant_id
        self.event_bus = event_bus
        self.redis = redis_client
        self.min_margin = Decimal(str(min_margin)) if not isinstance(min_margin, Decimal) else min_margin

    def _min_price(self, cost: Decimal) -> Decimal:
        """Calculate the minimum acceptable price given cost and margin."""
        return (cost * (1 + self.min_margin)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    async def calculate_optimal_price(
        self,
        asin: str,
        competitor_offers: list[dict],
        our_cost: Decimal,
        current_price: Decimal,
        we_own_buy_box: bool = False,
    ) -> dict:
        """Calculate the optimal price using game-theory logic.

        Returns dict with: action, suggested_price, reasoning, confidence, estimated_impact.
        """
        our_cost = Decimal(str(our_cost))
        current_price = Decimal(str(current_price))
        floor_price = self._min_price(our_cost)

        # Find the Buy Box winner price
        buy_box_offer = None
        for offer in competitor_offers:
            if offer.get("is_buy_box") or offer.get("IsBuyBoxWinner"):
                buy_box_offer = offer
                break

        buy_box_price = Decimal(str(buy_box_offer["price"])) if buy_box_offer else None

        # Find the closest competitor (lowest total price)
        competitor_total_prices = []
        for offer in competitor_offers:
            total = Decimal(str(offer.get("price", 0))) + Decimal(str(offer.get("shipping", 0)))
            competitor_total_prices.append(total)
        closest_competitor = min(competitor_total_prices) if competitor_total_prices else None

        # --- Game-theory decision logic ---

        # Case 1: We own Buy Box and no close competitors
        if we_own_buy_box and closest_competitor is not None:
            gap_ratio = (closest_competitor - current_price) / current_price if current_price > 0 else Decimal("0")

            if gap_ratio > CLOSE_COMPETITOR_THRESHOLD:
                # No close competition — gradual price increase (2-5%)
                increase_pct = min(
                    INCREASE_STEP_MAX,
                    gap_ratio / 4,  # Conservative: increase by 1/4 of the gap
                )
                increase_pct = max(INCREASE_STEP_MIN, increase_pct)
                new_price = (current_price * (1 + increase_pct)).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                return {
                    "action": "increase",
                    "suggested_price": float(new_price),
                    "reasoning": (
                        f"No close competitors (nearest is {float(closest_competitor):.2f}, "
                        f"{float(gap_ratio * 100):.1f}% above). "
                        f"Suggesting {float(increase_pct * 100):.1f}% increase."
                    ),
                    "confidence": 0.75,
                    "estimated_impact": {"buy_box_probability": 0.90, "margin_change_pct": float(increase_pct * 100)},
                }
            else:
                # Close competitor — hold current price
                return {
                    "action": "hold",
                    "suggested_price": float(current_price),
                    "reasoning": (
                        f"Already winning Buy Box. Closest competitor at "
                        f"{float(closest_competitor):.2f} is within {float(gap_ratio * 100):.1f}%. Holding."
                    ),
                    "confidence": 0.85,
                    "estimated_impact": {"buy_box_probability": 0.80, "margin_change_pct": 0.0},
                }

        # Case 2: We own Buy Box with no competitors at all
        if we_own_buy_box and not competitor_offers:
            new_price = (current_price * (1 + INCREASE_STEP_MIN)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            return {
                "action": "increase",
                "suggested_price": float(new_price),
                "reasoning": "No competitors found. Suggesting gradual 2% increase.",
                "confidence": 0.70,
                "estimated_impact": {"buy_box_probability": 0.95, "margin_change_pct": float(INCREASE_STEP_MIN * 100)},
            }

        # Case 3: Competitor owns Buy Box — try to undercut
        if buy_box_price is not None:
            # Calculate undercut price: match or undercut by $0.01-$0.50
            undercut_amount = min(
                UNDERCUT_RANGE_MAX,
                max(UNDERCUT_RANGE_MIN, (buy_box_price - floor_price) * Decimal("0.1")),
            )
            target_price = (buy_box_price - undercut_amount).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

            # Enforce minimum margin
            if target_price < floor_price:
                # Can't undercut and maintain margin
                return {
                    "action": "hold",
                    "suggested_price": float(max(current_price, floor_price)),
                    "reasoning": (
                        f"Buy Box at {float(buy_box_price):.2f}. Undercutting would violate "
                        f"minimum margin ({float(self.min_margin * 100):.0f}%). "
                        f"Floor price: {float(floor_price):.2f}. Holding."
                    ),
                    "confidence": 0.90,
                    "estimated_impact": {"buy_box_probability": 0.20, "margin_change_pct": 0.0},
                    "margin_limited": True,
                }

            return {
                "action": "decrease",
                "suggested_price": float(target_price),
                "reasoning": (
                    f"Undercutting Buy Box winner at {float(buy_box_price):.2f} "
                    f"by {float(undercut_amount):.2f}. "
                    f"Target: {float(target_price):.2f} (above floor {float(floor_price):.2f})."
                ),
                "confidence": 0.85,
                "estimated_impact": {
                    "buy_box_probability": 0.75,
                    "margin_change_pct": float(((target_price - current_price) / current_price) * 100),
                },
            }

        # Case 4: No Buy Box info, use closest competitor
        if closest_competitor is not None and closest_competitor < current_price:
            target_price = (closest_competitor - UNDERCUT_RANGE_MIN).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            if target_price >= floor_price:
                return {
                    "action": "decrease",
                    "suggested_price": float(target_price),
                    "reasoning": f"Matching closest competitor at {float(closest_competitor):.2f}.",
                    "confidence": 0.70,
                    "estimated_impact": {"buy_box_probability": 0.50, "margin_change_pct": float(((target_price - current_price) / current_price) * 100)},
                }

        # Default: hold
        return {
            "action": "hold",
            "suggested_price": float(current_price),
            "reasoning": "No actionable price change identified.",
            "confidence": 0.60,
            "estimated_impact": {"buy_box_probability": 0.50, "margin_change_pct": 0.0},
        }

    async def process_offer_change(self, notification: dict) -> dict | None:
        """Process an ANY_OFFER_CHANGED SP-API notification.

        Parses the notification, calculates optimal price, creates a proposal
        if action is needed, and records Buy Box status.
        """
        payload = notification.get("Payload", {})
        asin = payload.get("ASIN", "")
        buy_box_data = payload.get("BuyBoxPrice", {})
        offers = payload.get("Offers", [])

        # Determine current price and Buy Box ownership
        our_seller_id = "OUR_ID"  # Would come from tenant config
        current_price = Decimal("0")
        we_own_buy_box = False
        competitor_offers = []

        for offer in offers:
            seller_id = offer.get("SellerId", "")
            price = Decimal(str(offer.get("Price", offer.get("price", 0))))
            is_bb = offer.get("IsBuyBoxWinner", offer.get("is_buy_box", False))

            if seller_id == our_seller_id:
                current_price = price
                we_own_buy_box = bool(is_bb)
            else:
                competitor_offers.append({
                    "price": float(price),
                    "shipping": float(offer.get("Shipping", offer.get("shipping", 0))),
                    "is_buy_box": is_bb,
                    "seller_rating": offer.get("SellerRating", offer.get("seller_rating", 4.0)),
                })

        if current_price == 0:
            current_price = Decimal(str(buy_box_data.get("Amount", 25.00)))

        # Fetch cost from DB (fallback to estimated)
        our_cost = await self._get_product_cost(asin)

        # Calculate optimal price
        result = await self.calculate_optimal_price(
            asin=asin,
            competitor_offers=competitor_offers,
            our_cost=our_cost,
            current_price=current_price,
            we_own_buy_box=we_own_buy_box,
        )

        # Record Buy Box check
        await self.record_buy_box_check(asin, won=we_own_buy_box)

        # Create proposal if action needed
        if result["action"] != "hold" and self.db_session and self.tenant_id:
            await self._create_proposal(asin, result)

        # Publish event
        if result["action"] != "hold" and self.event_bus and self.tenant_id:
            event = Event(
                type=EventType.AGENT_ACTION_PROPOSED,
                tenant_id=uuid.UUID(self.tenant_id) if isinstance(self.tenant_id, str) else self.tenant_id,
                payload={
                    "agent_type": "pricing",
                    "asin": asin,
                    "action": result["action"],
                    "suggested_price": result["suggested_price"],
                },
            )
            try:
                await self.event_bus.publish(event)
            except Exception:
                logger.warning("event_publish_failed", asin=asin)

        return result

    async def _get_product_cost(self, asin: str) -> Decimal:
        """Fetch product cost from DB. Falls back to estimated cost."""
        # In production, this would query a products table.
        # For now, return a reasonable default.
        return Decimal("12.00")

    async def _create_proposal(self, asin: str, result: dict) -> str:
        """Create an agent_action record with status 'proposed'."""
        action_id = str(uuid.uuid4())
        proposed_change = {
            "action": result["action"],
            "suggested_price": result["suggested_price"],
            "estimated_impact": result.get("estimated_impact", {}),
        }
        await self.db_session.execute(
            text(
                "INSERT INTO agent_actions "
                "(id, tenant_id, agent_type, action_type, target_asin, status, "
                "proposed_change, reasoning, confidence_score) "
                "VALUES (:id, :tenant_id, 'pricing', 'price_update', :asin, 'proposed', "
                ":proposed_change, :reasoning, :confidence_score)"
            ),
            {
                "id": action_id,
                "tenant_id": self.tenant_id,
                "action_type": "price_update",
                "asin": asin,
                "proposed_change": json.dumps(proposed_change),
                "reasoning": result.get("reasoning", ""),
                "confidence_score": result.get("confidence", 0.0),
            },
        )
        await self.db_session.commit()
        return action_id

    # ── Buy Box Tracking ──────────────────────────────────────────

    async def record_buy_box_check(self, asin: str, won: bool) -> None:
        """Record a Buy Box ownership check in Redis."""
        if not self.redis:
            return
        key = f"buybox:{self.tenant_id}:{asin}"
        timestamp = time.time()
        value = f"{'win' if won else 'loss'}:{timestamp}"
        await self.redis.lpush(key, value)
        # Trim to keep only last N entries
        await self.redis.ltrim(key, 0, BUY_BOX_TRACKING_WINDOW - 1)

    async def get_buy_box_win_rate(self, asin: str) -> float:
        """Calculate Buy Box win rate from recent checks."""
        if not self.redis:
            return 0.0
        key = f"buybox:{self.tenant_id}:{asin}"
        entries = await self.redis.lrange(key, 0, BUY_BOX_TRACKING_WINDOW - 1)
        if not entries:
            return 0.0

        wins = 0
        total = len(entries)
        for entry in entries:
            entry_str = entry.decode() if isinstance(entry, bytes) else entry
            if entry_str.startswith("win"):
                wins += 1

        return round((wins / total) * 100, 2)

    # ── Price History ─────────────────────────────────────────────

    async def record_price_change(self, asin: str, old_price: Decimal, new_price: Decimal) -> None:
        """Store a price change event in Redis for charting."""
        if not self.redis:
            return
        key = f"price_history:{self.tenant_id}:{asin}"
        entry = json.dumps({
            "old_price": float(old_price),
            "new_price": float(new_price),
            "timestamp": time.time(),
        })
        await self.redis.lpush(key, entry)
        # Keep last 1000 entries
        await self.redis.ltrim(key, 0, 999)

    async def get_price_history(self, asin: str, limit: int = 10) -> list[dict]:
        """Retrieve recent price change history."""
        if not self.redis:
            return []
        key = f"price_history:{self.tenant_id}:{asin}"
        entries = await self.redis.lrange(key, 0, limit - 1)
        result = []
        for entry in entries:
            entry_str = entry.decode() if isinstance(entry, bytes) else entry
            result.append(json.loads(entry_str))
        return result
