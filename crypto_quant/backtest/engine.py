from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import pandas as pd
import numpy as np

from strategy.base import BaseStrategy, Signal, SignalType
from config.settings import settings
from utils.logger import logger


@dataclass
class BacktestTrade:
    entry_time: datetime
    exit_time: Optional[datetime]
    symbol: str
    side: str
    entry_price: float
    exit_price: float = 0.0
    amount: float = 0.0
    pnl: float = 0.0
    pnl_pct: float = 0.0
    commission: float = 0.0


@dataclass
class BacktestResult:
    strategy_name: str
    symbol: str
    timeframe: str
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_capital: float
    total_return: float
    total_return_pct: float
    max_drawdown: float
    max_drawdown_pct: float
    sharpe_ratio: float
    win_rate: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_profit: float
    avg_loss: float
    profit_factor: float
    trades: list = field(default_factory=list)
    equity_curve: list = field(default_factory=list)


class BacktestEngine:
    def __init__(self, strategy: BaseStrategy, data: pd.DataFrame,
                 initial_capital: float = None, commission: float = None,
                 slippage: float = None, position_size_pct: float = 0.95):
        self.strategy = strategy
        self.data = data.copy()
        bt_config = settings.backtest
        self.initial_capital = initial_capital or bt_config.get("initial_capital", 10000)
        self.commission = commission if commission is not None else bt_config.get("commission", 0.001)
        self.slippage = slippage if slippage is not None else bt_config.get("slippage", 0.0005)
        self.position_size_pct = position_size_pct

        self.capital = self.initial_capital
        self.position = 0.0
        self.entry_price = 0.0
        self.entry_time = None
        self.trades = []
        self.equity_curve = []
        self.peak_equity = self.initial_capital
        self.max_drawdown = 0.0

    def run(self) -> BacktestResult:
        logger.info(f"Starting backtest: {self.strategy.name} | {len(self.data)} bars")
        self.strategy.reset()

        for i in range(len(self.data)):
            window = self.data.iloc[:i + 1].copy()
            current_price = self.data["close"].iloc[i]
            current_time = self.data.index[i]

            signal = self.strategy.on_tick(window)

            if signal and signal.signal_type != SignalType.HOLD:
                self._process_signal(signal, current_price, current_time)

            equity = self._calculate_equity(current_price)
            self.equity_curve.append({
                "timestamp": current_time,
                "equity": equity,
                "capital": self.capital,
                "position": self.position,
                "price": current_price,
            })

            if equity > self.peak_equity:
                self.peak_equity = equity
            drawdown = self.peak_equity - equity
            if drawdown > self.max_drawdown:
                self.max_drawdown = drawdown

        if self.position > 0:
            last_price = self.data["close"].iloc[-1]
            last_time = self.data.index[-1]
            self._close_position(last_price, last_time)

        return self._generate_result()

    def _process_signal(self, signal: Signal, price: float, timestamp: datetime):
        if signal.signal_type == SignalType.BUY and self.position == 0:
            buy_price = price * (1 + self.slippage)
            amount = (self.capital * self.position_size_pct) / buy_price
            commission_cost = self.capital * self.position_size_pct * self.commission

            self.position = amount
            self.entry_price = buy_price
            self.entry_time = timestamp
            self.capital -= (amount * buy_price + commission_cost)

        elif signal.signal_type == SignalType.SELL and self.position > 0:
            sell_price = price * (1 - self.slippage)
            self._close_position(sell_price, timestamp)

    def _close_position(self, price: float, timestamp: datetime):
        if self.position <= 0:
            return

        sell_value = self.position * price
        commission_cost = sell_value * self.commission
        buy_value = self.position * self.entry_price

        pnl = sell_value - buy_value - commission_cost
        pnl_pct = pnl / buy_value if buy_value > 0 else 0

        trade = BacktestTrade(
            entry_time=self.entry_time,
            exit_time=timestamp,
            symbol=self.strategy.params.get("symbol", ""),
            side="long",
            entry_price=self.entry_price,
            exit_price=price,
            amount=self.position,
            pnl=pnl,
            pnl_pct=pnl_pct,
            commission=commission_cost,
        )
        self.trades.append(trade)

        self.capital += sell_value - commission_cost
        self.position = 0.0
        self.entry_price = 0.0
        self.entry_time = None

    def _calculate_equity(self, current_price: float) -> float:
        return self.capital + self.position * current_price

    def _generate_result(self) -> BacktestResult:
        final_equity = self.equity_curve[-1]["equity"] if self.equity_curve else self.initial_capital
        total_return = final_equity - self.initial_capital
        total_return_pct = (total_return / self.initial_capital) * 100 if self.initial_capital > 0 else 0

        max_dd_pct = (self.max_drawdown / self.peak_equity) * 100 if self.peak_equity > 0 else 0

        winning = [t for t in self.trades if t.pnl > 0]
        losing = [t for t in self.trades if t.pnl <= 0]
        win_rate = (len(winning) / len(self.trades) * 100) if self.trades else 0

        avg_profit = np.mean([t.pnl for t in winning]) if winning else 0
        avg_loss = np.mean([t.pnl for t in losing]) if losing else 0

        gross_profit = sum(t.pnl for t in winning)
        gross_loss = abs(sum(t.pnl for t in losing))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        sharpe = self._calculate_sharpe()

        return BacktestResult(
            strategy_name=self.strategy.name,
            symbol=self.strategy.params.get("symbol", ""),
            timeframe=self.strategy.params.get("timeframe", ""),
            start_date=self.data.index[0] if not self.data.empty else None,
            end_date=self.data.index[-1] if not self.data.empty else None,
            initial_capital=self.initial_capital,
            final_capital=final_equity,
            total_return=total_return,
            total_return_pct=total_return_pct,
            max_drawdown=self.max_drawdown,
            max_drawdown_pct=max_dd_pct,
            sharpe_ratio=sharpe,
            win_rate=win_rate,
            total_trades=len(self.trades),
            winning_trades=len(winning),
            losing_trades=len(losing),
            avg_profit=avg_profit,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            trades=self.trades,
            equity_curve=self.equity_curve,
        )

    def _calculate_sharpe(self, risk_free_rate: float = 0.02) -> float:
        if len(self.equity_curve) < 2:
            return 0.0

        equities = pd.Series([e["equity"] for e in self.equity_curve])
        returns = equities.pct_change().dropna()

        if returns.empty or returns.std() == 0:
            return 0.0

        periods_per_year = 365 * 24
        if len(returns) > 1:
            time_delta = (self.equity_curve[-1]["timestamp"] - self.equity_curve[0]["timestamp"])
            total_hours = time_delta.total_seconds() / 3600
            if total_hours > 0 and len(returns) > 1:
                periods_per_year = len(returns) / (total_hours / 8766)

        excess_return = returns.mean() - risk_free_rate / periods_per_year
        sharpe = excess_return / returns.std() * np.sqrt(periods_per_year)
        return sharpe


def print_backtest_result(result: BacktestResult):
    from rich.console import Console
    from rich.table import Table

    console = Console()

    table = Table(title=f"Backtest Result: {result.strategy_name}")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    metrics = [
        ("Symbol", result.symbol),
        ("Period", f"{result.start_date} ~ {result.end_date}"),
        ("Initial Capital", f"${result.initial_capital:,.2f}"),
        ("Final Capital", f"${result.final_capital:,.2f}"),
        ("Total Return", f"${result.total_return:,.2f}"),
        ("Return %", f"{result.total_return_pct:.2f}%"),
        ("Max Drawdown", f"${result.max_drawdown:,.2f}"),
        ("Max Drawdown %", f"{result.max_drawdown_pct:.2f}%"),
        ("Sharpe Ratio", f"{result.sharpe_ratio:.2f}"),
        ("Win Rate", f"{result.win_rate:.1f}%"),
        ("Total Trades", str(result.total_trades)),
        ("Winning Trades", str(result.winning_trades)),
        ("Losing Trades", str(result.losing_trades)),
        ("Avg Profit", f"${result.avg_profit:,.2f}"),
        ("Avg Loss", f"${result.avg_loss:,.2f}"),
        ("Profit Factor", f"{result.profit_factor:.2f}"),
    ]

    for name, value in metrics:
        style = "red" if "Loss" in name or "Drawdown" in name else "green"
        if "Return %" in name and result.total_return_pct < 0:
            style = "red"
        table.add_row(name, f"[{style}]{value}[/{style}]")

    console.print(table)
