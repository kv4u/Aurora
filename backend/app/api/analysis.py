"""On-demand AI-powered symbol analysis endpoint."""

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.audit_logger import AuditLogger
from app.core.claude_analyst import ClaudeAnalyst, SECTOR_MAP
from app.core.scheduler import TradingLoop
from app.database import get_db
from app.security.auth import require_auth

router = APIRouter()


@router.get("/{symbol}")
async def analyze_symbol(
    symbol: str,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _user: str = Depends(require_auth),
):
    """Request deep AI analysis for a single symbol.

    Returns comprehensive technical outlook, risk assessment,
    entry/exit zones, and conviction score.
    """
    symbol = symbol.upper().strip()
    if not symbol or len(symbol) > 10:
        raise HTTPException(400, "Invalid symbol")

    loop = TradingLoop(settings, db)
    try:
        context = await loop.build_analysis_context(symbol)
        analysis = await loop.claude.analyze_symbol(symbol, context)

        result = asdict(analysis)
        result["sector"] = SECTOR_MAP.get(symbol, "Unknown")
        result["price"] = context.get("price", 0)
        result["high_52w"] = context.get("high_52w", 0)
        result["low_52w"] = context.get("low_52w", 0)
        result["vix"] = context.get("vix", 20)

        return result
    finally:
        await loop.cleanup()


@router.get("")
async def get_watchlist_overview(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _user: str = Depends(require_auth),
):
    """Quick overview of all watchlist symbols with sector and price data.

    Does NOT call Claude — just returns available market data for the watchlist.
    Use GET /analysis/{symbol} for deep analysis on a specific symbol.
    """
    loop = TradingLoop(settings, db)
    try:
        symbols = settings.watchlist_symbols
        overview = []

        for symbol in symbols:
            indicators = await loop.indicators.compute_for_symbol(symbol)
            price = 0
            change = 0
            rsi = None
            macd_hist = None
            trend = "neutral"

            if indicators:
                price = indicators.get("close", 0) or 0
                change = indicators.get("return_1d", 0) or 0
                rsi = indicators.get("rsi_14")
                macd_hist = indicators.get("macd_histogram")

                sma20 = indicators.get("sma_20")
                sma50 = indicators.get("sma_50")
                if sma20 and sma50 and price:
                    if price > sma20 > sma50:
                        trend = "bullish"
                    elif price < sma20 < sma50:
                        trend = "bearish"
                    else:
                        trend = "mixed"

            if not price:
                latest = await loop.ingestion.get_latest_price(symbol)
                price = latest or 0

            high_52w, low_52w = await loop._get_52w_range(symbol)

            overview.append({
                "symbol": symbol,
                "sector": SECTOR_MAP.get(symbol, "Unknown"),
                "price": round(price, 2),
                "change_pct": round(change * 100, 2) if change else 0,
                "rsi": round(rsi, 1) if rsi else None,
                "macd_histogram": round(macd_hist, 4) if macd_hist else None,
                "trend": trend,
                "high_52w": round(high_52w, 2),
                "low_52w": round(low_52w, 2),
            })

        return overview
    finally:
        await loop.cleanup()
