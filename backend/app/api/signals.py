"""Signal endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.signals import Signal
from app.security.auth import require_auth

router = APIRouter()


@router.get("")
async def get_signals(
    symbol: str | None = None,
    status: str | None = None,
    action: str | None = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(require_auth),
):
    """Get signal history with optional filters."""
    query = select(Signal).order_by(desc(Signal.timestamp))

    if symbol:
        query = query.where(Signal.symbol == symbol.upper())
    if status:
        query = query.where(Signal.status == status)
    if action:
        query = query.where(Signal.action == action.upper())

    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    signals = result.scalars().all()

    return [
        {
            "id": s.id,
            "symbol": s.symbol,
            "action": s.action,
            "confidence": s.confidence,
            "claude_approved": s.claude_approved,
            "claude_adjusted_confidence": s.claude_adjusted_confidence,
            "claude_reasoning": s.claude_reasoning,
            "claude_position_sizing": s.claude_position_sizing,
            "risk_approved": s.risk_approved,
            "status": s.status,
            "model_version": s.model_version,
            "timestamp": s.timestamp.isoformat() if s.timestamp else None,
        }
        for s in signals
    ]
