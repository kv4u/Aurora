"""Tests for JWT authentication and security layer."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.security.auth import (
    create_access_token,
    hash_password,
    verify_password,
    verify_token,
)


# ─── Token Tests ───


class TestJWTTokens:
    """JWT token creation and verification."""

    SECRET = "test-secret-key-aurora-2024"

    def test_create_and_verify_token(self):
        """Token round-trip: create → verify → get username."""
        token = create_access_token(
            data={"sub": "keyva"}, secret=self.SECRET, expires_minutes=30
        )
        username = verify_token(token, self.SECRET)
        assert username == "keyva"

    def test_verify_token_wrong_secret(self):
        """Token verified with wrong secret returns None."""
        token = create_access_token(
            data={"sub": "keyva"}, secret=self.SECRET
        )
        result = verify_token(token, "wrong-secret")
        assert result is None

    def test_verify_token_expired(self):
        """Expired token returns None."""
        token = create_access_token(
            data={"sub": "keyva"}, secret=self.SECRET, expires_minutes=-1
        )
        result = verify_token(token, self.SECRET)
        assert result is None

    def test_verify_token_no_subject(self):
        """Token without 'sub' claim returns None."""
        token = create_access_token(
            data={"role": "admin"}, secret=self.SECRET
        )
        result = verify_token(token, self.SECRET)
        assert result is None

    def test_verify_token_invalid_string(self):
        """Garbage token returns None."""
        result = verify_token("not.a.valid.jwt", self.SECRET)
        assert result is None

    def test_verify_token_empty_string(self):
        """Empty token returns None."""
        result = verify_token("", self.SECRET)
        assert result is None

    def test_token_contains_expiry(self):
        """Token payload includes exp claim."""
        from jose import jwt

        token = create_access_token(
            data={"sub": "keyva"}, secret=self.SECRET, expires_minutes=60
        )
        payload = jwt.decode(token, self.SECRET, algorithms=["HS256"])
        assert "exp" in payload
        assert payload["sub"] == "keyva"


# ─── Password Tests ───


class TestPasswordHashing:
    """Bcrypt password hashing and verification."""

    def test_hash_and_verify(self):
        """Password round-trip: hash → verify."""
        hashed = hash_password("my-secure-password-123")
        assert verify_password("my-secure-password-123", hashed)

    def test_wrong_password_fails(self):
        """Wrong password doesn't verify."""
        hashed = hash_password("correct-password")
        assert not verify_password("wrong-password", hashed)

    def test_hash_is_different_each_time(self):
        """Bcrypt produces unique hashes (salt)."""
        h1 = hash_password("same-password")
        h2 = hash_password("same-password")
        assert h1 != h2  # Different salts

    def test_hash_starts_with_bcrypt_prefix(self):
        """Bcrypt hashes start with $2b$."""
        hashed = hash_password("test")
        assert hashed.startswith("$2b$")

    def test_empty_password_still_hashes(self):
        """Empty password can be hashed (app validates elsewhere)."""
        hashed = hash_password("")
        assert verify_password("", hashed)


# ─── Rate Limiter Tests ───


class TestRateLimiter:
    """In-memory rate limiter middleware."""

    @pytest.fixture
    def limiter(self):
        from app.security.rate_limiter import RateLimiter

        # Create a mock app
        mock_app = AsyncMock()
        return RateLimiter(mock_app, max_requests=5, window_seconds=60)

    def _make_request(self, path: str = "/api/v1/dashboard", client_ip: str = "127.0.0.1"):
        """Create a mock Starlette Request."""
        request = MagicMock()
        request.url.path = path
        request.client.host = client_ip
        return request

    @pytest.mark.asyncio
    async def test_allows_requests_under_limit(self, limiter):
        """Requests under the limit pass through."""
        request = self._make_request()
        call_next = AsyncMock(return_value=MagicMock())

        for _ in range(5):
            await limiter.dispatch(request, call_next)

        assert call_next.call_count == 5

    @pytest.mark.asyncio
    async def test_blocks_requests_over_limit(self, limiter):
        """Requests over the limit raise 429."""
        from fastapi import HTTPException

        request = self._make_request()
        call_next = AsyncMock(return_value=MagicMock())

        # Fill the bucket
        for _ in range(5):
            await limiter.dispatch(request, call_next)

        # Next should be blocked
        with pytest.raises(HTTPException) as exc_info:
            await limiter.dispatch(request, call_next)
        assert exc_info.value.status_code == 429

    @pytest.mark.asyncio
    async def test_health_endpoint_bypasses_limit(self, limiter):
        """Health check endpoint is never rate-limited."""
        request = self._make_request(path="/health")
        call_next = AsyncMock(return_value=MagicMock())

        for _ in range(10):
            await limiter.dispatch(request, call_next)

        assert call_next.call_count == 10  # All passed

    @pytest.mark.asyncio
    async def test_different_ips_have_separate_limits(self, limiter):
        """Each IP has its own rate limit bucket."""
        call_next = AsyncMock(return_value=MagicMock())

        for _ in range(5):
            await limiter.dispatch(self._make_request(client_ip="10.0.0.1"), call_next)
            await limiter.dispatch(self._make_request(client_ip="10.0.0.2"), call_next)

        assert call_next.call_count == 10  # 5 each


# ─── WebSocket Manager Tests ───


class TestConnectionManager:
    """WebSocket connection manager."""

    @pytest.fixture
    def manager(self):
        from app.api.ws import ConnectionManager
        return ConnectionManager()

    @pytest.mark.asyncio
    async def test_connect_adds_websocket(self, manager):
        """Connecting adds to active connections."""
        ws = AsyncMock()
        await manager.connect(ws)
        assert ws in manager.active_connections
        ws.accept.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_disconnect_removes_websocket(self, manager):
        """Disconnecting removes from active connections."""
        ws = AsyncMock()
        await manager.connect(ws)
        manager.disconnect(ws)
        assert ws not in manager.active_connections

    @pytest.mark.asyncio
    async def test_broadcast_sends_to_all(self, manager):
        """Broadcast sends message to all connected clients."""
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        await manager.connect(ws1)
        await manager.connect(ws2)

        await manager.broadcast({"type": "test", "payload": {}})

        ws1.send_json.assert_awaited_once_with({"type": "test", "payload": {}})
        ws2.send_json.assert_awaited_once_with({"type": "test", "payload": {}})

    @pytest.mark.asyncio
    async def test_broadcast_removes_dead_connections(self, manager):
        """Dead connections are cleaned up on broadcast."""
        ws_alive = AsyncMock()
        ws_dead = AsyncMock()
        ws_dead.send_json.side_effect = Exception("Connection closed")

        await manager.connect(ws_alive)
        await manager.connect(ws_dead)

        await manager.broadcast({"type": "test", "payload": {}})

        assert ws_alive in manager.active_connections
        assert ws_dead not in manager.active_connections

    @pytest.mark.asyncio
    async def test_send_portfolio_update(self, manager):
        """Portfolio update sends correct message type."""
        ws = AsyncMock()
        await manager.connect(ws)

        await manager.send_portfolio_update({"equity": 10000})

        ws.send_json.assert_awaited_once_with({
            "type": "portfolio_update",
            "payload": {"equity": 10000},
        })

    @pytest.mark.asyncio
    async def test_send_risk_alert(self, manager):
        """Risk alert sends correct message type."""
        ws = AsyncMock()
        await manager.connect(ws)

        await manager.send_risk_alert({"level": "YELLOW", "reason": "drawdown"})

        ws.send_json.assert_awaited_once_with({
            "type": "risk_alert",
            "payload": {"level": "YELLOW", "reason": "drawdown"},
        })

    @pytest.mark.asyncio
    async def test_send_circuit_breaker(self, manager):
        """Circuit breaker sends correct message type."""
        ws = AsyncMock()
        await manager.connect(ws)

        await manager.send_circuit_breaker({"level": "RED"})

        ws.send_json.assert_awaited_once_with({
            "type": "circuit_breaker",
            "payload": {"level": "RED"},
        })
