import pandas as pd
import numpy as np

from strategy.base import BaseStrategy, Signal, SignalType


class RSIStrategy(BaseStrategy):
    def __init__(self, period: int = 14, oversold: float = 30, overbought: float = 70, **kwargs):
        super().__init__(
            name="RSI",
            params={
                "period": period,
                "oversold": oversold,
                "overbought": overbought,
            },
        )

    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        period = self.params["period"]

        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)

        avg_gain = gain.rolling(window=period, min_periods=period).mean()
        avg_loss = loss.rolling(window=period, min_periods=period).mean()

        for i in range(period, len(df)):
            if i >= period and not pd.isna(avg_gain.iloc[i - 1]) and avg_loss.iloc[i - 1] != 0:
                avg_gain.iloc[i] = (avg_gain.iloc[i - 1] * (period - 1) + gain.iloc[i]) / period
                avg_loss.iloc[i] = (avg_loss.iloc[i - 1] * (period - 1) + loss.iloc[i]) / period

        rs = avg_gain / avg_loss.replace(0, np.inf)
        df["rsi"] = 100 - (100 / (1 + rs))
        return df

    def generate_signal(self, data: pd.DataFrame) -> Signal:
        if len(data) < self.params["period"] + 1:
            return Signal(signal_type=SignalType.HOLD, symbol="", price=0)

        current = data.iloc[-1]
        prev = data.iloc[-2]
        symbol = self.params.get("symbol", "BTC/USDT")

        if pd.isna(current.get("rsi")):
            return Signal(signal_type=SignalType.HOLD, symbol=symbol, price=current["close"])

        rsi = current["rsi"]
        rsi_prev = prev.get("rsi", 50)
        oversold = self.params["oversold"]
        overbought = self.params["overbought"]

        if rsi < oversold and rsi_prev >= oversold:
            return Signal(
                signal_type=SignalType.BUY,
                symbol=symbol,
                price=current["close"],
                reason=f"RSI oversold: RSI={rsi:.1f} crossed below {oversold}",
                confidence=(oversold - rsi) / oversold,
            )
        elif rsi > overbought and rsi_prev <= overbought:
            return Signal(
                signal_type=SignalType.SELL,
                symbol=symbol,
                price=current["close"],
                reason=f"RSI overbought: RSI={rsi:.1f} crossed above {overbought}",
                confidence=(rsi - overbought) / (100 - overbought),
            )

        return Signal(signal_type=SignalType.HOLD, symbol=symbol, price=current["close"])
