"""ML Model Training Pipeline — labels historical data and trains LightGBM.

Usage:
    python -m app.ml.train              # Train from DB data
    python -m app.ml.train --days 180   # Use last 180 days of data
"""

import argparse
import asyncio
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import classification_report, accuracy_score
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import Settings
from app.ml.feature_engineering import FEATURE_NAMES, FeatureEngineer
from app.models.market_data import MarketData

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
logger = logging.getLogger("aurora.ml.train")

MODEL_DIR = Path("ml_models")
MODEL_DIR.mkdir(exist_ok=True)

# Labeling parameters
FORWARD_DAYS = 5          # Look ahead N days for return
BUY_THRESHOLD = 0.02      # +2% forward return → BUY
SELL_THRESHOLD = -0.02     # -2% forward return → SELL


async def load_bars(db: AsyncSession, days: int) -> pd.DataFrame:
    """Load daily bars from DB into a DataFrame."""
    since = datetime.now(timezone.utc) - timedelta(days=days)

    result = await db.execute(
        select(MarketData)
        .where(
            MarketData.timeframe == "1Day",
            MarketData.timestamp >= since,
        )
        .order_by(MarketData.symbol, MarketData.timestamp)
    )
    rows = result.scalars().all()

    data = []
    for r in rows:
        data.append({
            "symbol": r.symbol,
            "timestamp": r.timestamp,
            "open": r.open,
            "high": r.high,
            "low": r.low,
            "close": r.close,
            "volume": r.volume,
        })

    df = pd.DataFrame(data)
    logger.info("Loaded %d bars for %d symbols", len(df), df["symbol"].nunique() if len(df) else 0)
    return df


def label_data(df: pd.DataFrame) -> pd.DataFrame:
    """Label each bar with BUY/SELL/HOLD based on forward returns."""
    labeled = []

    for symbol, group in df.groupby("symbol"):
        group = group.sort_values("timestamp").reset_index(drop=True)
        if len(group) < FORWARD_DAYS + 20:
            logger.debug("Skipping %s — only %d bars", symbol, len(group))
            continue

        # Compute forward return
        group["forward_return"] = group["close"].shift(-FORWARD_DAYS) / group["close"] - 1

        # Label
        group["label"] = "HOLD"
        group.loc[group["forward_return"] >= BUY_THRESHOLD, "label"] = "BUY"
        group.loc[group["forward_return"] <= SELL_THRESHOLD, "label"] = "SELL"

        # Drop rows without forward return (last N rows)
        group = group.dropna(subset=["forward_return"])
        labeled.append(group)

    if not labeled:
        return pd.DataFrame()

    result = pd.concat(labeled, ignore_index=True)
    counts = result["label"].value_counts()
    logger.info("Labels: %s", counts.to_dict())
    return result


def compute_features_for_bars(bars_df: pd.DataFrame) -> list[dict]:
    """Compute indicator features for each bar using a rolling window."""
    fe = FeatureEngineer()
    all_rows = []

    for symbol, group in bars_df.groupby("symbol"):
        group = group.sort_values("timestamp").reset_index(drop=True)
        closes = group["close"].values
        highs = group["high"].values
        lows = group["low"].values
        opens = group["open"].values
        volumes = group["volume"].values

        for i in range(50, len(group)):
            # Build a mini DataFrame for indicators
            window = group.iloc[max(0, i - 200):i + 1]
            indicators = _compute_indicators_from_window(window)
            if not indicators:
                continue

            features = fe.build_features(indicators, {"spy_return_1d": 0, "vix": 20, "vix_change": 0})
            if features:
                features["_symbol"] = symbol
                features["_timestamp"] = group.iloc[i]["timestamp"]
                features["_label"] = group.iloc[i].get("label", "HOLD")
                all_rows.append(features)

    logger.info("Computed features for %d samples", len(all_rows))
    return all_rows


def _compute_indicators_from_window(window: pd.DataFrame) -> dict:
    """Compute indicators from a window of OHLCV bars (same logic as IndicatorEngine)."""
    try:
        import ta
        df = window.copy()

        if len(df) < 20:
            return {}

        indicators = {}

        close = df["close"]
        high = df["high"]
        low = df["low"]
        volume = df["volume"].astype(float)
        open_price = df["open"]

        # Returns
        indicators["return_1d"] = float((close.iloc[-1] / close.iloc[-2] - 1)) if len(close) >= 2 else 0
        indicators["return_5d"] = float((close.iloc[-1] / close.iloc[-5] - 1)) if len(close) >= 5 else 0
        indicators["return_10d"] = float((close.iloc[-1] / close.iloc[-10] - 1)) if len(close) >= 10 else 0
        indicators["return_20d"] = float((close.iloc[-1] / close.iloc[-20] - 1)) if len(close) >= 20 else 0

        # Ratios
        indicators["high_low_ratio"] = float(high.iloc[-1] / low.iloc[-1]) if low.iloc[-1] > 0 else 1
        indicators["close_open_ratio"] = float(close.iloc[-1] / open_price.iloc[-1]) if open_price.iloc[-1] > 0 else 1
        indicators["gap_percentage"] = float((open_price.iloc[-1] / close.iloc[-2] - 1)) if len(close) >= 2 and close.iloc[-2] > 0 else 0

        # Moving averages
        sma20 = close.rolling(20).mean().iloc[-1]
        sma50 = close.rolling(50).mean().iloc[-1] if len(close) >= 50 else None
        sma200 = close.rolling(200).mean().iloc[-1] if len(close) >= 200 else None
        indicators["price_vs_sma20"] = float(close.iloc[-1] / sma20) if sma20 and sma20 > 0 else 1
        indicators["price_vs_sma50"] = float(close.iloc[-1] / sma50) if sma50 and sma50 > 0 else None
        indicators["price_vs_sma200"] = float(close.iloc[-1] / sma200) if sma200 and sma200 > 0 else None

        # RSI
        rsi_ind = ta.momentum.RSIIndicator(close, window=14)
        indicators["rsi_14"] = float(rsi_ind.rsi().iloc[-1]) if not pd.isna(rsi_ind.rsi().iloc[-1]) else 50

        # MACD
        macd_ind = ta.trend.MACD(close)
        indicators["macd"] = float(macd_ind.macd().iloc[-1]) if not pd.isna(macd_ind.macd().iloc[-1]) else 0
        indicators["macd_signal"] = float(macd_ind.macd_signal().iloc[-1]) if not pd.isna(macd_ind.macd_signal().iloc[-1]) else 0
        indicators["macd_histogram"] = float(macd_ind.macd_diff().iloc[-1]) if not pd.isna(macd_ind.macd_diff().iloc[-1]) else 0

        # Bollinger Bands
        bb = ta.volatility.BollingerBands(close, window=20, window_dev=2)
        bb_high = bb.bollinger_hband().iloc[-1]
        bb_low = bb.bollinger_lband().iloc[-1]
        bb_range = bb_high - bb_low if bb_high and bb_low and bb_high != bb_low else 1
        indicators["bb_position"] = float((close.iloc[-1] - bb_low) / bb_range) if bb_range > 0 else 0.5

        # ADX
        adx_ind = ta.trend.ADXIndicator(high, low, close, window=14)
        indicators["adx_14"] = float(adx_ind.adx().iloc[-1]) if not pd.isna(adx_ind.adx().iloc[-1]) else 20

        # CCI
        indicators["cci_20"] = float(ta.trend.CCIIndicator(high, low, close, window=20).cci().iloc[-1] or 0)

        # Stochastics
        stoch = ta.momentum.StochasticOscillator(high, low, close, window=14, smooth_window=3)
        indicators["stoch_k"] = float(stoch.stoch().iloc[-1] or 50)
        indicators["stoch_d"] = float(stoch.stoch_signal().iloc[-1] or 50)

        # OBV slope
        obv = ta.volume.OnBalanceVolumeIndicator(close, volume).on_balance_volume()
        if len(obv) >= 5:
            obv_vals = obv.iloc[-5:].values
            indicators["obv_slope"] = float(np.polyfit(range(5), obv_vals, 1)[0]) if not any(np.isnan(obv_vals)) else 0
        else:
            indicators["obv_slope"] = 0

        # VWAP diff
        typical = (high + low + close) / 3
        vwap = (typical * volume).rolling(20).sum() / volume.rolling(20).sum()
        vwap_val = vwap.iloc[-1]
        indicators["vwap_diff"] = float((close.iloc[-1] - vwap_val) / vwap_val) if vwap_val and vwap_val > 0 else 0

        # ATR
        atr_ind = ta.volatility.AverageTrueRange(high, low, close, window=14)
        atr_val = atr_ind.average_true_range().iloc[-1]
        indicators["atr_14"] = float(atr_val or 0)
        indicators["atr_ratio"] = float(atr_val / close.iloc[-1]) if atr_val and close.iloc[-1] > 0 else 0.02

        # Williams %R
        indicators["williams_r"] = float(ta.momentum.WilliamsRIndicator(high, low, close, lbp=14).williams_r().iloc[-1] or -50)

        # Parabolic SAR
        try:
            sar = ta.trend.PSARIndicator(high, low, close)
            sar_val = sar.psar().iloc[-1]
            indicators["parabolic_sar_signal"] = 1 if close.iloc[-1] > sar_val else -1
        except Exception:
            indicators["parabolic_sar_signal"] = 0

        # EMA crossovers
        ema12 = close.ewm(span=12).mean()
        ema26 = close.ewm(span=26).mean()
        indicators["ema12_ema26_cross"] = 1 if ema12.iloc[-1] > ema26.iloc[-1] else -1

        sma20_series = close.rolling(20).mean()
        sma50_series = close.rolling(50).mean() if len(close) >= 50 else sma20_series
        indicators["sma20_sma50_cross"] = 1 if sma20_series.iloc[-1] > sma50_series.iloc[-1] else -1

        # Volume
        vol_sma20 = volume.rolling(20).mean().iloc[-1]
        indicators["volume_vs_sma20"] = float(volume.iloc[-1] / vol_sma20) if vol_sma20 and vol_sma20 > 0 else 1
        vol_sma5 = volume.rolling(5).mean().iloc[-1] if len(volume) >= 5 else volume.iloc[-1]
        indicators["volume_ratio_5d"] = float(volume.iloc[-1] / vol_sma5) if vol_sma5 and vol_sma5 > 0 else 1

        # Keltner
        kc = ta.volatility.KeltnerChannel(high, low, close, window=20)
        kc_high = kc.keltner_channel_hband().iloc[-1]
        kc_low = kc.keltner_channel_lband().iloc[-1]
        kc_range = kc_high - kc_low if kc_high and kc_low and kc_high != kc_low else 1
        indicators["keltner_position"] = float((close.iloc[-1] - kc_low) / kc_range) if kc_range > 0 else 0.5

        # ROC
        indicators["roc_10"] = float(ta.momentum.ROCIndicator(close, window=10).roc().iloc[-1] or 0)

        # Composite signals
        rsi_bull = indicators["rsi_14"] > 50
        macd_bull = indicators["macd_histogram"] > 0
        indicators["rsi_macd_agreement"] = 1 if rsi_bull == macd_bull else -1

        price_up = indicators["return_1d"] > 0
        vol_up = indicators["volume_vs_sma20"] > 1
        indicators["volume_price_confirmation"] = 1 if price_up == vol_up else -1

        # BB squeeze
        bb_width = bb_range / close.iloc[-1] if close.iloc[-1] > 0 else 0
        indicators["bb_squeeze"] = 1.0 if bb_width < 0.04 else 0.0

        # Raw OHLCV
        indicators["close"] = float(close.iloc[-1])
        indicators["open"] = float(open_price.iloc[-1])
        indicators["high"] = float(high.iloc[-1])
        indicators["low"] = float(low.iloc[-1])
        indicators["volume"] = int(volume.iloc[-1])

        return indicators

    except Exception as e:
        logger.debug("Indicator computation failed: %s", e)
        return {}


def train_model(features_df: pd.DataFrame) -> lgb.LGBMClassifier:
    """Train a LightGBM classifier on labeled feature data."""

    X = features_df[FEATURE_NAMES].fillna(0)
    y = features_df["_label"]

    # Time-series split (no future leakage)
    tscv = TimeSeriesSplit(n_splits=3)

    model = lgb.LGBMClassifier(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.05,
        num_leaves=31,
        min_child_samples=20,
        subsample=0.8,
        colsample_bytree=0.8,
        class_weight="balanced",
        random_state=42,
        verbose=-1,
    )

    # Evaluate on last split
    scores = []
    for train_idx, val_idx in tscv.split(X):
        X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]

        model.fit(X_train, y_train)
        val_pred = model.predict(X_val)
        acc = accuracy_score(y_val, val_pred)
        scores.append(acc)
        logger.info("Fold accuracy: %.3f", acc)

    logger.info("Mean CV accuracy: %.3f", np.mean(scores))

    # Final train on all data
    model.fit(X, y)

    # Print classification report
    y_pred = model.predict(X)
    logger.info("\nFull training set report:\n%s", classification_report(y, y_pred))

    # Feature importance
    importance = dict(zip(FEATURE_NAMES, model.feature_importances_))
    top_10 = sorted(importance.items(), key=lambda x: x[1], reverse=True)[:10]
    logger.info("Top 10 features:")
    for fname, imp in top_10:
        logger.info("  %s: %d", fname, imp)

    return model


async def main(days: int = 365):
    """Main training pipeline."""
    settings = Settings()
    engine = create_async_engine(settings.database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        # 1. Load bars
        bars_df = await load_bars(db, days)
        if bars_df.empty:
            logger.error("No data found. Run data ingestion first.")
            return

        # 2. Label data
        labeled_df = label_data(bars_df)
        if labeled_df.empty:
            logger.error("Not enough data to label. Need at least %d days per symbol.", FORWARD_DAYS + 20)
            return

        # 3. Compute features
        logger.info("Computing features (this may take a moment)...")
        feature_rows = compute_features_for_bars(labeled_df)
        if not feature_rows:
            logger.error("Feature computation produced no samples.")
            return

        features_df = pd.DataFrame(feature_rows)
        logger.info("Training data shape: %s", features_df.shape)

        # 4. Train model
        model = train_model(features_df)

        # 5. Save model
        version = datetime.now().strftime("v%Y%m%d_%H%M")
        model_path = MODEL_DIR / "latest.joblib"
        joblib.dump(model, model_path)
        (MODEL_DIR / "latest_version.txt").write_text(version)

        # Also save a timestamped backup
        joblib.dump(model, MODEL_DIR / f"model_{version}.joblib")

        logger.info("Model saved: %s (%s)", model_path, version)
        logger.info("Training complete!")

    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train AURORA ML model")
    parser.add_argument("--days", type=int, default=365, help="Days of historical data to use")
    args = parser.parse_args()

    asyncio.run(main(args.days))
