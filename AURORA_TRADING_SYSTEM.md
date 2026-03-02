# 🌅 AURORA — Automated Unified Real-time Orchestrated Analytics

## Autonomous Stock Analysis & Trading System — Project Blueprint

> **Version:** 1.0.0
> **Deployment:** Web-based (Lightweight)
> **Phase Strategy:** Build → Paper Trade → Go Live (Small Capital)
> **AI Engine:** Claude API + Lightweight ML Models
> **Security First | Loss Limited | Fully Auditable**

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture & Tech Stack](#2-architecture--tech-stack)
3. [Directory Structure](#3-directory-structure)
4. [Module Breakdown](#4-module-breakdown)
5. [Data Pipeline](#5-data-pipeline)
6. [AI & ML Strategy Engine](#6-ai--ml-strategy-engine)
7. [Risk Management & Loss Limiter](#7-risk-management--loss-limiter)
8. [Security Framework](#8-security-framework)
9. [Trading Execution Engine](#9-trading-execution-engine)
10. [Web Dashboard](#10-web-dashboard)
11. [Audit System](#11-audit-system)
12. [Deployment Phases](#12-deployment-phases)
13. [Build Order](#13-build-order)
14. [Configuration & Environment](#14-configuration--environment)
15. [Testing Strategy](#15-testing-strategy)

---

## 1. Project Overview

### What AURORA Does

AURORA is a **fully automated, self-contained** stock analysis and trading system that:

- Continuously ingests real-time and historical market data
- Runs ML-based signal analysis using lightweight models (no GPU required)
- Uses Claude API as a "Smart Finance Analyst" for contextual reasoning about trades
- Executes trades autonomously through a brokerage API under strict risk limits
- Provides a clean web dashboard for monitoring, override, and audit
- Logs every single decision, trade, and reasoning chain for full auditability

### Core Principles

| Principle | Implementation |
|---|---|
| **No Security Risk** | Encrypted secrets, no exposed APIs, RBAC, rate limiting, HTTPS only |
| **No Major Money Loss** | Hard daily/weekly/monthly loss caps, per-trade limits, circuit breakers |
| **Fully Auditable** | Every decision logged with reasoning, exportable audit reports |
| **No Bloat** | Zero unnecessary modules — everything connects to the core trading loop |
| **Lightweight** | Runs on a standard VPS (2-4 CPU, 4-8GB RAM), no GPU needed |
| **Maximum Automation** | Human intervention only for emergencies and configuration changes |

---

## 2. Architecture & Tech Stack

### Why This Stack

We use **Python (FastAPI)** for the backend because it has the richest ecosystem for finance/ML, and **React (Vite)** for the frontend because it's fast and lightweight. Everything runs in Docker for easy deployment.

```
┌─────────────────────────────────────────────────────────────────┐
│                        AURORA SYSTEM                            │
│                                                                 │
│  ┌──────────┐  ┌──────────────┐  ┌────────────────────────┐    │
│  │  React   │  │   FastAPI    │  │   Background Workers   │    │
│  │  Vite    │◄─┤   Backend    │◄─┤                        │    │
│  │Dashboard │  │   + WS       │  │  • Data Ingestion      │    │
│  └──────────┘  └──────┬───────┘  │  • Signal Engine       │    │
│                       │          │  • Trade Executor       │    │
│                       ▼          │  • Risk Monitor         │    │
│               ┌──────────────┐   │  • Claude Analyst       │    │
│               │  PostgreSQL  │   │  • Audit Logger         │    │
│               │  + Redis     │   └────────────────────────┘    │
│               └──────────────┘                                  │
│                       │                                         │
│          ┌────────────┼────────────────┐                        │
│          ▼            ▼                ▼                         │
│   ┌──────────┐ ┌────────────┐  ┌─────────────┐                 │
│   │ Alpaca   │ │ Market     │  │  Claude     │                 │
│   │ Broker   │ │ Data APIs  │  │  API        │                 │
│   │ API      │ │ (free tier)│  │  (Analyst)  │                 │
│   └──────────┘ └────────────┘  └─────────────┘                 │
└─────────────────────────────────────────────────────────────────┘
```

### Tech Stack Summary

| Layer | Technology | Reason |
|---|---|---|
| **Backend** | Python 3.12 + FastAPI | Best finance/ML ecosystem, async, fast |
| **Frontend** | React 18 + Vite + TailwindCSS | Lightweight, fast builds, clean UI |
| **Database** | PostgreSQL 16 | Reliable, ACID, great for time-series with extensions |
| **Cache/Queue** | Redis 7 | Pub/sub for real-time, task queue, caching |
| **Task Runner** | APScheduler (in-process) | No extra infra needed (no Celery/RabbitMQ bloat) |
| **Broker API** | Alpaca Markets (free) | Commission-free, paper trading built-in, REST + WebSocket |
| **Market Data** | Alpaca Data API + yfinance (fallback) | Free tier sufficient, real-time streaming |
| **ML Engine** | scikit-learn + LightGBM + statsmodels | CPU-only, fast training, proven for finance |
| **AI Analyst** | Claude API (Sonnet) | Contextual trade reasoning, news analysis |
| **Containerization** | Docker + Docker Compose | One-command deploy |
| **Charts** | Lightweight Charts (TradingView lib) | Professional financial charts, open source |

---

## 3. Directory Structure

```
aurora/
├── docker-compose.yml
├── .env.example                  # Template — never commit .env
├── Makefile                      # Convenience commands
├── README.md
│
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── alembic.ini               # DB migrations
│   ├── alembic/
│   │   └── versions/
│   │
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py               # FastAPI app entry
│   │   ├── config.py             # Pydantic settings (from env)
│   │   ├── database.py           # DB session manager
│   │   │
│   │   ├── models/               # SQLAlchemy ORM models
│   │   │   ├── __init__.py
│   │   │   ├── market_data.py    # OHLCV, indicators
│   │   │   ├── signals.py        # Generated signals
│   │   │   ├── trades.py         # Trade records
│   │   │   ├── portfolio.py      # Holdings, P&L
│   │   │   ├── audit_log.py      # Full audit trail
│   │   │   └── risk_events.py    # Circuit breaker events
│   │   │
│   │   ├── api/                  # REST + WebSocket endpoints
│   │   │   ├── __init__.py
│   │   │   ├── router.py         # Main router aggregator
│   │   │   ├── dashboard.py      # Dashboard data endpoints
│   │   │   ├── trades.py         # Trade history & manual override
│   │   │   ├── portfolio.py      # Portfolio status
│   │   │   ├── signals.py        # Active signals
│   │   │   ├── audit.py          # Audit report endpoints
│   │   │   ├── settings.py       # Runtime config endpoints
│   │   │   └── ws.py             # WebSocket for real-time updates
│   │   │
│   │   ├── core/                 # Core business logic
│   │   │   ├── __init__.py
│   │   │   ├── data_ingestion.py # Market data fetcher
│   │   │   ├── indicators.py     # Technical indicator calculations
│   │   │   ├── signal_engine.py  # ML signal generator
│   │   │   ├── claude_analyst.py # Claude API integration
│   │   │   ├── trade_executor.py # Order placement & management
│   │   │   ├── risk_manager.py   # Loss limiter & circuit breakers
│   │   │   ├── portfolio_tracker.py # Position & P&L tracking
│   │   │   ├── scheduler.py      # APScheduler job definitions
│   │   │   └── audit_logger.py   # Structured audit logging
│   │   │
│   │   ├── ml/                   # Machine learning models
│   │   │   ├── __init__.py
│   │   │   ├── feature_engineering.py
│   │   │   ├── model_trainer.py
│   │   │   ├── model_registry.py # Versioned model storage
│   │   │   ├── predictor.py      # Inference pipeline
│   │   │   └── backtester.py     # Historical backtesting
│   │   │
│   │   └── security/             # Security layer
│   │       ├── __init__.py
│   │       ├── auth.py           # JWT auth for dashboard
│   │       ├── encryption.py     # Secret encryption utilities
│   │       ├── rate_limiter.py   # API rate limiting
│   │       └── validators.py     # Input sanitization
│   │
│   └── tests/
│       ├── conftest.py
│       ├── test_risk_manager.py
│       ├── test_signal_engine.py
│       ├── test_trade_executor.py
│       ├── test_claude_analyst.py
│       └── test_backtester.py
│
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── index.html
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── api/                  # API client
│       │   └── client.js
│       ├── components/
│       │   ├── Layout.jsx
│       │   ├── Sidebar.jsx
│       │   ├── charts/
│       │   │   ├── PriceChart.jsx      # TradingView lightweight
│       │   │   ├── PortfolioChart.jsx
│       │   │   └── SignalOverlay.jsx
│       │   ├── dashboard/
│       │   │   ├── StatusCards.jsx
│       │   │   ├── ActivePositions.jsx
│       │   │   ├── RecentTrades.jsx
│       │   │   └── RiskGauge.jsx
│       │   ├── audit/
│       │   │   ├── AuditTimeline.jsx
│       │   │   └── AuditExport.jsx
│       │   └── controls/
│       │       ├── EmergencyStop.jsx    # Kill switch
│       │       ├── ModeToggle.jsx       # Paper / Live
│       │       └── RiskSettings.jsx
│       ├── pages/
│       │   ├── Dashboard.jsx
│       │   ├── Trades.jsx
│       │   ├── Signals.jsx
│       │   ├── Audit.jsx
│       │   ├── Settings.jsx
│       │   └── Login.jsx
│       └── hooks/
│           ├── useWebSocket.js
│           └── usePortfolio.js
│
└── scripts/
    ├── seed_historical_data.py   # Initial data load
    ├── run_backtest.py           # CLI backtesting
    ├── generate_audit_report.py  # Full audit PDF export
    └── health_check.py           # System health probe
```

---

## 4. Module Breakdown

### Every module exists for one reason — to serve the core trading loop:

```
DATA IN → ANALYZE → DECIDE → RISK CHECK → EXECUTE → LOG → REPEAT
```

| Module | Purpose | Connects To |
|---|---|---|
| `data_ingestion` | Fetches OHLCV + news | Signal Engine, Indicators |
| `indicators` | Computes TA indicators (RSI, MACD, BB, etc.) | Signal Engine |
| `signal_engine` | ML model generates BUY/SELL/HOLD signals | Claude Analyst |
| `claude_analyst` | Claude reviews signals with market context | Trade Executor |
| `risk_manager` | Validates trade against all risk rules | Trade Executor |
| `trade_executor` | Places orders via Alpaca API | Portfolio Tracker |
| `portfolio_tracker` | Tracks positions, P&L, exposure | Risk Manager, Dashboard |
| `audit_logger` | Records every decision with full context | Audit endpoints |
| `scheduler` | Orchestrates the trading loop timing | All core modules |

**There are no orphan modules.** Everything feeds the loop.

---

## 5. Data Pipeline

### 5.1 Data Sources (All Free Tier)

| Source | Data | Frequency |
|---|---|---|
| **Alpaca Market Data API** | Real-time quotes, OHLCV bars, trade stream | Streaming / 1min bars |
| **yfinance** (fallback) | Historical OHLCV, fundamentals | Daily (backup only) |
| **Alpaca News API** | Market news headlines | Real-time |
| **FRED API** (optional) | Economic indicators (VIX, rates) | Daily |

### 5.2 Ingestion Flow

```python
# Pseudocode — data_ingestion.py

class DataIngestion:
    """
    Runs on scheduler every 1 minute during market hours.
    Streams real-time during active trading.
    """

    async def ingest_bars(self, symbols: list[str]):
        """Fetch latest 1-min OHLCV bars for watchlist."""
        bars = await alpaca_client.get_bars(symbols, timeframe="1Min", limit=1)
        await db.bulk_insert(MarketData, bars)
        await redis.publish("new_bars", symbols)

    async def ingest_daily(self, symbols: list[str]):
        """End-of-day full bar fetch + indicator computation."""
        bars = await alpaca_client.get_bars(symbols, timeframe="1Day", limit=200)
        indicators = compute_all_indicators(bars)
        await db.bulk_insert(MarketData, bars)
        await db.bulk_insert(Indicators, indicators)

    async def ingest_news(self, symbols: list[str]):
        """Fetch recent news for Claude context."""
        news = await alpaca_client.get_news(symbols, limit=10)
        return news  # Passed directly to Claude, not stored long-term
```

### 5.3 Watchlist Management

The system trades a **focused watchlist** (10-25 liquid stocks/ETFs) to keep compute and API usage low:

```python
DEFAULT_WATCHLIST = [
    # High-liquidity, well-covered stocks
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA",
    "META", "TSLA", "JPM", "V", "UNH",
    # ETFs for sector/market exposure
    "SPY", "QQQ", "IWM", "XLF", "XLE",
]
```

Users can customize this via the dashboard settings.

---

## 6. AI & ML Strategy Engine

### 6.1 Technical Indicators Computed

All indicators calculated using `pandas` + `ta-lib` (or pure pandas fallback):

| Category | Indicators |
|---|---|
| **Trend** | SMA(20,50,200), EMA(12,26), MACD, ADX, Parabolic SAR |
| **Momentum** | RSI(14), Stochastic(14,3), Williams %R, CCI(20), ROC |
| **Volatility** | Bollinger Bands(20,2), ATR(14), Keltner Channels |
| **Volume** | OBV, VWAP, Volume SMA(20), Accumulation/Distribution |
| **Custom** | Price vs SMA ratios, Multi-timeframe RSI divergence |

### 6.2 ML Signal Generator

**Model:** LightGBM Classifier (lightweight, fast, CPU-friendly, handles tabular data exceptionally well)

**Why LightGBM over deep learning?**
- Trains in seconds on CPU
- Handles missing data natively
- Feature importance built-in (auditable)
- Proven superior to neural nets on structured/tabular financial data
- No GPU, no PyTorch, no TensorFlow — minimal dependencies

```python
# Pseudocode — signal_engine.py

class SignalEngine:
    """
    Generates BUY / SELL / HOLD signals with confidence scores.
    Retrains weekly on rolling window of data.
    """

    def generate_signal(self, symbol: str) -> Signal:
        features = self.feature_engineering.build(symbol)  # ~50 features
        prediction = self.model.predict_proba(features)

        signal = Signal(
            symbol=symbol,
            action=self._classify(prediction),   # BUY/SELL/HOLD
            confidence=float(max(prediction)),     # 0.0 - 1.0
            features_snapshot=features.to_dict(),  # For audit
            model_version=self.model_registry.current_version,
            timestamp=utcnow()
        )
        return signal

    def _classify(self, proba) -> str:
        # Only act on high-confidence signals
        buy_prob, hold_prob, sell_prob = proba
        if buy_prob > 0.65:
            return "BUY"
        elif sell_prob > 0.65:
            return "SELL"
        return "HOLD"
```

### 6.3 Feature Engineering

```python
# feature_engineering.py — builds the feature vector for each symbol

FEATURES = {
    # Price-based (10)
    "return_1d", "return_5d", "return_10d", "return_20d",
    "high_low_ratio", "close_open_ratio",
    "price_vs_sma20", "price_vs_sma50", "price_vs_sma200",
    "gap_percentage",

    # Technical indicators (20)
    "rsi_14", "macd_signal_diff", "macd_histogram",
    "bb_position",  # Where price is within Bollinger Bands (0-1)
    "adx_14", "cci_20", "stoch_k", "stoch_d",
    "obv_slope", "vwap_diff", "atr_14", "atr_ratio",
    "williams_r", "parabolic_sar_signal",
    "ema12_ema26_cross", "sma20_sma50_cross",
    "volume_vs_sma20", "volume_ratio_5d",
    "keltner_position", "roc_10",

    # Multi-timeframe (8)
    "rsi_1h", "rsi_4h", "macd_1h", "macd_daily",
    "trend_alignment_score",   # How many timeframes agree
    "bb_squeeze",              # Volatility contraction
    "volume_breakout_score",
    "momentum_divergence",

    # Market context (5)
    "spy_return_1d", "vix_level", "vix_change",
    "sector_relative_strength", "market_breadth",

    # Derived / interaction (7)
    "rsi_macd_agreement",      # Both bullish/bearish?
    "volume_price_confirmation",
    "trend_strength_composite",
    "mean_reversion_score",
    "breakout_probability",
    "support_resistance_proximity",
    "claude_sentiment_score",  # From Claude analysis
}
# Total: ~50 features
```

### 6.4 Claude Smart Finance Analyst Integration

Claude acts as a **secondary analyst** that reviews ML signals before execution:

```python
# claude_analyst.py

class ClaudeAnalyst:
    """
    Uses Claude API to provide contextual analysis.
    Reviews every signal before it becomes a trade.
    """

    SYSTEM_PROMPT = """You are AURORA's senior financial analyst.
    You receive ML-generated trading signals with supporting data.

    Your job:
    1. Evaluate the signal quality given current market context
    2. Check for risks the ML model might miss (earnings, news, macro)
    3. Provide a CONFIDENCE ADJUSTMENT (-30 to +20 points)
    4. Flag any concerns
    5. Suggest position sizing (conservative/normal/aggressive)

    RULES:
    - Always err on the side of caution
    - Flag if earnings are within 5 days (avoid holding through earnings)
    - Flag unusual volume or price action
    - Consider sector rotation and macro trends
    - Be skeptical of signals during high VIX (>25)

    Respond ONLY in this JSON format:
    {
        "adjusted_confidence": <float 0-1>,
        "confidence_adjustment": <int -30 to +20>,
        "position_sizing": "conservative" | "normal" | "aggressive",
        "reasoning": "<2-3 sentence explanation>",
        "risk_flags": ["<flag1>", "<flag2>"],
        "approve": true | false
    }"""

    async def review_signal(self, signal: Signal, context: dict) -> AnalystReview:
        prompt = self._build_prompt(signal, context)

        response = await anthropic_client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=500,
            system=self.SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}]
        )

        review = parse_json(response.content[0].text)
        # Log the full Claude reasoning for audit
        await audit_logger.log("claude_review", {
            "signal": signal.dict(),
            "review": review,
            "prompt_tokens": response.usage.input_tokens,
            "response_tokens": response.usage.output_tokens,
        })
        return AnalystReview(**review)

    def _build_prompt(self, signal: Signal, context: dict) -> str:
        return f"""
        SIGNAL REVIEW REQUEST:
        Symbol: {signal.symbol}
        Action: {signal.action}
        ML Confidence: {signal.confidence:.1%}
        Model Version: {signal.model_version}

        CURRENT DATA:
        Price: ${context['price']:.2f}
        Change Today: {context['change_pct']:.2%}
        Volume vs Avg: {context['volume_ratio']:.1f}x
        RSI(14): {context['rsi']:.1f}
        MACD Signal: {context['macd_signal']}
        52w High/Low: ${context['high_52w']:.2f} / ${context['low_52w']:.2f}

        MARKET CONTEXT:
        SPY Today: {context['spy_change']:.2%}
        VIX: {context['vix']:.1f}
        Sector Performance: {context['sector_perf']}

        RECENT NEWS:
        {context['recent_news']}

        UPCOMING EVENTS:
        {context['upcoming_events']}

        Please review and provide your assessment.
        """
```

### 6.5 Model Retraining Pipeline

```python
# model_trainer.py

class ModelTrainer:
    """
    Automated weekly retraining on rolling 2-year window.
    Walk-forward validation to prevent look-ahead bias.
    """

    RETRAIN_SCHEDULE = "weekly"  # Every Sunday
    TRAINING_WINDOW = 504        # ~2 years of trading days
    VALIDATION_WINDOW = 63       # ~3 months
    MIN_ACCURACY_THRESHOLD = 0.52  # Must beat random

    async def retrain(self):
        # 1. Build features from rolling window
        X_train, y_train = self.build_dataset(window=self.TRAINING_WINDOW)
        X_val, y_val = self.build_dataset(window=self.VALIDATION_WINDOW, offset=True)

        # 2. Train LightGBM with walk-forward CV
        model = lgb.LGBMClassifier(
            n_estimators=500,
            max_depth=6,
            learning_rate=0.05,
            num_leaves=31,
            min_child_samples=20,
            reg_alpha=0.1,
            reg_lambda=0.1,
            class_weight="balanced",
            random_state=42,
        )
        model.fit(X_train, y_train,
                  eval_set=[(X_val, y_val)],
                  callbacks=[lgb.early_stopping(50)])

        # 3. Validate — must pass minimum thresholds
        metrics = self.evaluate(model, X_val, y_val)
        if metrics["accuracy"] < self.MIN_ACCURACY_THRESHOLD:
            await audit_logger.log("model_retrain_rejected", metrics)
            return  # Keep old model

        # 4. Register new model version
        version = await self.model_registry.register(model, metrics)
        await audit_logger.log("model_retrain_success", {
            "version": version,
            "metrics": metrics,
            "feature_importance": dict(zip(
                self.feature_names,
                model.feature_importances_
            ))
        })
```

---

## 7. Risk Management & Loss Limiter

### 🚨 THIS IS THE MOST CRITICAL MODULE 🚨

The risk manager has **absolute authority** — it can veto any trade and halt the entire system.

### 7.1 Hard Limits (Non-negotiable)

```python
# risk_manager.py

class RiskConfig(BaseModel):
    """All limits configurable via dashboard, but with hard maximums."""

    # === PER-TRADE LIMITS ===
    max_position_pct: float = 5.0          # Max 5% of portfolio per trade
    max_position_pct_hard: float = 10.0     # HARD CAP — cannot exceed
    max_shares_per_order: int = 500         # Prevent fat-finger
    min_confidence: float = 0.60            # Minimum signal confidence

    # === PORTFOLIO LIMITS ===
    max_open_positions: int = 8             # Max simultaneous positions
    max_sector_exposure_pct: float = 30.0   # Max 30% in one sector
    max_single_stock_pct: float = 15.0      # Max 15% in one stock (inc. unrealized)
    max_total_exposure_pct: float = 80.0    # Keep 20% cash minimum

    # === LOSS LIMITS (CIRCUIT BREAKERS) ===
    max_loss_per_trade_pct: float = 2.0     # Stop loss: -2% per trade
    max_daily_loss_pct: float = 3.0         # Halt trading if down 3% today
    max_weekly_loss_pct: float = 5.0        # Halt trading if down 5% this week
    max_monthly_loss_pct: float = 8.0       # Halt trading if down 8% this month
    max_drawdown_pct: float = 12.0          # FULL STOP if 12% drawdown from peak

    # === TIMING LIMITS ===
    no_trade_first_minutes: int = 15        # Skip first 15 min (high volatility)
    no_trade_last_minutes: int = 10         # Skip last 10 min
    max_trades_per_day: int = 10            # Prevent overtrading
    min_hold_minutes: int = 30              # Minimum hold time (avoid churn)

    # === VOLATILITY LIMITS ===
    max_vix_for_new_trades: float = 35.0    # No new positions if VIX > 35
    reduce_size_vix_threshold: float = 25.0 # Half position sizes if VIX > 25
```

### 7.2 Circuit Breaker System

```python
class CircuitBreaker:
    """
    Three levels of circuit breakers.
    Each level is more restrictive.
    """

    LEVELS = {
        "YELLOW": {
            "trigger": "daily_loss > 1.5%",
            "action": "reduce_position_sizes_50pct",
            "resume": "next_trading_day",
        },
        "ORANGE": {
            "trigger": "daily_loss > 3% OR weekly_loss > 5%",
            "action": "halt_new_trades_allow_exits",
            "resume": "manual_review_required",
        },
        "RED": {
            "trigger": "monthly_loss > 8% OR drawdown > 12%",
            "action": "close_all_positions_halt_system",
            "resume": "manual_restart_only",
        },
    }
```

### 7.3 Pre-Trade Risk Check Flow

```
Signal Generated
       │
       ▼
┌─────────────────┐     NO
│ Circuit Breaker  ├──────────► REJECT (system halted)
│ Status OK?       │
└───────┬─────────┘
        │ YES
        ▼
┌─────────────────┐     NO
│ Confidence >     ├──────────► REJECT (low confidence)
│ min_threshold?   │
└───────┬─────────┘
        │ YES
        ▼
┌─────────────────┐     NO
│ Within daily     ├──────────► REJECT (trade limit reached)
│ trade limit?     │
└───────┬─────────┘
        │ YES
        ▼
┌─────────────────┐     NO
│ Position size    ├──────────► RESIZE to max allowed
│ within limits?   │
└───────┬─────────┘
        │ YES
        ▼
┌─────────────────┐     NO
│ Portfolio        ├──────────► REJECT (overexposed)
│ exposure OK?     │
└───────┬─────────┘
        │ YES
        ▼
┌─────────────────┐     NO
│ Sector exposure  ├──────────► REJECT (sector concentrated)
│ OK?              │
└───────┬─────────┘
        │ YES
        ▼
┌─────────────────┐     NO
│ Market timing    ├──────────► QUEUE for later
│ OK? (not open/   │
│ close window)    │
└───────┬─────────┘
        │ YES
        ▼
   ✅ APPROVED → Execute Trade with Stop Loss
```

---

## 8. Security Framework

### 8.1 Secrets Management

```python
# NEVER store secrets in code or config files

# .env.example (template only — .env is gitignored)
ALPACA_API_KEY=your_key_here
ALPACA_SECRET_KEY=your_secret_here
ANTHROPIC_API_KEY=your_key_here
DB_PASSWORD=your_password_here
JWT_SECRET=generate_random_64_chars
ENCRYPTION_KEY=generate_random_32_bytes_base64

# All secrets loaded via Pydantic Settings
class Settings(BaseSettings):
    alpaca_api_key: SecretStr
    alpaca_secret_key: SecretStr
    anthropic_api_key: SecretStr
    db_password: SecretStr
    jwt_secret: SecretStr

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
```

### 8.2 Security Measures

| Layer | Measure |
|---|---|
| **API Keys** | Stored in `.env`, loaded as `SecretStr`, never logged |
| **Dashboard Auth** | JWT with bcrypt password hashing, session expiry |
| **HTTPS** | TLS termination via reverse proxy (Caddy/nginx) |
| **CORS** | Strict origin whitelist |
| **Rate Limiting** | 100 req/min per IP on all endpoints |
| **SQL Injection** | SQLAlchemy ORM only — no raw SQL |
| **Input Validation** | Pydantic models on all inputs |
| **Dependency Audit** | `pip-audit` in CI, automated alerts |
| **Docker** | Non-root user, read-only filesystem where possible |
| **Broker Permissions** | Alpaca key scoped to trading only (no withdrawal) |
| **Logging** | Secrets auto-redacted in all logs |

### 8.3 Authentication Flow

```python
# auth.py — Simple JWT auth for the dashboard

# IMPORTANT: Single-user system. No registration endpoint.
# User is created via CLI command during setup:
#   python -m app.security.auth create-user --username admin

class AuthConfig:
    ACCESS_TOKEN_EXPIRE_MINUTES = 30
    ALGORITHM = "HS256"

@router.post("/login")
async def login(credentials: LoginSchema):
    user = await verify_password(credentials.username, credentials.password)
    if not user:
        raise HTTPException(401, "Invalid credentials")
    token = create_access_token({"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}
```

---

## 9. Trading Execution Engine

### 9.1 Order Types Used

| Scenario | Order Type | Why |
|---|---|---|
| **Entry (BUY)** | Limit Order (slightly above ask) | Avoid slippage |
| **Entry (SELL/SHORT)** | Limit Order (slightly below bid) | Avoid slippage |
| **Stop Loss** | Stop-Limit Order | Hard protection floor |
| **Take Profit** | Limit Order (at target) | Lock in gains |
| **Emergency Exit** | Market Order | Speed over price |

### 9.2 Execution Flow

```python
# trade_executor.py

class TradeExecutor:
    """
    Handles order lifecycle: create → monitor → fill → track → exit.
    """

    async def execute(self, signal: Signal, review: AnalystReview) -> Trade:
        # 1. Calculate position size
        size = self.position_sizer.calculate(
            signal=signal,
            review=review,
            portfolio=await self.portfolio.get_current(),
            risk_config=self.risk_config,
        )

        # 2. Final risk check
        approved = await self.risk_manager.pre_trade_check(signal, size)
        if not approved:
            await audit_logger.log("trade_rejected_risk", {
                "signal": signal.dict(),
                "reason": approved.reason
            })
            return None

        # 3. Place entry order with attached stop-loss
        entry_order = await self.alpaca.submit_order(
            symbol=signal.symbol,
            qty=size.shares,
            side="buy" if signal.action == "BUY" else "sell",
            type="limit",
            limit_price=size.limit_price,
            time_in_force="day",
            order_class="bracket",  # Bracket order: entry + stop + target
            stop_loss={"stop_price": size.stop_price},
            take_profit={"limit_price": size.target_price},
        )

        # 4. Record everything
        trade = Trade(
            signal_id=signal.id,
            order_id=entry_order.id,
            symbol=signal.symbol,
            side=signal.action,
            shares=size.shares,
            entry_price=size.limit_price,
            stop_price=size.stop_price,
            target_price=size.target_price,
            status="pending",
            claude_reasoning=review.reasoning,
            ml_confidence=signal.confidence,
            claude_confidence=review.adjusted_confidence,
        )
        await db.insert(trade)
        await audit_logger.log("trade_placed", trade.dict())

        return trade
```

### 9.3 Position Sizing Algorithm

```python
class PositionSizer:
    """
    Kelly-criterion inspired sizing with conservative fractional application.
    """

    def calculate(self, signal, review, portfolio, risk_config) -> PositionSize:
        portfolio_value = portfolio.total_value
        current_price = signal.current_price

        # Base allocation from confidence
        base_pct = self._confidence_to_allocation(review.adjusted_confidence)

        # Apply Claude's sizing recommendation
        sizing_multiplier = {
            "conservative": 0.5,
            "normal": 1.0,
            "aggressive": 1.25,  # Still capped by hard limits
        }[review.position_sizing]

        # Apply VIX adjustment
        vix_multiplier = 1.0
        if portfolio.vix > risk_config.reduce_size_vix_threshold:
            vix_multiplier = 0.5

        # Calculate final position
        allocation_pct = min(
            base_pct * sizing_multiplier * vix_multiplier,
            risk_config.max_position_pct  # Hard cap
        )
        dollar_amount = portfolio_value * (allocation_pct / 100)
        shares = int(dollar_amount / current_price)

        # Calculate stop and target
        atr = signal.features["atr_14"]
        stop_price = current_price - (2.0 * atr)     # 2x ATR stop
        target_price = current_price + (3.0 * atr)    # 3x ATR target (1.5:1 R/R)

        return PositionSize(
            shares=shares,
            dollar_amount=dollar_amount,
            allocation_pct=allocation_pct,
            limit_price=round(current_price * 1.001, 2),  # Tiny premium for fill
            stop_price=round(stop_price, 2),
            target_price=round(target_price, 2),
            risk_reward_ratio=3.0 / 2.0,
        )
```

---

## 10. Web Dashboard

### 10.1 Pages & Components

| Page | Purpose | Key Components |
|---|---|---|
| **Dashboard** | At-a-glance system status | P&L card, Portfolio chart, Risk gauge, Active positions, Live price ticker |
| **Trades** | Full trade history | Filterable table, Trade detail modal (shows ML + Claude reasoning), P&L per trade |
| **Signals** | Current & historical signals | Signal strength heatmap, Acceptance rate, Model confidence distribution |
| **Audit** | Complete audit trail | Searchable timeline, Decision chain viewer, Export to PDF/CSV |
| **Settings** | System configuration | Risk limits editor, Watchlist manager, Mode toggle (Paper/Live), Emergency stop |
| **Login** | Authentication | JWT login form |

### 10.2 Real-Time Updates via WebSocket

```javascript
// useWebSocket.js
const useAuroraSocket = () => {
  const ws = useRef(null);
  const [portfolio, setPortfolio] = useState(null);
  const [signals, setSignals] = useState([]);
  const [alerts, setAlerts] = useState([]);

  useEffect(() => {
    ws.current = new WebSocket(`wss://${host}/ws`);
    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      switch (data.type) {
        case "portfolio_update":
          setPortfolio(data.payload);
          break;
        case "new_signal":
          setSignals(prev => [data.payload, ...prev]);
          break;
        case "trade_executed":
          // Trigger notification
          break;
        case "risk_alert":
          setAlerts(prev => [data.payload, ...prev]);
          break;
        case "circuit_breaker":
          // Show emergency modal
          break;
      }
    };
  }, []);
};
```

### 10.3 Emergency Controls

The dashboard has a prominent **EMERGENCY STOP** button that:
1. Cancels all open orders immediately
2. Closes all positions at market price
3. Halts the trading engine
4. Requires manual restart with confirmation
5. Logs the emergency event with timestamp

---

## 11. Audit System

### 11.1 What Gets Logged (Everything)

Every event is stored in `audit_log` table with:

```python
class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    event_type = Column(String(50), index=True)     # e.g., "signal_generated"
    severity = Column(String(10))                     # INFO, WARNING, CRITICAL
    component = Column(String(30))                    # Which module
    symbol = Column(String(10), nullable=True)
    details = Column(JSONB)                           # Full structured payload
    decision_chain_id = Column(UUID, nullable=True)   # Links related events

# LOGGED EVENTS:
# - data_ingestion_complete
# - indicators_computed
# - signal_generated (with full feature snapshot)
# - claude_review (with full prompt + response)
# - risk_check_passed / risk_check_failed (with reason)
# - trade_placed (with all parameters)
# - trade_filled
# - trade_closed (with P&L)
# - stop_loss_triggered
# - circuit_breaker_activated
# - model_retrain_started / completed / rejected
# - system_start / system_stop
# - config_changed (with before/after)
# - error_occurred
# - emergency_stop_activated
```

### 11.2 Decision Chain Tracking

Every trade can be traced through its complete decision chain:

```
Decision Chain: abc-123-def
├── 2025-01-15 10:01:00 — signal_generated (AAPL BUY, confidence 0.72)
├── 2025-01-15 10:01:01 — claude_review (approved, adjusted to 0.68)
├── 2025-01-15 10:01:01 — risk_check_passed (all limits OK)
├── 2025-01-15 10:01:02 — trade_placed (50 shares @ $185.20, stop $181.40)
├── 2025-01-15 10:01:03 — trade_filled (50 shares @ $185.18)
├── 2025-01-15 14:23:15 — trade_closed (target hit @ $190.60, P&L +$271)
└── RESULT: +1.46% return, held 4h22m
```

### 11.3 Audit Report Generation

```python
# generate_audit_report.py

class AuditReportGenerator:
    """
    Generates comprehensive PDF/CSV audit reports.
    Run on-demand or scheduled monthly.
    """

    def generate(self, start_date, end_date) -> AuditReport:
        return AuditReport(
            period=f"{start_date} to {end_date}",
            sections=[
                self.executive_summary(),
                self.trading_performance(),      # Win rate, avg P&L, Sharpe
                self.risk_events_summary(),       # All circuit breaker activations
                self.model_performance(),          # ML accuracy over period
                self.claude_agreement_rate(),      # How often Claude agreed with ML
                self.decision_chain_samples(),     # Random sample of full chains
                self.configuration_changes(),      # All settings changed
                self.error_log(),                  # All errors encountered
                self.recommendations(),            # Auto-generated improvements
            ]
        )
```

---

## 12. Deployment Phases

### Phase 1: BUILD (Weeks 1-3)

Build the system in this order:

```
Week 1: Foundation
├── Day 1-2: Project scaffold, Docker setup, database models
├── Day 3-4: Data ingestion pipeline + indicator computation
├── Day 5-7: ML signal engine + feature engineering

Week 2: Core Logic
├── Day 1-2: Risk manager + circuit breakers
├── Day 3-4: Claude analyst integration
├── Day 5-7: Trade executor + portfolio tracker

Week 3: Interface & Audit
├── Day 1-3: Web dashboard (React)
├── Day 4-5: Audit system + report generation
├── Day 6-7: Integration testing + bug fixes
```

### Phase 2: PAPER TRADING (Weeks 4-7)

```
Week 4-5: Active Paper Trading
├── Deploy with Alpaca paper trading account
├── Run full system during market hours
├── Monitor daily, fix bugs
├── Collect performance data

Week 6-7: Evaluation
├── Generate first audit report
├── Analyze: win rate, Sharpe ratio, max drawdown
├── Compare to SPY benchmark
├── Tune risk parameters based on results
├── Retrain ML model with paper trading feedback
├── Adjust Claude prompts if needed

GATE: Must achieve >50% win rate AND Sharpe >0.5
       AND max drawdown <10% over 4 weeks to proceed
```

### Phase 3: GO LIVE — Small Capital (Week 8+)

```
Week 8: Live Launch
├── Switch Alpaca to live account
├── Fund with SMALL amount ($500-$2,000 MAXIMUM initially)
├── Start with CONSERVATIVE risk settings:
│   ├── max_position_pct: 3% (not 5%)
│   ├── max_open_positions: 4 (not 8)
│   ├── max_daily_loss_pct: 2% (not 3%)
│   └── min_confidence: 0.70 (not 0.60)
├── Monitor closely for 2 weeks
├── Gradually increase limits if performing well

SCALING RULES:
├── After 1 month profitable → increase capital 50%
├── After 3 months profitable → increase to normal risk settings
├── After 6 months profitable → consider scaling capital
├── ANY month with >5% drawdown → reduce capital, review system
```

---

## 13. Build Order

### Build steps in sequence:

```
STEP 1 — SCAFFOLDING:
"Create the AURORA project scaffolding with Docker Compose
(FastAPI backend, React+Vite frontend, PostgreSQL, Redis).
Set up the backend with pyproject.toml including: fastapi, uvicorn,
sqlalchemy[asyncio], asyncpg, alembic, pydantic-settings, redis,
httpx, anthropic, lightgbm, scikit-learn, pandas, numpy, ta,
apscheduler, python-jose[cryptography], passlib[bcrypt], pytest.
Set up the frontend with Vite + React + TailwindCSS + React Router +
lightweight-charts. Create the directory structure as defined in
the blueprint. Include .env.example with all required variables.
Create Makefile with: up, down, logs, migrate, test, seed commands."

STEP 2 — DATABASE MODELS + MIGRATIONS:
"Create all SQLAlchemy models: MarketData, Indicator, Signal, Trade,
Portfolio, AuditLog, RiskEvent. Include proper indexes (symbol+timestamp),
JSONB columns for flexible data, and UUID decision_chain_id linking.
Set up Alembic and create the initial migration."

STEP 3 — DATA INGESTION:
"Build the data ingestion module with Alpaca Markets API integration.
Implement: real-time bar streaming, daily bar fetcher, news fetcher.
Use httpx async client. Store to PostgreSQL. Publish updates to Redis
pub/sub. Include yfinance as fallback for historical data.
Add proper error handling and retry logic."

STEP 4 — TECHNICAL INDICATORS:
"Build the indicator computation module using pandas and the 'ta'
library. Compute all indicators defined in the blueprint (trend,
momentum, volatility, volume). Compute on multiple timeframes
(1min, 1hour, daily). Store results linked to MarketData records.
Make it efficient for batch computation."

STEP 5 — FEATURE ENGINEERING + ML MODEL:
"Build the feature engineering pipeline creating ~50 features as
defined in the blueprint. Build the LightGBM signal generator with
3-class classification (BUY/SELL/HOLD). Implement walk-forward
cross-validation. Include model registry for versioning (save models
as joblib files with metadata). Include the backtester module.
Minimum confidence threshold of 0.65 to generate a signal."

STEP 6 — RISK MANAGER:
"Build the risk manager with ALL limits from the blueprint.
Implement the 3-level circuit breaker system (YELLOW/ORANGE/RED).
Build the complete pre-trade risk check pipeline (10-step validation).
Make all limits configurable via Pydantic settings but with hard
maximums that cannot be exceeded. Log every risk decision."

STEP 7 — CLAUDE ANALYST:
"Build the Claude analyst integration using the Anthropic Python SDK.
Implement the system prompt and review flow as defined in the blueprint.
Parse JSON responses safely with fallback handling. Log full prompts
and responses for audit. Include rate limiting to avoid excessive
API costs. Claude reviews every signal before trade execution."

STEP 8 — TRADE EXECUTOR:
"Build the trade executor using Alpaca API. Implement bracket orders
(entry + stop-loss + take-profit). Build the position sizer with
ATR-based stops and Kelly-inspired sizing. Handle order lifecycle:
pending → filled → closed. Connect to risk manager for pre-trade
validation. Log everything to audit trail."

STEP 9 — PORTFOLIO TRACKER + SCHEDULER:
"Build the portfolio tracker: track all positions, calculate real-time
P&L, track exposure by sector, maintain equity curve history.
Build the APScheduler-based scheduler that orchestrates the full
trading loop: ingest → analyze → decide → risk check → execute → log.
Run every 5 minutes during market hours. Include pre-market
and post-market routines."

STEP 10 — AUDIT LOGGER + REPORT GENERATOR:
"Build the structured audit logging system. Every module should log
to the audit_log table with event_type, severity, component, symbol,
and JSONB details. Implement decision chain tracking with UUID linking.
Build the audit report generator that produces comprehensive
PDF reports with: executive summary, performance metrics, risk events,
model performance, configuration changes, error log."

STEP 11 — API ENDPOINTS + WEBSOCKET:
"Build all FastAPI REST endpoints: dashboard data, trade history,
portfolio status, signals, audit trail, settings management.
Build WebSocket endpoint for real-time updates (portfolio, signals,
alerts, circuit breakers). Include JWT authentication middleware.
Include rate limiting. Include CORS configuration."

STEP 12 — REACT DASHBOARD:
"Build the React frontend with all pages: Dashboard, Trades, Signals,
Audit, Settings, Login. Use TailwindCSS for styling — clean, dark theme,
professional look. Use lightweight-charts for price charts.
Include: P&L cards, portfolio equity curve, risk gauge, active
positions table, recent trades, signal heatmap, audit timeline,
emergency stop button, paper/live mode toggle, risk settings editor.
Connect to backend via API client + WebSocket."

STEP 13 — SECURITY HARDENING:
"Implement all security measures: JWT auth with bcrypt, CORS whitelist,
rate limiting (100 req/min), input validation on all endpoints,
secret redaction in logs, Docker non-root user, Pydantic validators.
Create the CLI command for initial user creation.
Ensure no secrets appear in any log or error output."

STEP 14 — TESTING:
"Write comprehensive tests for: risk_manager (all limits, all circuit
breaker levels), signal_engine (feature engineering, classification),
trade_executor (order flow, error handling), claude_analyst (response
parsing, fallback), backtester (no look-ahead bias validation).
Use pytest + pytest-asyncio. Mock external APIs."

STEP 15 — FINAL INTEGRATION + DOCUMENTATION:
"Run full integration test: data ingestion → signals → claude review →
risk check → paper trade execution → audit log. Fix any issues.
Update README.md with: setup instructions, architecture diagram,
configuration guide, phase deployment guide. Create health_check.py
script for monitoring."
```

---

## 14. Configuration & Environment

### .env.example

```bash
# === AURORA Configuration ===

# --- Mode ---
AURORA_MODE=paper                    # paper | live
AURORA_LOG_LEVEL=INFO

# --- Alpaca (Broker + Data) ---
ALPACA_API_KEY=your_key
ALPACA_SECRET_KEY=your_secret
ALPACA_BASE_URL=https://paper-api.alpaca.markets   # Change for live
ALPACA_DATA_URL=https://data.alpaca.markets

# --- Anthropic (Claude Analyst) ---
ANTHROPIC_API_KEY=your_key
CLAUDE_MODEL=claude-sonnet-4-5-20250929
CLAUDE_MAX_REVIEWS_PER_DAY=50       # Cost control

# --- Database ---
DB_HOST=postgres
DB_PORT=5432
DB_NAME=aurora
DB_USER=aurora
DB_PASSWORD=your_strong_password

# --- Redis ---
REDIS_URL=redis://redis:6379/0

# --- Security ---
JWT_SECRET=generate_64_char_random_string
JWT_EXPIRY_MINUTES=30
ALLOWED_ORIGINS=http://localhost:3000

# --- Trading ---
WATCHLIST=AAPL,MSFT,GOOGL,AMZN,NVDA,META,TSLA,JPM,V,UNH,SPY,QQQ
TRADING_START_HOUR=9                 # EST
TRADING_END_HOUR=16
SIGNAL_INTERVAL_MINUTES=5

# --- Risk Limits (override defaults) ---
MAX_POSITION_PCT=5.0
MAX_DAILY_LOSS_PCT=3.0
MAX_WEEKLY_LOSS_PCT=5.0
MAX_MONTHLY_LOSS_PCT=8.0
MAX_DRAWDOWN_PCT=12.0
MAX_OPEN_POSITIONS=8
MAX_TRADES_PER_DAY=10
```

---

## 15. Testing Strategy

### Test Categories

| Category | What | Tool |
|---|---|---|
| **Unit Tests** | Individual functions (indicators, sizing, risk checks) | pytest |
| **Integration Tests** | Full signal-to-trade pipeline with mocked APIs | pytest + httpx mock |
| **Backtests** | ML model on historical data (walk-forward) | Custom backtester |
| **Paper Trading** | Live market with fake money | Alpaca paper account |
| **Stress Tests** | Circuit breakers under extreme scenarios | Simulated crashes |
| **Security Tests** | Auth, input validation, secret exposure | Manual + automated |

### Backtest Metrics to Track

```python
REQUIRED_METRICS = {
    "total_return_pct": "Total return over period",
    "annualized_return_pct": "Annualized return",
    "sharpe_ratio": "Risk-adjusted return (must be > 0.5)",
    "sortino_ratio": "Downside risk-adjusted return",
    "max_drawdown_pct": "Worst peak-to-trough (must be < 12%)",
    "win_rate_pct": "Percentage of profitable trades (must be > 50%)",
    "profit_factor": "Gross profits / gross losses (must be > 1.2)",
    "avg_win_loss_ratio": "Average win / average loss",
    "total_trades": "Number of trades executed",
    "avg_hold_time": "Average position hold duration",
    "beta_to_spy": "Correlation with market (lower = better diversification)",
    "calmar_ratio": "Annual return / max drawdown",
}
```

---

## Quick Start

After building:

```bash
# 1. Clone and configure
cp .env.example .env
# Edit .env with your Alpaca + Anthropic API keys

# 2. Launch everything
make up
# or: docker-compose up -d

# 3. Initialize database
make migrate

# 4. Create admin user
docker exec aurora-backend python -m app.security.auth create-user --username admin

# 5. Seed historical data
make seed

# 6. Open dashboard
# Navigate to http://localhost:3000

# 7. System will start paper trading automatically during market hours
```

---

## Cost Estimates (Monthly)

| Service | Cost |
|---|---|
| **Alpaca** (Trading + Data) | Free (basic tier) |
| **Claude API** (~50 reviews/day × 22 days) | ~$5-15/month (Sonnet) |
| **VPS** (2 CPU, 4GB RAM) | ~$10-20/month |
| **Domain + SSL** (optional) | ~$1/month |
| **Total** | **~$16-36/month** |

---

## Important Disclaimers

> ⚠️ **This system is for educational and personal use only.**
>
> - Past performance (including backtests) does not guarantee future results.
> - Automated trading carries significant risk of financial loss.
> - Start with paper trading. When going live, use only money you can afford to lose.
> - No trading system is guaranteed to be profitable.
> - This is not financial advice. Consult a licensed financial advisor.
> - The system authors are not responsible for any trading losses.
> - Markets can behave in ways no model can predict (black swan events).

---

*AURORA v1.0.0*
