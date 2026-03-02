"""Trading signal models."""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Signal(Base):
    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    decision_chain_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), default=uuid.uuid4, index=True
    )

    symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(10), nullable=False)  # BUY, SELL, HOLD
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)

    # Full feature snapshot for audit
    features_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Claude analyst review (filled after review)
    claude_approved: Mapped[bool | None] = mapped_column(nullable=True)
    claude_adjusted_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    claude_reasoning: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    claude_risk_flags: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    claude_position_sizing: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Risk check result
    risk_approved: Mapped[bool | None] = mapped_column(nullable=True)
    risk_rejection_reason: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Status tracking
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending, reviewed, approved, rejected, executed

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_signals_symbol_ts", "symbol", "timestamp"),
        Index("ix_signals_status", "status"),
    )
