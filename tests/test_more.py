import pytest
import pandas as pd
from datetime import datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "crypto_quant"))

from strategy.base import Signal, SignalType
from strategy.macd import MACDStrategy


class TestMACDStrategy:
    def test_init_default_params(self):
        strategy = MACDStrategy()
        assert strategy.name == "MACD"
        assert strategy.params["fast_period"] == 12
        assert strategy.params["slow_period"] == 26
        assert strategy.params["signal_period"] == 9

    def test_init_custom_params(self):
        strategy = MACDStrategy(fast_period=20, slow_period=40, signal_period=10)
        assert strategy.params["fast_period"] == 20
        assert strategy.params["slow_period"] == 40
        assert strategy.params["signal_period"] == 10

    def test_calculate_indicators(self, sample_ohlcv_data):
        strategy = MACDStrategy(fast_period=12, slow_period=26, signal_period=9)
        result = strategy.calculate_indicators(sample_ohlcv_data)
        assert "macd_line" in result.columns
        assert "signal_line" in result.columns
        assert "histogram" in result.columns
        assert "histogram_prev" in result.columns

    def test_generate_signal(self, sample_ohlcv_data):
        strategy = MACDStrategy()
        strategy.set_param("symbol", "BTC/USDT")
        result = strategy.calculate_indicators(sample_ohlcv_data)
        signal = strategy.generate_signal(result)
        assert isinstance(signal, Signal)
        assert signal.symbol == "BTC/USDT"

    def test_on_tick(self, sample_ohlcv_data):
        strategy = MACDStrategy()
        strategy.set_param("symbol", "BTC/USDT")
        signal = strategy.on_tick(sample_ohlcv_data)
        assert signal is not None
        assert signal.timestamp is not None

    def test_reset(self, sample_ohlcv_data):
        strategy = MACDStrategy()
        strategy.on_tick(sample_ohlcv_data)
        strategy.reset()
        assert strategy._data is None
        assert strategy.state.position_side is None


class TestDataValidators:
    def test_safe_float_valid(self):
        from utils.validators import safe_float
        assert safe_float("123.45") == 123.45
        assert safe_float(123.45) == 123.45
        assert safe_float(0) == 0.0

    def test_safe_float_invalid(self):
        from utils.validators import safe_float
        assert safe_float(None, -1.0) == -1.0
        assert safe_float("abc", -1.0) == -1.0
        assert safe_float("") == 0.0

    def test_safe_int_valid(self):
        from utils.validators import safe_int
        assert safe_int("100") == 100
        assert safe_int(100.5) == 100

    def test_safe_int_invalid(self):
        from utils.validators import safe_int
        assert safe_int(None, -1) == -1
        assert safe_int("abc", -1) == -1

    def test_safe_bool(self):
        from utils.validators import safe_bool
        assert safe_bool("true") is True
        assert safe_bool("false") is False
        assert safe_bool("1") is True
        assert safe_bool("0") is False
        assert safe_bool(None) is False
        assert safe_bool("yes") is True

    def test_validate_positive(self):
        from utils.validators import validate_positive
        assert validate_positive(10.0, "value") == 10.0
        with pytest.raises(ValueError):
            validate_positive(-1.0, "value")
        with pytest.raises(ValueError):
            validate_positive(0.0, "value")

    def test_validate_non_negative(self):
        from utils.validators import validate_non_negative
        assert validate_non_negative(0.0, "value") == 0.0
        assert validate_non_negative(10.0, "value") == 10.0
        with pytest.raises(ValueError):
            validate_non_negative(-1.0, "value")

    def test_validate_range(self):
        from utils.validators import validate_range
        assert validate_range(50.0, 0.0, 100.0, "value") == 50.0
        with pytest.raises(ValueError):
            validate_range(150.0, 0.0, 100.0, "value")
        with pytest.raises(ValueError):
            validate_range(-10.0, 0.0, 100.0, "value")


class TestConstants:
    def test_time_constants(self):
        from config.constants import TimeConstants
        assert TimeConstants.PORTFOLIO_UPDATE_INTERVAL_MINUTES == 5
        assert TimeConstants.DEFAULT_TIMEFRAME == "1h"
        assert TimeConstants.DEFAULT_CANDLE_LIMIT == 100

    def test_risk_constants(self):
        from config.constants import RiskConstants
        assert RiskConstants.DEFAULT_MAX_POSITION_SIZE_PCT == 0.1
        assert RiskConstants.DEFAULT_STOP_LOSS_PCT == 0.05
        assert RiskConstants.DEFAULT_TAKE_PROFIT_PCT == 0.1
        assert RiskConstants.DEFAULT_MAX_DRAWDOWN_PCT == 0.2

    def test_backtest_constants(self):
        from config.constants import BacktestConstants
        assert BacktestConstants.DEFAULT_INITIAL_CAPITAL == 10000
        assert BacktestConstants.DEFAULT_COMMISSION == 0.001
        assert BacktestConstants.DEFAULT_SLIPPAGE == 0.0005

    def test_trading_constants(self):
        from config.constants import TradingConstants
        assert TradingConstants.DEFAULT_EXCHANGE == "binance"
        assert TradingConstants.DEFAULT_SYMBOL == "BTC/USDT"
        assert TradingConstants.DEFAULT_MARKET_TYPE == "spot"


class TestEventBus:
    def test_subscribe_and_publish(self):
        from core.event_bus import EventBus, Event, EventType
        bus = EventBus()
        results = []

        def callback(event):
            results.append(event)

        bus.subscribe(EventType.TICK, callback)
        event = Event(event_type=EventType.TICK, data={"data": "test"})
        bus.publish(event)

        assert len(results) == 1
        assert results[0].data == {"data": "test"}

    def test_unsubscribe(self):
        from core.event_bus import EventBus, Event, EventType
        bus = EventBus()
        results = []

        def callback(event):
            results.append(event)

        bus.subscribe(EventType.TICK, callback)
        bus.unsubscribe(EventType.TICK, callback)
        event = Event(event_type=EventType.TICK, data={"data": "test"})
        bus.publish(event)

        assert len(results) == 0

    def test_multiple_subscribers(self):
        from core.event_bus import EventBus, Event, EventType
        bus = EventBus()
        results1 = []
        results2 = []

        def callback1(event):
            results1.append(event)

        def callback2(event):
            results2.append(event)

        bus.subscribe(EventType.TICK, callback1)
        bus.subscribe(EventType.TICK, callback2)
        event = Event(event_type=EventType.TICK, data={"data": "multi"})
        bus.publish(event)

        assert len(results1) == 1
        assert len(results2) == 1

    def test_event_types(self):
        from core.event_bus import EventType
        assert EventType.TICK.value == "tick"
        assert EventType.SIGNAL.value == "signal"
        assert EventType.ORDER_FILLED.value == "order_filled"
        assert EventType.RISK_ALERT.value == "risk_alert"

    def test_clear(self):
        from core.event_bus import EventBus, Event, EventType
        bus = EventBus()
        results = []

        def callback(event):
            results.append(event)

        bus.subscribe(EventType.TICK, callback)
        bus.clear()
        event = Event(event_type=EventType.TICK, data={"data": "clear"})
        bus.publish(event)

        assert len(results) == 0


class TestOrderTypes:
    def test_order_side_enum(self):
        from exchange.base import OrderSide
        assert OrderSide.BUY.value == "buy"
        assert OrderSide.SELL.value == "sell"

    def test_order_type_enum(self):
        from exchange.base import OrderType
        assert OrderType.MARKET.value == "market"
        assert OrderType.LIMIT.value == "limit"
