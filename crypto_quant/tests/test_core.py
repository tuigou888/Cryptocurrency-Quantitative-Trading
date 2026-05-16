import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from strategy.base import BaseStrategy, Signal, SignalType, StrategyState
from strategy.ma_cross import MACrossStrategy
from backtest.engine import BacktestEngine, BacktestResult
from risk.enhanced_manager import EnhancedRiskManager, CircuitBreaker, CircuitState, RiskCheckResult
from exchange.base import OrderType, OrderSide
from execution.simulator import ExecutionSimulator, ExecutionResult, LiquidityProfile
from utils.rate_limiter import RateLimiter
from data.processor import VectorizedDataProcessor


class TestMACrossStrategy:
    def test_calculate_indicators(self):
        data = pd.DataFrame({
            "open": [100, 101, 102, 103, 104, 105, 106, 107, 108, 109,
                     110, 111, 112, 113, 114, 115, 116, 117, 118, 119,
                     120, 121, 122, 123, 124, 125, 126, 127, 128, 129,
                     130, 131, 132, 133, 134, 135],
            "high": [102, 103, 104, 105, 106, 107, 108, 109, 110, 111,
                     112, 113, 114, 115, 116, 117, 118, 119, 120, 121,
                     122, 123, 124, 125, 126, 127, 128, 129, 130, 131,
                     132, 133, 134, 135, 136, 137],
            "low": [99, 100, 101, 102, 103, 104, 105, 106, 107, 108,
                    109, 110, 111, 112, 113, 114, 115, 116, 117, 118,
                    119, 120, 121, 122, 123, 124, 125, 126, 127, 128,
                    129, 130, 131, 132, 133, 134],
            "close": [101, 102, 103, 104, 105, 106, 107, 108, 109, 110,
                      111, 112, 113, 114, 115, 116, 117, 118, 119, 120,
                      121, 122, 123, 124, 125, 126, 127, 128, 129, 130,
                      131, 132, 133, 134, 135, 136],
            "volume": [1000] * 36,
        }, index=pd.date_range(start="2024-01-01", periods=36, freq="1h"))

        strategy = MACrossStrategy(fast_period=10, slow_period=30)
        result = strategy.calculate_indicators(data)

        assert "ma_fast" in result.columns
        assert "ma_slow" in result.columns
        assert not result["ma_fast"].isna().all()
        assert not result["ma_slow"].isna().all()

    def test_generate_signal_golden_cross(self):
        dates = pd.date_range(start="2024-01-01", periods=50, freq="1h")
        data = pd.DataFrame({
            "close": np.concatenate([
                np.linspace(100, 150, 30),
                np.linspace(150, 100, 20),
            ]),
            "open": np.linspace(99, 151, 50),
            "high": np.linspace(101, 153, 50),
            "low": np.linspace(98, 149, 50),
            "volume": [1000] * 50,
        }, index=dates)

        strategy = MACrossStrategy(fast_period=10, slow_period=30)
        indicators = strategy.calculate_indicators(data)
        strategy.indicators = indicators

        signal = strategy.generate_signal(indicators)
        assert signal is not None

    def test_reset(self):
        strategy = MACrossStrategy(fast_period=10, slow_period=30)
        strategy.state = StrategyState(position_size=100)
        strategy.indicators = pd.DataFrame({"test": [1, 2, 3]})

        strategy.reset()

        assert strategy.state.position_size == 0
        assert strategy.indicators is None


class TestBacktestEngine:
    def test_backtest_no_trades(self):
        dates = pd.date_range(start="2024-01-01", periods=100, freq="1h")
        data = pd.DataFrame({
            "close": np.cumsum(np.random.randn(100) * 0.01 + 0.001) + 100,
            "open": [100.0] * 100,
            "high": [105.0] * 100,
            "low": [95.0] * 100,
            "volume": [1000] * 100,
        }, index=dates)

        strategy = MACrossStrategy(fast_period=10, slow_period=30)
        engine = BacktestEngine(strategy, data, initial_capital=10000)
        result = engine.run()

        assert isinstance(result, BacktestResult)
        assert result.initial_capital == 10000
        assert len(result.equity_curve) == 100

    def test_backtest_with_trades(self):
        dates = pd.date_range(start="2024-01-01", periods=200, freq="1h")
        prices = np.concatenate([
            np.linspace(100, 200, 100),
            np.linspace(200, 100, 100),
        ])
        data = pd.DataFrame({
            "close": prices,
            "open": prices * 0.99,
            "high": prices * 1.01,
            "low": prices * 0.98,
            "volume": [1000] * 200,
        }, index=dates)

        strategy = MACrossStrategy(fast_period=20, slow_period=50)
        engine = BacktestEngine(strategy, data, initial_capital=10000)
        result = engine.run()

        assert isinstance(result, BacktestResult)
        assert result.total_trades >= 0
        assert result.win_rate >= 0 and result.win_rate <= 100

    def test_slippage_application(self):
        dates = pd.date_range(start="2024-01-01", periods=100, freq="1h")
        data = pd.DataFrame({
            "close": np.linspace(100, 110, 100),
            "open": [100.0] * 100,
            "high": [111.0] * 100,
            "low": [99.0] * 100,
            "volume": [1000] * 100,
        }, index=dates)

        strategy = MACrossStrategy(fast_period=10, slow_period=30)
        engine = BacktestEngine(strategy, data, initial_capital=10000, slippage=0.001)

        assert engine.slippage == 0.001

        engine.run()
        assert engine.initial_capital == 10000


class TestExecutionSimulator:
    def test_market_order_slippage(self):
        sim = ExecutionSimulator(exchange_id="binance", latency_ms=50)

        levels = 20
        bid_depth = np.array([100 * np.exp(-0.1 * i) for i in range(levels)])
        ask_depth = np.array([100 * np.exp(-0.1 * i) for i in range(levels)])

        profile = LiquidityProfile(
            bid_depth=bid_depth,
            ask_depth=ask_depth,
            mid_price=50000,
            spread_bps=5.0,
            volume_24h=1_000_000,
        )

        from exchange.base import OrderSide
        result = sim.simulate_order(
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            price=50000,
            amount=1.0,
            liquidity_profile=profile,
        )

        assert isinstance(result, ExecutionResult)
        assert result.executed_price > 0
        assert result.slippage_bps >= 0
        assert result.latency_ms >= 0

    def test_limit_order_no_fill(self):
        sim = ExecutionSimulator(exchange_id="binance", fill_probability=0.0)

        from exchange.base import OrderSide
        result = sim.simulate_order(
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            price=50000,
            amount=1.0,
        )

        assert isinstance(result, ExecutionResult)
        if not result.success:
            assert result.executed_amount == 0


class TestRateLimiter:
    def test_rate_limiter_allows_within_limit(self):
        limiter = RateLimiter(calls=5, period=60)

        for _ in range(5):
            assert limiter.allow() is True

    def test_rate_limiter_blocks_over_limit(self):
        limiter = RateLimiter(calls=3, period=60)

        assert limiter.allow() is True
        assert limiter.allow() is True
        assert limiter.allow() is True
        assert limiter.allow() is False

    def test_rate_limiter_resets(self):
        limiter = RateLimiter(calls=2, period=0.1)

        assert limiter.allow() is True
        assert limiter.allow() is True
        assert limiter.allow() is False

        import time
        time.sleep(0.15)

        assert limiter.allow() is True


class TestCircuitBreaker:
    def test_circuit_closes_after_failures(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout_seconds=60)

        assert cb.can_execute() is True
        cb.record_failure()
        assert cb.can_execute() is True
        cb.record_failure()
        assert cb.can_execute() is True
        cb.record_failure()
        assert cb.state.value == "open"
        assert cb.can_execute() is False

    def test_circuit_half_open_after_timeout(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout_seconds=0)

        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

        cb.last_failure_time = datetime.now() - timedelta(seconds=61)
        can_exec = cb.can_execute()

        assert can_exec is True
        assert cb.state == CircuitState.HALF_OPEN

    def test_circuit_resets_on_success(self):
        cb = CircuitBreaker(failure_threshold=3)

        cb.record_failure()
        cb.record_failure()
        cb.record_success()

        assert cb.failure_count == 0
        assert cb.state == CircuitState.CLOSED


class TestEnhancedRiskManager:
    def test_risk_manager_rejects_no_equity(self):
        rm = EnhancedRiskManager()
        signal = Signal(signal_type=SignalType.BUY, symbol="BTC/USDT", price=50000, amount=1.0)

        result = rm.check_signal(signal, equity=0)

        assert result.approved is False
        assert "No equity" in result.reason

    def test_risk_manager_rejects_daily_loss_limit(self):
        rm = EnhancedRiskManager(config={"max_daily_loss_pct": 0.05})
        rm._daily_pnl = -1000
        rm._daily_start_equity = 10000

        signal = Signal(signal_type=SignalType.BUY, symbol="BTC/USDT", price=50000, amount=0.1)
        result = rm.check_signal(signal, equity=9000)

        assert result.approved is False
        assert "Daily loss limit" in result.reason

    def test_risk_manager_kelly_sizing(self):
        rm = EnhancedRiskManager(config={"kelly_fraction": 0.25})

        for i in range(10):
            rm._trade_outcomes.append({"pnl": 100, "pnl_pct": 0.02})

        kelly = rm.calculate_kelly_position("BTC/USDT", 50000)
        assert 0 <= kelly <= rm.max_position_size_pct

    def test_var_calculation(self):
        rm = EnhancedRiskManager()
        equity_values = [10000, 10100, 10200, 9900, 9800, 10000, 10300, 10200, 10100, 10000]

        for eq in equity_values:
            rm._equity_history.append(eq)

        var = rm.calculate_var()
        assert var >= 0


class TestVectorizedDataProcessor:
    def test_candles_to_dataframe(self):
        from exchange.base import OHLCV
        candles = [
            OHLCV(timestamp=datetime(2024, 1, 1, 0), open=100, high=105, low=99, close=104, volume=1000),
            OHLCV(timestamp=datetime(2024, 1, 1, 1), open=104, high=106, low=103, close=105, volume=1100),
            OHLCV(timestamp=datetime(2024, 1, 1, 2), open=105, high=107, low=104, close=106, volume=1200),
        ]

        df = VectorizedDataProcessor.candles_to_dataframe(candles)

        assert len(df) == 3
        assert "open" in df.columns
        assert "high" in df.columns
        assert "low" in df.columns
        assert "close" in df.columns
        assert "volume" in df.columns
        assert df.iloc[0]["close"] == 104

    def test_add_indicators(self):
        df = pd.DataFrame({
            "close": np.linspace(100, 200, 100),
            "open": np.linspace(99, 199, 100),
            "high": np.linspace(101, 201, 100),
            "low": np.linspace(98, 198, 100),
            "volume": [1000] * 100,
        })

        result = VectorizedDataProcessor.add_indicators(df)

        assert "ma_5" in result.columns
        assert "rsi" in result.columns
        assert "atr" in result.columns

    def test_calculate_returns(self):
        df = pd.DataFrame({
            "close": [100, 105, 102, 108, 107],
            "open": [100, 105, 102, 108, 107],
            "high": [100, 105, 102, 108, 107],
            "low": [100, 105, 102, 108, 107],
            "volume": [1000] * 5,
        })

        result = VectorizedDataProcessor.calculate_returns(df)

        assert "returns" in result.columns
        assert "cumulative_returns" in result.columns

    def test_detect_crossover(self):
        s1 = pd.Series([1, 2, 3, 4, 5])
        s2 = pd.Series([3, 3, 3, 3, 3])

        result = VectorizedDataProcessor.detect_crossover(s1, s2)

        assert "golden" in result.columns
        assert "death" in result.columns
        assert result["golden"].iloc[3] == True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
