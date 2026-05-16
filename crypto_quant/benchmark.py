import time
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from strategy.ma_cross import MACrossStrategy
from backtest.engine import BacktestEngine
from execution.simulator import ExecutionSimulator
from risk.enhanced_manager import EnhancedRiskManager
from data.processor import VectorizedDataProcessor
from strategy.base import Signal, SignalType
from exchange.base import OrderType, OrderSide


def benchmark_data_processor(n_bars: int = 1000) -> dict:
    data = pd.DataFrame({
        "open": np.random.uniform(100, 110, n_bars),
        "high": np.random.uniform(110, 120, n_bars),
        "low": np.random.uniform(90, 100, n_bars),
        "close": np.random.uniform(100, 110, n_bars),
        "volume": np.random.uniform(1000, 5000, n_bars),
    })

    start = time.perf_counter()
    result = VectorizedDataProcessor.add_indicators(data)
    elapsed = time.perf_counter() - start

    return {
        "operation": "add_indicators",
        "n_bars": n_bars,
        "elapsed_ms": elapsed * 1000,
        "bars_per_second": n_bars / elapsed
    }


def benchmark_backtest_engine(n_bars: int = 2000) -> dict:
    dates = pd.date_range(start="2024-01-01", periods=n_bars, freq="1h")
    data = pd.DataFrame({
        "close": np.cumsum(np.random.randn(n_bars) * 0.01 + 0.001) + 100,
        "open": np.random.uniform(100, 110, n_bars),
        "high": np.random.uniform(110, 120, n_bars),
        "low": np.random.uniform(90, 100, n_bars),
        "volume": np.random.uniform(1000, 5000, n_bars),
    }, index=dates)

    strategy = MACrossStrategy(fast_period=10, slow_period=30)
    engine = BacktestEngine(strategy, data, initial_capital=10000)

    start = time.perf_counter()
    result = engine.run()
    elapsed = time.perf_counter() - start

    return {
        "operation": "backtest_engine",
        "n_bars": n_bars,
        "n_trades": len(result.trades),
        "elapsed_ms": elapsed * 1000,
        "bars_per_second": n_bars / elapsed
    }


def benchmark_execution_simulator(n_orders: int = 1000) -> dict:
    simulator = ExecutionSimulator()

    start = time.perf_counter()
    for i in range(n_orders):
        price = 50000 + np.random.randn() * 100
        amount = 0.1 + np.random.rand() * 0.5
        side = OrderSide.BUY if i % 2 == 0 else OrderSide.SELL
        simulator.simulate_order(side, OrderType.MARKET, price, amount)
    elapsed = time.perf_counter() - start

    return {
        "operation": "execution_simulator",
        "n_orders": n_orders,
        "elapsed_ms": elapsed * 1000,
        "orders_per_second": n_orders / elapsed
    }


def benchmark_risk_manager(n_checks: int = 10000) -> dict:
    rm = EnhancedRiskManager()
    signals = [
        Signal(
            signal_type=SignalType.BUY if i % 2 == 0 else SignalType.SELL,
            symbol="BTC/USDT",
            price=50000 + np.random.randn() * 100,
            amount=0.1 + np.random.rand() * 0.5
        )
        for i in range(100)
    ]

    equity = 10000

    start = time.perf_counter()
    for i in range(n_checks):
        signal = signals[i % len(signals)]
        rm.check_signal(signal, equity)
    elapsed = time.perf_counter() - start

    return {
        "operation": "risk_manager_check",
        "n_checks": n_checks,
        "elapsed_ms": elapsed * 1000,
        "checks_per_second": n_checks / elapsed
    }


def benchmark_crossover_detection(n_points: int = 10000) -> dict:
    s1 = pd.Series(np.linspace(1, 100, n_points) + np.random.randn(n_points) * 10)
    s2 = pd.Series(np.linspace(50, 150, n_points) + np.random.randn(n_points) * 10)

    start = time.perf_counter()
    result = VectorizedDataProcessor.detect_crossover(s1, s2)
    elapsed = time.perf_counter() - start

    return {
        "operation": "crossover_detection",
        "n_points": n_points,
        "elapsed_ms": elapsed * 1000,
        "points_per_second": n_points / elapsed
    }


def main():
    print("=" * 70)
    print("Cryptocurrency Quantitative Trading Platform - Performance Benchmark")
    print("=" * 70)

    benchmarks = [
        ("Data Processor (1000 bars)", benchmark_data_processor(1000)),
        ("Backtest Engine (2000 bars)", benchmark_backtest_engine(2000)),
        ("Execution Simulator (1000 orders)", benchmark_execution_simulator(1000)),
        ("Risk Manager (10000 checks)", benchmark_risk_manager(10000)),
        ("Crossover Detection (10000 points)", benchmark_crossover_detection(10000)),
    ]

    print(f"\n{'Component':<35} {'Operation':<25} {'Time (ms)':<12} {'Rate':<20}")
    print("-" * 70)

    for name, result in benchmarks:
        if "n_bars" in result:
            rate = f"{result['bars_per_second']:.0f} bars/sec"
        elif "n_orders" in result:
            rate = f"{result['orders_per_second']:.0f} orders/sec"
        elif "n_checks" in result:
            rate = f"{result['checks_per_second']:.0f} checks/sec"
        elif "n_points" in result:
            rate = f"{result['points_per_second']:.0f} points/sec"
        else:
            rate = "N/A"

        print(f"{name:<35} {result['operation']:<25} {result['elapsed_ms']:<12.2f} {rate:<20}")

    print("-" * 70)
    print("\nBenchmark completed successfully!")


if __name__ == "__main__":
    main()