"""Scheduler — orchestrates the full AURORA trading loop using APScheduler."""

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.core.audit_logger import AuditLogger
from app.core.claude_analyst import ClaudeAnalyst
from app.core.data_ingestion import DataIngestion
from app.core.indicators import IndicatorEngine
from app.core.portfolio_tracker import PortfolioTracker
from app.core.risk_manager import CircuitBreakerLevel, RiskManager
from app.core.trade_executor import TradeExecutor
from app.ml.signal_engine import SignalEngine

logger = logging.getLogger("aurora.scheduler")


class TradingLoop:
    """The core trading loop: DATA → ANALYZE → DECIDE → RISK → EXECUTE → LOG."""

    def __init__(
        self,
        settings: Settings,
        db: AsyncSession,
    ):
        self.settings = settings
        self.db = db
        self.audit = AuditLogger(db)
        self.ingestion = DataIngestion(settings, db)
        self.indicators = IndicatorEngine(db)
        self.signals = SignalEngine(db, self.audit)
        self.risk = RiskManager(settings, db, self.audit)
        self.claude = ClaudeAnalyst(settings, db, self.audit)
        self.executor = TradeExecutor(settings, db, self.risk, self.audit)
        self.portfolio = PortfolioTracker(settings, db)

    async def run_cycle(self) -> dict:
        """Execute one full trading cycle for all watchlist symbols.

        Flow: Ingest → Indicators → Signals → Claude Review → Risk Check → Execute → Log
        """
        cycle_id = str(uuid.uuid4())[:8]
        logger.info("═══ Trading cycle %s starting ═══", cycle_id)

        symbols = self.settings.watchlist_symbols
        results = {
            "cycle_id": cycle_id,
            "symbols_processed": 0,
            "signals_generated": 0,
            "signals_approved": 0,
            "trades_placed": 0,
            "errors": [],
        }

        try:
            # 1. Portfolio snapshot + circuit breaker evaluation
            portfolio_data = await self.portfolio.snapshot()
            if not portfolio_data:
                logger.error("Failed to get portfolio snapshot")
                results["errors"].append("portfolio_snapshot_failed")
                return results

            cb_level = await self.risk.evaluate_circuit_breakers(portfolio_data)
            if cb_level == CircuitBreakerLevel.RED:
                logger.critical("RED circuit breaker — aborting cycle")
                await self.audit.log(
                    "cycle_aborted",
                    {"reason": "RED circuit breaker", "cycle_id": cycle_id},
                    component="scheduler",
                    severity="CRITICAL",
                )
                return results

            # 2. Ingest latest bars
            await self.ingestion.ingest_bars(symbols, timeframe="1Min", limit=1)

            # 3. Compute indicators
            all_indicators = await self.indicators.compute_for_watchlist(symbols)

            # 4. Get market context (SPY, VIX)
            market_context = await self._build_market_context()

            # 5. Generate and process signals
            for symbol in symbols:
                indicators = all_indicators.get(symbol)
                if not indicators:
                    continue

                results["symbols_processed"] += 1

                try:
                    # Generate signal
                    signal = await self.signals.generate_signal(
                        symbol, indicators, market_context,
                    )
                    if signal is None or signal.action == "HOLD":
                        continue

                    results["signals_generated"] += 1

                    # Claude review
                    news = await self.ingestion.fetch_news([symbol], limit=5)
                    context = {
                        "price": indicators.get("close", 0) if "close" in indicators else 0,
                        "change_pct": indicators.get("return_1d", 0),
                        "volume_ratio": indicators.get("volume_vs_sma20", 1),
                        "vix": market_context.get("vix", 20),
                        "spy_change": market_context.get("spy_return_1d", 0),
                        "sector_perf": "N/A",
                        "recent_news": "\n".join(
                            [f"- {n['headline']}" for n in news[:3]]
                        ) if news else "No recent news.",
                        "upcoming_events": "None known.",
                        "high_52w": 0,
                        "low_52w": 0,
                    }

                    review = await self.claude.review_signal(
                        {
                            "symbol": signal.symbol,
                            "action": signal.action,
                            "confidence": signal.confidence,
                            "model_version": signal.model_version,
                            "features_snapshot": signal.features_snapshot,
                            "id": signal.id,
                        },
                        context,
                        decision_chain_id=signal.decision_chain_id,
                    )

                    # Update signal with review
                    signal.claude_approved = review.approve
                    signal.claude_adjusted_confidence = review.adjusted_confidence
                    signal.claude_reasoning = review.reasoning
                    signal.claude_risk_flags = {"flags": review.risk_flags}
                    signal.claude_position_sizing = review.position_sizing
                    signal.reviewed_at = datetime.now(timezone.utc)

                    if not review.approve:
                        signal.status = "rejected"
                        continue

                    results["signals_approved"] += 1
                    signal.status = "approved"

                    # Execute trade
                    trade = await self.executor.execute(
                        signal={
                            "symbol": signal.symbol,
                            "action": signal.action,
                            "confidence": review.adjusted_confidence,
                            "features_snapshot": signal.features_snapshot,
                            "current_price": context["price"],
                            "id": signal.id,
                        },
                        review=review,
                        portfolio=portfolio_data,
                        market_context=market_context,
                        decision_chain_id=signal.decision_chain_id,
                    )

                    if trade:
                        signal.status = "executed"
                        results["trades_placed"] += 1

                except Exception as e:
                    logger.error("Error processing %s: %s", symbol, e)
                    results["errors"].append(f"{symbol}: {str(e)}")

            # Commit all changes
            await self.db.commit()

        except Exception as e:
            logger.error("Trading cycle failed: %s", e)
            results["errors"].append(str(e))
            await self.db.rollback()

        # Log cycle completion
        await self.audit.log(
            "cycle_completed",
            results,
            component="scheduler",
        )
        await self.db.commit()

        logger.info(
            "═══ Cycle %s complete: %d symbols, %d signals, %d approved, %d trades ═══",
            cycle_id, results["symbols_processed"], results["signals_generated"],
            results["signals_approved"], results["trades_placed"],
        )

        return results

    async def _build_market_context(self) -> dict:
        """Build market context dict (SPY, VIX) for signal generation."""
        context = {"spy_return_1d": 0, "vix": 20, "vix_change": 0}

        try:
            spy_price = await self.ingestion.get_latest_price("SPY")
            if spy_price:
                context["spy_price"] = spy_price
        except Exception:
            pass

        return context

    async def cleanup(self):
        """Clean up resources."""
        await self.ingestion.close()
        await self.executor.close()
        await self.portfolio.close()
