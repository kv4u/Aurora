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

MODEL_DIR = Path("/app/ml_models")


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
        """Heuristic fallback when no ML model is available.
        Uses a weighted combination of technical signals.
        """
        score = 0.0
        weights_total = 0.0

        # RSI
        rsi = features.get("rsi_14", 50)
        if rsi < 30:
            score += 2.0  # Oversold → BUY signal
        elif rsi > 70:
            score -= 2.0  # Overbought → SELL signal
        elif rsi < 45:
            score += 0.5
        elif rsi > 55:
            score -= 0.5
        weights_total += 2.0

        # MACD
        macd_hist = features.get("macd_histogram", 0)
        if macd_hist > 0:
            score += 1.0
        else:
            score -= 1.0
        weights_total += 1.0

        # Trend alignment
        trend = features.get("trend_alignment_score", 0)
        score += trend * 2.0
        weights_total += 2.0

        # Volume confirmation
        vol_confirm = features.get("volume_price_confirmation", 0)
        score += vol_confirm * 1.0
        weights_total += 1.0

        # Bollinger Band position
        bb_pos = features.get("bb_position", 0.5)
        if bb_pos < 0.2:
            score += 1.5  # Near lower band → BUY
        elif bb_pos > 0.8:
            score -= 1.5  # Near upper band → SELL
        weights_total += 1.5

        # Normalize to -1 to +1
        normalized = score / weights_total if weights_total > 0 else 0

        # Convert to action and confidence
        if normalized > 0.3:
            confidence = min(0.5 + normalized * 0.3, 0.85)
            return "BUY", confidence
        elif normalized < -0.3:
            confidence = min(0.5 + abs(normalized) * 0.3, 0.85)
            return "SELL", confidence
        else:
            confidence = 0.5 + (1 - abs(normalized)) * 0.2
            return "HOLD", confidence

    def _get_top_features(self, features: dict, n: int = 5) -> dict:
        """Get top N features by absolute value (for audit)."""
        sorted_features = sorted(features.items(), key=lambda x: abs(x[1] or 0), reverse=True)
        return {k: v for k, v in sorted_features[:n]}
