"""Shared test fixtures for AURORA backend tests."""

import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_db():
    """Mock database session."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    return session


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    client = AsyncMock()
    client.publish = AsyncMock()
    client.get = AsyncMock(return_value=None)
    client.set = AsyncMock()
    return client


@pytest.fixture
def sample_signal():
    """Sample trading signal for tests."""
    return {
        "symbol": "AAPL",
        "action": "BUY",
        "confidence": 0.72,
        "model_version": "v1.0.0",
        "features_snapshot": {
            "rsi_14": 45.3,
            "macd_signal_diff": 0.15,
            "bb_position": 0.55,
            "volume_vs_sma20": 1.2,
            "atr_14": 2.85,
        },
    }


@pytest.fixture
def sample_portfolio():
    """Sample portfolio state for tests."""
    return {
        "total_equity": 10000.0,
        "cash": 8000.0,
        "market_value": 2000.0,
        "daily_pnl": 50.0,
        "daily_pnl_pct": 0.5,
        "open_positions_count": 2,
        "total_exposure_pct": 20.0,
        "peak_equity": 10200.0,
        "current_drawdown_pct": 1.96,
    }
