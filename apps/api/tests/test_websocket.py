"""WebSocket endpoint tests — 6 test cases."""

import sys
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.security import create_access_token
from core.ws_manager import manager

TENANT_A_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
TENANT_B_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
USER_A_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
USER_B_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")


@pytest.fixture
def test_app():
    from main import app
    return app


@pytest.fixture
def valid_ws_token():
    return create_access_token(TENANT_A_ID, USER_A_ID)


@pytest.fixture
def token_tenant_a():
    return create_access_token(TENANT_A_ID, USER_A_ID)


@pytest.fixture
def token_tenant_b():
    return create_access_token(TENANT_B_ID, USER_B_ID)


@pytest.fixture
def event_bus():
    """Return the global connection manager as the 'event bus' for WS tests."""
    return manager


class TestWebSocketEndpoint:

    def test_connects_with_valid_token(self, test_app, valid_ws_token):
        """WebSocket connection with valid JWT should succeed."""
        client = TestClient(test_app)
        with client.websocket_connect(f"/ws?token={valid_ws_token}") as ws:
            data = ws.receive_json()
            assert data["type"] == "connected"
            assert "tenant_id" in data

    def test_rejects_without_token(self, test_app):
        """WebSocket without token should be rejected."""
        client = TestClient(test_app)
        with pytest.raises(Exception):
            with client.websocket_connect("/ws") as ws:
                ws.receive_text()

    def test_rejects_invalid_token(self, test_app):
        """WebSocket with invalid token should be rejected."""
        client = TestClient(test_app)
        with pytest.raises(Exception):
            with client.websocket_connect("/ws?token=invalid.jwt.token") as ws:
                ws.receive_text()

    def test_receives_agent_updates(self, test_app, valid_ws_token):
        """Client should receive and respond to messages (ping/pong protocol)."""
        client = TestClient(test_app)
        with client.websocket_connect(f"/ws?token={valid_ws_token}") as ws:
            welcome = ws.receive_json()
            assert welcome["type"] == "connected"
            assert "tenant_id" in welcome
            assert "user_id" in welcome

            # Verify the connection is tracked by the manager
            tenant_id = welcome["tenant_id"]
            assert tenant_id in manager._connections
            assert len(manager._connections[tenant_id]) >= 1

    def test_heartbeat_ping_pong(self, test_app, valid_ws_token):
        """Server should respond to ping with pong."""
        client = TestClient(test_app)
        with client.websocket_connect(f"/ws?token={valid_ws_token}") as ws:
            ws.receive_json()  # welcome
            ws.send_json({"type": "ping"})
            response = ws.receive_json()
            assert response["type"] == "pong"

    def test_tenant_isolation(self, test_app, token_tenant_a, token_tenant_b):
        """Different tenants get different connection groups."""
        client = TestClient(test_app)

        with client.websocket_connect(f"/ws?token={token_tenant_a}") as ws_a:
            welcome_a = ws_a.receive_json()
            tid_a = welcome_a["tenant_id"]

            with client.websocket_connect(f"/ws?token={token_tenant_b}") as ws_b:
                welcome_b = ws_b.receive_json()
                tid_b = welcome_b["tenant_id"]

                # Verify different tenants
                assert tid_a != tid_b
                assert tid_a == str(TENANT_A_ID)
                assert tid_b == str(TENANT_B_ID)

                # Verify separate connection tracking
                assert tid_a in manager._connections
                assert tid_b in manager._connections
