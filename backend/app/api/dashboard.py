"""Dashboard API endpoints — at-a-glance system status."""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.database import get_db
from app.models.portfolio import Portfolio
from app.models.signals import Signal
from app.models.trades import Trade
from app.security.auth import require_auth

logger = logging.getLogger("aurora.dashboard")

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

    # Recent signals (last 20)
    signals_result = await db.execute(
        select(Signal).order_by(desc(Signal.timestamp)).limit(20)
    )
    recent_signals = signals_result.scalars().all()

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
            "open_positions_count": portfolio.open_positions_count if portfolio else 0,
            "positions": portfolio.positions if portfolio else {},
        },
        "recent_signals": [
            {
                "id": s.id,
                "symbol": s.symbol,
                "action": s.action,
                "confidence": s.confidence,
                "status": s.status,
                "claude_approved": s.claude_approved,
                "claude_reasoning": (s.claude_reasoning or "")[:200] if s.claude_reasoning else None,
                "created_at": s.timestamp.isoformat() if s.timestamp else None,
            }
            for s in recent_signals
        ],
        "signals_today": len([s for s in recent_signals if s.action != "HOLD"]),
        "active_trades": active_trades.scalar() or 0,
        "max_positions": 8,
        "system_status": "online",
        "circuit_breaker": "NONE",
    }


@router.post("/run-cycle")
async def run_manual_cycle(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _user: str = Depends(require_auth),
):
    """Manually trigger one trading cycle (for testing outside market hours).

    Runs: ingest -> indicators -> signals -> Claude review -> risk check -> execute
    """
    from app.api.emergency import is_halted
    from app.core.scheduler import TradingLoop

    if is_halted():
        return {"error": "Emergency halt is active. Resume trading first."}

    loop = TradingLoop(settings, db)
    try:
        logger.info("Manual trading cycle triggered")
        results = await loop.run_cycle()
        return results
    finally:
        await loop.cleanup()
