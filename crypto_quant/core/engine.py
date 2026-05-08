import time
import signal as sig
from datetime import datetime
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler

from core.event_bus import EventBus, Event, EventType
from exchange.base import MarketType
from exchange.ccxt_connector import ExchangeFactory
from strategy.base import BaseStrategy, SignalType
from risk.manager import RiskManager
from execution.order_manager import OrderManager
from portfolio.tracker import PortfolioTracker
from data.manager import DataManager
from data.storage import DataStorage
from notification.notifier import Notifier
from config.settings import settings
from utils.logger import logger


class TradingEngine:
    def __init__(self, exchange_id: str, strategy: BaseStrategy,
                 symbol: str = "BTC/USDT", timeframe: str = "1h",
                 market_type: MarketType = MarketType.SPOT,
                 dry_run: bool = True):
        self.exchange_id = exchange_id
        self.strategy = strategy
        self.symbol = symbol
        self.timeframe = timeframe
        self.market_type = market_type
        self.dry_run = dry_run

        strategy.set_param("symbol", symbol)
        strategy.set_param("timeframe", timeframe)

        self.event_bus = EventBus()
        self.storage = DataStorage()
        self.data_manager = DataManager(self.storage)
        self.risk_manager = RiskManager()
        self.notifier = Notifier()

        self.order_manager = OrderManager(
            exchange_id=exchange_id,
            risk_manager=self.risk_manager,
            storage=self.storage,
            dry_run=dry_run,
            market_type=market_type,
        )

        self.portfolio_tracker = PortfolioTracker(exchange_id, market_type)

        self._running = False
        self._scheduler = BackgroundScheduler()
        self._position_side = None
        self._position_size = 0.0
        self._entry_price = 0.0

    def start(self):
        logger.info(
            f"Starting trading engine: {self.strategy.name} | "
            f"{self.exchange_id}/{self.symbol}/{self.timeframe} | "
            f"Mode: {'DRY RUN' if self.dry_run else 'LIVE'}"
        )

        self._running = True
        self.event_bus.publish(Event(EventType.STRATEGY_START, {
            "strategy": self.strategy.name,
            "symbol": self.symbol,
            "exchange": self.exchange_id,
        }))

        self._scheduler.add_job(
            self._on_tick,
            "interval",
            minutes=self._timeframe_to_minutes(),
            id="trading_tick",
            replace_existing=True,
        )
        self._scheduler.add_job(
            self._update_portfolio,
            "interval",
            minutes=5,
            id="portfolio_update",
            replace_existing=True,
        )
        self._scheduler.start()

        logger.info(f"Scheduler started, tick interval: {self._timeframe_to_minutes()} min")

        try:
            while self._running:
                time.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            self.stop()

    def stop(self):
        logger.info("Stopping trading engine...")
        self._running = False
        self._scheduler.shutdown(wait=False)
        self.event_bus.publish(Event(EventType.STRATEGY_STOP, {
            "strategy": self.strategy.name,
        }))
        logger.info("Trading engine stopped")

    def run_once(self) -> Optional[dict]:
        return self._on_tick()

    def _on_tick(self) -> Optional[dict]:
        if not self._running:
            return None

        try:
            data = self.data_manager.get_latest_candles(
                self.exchange_id, self.symbol, self.timeframe,
                limit=200, market_type=self.market_type,
            )

            if data.empty:
                logger.warning("No data available")
                return None

            self.event_bus.publish(Event(EventType.TICK, {
                "symbol": self.symbol,
                "price": data["close"].iloc[-1],
                "timestamp": str(data.index[-1]),
            }))

            signal = self.strategy.on_tick(data)

            if signal and signal.signal_type != SignalType.HOLD:
                self.event_bus.publish(Event(EventType.SIGNAL, {
                    "type": signal.signal_type.value,
                    "symbol": signal.symbol,
                    "price": signal.price,
                    "reason": signal.reason,
                }))

                self.notifier.notify_strategy_signal(
                    self.strategy.name, signal.signal_type.value,
                    signal.symbol, signal.reason,
                )

                equity = self.portfolio_tracker.get_total_equity()
                if equity <= 0:
                    equity = settings.backtest.get("initial_capital", 10000)

                trade = self.order_manager.execute_signal(signal, equity)

                if trade:
                    self._update_position_from_trade(trade)

                    self.event_bus.publish(Event(EventType.ORDER_FILLED, {
                        "order_id": trade.order.id,
                        "side": trade.order.side.value,
                        "symbol": trade.order.symbol,
                        "price": trade.order.price,
                        "amount": trade.order.amount,
                    }))

                    self.notifier.notify_trade(
                        trade.order.side.value,
                        trade.order.symbol,
                        trade.order.amount,
                        trade.order.price,
                    )

            self._check_risk_controls(data["close"].iloc[-1])

            return {
                "signal": signal.signal_type.value if signal else "hold",
                "price": data["close"].iloc[-1],
                "position": self._position_side,
                "timestamp": str(datetime.now()),
            }

        except Exception as e:
            logger.error(f"Tick error: {e}")
            self.event_bus.publish(Event(EventType.ERROR, {"error": str(e)}))
            return None

    def _update_portfolio(self):
        try:
            snapshot = self.portfolio_tracker.update()
            self.risk_manager.update_equity(snapshot.total_equity)
            self.risk_manager.update_exposure(
                sum(p.size * p.mark_price for p in snapshot.positions)
            )
        except Exception as e:
            logger.error(f"Portfolio update error: {e}")

    def _update_position_from_trade(self, trade):
        from exchange.base import OrderSide
        if trade.order.side == OrderSide.BUY:
            self._position_side = "long"
            self._position_size += trade.order.amount
            if self._entry_price == 0:
                self._entry_price = trade.order.price
        elif trade.order.side == OrderSide.SELL:
            if self._position_side == "long":
                pnl = (trade.order.price - self._entry_price) * self._position_size
                self.risk_manager.update_pnl(pnl)
                self._position_side = None
                self._position_size = 0.0
                self._entry_price = 0.0

    def _check_risk_controls(self, current_price: float):
        if self._position_side == "long" and self._entry_price > 0:
            if self.risk_manager.check_stop_loss(self._entry_price, current_price, "long"):
                self.notifier.notify_risk_alert(
                    f"Stop loss triggered for {self.symbol}: entry={self._entry_price:.2f}, current={current_price:.2f}",
                    level="critical",
                )
            elif self.risk_manager.check_take_profit(self._entry_price, current_price, "long"):
                self.notifier.notify_risk_alert(
                    f"Take profit target reached for {self.symbol}: entry={self._entry_price:.2f}, current={current_price:.2f}",
                    level="info",
                )

    def _timeframe_to_minutes(self) -> int:
        mapping = {
            "1m": 1, "3m": 3, "5m": 5, "15m": 15, "30m": 30,
            "1h": 60, "2h": 120, "4h": 240, "6h": 360, "12h": 720,
            "1d": 1440, "1w": 10080,
        }
        return mapping.get(self.timeframe, 60)

    def get_status(self) -> dict:
        return {
            "running": self._running,
            "dry_run": self.dry_run,
            "exchange": self.exchange_id,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "strategy": self.strategy.info(),
            "risk": self.risk_manager.get_status(),
            "position": {
                "side": self._position_side,
                "size": self._position_size,
                "entry_price": self._entry_price,
            },
            "open_orders": len(self.order_manager.get_open_orders()),
            "trade_history_count": len(self.order_manager.get_trade_history()),
        }
