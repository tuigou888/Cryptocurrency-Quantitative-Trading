import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import logging
import numpy as np
import pandas as pd
import ccxt

logger = logging.getLogger(__name__)

from strategy.ma_cross import MACrossStrategy
from strategy.rsi import RSIStrategy
from strategy.grid import GridStrategy
from backtest.engine import BacktestEngine

STRATEGY_MAP = {
    "ma_cross": {"name": "MA均线交叉", "cls": MACrossStrategy},
    "rsi": {"name": "RSI超买超卖", "cls": RSIStrategy},
    "grid": {"name": "网格交易", "cls": GridStrategy},
}


def fetch_real_market_data(days=60, symbol="BTC/USDT", timeframe="1h"):
    try:
        exchange = ccxt.binance({
            "enableRateLimit": False,
            "timeout": 2000,
            "options": {"defaultType": "spot"},
        })
        limit = min(days * 24, 1000)
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)
        logger.info(f"Fetched {len(df)} real bars from Binance for {symbol}")
        return df
    except Exception as e:
        logger.warning(f"Binance unavailable ({e}), using sample data")
        return generate_sample_data(days)


def generate_sample_data(days=60):
    np.random.seed(42)
    periods = days * 24
    dates = pd.date_range(end=pd.Timestamp.now(), periods=periods, freq="1h")
    price = 40000
    prices = []
    for _ in range(periods):
        price *= (1 + np.random.normal(0.0001, 0.008))
        prices.append(price)
    return pd.DataFrame({
        "open": [p * (1 + np.random.uniform(-0.002, 0.002)) for p in prices],
        "high": [p * (1 + abs(np.random.normal(0, 0.005))) for p in prices],
        "low": [p * (1 - abs(np.random.normal(0, 0.005))) for p in prices],
        "close": prices,
        "volume": [np.random.uniform(100, 2000) for _ in range(periods)],
    }, index=dates)


def run_backtest(strategy_id, days=60, capital=10000, **kwargs):
    df = fetch_real_market_data(days)
    info = STRATEGY_MAP[strategy_id]
    strat = info["cls"](**kwargs)
    strat.set_param("symbol", "BTC/USDT")
    engine = BacktestEngine(strat, df, initial_capital=capital)
    return engine.run(), df