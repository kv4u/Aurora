"""Claude Smart Finance Analyst — reviews ML signals before trade execution."""

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.core.audit_logger import AuditLogger

logger = logging.getLogger("aurora.claude")


SYSTEM_PROMPT = """You are AURORA's senior financial analyst.
You receive ML-generated trading signals with supporting data.

Your job:
1. Evaluate the signal quality given current market context
2. Check for risks the ML model might miss (earnings, news, macro events)
3. Provide a CONFIDENCE ADJUSTMENT (-30 to +20 points)
4. Flag any concerns
5. Suggest position sizing (conservative/normal/aggressive)

RULES:
- Always err on the side of caution
- Flag if earnings are within 5 days (avoid holding through earnings)
- Flag unusual volume or price action
- Consider sector rotation and macro trends
- Be skeptical of signals during high VIX (>25)
- If unsure, recommend conservative sizing

Respond ONLY in this JSON format (no markdown, no extra text):
{
    "adjusted_confidence": <float 0.0-1.0>,
    "confidence_adjustment": <int -30 to +20>,
    "position_sizing": "conservative" | "normal" | "aggressive",
    "reasoning": "<2-3 sentence explanation>",
    "risk_flags": ["<flag1>", "<flag2>"],
    "approve": true | false
}"""


@dataclass
class AnalystReview:
    adjusted_confidence: float
    confidence_adjustment: int
    position_sizing: str
    reasoning: str
    risk_flags: list[str] = field(default_factory=list)
    approve: bool = True
    input_tokens: int = 0
    output_tokens: int = 0


class ClaudeAnalyst:
    """Uses Claude API to review every ML signal before execution."""

    def __init__(self, settings: Settings, db: AsyncSession, audit: AuditLogger):
        self.settings = settings
        self.db = db
        self.audit = audit
        self._client: anthropic.AsyncAnthropic | None = None
        self._reviews_today = 0
        self._review_date: str = ""

    @property
    def client(self):
        if self._client is None:
            import anthropic
            self._client = anthropic.AsyncAnthropic(
                api_key=self.settings.anthropic_api_key.get_secret_value()
            )
        return self._client

    async def review_signal(
        self,
        signal: dict,
        context: dict,
        decision_chain_id: uuid.UUID | None = None,
    ) -> AnalystReview:
        """Have Claude review a trading signal. Returns structured review."""

        # Rate limit check
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if today != self._review_date:
            self._reviews_today = 0
            self._review_date = today

        if self._reviews_today >= self.settings.claude_max_reviews_per_day:
            logger.warning("Claude review limit reached (%d/day)", self.settings.claude_max_reviews_per_day)
            return AnalystReview(
                adjusted_confidence=signal["confidence"] * 0.9,
                confidence_adjustment=-10,
                position_sizing="conservative",
                reasoning="Review limit reached — auto-conservative sizing applied.",
                risk_flags=["review_limit_reached"],
                approve=signal["confidence"] > 0.70,
            )

        prompt = self._build_prompt(signal, context)

        try:
            response = await self.client.messages.create(
                model=self.settings.claude_model,
                max_tokens=500,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )

            self._reviews_today += 1
            review = self._parse_response(response.content[0].text, signal)
            review.input_tokens = response.usage.input_tokens
            review.output_tokens = response.usage.output_tokens

            # Audit log
            await self.audit.log(
                "claude_review",
                {
                    "signal_symbol": signal.get("symbol"),
                    "signal_action": signal.get("action"),
                    "ml_confidence": signal.get("confidence"),
                    "claude_approved": review.approve,
                    "adjusted_confidence": review.adjusted_confidence,
                    "position_sizing": review.position_sizing,
                    "reasoning": review.reasoning,
                    "risk_flags": review.risk_flags,
                    "tokens": {
                        "input": review.input_tokens,
                        "output": review.output_tokens,
                    },
                    "reviews_today": self._reviews_today,
                },
                component="claude_analyst",
                symbol=signal.get("symbol"),
                decision_chain_id=decision_chain_id,
            )

            return review

        except Exception as e:
            logger.error("Claude review failed: %s", e)
            # Fallback: approve with conservative sizing if ML confidence is high enough
            return AnalystReview(
                adjusted_confidence=signal["confidence"] * 0.85,
                confidence_adjustment=-15,
                position_sizing="conservative",
                reasoning=f"Claude review failed ({type(e).__name__}) — auto-conservative fallback.",
                risk_flags=["claude_api_error"],
                approve=signal["confidence"] > 0.72,
            )

    def _build_prompt(self, signal: dict, context: dict) -> str:
        features = signal.get("features_snapshot", {})
        return f"""SIGNAL REVIEW REQUEST:
Symbol: {signal.get('symbol')}
Action: {signal.get('action')}
ML Confidence: {signal.get('confidence', 0):.1%}
Model Version: {signal.get('model_version', 'unknown')}

CURRENT DATA:
Price: ${context.get('price', 0):.2f}
Change Today: {context.get('change_pct', 0):.2%}
Volume vs Avg: {context.get('volume_ratio', 1):.1f}x
RSI(14): {features.get('rsi_14', 'N/A')}
MACD Histogram: {features.get('macd_histogram', 'N/A')}
BB Position: {features.get('bb_position', 'N/A')}
ATR(14): {features.get('atr_14', 'N/A')}
52w Range: ${context.get('low_52w', 0):.2f} — ${context.get('high_52w', 0):.2f}

MARKET CONTEXT:
SPY Today: {context.get('spy_change', 0):.2%}
VIX: {context.get('vix', 0):.1f}
Sector Performance: {context.get('sector_perf', 'N/A')}

RECENT NEWS:
{context.get('recent_news', 'No recent news available.')}

UPCOMING EVENTS:
{context.get('upcoming_events', 'None known.')}

Please review and provide your assessment."""

    def _parse_response(self, text: str, signal: dict) -> AnalystReview:
        """Parse Claude's JSON response with fallback handling."""
        try:
            # Strip markdown code blocks if present
            clean = text.strip()
            if clean.startswith("```"):
                clean = clean.split("\n", 1)[1]
                clean = clean.rsplit("```", 1)[0]

            data = json.loads(clean)

            return AnalystReview(
                adjusted_confidence=float(data.get("adjusted_confidence", signal["confidence"])),
                confidence_adjustment=int(data.get("confidence_adjustment", 0)),
                position_sizing=data.get("position_sizing", "conservative"),
                reasoning=data.get("reasoning", "No reasoning provided."),
                risk_flags=data.get("risk_flags", []),
                approve=data.get("approve", True),
            )
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning("Failed to parse Claude response: %s", e)
            return AnalystReview(
                adjusted_confidence=signal["confidence"] * 0.9,
                confidence_adjustment=-10,
                position_sizing="conservative",
                reasoning=f"Parse error — applying conservative defaults. Raw: {text[:200]}",
                risk_flags=["parse_error"],
                approve=signal["confidence"] > 0.70,
            )
