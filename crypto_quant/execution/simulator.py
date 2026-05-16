from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Callable
from enum import Enum
import numpy as np
import pandas as pd

from exchange.base import OrderSide, OrderType, OrderStatus


class FillModel(Enum):
    INSTANT = "instant"
    TAKER = "taker"
    MAKER = "maker"


@dataclass
class ExecutionResult:
    executed_price: float
    executed_amount: float
    slippage_bps: float
    commission: float
    market_impact: float
    latency_ms: float
    fill_time: datetime
    success: bool
    error: Optional[str] = None


@dataclass
class LiquidityProfile:
    bid_depth: np.ndarray
    ask_depth: np.ndarray
    mid_price: float
    spread_bps: float
    volume_24h: float


class ExecutionSimulator:
    """
    增强订单执行模拟器，参考 Hummingbot/Freqtrade 的订单簿模拟。

    Features:
    - Volume-weighted slippage based on order book depth
    - Taker/Maker fee modeling
    - Market impact estimation
    - Latency simulation
    - Fill probability modeling
    """

    TAKER_RATES = {"binance": 0.001, "okx": 0.0015, "bybit": 0.001, "default": 0.001}
    MAKER_RATES = {"binance": 0.0002, "okx": 0.0003, "bybit": 0.0002, "default": 0.0002}

    def __init__(
        self,
        exchange_id: str = "binance",
        latency_ms: float = 50.0,
        latency_std_ms: float = 20.0,
        market_impact_factor: float = 0.1,
        fill_probability: float = 0.95,
    ):
        self.exchange_id = exchange_id
        self.latency_ms = latency_ms
        self.latency_std_ms = latency_std_ms
        self.market_impact_factor = market_impact_factor
        self.fill_probability = fill_probability

    def simulate_order(
        self,
        side: OrderSide,
        order_type: OrderType,
        price: float,
        amount: float,
        liquidity_profile: Optional[LiquidityProfile] = None,
        timestamp: Optional[datetime] = None,
    ) -> ExecutionResult:
        """
        模拟订单执行，考虑：
        1. 滑点（基于订单簿深度和订单大小）
        2. 手续费（Taker/Maker）
        3. 市场冲击
        4. 延迟
        5. 成交概率
        """
        if timestamp is None:
            timestamp = datetime.now()

        if amount <= 0 or price <= 0:
            return ExecutionResult(
                executed_price=0,
                executed_amount=0,
                slippage_bps=0,
                commission=0,
                market_impact=0,
                latency_ms=0,
                fill_time=timestamp,
                success=False,
                error="Invalid order parameters",
            )

        if order_type == OrderType.LIMIT:
            return self._simulate_limit_order(side, price, amount, timestamp)
        else:
            return self._simulate_market_order(
                side, price, amount, liquidity_profile, timestamp
            )

    def _simulate_limit_order(
        self, side: OrderSide, price: float, amount: float, timestamp: datetime
    ) -> ExecutionResult:
        import random

        if random.random() > self.fill_probability * 0.8:
            return ExecutionResult(
                executed_price=price,
                executed_amount=0,
                slippage_bps=0,
                commission=0,
                market_impact=0,
                latency_ms=0,
                fill_time=timestamp,
                success=False,
                error="Limit order not filled (no liquidity)",
            )

        maker_rate = self.MAKER_RATES.get(self.exchange_id, self.MAKER_RATES["default"])
        commission = price * amount * maker_rate
        latency = max(0, np.random.normal(self.latency_ms * 1.5, self.latency_std_ms))

        return ExecutionResult(
            executed_price=price,
            executed_amount=amount,
            slippage_bps=0,
            commission=commission,
            market_impact=0,
            latency_ms=latency,
            fill_time=timestamp,
            success=True,
        )

    def _simulate_market_order(
        self,
        side: OrderSide,
        price: float,
        amount: float,
        profile: Optional[LiquidityProfile],
        timestamp: datetime,
    ) -> ExecutionResult:
        import random

        latency = max(0, np.random.normal(self.latency_ms, self.latency_std_ms))
        fill_time = timestamp

        if profile is None:
            profile = self._default_liquidity_profile(price)

        participation_rate = amount / (profile.volume_24h / 86400) if profile.volume_24h > 0 else 0.1
        participation_rate = min(participation_rate, 1.0)

        if side == OrderSide.BUY:
            depth = profile.ask_depth
            base_price = profile.mid_price * (1 + profile.spread_bps / 20000)
        else:
            depth = profile.bid_depth
            base_price = profile.mid_price * (1 - profile.spread_bps / 20000)

        slippage_bps = self._calculate_slippage(
            amount, depth, participation_rate
        )

        market_impact_bps = participation_rate * self.market_impact_factor * 50

        if side == OrderSide.BUY:
            executed_price = base_price * (1 + slippage_bps / 10000 + market_impact_bps / 10000)
        else:
            executed_price = base_price * (1 - slippage_bps / 10000 - market_impact_bps / 10000)

        taker_rate = self.TAKER_RATES.get(self.exchange_id, self.TAKER_RATES["default"])
        commission = executed_price * amount * taker_rate

        if random.random() > self.fill_probability:
            return ExecutionResult(
                executed_price=executed_price,
                executed_amount=amount * random.uniform(0.3, 0.9),
                slippage_bps=slippage_bps + market_impact_bps,
                commission=commission,
                market_impact=market_impact_bps,
                latency_ms=latency,
                fill_time=fill_time,
                success=False,
                error="Market order partial fill",
            )

        return ExecutionResult(
            executed_price=executed_price,
            executed_amount=amount,
            slippage_bps=slippage_bps + market_impact_bps,
            commission=commission,
            market_impact=market_impact_bps,
            latency_ms=latency,
            fill_time=fill_time,
            success=True,
        )

    def _calculate_slippage(self, amount: float, depth: np.ndarray, participation: float) -> float:
        """
        基于订单簿深度计算滑点（单位：bps）。
        深度数组 [0] = 最近价格档位，[n] = 第 n 档。
        """
        if len(depth) == 0 or amount <= 0:
            return 0.0

        cumulative_volume = np.cumsum(depth)
        notional = amount * 1000
        slippage = 0.0
        remaining = notional

        for i, vol in enumerate(depth):
            if remaining <= 0:
                break
            filled = min(remaining, vol)
            slippage += filled * (i + 1) * 0.1
            remaining -= filled

        base_slippage = slippage / notional * 10000 if notional > 0 else 0
        return min(base_slippage, 100)

    def _default_liquidity_profile(self, price: float) -> LiquidityProfile:
        levels = 20
        base_vol = 100.0
        bid_depth = np.array([base_vol * np.exp(-0.1 * i) for i in range(levels)])
        ask_depth = np.array([base_vol * np.exp(-0.1 * i) for i in range(levels)])
        spread_bps = 5.0
        return LiquidityProfile(
            bid_depth=bid_depth,
            ask_depth=ask_depth,
            mid_price=price,
            spread_bps=spread_bps,
            volume_24h=price * base_vol * 86400 / 1000,
        )

    @staticmethod
    def profile_from_orderbook(
        bids: list, asks: list, mid_price: float
    ) -> LiquidityProfile:
        """从交易所订单簿构建流动性画像"""
        bid_depth = np.array([float(b.get("quantity", 0)) for b in bids[:20]])
        ask_depth = np.array([float(a.get("quantity", 0)) for a in asks[:20]])
        best_bid = float(bids[0]["price"]) if bids else mid_price * 0.999
        best_ask = float(asks[0]["price"]) if asks else mid_price * 1.001
        spread_bps = abs(best_ask - best_bid) / mid_price * 10000
        return LiquidityProfile(
            bid_depth=bid_depth,
            ask_depth=ask_depth,
            mid_price=mid_price,
            spread_bps=spread_bps,
            volume_24h=0,
        )
