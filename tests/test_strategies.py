import pytest
import numpy as np
import pandas as pd
from datetime import datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "crypto_quant"))

from strategy.base import SignalType, Signal
from strategy.ma_cross import MACrossStrategy
from strategy.rsi import RSIStrategy
from strategy.grid import GridStrategy


class TestMACrossStrategy:
    def test_init_default_params(self):
        strategy = MACrossStrategy()
        assert strategy.name == "MA_Cross"
        assert strategy.params["fast_period"] == 10
        assert strategy.params["slow_period"] == 30

    def test_init_custom_params(self):
        strategy = MACrossStrategy(fast_period=20, slow_period=50)
        assert strategy.params["fast_period"] == 20
        assert strategy.params["slow_period"] == 50

    def test_calculate_indicators(self, sample_ohlcv_data):
        strategy = MACrossStrategy(fast_period=10, slow_period=30)
        result = strategy.calculate_indicators(sample_ohlcv_data)
        assert "ma_fast" in result.columns
        assert "ma_slow" in result.columns
        assert "ma_diff" in result.columns
        assert "ma_diff_prev" in result.columns

    def test_generate_signal_golden_cross(self, sample_ohlcv_data):
        strategy = MACrossStrategy(fast_period=10, slow_period=30)
        strategy.set_param("symbol", "BTC/USDT")
        result = strategy.calculate_indicators(sample_ohlcv_data)
        signal = strategy.generate_signal(result)
        assert isinstance(signal, Signal)
        assert signal.symbol == "BTC/USDT"
        assert signal.price > 0

    def test_generate_signal_insufficient_data(self, empty_df):
        strategy = MACrossStrategy(fast_period=10, slow_period=30)
        result = strategy.calculate_indicators(empty_df)
        signal = strategy.generate_signal(result)
        assert signal.signal_type == SignalType.HOLD

    def test_on_tick(self, sample_ohlcv_data):
        strategy = MACrossStrategy(fast_period=10, slow_period=30)
        strategy.set_param("symbol", "BTC/USDT")
        signal = strategy.on_tick(sample_ohlcv_data)
        assert signal is not None
        assert signal.timestamp is not None

    def test_reset(self, sample_ohlcv_data):
        strategy = MACrossStrategy()
        strategy.on_tick(sample_ohlcv_data)
        strategy.reset()
        assert strategy._data is None
        assert strategy.state.position_side is None

    def test_set_param(self):
        strategy = MACrossStrategy()
        strategy.set_param("symbol", "ETH/USDT")
        assert strategy.params["symbol"] == "ETH/USDT"

    def test_get_param(self):
        strategy = MACrossStrategy(fast_period=20)
        assert strategy.get_param("fast_period") == 20
        assert strategy.get_param("nonexistent", "default") == "default"

    def test_info(self):
        strategy = MACrossStrategy(fast_period=15, slow_period=40)
        info = strategy.info()
        assert info["name"] == "MA_Cross"
        assert info["params"]["fast_period"] == 15


class TestRSIStrategy:
    def test_init_default_params(self):
        strategy = RSIStrategy()
        assert strategy.name == "RSI"
        assert strategy.params["period"] == 14
        assert strategy.params["oversold"] == 30
        assert strategy.params["overbought"] == 70

    def test_calculate_indicators(self, sample_ohlcv_data):
        strategy = RSIStrategy(period=14)
        result = strategy.calculate_indicators(sample_ohlcv_data)
        assert "rsi" in result.columns
        assert not result["rsi"].isna().all()

    def test_rsi_values_range(self, sample_ohlcv_data):
        strategy = RSIStrategy(period=14)
        result = strategy.calculate_indicators(sample_ohlcv_data)
        rsi_values = result["rsi"].dropna()
        if len(rsi_values) > 0:
            assert rsi_values.min() >= 0
            assert rsi_values.max() <= 100

    def test_generate_signal(self, sample_ohlcv_data):
        strategy = RSIStrategy()
        strategy.set_param("symbol", "BTC/USDT")
        result = strategy.calculate_indicators(sample_ohlcv_data)
        signal = strategy.generate_signal(result)
        assert isinstance(signal, Signal)


class TestGridStrategy:
    def test_init_default_params(self):
        strategy = GridStrategy()
        assert strategy.name == "Grid"
        assert strategy.params["grid_num"] == 10
        assert strategy.params["grid_range_pct"] == 0.05
        assert strategy.params["amount_per_grid"] == 0.001

    def test_calculate_indicators(self, sample_ohlcv_data):
        strategy = GridStrategy(grid_num=10, grid_range_pct=0.05)
        result = strategy.calculate_indicators(sample_ohlcv_data)
        assert "grid_center" in result.columns
        assert "grid_upper" in result.columns
        assert "grid_lower" in result.columns
        assert len(strategy._grid_levels) == 11

    def test_generate_signal(self, sample_ohlcv_data):
        strategy = GridStrategy()
        strategy.set_param("symbol", "BTC/USDT")
        result = strategy.calculate_indicators(sample_ohlcv_data)
        signal = strategy.generate_signal(result)
        assert isinstance(signal, Signal)

    def test_reset(self, sample_ohlcv_data):
        strategy = GridStrategy()
        strategy.calculate_indicators(sample_ohlcv_data)
        assert len(strategy._grid_levels) > 0
        strategy.reset()
        assert len(strategy._grid_levels) == 0
        assert len(strategy._filled_grids) == 0


class TestBaseStrategy:
    def test_base_strategy_abstract(self):
        with pytest.raises(TypeError):
            from strategy.base import BaseStrategy
            BaseStrategy()

    def test_signal_creation(self):
        signal = Signal(
            signal_type=SignalType.BUY,
            symbol="BTC/USDT",
            price=50000.0,
            amount=0.001,
            stop_loss=49000.0,
            take_profit=52000.0,
        )
        assert signal.signal_type == SignalType.BUY
        assert signal.price == 50000.0
        assert signal.stop_loss == 49000.0
        assert signal.take_profit == 52000.0
