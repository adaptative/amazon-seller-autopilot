"""Listing Agent — AI-powered Amazon product listing generation and optimization."""

import json
import re
import uuid

import anthropic
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from agents.prompts.listing_prompt import (
    GENERATE_TEMPLATE,
    OPTIMIZE_TEMPLATE,
    SYSTEM_PROMPT,
)

# Amazon SP-API constraint constants
MAX_TITLE_LENGTH = 200
MAX_BULLET_LENGTH = 500
MAX_DESCRIPTION_LENGTH = 2000
MAX_SEARCH_TERMS_BYTES = 250
REQUIRED_BULLET_COUNT = 5
MAX_RETRIES = 2

BANNED_PHRASES = [
    "sale", "discount", "best", "cheapest", "free",
    "buy now", "limited time", "act now", "order now",
    "best seller", "top rated", "#1", "number one",
]

HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
PHONE_PATTERN = re.compile(r"\+?\d[\d\-\s()]{7,}\d")
URL_PATTERN = re.compile(r"https?://\S+|www\.\S+")


class ListingAgent:
    """AI agent that generates and optimizes Amazon product listings using Claude."""

    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "claude-sonnet-4-20250514"
        self.max_tokens = 4096

    def validate(self, listing: dict) -> list[str]:
        """Validate a listing against Amazon SP-API constraints.

        Returns a list of error strings. Empty list means the listing is valid.
        """
        errors: list[str] = []
        title = listing.get("title", "")
        bullet_points = listing.get("bullet_points", [])
        description = listing.get("description", "")
        search_terms = listing.get("search_terms", "")

        # Title constraints
        if len(title) > MAX_TITLE_LENGTH:
            errors.append(f"Title exceeds {MAX_TITLE_LENGTH} characters ({len(title)})")

        # Bullet point constraints
        if len(bullet_points) != REQUIRED_BULLET_COUNT:
            errors.append(
                f"Expected {REQUIRED_BULLET_COUNT} bullet points, got {len(bullet_points)}"
            )
        for i, bullet in enumerate(bullet_points):
            if len(bullet) > MAX_BULLET_LENGTH:
                errors.append(
                    f"Bullet point {i + 1} exceeds {MAX_BULLET_LENGTH} characters ({len(bullet)})"
                )

        # Description constraints
        if len(description) > MAX_DESCRIPTION_LENGTH:
            errors.append(
                f"Description exceeds {MAX_DESCRIPTION_LENGTH} characters ({len(description)})"
            )

        # Search terms byte constraint (UTF-8)
        search_terms_bytes = len(search_terms.encode("utf-8"))
        if search_terms_bytes > MAX_SEARCH_TERMS_BYTES:
            errors.append(
                f"Search terms exceed {MAX_SEARCH_TERMS_BYTES} bytes ({search_terms_bytes})"
            )

        # Banned promotional language
        all_text = f"{title} {' '.join(bullet_points)} {description} {search_terms}".lower()
        for phrase in BANNED_PHRASES:
            if re.search(r'\b' + re.escape(phrase) + r'\b', all_text):
                errors.append(f"Banned promotional language detected: '{phrase}'")

        # No HTML tags
        for field_name, field_value in [
            ("title", title),
            ("description", description),
            ("search_terms", search_terms),
        ] + [(f"bullet_{i+1}", b) for i, b in enumerate(bullet_points)]:
            if HTML_TAG_PATTERN.search(field_value):
                errors.append(f"HTML tags detected in {field_name}")

        # No phone numbers
        for field_name, field_value in [
            ("title", title),
            ("description", description),
        ] + [(f"bullet_{i+1}", b) for i, b in enumerate(bullet_points)]:
            if PHONE_PATTERN.search(field_value):
                errors.append(f"Phone number detected in {field_name}")

        # No URLs
        for field_name, field_value in [
            ("title", title),
            ("description", description),
        ] + [(f"bullet_{i+1}", b) for i, b in enumerate(bullet_points)]:
            if URL_PATTERN.search(field_value):
                errors.append(f"URL detected in {field_name}")

        # Duplicate keywords between search terms and title/bullets
        if search_terms and title:
            title_words = set(title.lower().split())
            bullet_words = set()
            for b in bullet_points:
                bullet_words.update(b.lower().split())
            visible_words = title_words | bullet_words
            search_words = set(search_terms.lower().split())
            duplicates = visible_words & search_words
            # Filter out common short words (prepositions, articles)
            stop_words = {"a", "an", "the", "and", "or", "for", "in", "on", "of", "to", "with", "is", "by", "at"}
            meaningful_duplicates = duplicates - stop_words
            if meaningful_duplicates:
                errors.append(
                    f"Duplicate keywords in search terms already present in title/bullets: "
                    f"{', '.join(sorted(meaningful_duplicates))}"
                )

        return errors

    def _call_claude(self, user_prompt: str) -> dict:
        """Call Claude API and parse the JSON response."""
        message = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=[{"role": "user", "content": user_prompt}],
            system=SYSTEM_PROMPT,
        )
        response_text = message.content[0].text

        # Strip markdown code fences if present
        cleaned = response_text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            # Remove first and last lines (```json and ```)
            lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines)

        return json.loads(cleaned)

    def _call_claude_with_retry(self, user_prompt: str, constraint_errors: list[str] | None = None) -> dict:
        """Call Claude with auto-fix retry on constraint violations."""
        if constraint_errors:
            fix_prompt = (
                f"{user_prompt}\n\n"
                f"IMPORTANT: Your previous response had these constraint violations that MUST be fixed:\n"
                + "\n".join(f"- {e}" for e in constraint_errors)
                + "\n\nPlease fix ALL violations and return a valid listing."
            )
            return self._call_claude(fix_prompt)
        return self._call_claude(user_prompt)

    async def generate(
        self,
        asin: str,
        product_data: dict,
        marketplace_id: str,
        session: AsyncSession | None = None,
        tenant_id: str | None = None,
    ) -> dict:
        """Generate a complete Amazon product listing.

        Args:
            asin: The product ASIN.
            product_data: Product information for listing generation.
            marketplace_id: Amazon marketplace identifier.
            session: Optional database session for creating agent_action records.
            tenant_id: Optional tenant ID for multi-tenant record creation.

        Returns:
            Dict containing the generated listing, validation status, and metadata.
        """
        product_data_str = json.dumps(product_data, indent=2)
        user_prompt = GENERATE_TEMPLATE.format(
            asin=asin,
            marketplace_id=marketplace_id,
            product_data=product_data_str,
        )

        # Generate with auto-fix retry loop
        listing = self._call_claude(user_prompt)
        errors = self.validate(listing)

        for _ in range(MAX_RETRIES):
            if not errors:
                break
            listing = self._call_claude_with_retry(user_prompt, errors)
            errors = self.validate(listing)

        result = {
            "asin": asin,
            "marketplace_id": marketplace_id,
            "listing": {
                "title": listing.get("title", ""),
                "bullet_points": listing.get("bullet_points", []),
                "description": listing.get("description", ""),
                "search_terms": listing.get("search_terms", ""),
            },
            "reasoning": listing.get("reasoning", ""),
            "confidence_score": listing.get("confidence_score", 0.0),
            "validation_errors": errors,
            "is_valid": len(errors) == 0,
        }

        # Create agent_action record if session is provided
        if session and tenant_id:
            await self._create_agent_action(
                session=session,
                tenant_id=tenant_id,
                asin=asin,
                action_type="listing_generate",
                proposed_change=result["listing"],
                reasoning=result["reasoning"],
                confidence_score=result["confidence_score"],
            )

        return result

    async def optimize(
        self,
        asin: str,
        existing_listing: dict,
        marketplace_id: str,
        keywords_to_preserve: list[str] | None = None,
        session: AsyncSession | None = None,
        tenant_id: str | None = None,
    ) -> dict:
        """Optimize an existing Amazon product listing.

        Args:
            asin: The product ASIN.
            existing_listing: Current listing data.
            marketplace_id: Amazon marketplace identifier.
            keywords_to_preserve: High-performing keywords to keep.
            session: Optional database session for creating agent_action records.
            tenant_id: Optional tenant ID for multi-tenant record creation.

        Returns:
            Dict containing the optimized listing, diff, reasoning, and confidence score.
        """
        current_bullets = "\n".join(
            f"  - {b}" for b in existing_listing.get("bullet_points", [])
        )
        keywords_str = ", ".join(keywords_to_preserve) if keywords_to_preserve else "None specified"

        user_prompt = OPTIMIZE_TEMPLATE.format(
            asin=asin,
            marketplace_id=marketplace_id,
            current_title=existing_listing.get("title", ""),
            current_bullets=current_bullets,
            current_description=existing_listing.get("description", ""),
            current_search_terms=existing_listing.get("search_terms", ""),
            keywords_to_preserve=keywords_str,
        )

        # Optimize with auto-fix retry loop
        listing = self._call_claude(user_prompt)
        errors = self.validate(listing)

        for _ in range(MAX_RETRIES):
            if not errors:
                break
            listing = self._call_claude_with_retry(user_prompt, errors)
            errors = self.validate(listing)

        optimized_listing = {
            "title": listing.get("title", ""),
            "bullet_points": listing.get("bullet_points", []),
            "description": listing.get("description", ""),
            "search_terms": listing.get("search_terms", ""),
        }

        # Generate diff
        diff = self._generate_diff(existing_listing, optimized_listing)

        result = {
            "asin": asin,
            "marketplace_id": marketplace_id,
            "listing": optimized_listing,
            "diff": diff,
            "reasoning": listing.get("reasoning", ""),
            "confidence_score": listing.get("confidence_score", 0.0),
            "validation_errors": errors,
            "is_valid": len(errors) == 0,
            "preserved_keywords": keywords_to_preserve or [],
        }

        # Create agent_action record if session is provided
        if session and tenant_id:
            await self._create_agent_action(
                session=session,
                tenant_id=tenant_id,
                asin=asin,
                action_type="listing_optimize",
                proposed_change={
                    "optimized_listing": optimized_listing,
                    "diff": diff,
                },
                reasoning=result["reasoning"],
                confidence_score=result["confidence_score"],
            )

        return result

    def _generate_diff(self, original: dict, optimized: dict) -> dict:
        """Generate a diff between original and optimized listings."""
        diff: dict = {}

        if original.get("title", "") != optimized.get("title", ""):
            diff["title"] = {
                "old": original.get("title", ""),
                "new": optimized.get("title", ""),
            }

        old_bullets = original.get("bullet_points", [])
        new_bullets = optimized.get("bullet_points", [])
        bullet_changes = []
        for i in range(max(len(old_bullets), len(new_bullets))):
            old_b = old_bullets[i] if i < len(old_bullets) else ""
            new_b = new_bullets[i] if i < len(new_bullets) else ""
            if old_b != new_b:
                bullet_changes.append({"index": i, "old": old_b, "new": new_b})
        if bullet_changes:
            diff["bullet_points"] = bullet_changes

        if original.get("description", "") != optimized.get("description", ""):
            diff["description"] = {
                "old": original.get("description", ""),
                "new": optimized.get("description", ""),
            }

        if original.get("search_terms", "") != optimized.get("search_terms", ""):
            diff["search_terms"] = {
                "old": original.get("search_terms", ""),
                "new": optimized.get("search_terms", ""),
            }

        return diff

    async def _create_agent_action(
        self,
        session: AsyncSession,
        tenant_id: str,
        asin: str,
        action_type: str,
        proposed_change: dict,
        reasoning: str,
        confidence_score: float,
    ) -> str:
        """Create an agent_action record in 'proposed' status.

        Returns the ID of the created record.
        """
        action_id = str(uuid.uuid4())
        await session.execute(
            text(
                "INSERT INTO agent_actions "
                "(id, tenant_id, agent_type, action_type, target_asin, status, "
                "proposed_change, reasoning, confidence_score) "
                "VALUES (:id, :tenant_id, 'listing', :action_type, :asin, 'proposed', "
                ":proposed_change, :reasoning, :confidence_score)"
            ),
            {
                "id": action_id,
                "tenant_id": tenant_id,
                "action_type": action_type,
                "asin": asin,
                "proposed_change": json.dumps(proposed_change),
                "reasoning": reasoning,
                "confidence_score": confidence_score,
            },
        )
        await session.commit()
        return action_id
