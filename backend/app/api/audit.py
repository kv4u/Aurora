"""Audit trail endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.audit_log import AuditLog

router = APIRouter()


@router.get("")
async def get_audit_log(
    event_type: str | None = None,
    severity: str | None = None,
    symbol: str | None = None,
    limit: int = Query(100, le=500),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """Get audit log entries with optional filters."""
    query = select(AuditLog).order_by(desc(AuditLog.timestamp))

    if event_type:
        query = query.where(AuditLog.event_type == event_type)
    if severity:
        query = query.where(AuditLog.severity == severity)
    if symbol:
        query = query.where(AuditLog.symbol == symbol.upper())

    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    entries = result.scalars().all()

    return [
        {
            "id": e.id,
            "timestamp": e.timestamp.isoformat() if e.timestamp else None,
            "event_type": e.event_type,
            "severity": e.severity,
            "component": e.component,
            "symbol": e.symbol,
            "details": e.details,
            "decision_chain_id": str(e.decision_chain_id) if e.decision_chain_id else None,
        }
        for e in entries
    ]


@router.get("/chain/{chain_id}")
async def get_decision_chain(chain_id: str, db: AsyncSession = Depends(get_db)):
    """Get all audit entries for a decision chain."""
    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.decision_chain_id == chain_id)
        .order_by(AuditLog.timestamp)
    )
    entries = result.scalars().all()

    return [
        {
            "id": e.id,
            "timestamp": e.timestamp.isoformat() if e.timestamp else None,
            "event_type": e.event_type,
            "severity": e.severity,
            "component": e.component,
            "details": e.details,
        }
        for e in entries
    ]
