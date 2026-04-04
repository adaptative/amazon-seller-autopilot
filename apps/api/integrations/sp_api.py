"""Amazon SP-API integration utilities."""

import os

import httpx
import structlog

logger = structlog.get_logger()

SP_API_CLIENT_ID = os.getenv("SP_API_CLIENT_ID", "")
SP_API_CLIENT_SECRET = os.getenv("SP_API_CLIENT_SECRET", "")
LWA_TOKEN_URL = "https://api.amazon.com/auth/o2/token"

MARKETPLACE_MAP = {
    "ATVPDKIKX0DER": {
        "name": "United States",
        "domain": "amazon.com",
        "region": "na",
        "flag": "\U0001F1FA\U0001F1F8",
        "auth_url": "https://sellercentral.amazon.com/apps/authorize/consent",
    },
    "A1F83G8C2ARO7P": {
        "name": "United Kingdom",
        "domain": "amazon.co.uk",
        "region": "eu",
        "flag": "\U0001F1EC\U0001F1E7",
        "auth_url": "https://sellercentral-europe.amazon.com/apps/authorize/consent",
    },
    "A1PA6795UKMFR9": {
        "name": "Germany",
        "domain": "amazon.de",
        "region": "eu",
        "flag": "\U0001F1E9\U0001F1EA",
        "auth_url": "https://sellercentral-europe.amazon.com/apps/authorize/consent",
    },
    "A1VC38T7YXB528": {
        "name": "Japan",
        "domain": "amazon.co.jp",
        "region": "fe",
        "flag": "\U0001F1EF\U0001F1F5",
        "auth_url": "https://sellercentral-japan.amazon.com/apps/authorize/consent",
    },
    "A2EUQ1WTGCTBG2": {
        "name": "Canada",
        "domain": "amazon.ca",
        "region": "na",
        "flag": "\U0001F1E8\U0001F1E6",
        "auth_url": "https://sellercentral.amazon.com/apps/authorize/consent",
    },
    "A21TJRUUN4KGV": {
        "name": "India",
        "domain": "amazon.in",
        "region": "eu",
        "flag": "\U0001F1EE\U0001F1F3",
        "auth_url": "https://sellercentral.amazon.in/apps/authorize/consent",
    },
}


async def exchange_auth_code(code: str) -> dict:
    """Exchange SP-API authorization code for tokens via Amazon LWA."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            LWA_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": SP_API_CLIENT_ID,
                "client_secret": SP_API_CLIENT_SECRET,
            },
        )
        response.raise_for_status()
        return response.json()


async def refresh_access_token(refresh_token: str) -> dict:
    """Refresh an SP-API access token."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            LWA_TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": SP_API_CLIENT_ID,
                "client_secret": SP_API_CLIENT_SECRET,
            },
        )
        response.raise_for_status()
        return response.json()
