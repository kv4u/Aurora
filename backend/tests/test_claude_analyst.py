"""Tests for the Claude analyst integration."""

import pytest
from app.core.claude_analyst import ClaudeAnalyst, AnalystReview


class TestClaudeResponseParsing:
    """Test JSON response parsing from Claude."""

    def test_parses_valid_json(self):
        analyst = ClaudeAnalyst.__new__(ClaudeAnalyst)
        signal = {"confidence": 0.72}

        text = '''{
            "adjusted_confidence": 0.68,
            "confidence_adjustment": -4,
            "position_sizing": "normal",
            "reasoning": "Signal looks solid. Good momentum alignment.",
            "risk_flags": ["earnings_nearby"],
            "approve": true
        }'''
        review = analyst._parse_response(text, signal)

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
    "reasoning": "High VIX environment.",
    "risk_flags": ["high_vix"],
    "approve": true
}
```'''
        review = analyst._parse_response(text, signal)
        assert review.adjusted_confidence == 0.65
        assert review.position_sizing == "conservative"

    def test_fallback_on_invalid_json(self):
        """Invalid JSON should trigger conservative fallback."""
        analyst = ClaudeAnalyst.__new__(ClaudeAnalyst)
        signal = {"confidence": 0.72}

        text = "I think this is a good trade because..."
        review = analyst._parse_response(text, signal)

        assert review.position_sizing == "conservative"
        assert "parse_error" in review.risk_flags
        assert review.adjusted_confidence == pytest.approx(0.72 * 0.9)

    def test_fallback_on_missing_fields(self):
        """Missing fields should use defaults."""
        analyst = ClaudeAnalyst.__new__(ClaudeAnalyst)
        signal = {"confidence": 0.72}

        text = '{"approve": false}'
        review = analyst._parse_response(text, signal)
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
        review = analyst._parse_response(text, signal)
        assert review.approve is False
        assert "earnings" in review.reasoning.lower()
        assert len(review.risk_flags) == 2


class TestAnalystReviewDataclass:
    """Test AnalystReview defaults."""

    def test_defaults(self):
        review = AnalystReview(
            adjusted_confidence=0.7,
            confidence_adjustment=0,
            position_sizing="normal",
            reasoning="Test",
        )
        assert review.approve is True
        assert review.risk_flags == []
        assert review.input_tokens == 0
