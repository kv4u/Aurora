"""Feature engineering pipeline — builds ~50 features for the ML model."""

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger("aurora.features")


# All feature names used by the model
FEATURE_NAMES = [
    # Price-based (10)
    "return_1d", "return_5d", "return_10d", "return_20d",
    "high_low_ratio", "close_open_ratio",
    "price_vs_sma20", "price_vs_sma50", "price_vs_sma200",
    "gap_percentage",
    # Technical indicators (20)
    "rsi_14", "macd_signal_diff", "macd_histogram",
    "bb_position", "adx_14", "cci_20", "stoch_k", "stoch_d",
    "obv_slope", "vwap_diff", "atr_14", "atr_ratio",
    "williams_r", "parabolic_sar_signal",
    "ema12_ema26_cross", "sma20_sma50_cross",
    "volume_vs_sma20", "volume_ratio_5d",
    "keltner_position", "roc_10",
    # Multi-timeframe (5)
    "trend_alignment_score", "bb_squeeze",
    "volume_breakout_score", "momentum_divergence",
    "rsi_macd_agreement",
    # Market context (3)
    "spy_return_1d", "vix_level", "vix_change",
    # Derived (5)
    "volume_price_confirmation",
    "trend_strength_composite",
    "mean_reversion_score",
    "breakout_probability",
    "support_resistance_proximity",
]


class FeatureEngineer:
    """Builds feature vectors from indicator data for ML model input."""

    def build_features(self, indicators: dict, market_context: dict | None = None) -> dict:
        """Build a feature vector from computed indicators and market context.

        Args:
            indicators: Dict of indicator values from IndicatorEngine.
            market_context: Dict with SPY/VIX data.

        Returns:
            Dict of feature_name -> float value.
        """
        if not indicators:
            return {}

        ctx = market_context or {}
        features = {}

        # ─── Price-based ───
        features["return_1d"] = indicators.get("return_1d", 0)
        features["return_5d"] = indicators.get("return_5d", 0)
        features["return_10d"] = indicators.get("return_10d", 0)
        features["return_20d"] = indicators.get("return_20d", 0)
        features["high_low_ratio"] = indicators.get("high_low_ratio", 1)
        features["close_open_ratio"] = indicators.get("close_open_ratio", 1)
        features["price_vs_sma20"] = indicators.get("price_vs_sma20", 1)
        features["price_vs_sma50"] = indicators.get("price_vs_sma50") or 1
        features["price_vs_sma200"] = indicators.get("price_vs_sma200") or 1
        features["gap_percentage"] = indicators.get("gap_percentage", 0)

        # ─── Technical ───
        features["rsi_14"] = indicators.get("rsi_14", 50)
        macd = indicators.get("macd", 0)
        macd_sig = indicators.get("macd_signal", 0)
        features["macd_signal_diff"] = (macd - macd_sig) if macd and macd_sig else 0
        features["macd_histogram"] = indicators.get("macd_histogram", 0)
        features["bb_position"] = indicators.get("bb_position", 0.5)
        features["adx_14"] = indicators.get("adx_14", 20)
        features["cci_20"] = indicators.get("cci_20", 0)
        features["stoch_k"] = indicators.get("stoch_k", 50)
        features["stoch_d"] = indicators.get("stoch_d", 50)
        features["obv_slope"] = indicators.get("obv_slope", 0)
        features["vwap_diff"] = indicators.get("vwap_diff", 0)
        features["atr_14"] = indicators.get("atr_14", 0)
        features["atr_ratio"] = indicators.get("atr_ratio", 0.02)
        features["williams_r"] = indicators.get("williams_r", -50)
        features["parabolic_sar_signal"] = indicators.get("parabolic_sar_signal", 0)
        features["ema12_ema26_cross"] = indicators.get("ema12_ema26_cross", 0)
        features["sma20_sma50_cross"] = indicators.get("sma20_sma50_cross", 0)
        features["volume_vs_sma20"] = indicators.get("volume_vs_sma20", 1)
        features["volume_ratio_5d"] = indicators.get("volume_ratio_5d", 1)
        features["keltner_position"] = indicators.get("keltner_position", 0.5)
        features["roc_10"] = indicators.get("roc_10", 0)

        # ─── Multi-timeframe / composite ───
        features["rsi_macd_agreement"] = indicators.get("rsi_macd_agreement", 0)
        features["volume_price_confirmation"] = indicators.get("volume_price_confirmation", 0)
        features["bb_squeeze"] = indicators.get("bb_squeeze", 0)

        # Trend alignment: count how many trend signals agree
        trend_signals = [
            1 if features["ema12_ema26_cross"] > 0 else -1,
            1 if features["sma20_sma50_cross"] > 0 else -1,
            1 if features["macd_histogram"] > 0 else -1,
            1 if features["parabolic_sar_signal"] > 0 else -1,
        ]
        features["trend_alignment_score"] = sum(trend_signals) / len(trend_signals)

        # Volume breakout
        features["volume_breakout_score"] = min(features["volume_vs_sma20"] / 2.0, 1.0)

        # Momentum divergence (simplified)
        rsi_bull = features["rsi_14"] > 50
        price_bull = features["return_5d"] > 0
        features["momentum_divergence"] = 0.0 if rsi_bull == price_bull else 1.0

        # ─── Market context ───
        features["spy_return_1d"] = ctx.get("spy_return_1d", 0)
        features["vix_level"] = ctx.get("vix", 20)
        features["vix_change"] = ctx.get("vix_change", 0)

        # ─── Derived ───
        features["trend_strength_composite"] = (
            abs(features["adx_14"] / 50) * features["trend_alignment_score"]
        )

        # Mean reversion score: how far from "mean" (SMA20)
        features["mean_reversion_score"] = abs(1 - features["price_vs_sma20"])

        # Breakout probability (simplified)
        features["breakout_probability"] = min(
            features["volume_breakout_score"] * abs(features["bb_position"] - 0.5) * 2,
            1.0,
        )

        # Support/resistance proximity (simplified using BB)
        features["support_resistance_proximity"] = min(
            features["bb_position"], 1 - features["bb_position"]
        )

        # Clean NaN/None values
        for key in features:
            if features[key] is None or (isinstance(features[key], float) and np.isnan(features[key])):
                features[key] = 0.0

        return features

    def features_to_dataframe(self, features: dict) -> pd.DataFrame:
        """Convert feature dict to a single-row DataFrame for model input."""
        return pd.DataFrame([features])[FEATURE_NAMES]
