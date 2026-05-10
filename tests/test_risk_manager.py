import pytest
import numpy as np
import pandas as pd

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "crypto_quant"))

from strategy.base import Signal, SignalType
from risk.manager import RiskManager, RiskCheckResult


class TestRiskManager:
    def test_init_default_config(self):
        rm = RiskManager()
        assert rm.max_position_size_pct == 0.1
        assert rm.stop_loss_pct == 0.05
        assert rm.take_profit_pct == 0.1
        assert rm.max_drawdown_pct == 0.2

    def test_init_custom_config(self):
        rm = RiskManager(config={"max_position_size_pct": 0.2, "stop_loss_pct": 0.1})
        assert rm.max_position_size_pct == 0.2
        assert rm.stop_loss_pct == 0.1

    def test_update_equity(self):
        rm = RiskManager()
        rm.update_equity(10000)
        assert rm._current_equity == 10000
        assert rm._peak_equity == 10000

    def test_update_equity_peak_tracking(self):
        rm = RiskManager()
        rm.update_equity(10000)
        rm.update_equity(12000)
        rm.update_equity(11000)
        assert rm._peak_equity == 12000
        assert rm._current_equity == 11000

    def test_daily_pnl_reset(self):
        rm = RiskManager()
        rm.update_equity(10000)
        rm.update_pnl(-100)
        assert rm._daily_pnl == -100

    def test_check_signal_hold(self):
        rm = RiskManager()
        rm.update_equity(10000)
        signal = Signal(signal_type=SignalType.HOLD, symbol="", price=0)
        result = rm.check_signal(signal, 10000)
        assert result.approved is True

    def test_check_signal_insufficient_equity(self):
        rm = RiskManager()
        signal = Signal(signal_type=SignalType.BUY, symbol="BTC/USDT", price=50000, amount=0.001)
        result = rm.check_signal(signal, 0)
        assert result.approved is False

    def test_position_size_adjustment(self):
        rm = RiskManager()
        rm.update_equity(10000)
        rm._total_exposure = 0
        signal = Signal(signal_type=SignalType.BUY, symbol="BTC/USDT", price=50000, amount=0.001)
        result = rm.check_signal(signal, 10000)
        assert result.approved is True

    def test_daily_loss_limit(self):
        rm = RiskManager()
        rm.update_equity(10000)
        rm._daily_pnl = -500
        signal = Signal(signal_type=SignalType.BUY, symbol="BTC/USDT", price=50000, amount=0.001)
        result = rm.check_signal(signal, 10000)
        assert result.approved is False or result.risk_level == "critical"

    def test_check_stop_loss_long(self):
        rm = RiskManager()
        assert rm.check_stop_loss(100, 94, "long") is True
        assert rm.check_stop_loss(100, 96, "long") is False

    def test_check_stop_loss_short(self):
        rm = RiskManager()
        assert rm.check_stop_loss(100, 106, "short") is True
        assert rm.check_stop_loss(100, 104, "short") is False

    def test_check_take_profit_long(self):
        rm = RiskManager()
        assert rm.check_take_profit(100, 110, "long") is True
        assert rm.check_take_profit(100, 105, "long") is False

    def test_check_take_profit_short(self):
        rm = RiskManager()
        assert rm.check_take_profit(100, 90, "short") is True
        assert rm.check_take_profit(100, 95, "short") is False

    def test_get_status(self):
        rm = RiskManager()
        rm.update_equity(10000)
        rm.update_pnl(100)
        status = rm.get_status()
        assert "current_equity" in status
        assert "daily_pnl" in status
        assert status["current_equity"] == 10000
        assert status["daily_pnl"] == 100

    def test_auto_stop_loss_take_profit(self):
        rm = RiskManager()
        rm.update_equity(10000)
        signal = Signal(signal_type=SignalType.BUY, symbol="BTC/USDT", price=50000, amount=0.001)
        rm.check_signal(signal, 10000)
        assert signal.stop_loss is not None
        assert signal.take_profit is not None
        assert signal.stop_loss < 50000
        assert signal.take_profit > 50000
