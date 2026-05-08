import time
from datetime import datetime
from typing import Optional

import ccxt

from exchange.base import (
    BaseExchange, Ticker, OHLCV, Order, Position, Balance,
    AccountInfo, OrderSide, OrderType, OrderStatus, MarketType,
)
from config.settings import settings
from utils.logger import logger


class CcxtConnector(BaseExchange):
    def __init__(self, exchange_id: str, market_type: MarketType = MarketType.SPOT):
        self.exchange_id = exchange_id
        self.market_type = market_type
        self._exchange = self._create_exchange()

    def _create_exchange(self) -> ccxt.Exchange:
        exchange_config = settings.exchanges.get(self.exchange_id)
        if not exchange_config:
            raise ValueError(f"Exchange '{self.exchange_id}' not found in config")

        exchange_class = getattr(ccxt, self.exchange_id, None)
        if not exchange_class:
            raise ValueError(f"Exchange '{self.exchange_id}' not supported by ccxt")

        config = {
            "apiKey": exchange_config.get("api_key", ""),
            "secret": exchange_config.get("secret", ""),
            "enableRateLimit": True,
            "rateLimit": exchange_config.get("rate_limit", 1000),
            "options": exchange_config.get("options", {}),
        }

        if self.exchange_id == "okx":
            password = exchange_config.get("password", "")
            if password:
                config["password"] = password

        if exchange_config.get("sandbox", False):
            config["options"]["sandboxMode"] = True

        exchange = exchange_class(config)

        if self.market_type == MarketType.FUTURE or self.market_type == MarketType.SWAP:
            exchange.options["defaultType"] = "swap"
        else:
            exchange.options["defaultType"] = "spot"

        logger.info(f"Exchange connector created: {self.exchange_id} ({self.market_type.value})")
        return exchange

    @property
    def exchange(self) -> ccxt.Exchange:
        return self._exchange

    def _convert_side(self, side: OrderSide) -> str:
        return side.value

    def _convert_order_type(self, order_type: OrderType) -> str:
        return order_type.value

    def _parse_order(self, raw: dict) -> Order:
        status_map = {
            "open": OrderStatus.OPEN,
            "closed": OrderStatus.FILLED,
            "canceled": OrderStatus.CANCELED,
            "rejected": OrderStatus.REJECTED,
            "expired": OrderStatus.EXPIRED,
        }
        raw_status = raw.get("status", "")
        status = status_map.get(raw_status, OrderStatus.PENDING)

        side = OrderSide.BUY if raw.get("side") == "buy" else OrderSide.SELL
        otype = OrderType.MARKET if raw.get("type") == "market" else OrderType.LIMIT

        ts = raw.get("timestamp")
        timestamp = datetime.fromtimestamp(ts / 1000) if ts else datetime.now()

        return Order(
            id=str(raw.get("id", "")),
            symbol=raw.get("symbol", ""),
            side=side,
            order_type=otype,
            price=float(raw.get("price", 0) or 0),
            amount=float(raw.get("amount", 0) or 0),
            status=status,
            filled=float(raw.get("filled", 0) or 0),
            remaining=float(raw.get("remaining", 0) or 0),
            cost=float(raw.get("cost", 0) or 0),
            timestamp=timestamp,
            exchange=self.exchange_id,
            params=raw.get("info", {}),
        )

    def _parse_ticker(self, raw: dict) -> Ticker:
        ts = raw.get("timestamp")
        timestamp = datetime.fromtimestamp(ts / 1000) if ts else datetime.now()
        return Ticker(
            symbol=raw.get("symbol", ""),
            last=float(raw.get("last", 0) or 0),
            bid=float(raw.get("bid", 0) or 0),
            ask=float(raw.get("ask", 0) or 0),
            high=float(raw.get("high", 0) or 0),
            low=float(raw.get("low", 0) or 0),
            volume=float(raw.get("baseVolume", 0) or 0),
            timestamp=timestamp,
            exchange=self.exchange_id,
        )

    def get_ticker(self, symbol: str) -> Ticker:
        try:
            raw = self._exchange.fetch_ticker(symbol)
            return self._parse_ticker(raw)
        except ccxt.BaseError as e:
            logger.error(f"Failed to fetch ticker for {symbol}: {e}")
            raise

    def get_ohlcv(self, symbol: str, timeframe: str = "1h", limit: int = 100) -> list:
        try:
            raw_candles = self._exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            candles = []
            for c in raw_candles:
                candles.append(OHLCV(
                    timestamp=datetime.fromtimestamp(c[0] / 1000),
                    open=c[1],
                    high=c[2],
                    low=c[3],
                    close=c[4],
                    volume=c[5],
                ))
            return candles
        except ccxt.BaseError as e:
            logger.error(f"Failed to fetch OHLCV for {symbol}: {e}")
            raise

    def get_order_book(self, symbol: str, limit: int = 20) -> dict:
        try:
            return self._exchange.fetch_order_book(symbol, limit)
        except ccxt.BaseError as e:
            logger.error(f"Failed to fetch order book for {symbol}: {e}")
            raise

    def create_order(self, symbol: str, side: OrderSide, order_type: OrderType,
                     amount: float, price: Optional[float] = None, params: dict = None) -> Order:
        try:
            params = params or {}
            raw = self._exchange.create_order(
                symbol=symbol,
                type=self._convert_order_type(order_type),
                side=self._convert_side(side),
                amount=amount,
                price=price,
                params=params,
            )
            order = self._parse_order(raw)
            logger.info(f"Order created: {order.side.value} {order.amount} {order.symbol} @ {order.price}")
            return order
        except ccxt.BaseError as e:
            logger.error(f"Failed to create order: {e}")
            raise

    def cancel_order(self, order_id: str, symbol: str) -> Order:
        try:
            raw = self._exchange.cancel_order(order_id, symbol)
            order = self._parse_order(raw)
            logger.info(f"Order canceled: {order_id}")
            return order
        except ccxt.BaseError as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            raise

    def get_order(self, order_id: str, symbol: str) -> Order:
        try:
            raw = self._exchange.fetch_order(order_id, symbol)
            return self._parse_order(raw)
        except ccxt.BaseError as e:
            logger.error(f"Failed to fetch order {order_id}: {e}")
            raise

    def get_orders(self, symbol: str) -> list:
        try:
            raw_orders = self._exchange.fetch_orders(symbol)
            return [self._parse_order(o) for o in raw_orders]
        except ccxt.BaseError as e:
            logger.error(f"Failed to fetch orders for {symbol}: {e}")
            raise

    def get_open_orders(self, symbol: str) -> list:
        try:
            raw_orders = self._exchange.fetch_open_orders(symbol)
            return [self._parse_order(o) for o in raw_orders]
        except ccxt.BaseError as e:
            logger.error(f"Failed to fetch open orders for {symbol}: {e}")
            raise

    def get_balance(self) -> AccountInfo:
        try:
            raw = self._exchange.fetch_balance()
            balances = []
            for currency, amounts in raw.items():
                if currency in ("free", "used", "total", "info"):
                    continue
                if isinstance(amounts, dict):
                    balances.append(Balance(
                        currency=currency,
                        free=float(amounts.get("free", 0) or 0),
                        used=float(amounts.get("used", 0) or 0),
                        total=float(amounts.get("total", 0) or 0),
                    ))
                elif isinstance(amounts, (int, float)):
                    if amounts > 0:
                        balances.append(Balance(
                            currency=currency,
                            free=float(raw.get("free", {}).get(currency, 0) or 0),
                            used=float(raw.get("used", {}).get(currency, 0) or 0),
                            total=float(amounts),
                        ))

            total_equity = float(raw.get("total", {}).get("USDT", 0) or 0)

            return AccountInfo(
                balances=balances,
                total_equity=total_equity,
            )
        except ccxt.BaseError as e:
            logger.error(f"Failed to fetch balance: {e}")
            raise

    def get_positions(self, symbols: list = None) -> list:
        try:
            if self.market_type == MarketType.SPOT:
                return []

            raw_positions = self._exchange.fetch_positions(symbols)
            positions = []
            for p in raw_positions:
                positions.append(Position(
                    symbol=p.get("symbol", ""),
                    side=p.get("side", ""),
                    size=float(p.get("contracts", 0) or 0),
                    entry_price=float(p.get("entryPrice", 0) or 0),
                    mark_price=float(p.get("markPrice", 0) or 0),
                    unrealized_pnl=float(p.get("unrealizedPnl", 0) or 0),
                    leverage=int(p.get("leverage", 1) or 1),
                    liquidation_price=float(p.get("liquidationPrice", 0) or 0),
                    exchange=self.exchange_id,
                ))
            return positions
        except ccxt.BaseError as e:
            logger.error(f"Failed to fetch positions: {e}")
            raise

    def set_leverage(self, symbol: str, leverage: int) -> bool:
        try:
            if hasattr(self._exchange, "set_leverage"):
                self._exchange.set_leverage(leverage, symbol)
                logger.info(f"Leverage set to {leverage}x for {symbol}")
                return True
            logger.warning(f"set_leverage not supported for {self.exchange_id}")
            return False
        except ccxt.BaseError as e:
            logger.error(f"Failed to set leverage for {symbol}: {e}")
            return False

    def get_markets(self) -> list:
        try:
            self._exchange.load_markets()
            return list(self._exchange.markets.keys())
        except ccxt.BaseError as e:
            logger.error(f"Failed to fetch markets: {e}")
            raise


class ExchangeFactory:
    _instances = {}

    @classmethod
    def create(cls, exchange_id: str, market_type: MarketType = MarketType.SPOT) -> CcxtConnector:
        key = f"{exchange_id}_{market_type.value}"
        if key not in cls._instances:
            cls._instances[key] = CcxtConnector(exchange_id, market_type)
        return cls._instances[key]

    @classmethod
    def reset(cls):
        cls._instances.clear()
