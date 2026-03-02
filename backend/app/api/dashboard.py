"""Dashboard API endpoints — at-a-glance system status."""

from fastapi import APIRouter, Depends
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.portfolio import Portfolio
from app.models.signals import Signal
from app.models.trades import Trade
from app.security.auth import require_auth

router = APIRouter()


@router.get("")
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(require_auth),
):
    """Get dashboard overview data."""

    # Latest portfolio snapshot
    result = await db.execute(
        select(Portfolio).order_by(desc(Portfolio.timestamp)).limit(1)
    )
    portfolio = result.scalar_one_or_none()

    # Recent signals count (last 24h)
    signals_count = await db.execute(
        select(func.count(Signal.id)).where(Signal.status != "pending")
    )

    # Active trades
    active_trades = await db.execute(
        select(func.count(Trade.id)).where(Trade.status.in_(["pending", "filled"]))
    )

    return {
        "portfolio": {
            "total_equity": portfolio.total_equity if portfolio else 0,
            "cash": portfolio.cash if portfolio else 0,
            "daily_pnl": portfolio.daily_pnl if portfolio else 0,
            "daily_pnl_pct": portfolio.daily_pnl_pct if portfolio else 0,
            "total_exposure_pct": portfolio.total_exposure_pct if portfolio else 0,
            "open_positions": portfolio.open_positions_count if portfolio else 0,
        },
        "signals_today": signals_count.scalar() or 0,
        "active_trades": active_trades.scalar() or 0,
        "system_status": "online",
        "circuit_breaker": "NONE",
    }
