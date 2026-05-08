from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderStatus(Enum):
    PENDING = "pending"
    OPEN = "open"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELED = "canceled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class MarketType(Enum):
    SPOT = "spot"
    FUTURE = "future"
    SWAP = "swap"


@dataclass
class Ticker:
    symbol: str
    last: float
    bid: float
    ask: float
    high: float
    low: float
    volume: float
    timestamp: datetime
    exchange: str = ""


@dataclass
class OHLCV:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class Order:
    id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    price: float
    amount: float
    status: OrderStatus = OrderStatus.PENDING
    filled: float = 0.0
    remaining: float = 0.0
    cost: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    exchange: str = ""
    params: dict = field(default_factory=dict)


@dataclass
class Position:
    symbol: str
    side: str
    size: float
    entry_price: float
    mark_price: float = 0.0
    unrealized_pnl: float = 0.0
    leverage: int = 1
    liquidation_price: float = 0.0
    exchange: str = ""


@dataclass
class Balance:
    currency: str
    free: float
    used: float
    total: float


@dataclass
class AccountInfo:
    balances: list = field(default_factory=list)
    total_equity: float = 0.0
    available_margin: float = 0.0
    unrealized_pnl: float = 0.0


class BaseExchange(ABC):
    @abstractmethod
    def get_ticker(self, symbol: str) -> Ticker:
        pass

    @abstractmethod
    def get_ohlcv(self, symbol: str, timeframe: str = "1h", limit: int = 100) -> list:
        pass

    @abstractmethod
    def get_order_book(self, symbol: str, limit: int = 20) -> dict:
        pass

    @abstractmethod
    def create_order(self, symbol: str, side: OrderSide, order_type: OrderType,
                     amount: float, price: Optional[float] = None, params: dict = None) -> Order:
        pass

    @abstractmethod
    def cancel_order(self, order_id: str, symbol: str) -> Order:
        pass

    @abstractmethod
    def get_order(self, order_id: str, symbol: str) -> Order:
        pass

    @abstractmethod
    def get_orders(self, symbol: str) -> list:
        pass

    @abstractmethod
    def get_open_orders(self, symbol: str) -> list:
        pass

    @abstractmethod
    def get_balance(self) -> AccountInfo:
        pass

    @abstractmethod
    def get_positions(self, symbols: list = None) -> list:
        pass

    @abstractmethod
    def set_leverage(self, symbol: str, leverage: int) -> bool:
        pass

    @abstractmethod
    def get_markets(self) -> list:
        pass
