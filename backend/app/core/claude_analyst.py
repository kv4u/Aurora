"""Claude Financial Analyst — deep market analysis and ML signal review."""

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.core.audit_logger import AuditLogger

logger = logging.getLogger("aurora.claude")

# ─── Sector Mapping ───

SECTOR_MAP = {
    "AAPL": "Technology", "MSFT": "Technology", "GOOGL": "Technology",
    "AMZN": "Consumer Discretionary", "NVDA": "Technology", "META": "Technology",
    "TSLA": "Consumer Discretionary", "JPM": "Financials", "V": "Financials",
    "UNH": "Healthcare", "JNJ": "Healthcare", "PG": "Consumer Staples",
    "XOM": "Energy", "CVX": "Energy", "HD": "Consumer Discretionary",
    "MA": "Financials", "BAC": "Financials", "ABBV": "Healthcare",
    "PFE": "Healthcare", "KO": "Consumer Staples", "PEP": "Consumer Staples",
    "COST": "Consumer Staples", "WMT": "Consumer Staples", "CRM": "Technology",
    "AMD": "Technology", "INTC": "Technology", "NFLX": "Technology",
    "DIS": "Communication Services", "CMCSA": "Communication Services",
    "T": "Communication Services", "VZ": "Communication Services",
    "LLY": "Healthcare", "MRK": "Healthcare", "TMO": "Healthcare",
    "AVGO": "Technology", "QCOM": "Technology", "ORCL": "Technology",
    "ADBE": "Technology", "TXN": "Technology", "GS": "Financials",
    "MS": "Financials", "C": "Financials", "BLK": "Financials",
    "NEE": "Utilities", "SO": "Utilities", "DUK": "Utilities",
    "SPY": "Index", "QQQ": "Index", "IWM": "Index", "DIA": "Index",
}


# ─── Signal Review System Prompt ───

REVIEW_SYSTEM_PROMPT = """You are AURORA's senior financial analyst. An autonomous trading system
is presenting you with an ML-generated signal and full market context.

YOUR ROLE: Act as the final human-quality gate before capital is deployed. You are
the last line of defense between a mathematical model and real money.

ANALYTICAL FRAMEWORK — evaluate in this order:

1. TREND STRUCTURE
   - Is the signal aligned with the dominant trend (price vs SMA20/50/200)?
   - Higher highs & higher lows (uptrend) or lower highs & lower lows (downtrend)?
   - Is this a trend-following or mean-reversion signal? Which is appropriate given volatility?

2. MOMENTUM & DIVERGENCE
   - RSI: Is it overbought (>70) or oversold (<30)? Any divergence from price?
   - MACD: Is the histogram expanding or contracting? Recent crossover?
   - Stochastic: Confirm momentum direction from %K/%D

3. VOLATILITY REGIME
   - VIX level: <15 = complacent, 15-25 = normal, 25-35 = elevated, >35 = crisis
   - Bollinger Band squeeze? If BB width is contracting, expect a breakout
   - ATR ratio: High ATR = wider stops needed, reduced position size
   - Keltner Channel position confirms BB signal

4. VOLUME CONFIRMATION
   - Is volume confirming the move? (price up + volume up = strong)
   - Volume vs 20-day average: >1.5x is significant
   - OBV slope: diverging from price = warning sign

5. SUPPORT & RESISTANCE
   - Where is price relative to key moving averages?
   - 52-week high/low proximity: within 5% of either = caution
   - VWAP position: above = bullish intraday bias, below = bearish

6. RISK ASSESSMENT
   - Earnings within 5 trading days → REJECT (binary event risk)
   - Major news with uncertain outcome → reduce sizing or reject
   - Sector rotation: is money flowing into or out of this sector?
   - Correlation risk: too many positions in same sector?
   - Gap percentage: large gap = potential exhaustion

7. POSITION SIZING LOGIC
   - conservative: Signal is marginal, elevated risk, or uncertain context
   - normal: Signal aligns with trend, adequate volume, acceptable risk
   - aggressive: Strong multi-indicator confluence, low risk, high conviction setup

CONFIDENCE ADJUSTMENT GUIDE:
   +15 to +20: Exceptional multi-indicator confluence, strong trend, volume confirms
   +5 to +14: Good alignment, minor concerns
   0: Neutral — signal is fair as-is
   -1 to -14: Some concerns (divergences, low volume, mixed signals)
   -15 to -30: Significant issues (counter-trend, high VIX, earnings risk, weak volume)

CRITICAL RULES:
- Capital preservation ALWAYS takes priority over opportunity
- When indicators conflict, side with caution
- A rejected trade costs nothing; a bad trade costs real money
- Flag ANY risk the ML model could have missed
- Be specific in your reasoning — cite the indicators that inform your decision

Respond ONLY in this JSON format (no markdown, no extra text):
{
    "adjusted_confidence": <float 0.0-1.0>,
    "confidence_adjustment": <int -30 to +20>,
    "position_sizing": "conservative" | "normal" | "aggressive",
    "reasoning": "<2-3 sentence explanation citing specific indicators>",
    "risk_flags": ["<specific_flag>"],
    "approve": true | false
}"""


# ─── Deep Analysis System Prompt ───

ANALYSIS_SYSTEM_PROMPT = """You are AURORA's senior financial analyst performing a comprehensive
market analysis for a single stock. Provide an institutional-quality assessment.

Analyze the data provided and produce a thorough report covering:

1. TECHNICAL OUTLOOK
   - Current trend direction and strength (reference specific MAs, ADX)
   - Key support and resistance zones (from Bollinger Bands, moving averages, 52w range)
   - Momentum status (RSI, MACD, Stochastic — are they confirming or diverging?)
   - Volume analysis (OBV trend, volume vs average, any accumulation/distribution signals)

2. VOLATILITY ASSESSMENT
   - Current volatility regime (ATR ratio, BB width)
   - Is a volatility expansion or contraction likely?
   - Implied vs realized volatility context (from VIX if available)

3. RISK FACTORS
   - Upcoming catalysts (earnings, news, macro events)
   - Sector headwinds or tailwinds
   - Correlation exposure (if heavily correlated with market)
   - Proximity to key levels that could trigger stop runs

4. TRADE OPPORTUNITIES
   - Best entry zones (price levels with confluence of support)
   - Stop-loss placement (ATR-based with key level awareness)
   - Take-profit targets (resistance levels, measured moves)
   - Preferred direction (long/short/neutral)

5. CONVICTION SCORE
   - Overall score 1-10 (10 = highest conviction)
   - Timeframe: scalp (minutes), intraday, swing (days), position (weeks)
   - Risk/reward ratio estimate

Respond ONLY in this JSON format (no markdown, no extra text):
{
    "symbol": "<symbol>",
    "direction": "bullish" | "bearish" | "neutral",
    "conviction": <int 1-10>,
    "timeframe": "scalp" | "intraday" | "swing" | "position",
    "technical_outlook": "<3-5 sentences on trend, momentum, key levels>",
    "volatility_assessment": "<2-3 sentences on vol regime and expectations>",
    "risk_factors": ["<specific risk 1>", "<specific risk 2>"],
    "entry_zone": {"low": <float>, "high": <float>},
    "stop_loss": <float>,
    "take_profit_1": <float>,
    "take_profit_2": <float>,
    "risk_reward_ratio": <float>,
    "key_levels": {"support": [<float>, <float>], "resistance": [<float>, <float>]},
    "summary": "<2-3 sentence executive summary>"
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


@dataclass
class SymbolAnalysis:
    symbol: str
    direction: str
    conviction: int
    timeframe: str
    technical_outlook: str
    volatility_assessment: str
    risk_factors: list[str]
    entry_zone: dict
    stop_loss: float
    take_profit_1: float
    take_profit_2: float | None
    risk_reward_ratio: float
    key_levels: dict
    summary: str
    input_tokens: int = 0
    output_tokens: int = 0
    analyzed_at: str = ""


class ClaudeAnalyst:
    """Financial analysis engine powered by Claude API."""

    def __init__(self, settings: Settings, db: AsyncSession, audit: AuditLogger):
        self.settings = settings
        self.db = db
        self.audit = audit
        self._client = None
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

    # ─── Signal Review (used in trading loop) ───

    async def review_signal(
        self,
        signal: dict,
        context: dict,
        decision_chain_id: uuid.UUID | None = None,
    ) -> AnalystReview:
        """Review a trading signal with full market context. Returns structured review."""

        # Rate limit check
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if today != self._review_date:
            self._reviews_today = 0
            self._review_date = today

        if self._reviews_today >= self.settings.claude_max_reviews_per_day:
            logger.warning("Review limit reached (%d/day)", self.settings.claude_max_reviews_per_day)
            return AnalystReview(
                adjusted_confidence=signal["confidence"] * 0.9,
                confidence_adjustment=-10,
                position_sizing="conservative",
                reasoning="Review limit reached — auto-conservative sizing applied.",
                risk_flags=["review_limit_reached"],
                approve=signal["confidence"] > 0.70,
            )

        prompt = self._build_review_prompt(signal, context)

        try:
            response = await self.client.messages.create(
                model=self.settings.claude_model,
                max_tokens=600,
                system=REVIEW_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )

            self._reviews_today += 1
            review = self._parse_review(response.content[0].text, signal)
            review.input_tokens = response.usage.input_tokens
            review.output_tokens = response.usage.output_tokens

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
            logger.error("Review failed: %s", e)
            return AnalystReview(
                adjusted_confidence=signal["confidence"] * 0.85,
                confidence_adjustment=-15,
                position_sizing="conservative",
                reasoning=f"Review failed ({type(e).__name__}) — auto-conservative fallback.",
                risk_flags=["api_error"],
                approve=signal["confidence"] > 0.72,
            )

    # ─── Deep Symbol Analysis (on-demand) ───

    async def analyze_symbol(self, symbol: str, context: dict) -> SymbolAnalysis:
        """Perform deep financial analysis on a single symbol. Used for on-demand analysis."""

        prompt = self._build_analysis_prompt(symbol, context)

        try:
            response = await self.client.messages.create(
                model=self.settings.claude_model,
                max_tokens=1200,
                system=ANALYSIS_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )

            analysis = self._parse_analysis(response.content[0].text, symbol, context)
            analysis.input_tokens = response.usage.input_tokens
            analysis.output_tokens = response.usage.output_tokens
            analysis.analyzed_at = datetime.now(timezone.utc).isoformat()

            await self.audit.log(
                "claude_analysis",
                {
                    "symbol": symbol,
                    "direction": analysis.direction,
                    "conviction": analysis.conviction,
                    "timeframe": analysis.timeframe,
                    "summary": analysis.summary,
                    "tokens": {
                        "input": analysis.input_tokens,
                        "output": analysis.output_tokens,
                    },
                },
                component="claude_analyst",
                symbol=symbol,
            )

            return analysis

        except Exception as e:
            logger.error("Analysis failed for %s: %s", symbol, e)
            price = context.get("price", 0)
            atr = context.get("atr_14", price * 0.02)
            return SymbolAnalysis(
                symbol=symbol,
                direction="neutral",
                conviction=3,
                timeframe="swing",
                technical_outlook=f"Analysis unavailable ({type(e).__name__}). Review indicators manually.",
                volatility_assessment="Unable to assess — check ATR and VIX manually.",
                risk_factors=["analysis_api_error"],
                entry_zone={"low": price * 0.99, "high": price * 1.01},
                stop_loss=round(price - 2 * atr, 2) if price else 0,
                take_profit_1=round(price + 3 * atr, 2) if price else 0,
                take_profit_2=None,
                risk_reward_ratio=1.5,
                key_levels={"support": [], "resistance": []},
                summary=f"Analysis failed for {symbol}. Manual review required.",
                analyzed_at=datetime.now(timezone.utc).isoformat(),
            )

    # ─── Prompt Builders ───

    def _build_review_prompt(self, signal: dict, context: dict) -> str:
        """Build a rich context prompt for signal review."""
        f = signal.get("features_snapshot", {})
        sym = signal.get("symbol", "???")
        sector = SECTOR_MAP.get(sym, "Unknown")

        # Trend context
        sma20 = f.get("sma_20")
        sma50 = f.get("sma_50")
        sma200 = f.get("sma_200")
        price = context.get("price", 0)

        trend_lines = []
        if sma20 and price:
            trend_lines.append(f"  Price vs SMA20: {((price / sma20) - 1) * 100:+.2f}%")
        if sma50 and price:
            trend_lines.append(f"  Price vs SMA50: {((price / sma50) - 1) * 100:+.2f}%")
        if sma200 and price:
            trend_lines.append(f"  Price vs SMA200: {((price / sma200) - 1) * 100:+.2f}%")

        trend_str = "\n".join(trend_lines) if trend_lines else "  Moving averages unavailable"

        # Volume context
        vol_ratio = context.get("volume_ratio", f.get("volume_vs_sma20", 1))
        vol_5d = f.get("volume_ratio_5d", "N/A")
        obv_slope = f.get("obv_slope", "N/A")

        # Relative strength vs SPY
        spy_ret = context.get("spy_change", 0)
        stock_ret = context.get("change_pct", f.get("return_1d", 0))
        rel_strength = stock_ret - spy_ret if isinstance(stock_ret, (int, float)) and isinstance(spy_ret, (int, float)) else None

        return f"""SIGNAL REVIEW REQUEST
{"═" * 50}
Symbol: {sym} ({sector})
Action: {signal.get('action')}
ML Confidence: {signal.get('confidence', 0):.1%}
Model: {signal.get('model_version', 'unknown')}

PRICE & TREND
  Current Price: ${price:.2f}
  Change Today: {context.get('change_pct', 0):.2%}
  52-Week Range: ${context.get('low_52w', 0):.2f} — ${context.get('high_52w', 0):.2f}
  ADX(14): {f.get('adx_14', 'N/A')}
  Parabolic SAR Signal: {_sar_label(f.get('parabolic_sar_signal'))}
{trend_str}

MOMENTUM
  RSI(14): {_fmt(f.get('rsi_14'))}
  MACD Histogram: {_fmt(f.get('macd_histogram'), 4)}
  MACD Signal Cross: {_cross_label(f.get('ema12_ema26_cross'))}
  Stochastic %K/%D: {_fmt(f.get('stoch_k'))}/{_fmt(f.get('stoch_d'))}
  Williams %R: {_fmt(f.get('williams_r'))}
  CCI(20): {_fmt(f.get('cci_20'))}
  ROC(10): {_fmt(f.get('roc_10'))}

VOLATILITY
  ATR(14): {_fmt(f.get('atr_14'), 3)}
  ATR Ratio: {_fmt(f.get('atr_ratio'), 4)}
  BB Position: {_fmt(f.get('bb_position'), 3)} (0=low band, 1=high band)
  BB Squeeze: {_fmt(f.get('bb_squeeze'), 4)}
  Keltner Position: {_fmt(f.get('keltner_position'), 3)}

VOLUME
  Volume vs 20d Avg: {_fmt(vol_ratio)}x
  Volume vs 5d Avg: {_fmt(vol_5d)}x
  OBV Slope (5d): {_fmt(obv_slope)}
  Volume-Price Confirm: {'YES' if f.get('volume_price_confirmation') == 1.0 else 'NO'}

MARKET CONTEXT
  SPY Today: {context.get('spy_change', 0):.2%}
  VIX: {context.get('vix', 0):.1f}
  VIX Change: {context.get('vix_change', 0):.2%}
  Sector: {sector} — {context.get('sector_perf', 'N/A')}
  Relative Strength vs SPY: {f'{rel_strength:+.2%}' if rel_strength is not None else 'N/A'}

PRICE STRUCTURE
  Gap Today: {_fmt(f.get('gap_percentage'), 3)}
  VWAP Diff: ${_fmt(f.get('vwap_diff'), 2)}
  Return 5d: {f.get('return_5d', 0):.2%}
  Return 10d: {f.get('return_10d', 0):.2%}
  Return 20d: {f.get('return_20d', 0):.2%}
  RSI-MACD Agreement: {'YES' if f.get('rsi_macd_agreement') == 1.0 else 'NO'}
  SMA20/50 Cross: {_cross_label(f.get('sma20_sma50_cross'))}

NEWS & EVENTS
{context.get('recent_news', 'No recent news available.')}

UPCOMING EVENTS:
{context.get('upcoming_events', 'None known.')}

Provide your assessment."""

    def _build_analysis_prompt(self, symbol: str, context: dict) -> str:
        """Build prompt for deep on-demand symbol analysis."""
        indicators = context.get("indicators", {})
        sector = SECTOR_MAP.get(symbol, "Unknown")
        price = context.get("price", 0)

        sma20 = indicators.get("sma_20")
        sma50 = indicators.get("sma_50")
        sma200 = indicators.get("sma_200")

        trend_lines = []
        if sma20 and price:
            trend_lines.append(f"  SMA20: ${sma20:.2f} ({((price / sma20) - 1) * 100:+.2f}%)")
        if sma50 and price:
            trend_lines.append(f"  SMA50: ${sma50:.2f} ({((price / sma50) - 1) * 100:+.2f}%)")
        if sma200 and price:
            trend_lines.append(f"  SMA200: ${sma200:.2f} ({((price / sma200) - 1) * 100:+.2f}%)")

        return f"""DEEP ANALYSIS REQUEST — {symbol}
{"═" * 50}
Symbol: {symbol} ({sector})

PRICE DATA
  Current Price: ${price:.2f}
  52-Week High: ${context.get('high_52w', 0):.2f}
  52-Week Low: ${context.get('low_52w', 0):.2f}
  Change Today: {context.get('change_pct', 0):.2%}

MOVING AVERAGES
{chr(10).join(trend_lines) if trend_lines else '  Unavailable'}

TREND INDICATORS
  ADX(14): {_fmt(indicators.get('adx_14'))}
  Parabolic SAR: {_sar_label(indicators.get('parabolic_sar_signal'))}
  EMA12/26 Cross: {_cross_label(indicators.get('ema12_ema26_cross'))}
  SMA20/50 Cross: {_cross_label(indicators.get('sma20_sma50_cross'))}

MOMENTUM
  RSI(14): {_fmt(indicators.get('rsi_14'))}
  MACD: {_fmt(indicators.get('macd'), 4)}
  MACD Signal: {_fmt(indicators.get('macd_signal'), 4)}
  MACD Histogram: {_fmt(indicators.get('macd_histogram'), 4)}
  Stochastic %K: {_fmt(indicators.get('stoch_k'))}
  Stochastic %D: {_fmt(indicators.get('stoch_d'))}
  Williams %R: {_fmt(indicators.get('williams_r'))}
  CCI(20): {_fmt(indicators.get('cci_20'))}
  ROC(10): {_fmt(indicators.get('roc_10'))}

VOLATILITY
  ATR(14): ${_fmt(indicators.get('atr_14'), 3)}
  ATR Ratio: {_fmt(indicators.get('atr_ratio'), 4)}
  BB High: ${_fmt(indicators.get('bb_high'), 2)}
  BB Low: ${_fmt(indicators.get('bb_low'), 2)}
  BB Position: {_fmt(indicators.get('bb_position'), 3)}
  BB Squeeze: {_fmt(indicators.get('bb_squeeze'), 4)}
  Keltner Position: {_fmt(indicators.get('keltner_position'), 3)}

VOLUME
  Volume vs 20d Avg: {_fmt(indicators.get('volume_vs_sma20'))}x
  Volume vs 5d Avg: {_fmt(indicators.get('volume_ratio_5d'))}x
  OBV Slope (5d): {_fmt(indicators.get('obv_slope'))}
  VWAP: ${_fmt(indicators.get('vwap'), 2)}
  VWAP Diff: ${_fmt(indicators.get('vwap_diff'), 2)}

RETURNS
  1-Day: {_pct(indicators.get('return_1d'))}
  5-Day: {_pct(indicators.get('return_5d'))}
  10-Day: {_pct(indicators.get('return_10d'))}
  20-Day: {_pct(indicators.get('return_20d'))}

MARKET CONTEXT
  SPY Today: {context.get('spy_change', 0):.2%}
  VIX: {context.get('vix', 0):.1f}
  VIX Change: {context.get('vix_change', 0):.2%}
  Sector: {sector}

NEWS & CATALYSTS
{context.get('recent_news', 'No recent news available.')}

UPCOMING EVENTS:
{context.get('upcoming_events', 'None known.')}

Provide your comprehensive analysis."""

    # ─── Response Parsers ───

    def _parse_review(self, text: str, signal: dict) -> AnalystReview:
        """Parse signal review response."""
        try:
            data = _extract_json(text)
            return AnalystReview(
                adjusted_confidence=float(data.get("adjusted_confidence", signal["confidence"])),
                confidence_adjustment=int(data.get("confidence_adjustment", 0)),
                position_sizing=data.get("position_sizing", "conservative"),
                reasoning=data.get("reasoning", "No reasoning provided."),
                risk_flags=data.get("risk_flags", []),
                approve=data.get("approve", True),
            )
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
            logger.warning("Failed to parse review response: %s", e)
            return AnalystReview(
                adjusted_confidence=signal["confidence"] * 0.9,
                confidence_adjustment=-10,
                position_sizing="conservative",
                reasoning=f"Parse error — applying conservative defaults. Raw: {text[:200]}",
                risk_flags=["parse_error"],
                approve=signal["confidence"] > 0.70,
            )

    def _parse_analysis(self, text: str, symbol: str, context: dict) -> SymbolAnalysis:
        """Parse deep analysis response."""
        price = context.get("price", 0)
        atr = context.get("indicators", {}).get("atr_14", price * 0.02) or (price * 0.02)

        try:
            data = _extract_json(text)
            return SymbolAnalysis(
                symbol=data.get("symbol", symbol),
                direction=data.get("direction", "neutral"),
                conviction=int(data.get("conviction", 5)),
                timeframe=data.get("timeframe", "swing"),
                technical_outlook=data.get("technical_outlook", ""),
                volatility_assessment=data.get("volatility_assessment", ""),
                risk_factors=data.get("risk_factors", []),
                entry_zone=data.get("entry_zone", {"low": price * 0.99, "high": price * 1.01}),
                stop_loss=float(data.get("stop_loss", price - 2 * atr)),
                take_profit_1=float(data.get("take_profit_1", price + 3 * atr)),
                take_profit_2=float(data["take_profit_2"]) if data.get("take_profit_2") else None,
                risk_reward_ratio=float(data.get("risk_reward_ratio", 1.5)),
                key_levels=data.get("key_levels", {"support": [], "resistance": []}),
                summary=data.get("summary", "Analysis completed."),
            )
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
            logger.warning("Failed to parse analysis response: %s", e)
            return SymbolAnalysis(
                symbol=symbol,
                direction="neutral",
                conviction=3,
                timeframe="swing",
                technical_outlook=f"Parse error — review raw response. Raw: {text[:300]}",
                volatility_assessment="Unable to parse.",
                risk_factors=["parse_error"],
                entry_zone={"low": price * 0.99, "high": price * 1.01},
                stop_loss=round(price - 2 * atr, 2) if price else 0,
                take_profit_1=round(price + 3 * atr, 2) if price else 0,
                take_profit_2=None,
                risk_reward_ratio=1.5,
                key_levels={"support": [], "resistance": []},
                summary=f"Analysis parse failed for {symbol}.",
            )


# ─── Helpers ───

def _extract_json(text: str) -> dict:
    """Extract JSON from Claude response, handling markdown code blocks."""
    clean = text.strip()
    if clean.startswith("```"):
        clean = clean.split("\n", 1)[1]
        clean = clean.rsplit("```", 1)[0]
    return json.loads(clean)


def _fmt(val, decimals=1) -> str:
    if val is None:
        return "N/A"
    try:
        return f"{float(val):.{decimals}f}"
    except (ValueError, TypeError):
        return str(val)


def _pct(val) -> str:
    if val is None:
        return "N/A"
    try:
        return f"{float(val):.2%}"
    except (ValueError, TypeError):
        return str(val)


def _cross_label(val) -> str:
    if val == 1.0:
        return "BULLISH"
    elif val == -1.0:
        return "BEARISH"
    return "N/A"


def _sar_label(val) -> str:
    if val == 1.0:
        return "BULLISH (price above SAR)"
    elif val == -1.0:
        return "BEARISH (price below SAR)"
    return "N/A"
