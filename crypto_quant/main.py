import sys
import json
from pathlib import Path

import click
import pandas as pd
import numpy as np
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config.settings import settings
from exchange.base import MarketType
from exchange.ccxt_connector import ExchangeFactory
from strategy.ma_cross import MACrossStrategy
from strategy.rsi import RSIStrategy
from strategy.grid import GridStrategy
from data.manager import DataManager
from data.storage import DataStorage
from backtest.engine import BacktestEngine, print_backtest_result
from core.engine import TradingEngine
from utils.logger import logger

console = Console()

STRATEGY_MAP = {
    "ma_cross": MACrossStrategy,
    "rsi": RSIStrategy,
    "grid": GridStrategy,
}


def parse_params(params_list):
    params = {}
    if params_list:
        for p in params_list:
            if "=" in p:
                k, v = p.split("=", 1)
                try:
                    v = float(v) if "." in v else int(v)
                except ValueError:
                    pass
                params[k] = v
    return params


@click.group()
def cli():
    """CryptoQuant - 虚拟货币量化交易系统"""
    pass


@cli.command()
@click.option("--exchange", "-e", default="binance", help="交易所ID")
@click.option("--market-type", "-m", type=click.Choice(["spot", "swap"]), default="spot", help="市场类型")
def markets(exchange, market_type):
    """列出交易所支持的交易对"""
    mt = MarketType.SPOT if market_type == "spot" else MarketType.SWAP
    try:
        connector = ExchangeFactory.create(exchange, mt)
        symbols = connector.get_markets()

        table = Table(title=f"{exchange.upper()} - {market_type.upper()} Markets")
        table.add_column("Symbol", style="cyan")
        for s in sorted(symbols)[:50]:
            table.add_row(s)

        console.print(table)
        console.print(f"[green]Total: {len(symbols)} markets[/green]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@cli.command()
@click.option("--exchange", "-e", default="binance", help="交易所ID")
@click.option("--symbol", "-s", default="BTC/USDT", help="交易对")
@click.option("--market-type", "-m", type=click.Choice(["spot", "swap"]), default="spot")
def ticker(exchange, symbol, market_type):
    """获取实时行情"""
    mt = MarketType.SPOT if market_type == "spot" else MarketType.SWAP
    try:
        connector = ExchangeFactory.create(exchange, mt)
        t = connector.get_ticker(symbol)

        table = Table(title=f"{symbol} Ticker - {exchange.upper()}")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="green")
        for k, v in [
            ("Last", f"{t.last:.2f}"),
            ("Bid", f"{t.bid:.2f}"),
            ("Ask", f"{t.ask:.2f}"),
            ("High", f"{t.high:.2f}"),
            ("Low", f"{t.low:.2f}"),
            ("Volume", f"{t.volume:.4f}"),
            ("Time", str(t.timestamp)),
        ]:
            table.add_row(k, v)
        console.print(table)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@cli.command()
@click.option("--exchange", "-e", default="binance", help="交易所ID")
@click.option("--symbol", "-s", default="BTC/USDT", help="交易对")
@click.option("--timeframe", "-t", default="1h", help="K线周期")
@click.option("--limit", "-n", default=100, help="K线数量")
@click.option("--market-type", "-m", type=click.Choice(["spot", "swap"]), default="spot")
def fetch(exchange, symbol, timeframe, limit, market_type):
    """获取并存储历史K线数据"""
    mt = MarketType.SPOT if market_type == "spot" else MarketType.SWAP
    try:
        dm = DataManager()
        df = dm.fetch_and_store(exchange, symbol, timeframe, limit, mt)
        console.print(f"[green]Fetched {len(df)} candles for {exchange}/{symbol}/{timeframe}[/green]")
        if not df.empty:
            console.print(df.tail(10).to_string())
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@cli.command()
@click.option("--strategy", "-st", type=click.Choice(list(STRATEGY_MAP.keys())), default="ma_cross", help="策略")
@click.option("--exchange", "-e", default="binance", help="交易所ID")
@click.option("--symbol", "-s", default="BTC/USDT", help="交易对")
@click.option("--timeframe", "-t", default="1h", help="K线周期")
@click.option("--capital", "-c", default=10000, type=float, help="初始资金")
@click.option("--param", "-p", multiple=True, help="策略参数 (key=value)")
def backtest(strategy, exchange, symbol, timeframe, capital, param):
    """运行策略回测"""
    params = parse_params(param)
    params["symbol"] = symbol

    strategy_cls = STRATEGY_MAP[strategy]
    strat = strategy_cls(**params)

    console.print(Panel(f"[bold]Backtest Configuration[/bold]\n"
                        f"Strategy: {strat.name}\n"
                        f"Symbol: {symbol}\n"
                        f"Timeframe: {timeframe}\n"
                        f"Capital: ${capital:,.2f}\n"
                        f"Params: {params}"))

    try:
        dm = DataManager()
        df = dm.get_historical_data(exchange, symbol, timeframe)

        if df.empty:
            console.print("[yellow]No data available. Fetching from exchange...[/yellow]")
            df = dm.fetch_and_store(exchange, symbol, timeframe, limit=500)

        if df.empty:
            console.print("[red]No data available for backtesting[/red]")
            return

        engine = BacktestEngine(strat, df, initial_capital=capital)
        result = engine.run()
        print_backtest_result(result)

    except Exception as e:
        console.print(f"[red]Backtest error: {e}[/red]")
        logger.exception("Backtest failed")


@cli.command()
@click.option("--strategy", "-st", type=click.Choice(list(STRATEGY_MAP.keys())), default="ma_cross", help="策略")
@click.option("--exchange", "-e", default="binance", help="交易所ID")
@click.option("--symbol", "-s", default="BTC/USDT", help="交易对")
@click.option("--timeframe", "-t", default="1h", help="K线周期")
@click.option("--market-type", "-m", type=click.Choice(["spot", "swap"]), default="spot")
@click.option("--dry-run/--live", default=True, help="模拟盘/实盘")
@click.option("--param", "-p", multiple=True, help="策略参数 (key=value)")
def trade(strategy, exchange, symbol, timeframe, market_type, dry_run, param):
    """启动自动交易"""
    params = parse_params(param)
    mt = MarketType.SPOT if market_type == "spot" else MarketType.SWAP

    strategy_cls = STRATEGY_MAP[strategy]
    strat = strategy_cls(**params)

    mode = "DRY RUN (模拟盘)" if dry_run else "LIVE (实盘)"
    console.print(Panel(
        f"[bold]Trading Engine[/bold]\n"
        f"Strategy: {strat.name}\n"
        f"Exchange: {exchange}\n"
        f"Symbol: {symbol}\n"
        f"Timeframe: {timeframe}\n"
        f"Market: {market_type}\n"
        f"Mode: {mode}",
        style="green" if dry_run else "red",
    ))

    if not dry_run:
        console.print("[bold red]⚠️  实盘模式！请确保你已正确配置API密钥和风控参数！[/bold red]")
        if not click.confirm("确认启动实盘交易？"):
            return

    engine = TradingEngine(
        exchange_id=exchange,
        strategy=strat,
        symbol=symbol,
        timeframe=timeframe,
        market_type=mt,
        dry_run=dry_run,
    )

    try:
        engine.start()
    except KeyboardInterrupt:
        engine.stop()
        console.print("[yellow]Trading engine stopped by user[/yellow]")


@cli.command()
@click.option("--strategy", "-st", type=click.Choice(list(STRATEGY_MAP.keys())), default="ma_cross", help="策略")
@click.option("--exchange", "-e", default="binance", help="交易所ID")
@click.option("--symbol", "-s", default="BTC/USDT", help="交易对")
@click.option("--timeframe", "-t", default="1h", help="K线周期")
@click.option("--market-type", "-m", type=click.Choice(["spot", "swap"]), default="spot")
@click.option("--dry-run/--live", default=True)
@click.option("--param", "-p", multiple=True, help="策略参数 (key=value)")
def signal(strategy, exchange, symbol, timeframe, market_type, dry_run, param):
    """获取当前策略信号（单次执行）"""
    params = parse_params(param)
    params["symbol"] = symbol
    mt = MarketType.SPOT if market_type == "spot" else MarketType.SWAP

    strategy_cls = STRATEGY_MAP[strategy]
    strat = strategy_cls(**params)

    try:
        dm = DataManager()
        df = dm.get_latest_candles(exchange, symbol, timeframe, limit=200, market_type=mt)

        if df.empty:
            console.print("[red]No data available[/red]")
            return

        sig = strat.on_tick(df)

        table = Table(title=f"Strategy Signal: {strat.name}")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="green")
        table.add_row("Symbol", symbol)
        table.add_row("Signal", sig.signal_type.value)
        table.add_row("Price", f"{sig.price:.2f}")
        table.add_row("Reason", sig.reason or "-")
        table.add_row("Confidence", f"{sig.confidence:.2f}")
        if sig.stop_loss:
            table.add_row("Stop Loss", f"{sig.stop_loss:.2f}")
        if sig.take_profit:
            table.add_row("Take Profit", f"{sig.take_profit:.2f}")
        console.print(table)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@cli.command()
def status():
    """显示系统状态"""
    table = Table(title="System Status")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")

    table.add_row("Config", "✓ Loaded" if settings.exchanges else "✗ Not configured")
    table.add_row("Exchanges", ", ".join(settings.exchanges.keys()) or "None")
    table.add_row("Default Exchange", settings.trading.get("default_exchange", "N/A"))
    table.add_row("Default Symbol", settings.trading.get("default_symbol", "N/A"))
    table.add_row("Risk Max Position", f"{settings.risk.get('max_position_size_pct', 0):.0%}")
    table.add_row("Risk Stop Loss", f"{settings.risk.get('stop_loss_pct', 0):.1%}")
    table.add_row("Risk Max Drawdown", f"{settings.risk.get('max_drawdown_pct', 0):.1%}")
    table.add_row("Backtest Capital", f"${settings.backtest.get('initial_capital', 0):,.0f}")
    table.add_row("Notification", "Enabled" if settings.notification.get("enabled") else "Disabled")

    console.print(table)


if __name__ == "__main__":
    cli()
