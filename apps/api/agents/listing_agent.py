"""Listing Agent — AI-powered Amazon product listing generation and optimization."""

import json
import re
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from agents.prompts.listing_prompt import (
    FIX_VIOLATIONS_TEMPLATE,
    GENERATE_TEMPLATE,
    OPTIMIZE_TEMPLATE,
    SYSTEM_PROMPT,
)

# Banned promotional words (case-insensitive matching)
BANNED_WORDS = [
    "best",
    "cheapest",
    "sale",
    "discount",
    "free",
    "#1",
    "guaranteed",
    "top rated",
    "lowest price",
    "limited time",
]

MAX_RETRIES = 2
CLAUDE_MODEL = "claude-sonnet-4-20250514"
CLAUDE_MAX_TOKENS = 4096


class ListingAgent:
    """AI agent that generates and optimizes Amazon product listings using Claude."""

    def __init__(
        self,
        claude_client: Any,
        sp_api_connector: Any,
        db_session: AsyncSession | None,
        tenant_id: uuid.UUID,
    ):
        self._claude = claude_client
        self._sp_api = sp_api_connector
        self._db = db_session
        self._tenant_id = tenant_id

    async def generate(
        self,
        asin: str,
        product_data: dict,
        marketplace_id: str,
    ) -> dict:
        """Generate a new optimized Amazon product listing.

        1. Fetch current listing from SP-API (if exists)
        2. Fetch competitor listings for context
        3. Build Claude prompt with product_data + competitor context + Amazon constraints
        4. Call Claude API
        5. Parse structured JSON response
        6. Validate — if violations, re-prompt Claude (max 2 retries)
        7. Create agent_action record with status='proposed'
        8. Return listing dict
        """
        # Gather context from SP-API
        existing_listing = await self._sp_api.get_listing(asin) if self._sp_api else None
        competitors = await self._sp_api.get_competitive_pricing(asin) if self._sp_api else []

        existing_context = ""
        if existing_listing:
            existing_context = f"**Existing Listing:**\n{json.dumps(existing_listing, indent=2)}"

        competitor_context = ""
        if competitors:
            competitor_context = f"**Competitor Context:**\n{json.dumps(competitors[:3], indent=2)}"

        user_prompt = GENERATE_TEMPLATE.format(
            asin=asin,
            marketplace_id=marketplace_id,
            product_data=json.dumps(product_data, indent=2),
            existing_listing_context=existing_context,
            competitor_context=competitor_context,
        )

        listing = await self._call_claude_with_retries(user_prompt)

        # Persist proposal if DB session available
        if self._db:
            await self._create_proposal(
                asin=asin,
                action_type="generate",
                listing=listing,
            )

        return listing

    async def optimize(
        self,
        asin: str,
        existing_listing: dict,
        marketplace_id: str,
    ) -> dict:
        """Optimize an existing Amazon product listing.

        1. Build optimization prompt with existing listing and high-performing keywords
        2. Call Claude, parse, validate
        3. Generate diff between old and new
        4. Return optimized listing with diff, reasoning, confidence
        """
        high_keywords = existing_listing.get("high_performing_keywords", [])

        user_prompt = OPTIMIZE_TEMPLATE.format(
            asin=asin,
            marketplace_id=marketplace_id,
            existing_title=existing_listing.get("title", ""),
            existing_bullets=json.dumps(existing_listing.get("bullets", []), indent=2),
            high_performing_keywords=", ".join(high_keywords) if high_keywords else "None provided",
        )

        listing = await self._call_claude_with_retries(user_prompt)

        # Ensure diff is present
        if "diff" not in listing:
            listing["diff"] = self._compute_diff(existing_listing, listing)

        # Persist proposal if DB session available
        if self._db:
            await self._create_proposal(
                asin=asin,
                action_type="optimize",
                listing=listing,
            )

        return listing

    def validate(self, listing: dict) -> list[str]:
        """Validate a listing against all Amazon SP-API constraints.

        Returns a list of error strings. Empty list means valid.
        """
        errors: list[str] = []

        title = listing.get("title", "")
        bullets = listing.get("bullets", [])
        description = listing.get("description", "")
        search_terms = listing.get("search_terms", "")

        # Title length
        if len(title) > 200:
            errors.append(f"Title exceeds 200 characters ({len(title)} chars)")

        # Bullet count
        if len(bullets) != 5:
            errors.append(f"Expected exactly 5 bullet points, got {len(bullets)}")

        # Bullet lengths
        for i, bullet in enumerate(bullets):
            if len(bullet) > 500:
                errors.append(f"Bullet {i + 1} exceeds 500 characters ({len(bullet)} chars)")

        # Description length
        if len(description) > 2000:
            errors.append(f"Description exceeds 2,000 characters ({len(description)} chars)")

        # Search terms byte size (UTF-8)
        search_bytes = len(search_terms.encode("utf-8"))
        if search_bytes > 250:
            errors.append(f"Search terms exceed 250 bytes ({search_bytes} bytes)")

        # Banned promotional words
        all_text = (title + " " + " ".join(bullets)).lower()
        for word in BANNED_WORDS:
            if word in all_text:
                errors.append(f"Banned promotional word found: '{word}'")

        # HTML tags
        if re.search(r"<[^>]+>", title + " ".join(bullets) + description):
            errors.append("HTML tags are not allowed")

        # Phone numbers
        if re.search(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", title + " ".join(bullets) + description):
            errors.append("Phone numbers are not allowed")

        # URLs
        if re.search(r"https?://|www\.", title + " ".join(bullets) + description):
            errors.append("URLs are not allowed")

        return errors

    # ── Private methods ────────────────────────────────────────

    async def _call_claude_with_retries(self, user_prompt: str) -> dict:
        """Call Claude API and retry if response violates constraints."""
        listing = await self._call_claude(user_prompt)
        errors = self.validate(listing)

        for _ in range(MAX_RETRIES):
            if not errors:
                break

            fix_prompt = FIX_VIOLATIONS_TEMPLATE.format(
                violations="\n".join(f"- {e}" for e in errors),
            )
            listing = await self._call_claude(fix_prompt)
            errors = self.validate(listing)

        return listing

    async def _call_claude(self, user_prompt: str) -> dict:
        """Make a single Claude API call and parse the JSON response."""
        response = await self._claude.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=CLAUDE_MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        # Extract text from response
        raw_text = ""
        for block in response.content:
            if block.type == "text":
                raw_text += block.text

        # Parse JSON — strip markdown fences if present
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)

        return json.loads(cleaned)

    async def _create_proposal(self, asin: str, action_type: str, listing: dict) -> None:
        """Persist an agent_action record with status='proposed'."""
        action_id = uuid.uuid4()
        confidence = listing.get("confidence")

        await self._db.execute(
            text(
                "INSERT INTO agent_actions "
                "(id, tenant_id, agent_type, action_type, target_asin, status, proposed_change, reasoning, confidence_score) "
                "VALUES (:id, :tenant_id, 'listing', :action_type, :asin, 'proposed', :proposed_change, :reasoning, :confidence)"
            ),
            {
                "id": str(action_id),
                "tenant_id": str(self._tenant_id),
                "action_type": action_type,
                "asin": asin,
                "proposed_change": json.dumps({
                    "title": listing.get("title"),
                    "bullets": listing.get("bullets"),
                    "description": listing.get("description"),
                    "search_terms": listing.get("search_terms"),
                }),
                "reasoning": listing.get("reasoning"),
                "confidence": confidence,
            },
        )
        await self._db.commit()

    @staticmethod
    def _compute_diff(old: dict, new: dict) -> dict:
        """Compute a simple diff between old and new listings."""
        diff: dict[str, Any] = {}

        old_title = old.get("title", "")
        new_title = new.get("title", "")
        if old_title != new_title:
            diff["title"] = {"old": old_title, "new": new_title}

        old_bullets = old.get("bullets", [])
        new_bullets = new.get("bullets", [])
        changed_indices = [
            i
            for i in range(max(len(old_bullets), len(new_bullets)))
            if i >= len(old_bullets) or i >= len(new_bullets) or old_bullets[i] != new_bullets[i]
        ]
        if changed_indices:
            diff["bullets_changed"] = changed_indices

        return diff
