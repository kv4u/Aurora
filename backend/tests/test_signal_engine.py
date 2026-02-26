"""Tests for the ML signal engine and feature engineering."""

import pytest
from app.ml.feature_engineering import FeatureEngineer, FEATURE_NAMES


class TestFeatureEngineering:
    """Test feature vector construction."""

    def setup_method(self):
        self.fe = FeatureEngineer()

    def test_builds_features_from_indicators(self):
        """Feature engineer should produce features from indicator dict."""
        indicators = {
            "rsi_14": 45.3,
            "macd": 0.5,
            "macd_signal": 0.35,
            "macd_histogram": 0.15,
            "bb_position": 0.55,
            "adx_14": 25.0,
            "cci_20": 12.0,
            "stoch_k": 55.0,
            "stoch_d": 52.0,
            "obv_slope": 1000.0,
            "vwap_diff": 0.5,
            "atr_14": 2.85,
            "atr_ratio": 0.015,
            "williams_r": -45.0,
            "parabolic_sar_signal": 1.0,
            "ema12_ema26_cross": 1.0,
            "sma20_sma50_cross": 1.0,
            "volume_vs_sma20": 1.2,
            "volume_ratio_5d": 1.1,
            "keltner_position": 0.6,
            "roc_10": 2.5,
            "return_1d": 0.01,
            "return_5d": 0.03,
            "return_10d": 0.05,
            "return_20d": 0.08,
            "high_low_ratio": 1.02,
            "close_open_ratio": 1.005,
            "price_vs_sma20": 1.01,
            "price_vs_sma50": 1.02,
            "price_vs_sma200": 1.10,
            "gap_percentage": 0.002,
            "rsi_macd_agreement": 0.0,
            "volume_price_confirmation": 1.0,
            "bb_squeeze": 0.04,
        }
        features = self.fe.build_features(indicators)

        assert "rsi_14" in features
        assert "macd_histogram" in features
        assert "trend_alignment_score" in features
        assert features["rsi_14"] == 45.3

    def test_handles_empty_indicators(self):
        features = self.fe.build_features({})
        assert features == {}

    def test_all_feature_names_present(self):
        """Every defined feature name should be in the output."""
        indicators = {
            "rsi_14": 50, "macd": 0, "macd_signal": 0, "macd_histogram": 0,
            "bb_position": 0.5, "adx_14": 20, "cci_20": 0, "stoch_k": 50,
            "stoch_d": 50, "obv_slope": 0, "vwap_diff": 0, "atr_14": 1,
            "atr_ratio": 0.01, "williams_r": -50, "parabolic_sar_signal": 1,
            "ema12_ema26_cross": 1, "sma20_sma50_cross": 1, "volume_vs_sma20": 1,
            "volume_ratio_5d": 1, "keltner_position": 0.5, "roc_10": 0,
            "return_1d": 0, "return_5d": 0, "return_10d": 0, "return_20d": 0,
            "high_low_ratio": 1, "close_open_ratio": 1, "price_vs_sma20": 1,
            "price_vs_sma50": 1, "price_vs_sma200": 1, "gap_percentage": 0,
            "rsi_macd_agreement": 0, "volume_price_confirmation": 0, "bb_squeeze": 0,
        }
        features = self.fe.build_features(indicators)

        for name in FEATURE_NAMES:
            assert name in features, f"Missing feature: {name}"

    def test_nan_values_cleaned(self):
        """NaN values should be replaced with 0.0."""
        import math
        indicators = {"rsi_14": float("nan"), "macd": 0}
        features = self.fe.build_features(indicators)
        assert not math.isnan(features["rsi_14"])

    def test_to_dataframe(self):
        """Should produce a proper DataFrame for model input."""
        indicators = {k: 0.0 for k in [
            "rsi_14", "macd", "macd_signal", "macd_histogram", "bb_position",
            "adx_14", "cci_20", "stoch_k", "stoch_d", "obv_slope", "vwap_diff",
            "atr_14", "atr_ratio", "williams_r", "parabolic_sar_signal",
            "ema12_ema26_cross", "sma20_sma50_cross", "volume_vs_sma20",
            "volume_ratio_5d", "keltner_position", "roc_10", "return_1d",
            "return_5d", "return_10d", "return_20d", "high_low_ratio",
            "close_open_ratio", "price_vs_sma20", "price_vs_sma50",
            "price_vs_sma200", "gap_percentage", "rsi_macd_agreement",
            "volume_price_confirmation", "bb_squeeze",
        ]}
        features = self.fe.build_features(indicators)
        df = self.fe.features_to_dataframe(features)

        assert list(df.columns) == FEATURE_NAMES
        assert len(df) == 1


class TestHeuristicSignals:
    """Test the heuristic fallback signal generation."""

    def test_oversold_generates_buy(self):
        """RSI < 30 should generate a BUY signal."""
        from app.ml.signal_engine import SignalEngine
        engine = SignalEngine.__new__(SignalEngine)
        engine._model = None  # Force heuristic mode

        features = {
            "rsi_14": 25.0, "macd_histogram": 0.1, "trend_alignment_score": 0.5,
            "volume_price_confirmation": 1.0, "bb_position": 0.15,
        }
        action, confidence = engine._predict_heuristic(features)
        assert action == "BUY"
        assert confidence >= 0.5

    def test_overbought_generates_sell(self):
        """RSI > 70 should generate a SELL signal."""
        from app.ml.signal_engine import SignalEngine
        engine = SignalEngine.__new__(SignalEngine)
        engine._model = None

        features = {
            "rsi_14": 78.0, "macd_histogram": -0.2, "trend_alignment_score": -0.5,
            "volume_price_confirmation": 0.0, "bb_position": 0.9,
        }
        action, confidence = engine._predict_heuristic(features)
        assert action == "SELL"
        assert confidence >= 0.5

    def test_neutral_generates_hold(self):
        """Neutral indicators should generate HOLD."""
        from app.ml.signal_engine import SignalEngine
        engine = SignalEngine.__new__(SignalEngine)
        engine._model = None

        features = {
            "rsi_14": 50.0, "macd_histogram": 0.01, "trend_alignment_score": 0.0,
            "volume_price_confirmation": 0.0, "bb_position": 0.5,
        }
        action, confidence = engine._predict_heuristic(features)
        assert action == "HOLD"
