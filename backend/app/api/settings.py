"""Runtime settings endpoints."""

from fastapi import APIRouter

from app.config import get_settings

router = APIRouter()


@router.get("")
async def get_settings_endpoint():
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
