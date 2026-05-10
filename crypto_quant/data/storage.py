import os
import csv
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

import pandas as pd

from exchange.base import OHLCV, Ticker
from config.settings import settings
from config import DATA_DIR
from utils.logger import logger


class DataStorage:
    def __init__(self, storage_type: str = None, sqlite_path: str = None, csv_path: str = None):
        data_config = settings.data
        self.storage_type = storage_type or data_config.get("storage_type", "sqlite")
        self.sqlite_path = sqlite_path or data_config.get("sqlite_path", "data/trading.db")
        self.csv_path = csv_path or data_config.get("csv_path", "data/csv")

        if not Path(self.sqlite_path).is_absolute():
            self.sqlite_path = str(DATA_DIR.parent / self.sqlite_path)
        if not Path(self.csv_path).is_absolute():
            self.csv_path = str(DATA_DIR.parent / self.csv_path)

        Path(self.csv_path).mkdir(parents=True, exist_ok=True)
        Path(self.sqlite_path).parent.mkdir(parents=True, exist_ok=True)

        self._connection = None
        if self.storage_type == "sqlite":
            self._init_sqlite()

    def _get_connection(self) -> sqlite3.Connection:
        if self._connection is None:
            self._connection = sqlite3.connect(self.sqlite_path)
        return self._connection

    def _close_connection(self):
        if self._connection:
            self._connection.close()
            self._connection = None

    def _init_sqlite(self):
        conn = self._get_connection()
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS ohlcv (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exchange TEXT NOT NULL,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                UNIQUE(exchange, symbol, timeframe, timestamp)
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS tickers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exchange TEXT NOT NULL,
                symbol TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                last REAL,
                bid REAL,
                ask REAL,
                high REAL,
                low REAL,
                volume REAL
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exchange TEXT NOT NULL,
                symbol TEXT NOT NULL,
                order_id TEXT,
                side TEXT,
                price REAL,
                amount REAL,
                cost REAL,
                timestamp TEXT,
                strategy TEXT
            )
        """)
        conn.commit()

    def save_ohlcv(self, candles: list, exchange: str, symbol: str, timeframe: str):
        if not candles:
            return

        if self.storage_type == "sqlite":
            self._save_ohlcv_sqlite(candles, exchange, symbol, timeframe)
        else:
            self._save_ohlcv_csv(candles, exchange, symbol, timeframe)

    def _save_ohlcv_sqlite(self, candles: list, exchange: str, symbol: str, timeframe: str):
        conn = self._get_connection()
        c = conn.cursor()
        data = [
            (
                exchange, symbol, timeframe,
                candle.timestamp.isoformat(),
                candle.open, candle.high, candle.low, candle.close, candle.volume,
            )
            for candle in candles
        ]
        c.executemany("""
            INSERT OR REPLACE INTO ohlcv (exchange, symbol, timeframe, timestamp, open, high, low, close, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, data)
        conn.commit()
        logger.debug(f"Saved {len(candles)} candles to SQLite for {exchange}/{symbol}/{timeframe}")

    def _save_ohlcv_csv(self, candles: list, exchange: str, symbol: str, timeframe: str):
        filename = f"{exchange}_{symbol.replace('/', '_')}_{timeframe}.csv"
        filepath = Path(self.csv_path) / filename
        file_exists = filepath.exists()

        with open(filepath, "a", newline="") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["timestamp", "open", "high", "low", "close", "volume"])
            for candle in candles:
                writer.writerow([
                    candle.timestamp.isoformat(),
                    candle.open, candle.high, candle.low, candle.close, candle.volume,
                ])
        logger.debug(f"Saved {len(candles)} candles to CSV: {filepath}")

    def load_ohlcv(self, exchange: str, symbol: str, timeframe: str,
                   start: Optional[datetime] = None, end: Optional[datetime] = None) -> pd.DataFrame:
        if self.storage_type == "sqlite":
            return self._load_ohlcv_sqlite(exchange, symbol, timeframe, start, end)
        else:
            return self._load_ohlcv_csv(exchange, symbol, timeframe, start, end)

    def _load_ohlcv_sqlite(self, exchange: str, symbol: str, timeframe: str,
                           start: Optional[datetime], end: Optional[datetime]) -> pd.DataFrame:
        conn = self._get_connection()
        query = "SELECT timestamp, open, high, low, close, volume FROM ohlcv WHERE exchange=? AND symbol=? AND timeframe=?"
        params: List[Any] = [exchange, symbol, timeframe]

        if start:
            query += " AND timestamp >= ?"
            params.append(start.isoformat())
        if end:
            query += " AND timestamp <= ?"
            params.append(end.isoformat())

        query += " ORDER BY timestamp ASC"
        df = pd.read_sql_query(query, conn, params=params)

        if not df.empty:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df.set_index("timestamp", inplace=True)
        return df

    def _load_ohlcv_csv(self, exchange: str, symbol: str, timeframe: str,
                        start: Optional[datetime], end: Optional[datetime]) -> pd.DataFrame:
        filename = f"{exchange}_{symbol.replace('/', '_')}_{timeframe}.csv"
        filepath = Path(self.csv_path) / filename

        if not filepath.exists():
            return pd.DataFrame()

        df = pd.read_csv(filepath)
        if df.empty:
            return df

        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df.set_index("timestamp", inplace=True)

        if start:
            df = df[df.index >= start]
        if end:
            df = df[df.index <= end]
        return df

    def save_trade(self, exchange: str, symbol: str, order_id: str, side: str,
                   price: float, amount: float, cost: float, strategy: str = ""):
        if self.storage_type != "sqlite":
            return
        conn = self._get_connection()
        c = conn.cursor()
        c.execute("""
            INSERT INTO trades (exchange, symbol, order_id, side, price, amount, cost, timestamp, strategy)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (exchange, symbol, order_id, side, price, amount, cost, datetime.now().isoformat(), strategy))
        conn.commit()

    def __del__(self):
        self._close_connection()
