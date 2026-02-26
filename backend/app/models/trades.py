"""Trade record models."""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    decision_chain_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    signal_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)

    # Order info
    order_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    side: Mapped[str] = mapped_column(String(10), nullable=False)  # buy, sell
    shares: Mapped[int] = mapped_column(Integer, nullable=False)

    # Prices
    entry_price: Mapped[float] = mapped_column(Float, nullable=False)
    stop_price: Mapped[float] = mapped_column(Float, nullable=False)
    target_price: Mapped[float] = mapped_column(Float, nullable=False)
    fill_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    exit_price: Mapped[float | None] = mapped_column(Float, nullable=True)

    # P&L
    realized_pnl: Mapped[float | None] = mapped_column(Float, nullable=True)
    realized_pnl_pct: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Confidence
    ml_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    claude_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    claude_reasoning: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # Position sizing details
    allocation_pct: Mapped[float] = mapped_column(Float, nullable=False)
    dollar_amount: Mapped[float] = mapped_column(Float, nullable=False)

    # Status & lifecycle
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending, filled, partial, closed, cancelled, expired
    exit_reason: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # target_hit, stop_loss, manual, emergency, timeout

    # Timestamps
    placed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    filled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Extra data
    extra_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        Index("ix_trades_symbol_placed", "symbol", "placed_at"),
        Index("ix_trades_status", "status"),
    )
