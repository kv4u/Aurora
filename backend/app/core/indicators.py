"""Technical indicator calculations using pandas + ta library."""

import logging

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market_data import Indicator, MarketData

logger = logging.getLogger("aurora.indicators")


def compute_all_indicators(df: pd.DataFrame) -> dict:
    """Compute all technical indicators from OHLCV DataFrame.

    Args:
        df: DataFrame with columns [open, high, low, close, volume] indexed by timestamp.

    Returns:
        Dictionary of indicator name -> value for the latest bar.
    """
    if len(df) < 50:
        logger.warning("Not enough data for full indicator computation (%d bars)", len(df))
        return {}

    try:
        import ta
    except ImportError:
        logger.error("'ta' library not installed")
        return {}

    indicators = {}

    # ─── Trend ───
    indicators["sma_20"] = float(df["close"].rolling(20).mean().iloc[-1])
    indicators["sma_50"] = float(df["close"].rolling(50).mean().iloc[-1]) if len(df) >= 50 else None
    indicators["sma_200"] = float(df["close"].rolling(200).mean().iloc[-1]) if len(df) >= 200 else None
    indicators["ema_12"] = float(df["close"].ewm(span=12).mean().iloc[-1])
    indicators["ema_26"] = float(df["close"].ewm(span=26).mean().iloc[-1])

    macd = ta.trend.MACD(df["close"])
    indicators["macd"] = float(macd.macd().iloc[-1])
    indicators["macd_signal"] = float(macd.macd_signal().iloc[-1])
    indicators["macd_histogram"] = float(macd.macd_diff().iloc[-1])

    adx = ta.trend.ADXIndicator(df["high"], df["low"], df["close"])
    indicators["adx_14"] = float(adx.adx().iloc[-1])

    psar = ta.trend.PSARIndicator(df["high"], df["low"], df["close"])
    psar_val = psar.psar().iloc[-1]
    indicators["parabolic_sar"] = float(psar_val)
    indicators["parabolic_sar_signal"] = 1.0 if df["close"].iloc[-1] > psar_val else -1.0

    # ─── Momentum ───
    rsi = ta.momentum.RSIIndicator(df["close"], window=14)
    indicators["rsi_14"] = float(rsi.rsi().iloc[-1])

    stoch = ta.momentum.StochasticOscillator(df["high"], df["low"], df["close"])
    indicators["stoch_k"] = float(stoch.stoch().iloc[-1])
    indicators["stoch_d"] = float(stoch.stoch_signal().iloc[-1])

    williams = ta.momentum.WilliamsRIndicator(df["high"], df["low"], df["close"])
    indicators["williams_r"] = float(williams.williams_r().iloc[-1])

    cci = ta.trend.CCIIndicator(df["high"], df["low"], df["close"], window=20)
    indicators["cci_20"] = float(cci.cci().iloc[-1])

    roc = ta.momentum.ROCIndicator(df["close"], window=10)
    indicators["roc_10"] = float(roc.roc().iloc[-1])

    # ─── Volatility ───
    bb = ta.volatility.BollingerBands(df["close"], window=20, window_dev=2)
    bb_high = bb.bollinger_hband().iloc[-1]
    bb_low = bb.bollinger_lband().iloc[-1]
    indicators["bb_high"] = float(bb_high)
    indicators["bb_low"] = float(bb_low)
    indicators["bb_mid"] = float(bb.bollinger_mavg().iloc[-1])
    bb_range = bb_high - bb_low
    indicators["bb_position"] = float((df["close"].iloc[-1] - bb_low) / bb_range) if bb_range > 0 else 0.5
    indicators["bb_squeeze"] = float(bb_range / indicators["sma_20"]) if indicators["sma_20"] else 0.0

    atr = ta.volatility.AverageTrueRange(df["high"], df["low"], df["close"], window=14)
    indicators["atr_14"] = float(atr.average_true_range().iloc[-1])
    indicators["atr_ratio"] = float(indicators["atr_14"] / df["close"].iloc[-1]) if df["close"].iloc[-1] else 0.0

    kc = ta.volatility.KeltnerChannel(df["high"], df["low"], df["close"])
    kc_high = kc.keltner_channel_hband().iloc[-1]
    kc_low = kc.keltner_channel_lband().iloc[-1]
    kc_range = kc_high - kc_low
    indicators["keltner_position"] = float((df["close"].iloc[-1] - kc_low) / kc_range) if kc_range > 0 else 0.5

    # ─── Volume ───
    obv = ta.volume.OnBalanceVolumeIndicator(df["close"], df["volume"])
    obv_series = obv.on_balance_volume()
    indicators["obv"] = float(obv_series.iloc[-1])
    indicators["obv_slope"] = float(obv_series.diff(5).iloc[-1]) if len(obv_series) >= 5 else 0.0

    # VWAP (intraday approximation)
    typical_price = (df["high"] + df["low"] + df["close"]) / 3
    cumulative_tp_vol = (typical_price * df["volume"]).cumsum()
    cumulative_vol = df["volume"].cumsum()
    vwap = cumulative_tp_vol / cumulative_vol
    indicators["vwap"] = float(vwap.iloc[-1]) if not np.isnan(vwap.iloc[-1]) else float(df["close"].iloc[-1])
    indicators["vwap_diff"] = float(df["close"].iloc[-1] - indicators["vwap"])

    vol_sma = df["volume"].rolling(20).mean()
    indicators["volume_vs_sma20"] = float(df["volume"].iloc[-1] / vol_sma.iloc[-1]) if vol_sma.iloc[-1] > 0 else 1.0

    vol_5d = df["volume"].rolling(5).mean()
    indicators["volume_ratio_5d"] = float(df["volume"].iloc[-1] / vol_5d.iloc[-1]) if vol_5d.iloc[-1] > 0 else 1.0

    # ─── Raw OHLCV (latest bar) ───
    indicators["open"] = float(df["open"].iloc[-1])
    indicators["high"] = float(df["high"].iloc[-1])
    indicators["low"] = float(df["low"].iloc[-1])
    indicators["close"] = float(df["close"].iloc[-1])
    indicators["volume"] = int(df["volume"].iloc[-1])

    # ─── Price-based ───
    close = df["close"].iloc[-1]
    indicators["return_1d"] = float(df["close"].pct_change(1).iloc[-1])
    indicators["return_5d"] = float(df["close"].pct_change(5).iloc[-1])
    indicators["return_10d"] = float(df["close"].pct_change(10).iloc[-1])
    indicators["return_20d"] = float(df["close"].pct_change(20).iloc[-1])
    indicators["high_low_ratio"] = float(df["high"].iloc[-1] / df["low"].iloc[-1]) if df["low"].iloc[-1] > 0 else 1.0
    indicators["close_open_ratio"] = float(close / df["open"].iloc[-1]) if df["open"].iloc[-1] > 0 else 1.0
    indicators["price_vs_sma20"] = float(close / indicators["sma_20"]) if indicators["sma_20"] else 1.0
    indicators["price_vs_sma50"] = float(close / indicators["sma_50"]) if indicators.get("sma_50") else None
    indicators["price_vs_sma200"] = float(close / indicators["sma_200"]) if indicators.get("sma_200") else None
    indicators["gap_percentage"] = float((df["open"].iloc[-1] - df["close"].iloc[-2]) / df["close"].iloc[-2]) if len(df) >= 2 else 0.0

    # ─── Cross signals ───
    ema12 = df["close"].ewm(span=12).mean()
    ema26 = df["close"].ewm(span=26).mean()
    indicators["ema12_ema26_cross"] = 1.0 if ema12.iloc[-1] > ema26.iloc[-1] else -1.0

    sma20 = df["close"].rolling(20).mean()
    sma50 = df["close"].rolling(50).mean() if len(df) >= 50 else sma20
    indicators["sma20_sma50_cross"] = 1.0 if sma20.iloc[-1] > sma50.iloc[-1] else -1.0

    # ─── Composite signals ───
    rsi_val = indicators["rsi_14"]
    macd_val = indicators["macd_histogram"]
    indicators["rsi_macd_agreement"] = 1.0 if (rsi_val > 50 and macd_val > 0) or (rsi_val < 50 and macd_val < 0) else 0.0
    indicators["volume_price_confirmation"] = 1.0 if (indicators["return_1d"] > 0 and indicators["volume_vs_sma20"] > 1.2) else 0.0

    # Clean NaN values
    return {k: (None if v is not None and isinstance(v, float) and np.isnan(v) else v) for k, v in indicators.items()}


class IndicatorEngine:
    """Computes and stores indicators linked to market data."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def compute_for_symbol(self, symbol: str, timeframe: str = "1Day") -> dict | None:
        """Load bars from DB, compute indicators, store results."""
        # Load recent bars
        result = await self.db.execute(
            select(MarketData)
            .where(MarketData.symbol == symbol, MarketData.timeframe == timeframe)
            .order_by(MarketData.timestamp.desc())
            .limit(250)
        )
        rows = list(result.scalars().all())

        if len(rows) < 50:
            logger.warning("Not enough bars for %s (%d), need 50+", symbol, len(rows))
            return None

        # Convert to DataFrame
        rows.reverse()  # Oldest first
        df = pd.DataFrame([
            {
                "timestamp": r.timestamp,
                "open": r.open,
                "high": r.high,
                "low": r.low,
                "close": r.close,
                "volume": r.volume,
            }
            for r in rows
        ])
        df.set_index("timestamp", inplace=True)

        # Compute
        indicators = compute_all_indicators(df)
        if not indicators:
            return None

        # Store
        latest_ts = rows[-1].timestamp
        stmt = pg_insert(Indicator).values(
            symbol=symbol,
            timeframe=timeframe,
            timestamp=latest_ts,
            values=indicators,
        ).on_conflict_do_update(
            index_elements=["symbol", "timeframe", "timestamp"],
            set_={"values": indicators},
        )
        await self.db.execute(stmt)
        await self.db.flush()

        logger.info("Computed %d indicators for %s (%s)", len(indicators), symbol, timeframe)
        return indicators

    async def compute_for_watchlist(self, symbols: list[str], timeframe: str = "1Day") -> dict[str, dict]:
        """Compute indicators for all symbols in the watchlist."""
        results = {}
        for symbol in symbols:
            indicators = await self.compute_for_symbol(symbol, timeframe)
            if indicators:
                results[symbol] = indicators
        return results
