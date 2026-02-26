"""Market data ingestion — Alpaca API primary, yfinance fallback."""

import logging
from datetime import datetime, timedelta, timezone

import httpx
import pandas as pd
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models.market_data import MarketData

logger = logging.getLogger("aurora.ingestion")


class DataIngestion:
    """Fetches and stores market data from Alpaca and yfinance."""

    def __init__(self, settings: Settings, db: AsyncSession):
        self.settings = settings
        self.db = db
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.settings.alpaca_data_url,
                headers={
                    "APCA-API-KEY-ID": self.settings.alpaca_api_key.get_secret_value(),
                    "APCA-API-SECRET-KEY": self.settings.alpaca_secret_key.get_secret_value(),
                },
                timeout=30.0,
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    # ─── Bar Fetching ───

    async def ingest_bars(
        self,
        symbols: list[str],
        timeframe: str = "1Min",
        limit: int = 1,
    ) -> int:
        """Fetch latest bars for watchlist symbols."""
        total_stored = 0
        for symbol in symbols:
            try:
                bars = await self._fetch_bars_alpaca(symbol, timeframe, limit)
                if bars:
                    count = await self._store_bars(bars, symbol, timeframe)
                    total_stored += count
            except Exception as e:
                logger.warning("Alpaca bar fetch failed for %s: %s", symbol, e)
                # Try yfinance fallback for daily bars
                if timeframe in ("1Day", "1D"):
                    try:
                        bars = await self._fetch_bars_yfinance(symbol, limit)
                        if bars:
                            count = await self._store_bars(bars, symbol, "1Day")
                            total_stored += count
                    except Exception as e2:
                        logger.error("yfinance fallback also failed for %s: %s", symbol, e2)

        logger.info("Ingested %d bars for %d symbols (%s)", total_stored, len(symbols), timeframe)
        return total_stored

    async def ingest_daily(self, symbols: list[str], days: int = 200) -> int:
        """End-of-day full bar fetch for historical data."""
        return await self.ingest_bars(symbols, timeframe="1Day", limit=days)

    async def _fetch_bars_alpaca(
        self,
        symbol: str,
        timeframe: str,
        limit: int,
    ) -> list[dict]:
        """Fetch bars from Alpaca Data API v2."""
        resp = await self.client.get(
            f"/v2/stocks/{symbol}/bars",
            params={
                "timeframe": timeframe,
                "limit": limit,
                "adjustment": "raw",
                "feed": "iex",  # Free tier
            },
        )
        resp.raise_for_status()
        data = resp.json()
        bars = data.get("bars", [])

        return [
            {
                "timestamp": bar["t"],
                "open": bar["o"],
                "high": bar["h"],
                "low": bar["l"],
                "close": bar["c"],
                "volume": bar["v"],
                "vwap": bar.get("vw"),
                "trade_count": bar.get("n"),
            }
            for bar in bars
        ]

    async def _fetch_bars_yfinance(self, symbol: str, limit: int) -> list[dict]:
        """Fallback: fetch daily bars using yfinance."""
        import yfinance as yf

        ticker = yf.Ticker(symbol)
        period = "1y" if limit > 200 else f"{limit}d"
        hist = ticker.history(period=period)

        if hist.empty:
            return []

        bars = []
        for ts, row in hist.iterrows():
            bars.append({
                "timestamp": ts.isoformat(),
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": int(row["Volume"]),
                "vwap": None,
                "trade_count": None,
            })
        return bars[-limit:]

    async def _store_bars(
        self,
        bars: list[dict],
        symbol: str,
        timeframe: str,
    ) -> int:
        """Upsert bars into the database."""
        if not bars:
            return 0

        for bar in bars:
            stmt = pg_insert(MarketData).values(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=bar["timestamp"],
                open=bar["open"],
                high=bar["high"],
                low=bar["low"],
                close=bar["close"],
                volume=bar["volume"],
                vwap=bar.get("vwap"),
                trade_count=bar.get("trade_count"),
            ).on_conflict_do_update(
                index_elements=["symbol", "timeframe", "timestamp"],
                set_={
                    "open": bar["open"],
                    "high": bar["high"],
                    "low": bar["low"],
                    "close": bar["close"],
                    "volume": bar["volume"],
                    "vwap": bar.get("vwap"),
                    "trade_count": bar.get("trade_count"),
                },
            )
            await self.db.execute(stmt)

        await self.db.flush()
        return len(bars)

    # ─── News Fetching ───

    async def fetch_news(self, symbols: list[str], limit: int = 10) -> list[dict]:
        """Fetch recent news headlines from Alpaca for Claude context."""
        try:
            resp = await self.client.get(
                "/v1beta1/news",
                params={
                    "symbols": ",".join(symbols),
                    "limit": limit,
                    "sort": "desc",
                },
            )
            resp.raise_for_status()
            data = resp.json()

            return [
                {
                    "headline": article["headline"],
                    "summary": article.get("summary", ""),
                    "source": article.get("source", ""),
                    "created_at": article["created_at"],
                    "symbols": article.get("symbols", []),
                    "url": article.get("url", ""),
                }
                for article in data.get("news", [])
            ]
        except Exception as e:
            logger.warning("News fetch failed: %s", e)
            return []

    # ─── Latest Price ───

    async def get_latest_price(self, symbol: str) -> float | None:
        """Get the latest trade price for a symbol."""
        try:
            resp = await self.client.get(
                f"/v2/stocks/{symbol}/trades/latest",
                params={"feed": "iex"},
            )
            resp.raise_for_status()
            data = resp.json()
            return float(data["trade"]["p"])
        except Exception as e:
            logger.warning("Latest price fetch failed for %s: %s", symbol, e)
            return None

    async def get_latest_prices(self, symbols: list[str]) -> dict[str, float]:
        """Get latest prices for multiple symbols."""
        prices = {}
        for symbol in symbols:
            price = await self.get_latest_price(symbol)
            if price is not None:
                prices[symbol] = price
        return prices
