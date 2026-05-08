from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from strategy.base import Signal, SignalType
from exchange.base import OrderSide
from config.settings import settings
from utils.logger import logger


@dataclass
class RiskCheckResult:
    approved: bool
    reason: str = ""
    adjusted_amount: Optional[float] = None
    risk_level: str = "low"


class RiskManager:
    def __init__(self):
        risk_config = settings.risk
        self.max_position_size_pct = risk_config.get("max_position_size_pct", 0.1)
        self.max_total_exposure_pct = risk_config.get("max_total_exposure_pct", 0.5)
        self.stop_loss_pct = risk_config.get("stop_loss_pct", 0.05)
        self.take_profit_pct = risk_config.get("take_profit_pct", 0.1)
        self.max_drawdown_pct = risk_config.get("max_drawdown_pct", 0.2)
        self.max_daily_loss_pct = risk_config.get("max_daily_loss_pct", 0.03)
        self.max_open_orders = risk_config.get("max_open_orders", 10)

        self._daily_pnl = 0.0
        self._daily_start_equity = 0.0
        self._daily_reset_time = datetime.now()
        self._open_orders_count = 0
        self._total_exposure = 0.0
        self._peak_equity = 0.0
        self._current_equity = 0.0

    def update_equity(self, equity: float):
        self._current_equity = equity
        if equity > self._peak_equity:
            self._peak_equity = equity

        now = datetime.now()
        if now.date() != self._daily_reset_time.date():
            self._daily_pnl = 0.0
            self._daily_start_equity = equity
            self._daily_reset_time = now

    def update_pnl(self, pnl: float):
        self._daily_pnl += pnl

    def update_open_orders(self, count: int):
        self._open_orders_count = count

    def update_exposure(self, exposure: float):
        self._total_exposure = exposure

    def check_signal(self, signal: Signal, equity: float) -> RiskCheckResult:
        if signal.signal_type == SignalType.HOLD:
            return RiskCheckResult(approved=True, reason="Hold signal, no action needed")

        self.update_equity(equity)

        if equity <= 0:
            return RiskCheckResult(approved=False, reason="No equity available", risk_level="critical")

        daily_loss_limit = self._daily_start_equity * self.max_daily_loss_pct
        if self._daily_pnl < -daily_loss_limit:
            return RiskCheckResult(
                approved=False,
                reason=f"Daily loss limit reached: {self._daily_pnl:.2f} < -{daily_loss_limit:.2f}",
                risk_level="critical",
            )

        if self._peak_equity > 0:
            drawdown = (self._peak_equity - self._current_equity) / self._peak_equity
            if drawdown > self.max_drawdown_pct:
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
            position_pct = position_value / equity if equity > 0 else 1

            if position_pct > self.max_position_size_pct:
                adjusted_amount = (equity * self.max_position_size_pct) / signal.price
                logger.warning(
                    f"Position size adjusted: {signal.amount} -> {adjusted_amount:.6f} "
                    f"(max {self.max_position_size_pct:.0%} of equity)"
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
        drawdown = (self._peak_equity - self._current_equity) / self._peak_equity if self._peak_equity > 0 else 0
        if drawdown > self.max_drawdown_pct * 0.5:
            risk_level = "high"

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
        return {
            "current_equity": self._current_equity,
            "peak_equity": self._peak_equity,
            "daily_pnl": self._daily_pnl,
            "open_orders": self._open_orders_count,
            "total_exposure": self._total_exposure,
            "drawdown": (self._peak_equity - self._current_equity) / self._peak_equity if self._peak_equity > 0 else 0,
        }
