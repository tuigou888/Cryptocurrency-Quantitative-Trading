import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

from strategy.ma_cross import MACrossStrategy
from strategy.rsi import RSIStrategy
from strategy.grid import GridStrategy
from backtest.engine import BacktestEngine
from data.manager import DataManager
from config.settings import settings

STRATEGY_MAP = {
    "MA均线交叉": MACrossStrategy,
    "RSI超买超卖": RSIStrategy,
    "网格交易": GridStrategy,
}

st.set_page_config(
    page_title="CryptoQuant 量化交易仪表盘",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #1e1e2e 0%, #2d2d44 100%);
        border-radius: 12px;
        padding: 20px;
        border: 1px solid #3d3d5c;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    .metric-value {
        font-size: 28px;
        font-weight: 700;
    }
    .metric-label {
        font-size: 14px;
        color: #8888aa;
    }
    .positive { color: #00d4aa; }
    .negative { color: #ff4757; }
    .neutral { color: #ffa502; }
    div[data-testid="stSidebarNav"] { display: none; }
</style>
""", unsafe_allow_html=True)


def generate_sample_data(symbol="BTC/USDT", days=180):
    np.random.seed(42)
    periods = days * 24
    dates = pd.date_range(end=pd.Timestamp.now(), periods=periods, freq="1h")
    price = 40000
    prices = []
    for _ in range(periods):
        price *= (1 + np.random.normal(0.0001, 0.008))
        prices.append(price)

    df = pd.DataFrame({
        "open": [p * (1 + np.random.uniform(-0.002, 0.002)) for p in prices],
        "high": [p * (1 + abs(np.random.normal(0, 0.005))) for p in prices],
        "low": [p * (1 - abs(np.random.normal(0, 0.005))) for p in prices],
        "close": prices,
        "volume": [np.random.uniform(100, 2000) for _ in range(periods)],
    }, index=dates)
    return df


def run_backtest_with_data(strategy_name, df, capital=10000, **kwargs):
    strategy_cls = STRATEGY_MAP[strategy_name]
    strategy = strategy_cls(**kwargs)
    strategy.set_param("symbol", "BTC/USDT")
    engine = BacktestEngine(strategy, df, initial_capital=capital)
    return engine.run()


def metric_card(col, label, value, delta=None, is_pct=False):
    fmt = f"{value:+.2f}%" if is_pct else f"{value:,.2f}"
    delta_fmt = f"{delta:+.2f}%" if delta is not None and is_pct else (f"{delta:+,.2f}" if delta is not None else None)
    col.metric(label=label, value=fmt, delta=delta_fmt)


def sidebar_nav():
    with st.sidebar:
        st.markdown("## 📊 CryptoQuant")
        st.markdown("---")
        page = st.radio(
            "导航",
            ["🏠 概览", "📈 回测分析", "💰 交易分析", "⚠️ 风险分析", "🔄 实时交易"],
            label_visibility="collapsed",
        )
        st.markdown("---")
        st.markdown("### 全局配置")
        exchange = st.selectbox("交易所", list(settings.exchanges.keys()), index=0)
        symbol = st.text_input("交易对", value="BTC/USDT")
        timeframe = st.selectbox("时间周期", ["1m", "5m", "15m", "1h", "4h", "1d"], index=3)
        capital = st.number_input("初始资金 (USDT)", value=10000, min_value=100, step=1000)
        st.markdown("---")
        st.markdown(f"**交易所**: {exchange}")
        st.markdown(f"**交易对**: {symbol}")
        st.markdown(f"**周期**: {timeframe}")
        return page, exchange, symbol, timeframe, capital
