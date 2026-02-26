"""Trade history endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.trades import Trade

router = APIRouter()


@router.get("")
async def get_trades(
    symbol: str | None = None,
    status: str | None = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """Get trade history with optional filters."""
    query = select(Trade).order_by(desc(Trade.placed_at))

    if symbol:
        query = query.where(Trade.symbol == symbol.upper())
    if status:
        query = query.where(Trade.status == status)

    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    trades = result.scalars().all()

    return [
        {
            "id": t.id,
            "symbol": t.symbol,
            "side": t.side,
            "shares": t.shares,
            "entry_price": t.entry_price,
            "fill_price": t.fill_price,
            "exit_price": t.exit_price,
            "stop_price": t.stop_price,
            "target_price": t.target_price,
            "realized_pnl": t.realized_pnl,
            "realized_pnl_pct": t.realized_pnl_pct,
            "ml_confidence": t.ml_confidence,
            "claude_confidence": t.claude_confidence,
            "claude_reasoning": t.claude_reasoning,
            "status": t.status,
            "exit_reason": t.exit_reason,
            "placed_at": t.placed_at.isoformat() if t.placed_at else None,
            "filled_at": t.filled_at.isoformat() if t.filled_at else None,
            "closed_at": t.closed_at.isoformat() if t.closed_at else None,
        }
        for t in trades
    ]


@router.get("/{trade_id}")
async def get_trade(trade_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single trade with full details."""
    result = await db.execute(select(Trade).where(Trade.id == trade_id))
    trade = result.scalar_one_or_none()
    if not trade:
        return {"error": "Trade not found"}

    return {
        "id": trade.id,
        "decision_chain_id": str(trade.decision_chain_id),
        "symbol": trade.symbol,
        "side": trade.side,
        "shares": trade.shares,
        "entry_price": trade.entry_price,
        "fill_price": trade.fill_price,
        "exit_price": trade.exit_price,
        "stop_price": trade.stop_price,
        "target_price": trade.target_price,
        "realized_pnl": trade.realized_pnl,
        "realized_pnl_pct": trade.realized_pnl_pct,
        "ml_confidence": trade.ml_confidence,
        "claude_confidence": trade.claude_confidence,
        "claude_reasoning": trade.claude_reasoning,
        "allocation_pct": trade.allocation_pct,
        "dollar_amount": trade.dollar_amount,
        "status": trade.status,
        "exit_reason": trade.exit_reason,
        "placed_at": trade.placed_at.isoformat() if trade.placed_at else None,
        "filled_at": trade.filled_at.isoformat() if trade.filled_at else None,
        "closed_at": trade.closed_at.isoformat() if trade.closed_at else None,
        "metadata": trade.extra_data,
    }
