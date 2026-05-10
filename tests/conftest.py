import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "crypto_quant"))


@pytest.fixture
def sample_ohlcv_data():
    np.random.seed(42)
    periods = 500
    dates = pd.date_range(end=datetime.now(), periods=periods, freq="1h")
    price = 40000
    prices = []
    for _ in range(periods):
        price *= (1 + np.random.normal(0.0001, 0.008))
        prices.append(price)
    df = pd.DataFrame({
        "open": [p * (1 + np.random.uniform(-0.002, 0.002)) for p in prices],
        "high": [p * (1 + abs(np.random.normal(0, 0.005))) for p in prices],
        "low": [p * (1 - abs(np.random.normal(0, 0.005))) for p in prices],
        "close": prices,
        "volume": [np.random.uniform(100, 2000) for _ in range(periods)],
    }, index=dates)
    df.index.name = "timestamp"
    return df


@pytest.fixture
def empty_df():
    return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
