from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, Union

import pandas as pd
import numpy as np

from exchange.base import OrderSide, OrderType


class SignalType(Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    CLOSE_LONG = "close_long"
    CLOSE_SHORT = "close_short"


@dataclass
class Signal:
    signal_type: SignalType
    symbol: str
    price: float
    amount: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    order_type: OrderType = OrderType.MARKET
    confidence: float = 1.0
    reason: str = ""
    timestamp: Optional[pd.Timestamp] = None


@dataclass
class StrategyState:
    position_side: Optional[str] = None
    position_size: float = 0.0
    entry_price: float = 0.0
    unrealized_pnl: float = 0.0
    indicators: Dict[str, Any] = field(default_factory=dict)


class BaseStrategy(ABC):
    def __init__(self, name: str, params: Optional[Dict[str, Any]] = None):
        self.name = name
        self.params = params or {}
        self.state = StrategyState()
        self._data: Optional[pd.DataFrame] = None

    @property
    def data(self) -> Optional[pd.DataFrame]:
        return self._data

    @data.setter
    def data(self, value: pd.DataFrame):
        self._data = value

    def set_param(self, key: str, value: Any) -> None:
        self.params[key] = value

    def get_param(self, key: str, default: Any = None) -> Any:
        return self.params.get(key, default)

    @abstractmethod
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        pass

    @abstractmethod
    def generate_signal(self, data: pd.DataFrame) -> Signal:
        pass

    def on_tick(self, data: pd.DataFrame) -> Optional[Signal]:
        self._data = data
        data_with_indicators = self.calculate_indicators(data)
        signal = self.generate_signal(data_with_indicators)
        if signal and signal.timestamp is None and not data.empty:
            signal.timestamp = data.index[-1]
        return signal

    def reset(self) -> None:
        self.state = StrategyState()
        self._data = None

    def info(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "params": self.params,
            "position_side": self.state.position_side,
            "position_size": self.state.position_size,
        }
