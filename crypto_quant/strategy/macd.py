"""MACD策略 - 基于MACD指标的动量策略"""
from typing import Any, Optional

import pandas as pd

from strategy.base import BaseStrategy, Signal, SignalType


class MACDStrategy(BaseStrategy):
    def __init__(self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9, **kwargs: Any) -> None:
        super().__init__(
            name="MACD",
            params={
                "fast_period": fast_period,
                "slow_period": slow_period,
                "signal_period": signal_period,
                **kwargs,
            },
        )

    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        fast_period = self.get_param("fast_period")
        slow_period = self.get_param("slow_period")
        signal_period = self.get_param("signal_period")

        ema_fast = df["close"].ewm(span=fast_period, adjust=False).mean()
        ema_slow = df["close"].ewm(span=slow_period, adjust=False).mean()
        df["macd_line"] = ema_fast - ema_slow
        df["signal_line"] = df["macd_line"].ewm(span=signal_period, adjust=False).mean()
        df["histogram"] = df["macd_line"] - df["signal_line"]
        df["histogram_prev"] = df["histogram"].shift(1)
        return df

    def generate_signal(self, data: pd.DataFrame) -> Signal:
        symbol = self.get_param("symbol", "BTC/USDT")
        if len(data) < 2:
            return Signal(signal_type=SignalType.HOLD, symbol=symbol, price=0)

        last = data.iloc[-1]
        prev = data.iloc[-2]
        price = last["close"]

        macd = last.get("macd_line")
        signal = last.get("signal_line")
        histogram = last.get("histogram")
        histogram_prev = last.get("histogram_prev")

        if pd.isna(macd) or pd.isna(signal) or pd.isna(histogram) or pd.isna(histogram_prev):
            return Signal(signal_type=SignalType.HOLD, symbol=symbol, price=price)

        if histogram_prev <= 0 and histogram > 0:
            return Signal(signal_type=SignalType.BUY, symbol=symbol, price=price, reason="MACD Histogram Cross Bullish")

        if histogram_prev >= 0 and histogram < 0:
            if self.state.position_size > 0:
                return Signal(
                    signal_type=SignalType.SELL,
                    symbol=symbol,
                    price=price,
                    amount=self.state.position_size,
                    reason="MACD Histogram Cross Bearish",
                )
            return Signal(signal_type=SignalType.HOLD, symbol=symbol, price=price)

        return Signal(signal_type=SignalType.HOLD, symbol=symbol, price=price)
