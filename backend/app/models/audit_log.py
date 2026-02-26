"""Audit logging model — records every system decision."""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(10), nullable=False, default="INFO")
    component: Mapped[str] = mapped_column(String(30), nullable=False)
    symbol: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)

    # Full structured payload
    details: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Links related events in a decision chain
    decision_chain_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )

    __table_args__ = (
        Index("ix_audit_log_ts_type", "timestamp", "event_type"),
        Index("ix_audit_log_severity", "severity"),
    )
