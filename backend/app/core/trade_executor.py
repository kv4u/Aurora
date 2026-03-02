"""Trade Executor — handles order placement, lifecycle, and position sizing."""

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.core.audit_logger import AuditLogger
from app.core.claude_analyst import AnalystReview
from app.core.risk_manager import RiskManager
from app.models.trades import Trade

logger = logging.getLogger("aurora.executor")


@dataclass
class PositionSize:
    shares: int
    dollar_amount: float
    allocation_pct: float
    limit_price: float
    stop_price: float
    target_price: float
    risk_reward_ratio: float


class TradeExecutor:
    """Handles order lifecycle: size → risk check → place → monitor → close."""

    def __init__(
        self,
        settings: Settings,
        db: AsyncSession,
        risk_manager: RiskManager,
        audit: AuditLogger,
    ):
        self.settings = settings
        self.db = db
        self.risk = risk_manager
        self.audit = audit
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.settings.alpaca_base_url,
                headers={
                    "APCA-API-KEY-ID": self.settings.alpaca_api_key.get_secret_value(),
                    "APCA-API-SECRET-KEY": self.settings.alpaca_secret_key.get_secret_value(),
                },
                timeout=30.0,
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    # ─── Position Sizing ───

    def calculate_position(
        self,
        signal: dict,
        review: AnalystReview,
        portfolio: dict,
        allocation_pct: float,
    ) -> PositionSize:
        """Calculate position size using ATR-based stops and Kelly-inspired sizing."""
        portfolio_value = portfolio.get("total_equity", 0)
        current_price = signal.get("current_price", 0)
        features = signal.get("features_snapshot", {})
        atr = features.get("atr_14", current_price * 0.02)  # Fallback: 2% of price

        # Apply Claude sizing recommendation
        sizing_multiplier = {
            "conservative": 0.5,
            "normal": 1.0,
            "aggressive": 1.25,
        }.get(review.position_sizing, 0.5)

        final_pct = allocation_pct * sizing_multiplier

        # Calculate dollar amount and shares
        dollar_amount = portfolio_value * (final_pct / 100)
        shares = int(dollar_amount / current_price) if current_price > 0 else 0

        if shares <= 0:
            shares = 1  # Minimum 1 share

        # ATR-based stop and target
        stop_price = round(current_price - (2.0 * atr), 2)
        target_price = round(current_price + (3.0 * atr), 2)
        limit_price = round(current_price * 1.001, 2)  # Tiny premium for fill

        risk = current_price - stop_price
        reward = target_price - current_price
        rr_ratio = round(reward / risk, 2) if risk > 0 else 0

        return PositionSize(
            shares=shares,
            dollar_amount=round(shares * current_price, 2),
            allocation_pct=round(final_pct, 2),
            limit_price=limit_price,
            stop_price=stop_price,
            target_price=target_price,
            risk_reward_ratio=rr_ratio,
        )

    # ─── Order Execution ───

    async def execute(
        self,
        signal: dict,
        review: AnalystReview,
        portfolio: dict,
        market_context: dict,
        decision_chain_id: uuid.UUID,
    ) -> Trade | None:
        """Full execution pipeline: size → risk check → place bracket order."""

        # 1. Pre-trade risk check
        risk_result = await self.risk.pre_trade_check(
            symbol=signal["symbol"],
            action=signal["action"],
            confidence=review.adjusted_confidence,
            position_pct=self.settings.max_position_pct,
            portfolio=portfolio,
            market_context=market_context,
            decision_chain_id=decision_chain_id,
        )

        if not risk_result.approved:
            await self.audit.log_decision_chain(
                decision_chain_id,
                "trade_rejected_risk",
                {"symbol": signal["symbol"], "reason": risk_result.reason},
                component="trade_executor",
                symbol=signal["symbol"],
            )
            logger.info("Trade rejected by risk manager: %s — %s", signal["symbol"], risk_result.reason)
            return None

        # 2. Calculate position size
        position = self.calculate_position(
            signal, review, portfolio, risk_result.adjusted_size_pct or self.settings.max_position_pct,
        )

        if position.shares <= 0:
            logger.warning("Position sizing resulted in 0 shares for %s", signal["symbol"])
            return None

        # 3. Place bracket order via Alpaca
        try:
            order_data = await self._place_bracket_order(signal, position)
        except Exception as e:
            logger.error("Order placement failed for %s: %s", signal["symbol"], e)
            await self.audit.log_decision_chain(
                decision_chain_id,
                "trade_placement_failed",
                {"symbol": signal["symbol"], "error": str(e)},
                component="trade_executor",
                symbol=signal["symbol"],
                severity="WARNING",
            )
            return None

        # 4. Record trade
        trade = Trade(
            decision_chain_id=decision_chain_id,
            signal_id=signal.get("id", 0),
            order_id=order_data.get("id", "unknown"),
            symbol=signal["symbol"],
            side="buy" if signal["action"] == "BUY" else "sell",
            shares=position.shares,
            entry_price=position.limit_price,
            stop_price=position.stop_price,
            target_price=position.target_price,
            ml_confidence=signal["confidence"],
            claude_confidence=review.adjusted_confidence,
            claude_reasoning=review.reasoning,
            allocation_pct=position.allocation_pct,
            dollar_amount=position.dollar_amount,
            status="pending",
        )
        self.db.add(trade)
        await self.db.flush()

        # 5. Audit log
        await self.audit.log_decision_chain(
            decision_chain_id,
            "trade_placed",
            {
                "symbol": signal["symbol"],
                "side": trade.side,
                "shares": position.shares,
                "entry_price": position.limit_price,
                "stop_price": position.stop_price,
                "target_price": position.target_price,
                "allocation_pct": position.allocation_pct,
                "risk_reward": position.risk_reward_ratio,
                "order_id": trade.order_id,
            },
            component="trade_executor",
            symbol=signal["symbol"],
        )

        logger.info(
            "Trade placed: %s %s %d shares @ $%.2f (stop: $%.2f, target: $%.2f)",
            signal["action"], signal["symbol"], position.shares,
            position.limit_price, position.stop_price, position.target_price,
        )

        return trade

    async def _place_bracket_order(self, signal: dict, position: PositionSize) -> dict:
        """Place a bracket order (entry + stop-loss + take-profit) via Alpaca."""
        order_payload = {
            "symbol": signal["symbol"],
            "qty": str(position.shares),
            "side": "buy" if signal["action"] == "BUY" else "sell",
            "type": "limit",
            "limit_price": str(position.limit_price),
            "time_in_force": "day",
            "order_class": "bracket",
            "stop_loss": {"stop_price": str(position.stop_price)},
            "take_profit": {"limit_price": str(position.target_price)},
        }

        resp = await self.client.post("/v2/orders", json=order_payload)
        resp.raise_for_status()
        return resp.json()

    # ─── Emergency Actions ───

    async def cancel_all_orders(self) -> int:
        """Cancel all open orders."""
        resp = await self.client.delete("/v2/orders")
        resp.raise_for_status()
        cancelled = resp.json()
        count = len(cancelled) if isinstance(cancelled, list) else 0

        await self.audit.log(
            "all_orders_cancelled",
            {"count": count},
            component="trade_executor",
            severity="WARNING",
        )
        return count

    async def close_all_positions(self) -> int:
        """Close all open positions at market price."""
        resp = await self.client.delete("/v2/positions", params={"cancel_orders": "true"})
        resp.raise_for_status()
        closed = resp.json()
        count = len(closed) if isinstance(closed, list) else 0

        await self.audit.log(
            "all_positions_closed",
            {"count": count},
            component="trade_executor",
            severity="CRITICAL",
        )
        return count
