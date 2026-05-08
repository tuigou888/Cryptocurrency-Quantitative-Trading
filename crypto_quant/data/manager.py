from datetime import datetime
from typing import Optional

import pandas as pd

from exchange.base import OHLCV, MarketType
from exchange.ccxt_connector import ExchangeFactory
from data.storage import DataStorage
from utils.logger import logger


class DataManager:
    def __init__(self, storage: DataStorage = None):
        self.storage = storage or DataStorage()

    def fetch_and_store(self, exchange_id: str, symbol: str, timeframe: str = "1h",
                        limit: int = 500, market_type: MarketType = MarketType.SPOT) -> pd.DataFrame:
        connector = ExchangeFactory.create(exchange_id, market_type)
        candles = connector.get_ohlcv(symbol, timeframe, limit)

        if candles:
            self.storage.save_ohlcv(candles, exchange_id, symbol, timeframe)
            logger.info(f"Fetched and stored {len(candles)} candles: {exchange_id}/{symbol}/{timeframe}")

        return self._candles_to_dataframe(candles)

    def get_historical_data(self, exchange_id: str, symbol: str, timeframe: str = "1h",
                            start: Optional[datetime] = None, end: Optional[datetime] = None,
                            market_type: MarketType = MarketType.SPOT) -> pd.DataFrame:
        df = self.storage.load_ohlcv(exchange_id, symbol, timeframe, start, end)

        if df.empty:
            logger.info(f"No cached data found, fetching from exchange...")
            df = self.fetch_and_store(exchange_id, symbol, timeframe, market_type=market_type)

        return df

    def get_latest_candles(self, exchange_id: str, symbol: str, timeframe: str = "1h",
                           limit: int = 100, market_type: MarketType = MarketType.SPOT) -> pd.DataFrame:
        connector = ExchangeFactory.create(exchange_id, market_type)
        candles = connector.get_ohlcv(symbol, timeframe, limit)
        return self._candles_to_dataframe(candles)

    @staticmethod
    def _candles_to_dataframe(candles: list) -> pd.DataFrame:
        if not candles:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

        data = {
            "open": [c.open for c in candles],
            "high": [c.high for c in candles],
            "low": [c.low for c in candles],
            "close": [c.close for c in candles],
            "volume": [c.volume for c in candles],
        }
        index = [c.timestamp for c in candles]
        df = pd.DataFrame(data, index=index)
        df.index.name = "timestamp"
        return df
