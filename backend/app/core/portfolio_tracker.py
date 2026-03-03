"""Portfolio Tracker — tracks positions, P&L, exposure, and equity curve."""

import logging
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import desc, select, func as sqlfunc
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models.portfolio import Portfolio
from app.models.trades import Trade

logger = logging.getLogger("aurora.portfolio")

PAPER_STARTING_BALANCE = 100_000.0


class PortfolioTracker:
    """Tracks all positions, calculates P&L, and monitors exposure."""

    def __init__(self, settings: Settings, db: AsyncSession):
        self.settings = settings
        self.db = db
        self._client: httpx.AsyncClient | None = None
        self._has_alpaca = bool(settings.alpaca_api_key.get_secret_value())

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
        """Take a full portfolio snapshot. Uses Alpaca if available, else paper mode."""
        if self._has_alpaca:
            return await self._snapshot_alpaca()
        return await self._snapshot_paper()

    async def _snapshot_paper(self) -> dict:
        """Paper-mode snapshot: reads open trades from DB, prices them live."""

        # 1. Get open (filled) trades from DB
        result = await self.db.execute(
            select(Trade).where(Trade.status == "filled")
        )
        open_trades = list(result.scalars().all())

        # 2. Get live prices for symbols with open trades
        live_prices = {}
        if open_trades:
            symbols = list({t.symbol for t in open_trades})
            live_prices = await self._get_live_prices(symbols)

        # 3. Compute realized P&L from closed trades
        closed_result = await self.db.execute(
            select(sqlfunc.coalesce(sqlfunc.sum(Trade.realized_pnl), 0)).where(
                Trade.status == "closed"
            )
        )
        total_realized_pnl = float(closed_result.scalar() or 0)

        # 4. Build positions and compute unrealized P&L
        positions_data = {}
        total_unrealized_pnl = 0.0
        total_market_value = 0.0

        for trade in open_trades:
            current_price = live_prices.get(trade.symbol, trade.fill_price or trade.entry_price)
            entry = trade.fill_price or trade.entry_price
            shares = trade.shares

            if trade.side == "buy":
                unrealized_pnl = (current_price - entry) * shares
            else:  # short
                unrealized_pnl = (entry - current_price) * shares

            market_val = current_price * shares
            pnl_pct = ((current_price - entry) / entry * 100) if entry > 0 else 0
            if trade.side == "sell":
                pnl_pct = -pnl_pct

            total_unrealized_pnl += unrealized_pnl
            total_market_value += market_val

            positions_data[trade.symbol] = {
                "trade_id": trade.id,
                "shares": shares,
                "side": trade.side,
                "entry_price": round(entry, 2),
                "current_price": round(current_price, 2),
                "market_value": round(market_val, 2),
                "unrealized_pnl": round(unrealized_pnl, 2),
                "unrealized_pnl_pct": round(pnl_pct, 2),
                "stop_price": trade.stop_price,
                "target_price": trade.target_price,
            }

        # 5. Compute cash = starting balance - capital in open trades + realized P&L
        capital_deployed = sum(t.dollar_amount for t in open_trades)
        cash = PAPER_STARTING_BALANCE - capital_deployed + total_realized_pnl
        equity = cash + total_market_value
        peak_equity = equity  # Will compare with historical

        # Get historical peak
        peak_result = await self.db.execute(
            select(sqlfunc.max(Portfolio.peak_equity))
        )
        hist_peak = peak_result.scalar() or PAPER_STARTING_BALANCE
        peak_equity = max(hist_peak, equity)

        total_exposure_pct = (total_market_value / equity * 100) if equity > 0 else 0
        drawdown = ((peak_equity - equity) / peak_equity * 100) if peak_equity > 0 else 0

        # Daily P&L (compare with snapshot from ~24h ago)
        yesterday = datetime.now(timezone.utc) - timedelta(hours=24)
        prev_result = await self.db.execute(
            select(Portfolio.total_equity)
            .where(Portfolio.timestamp <= yesterday)
            .order_by(desc(Portfolio.timestamp))
            .limit(1)
        )
        prev_equity = prev_result.scalar() or PAPER_STARTING_BALANCE
        daily_pnl = equity - prev_equity
        daily_pnl_pct = (daily_pnl / prev_equity * 100) if prev_equity > 0 else 0

        # Trades today count
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        trades_today_result = await self.db.execute(
            select(sqlfunc.count(Trade.id)).where(Trade.placed_at >= today_start)
        )
        trades_today = trades_today_result.scalar() or 0

        # 6. Store snapshot
        snap = Portfolio(
            total_equity=round(equity, 2),
            cash=round(cash, 2),
            market_value=round(total_market_value, 2),
            daily_pnl=round(daily_pnl, 2),
            daily_pnl_pct=round(daily_pnl_pct, 2),
            total_pnl=round(total_realized_pnl + total_unrealized_pnl, 2),
            total_pnl_pct=round(((equity - PAPER_STARTING_BALANCE) / PAPER_STARTING_BALANCE * 100), 2),
            total_exposure_pct=round(total_exposure_pct, 2),
            open_positions_count=len(positions_data),
            peak_equity=round(peak_equity, 2),
            current_drawdown_pct=round(drawdown, 2),
            max_drawdown_pct=round(drawdown, 2),
            sector_exposure={},
            positions=positions_data,
            trades_today=trades_today,
        )
        self.db.add(snap)
        await self.db.flush()

        logger.info(
            "Paper portfolio: $%.2f equity, $%.2f cash, %d positions, $%.2f unrealized P&L, %.1f%% exposure",
            equity, cash, len(positions_data), total_unrealized_pnl, total_exposure_pct,
        )

        return {
            "total_equity": round(equity, 2),
            "cash": round(cash, 2),
            "market_value": round(total_market_value, 2),
            "daily_pnl": round(daily_pnl, 2),
            "daily_pnl_pct": round(daily_pnl_pct, 2),
            "weekly_pnl": 0.0,
            "weekly_pnl_pct": 0.0,
            "monthly_pnl": 0.0,
            "monthly_pnl_pct": 0.0,
            "total_exposure_pct": round(total_exposure_pct, 2),
            "open_positions_count": len(positions_data),
            "positions": positions_data,
            "sector_exposure": {},
            "peak_equity": round(peak_equity, 2),
            "current_drawdown_pct": round(drawdown, 2),
            "trades_today": trades_today,
        }

    async def _get_live_prices(self, symbols: list[str]) -> dict[str, float]:
        """Fetch current prices via yfinance for paper mode."""
        import yfinance as yf

        prices = {}
        try:
            for symbol in symbols:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="1d")
                if not hist.empty:
                    prices[symbol] = float(hist["Close"].iloc[-1])
        except Exception as e:
            logger.warning("Live price fetch failed: %s", e)
        return prices

    async def _snapshot_alpaca(self) -> dict:
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
