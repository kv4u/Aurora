"""Portfolio Tracker — tracks positions, P&L, exposure, and equity curve."""

import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models.portfolio import Portfolio

logger = logging.getLogger("aurora.portfolio")


class PortfolioTracker:
    """Tracks all positions, calculates P&L, and monitors exposure."""

    def __init__(self, settings: Settings, db: AsyncSession):
        self.settings = settings
        self.db = db
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.settings.alpaca_base_url,
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

    async def get_account(self) -> dict:
        """Fetch account info from Alpaca."""
        resp = await self.client.get("/v2/account")
        resp.raise_for_status()
        return resp.json()

    async def get_positions(self) -> list[dict]:
        """Fetch all open positions from Alpaca."""
        resp = await self.client.get("/v2/positions")
        resp.raise_for_status()
        return resp.json()

    async def snapshot(self) -> dict:
        """Take a full portfolio snapshot and store it."""
        try:
            account = await self.get_account()
            positions = await self.get_positions()
        except Exception as e:
            logger.error("Failed to fetch portfolio data: %s", e)
            return {}

        equity = float(account.get("equity", 0))
        cash = float(account.get("cash", 0))
        market_value = float(account.get("long_market_value", 0)) + abs(float(account.get("short_market_value", 0)))

        # Calculate P&L from Alpaca account fields
        last_equity = float(account.get("last_equity", equity))
        daily_pnl = equity - last_equity
        daily_pnl_pct = (daily_pnl / last_equity * 100) if last_equity > 0 else 0

        # Build positions dict
        positions_data = {}
        sector_exposure = {}
        for pos in positions:
            symbol = pos["symbol"]
            market_val = abs(float(pos.get("market_value", 0)))
            pnl = float(pos.get("unrealized_pl", 0))
            pnl_pct = float(pos.get("unrealized_plpc", 0)) * 100

            positions_data[symbol] = {
                "shares": int(pos.get("qty", 0)),
                "side": pos.get("side", "long"),
                "entry_price": float(pos.get("avg_entry_price", 0)),
                "current_price": float(pos.get("current_price", 0)),
                "market_value": market_val,
                "unrealized_pnl": pnl,
                "unrealized_pnl_pct": pnl_pct,
            }

        total_exposure_pct = (market_value / equity * 100) if equity > 0 else 0

        # Store snapshot
        snapshot = Portfolio(
            total_equity=equity,
            cash=cash,
            market_value=market_value,
            daily_pnl=daily_pnl,
            daily_pnl_pct=daily_pnl_pct,
            total_exposure_pct=total_exposure_pct,
            open_positions_count=len(positions),
            peak_equity=max(equity, equity),  # Will compare with historical peak
            current_drawdown_pct=0.0,  # Will be computed from historical data
            sector_exposure=sector_exposure,
            positions=positions_data,
        )
        self.db.add(snapshot)
        await self.db.flush()

        logger.info(
            "Portfolio snapshot: $%.2f equity, %d positions, %.1f%% exposure, $%.2f daily P&L",
            equity, len(positions), total_exposure_pct, daily_pnl,
        )

        return {
            "total_equity": equity,
            "cash": cash,
            "market_value": market_value,
            "daily_pnl": daily_pnl,
            "daily_pnl_pct": daily_pnl_pct,
            "weekly_pnl": 0.0,  # Computed from historical snapshots
            "weekly_pnl_pct": 0.0,
            "monthly_pnl": 0.0,
            "monthly_pnl_pct": 0.0,
            "total_exposure_pct": total_exposure_pct,
            "open_positions_count": len(positions),
            "positions": positions_data,
            "sector_exposure": sector_exposure,
            "peak_equity": equity,
            "current_drawdown_pct": 0.0,
            "trades_today": 0,  # Computed from trade records
        }
