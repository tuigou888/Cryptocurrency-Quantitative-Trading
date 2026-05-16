import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache

from exchange.base import OHLCV
from utils.logger import logger


class VectorizedDataProcessor:
    """
    向量化数据处理管道，替代逐行循环 DataFrame 操作。

    优化点:
    - 批量 OHLCV 转换 (避免逐条循环)
    - 技术指标向量化计算
    - 并行数据获取
    - 数据缓存
    """

    @staticmethod
    def candles_to_dataframe(candles: List[OHLCV]) -> pd.DataFrame:
        """批量转换 OHLCV 列表为 DataFrame（向量化）"""
        if not candles:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

        timestamps = np.array([c.timestamp for c in candles], dtype="datetime64[ms]")
        data = np.array([
            [c.open for c in candles],
            [c.high for c in candles],
            [c.low for c in candles],
            [c.close for c in candles],
            [c.volume for c in candles],
        ])

        df = pd.DataFrame(
            data.T,
            columns=["open", "high", "low", "close", "volume"],
            index=timestamps,
        )
        df.index.name = "timestamp"
        return df

    @staticmethod
    def dataframe_to_candles(df: pd.DataFrame) -> List[OHLCV]:
        """批量转换 DataFrame 为 OHLCV 列表"""
        if df.empty:
            return []

        return [
            OHLCV(
                timestamp=idx.to_pydatetime() if hasattr(idx, "to_pydatetime") else idx,
                open=row["open"],
                high=row["high"],
                low=row["low"],
                close=row["close"],
                volume=row["volume"],
            )
            for idx, row in df.iterrows()
        ]

    @staticmethod
    def add_indicators(df: pd.DataFrame, indicators: Optional[List[str]] = None) -> pd.DataFrame:
        """批量添加技术指标（向量化计算）"""
        if df.empty:
            return df

        result = df.copy()
        indicators = indicators or ["ma_fast", "ma_slow", "rsi", "atr", "bb_upper", "bb_lower", "macd", "signal"]

        if "ma_fast" in indicators and "ma" in df.columns or "close" in df.columns:
            for period in [5, 10, 20]:
                result[f"ma_{period}"] = df["close"].rolling(window=period, min_periods=1).mean()

        if "ma_slow" in indicators and "close" in df.columns:
            for period in [50, 100, 200]:
                result[f"ma_{period}"] = df["close"].rolling(window=period, min_periods=1).mean()

        if "rsi" in indicators and "close" in df.columns:
            delta = df["close"].diff()
            gain = delta.where(delta > 0, 0.0).rolling(window=14, min_periods=1).mean()
            loss = (-delta.where(delta < 0, 0.0)).rolling(window=14, min_periods=1).mean()
            rs = gain / loss.replace(0, np.inf)
            result["rsi"] = 100 - (100 / (1 + rs))
            result["rsi"] = result["rsi"].fillna(50)

        if "atr" in indicators and all(c in df.columns for c in ["high", "low", "close"]):
            high_low = df["high"] - df["low"]
            high_close = np.abs(df["high"] - df["close"].shift())
            low_close = np.abs(df["low"] - df["close"].shift())
            true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            result["atr"] = true_range.rolling(window=14, min_periods=1).mean()

        if "bb" in str(indicators) and "close" in df.columns:
            bb_period = 20
            sma = df["close"].rolling(window=bb_period, min_periods=1).mean()
            std = df["close"].rolling(window=bb_period, min_periods=1).std()
            result["bb_upper"] = sma + (std * 2)
            result["bb_lower"] = sma - (std * 2)
            result["bb_middle"] = sma

        if "macd" in indicators and "close" in df.columns:
            ema12 = df["close"].ewm(span=12, adjust=False).mean()
            ema26 = df["close"].ewm(span=26, adjust=False).mean()
            result["macd"] = ema12 - ema26
            result["signal"] = result["macd"].ewm(span=9, adjust=False).mean()
            result["macd_hist"] = result["macd"] - result["signal"]

        return result

    @staticmethod
    def resample_data(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        """将 1h 数据重新采样为其他周期"""
        if df.empty:
            return df

        timeframe_map = {
            "4h": "4H",
            "1d": "1D",
            "15m": "15T",
            "5m": "5T",
        }

        freq = timeframe_map.get(timeframe, timeframe)
        resampled = pd.DataFrame()
        resampled["open"] = df["open"].resample(freq).first()
        resampled["high"] = df["high"].resample(freq).max()
        resampled["low"] = df["low"].resample(freq).min()
        resampled["close"] = df["close"].resample(freq).last()
        resampled["volume"] = df["volume"].resample(freq).sum()
        return resampled.dropna()

    @staticmethod
    def calculate_returns(df: pd.DataFrame) -> pd.DataFrame:
        """批量计算收益率相关指标"""
        result = df.copy()
        result["returns"] = df["close"].pct_change()
        result["log_returns"] = np.log(df["close"] / df["close"].shift(1))
        result["cumulative_returns"] = (1 + result["returns"]).cumprod() - 1
        return result

    @staticmethod
    def detect_crossover(series1: pd.Series, series2: pd.Series) -> pd.Series:
        """检测金叉/死叉（向量化）"""
        prev1 = series1.shift(1)
        prev2 = series2.shift(1)
        golden = (prev1 <= prev2) & (series1 > series2)
        death = (prev1 >= prev2) & (series1 < series2)
        return pd.DataFrame({"golden": golden, "death": death})


class ChunkedDataLoader:
    """
    分块数据加载器，支持大时间范围数据分段获取。
    参考 Freqtrade 的数据获取策略。
    """

    def __init__(self, max_chunk_days: int = 90, max_workers: int = 4):
        self.max_chunk_days = max_chunk_days
        self.max_workers = max_workers

    def load_range(
        self,
        fetch_func,
        start_date: datetime,
        end_date: datetime,
        **kwargs
    ) -> pd.DataFrame:
        """
        分块加载历史数据，自动分段避免交易所限制。
        fetch_func(start, end, **kwargs) -> pd.DataFrame
        """
        chunks = []
        current = start_date

        while current < end_date:
            chunk_end = min(current + timedelta(days=self.max_chunk_days), end_date)
            try:
                df = fetch_func(current, chunk_end, **kwargs)
                if df is not None and not df.empty:
                    chunks.append(df)
                    logger.info(f"Loaded chunk: {current.date()} to {chunk_end.date()}, {len(df)} rows")
            except Exception as e:
                logger.error(f"Failed to load chunk {current.date()} to {chunk_end.date()}: {e}")
            current = chunk_end

        if not chunks:
            return pd.DataFrame()

        return pd.concat(chunks, ignore_index=False).drop_duplicates().sort_index()
