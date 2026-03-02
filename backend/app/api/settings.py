"""Runtime settings endpoints."""

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.config import get_settings
from app.security.auth import require_auth

logger = logging.getLogger("aurora.api.settings")

router = APIRouter()


@router.get("")
async def get_settings_endpoint(_user: str = Depends(require_auth)):
    """Get current system settings (non-sensitive)."""
    settings = get_settings()
    return {
        "mode": settings.aurora_mode,
        "watchlist": settings.watchlist_symbols,
        "risk_limits": {
            "max_position_pct": settings.max_position_pct,
            "max_daily_loss_pct": settings.max_daily_loss_pct,
            "max_weekly_loss_pct": settings.max_weekly_loss_pct,
            "max_monthly_loss_pct": settings.max_monthly_loss_pct,
            "max_drawdown_pct": settings.max_drawdown_pct,
            "max_open_positions": settings.max_open_positions,
            "max_trades_per_day": settings.max_trades_per_day,
        },
        "trading_hours": {
            "start": settings.trading_start_hour,
            "end": settings.trading_end_hour,
        },
        "signal_interval_minutes": settings.signal_interval_minutes,
        "claude_model": settings.claude_model,
        "claude_max_reviews_per_day": settings.claude_max_reviews_per_day,
    }


# ─── Runtime Settings Update ───
# These are in-memory overrides that persist until restart.
# For permanent changes, modify .env and restart.

_runtime_overrides: dict = {}


class SettingsUpdate(BaseModel):
    """Updateable settings — only safe, non-sensitive fields."""

    mode: str | None = None
    max_position_pct: float | None = None
    max_daily_loss_pct: float | None = None
    max_open_positions: int | None = None
    max_trades_per_day: int | None = None


@router.put("")
async def update_settings(
    updates: SettingsUpdate,
    _user: str = Depends(require_auth),
):
    """Update runtime settings (non-persistent — resets on restart).

    Use for quick adjustments during trading. For permanent changes,
    edit .env and restart.
    """
    settings = get_settings()
    applied = {}

    if updates.mode is not None and updates.mode in ("paper", "live"):
        settings.aurora_mode = updates.mode
        applied["mode"] = updates.mode

    if updates.max_position_pct is not None:
        # Respect hard caps from risk manager
        val = min(updates.max_position_pct, 10.0)
        settings.max_position_pct = val
        applied["max_position_pct"] = val

    if updates.max_daily_loss_pct is not None:
        val = min(updates.max_daily_loss_pct, 5.0)
        settings.max_daily_loss_pct = val
        applied["max_daily_loss_pct"] = val

    if updates.max_open_positions is not None:
        val = min(updates.max_open_positions, 15)
        settings.max_open_positions = val
        applied["max_open_positions"] = val

    if updates.max_trades_per_day is not None:
        val = min(updates.max_trades_per_day, 20)
        settings.max_trades_per_day = val
        applied["max_trades_per_day"] = val

    logger.info("Settings updated: %s", applied)
    _runtime_overrides.update(applied)

    return {"updated": applied, "note": "Runtime override — resets on restart"}
