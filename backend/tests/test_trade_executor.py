"""Tests for trade executor and position sizing."""

import pytest
from app.core.trade_executor import TradeExecutor, PositionSize
from app.core.claude_analyst import AnalystReview


class TestPositionSizing:
    """Test ATR-based position sizing logic."""

    def setup_method(self):
        self.executor = TradeExecutor.__new__(TradeExecutor)

    def test_basic_position_calculation(self):
        signal = {
            "current_price": 185.0,
            "features_snapshot": {"atr_14": 2.85},
        }
        review = AnalystReview(
            adjusted_confidence=0.68,
            confidence_adjustment=-4,
            position_sizing="normal",
            reasoning="Test",
        )
        portfolio = {"total_equity": 10000.0}

        pos = self.executor.calculate_position(signal, review, portfolio, allocation_pct=5.0)

        assert pos.shares > 0
        assert pos.stop_price < signal["current_price"]
        assert pos.target_price > signal["current_price"]
        assert pos.limit_price >= signal["current_price"]
        assert pos.risk_reward_ratio == pytest.approx(1.5)

    def test_conservative_sizing_halves_allocation(self):
        signal = {"current_price": 100.0, "features_snapshot": {"atr_14": 2.0}}
        review_conservative = AnalystReview(
            adjusted_confidence=0.65, confidence_adjustment=-5,
            position_sizing="conservative", reasoning="Test",
        )
        review_normal = AnalystReview(
            adjusted_confidence=0.70, confidence_adjustment=0,
            position_sizing="normal", reasoning="Test",
        )
        portfolio = {"total_equity": 10000.0}

        pos_conservative = self.executor.calculate_position(signal, review_conservative, portfolio, 5.0)
        pos_normal = self.executor.calculate_position(signal, review_normal, portfolio, 5.0)

        assert pos_conservative.shares < pos_normal.shares

    def test_aggressive_sizing_increases_allocation(self):
        signal = {"current_price": 100.0, "features_snapshot": {"atr_14": 2.0}}
        review = AnalystReview(
            adjusted_confidence=0.80, confidence_adjustment=10,
            position_sizing="aggressive", reasoning="Test",
        )
        portfolio = {"total_equity": 10000.0}

        pos = self.executor.calculate_position(signal, review, portfolio, 5.0)
        # 5% * 1.25 = 6.25% = $625 → 6 shares at $100
        assert pos.shares >= 6

    def test_stop_loss_is_2x_atr(self):
        signal = {"current_price": 200.0, "features_snapshot": {"atr_14": 5.0}}
        review = AnalystReview(
            adjusted_confidence=0.70, confidence_adjustment=0,
            position_sizing="normal", reasoning="Test",
        )
        portfolio = {"total_equity": 50000.0}

        pos = self.executor.calculate_position(signal, review, portfolio, 5.0)

        expected_stop = round(200.0 - (2.0 * 5.0), 2)
        assert pos.stop_price == expected_stop  # $190.00

    def test_target_is_3x_atr(self):
        signal = {"current_price": 200.0, "features_snapshot": {"atr_14": 5.0}}
        review = AnalystReview(
            adjusted_confidence=0.70, confidence_adjustment=0,
            position_sizing="normal", reasoning="Test",
        )
        portfolio = {"total_equity": 50000.0}

        pos = self.executor.calculate_position(signal, review, portfolio, 5.0)

        expected_target = round(200.0 + (3.0 * 5.0), 2)
        assert pos.target_price == expected_target  # $215.00

    def test_minimum_one_share(self):
        signal = {"current_price": 5000.0, "features_snapshot": {"atr_14": 50.0}}
        review = AnalystReview(
            adjusted_confidence=0.65, confidence_adjustment=-5,
            position_sizing="conservative", reasoning="Test",
        )
        portfolio = {"total_equity": 1000.0}  # Very small portfolio

        pos = self.executor.calculate_position(signal, review, portfolio, 5.0)
        assert pos.shares >= 1

    def test_atr_fallback_when_missing(self):
        """Should use 2% of price as ATR fallback."""
        signal = {"current_price": 100.0, "features_snapshot": {}}
        review = AnalystReview(
            adjusted_confidence=0.70, confidence_adjustment=0,
            position_sizing="normal", reasoning="Test",
        )
        portfolio = {"total_equity": 10000.0}

        pos = self.executor.calculate_position(signal, review, portfolio, 5.0)
        # ATR fallback = 100 * 0.02 = 2.0
        assert pos.stop_price == round(100.0 - 4.0, 2)  # 2 * 2.0
        assert pos.target_price == round(100.0 + 6.0, 2)  # 3 * 2.0
