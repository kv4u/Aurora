"""Scheduler — orchestrates the full AURORA trading loop using APScheduler."""

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, func as sqlfunc
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.core.audit_logger import AuditLogger
from app.core.claude_analyst import ClaudeAnalyst, SECTOR_MAP
from app.core.data_ingestion import DataIngestion
from app.core.indicators import IndicatorEngine
from app.core.portfolio_tracker import PortfolioTracker
from app.core.risk_manager import CircuitBreakerLevel, RiskManager
from app.core.trade_executor import TradeExecutor
from app.ml.signal_engine import SignalEngine
from app.models.market_data import MarketData

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

            # 4. Build rich market context (SPY, VIX, realized vol)
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

                    # Build rich context for Claude
                    context = await self._build_symbol_context(
                        symbol, indicators, market_context,
                    )

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

    # ─── Context Builders ───

    async def _build_market_context(self) -> dict:
        """Build market-wide context: SPY price/return, realized volatility as VIX proxy."""
        context = {"spy_return_1d": 0, "spy_change": 0, "vix": 20, "vix_change": 0}

        try:
            spy_price = await self.ingestion.get_latest_price("SPY")
            if spy_price:
                context["spy_price"] = spy_price

            # SPY return from stored bars
            spy_bars = await self._get_recent_bars("SPY", limit=20)
            if len(spy_bars) >= 2:
                prev_close = spy_bars[-2]["close"]
                cur_close = spy_bars[-1]["close"]
                if prev_close > 0:
                    ret = (cur_close - prev_close) / prev_close
                    context["spy_return_1d"] = ret
                    context["spy_change"] = ret

            # Estimate realized vol as VIX proxy from SPY returns
            if len(spy_bars) >= 10:
                import numpy as np
                closes = [b["close"] for b in spy_bars]
                returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]
                realized_vol = float(np.std(returns) * (252 ** 0.5) * 100)
                context["vix"] = round(realized_vol, 1)
                if len(returns) >= 10:
                    recent_vol = float(np.std(returns[-5:]) * (252 ** 0.5) * 100)
                    prior_vol = float(np.std(returns[-10:-5]) * (252 ** 0.5) * 100)
                    context["vix_change"] = (recent_vol - prior_vol) / prior_vol if prior_vol > 0 else 0
        except Exception:
            logger.debug("Market context build failed, using defaults")

        return context

    async def _build_symbol_context(
        self,
        symbol: str,
        indicators: dict,
        market_context: dict,
    ) -> dict:
        """Build rich per-symbol context for Claude signal review."""

        price = indicators.get("close", 0)
        if not price:
            latest_price = await self.ingestion.get_latest_price(symbol)
            price = latest_price or 0

        # 52-week high/low from stored bar data
        high_52w, low_52w = await self._get_52w_range(symbol)

        # News with summaries
        news = await self.ingestion.fetch_news([symbol], limit=5)
        news_lines = []
        for n in news[:5]:
            headline = n.get("headline", "")
            summary = n.get("summary", "")
            source = n.get("source", "")
            line = f"- [{source}] {headline}"
            if summary:
                line += f" — {summary[:120]}"
            news_lines.append(line)
        news_str = "\n".join(news_lines) if news_lines else "No recent news available."

        # Sector context
        sector = SECTOR_MAP.get(symbol, "Unknown")
        sector_perf = self._estimate_sector_label(market_context)

        return {
            "price": price,
            "change_pct": indicators.get("return_1d", 0),
            "volume_ratio": indicators.get("volume_vs_sma20", 1),
            "vix": market_context.get("vix", 20),
            "vix_change": market_context.get("vix_change", 0),
            "spy_change": market_context.get("spy_change", 0),
            "sector_perf": f"{sector} — {sector_perf}",
            "recent_news": news_str,
            "upcoming_events": "None known.",
            "high_52w": high_52w,
            "low_52w": low_52w,
        }

    async def build_analysis_context(self, symbol: str) -> dict:
        """Build full context for on-demand deep analysis. Called by the API endpoint."""

        indicators = await self.indicators.compute_for_symbol(symbol)
        if not indicators:
            indicators = {}

        price = indicators.get("close", 0)
        if not price:
            latest_price = await self.ingestion.get_latest_price(symbol)
            price = latest_price or 0

        high_52w, low_52w = await self._get_52w_range(symbol)
        market_context = await self._build_market_context()

        # Richer news for on-demand analysis
        news = await self.ingestion.fetch_news([symbol], limit=8)
        news_lines = []
        for n in news[:8]:
            headline = n.get("headline", "")
            summary = n.get("summary", "")
            source = n.get("source", "")
            line = f"- [{source}] {headline}"
            if summary:
                line += f" — {summary[:150]}"
            news_lines.append(line)
        news_str = "\n".join(news_lines) if news_lines else "No recent news available."

        sector = SECTOR_MAP.get(symbol, "Unknown")
        sector_perf = self._estimate_sector_label(market_context)

        return {
            "price": price,
            "change_pct": indicators.get("return_1d", 0),
            "high_52w": high_52w,
            "low_52w": low_52w,
            "vix": market_context.get("vix", 20),
            "vix_change": market_context.get("vix_change", 0),
            "spy_change": market_context.get("spy_change", 0),
            "sector_perf": f"{sector} — {sector_perf}",
            "recent_news": news_str,
            "upcoming_events": "None known.",
            "indicators": indicators,
        }

    # ─── Data Helpers ───

    async def _get_52w_range(self, symbol: str) -> tuple[float, float]:
        """Compute 52-week high/low from stored daily bar data."""
        try:
            result = await self.db.execute(
                select(
                    sqlfunc.max(MarketData.high).label("high_52w"),
                    sqlfunc.min(MarketData.low).label("low_52w"),
                )
                .where(
                    MarketData.symbol == symbol,
                    MarketData.timeframe == "1Day",
                )
            )
            row = result.one_or_none()
            if row and row.high_52w and row.low_52w:
                return float(row.high_52w), float(row.low_52w)
        except Exception as e:
            logger.debug("52w range query failed for %s: %s", symbol, e)

        return 0.0, 0.0

    async def _get_recent_bars(self, symbol: str, limit: int = 20) -> list[dict]:
        """Get recent daily bars from database."""
        try:
            result = await self.db.execute(
                select(MarketData)
                .where(
                    MarketData.symbol == symbol,
                    MarketData.timeframe == "1Day",
                )
                .order_by(MarketData.timestamp.desc())
                .limit(limit)
            )
            rows = list(result.scalars().all())
            rows.reverse()
            return [
                {"close": r.close, "high": r.high, "low": r.low, "volume": r.volume}
                for r in rows
            ]
        except Exception:
            return []

    @staticmethod
    def _estimate_sector_label(market_context: dict) -> str:
        """Simple sector label based on broad market direction."""
        spy_ret = market_context.get("spy_change", 0)
        if abs(spy_ret) < 0.001:
            return "Flat"
        elif spy_ret > 0.01:
            return "Broad market positive"
        elif spy_ret < -0.01:
            return "Broad market negative"
        return "Slightly positive" if spy_ret > 0 else "Slightly negative"

    async def cleanup(self):
        """Clean up resources."""
        await self.ingestion.close()
        await self.executor.close()
        await self.portfolio.close()
