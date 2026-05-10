import pytest
import numpy as np
import pandas as pd
from datetime import datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "crypto_quant"))

from strategy.ma_cross import MACrossStrategy
from backtest.engine import BacktestEngine, BacktestResult, print_backtest_result


class TestBacktestEngine:
    def test_init_default_config(self, sample_ohlcv_data):
        strategy = MACrossStrategy(fast_period=10, slow_period=30)
        strategy.set_param("symbol", "BTC/USDT")
        strategy.set_param("timeframe", "1h")
        engine = BacktestEngine(strategy, sample_ohlcv_data)
        assert engine.initial_capital == 10000
        assert engine.commission == 0.001
        assert engine.slippage == 0.0005

    def test_init_custom_config(self, sample_ohlcv_data):
        strategy = MACrossStrategy()
        strategy.set_param("symbol", "BTC/USDT")
        engine = BacktestEngine(
            strategy, sample_ohlcv_data,
            initial_capital=50000,
            commission=0.002,
            slippage=0.001,
        )
        assert engine.initial_capital == 50000
        assert engine.commission == 0.002
        assert engine.slippage == 0.001

    def test_run_backtest(self, sample_ohlcv_data):
        strategy = MACrossStrategy(fast_period=10, slow_period=30)
        strategy.set_param("symbol", "BTC/USDT")
        strategy.set_param("timeframe", "1h")
        engine = BacktestEngine(strategy, sample_ohlcv_data, initial_capital=10000)
        result = engine.run()
        assert isinstance(result, BacktestResult)
        assert result.strategy_name == "MA_Cross"
        assert result.initial_capital == 10000
        assert result.final_capital >= 0
        assert result.total_trades >= 0

    def test_backtest_result_metrics(self, sample_ohlcv_data):
        strategy = MACrossStrategy(fast_period=10, slow_period=30)
        strategy.set_param("symbol", "BTC/USDT")
        strategy.set_param("timeframe", "1h")
        engine = BacktestEngine(strategy, sample_ohlcv_data, initial_capital=10000)
        result = engine.run()
        assert result.start_date is not None
        assert result.end_date is not None
        assert result.total_return_pct is not None
        assert result.max_drawdown_pct >= 0
        assert 0 <= result.win_rate <= 100 if result.total_trades > 0 else result.win_rate == 0
        assert result.profit_factor >= 0

    def test_backtest_equity_curve(self, sample_ohlcv_data):
        strategy = MACrossStrategy(fast_period=10, slow_period=30)
        strategy.set_param("symbol", "BTC/USDT")
        strategy.set_param("timeframe", "1h")
        engine = BacktestEngine(strategy, sample_ohlcv_data, initial_capital=10000)
        result = engine.run()
        assert len(result.equity_curve) > 0
        assert all("equity" in e for e in result.equity_curve)
        assert all("timestamp" in e for e in result.equity_curve)

    def test_backtest_trades(self, sample_ohlcv_data):
        strategy = MACrossStrategy(fast_period=10, slow_period=30)
        strategy.set_param("symbol", "BTC/USDT")
        strategy.set_param("timeframe", "1h")
        engine = BacktestEngine(strategy, sample_ohlcv_data, initial_capital=10000)
        result = engine.run()
        for trade in result.trades:
            assert trade.entry_price > 0
            assert trade.amount >= 0
            assert trade.entry_time is not None

    def test_sharpe_ratio_calculation(self, sample_ohlcv_data):
        strategy = MACrossStrategy(fast_period=10, slow_period=30)
        strategy.set_param("symbol", "BTC/USDT")
        strategy.set_param("timeframe", "1h")
        engine = BacktestEngine(strategy, sample_ohlcv_data, initial_capital=10000)
        result = engine.run()
        assert isinstance(result.sharpe_ratio, float)

    def test_empty_data_backtest(self, empty_df):
        strategy = MACrossStrategy()
        strategy.set_param("symbol", "BTC/USDT")
        strategy.set_param("timeframe", "1h")
        engine = BacktestEngine(strategy, empty_df, initial_capital=10000)
        result = engine.run()
        assert result.total_trades == 0
        assert result.final_capital == 10000

    def test_backtest_position_management(self, sample_ohlcv_data):
        strategy = MACrossStrategy(fast_period=10, slow_period=30)
        strategy.set_param("symbol", "BTC/USDT")
        strategy.set_param("timeframe", "1h")
        engine = BacktestEngine(strategy, sample_ohlcv_data, initial_capital=10000)
        engine.run()
        assert engine.position == 0
