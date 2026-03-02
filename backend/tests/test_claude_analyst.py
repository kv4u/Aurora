"""Tests for the Claude financial analyst integration."""

import pytest
from app.core.claude_analyst import (
    ClaudeAnalyst,
    AnalystReview,
    SymbolAnalysis,
    SECTOR_MAP,
    _extract_json,
    _fmt,
    _pct,
    _cross_label,
    _sar_label,
)


class TestReviewResponseParsing:
    """Test JSON response parsing for signal reviews."""

    def test_parses_valid_json(self):
        analyst = ClaudeAnalyst.__new__(ClaudeAnalyst)
        signal = {"confidence": 0.72}

        text = '''{
            "adjusted_confidence": 0.68,
            "confidence_adjustment": -4,
            "position_sizing": "normal",
            "reasoning": "Signal looks solid. Good momentum alignment with RSI at 55.",
            "risk_flags": ["earnings_nearby"],
            "approve": true
        }'''
        review = analyst._parse_review(text, signal)

        assert review.adjusted_confidence == 0.68
        assert review.confidence_adjustment == -4
        assert review.position_sizing == "normal"
        assert review.approve is True
        assert "earnings_nearby" in review.risk_flags

    def test_parses_json_with_markdown_wrapper(self):
        """Claude sometimes wraps JSON in markdown code blocks."""
        analyst = ClaudeAnalyst.__new__(ClaudeAnalyst)
        signal = {"confidence": 0.72}

        text = '''```json
{
    "adjusted_confidence": 0.65,
    "confidence_adjustment": -7,
    "position_sizing": "conservative",
    "reasoning": "High VIX environment. ATR ratio elevated at 0.035.",
    "risk_flags": ["high_vix"],
    "approve": true
}
```'''
        review = analyst._parse_review(text, signal)
        assert review.adjusted_confidence == 0.65
        assert review.position_sizing == "conservative"

    def test_fallback_on_invalid_json(self):
        """Invalid JSON should trigger conservative fallback."""
        analyst = ClaudeAnalyst.__new__(ClaudeAnalyst)
        signal = {"confidence": 0.72}

        text = "I think this is a good trade because..."
        review = analyst._parse_review(text, signal)

        assert review.position_sizing == "conservative"
        assert "parse_error" in review.risk_flags
        assert review.adjusted_confidence == pytest.approx(0.72 * 0.9)

    def test_fallback_on_missing_fields(self):
        """Missing fields should use defaults."""
        analyst = ClaudeAnalyst.__new__(ClaudeAnalyst)
        signal = {"confidence": 0.72}

        text = '{"approve": false}'
        review = analyst._parse_review(text, signal)
        assert review.approve is False

    def test_rejection_preserves_reasoning(self):
        """When Claude rejects, reasoning should be preserved."""
        analyst = ClaudeAnalyst.__new__(ClaudeAnalyst)
        signal = {"confidence": 0.72}

        text = '''{
            "adjusted_confidence": 0.35,
            "confidence_adjustment": -30,
            "position_sizing": "conservative",
            "reasoning": "Earnings report tomorrow. Avoid holding through earnings.",
            "risk_flags": ["earnings_within_5_days", "high_iv"],
            "approve": false
        }'''
        review = analyst._parse_review(text, signal)
        assert review.approve is False
        assert "earnings" in review.reasoning.lower()
        assert len(review.risk_flags) == 2


class TestAnalysisResponseParsing:
    """Test JSON response parsing for deep symbol analysis."""

    def test_parses_valid_analysis(self):
        analyst = ClaudeAnalyst.__new__(ClaudeAnalyst)
        context = {"price": 150.0, "indicators": {"atr_14": 3.5}}

        text = '''{
            "symbol": "AAPL",
            "direction": "bullish",
            "conviction": 7,
            "timeframe": "swing",
            "technical_outlook": "Strong uptrend with price above all key MAs.",
            "volatility_assessment": "Normal vol regime, BB not squeezed.",
            "risk_factors": ["upcoming_earnings", "sector_rotation"],
            "entry_zone": {"low": 148.50, "high": 150.00},
            "stop_loss": 145.00,
            "take_profit_1": 158.00,
            "take_profit_2": 163.00,
            "risk_reward_ratio": 2.3,
            "key_levels": {"support": [148.00, 145.00], "resistance": [155.00, 160.00]},
            "summary": "AAPL shows strong bullish momentum with multi-indicator confluence."
        }'''
        analysis = analyst._parse_analysis(text, "AAPL", context)

        assert analysis.symbol == "AAPL"
        assert analysis.direction == "bullish"
        assert analysis.conviction == 7
        assert analysis.timeframe == "swing"
        assert analysis.stop_loss == 145.00
        assert analysis.take_profit_1 == 158.00
        assert analysis.take_profit_2 == 163.00
        assert analysis.risk_reward_ratio == 2.3
        assert len(analysis.risk_factors) == 2
        assert len(analysis.key_levels["support"]) == 2

    def test_analysis_fallback_on_invalid_json(self):
        analyst = ClaudeAnalyst.__new__(ClaudeAnalyst)
        context = {"price": 150.0, "indicators": {"atr_14": 3.5}}

        text = "This stock looks interesting because..."
        analysis = analyst._parse_analysis(text, "AAPL", context)

        assert analysis.symbol == "AAPL"
        assert analysis.direction == "neutral"
        assert analysis.conviction == 3
        assert "parse_error" in analysis.risk_factors

    def test_analysis_with_markdown_wrapper(self):
        analyst = ClaudeAnalyst.__new__(ClaudeAnalyst)
        context = {"price": 200.0, "indicators": {"atr_14": 5.0}}

        text = '''```json
{
    "symbol": "NVDA",
    "direction": "bearish",
    "conviction": 4,
    "timeframe": "intraday",
    "technical_outlook": "Momentum fading with RSI divergence.",
    "volatility_assessment": "Elevated ATR suggests caution.",
    "risk_factors": ["high_volatility"],
    "entry_zone": {"low": 195.00, "high": 198.00},
    "stop_loss": 205.00,
    "take_profit_1": 188.00,
    "take_profit_2": null,
    "risk_reward_ratio": 1.8,
    "key_levels": {"support": [190.00], "resistance": [210.00]},
    "summary": "Short-term bearish with momentum divergence."
}
```'''
        analysis = analyst._parse_analysis(text, "NVDA", context)
        assert analysis.direction == "bearish"
        assert analysis.conviction == 4
        assert analysis.take_profit_2 is None

    def test_analysis_missing_optional_fields(self):
        analyst = ClaudeAnalyst.__new__(ClaudeAnalyst)
        context = {"price": 100.0, "indicators": {"atr_14": 2.0}}

        text = '''{"symbol": "TSLA", "direction": "neutral", "conviction": 5,
        "timeframe": "swing", "technical_outlook": "Mixed.", "volatility_assessment": "Normal.",
        "risk_factors": [], "entry_zone": {"low": 99, "high": 101}, "stop_loss": 96,
        "take_profit_1": 106, "risk_reward_ratio": 1.5, "key_levels": {"support": [], "resistance": []},
        "summary": "Neutral stance."}'''
        analysis = analyst._parse_analysis(text, "TSLA", context)
        assert analysis.take_profit_2 is None
        assert analysis.risk_factors == []


class TestAnalystDataclasses:
    """Test dataclass defaults."""

    def test_review_defaults(self):
        review = AnalystReview(
            adjusted_confidence=0.7,
            confidence_adjustment=0,
            position_sizing="normal",
            reasoning="Test",
        )
        assert review.approve is True
        assert review.risk_flags == []
        assert review.input_tokens == 0

    def test_analysis_defaults(self):
        analysis = SymbolAnalysis(
            symbol="AAPL",
            direction="bullish",
            conviction=7,
            timeframe="swing",
            technical_outlook="Good",
            volatility_assessment="Normal",
            risk_factors=[],
            entry_zone={"low": 149, "high": 151},
            stop_loss=145,
            take_profit_1=160,
            take_profit_2=None,
            risk_reward_ratio=2.0,
            key_levels={"support": [], "resistance": []},
            summary="Test",
        )
        assert analysis.input_tokens == 0
        assert analysis.output_tokens == 0
        assert analysis.analyzed_at == ""


class TestHelperFunctions:
    """Test formatting and label helpers."""

    def test_extract_json_plain(self):
        data = _extract_json('{"key": "value"}')
        assert data["key"] == "value"

    def test_extract_json_markdown_wrapper(self):
        data = _extract_json('```json\n{"key": "value"}\n```')
        assert data["key"] == "value"

    def test_fmt_none(self):
        assert _fmt(None) == "N/A"

    def test_fmt_value(self):
        assert _fmt(3.14159, 2) == "3.14"

    def test_pct_none(self):
        assert _pct(None) == "N/A"

    def test_pct_value(self):
        assert _pct(0.0523) == "5.23%"

    def test_cross_label_bullish(self):
        assert _cross_label(1.0) == "BULLISH"

    def test_cross_label_bearish(self):
        assert _cross_label(-1.0) == "BEARISH"

    def test_cross_label_none(self):
        assert _cross_label(None) == "N/A"

    def test_sar_label_bullish(self):
        assert "BULLISH" in _sar_label(1.0)

    def test_sar_label_bearish(self):
        assert "BEARISH" in _sar_label(-1.0)


class TestSectorMap:
    """Test the sector mapping is populated."""

    def test_known_symbols(self):
        assert SECTOR_MAP["AAPL"] == "Technology"
        assert SECTOR_MAP["JPM"] == "Financials"
        assert SECTOR_MAP["UNH"] == "Healthcare"
        assert SECTOR_MAP["XOM"] == "Energy"
        assert SECTOR_MAP["SPY"] == "Index"

    def test_unknown_symbol_returns_default(self):
        assert SECTOR_MAP.get("ZZZZ", "Unknown") == "Unknown"


class TestPromptBuilder:
    """Test the prompt builder produces coherent output."""

    def test_review_prompt_contains_all_sections(self):
        analyst = ClaudeAnalyst.__new__(ClaudeAnalyst)
        signal = {
            "symbol": "AAPL",
            "action": "BUY",
            "confidence": 0.72,
            "model_version": "heuristic_v1",
            "features_snapshot": {
                "rsi_14": 55.3,
                "macd_histogram": 0.45,
                "bb_position": 0.65,
                "atr_14": 3.2,
                "sma_20": 148.0,
                "sma_50": 145.0,
                "adx_14": 25.0,
                "volume_vs_sma20": 1.3,
                "return_1d": 0.01,
                "return_5d": 0.03,
                "return_10d": 0.05,
                "return_20d": 0.08,
            },
        }
        context = {
            "price": 150.0,
            "change_pct": 0.012,
            "volume_ratio": 1.3,
            "vix": 18.5,
            "vix_change": -0.05,
            "spy_change": 0.005,
            "sector_perf": "Technology — Broad market positive",
            "recent_news": "- [Reuters] Apple new product launch",
            "upcoming_events": "Earnings in 12 days.",
            "high_52w": 180.0,
            "low_52w": 125.0,
        }

        prompt = analyst._build_review_prompt(signal, context)

        assert "AAPL" in prompt
        assert "Technology" in prompt
        assert "BUY" in prompt
        assert "PRICE & TREND" in prompt
        assert "MOMENTUM" in prompt
        assert "VOLATILITY" in prompt
        assert "VOLUME" in prompt
        assert "MARKET CONTEXT" in prompt
        assert "NEWS" in prompt
        assert "$150.00" in prompt
        assert "$180.00" in prompt
        assert "$125.00" in prompt

    def test_analysis_prompt_contains_all_sections(self):
        analyst = ClaudeAnalyst.__new__(ClaudeAnalyst)
        context = {
            "price": 200.0,
            "change_pct": -0.02,
            "high_52w": 240.0,
            "low_52w": 160.0,
            "vix": 22.0,
            "vix_change": 0.1,
            "spy_change": -0.008,
            "sector_perf": "Technology — Slightly negative",
            "recent_news": "- [CNBC] NVDA data center growth",
            "upcoming_events": "None known.",
            "indicators": {
                "rsi_14": 45.0,
                "macd": -0.5,
                "macd_signal": -0.3,
                "macd_histogram": -0.2,
                "sma_20": 205.0,
                "sma_50": 210.0,
                "atr_14": 6.5,
            },
        }

        prompt = analyst._build_analysis_prompt("NVDA", context)

        assert "NVDA" in prompt
        assert "DEEP ANALYSIS REQUEST" in prompt
        assert "MOVING AVERAGES" in prompt
        assert "TREND INDICATORS" in prompt
        assert "MOMENTUM" in prompt
        assert "VOLATILITY" in prompt
        assert "VOLUME" in prompt
        assert "RETURNS" in prompt
        assert "MARKET CONTEXT" in prompt
        assert "$200.00" in prompt
        assert "$240.00" in prompt
