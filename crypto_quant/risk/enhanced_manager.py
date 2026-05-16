from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from collections import deque
from enum import Enum
import numpy as np

from strategy.base import Signal, SignalType
from utils.logger import logger
from utils.rate_limiter import RateLimiter


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    failure_threshold: int = 5
    recovery_timeout_seconds: int = 60
    half_open_max_calls: int = 3
    state: CircuitState = field(default=CircuitState.CLOSED)
    failure_count: int = field(default=0)
    last_failure_time: Optional[datetime] = field(default=None)
    half_open_calls: int = field(default=0)

    def record_success(self):
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        self.half_open_calls = 0

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker OPENED after {self.failure_count} failures")

    def can_execute(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            if self.last_failure_time:
                elapsed = (datetime.now() - self.last_failure_time).total_seconds()
                if elapsed >= self.recovery_timeout_seconds:
                    self.state = CircuitState.HALF_OPEN
                    self.half_open_calls = 0
                    logger.info("Circuit breaker HALF_OPEN (recovery timeout reached)")
                    return True
            return False
        if self.state == CircuitState.HALF_OPEN:
            if self.half_open_calls < self.half_open_max_calls:
                self.half_open_calls += 1
                return True
            return False
        return False


@dataclass
class RiskCheckResult:
    approved: bool
    risk_level: str = "low"
    adjusted_amount: Optional[float] = None
    reason: Optional[str] = None


class EnhancedRiskManager:
    """
    增强型风险管理器，参考 Freqtrade/Hummingbot 的风控设计。

    新增功能:
    - 熔断器（Circuit Breaker）：连续失败后暂停交易
    - Kelly Criterion 动态仓位
    - 追踪止损（Trailing Stop）
    - 时间加权风险敞口（TWaR）
    - 滚动窗口VaR
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        if config is None:
            config = {}
        self.max_position_size_pct = config.get("max_position_size_pct", 0.95)
        self.max_total_exposure_pct = config.get("max_total_exposure_pct", 1.0)
        self.stop_loss_pct = config.get("stop_loss_pct", 0.02)
        self.take_profit_pct = config.get("take_profit_pct", 0.06)
        self.max_drawdown_pct = config.get("max_drawdown_pct", 0.20)
        self.max_daily_loss_pct = config.get("max_daily_loss_pct", 0.05)
        self.max_open_orders = config.get("max_open_orders", 5)
        self.kelly_fraction = config.get("kelly_fraction", 0.25)
        self.trailing_stop_pct = config.get("trailing_stop_pct", 0.015)
        self.var_confidence = config.get("var_confidence", 0.95)
        self.var_window = config.get("var_window", 100)

        self._current_equity = 0.0
        self._peak_equity = 0.0
        self._daily_pnl = 0.0
        self._daily_start_equity = 0.0
        self._daily_reset_time = datetime.now()
        self._open_orders_count = 0
        self._total_exposure = 0.0

        self._entry_prices: Dict[str, float] = {}
        self._stop_prices: Dict[str, float] = {}
        self._trail_prices: Dict[str, float] = {}

        self._equity_history = deque(maxlen=self.var_window)
        self._pnl_history = deque(maxlen=100)
        self._trade_outcomes = deque(maxlen=200)

        self._circuit_breaker = CircuitBreaker()
        self._rate_limiter = RateLimiter(calls=10, period=60)

    def update_equity(self, equity: float):
        self._current_equity = equity
        self._equity_history.append(equity)
        if equity > self._peak_equity:
            self._peak_equity = equity

        now = datetime.now()
        if now.date() != self._daily_reset_time.date():
            self._daily_pnl = 0.0
            self._daily_start_equity = equity
            self._daily_reset_time = now

    def update_pnl(self, pnl: float):
        self._daily_pnl += pnl
        self._pnl_history.append(pnl)

    def record_trade_outcome(self, pnl: float, pnl_pct: float):
        self._trade_outcomes.append({"pnl": pnl, "pnl_pct": pnl_pct})

    def update_entry_price(self, symbol: str, price: float, side: str = "long"):
        self._entry_prices[symbol] = price
        self._update_trailing_stop(symbol, price, side)

    def _update_trailing_stop(self, symbol: str, price: float, side: str):
        if side == "long":
            self._trail_prices[symbol] = price * (1 - self.trailing_stop_pct)
        else:
            self._trail_prices[symbol] = price * (1 + self.trailing_stop_pct)

    def update_trailing_stop(self, symbol: str, current_price: float, side: str):
        if symbol not in self._entry_prices:
            return

        if side == "long":
            new_trail = current_price * (1 - self.trailing_stop_pct)
            if new_trail > self._trail_prices.get(symbol, 0):
                self._trail_prices[symbol] = new_trail
        else:
            new_trail = current_price * (1 + self.trailing_stop_pct)
            if new_trail < self._trail_prices.get(symbol, float("inf")):
                self._trail_prices[symbol] = new_trail

    def check_trailing_stop(self, symbol: str, current_price: float, side: str) -> bool:
        if symbol not in self._trail_prices:
            return False
        trail = self._trail_prices[symbol]
        if side == "long":
            return current_price <= trail
        else:
            return current_price >= trail

    def calculate_var(self) -> float:
        if len(self._equity_history) < 2:
            return 0.0
        returns = np.diff(list(self._equity_history)) / np.array(list(self._equity_history))[:-1]
        if len(returns) == 0:
            return 0.0
        sorted_returns = np.sort(returns)
        index = int((1 - self.var_confidence) * len(sorted_returns))
        var = abs(sorted_returns[index]) if index < len(sorted_returns) else 0.0
        return var

    def calculate_kelly_position(self, symbol: str, price: float) -> float:
        outcomes = [t for t in self._trade_outcomes if t.get("symbol") == symbol]
        if len(outcomes) < 5:
            return self.max_position_size_pct

        wins = [t["pnl_pct"] for t in outcomes if t["pnl"] > 0]
        losses = [abs(t["pnl_pct"]) for t in outcomes if t["pnl"] <= 0]

        if not wins or not losses:
            return self.max_position_size_pct

        win_rate = len(wins) / len(outcomes)
        avg_win = np.mean(wins)
        avg_loss = np.mean(losses)

        if avg_loss == 0:
            return self.max_position_size_pct

        b = avg_win / avg_loss
        kelly = (b * win_rate - (1 - win_rate)) / b
        kelly = max(0, min(kelly, self.max_position_size_pct))
        return kelly * self.kelly_fraction

    def check_signal(self, signal: Signal, equity: float) -> RiskCheckResult:
        if signal.signal_type == SignalType.HOLD:
            return RiskCheckResult(approved=True, reason="Hold signal, no action needed")

        if not self._circuit_breaker.can_execute():
            return RiskCheckResult(
                approved=False,
                reason=f"Circuit breaker {self._circuit_breaker.state.value} - trading paused",
                risk_level="critical",
            )

        if not self._rate_limiter.allow():
            return RiskCheckResult(
                approved=False,
                reason="Rate limit exceeded",
                risk_level="high",
            )

        self.update_equity(equity)

        if equity <= 0:
            self._circuit_breaker.record_failure()
            return RiskCheckResult(approved=False, reason="No equity available", risk_level="critical")

        daily_loss_limit = self._daily_start_equity * self.max_daily_loss_pct
        if self._daily_pnl < -daily_loss_limit:
            self._circuit_breaker.record_failure()
            return RiskCheckResult(
                approved=False,
                reason=f"Daily loss limit reached: {self._daily_pnl:.2f} < -{daily_loss_limit:.2f}",
                risk_level="critical",
            )

        if self._peak_equity > 0:
            drawdown = (self._peak_equity - self._current_equity) / self._peak_equity
            if drawdown > self.max_drawdown_pct:
                self._circuit_breaker.record_failure()
                return RiskCheckResult(
                    approved=False,
                    reason=f"Max drawdown exceeded: {drawdown:.2%} > {self.max_drawdown_pct:.2%}",
                    risk_level="critical",
                )

        if self._open_orders_count >= self.max_open_orders:
            return RiskCheckResult(
                approved=False,
                reason=f"Max open orders reached: {self._open_orders_count}/{self.max_open_orders}",
                risk_level="high",
            )

        if signal.signal_type in (SignalType.BUY, SignalType.SELL):
            position_value = (signal.amount or 0) * signal.price
            kelly_size = self.calculate_kelly_position(signal.symbol, signal.price)
            position_pct = position_value / equity if equity > 0 else 1

            max_size = min(self.max_position_size_pct, kelly_size)
            if position_pct > max_size:
                adjusted_amount = (equity * max_size) / signal.price
                logger.warning(
                    f"Position size adjusted: {signal.amount} -> {adjusted_amount:.6f} "
                    f"(Kelly: {kelly_size:.2%}, max: {self.max_position_size_pct:.0%})"
                )
                signal.amount = adjusted_amount

            total_exposure_pct = (self._total_exposure + position_value) / equity if equity > 0 else 1
            if total_exposure_pct > self.max_total_exposure_pct:
                return RiskCheckResult(
                    approved=False,
                    reason=f"Total exposure would exceed limit: {total_exposure_pct:.2%} > {self.max_total_exposure_pct:.2%}",
                    risk_level="high",
                )

        if signal.stop_loss is None and signal.signal_type == SignalType.BUY:
            signal.stop_loss = signal.price * (1 - self.stop_loss_pct)
        if signal.take_profit is None and signal.signal_type == SignalType.BUY:
            signal.take_profit = signal.price * (1 + self.take_profit_pct)

        risk_level = "low"
        if self._daily_pnl < 0:
            risk_level = "medium"
        if self._peak_equity > 0:
            drawdown = (self._peak_equity - self._current_equity) / self._peak_equity
            if drawdown > self.max_drawdown_pct * 0.5:
                risk_level = "high"

        self._circuit_breaker.record_success()
        return RiskCheckResult(
            approved=True,
            reason="Signal approved",
            adjusted_amount=signal.amount,
            risk_level=risk_level,
        )

    def check_stop_loss(self, entry_price: float, current_price: float, side: str) -> bool:
        if side == "long":
            loss_pct = (entry_price - current_price) / entry_price
            return loss_pct >= self.stop_loss_pct
        elif side == "short":
            loss_pct = (current_price - entry_price) / entry_price
            return loss_pct >= self.stop_loss_pct
        return False

    def check_take_profit(self, entry_price: float, current_price: float, side: str) -> bool:
        if side == "long":
            profit_pct = (current_price - entry_price) / entry_price
            return profit_pct >= self.take_profit_pct
        elif side == "short":
            profit_pct = (entry_price - current_price) / entry_price
            return profit_pct >= self.take_profit_pct
        return False

    def get_status(self) -> dict:
        var = self.calculate_var()
        return {
            "current_equity": self._current_equity,
            "peak_equity": self._peak_equity,
            "daily_pnl": self._daily_pnl,
            "open_orders": self._open_orders_count,
            "total_exposure": self._total_exposure,
            "drawdown": (self._peak_equity - self._current_equity) / self._peak_equity if self._peak_equity > 0 else 0,
            "var_95": var,
            "circuit_breaker": self._circuit_breaker.state.value,
            "trade_outcomes_count": len(self._trade_outcomes),
        }
