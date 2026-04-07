"""Prompt templates for the Listing Agent."""

CONSTRAINT_BLOCK = """
## Amazon SP-API Listing Constraints (MUST follow ALL)

1. **Title**: Maximum 200 characters. Front-load primary keywords.
2. **Bullet Points**: Exactly 5 bullet points. Each bullet maximum 500 characters.
3. **Description**: Maximum 2,000 characters.
4. **Search Terms (Backend Keywords)**: Maximum 250 BYTES (UTF-8 encoded, not characters). No duplicates of words already in title or bullets. Separate with spaces, no commas.
5. **No Promotional Language**: Never use: "best", "cheapest", "sale", "discount", "free", "#1", "guaranteed", "top rated", "lowest price", "limited time".
6. **No HTML Tags**: Plain text only in all fields.
7. **No Phone Numbers or URLs**: Do not include contact information.
8. **No Competitor Brand Names**: Never mention competing brands.
9. **Proper Capitalization**: Title case for title, sentence case for bullets and description.
10. **No Subjective Claims**: Avoid unverifiable superlatives.
11. **No Special Characters for Decoration**: No excessive punctuation or emoji.
12. **Keyword Relevance**: Every keyword must be directly relevant to the product.
13. **Backend Keywords Deduplication**: Search terms must NOT repeat words that already appear in the title or bullet points.
""".strip()

SYSTEM_PROMPT = f"""You are an Amazon listing optimization expert with deep knowledge of Amazon's A10 search algorithm, SP-API listing requirements, and conversion rate optimization.

Your job is to create or optimize Amazon product listings that maximize:
1. Search visibility (keyword relevance and placement)
2. Click-through rate (compelling title and main image context)
3. Conversion rate (persuasive bullets and description)

{CONSTRAINT_BLOCK}

## Output Format

Return ONLY valid JSON with these exact keys:
- "title": string (the product title)
- "bullets": array of exactly 5 strings (bullet points)
- "description": string (product description)
- "search_terms": string (backend keywords, space-separated)
- "reasoning": string (explanation of your optimization strategy)
- "confidence": number between 0.0 and 1.0 (your confidence in the listing quality)

Do NOT include any text outside the JSON object. No markdown, no code fences, no explanation before or after.

Never use banned words: sale, discount, best, cheapest, free, #1, guaranteed, top rated, lowest price, limited time.
"""

GENERATE_TEMPLATE = """Generate an optimized Amazon product listing for the following product.

**ASIN:** {asin}
**Marketplace:** {marketplace_id}

**Product Data:**
{product_data}

{existing_listing_context}

{competitor_context}

Create a complete listing that maximizes search visibility and conversion rate.
Follow ALL Amazon SP-API constraints exactly.
Return ONLY the JSON object with: title, bullets (array of 5), description, search_terms, reasoning, confidence.
"""

OPTIMIZE_TEMPLATE = """Optimize the existing Amazon product listing below. Preserve high-performing keywords while improving weak areas.

**ASIN:** {asin}
**Marketplace:** {marketplace_id}

**Current Listing:**
- Title: {existing_title}
- Bullets: {existing_bullets}

**High-Performing Keywords to PRESERVE:** {high_performing_keywords}

**Instructions:**
1. Keep all high-performing keywords in prominent positions (title or early bullets).
2. Improve keyword density and relevance where possible.
3. Enhance persuasiveness and readability of bullets.
4. Optimize search terms (no duplicates from title/bullets).
5. Follow ALL Amazon SP-API constraints.

Return ONLY the JSON object with: title, bullets (array of 5), description, search_terms, reasoning, confidence.
Include a "diff" key with an object showing: {{"title": {{"old": "...", "new": "..."}}, "bullets_changed": [indices]}}.
"""

FIX_VIOLATIONS_TEMPLATE = """The listing you generated has the following constraint violations:

{violations}

Please fix ONLY the violations while keeping the rest of the listing intact.
Return the complete corrected listing as a JSON object with: title, bullets (array of 5), description, search_terms, reasoning, confidence.

Remember:
- Title must be <= 200 characters
- Each bullet must be <= 500 characters
- Description must be <= 2,000 characters
- Search terms must be <= 250 bytes (UTF-8)
- No banned words: sale, discount, best, cheapest, free, #1, guaranteed, top rated, lowest price, limited time

Return ONLY valid JSON, no other text.
"""
