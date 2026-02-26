"""Portfolio status endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.portfolio import Portfolio

router = APIRouter()


@router.get("")
async def get_portfolio(db: AsyncSession = Depends(get_db)):
    """Get latest portfolio snapshot."""
    result = await db.execute(
        select(Portfolio).order_by(desc(Portfolio.timestamp)).limit(1)
    )
    p = result.scalar_one_or_none()
    if not p:
        return {"message": "No portfolio data yet"}

    return {
        "total_equity": p.total_equity,
        "cash": p.cash,
        "market_value": p.market_value,
        "daily_pnl": p.daily_pnl,
        "daily_pnl_pct": p.daily_pnl_pct,
        "weekly_pnl": p.weekly_pnl,
        "weekly_pnl_pct": p.weekly_pnl_pct,
        "monthly_pnl": p.monthly_pnl,
        "monthly_pnl_pct": p.monthly_pnl_pct,
        "total_exposure_pct": p.total_exposure_pct,
        "open_positions_count": p.open_positions_count,
        "positions": p.positions,
        "sector_exposure": p.sector_exposure,
        "max_drawdown_pct": p.max_drawdown_pct,
        "current_drawdown_pct": p.current_drawdown_pct,
        "peak_equity": p.peak_equity,
        "win_rate_30d": p.win_rate_30d,
        "sharpe_30d": p.sharpe_30d,
        "timestamp": p.timestamp.isoformat(),
    }


@router.get("/equity-curve")
async def get_equity_curve(
    days: int = Query(30, le=365),
    db: AsyncSession = Depends(get_db),
):
    """Get equity curve data for charting."""
    result = await db.execute(
        select(Portfolio.timestamp, Portfolio.total_equity, Portfolio.daily_pnl_pct)
        .order_by(desc(Portfolio.timestamp))
        .limit(days * 24)  # Rough: multiple snapshots per day
    )
    rows = result.all()

    return [
        {
            "timestamp": row.timestamp.isoformat(),
            "equity": row.total_equity,
            "daily_pnl_pct": row.daily_pnl_pct,
        }
        for row in reversed(rows)
    ]
