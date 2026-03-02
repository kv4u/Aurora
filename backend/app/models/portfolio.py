"""Portfolio and position tracking models."""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Portfolio(Base):
    __tablename__ = "portfolio_snapshots"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    # Value
    total_equity: Mapped[float] = mapped_column(Float, nullable=False)
    cash: Mapped[float] = mapped_column(Float, nullable=False)
    market_value: Mapped[float] = mapped_column(Float, nullable=False)

    # P&L
    daily_pnl: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    daily_pnl_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    weekly_pnl: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    weekly_pnl_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    monthly_pnl: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    monthly_pnl_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_pnl: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_pnl_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Risk metrics
    max_drawdown_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    peak_equity: Mapped[float] = mapped_column(Float, nullable=False)
    current_drawdown_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Exposure
    total_exposure_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    open_positions_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sector_exposure: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Positions snapshot
    positions: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Trading stats
    trades_today: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    win_rate_30d: Mapped[float | None] = mapped_column(Float, nullable=True)
    sharpe_30d: Mapped[float | None] = mapped_column(Float, nullable=True)
