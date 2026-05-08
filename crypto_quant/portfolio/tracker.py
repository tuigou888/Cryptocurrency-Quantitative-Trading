from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from exchange.base import AccountInfo, Balance, Position, MarketType
from exchange.ccxt_connector import ExchangeFactory
from utils.logger import logger


@dataclass
class PortfolioSnapshot:
    timestamp: datetime
    total_equity: float
    available_balance: float
    positions: list = field(default_factory=list)
    unrealized_pnl: float = 0.0


class PortfolioTracker:
    def __init__(self, exchange_id: str, market_type: MarketType = MarketType.SPOT):
        self.exchange_id = exchange_id
        self.market_type = market_type
        self._connector = None
        self._snapshots = []
        self._positions = {}
        self._balances = {}

    @property
    def connector(self):
        if self._connector is None:
            self._connector = ExchangeFactory.create(self.exchange_id, self.market_type)
        return self._connector

    def update(self) -> PortfolioSnapshot:
        try:
            account = self.connector.get_balance()
            self._balances = {b.currency: b for b in account.balances}

            positions = []
            if self.market_type != MarketType.SPOT:
                raw_positions = self.connector.get_positions()
                for p in raw_positions:
                    if p.size > 0:
                        positions.append(p)
                        self._positions[p.symbol] = p

            snapshot = PortfolioSnapshot(
                timestamp=datetime.now(),
                total_equity=account.total_equity,
                available_balance=account.available_margin,
                positions=positions,
                unrealized_pnl=account.unrealized_pnl,
            )
            self._snapshots.append(snapshot)
            return snapshot

        except Exception as e:
            logger.error(f"Failed to update portfolio: {e}")
            return PortfolioSnapshot(timestamp=datetime.now(), total_equity=0, available_balance=0)

    def get_balance(self, currency: str = "USDT") -> Optional[Balance]:
        return self._balances.get(currency)

    def get_position(self, symbol: str) -> Optional[Position]:
        return self._positions.get(symbol)

    def get_total_equity(self) -> float:
        if self._snapshots:
            return self._snapshots[-1].total_equity
        return 0.0

    def get_available_balance(self) -> float:
        if self._snapshots:
            return self._snapshots[-1].available_balance
        return 0.0

    def get_performance_summary(self) -> dict:
        if len(self._snapshots) < 2:
            return {"total_return": 0, "total_return_pct": 0}

        initial = self._snapshots[0].total_equity
        current = self._snapshots[-1].total_equity
        total_return = current - initial
        total_return_pct = (total_return / initial * 100) if initial > 0 else 0

        peak = max(s.total_equity for s in self._snapshots)
        max_drawdown = peak - min(s.total_equity for s in self._snapshots)
        max_drawdown_pct = (max_drawdown / peak * 100) if peak > 0 else 0

        return {
            "initial_equity": initial,
            "current_equity": current,
            "total_return": total_return,
            "total_return_pct": total_return_pct,
            "max_drawdown": max_drawdown,
            "max_drawdown_pct": max_drawdown_pct,
            "snapshots_count": len(self._snapshots),
        }

    def get_snapshot_history(self, limit: int = 100) -> list:
        return self._snapshots[-limit:]
