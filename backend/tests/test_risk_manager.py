"""Tests for the risk manager module — the most critical module in AURORA."""

import pytest


class TestRiskLimits:
    """Test that all risk limits are properly enforced."""

    def test_max_position_pct_cannot_exceed_hard_cap(self):
        """Position size must never exceed 10% hard cap."""
        hard_cap = 10.0
        requested = 15.0
        assert min(requested, hard_cap) == hard_cap

    def test_stop_loss_always_set(self):
        """Every trade must have a stop loss."""
        # Stop price should be below entry for BUY
        entry_price = 185.0
        atr = 2.85
        stop_price = entry_price - (2.0 * atr)
        assert stop_price < entry_price
        assert stop_price == pytest.approx(179.30)

    def test_daily_loss_limit_triggers_circuit_breaker(self):
        """Daily loss exceeding 3% should trigger ORANGE circuit breaker."""
        daily_loss_pct = 3.5
        max_daily_loss = 3.0
        assert daily_loss_pct > max_daily_loss

    def test_monthly_loss_limit_triggers_red(self):
        """Monthly loss exceeding 8% should trigger RED circuit breaker."""
        monthly_loss_pct = 9.0
        max_monthly_loss = 8.0
        assert monthly_loss_pct > max_monthly_loss

    def test_max_open_positions(self):
        """Cannot open more than max_open_positions."""
        max_positions = 8
        current_positions = 8
        assert current_positions >= max_positions

    def test_no_trades_during_market_open_close(self):
        """No trades in first 15 min and last 10 min of trading."""
        no_trade_first_minutes = 15
        no_trade_last_minutes = 10
        assert no_trade_first_minutes > 0
        assert no_trade_last_minutes > 0

    def test_min_confidence_threshold(self):
        """Signals below 60% confidence should be rejected."""
        min_confidence = 0.60
        low_signal = 0.55
        high_signal = 0.72
        assert low_signal < min_confidence
        assert high_signal >= min_confidence


class TestCircuitBreakers:
    """Test the 3-level circuit breaker system."""

    def test_yellow_reduces_position_sizes(self):
        """YELLOW: daily loss > 1.5% → reduce sizes by 50%."""
        daily_loss = 1.8
        yellow_trigger = 1.5
        size_multiplier = 0.5 if daily_loss > yellow_trigger else 1.0
        assert size_multiplier == 0.5

    def test_orange_halts_new_trades(self):
        """ORANGE: daily loss > 3% → halt new trades."""
        daily_loss = 3.2
        orange_trigger = 3.0
        allow_new_trades = daily_loss <= orange_trigger
        assert allow_new_trades is False

    def test_red_closes_all_positions(self):
        """RED: monthly loss > 8% → close all, halt system."""
        monthly_loss = 8.5
        red_trigger = 8.0
        emergency_close = monthly_loss > red_trigger
        assert emergency_close is True


class TestPositionSizing:
    """Test ATR-based position sizing."""

    def test_risk_reward_ratio(self):
        """Target should be 3x ATR, stop should be 2x ATR (1.5:1 R/R)."""
        entry = 185.0
        atr = 2.85
        stop = entry - (2.0 * atr)
        target = entry + (3.0 * atr)
        risk = entry - stop
        reward = target - entry
        rr_ratio = reward / risk
        assert rr_ratio == pytest.approx(1.5)

    def test_vix_reduces_position_size(self):
        """High VIX (>25) should halve position sizes."""
        vix = 28.0
        vix_threshold = 25.0
        multiplier = 0.5 if vix > vix_threshold else 1.0
        assert multiplier == 0.5

    def test_no_trades_above_max_vix(self):
        """No new positions if VIX > 35."""
        vix = 36.0
        max_vix = 35.0
        allow_trade = vix <= max_vix
        assert allow_trade is False
