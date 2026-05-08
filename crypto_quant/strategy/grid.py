import pandas as pd
import numpy as np

from strategy.base import BaseStrategy, Signal, SignalType


class GridStrategy(BaseStrategy):
    def __init__(self, grid_num: int = 10, grid_range_pct: float = 0.05,
                 amount_per_grid: float = 0.001, **kwargs):
        super().__init__(
            name="Grid",
            params={
                "grid_num": grid_num,
                "grid_range_pct": grid_range_pct,
                "amount_per_grid": amount_per_grid,
                "center_price": None,
            },
        )
        self._grid_levels = []
        self._filled_grids = set()

    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()

        if self.params["center_price"] is None and not data.empty:
            self.params["center_price"] = data["close"].iloc[-1]

        center = self.params["center_price"]
        grid_num = self.params["grid_num"]
        range_pct = self.params["grid_range_pct"]

        upper = center * (1 + range_pct)
        lower = center * (1 - range_pct)
        step = (upper - lower) / grid_num

        self._grid_levels = [lower + i * step for i in range(grid_num + 1)]

        df["grid_center"] = center
        df["grid_upper"] = upper
        df["grid_lower"] = lower
        return df

    def generate_signal(self, data: pd.DataFrame) -> Signal:
        if not self._grid_levels or data.empty:
            return Signal(signal_type=SignalType.HOLD, symbol="", price=0)

        current = data.iloc[-1]
        price = current["close"]
        symbol = self.params.get("symbol", "BTC/USDT")
        amount = self.params["amount_per_grid"]

        for i in range(len(self._grid_levels) - 1):
            lower = self._grid_levels[i]
            upper = self._grid_levels[i + 1]

            if lower <= price < upper:
                grid_key = i

                if grid_key not in self._filled_grids:
                    if price < self.params["center_price"]:
                        self._filled_grids.add(grid_key)
                        return Signal(
                            signal_type=SignalType.BUY,
                            symbol=symbol,
                            price=price,
                            amount=amount,
                            reason=f"Grid buy at level {i}: price={price:.2f} in [{lower:.2f}, {upper:.2f})",
                        )
                else:
                    if price > self.params["center_price"]:
                        self._filled_grids.discard(grid_key)
                        return Signal(
                            signal_type=SignalType.SELL,
                            symbol=symbol,
                            price=price,
                            amount=amount,
                            reason=f"Grid sell at level {i}: price={price:.2f} in [{lower:.2f}, {upper:.2f})",
                        )
                break

        return Signal(signal_type=SignalType.HOLD, symbol=symbol, price=price)

    def reset(self):
        super().reset()
        self._grid_levels = []
        self._filled_grids = set()
