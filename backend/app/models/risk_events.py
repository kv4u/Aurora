"""Risk event and circuit breaker models."""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Float, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RiskEvent(Base):
    __tablename__ = "risk_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    # Circuit breaker info
    level: Mapped[str] = mapped_column(
        String(10), nullable=False
    )  # YELLOW, ORANGE, RED
    trigger_reason: Mapped[str] = mapped_column(String(200), nullable=False)
    trigger_value: Mapped[float] = mapped_column(Float, nullable=False)
    threshold_value: Mapped[float] = mapped_column(Float, nullable=False)

    # Action taken
    action_taken: Mapped[str] = mapped_column(String(100), nullable=False)

    # Resolution
    resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # auto, manual

    # Extra data
    details: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
