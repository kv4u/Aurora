"""ML Signal Engine — generates BUY/SELL/HOLD signals using LightGBM."""

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit_logger import AuditLogger
from app.ml.feature_engineering import FEATURE_NAMES, FeatureEngineer
from app.models.signals import Signal

logger = logging.getLogger("aurora.signals")

MODEL_DIR = Path(__file__).resolve().parent.parent.parent / "ml_models"


class SignalEngine:
    """Generates trading signals using LightGBM classifier."""

    MIN_CONFIDENCE = 0.65  # Only act on high-confidence signals

    def __init__(self, db: AsyncSession, audit: AuditLogger):
        self.db = db
        self.audit = audit
        self.feature_engineer = FeatureEngineer()
        self._model = None
        self._model_version = "v0.0.0"

    @property
    def model(self):
        if self._model is None:
            self._load_model()
        return self._model

    def _load_model(self):
        """Load the latest model from disk."""
        model_path = MODEL_DIR / "latest.joblib"
        if model_path.exists():
            import joblib
            self._model = joblib.load(model_path)
            version_path = MODEL_DIR / "latest_version.txt"
            if version_path.exists():
                self._model_version = version_path.read_text().strip()
            logger.info("Loaded model %s from %s", self._model_version, model_path)
        else:
            logger.warning("No trained model found at %s — using heuristic fallback", model_path)
            self._model = None

    async def generate_signal(
        self,
        symbol: str,
        indicators: dict,
        market_context: dict | None = None,
    ) -> Signal | None:
        """Generate a BUY/SELL/HOLD signal for a symbol."""

        # Build features
        features = self.feature_engineer.build_features(indicators, market_context)
        if not features:
            logger.warning("No features computed for %s", symbol)
            return None

        # Get prediction
        action, confidence = self._predict(features)

        # Only create signals above minimum confidence
        if confidence < self.MIN_CONFIDENCE:
            logger.debug(
                "Signal for %s below threshold: %s %.1f%% (min: %.1f%%)",
                symbol, action, confidence * 100, self.MIN_CONFIDENCE * 100,
            )
            return None

        # Create signal record
        chain_id = uuid.uuid4()
        signal = Signal(
            decision_chain_id=chain_id,
            symbol=symbol,
            action=action,
            confidence=confidence,
            model_version=self._model_version,
            features_snapshot=features,
            status="pending",
        )
        self.db.add(signal)
        await self.db.flush()

        # Audit
        await self.audit.log_decision_chain(
            chain_id,
            "signal_generated",
            {
                "symbol": symbol,
                "action": action,
                "confidence": confidence,
                "model_version": self._model_version,
                "top_features": self._get_top_features(features),
            },
            component="signal_engine",
            symbol=symbol,
        )

        logger.info("Signal: %s %s (confidence: %.1f%%)", action, symbol, confidence * 100)
        return signal

    def _predict(self, features: dict) -> tuple[str, float]:
        """Run prediction using the ML model or heuristic fallback."""
        if self._model is not None:
            return self._predict_ml(features)
        return self._predict_heuristic(features)

    def _predict_ml(self, features: dict) -> tuple[str, float]:
        """Predict using the trained LightGBM model."""
        df = self.feature_engineer.features_to_dataframe(features)
        proba = self._model.predict_proba(df)[0]

        # Classes: [BUY, HOLD, SELL]
        buy_prob, hold_prob, sell_prob = proba

        if buy_prob > self.MIN_CONFIDENCE:
            return "BUY", float(buy_prob)
        elif sell_prob > self.MIN_CONFIDENCE:
            return "SELL", float(sell_prob)
        return "HOLD", float(hold_prob)

    def _predict_heuristic(self, features: dict) -> tuple[str, float]:
        """Multi-strategy heuristic when no ML model is available.

        Runs 4 independent strategy scores, picks the strongest signal.
        Each strategy returns a directional score (-1 to +1) and a weight.
        """
        strategies = {
            "mean_reversion": self._strategy_mean_reversion(features),
            "momentum": self._strategy_momentum(features),
            "trend_follow": self._strategy_trend_follow(features),
            "breakout": self._strategy_breakout(features),
        }

        # Weighted combination
        total_score = 0.0
        total_weight = 0.0
        for name, (score, weight) in strategies.items():
            total_score += score * weight
            total_weight += weight

        normalized = total_score / total_weight if total_weight > 0 else 0

        # Also check if any single strategy has a very strong conviction
        best_strategy = max(strategies.items(), key=lambda x: abs(x[1][0]) * x[1][1])
        best_name, (best_score, best_weight) = best_strategy

        # If a single strategy is very strong (>0.7), boost the signal
        if abs(best_score) > 0.7:
            normalized = normalized * 0.6 + best_score * 0.4

        # Convert to action and confidence
        # Threshold of 0.15 (lowered from 0.3) — Claude review will filter bad signals
        if normalized > 0.15:
            confidence = min(0.55 + normalized * 0.35, 0.85)
            return "BUY", confidence
        elif normalized < -0.15:
            confidence = min(0.55 + abs(normalized) * 0.35, 0.85)
            return "SELL", confidence
        else:
            confidence = 0.5 + (1 - abs(normalized)) * 0.2
            return "HOLD", confidence

    @staticmethod
    def _strategy_mean_reversion(f: dict) -> tuple[float, float]:
        """Mean reversion: buy oversold, sell overbought."""
        score = 0.0
        rsi = f.get("rsi_14", 50)
        bb_pos = f.get("bb_position", 0.5)
        williams = f.get("williams_r", -50)
        stoch_k = f.get("stoch_k", 50)
        mean_rev = f.get("mean_reversion_score", 0)

        # RSI extremes
        if rsi < 30:
            score += 0.6
        elif rsi < 40:
            score += 0.2
        elif rsi > 70:
            score -= 0.6
        elif rsi > 60:
            score -= 0.2

        # Bollinger Band extremes
        if bb_pos < 0.1:
            score += 0.5
        elif bb_pos < 0.25:
            score += 0.2
        elif bb_pos > 0.9:
            score -= 0.5
        elif bb_pos > 0.75:
            score -= 0.2

        # Stochastics oversold/overbought
        if stoch_k < 20:
            score += 0.3
        elif stoch_k > 80:
            score -= 0.3

        # Williams %R
        if williams < -80:
            score += 0.2
        elif williams > -20:
            score -= 0.2

        # Weight increases when price is far from mean (higher mean_rev_score)
        weight = 1.0 + min(mean_rev * 2, 1.0)
        return (max(min(score, 1.0), -1.0), weight)

    @staticmethod
    def _strategy_momentum(f: dict) -> tuple[float, float]:
        """Momentum: follow short-term price direction with volume confirmation."""
        score = 0.0
        ret_1d = f.get("return_1d", 0)
        ret_5d = f.get("return_5d", 0)
        roc = f.get("roc_10", 0)
        macd_hist = f.get("macd_histogram", 0)
        vol_confirm = f.get("volume_price_confirmation", 0)
        rsi_macd = f.get("rsi_macd_agreement", 0)

        # Short-term returns
        if ret_1d > 0.02:
            score += 0.3
        elif ret_1d < -0.02:
            score -= 0.3

        if ret_5d > 0.03:
            score += 0.3
        elif ret_5d < -0.03:
            score -= 0.3

        # Rate of change
        if roc > 5:
            score += 0.2
        elif roc < -5:
            score -= 0.2

        # MACD histogram direction
        if macd_hist > 0:
            score += 0.2
        elif macd_hist < 0:
            score -= 0.2

        # Volume-price confirmation amplifies the signal
        score *= (1 + abs(vol_confirm) * 0.5)

        # RSI-MACD agreement
        if rsi_macd > 0:
            score *= 1.2
        elif rsi_macd < 0:
            score *= 0.8

        weight = 1.5  # Momentum gets higher base weight
        return (max(min(score, 1.0), -1.0), weight)

    @staticmethod
    def _strategy_trend_follow(f: dict) -> tuple[float, float]:
        """Trend following: align with the dominant trend direction."""
        score = 0.0
        trend = f.get("trend_alignment_score", 0)
        adx = f.get("adx_14", 20)
        trend_strength = f.get("trend_strength_composite", 0)
        ema_cross = f.get("ema12_ema26_cross", 0)
        sma_cross = f.get("sma20_sma50_cross", 0)
        price_sma20 = f.get("price_vs_sma20", 1)
        price_sma50 = f.get("price_vs_sma50", 1)
        sar = f.get("parabolic_sar_signal", 0)

        # Trend alignment is the core signal
        score += trend * 0.4

        # EMA/SMA crossovers
        if ema_cross > 0:
            score += 0.15
        elif ema_cross < 0:
            score -= 0.15

        if sma_cross > 0:
            score += 0.15
        elif sma_cross < 0:
            score -= 0.15

        # Price above/below moving averages
        if price_sma20 > 1.01 and price_sma50 > 1.01:
            score += 0.2  # Bullish: above both MAs
        elif price_sma20 < 0.99 and price_sma50 < 0.99:
            score -= 0.2  # Bearish: below both MAs

        # SAR signal
        score += sar * 0.1

        # ADX gives weight — strong trend means this strategy matters more
        weight = 0.8 + min(adx / 40, 1.2)
        return (max(min(score, 1.0), -1.0), weight)

    @staticmethod
    def _strategy_breakout(f: dict) -> tuple[float, float]:
        """Breakout detection: volume surge + price at extremes."""
        score = 0.0
        vol_ratio = f.get("volume_vs_sma20", 1)
        vol_breakout = f.get("volume_breakout_score", 0)
        bb_pos = f.get("bb_position", 0.5)
        bb_squeeze = f.get("bb_squeeze", 0)
        breakout_prob = f.get("breakout_probability", 0)
        ret_1d = f.get("return_1d", 0)
        keltner = f.get("keltner_position", 0.5)

        # Volume surge is necessary for breakout
        if vol_ratio < 1.3:
            return (0.0, 0.5)  # No volume surge = no breakout

        # Bollinger squeeze release
        if bb_squeeze > 0.5:
            score += 0.3 if ret_1d > 0 else -0.3

        # Price breaking above/below bands
        if bb_pos > 0.95 and ret_1d > 0:
            score += 0.4  # Upside breakout
        elif bb_pos < 0.05 and ret_1d < 0:
            score -= 0.4  # Downside breakdown

        # Keltner channel breakout
        if keltner > 0.9 and ret_1d > 0:
            score += 0.3
        elif keltner < 0.1 and ret_1d < 0:
            score -= 0.3

        # Scale by volume surge strength
        vol_multiplier = min(vol_ratio / 2.0, 1.5)
        score *= vol_multiplier

        weight = 1.0 + breakout_prob
        return (max(min(score, 1.0), -1.0), weight)

    def _get_top_features(self, features: dict, n: int = 5) -> dict:
        """Get top N features by absolute value (for audit)."""
        sorted_features = sorted(features.items(), key=lambda x: abs(x[1] or 0), reverse=True)
        return {k: v for k, v in sorted_features[:n]}
