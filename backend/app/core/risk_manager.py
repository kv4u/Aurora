"""Risk Manager — the most critical module. Has absolute authority over all trades."""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.core.audit_logger import AuditLogger
from app.models.risk_events import RiskEvent

logger = logging.getLogger("aurora.risk")


class CircuitBreakerLevel(str, Enum):
    NONE = "NONE"
    YELLOW = "YELLOW"   # Reduce position sizes 50%
    ORANGE = "ORANGE"   # Halt new trades, allow exits
    RED = "RED"         # Close all positions, halt system


@dataclass
class RiskCheckResult:
    approved: bool
    reason: str = ""
    adjusted_size_pct: float | None = None
    warnings: list[str] = field(default_factory=list)


class RiskManager:
    """Validates every trade against all risk limits. Can veto any trade."""

    # ─── Hard Maximums (cannot be overridden by settings) ───
    HARD_MAX_POSITION_PCT = 10.0
    HARD_MAX_DAILY_LOSS_PCT = 5.0
    HARD_MAX_WEEKLY_LOSS_PCT = 10.0
    HARD_MAX_MONTHLY_LOSS_PCT = 15.0
    HARD_MAX_DRAWDOWN_PCT = 20.0
    HARD_MAX_OPEN_POSITIONS = 15
    HARD_MAX_TRADES_PER_DAY = 20

    def __init__(self, settings: Settings, db: AsyncSession, audit: AuditLogger):
        self.settings = settings
        self.db = db
        self.audit = audit
        self._circuit_breaker = CircuitBreakerLevel.NONE

    @property
    def circuit_breaker_level(self) -> CircuitBreakerLevel:
        return self._circuit_breaker

    # ─── Configuration (clamped to hard maximums) ───

    @property
    def max_position_pct(self) -> float:
        return min(self.settings.max_position_pct, self.HARD_MAX_POSITION_PCT)

    @property
    def max_daily_loss_pct(self) -> float:
        return min(self.settings.max_daily_loss_pct, self.HARD_MAX_DAILY_LOSS_PCT)

    @property
    def max_weekly_loss_pct(self) -> float:
        return min(self.settings.max_weekly_loss_pct, self.HARD_MAX_WEEKLY_LOSS_PCT)

    @property
    def max_monthly_loss_pct(self) -> float:
        return min(self.settings.max_monthly_loss_pct, self.HARD_MAX_MONTHLY_LOSS_PCT)

    @property
    def max_drawdown_pct(self) -> float:
        return min(self.settings.max_drawdown_pct, self.HARD_MAX_DRAWDOWN_PCT)

    @property
    def max_open_positions(self) -> int:
        return min(self.settings.max_open_positions, self.HARD_MAX_OPEN_POSITIONS)

    @property
    def max_trades_per_day(self) -> int:
        return min(self.settings.max_trades_per_day, self.HARD_MAX_TRADES_PER_DAY)

    # ─── Pre-Trade Risk Check (10-step validation) ───

    async def pre_trade_check(
        self,
        symbol: str,
        action: str,
        confidence: float,
        position_pct: float,
        portfolio: dict,
        market_context: dict,
        decision_chain_id: uuid.UUID | None = None,
    ) -> RiskCheckResult:
        """Full pre-trade validation pipeline. Returns approval or rejection."""

        warnings = []

        # 1. Circuit breaker status
        if self._circuit_breaker == CircuitBreakerLevel.RED:
            return RiskCheckResult(False, "RED circuit breaker active — system halted")
        if self._circuit_breaker == CircuitBreakerLevel.ORANGE and action != "SELL":
            return RiskCheckResult(False, "ORANGE circuit breaker — only exits allowed")

        # 2. Minimum confidence threshold
        min_confidence = 0.60
        if confidence < min_confidence:
            return RiskCheckResult(False, f"Confidence {confidence:.1%} below minimum {min_confidence:.1%}")

        # 3. Daily trade limit
        trades_today = portfolio.get("trades_today", 0)
        if trades_today >= self.max_trades_per_day:
            return RiskCheckResult(False, f"Daily trade limit reached ({trades_today}/{self.max_trades_per_day})")

        # 4. Position size check
        adjusted_pct = min(position_pct, self.max_position_pct)
        if self._circuit_breaker == CircuitBreakerLevel.YELLOW:
            adjusted_pct *= 0.5
            warnings.append("YELLOW circuit breaker — position size halved")

        # 5. VIX check
        vix = market_context.get("vix", 0)
        if vix > 35.0:
            return RiskCheckResult(False, f"VIX ({vix:.1f}) exceeds max threshold (35.0)")
        if vix > 25.0:
            adjusted_pct *= 0.5
            warnings.append(f"High VIX ({vix:.1f}) — position size halved")

        # 6. Portfolio exposure check
        total_exposure = portfolio.get("total_exposure_pct", 0)
        max_exposure = 80.0
        if total_exposure + adjusted_pct > max_exposure:
            return RiskCheckResult(False, f"Total exposure ({total_exposure + adjusted_pct:.1f}%) would exceed {max_exposure}%")

        # 7. Open positions check
        open_positions = portfolio.get("open_positions_count", 0)
        if action == "BUY" and open_positions >= self.max_open_positions:
            return RiskCheckResult(False, f"Max open positions reached ({open_positions}/{self.max_open_positions})")

        # 8. Sector exposure check
        sector_exposure = portfolio.get("sector_exposure", {})
        max_sector_pct = 30.0
        # Simplified — would need symbol-to-sector mapping
        for sector, pct in sector_exposure.items():
            if pct > max_sector_pct:
                warnings.append(f"Sector {sector} exposure ({pct:.1f}%) exceeds recommended {max_sector_pct}%")

        # 9. Single stock exposure check
        max_single_stock = 15.0
        # Would check existing position + new allocation
        if adjusted_pct > max_single_stock:
            adjusted_pct = max_single_stock
            warnings.append(f"Position capped to {max_single_stock}% single stock limit")

        # 10. Market timing check
        now = datetime.now(timezone.utc)
        hour = now.hour
        minute = now.minute
        # Market open: ~9:30 ET = 14:30 UTC, Close: ~16:00 ET = 21:00 UTC
        # Skip first 15 min and last 10 min
        market_open_minutes = (hour - 14) * 60 + (minute - 30) if hour >= 14 else 0
        market_close_minutes = (21 - hour) * 60 - minute if hour < 21 else 0

        if 0 < market_open_minutes < 15:
            return RiskCheckResult(False, "No trades in first 15 minutes after open")
        if 0 < market_close_minutes < 10:
            return RiskCheckResult(False, "No trades in last 10 minutes before close")

        # Log the check
        await self.audit.log(
            "risk_check_passed" if True else "risk_check_failed",
            {
                "symbol": symbol,
                "action": action,
                "confidence": confidence,
                "original_size_pct": position_pct,
                "adjusted_size_pct": adjusted_pct,
                "warnings": warnings,
                "circuit_breaker": self._circuit_breaker.value,
            },
            component="risk_manager",
            symbol=symbol,
            decision_chain_id=decision_chain_id,
        )

        return RiskCheckResult(
            approved=True,
            adjusted_size_pct=adjusted_pct,
            warnings=warnings,
        )

    # ─── Circuit Breaker Evaluation ───

    async def evaluate_circuit_breakers(self, portfolio: dict) -> CircuitBreakerLevel:
        """Check portfolio P&L against circuit breaker thresholds."""
        daily_loss = abs(portfolio.get("daily_pnl_pct", 0)) if portfolio.get("daily_pnl_pct", 0) < 0 else 0
        weekly_loss = abs(portfolio.get("weekly_pnl_pct", 0)) if portfolio.get("weekly_pnl_pct", 0) < 0 else 0
        monthly_loss = abs(portfolio.get("monthly_pnl_pct", 0)) if portfolio.get("monthly_pnl_pct", 0) < 0 else 0
        drawdown = portfolio.get("current_drawdown_pct", 0)

        old_level = self._circuit_breaker

        # RED — most severe (check first)
        if monthly_loss > self.max_monthly_loss_pct or drawdown > self.max_drawdown_pct:
            self._circuit_breaker = CircuitBreakerLevel.RED

        # ORANGE
        elif daily_loss > self.max_daily_loss_pct or weekly_loss > self.max_weekly_loss_pct:
            self._circuit_breaker = CircuitBreakerLevel.ORANGE

        # YELLOW
        elif daily_loss > (self.max_daily_loss_pct * 0.5):  # 50% of daily limit
            self._circuit_breaker = CircuitBreakerLevel.YELLOW

        # Clear
        else:
            self._circuit_breaker = CircuitBreakerLevel.NONE

        # Log level changes
        if self._circuit_breaker != old_level:
            logger.warning(
                "Circuit breaker changed: %s → %s",
                old_level.value, self._circuit_breaker.value,
            )
            event = RiskEvent(
                level=self._circuit_breaker.value,
                trigger_reason=f"daily={daily_loss:.2f}% weekly={weekly_loss:.2f}% monthly={monthly_loss:.2f}% drawdown={drawdown:.2f}%",
                trigger_value=max(daily_loss, weekly_loss, monthly_loss, drawdown),
                threshold_value=self.max_daily_loss_pct,
                action_taken=self._circuit_breaker_action(self._circuit_breaker),
                details={
                    "daily_loss_pct": daily_loss,
                    "weekly_loss_pct": weekly_loss,
                    "monthly_loss_pct": monthly_loss,
                    "drawdown_pct": drawdown,
                    "old_level": old_level.value,
                    "new_level": self._circuit_breaker.value,
                },
            )
            self.db.add(event)

            await self.audit.log(
                "circuit_breaker_activated",
                event.details,
                component="risk_manager",
                severity="CRITICAL" if self._circuit_breaker == CircuitBreakerLevel.RED else "WARNING",
            )

        return self._circuit_breaker

    def _circuit_breaker_action(self, level: CircuitBreakerLevel) -> str:
        actions = {
            CircuitBreakerLevel.NONE: "normal_trading",
            CircuitBreakerLevel.YELLOW: "reduce_position_sizes_50pct",
            CircuitBreakerLevel.ORANGE: "halt_new_trades_allow_exits",
            CircuitBreakerLevel.RED: "close_all_positions_halt_system",
        }
        return actions[level]

    # ─── Emergency Stop ───

    async def emergency_stop(self, reason: str = "Manual emergency stop") -> None:
        """Immediately activate RED circuit breaker."""
        self._circuit_breaker = CircuitBreakerLevel.RED
        logger.critical("EMERGENCY STOP ACTIVATED: %s", reason)

        event = RiskEvent(
            level="RED",
            trigger_reason=reason,
            trigger_value=0.0,
            threshold_value=0.0,
            action_taken="emergency_close_all_halt_system",
            details={"manual": True, "reason": reason},
        )
        self.db.add(event)

        await self.audit.log(
            "emergency_stop_activated",
            {"reason": reason},
            component="risk_manager",
            severity="CRITICAL",
        )
