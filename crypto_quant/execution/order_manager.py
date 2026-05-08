from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from exchange.base import Order, OrderSide, OrderType, OrderStatus, MarketType
from exchange.ccxt_connector import ExchangeFactory
from strategy.base import Signal, SignalType
from risk.manager import RiskManager, RiskCheckResult
from data.storage import DataStorage
from utils.logger import logger


@dataclass
class ExecutedTrade:
    order: Order
    signal: Signal
    risk_check: RiskCheckResult
    timestamp: datetime = field(default_factory=datetime.now)


class OrderManager:
    def __init__(self, exchange_id: str, risk_manager: RiskManager,
                 storage: DataStorage = None, dry_run: bool = False,
                 market_type: MarketType = MarketType.SPOT):
        self.exchange_id = exchange_id
        self.risk_manager = risk_manager
        self.storage = storage
        self.dry_run = dry_run
        self.market_type = market_type

        self._open_orders = {}
        self._trade_history = []
        self._connector = None

    @property
    def connector(self):
        if self._connector is None:
            self._connector = ExchangeFactory.create(self.exchange_id, self.market_type)
        return self._connector

    def execute_signal(self, signal: Signal, equity: float) -> Optional[ExecutedTrade]:
        if signal.signal_type == SignalType.HOLD:
            return None

        risk_check = self.risk_manager.check_signal(signal, equity)
        if not risk_check.approved:
            logger.warning(f"Signal rejected by risk manager: {risk_check.reason}")
            return None

        order_side = self._signal_to_order_side(signal)
        if order_side is None:
            return None

        amount = signal.amount or risk_check.adjusted_amount
        if not amount or amount <= 0:
            logger.warning("No valid amount for order")
            return None

        order_type = signal.order_type
        price = signal.price if order_type == OrderType.LIMIT else None

        if self.dry_run:
            order = Order(
                id=f"DRY_{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
                symbol=signal.symbol,
                side=order_side,
                order_type=order_type,
                price=signal.price,
                amount=amount,
                status=OrderStatus.FILLED,
                filled=amount,
                cost=amount * signal.price,
                timestamp=datetime.now(),
                exchange=self.exchange_id,
            )
            logger.info(f"[DRY RUN] Order: {order_side.value} {amount} {signal.symbol} @ {signal.price}")
        else:
            try:
                params = {}
                if signal.stop_loss:
                    params["stopLoss"] = {"triggerPrice": signal.stop_loss}
                if signal.take_profit:
                    params["takeProfit"] = {"triggerPrice": signal.take_profit}

                order = self.connector.create_order(
                    symbol=signal.symbol,
                    side=order_side,
                    order_type=order_type,
                    amount=amount,
                    price=price,
                    params=params if params else None,
                )
            except Exception as e:
                logger.error(f"Order execution failed: {e}")
                return None

        trade = ExecutedTrade(
            order=order,
            signal=signal,
            risk_check=risk_check,
        )
        self._trade_history.append(trade)

        if order.status in (OrderStatus.OPEN, OrderStatus.PENDING):
            self._open_orders[order.id] = order

        if self.storage and order.status == OrderStatus.FILLED:
            self.storage.save_trade(
                exchange=self.exchange_id,
                symbol=signal.symbol,
                order_id=order.id,
                side=order.side.value,
                price=order.price,
                amount=order.amount,
                cost=order.cost,
                strategy=signal.reason,
            )

        logger.info(
            f"Trade executed: {order_side.value} {amount} {signal.symbol} @ {signal.price:.2f} "
            f"| Risk: {risk_check.risk_level} | {'DRY RUN' if self.dry_run else 'LIVE'}"
        )
        return trade

    def cancel_open_orders(self, symbol: str = None) -> list:
        canceled = []
        orders_to_cancel = list(self._open_orders.items())

        for order_id, order in orders_to_cancel:
            if symbol and order.symbol != symbol:
                continue

            if self.dry_run:
                order.status = OrderStatus.CANCELED
                logger.info(f"[DRY RUN] Canceled order: {order_id}")
            else:
                try:
                    self.connector.cancel_order(order_id, order.symbol)
                    logger.info(f"Canceled order: {order_id}")
                except Exception as e:
                    logger.error(f"Failed to cancel order {order_id}: {e}")
                    continue

            self._open_orders.pop(order_id, None)
            canceled.append(order)

        return canceled

    def sync_open_orders(self, symbol: str = None):
        if self.dry_run:
            return
        try:
            open_orders = self.connector.get_open_orders(symbol or "")
            self._open_orders = {o.id: o for o in open_orders}
            self.risk_manager.update_open_orders(len(self._open_orders))
        except Exception as e:
            logger.error(f"Failed to sync open orders: {e}")

    def get_open_orders(self) -> list:
        return list(self._open_orders.values())

    def get_trade_history(self) -> list:
        return self._trade_history

    @staticmethod
    def _signal_to_order_side(signal: Signal) -> Optional[OrderSide]:
        mapping = {
            SignalType.BUY: OrderSide.BUY,
            SignalType.SELL: OrderSide.SELL,
            SignalType.CLOSE_LONG: OrderSide.SELL,
            SignalType.CLOSE_SHORT: OrderSide.BUY,
        }
        return mapping.get(signal.signal_type)
