import pandas as pd
import numpy as np
from typing import Any

from strategy.base import BaseStrategy, Signal, SignalType, OrderType


class MACrossStrategy(BaseStrategy):
    def __init__(self, fast_period: int = 10, slow_period: int = 30, **kwargs: Any) -> None:
        super().__init__(
            name="MA_Cross",
            params={
                "fast_period": fast_period,
                "slow_period": slow_period,
            },
        )

    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        fast = self.params["fast_period"]
        slow = self.params["slow_period"]

        df["ma_fast"] = df["close"].rolling(window=fast).mean()
        df["ma_slow"] = df["close"].rolling(window=slow).mean()
        df["ma_diff"] = df["ma_fast"] - df["ma_slow"]
        df["ma_diff_prev"] = df["ma_diff"].shift(1)
        return df

    def generate_signal(self, data: pd.DataFrame) -> Signal:
        if len(data) < self.params["slow_period"] + 1:
            return Signal(signal_type=SignalType.HOLD, symbol="", price=0)

        current = data.iloc[-1]
        prev = data.iloc[-2]
        symbol = self.params.get("symbol", "BTC/USDT")

        if pd.isna(current["ma_diff"]) or pd.isna(prev["ma_diff"]):
            return Signal(signal_type=SignalType.HOLD, symbol=symbol, price=current["close"])

        golden_cross = prev["ma_diff"] <= 0 and current["ma_diff"] > 0
        death_cross = prev["ma_diff"] >= 0 and current["ma_diff"] < 0

        if golden_cross:
            return Signal(
                signal_type=SignalType.BUY,
                symbol=symbol,
                price=current["close"],
                reason=f"Golden cross: MA{self.params['fast_period']} crossed above MA{self.params['slow_period']}",
                confidence=min(abs(current["ma_diff"]) / current["close"] * 100, 1.0),
            )
        elif death_cross:
            return Signal(
                signal_type=SignalType.SELL,
                symbol=symbol,
                price=current["close"],
                reason=f"Death cross: MA{self.params['fast_period']} crossed below MA{self.params['slow_period']}",
                confidence=min(abs(current["ma_diff"]) / current["close"] * 100, 1.0),
            )

        return Signal(signal_type=SignalType.HOLD, symbol=symbol, price=current["close"])
