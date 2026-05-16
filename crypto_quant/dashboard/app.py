import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
import logging
import numpy as np
import pandas as pd
import plotly
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from flask import Flask, render_template_string, jsonify, request

logger = logging.getLogger(__name__)

from strategy.ma_cross import MACrossStrategy
from strategy.rsi import RSIStrategy
from strategy.grid import GridStrategy
from backtest.engine import BacktestEngine
from config.settings import settings
from exchange.config_manager import (
    list_exchange_configs, get_exchange_config, save_exchange_config,
    delete_exchange_config, test_exchange_connection, get_exchange_instance,
    get_supported_exchanges,
)

from dashboard.common import run_backtest, fetch_real_market_data, generate_sample_data, STRATEGY_MAP

app = Flask(__name__)

from dashboard.chart_api import chart_bp
app.register_blueprint(chart_bp)

PLOTLY_CONFIG = {"displayModeBar": True, "displaylogo": False, "responsive": True}
DARK_LAYOUT = dict(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#e2e8f0", family="Inter, sans-serif"))
DARK_MARGIN = dict(l=60, r=20, t=40, b=40)

_CACHE = {}
_CACHE_TTL = 300


def get_cached(key, builder, *args, **kwargs):
    import time
    now = time.time()
    if key in _CACHE and now - _CACHE[key]["ts"] < _CACHE_TTL:
        return _CACHE[key]["data"]
    data = builder(*args, **kwargs)
    _CACHE[key] = {"data": data, "ts": now}
    return data


def fig_to_json(fig):
    return json.loads(plotly.io.to_json(fig))


def color_pct(val):
    if val >= 0:
        return "#00d4aa"
    return "#ff4757"


def build_overview_data():
    result, df = run_backtest("ma_cross", 60, 10000)

    eq_df = pd.DataFrame(result.equity_curve)
    fig_eq = go.Figure()
    fig_eq.add_trace(go.Scatter(x=eq_df["timestamp"], y=eq_df["equity"], name="权益",
                                line=dict(color="#00d4aa", width=2),
                                fill="tozeroy", fillcolor="rgba(0,212,170,0.08)"))
    fig_eq.add_hline(y=10000, line_dash="dash", line_color="#ffa502", annotation_text="初始资金")
    fig_eq.update_layout(**DARK_LAYOUT, height=380, xaxis_title="时间", yaxis_title="权益 (USDT)", margin=DARK_MARGIN)

    sample = df.iloc[::6]
    fig_kline = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
    fig_kline.add_trace(go.Candlestick(x=sample.index, open=sample["open"], high=sample["high"],
                                       low=sample["low"], close=sample["close"], name="K线",
                                       increasing_line_color="#00d4aa", decreasing_line_color="#ff4757"), row=1, col=1)
    fig_kline.add_trace(go.Bar(x=sample.index, y=sample["volume"], name="成交量", marker_color="#4a4a6a"), row=2, col=1)
    fig_kline.update_layout(**DARK_LAYOUT, height=380, xaxis_rangeslider_visible=False, margin=DARK_MARGIN)

    monthly_data = []
    if not eq_df.empty and len(eq_df) > 24:
        eq_df["month"] = pd.to_datetime(eq_df["timestamp"]).dt.to_period("M")
        monthly = eq_df.groupby("month").agg(start=("equity", "first"), end=("equity", "last"))
        monthly["pct"] = (monthly["end"] - monthly["start"]) / monthly["start"] * 100
        monthly = monthly.reset_index()
        monthly["label"] = monthly["month"].astype(str)
        colors = [color_pct(r) for r in monthly["pct"]]
        fig_month = go.Figure(go.Bar(x=monthly["label"], y=monthly["pct"], marker_color=colors,
                                     text=[f"{r:+.1f}%" for r in monthly["pct"]], textposition="auto"))
        fig_month.update_layout(**DARK_LAYOUT, height=380, xaxis_title="月份", yaxis_title="收益率 (%)", margin=DARK_MARGIN)
    else:
        fig_month = go.Figure()
        fig_month.update_layout(**DARK_LAYOUT, height=380, margin=DARK_MARGIN)

    return {
        "metrics": {
            "total_return_pct": round(result.total_return_pct, 2),
            "sharpe_ratio": round(result.sharpe_ratio, 2),
            "max_drawdown_pct": round(result.max_drawdown_pct, 2),
            "win_rate": round(result.win_rate, 1),
            "profit_factor": round(result.profit_factor, 2),
            "total_trades": result.total_trades,
            "avg_profit": round(result.avg_profit, 2),
            "avg_loss": round(result.avg_loss, 2),
            "total_return": round(result.total_return, 2),
            "max_drawdown": round(result.max_drawdown, 2),
            "winning_trades": result.winning_trades,
            "losing_trades": result.losing_trades,
        },
        "equity_chart": fig_to_json(fig_eq),
        "kline_chart": fig_to_json(fig_kline),
        "monthly_chart": fig_to_json(fig_month),
    }


def build_backtest_data(strategy_id, days, capital, commission, slippage, params):
    kwargs = {}
    if strategy_id == "ma_cross":
        kwargs["fast_period"] = int(params.get("fast_period", 10))
        kwargs["slow_period"] = int(params.get("slow_period", 30))
    elif strategy_id == "rsi":
        kwargs["period"] = int(params.get("period", 14))
        kwargs["oversold"] = float(params.get("oversold", 30))
        kwargs["overbought"] = float(params.get("overbought", 70))
    elif strategy_id == "grid":
        kwargs["grid_num"] = int(params.get("grid_num", 10))
        kwargs["grid_range_pct"] = float(params.get("grid_range_pct", 0.05))

    result, df = run_backtest(strategy_id, days, capital, **kwargs)

    eq_df = pd.DataFrame(result.equity_curve)
    fig_eq = go.Figure()
    fig_eq.add_trace(go.Scatter(x=eq_df["timestamp"], y=eq_df["equity"], name="权益",
                                line=dict(color="#00d4aa", width=2),
                                fill="tozeroy", fillcolor="rgba(0,212,170,0.08)"))
    fig_eq.add_hline(y=capital, line_dash="dash", line_color="#ffa502")
    fig_eq.update_layout(**DARK_LAYOUT, height=350, xaxis_title="时间", yaxis_title="权益 (USDT)", margin=DARK_MARGIN)

    if not eq_df.empty:
        eq_df["drawdown"] = (eq_df["equity"] - eq_df["equity"].cummax()) / eq_df["equity"].cummax() * 100
        fig_dd = go.Figure()
        fig_dd.add_trace(go.Scatter(x=eq_df["timestamp"], y=eq_df["drawdown"], fill="tozeroy",
                                    fillcolor="rgba(255,71,87,0.15)", line=dict(color="#ff4757", width=1.5), name="回撤"))
        fig_dd.update_layout(**DARK_LAYOUT, height=350, xaxis_title="时间", yaxis_title="回撤 (%)", margin=DARK_MARGIN)
    else:
        fig_dd = go.Figure()

    trade_pnls = [t.pnl for t in result.trades]
    fig_pnl = go.Figure()
    if trade_pnls:
        cum_pnl = np.cumsum(trade_pnls)
        fig_pnl.add_trace(go.Bar(x=list(range(1, len(trade_pnls) + 1)), y=trade_pnls,
                                 name="单笔盈亏",
                                 marker_color=[color_pct(p) for p in trade_pnls]))
        fig_pnl.add_trace(go.Scatter(x=list(range(1, len(cum_pnl) + 1)), y=cum_pnl,
                                     name="累计盈亏", line=dict(color="#ffa502", width=2), yaxis="y2"))
        fig_pnl.update_layout(**DARK_LAYOUT, height=350, yaxis2=dict(overlaying="y", side="right"), margin=DARK_MARGIN, barmode="group")

    fig_dist = go.Figure()
    if trade_pnls:
        fig_dist.add_trace(go.Histogram(x=trade_pnls, nbinsx=20, marker_color="#4a90d9", marker_line_color="#6ab0ff"))
        fig_dist.add_vline(x=0, line_dash="dash", line_color="#ffa502")
        fig_dist.update_layout(**DARK_LAYOUT, height=350, xaxis_title="盈亏 (USDT)", yaxis_title="频次", margin=DARK_MARGIN)

    trades_table = []
    for i, t in enumerate(result.trades):
        trades_table.append({
            "id": i + 1, "side": t.side,
            "entry_time": str(t.entry_time), "exit_time": str(t.exit_time),
            "entry_price": round(t.entry_price, 2), "exit_price": round(t.exit_price, 2),
            "amount": round(t.amount, 6), "pnl": round(t.pnl, 2),
            "pnl_pct": round(t.pnl_pct, 2), "commission": round(t.commission, 2),
        })

    return {
        "metrics": {
            "total_return_pct": round(result.total_return_pct, 2),
            "sharpe_ratio": round(result.sharpe_ratio, 2),
            "max_drawdown_pct": round(result.max_drawdown_pct, 2),
            "win_rate": round(result.win_rate, 1),
            "profit_factor": round(result.profit_factor, 2),
            "total_trades": result.total_trades,
            "avg_profit": round(result.avg_profit, 2),
            "avg_loss": round(result.avg_loss, 2),
            "initial_capital": round(result.initial_capital, 2),
            "final_capital": round(result.final_capital, 2),
            "winning_trades": result.winning_trades,
            "losing_trades": result.losing_trades,
        },
        "equity_chart": fig_to_json(fig_eq),
        "drawdown_chart": fig_to_json(fig_dd),
        "pnl_chart": fig_to_json(fig_pnl),
        "dist_chart": fig_to_json(fig_dist),
        "trades": trades_table,
    }


def build_compare_data(days=60, capital=10000):
    results = {}
    for sid, info in STRATEGY_MAP.items():
        strat = info["cls"]()
        strat.set_param("symbol", "BTC/USDT")
        df = generate_sample_data(days)
        engine = BacktestEngine(strat, df, initial_capital=capital)
        results[sid] = engine.run()

    compare = []
    for sid, r in results.items():
        compare.append({
            "id": sid, "name": STRATEGY_MAP[sid]["name"],
            "total_return_pct": round(r.total_return_pct, 2),
            "sharpe_ratio": round(r.sharpe_ratio, 2),
            "max_drawdown_pct": round(r.max_drawdown_pct, 2),
            "win_rate": round(r.win_rate, 1),
            "profit_factor": round(r.profit_factor, 2),
            "total_trades": r.total_trades,
            "winning_trades": r.winning_trades,
            "losing_trades": r.losing_trades,
            "avg_profit": round(r.avg_profit, 2),
            "avg_loss": round(r.avg_loss, 2),
        })

    names = [c["name"] for c in compare]
    fig_ret = go.Figure(go.Bar(x=names, y=[c["total_return_pct"] for c in compare],
                               marker_color=[color_pct(c["total_return_pct"]) for c in compare],
                               text=[f"{c['total_return_pct']:+.2f}%" for c in compare], textposition="auto"))
    fig_ret.update_layout(**DARK_LAYOUT, height=350, yaxis_title="收益率 (%)", margin=DARK_MARGIN)

    fig_sharpe = go.Figure(go.Bar(x=names, y=[c["sharpe_ratio"] for c in compare],
                                  marker_color="#4a90d9",
                                  text=[f"{c['sharpe_ratio']:.2f}" for c in compare], textposition="auto"))
    fig_sharpe.update_layout(**DARK_LAYOUT, height=350, yaxis_title="夏普比率", margin=DARK_MARGIN)

    fig_all_eq = go.Figure()
    for sid, r in results.items():
        eq_df = pd.DataFrame(r.equity_curve)
        if not eq_df.empty:
            fig_all_eq.add_trace(go.Scatter(x=eq_df["timestamp"], y=eq_df["equity"],
                                            name=STRATEGY_MAP[sid]["name"], line=dict(width=2)))
    fig_all_eq.add_hline(y=capital, line_dash="dash", line_color="#ffa502", annotation_text="初始资金")
    fig_all_eq.update_layout(**DARK_LAYOUT, height=450, xaxis_title="时间", yaxis_title="权益 (USDT)", margin=DARK_MARGIN)

    fig_wr = go.Figure(go.Bar(x=names, y=[c["win_rate"] for c in compare], marker_color="#00d4aa"))
    fig_wr.update_layout(**DARK_LAYOUT, height=350, yaxis_title="胜率 (%)", margin=DARK_MARGIN)

    fig_mdd = go.Figure(go.Bar(x=names, y=[c["max_drawdown_pct"] for c in compare], marker_color="#ff4757"))
    fig_mdd.update_layout(**DARK_LAYOUT, height=350, yaxis_title="最大回撤 (%)", margin=DARK_MARGIN)

    return {
        "compare": compare,
        "return_chart": fig_to_json(fig_ret),
        "sharpe_chart": fig_to_json(fig_sharpe),
        "equity_chart": fig_to_json(fig_all_eq),
        "winrate_chart": fig_to_json(fig_wr),
        "drawdown_chart": fig_to_json(fig_mdd),
    }


def build_risk_data(days=60, capital=10000):
    result, df = run_backtest("ma_cross", days, capital)
    eq_df = pd.DataFrame(result.equity_curve)
    if eq_df.empty:
        return {"summary": {}, "risk_metrics": [], "drawdown_chart": {}, "dd_dist_chart": {}, "return_dist_chart": {}, "rolling_sharpe_chart": {}}

    eq_df["timestamp"] = pd.to_datetime(eq_df["timestamp"])
    eq_df.set_index("timestamp", inplace=True)
    eq_df["returns"] = eq_df["equity"].pct_change()
    eq_df["drawdown"] = (eq_df["equity"] - eq_df["equity"].cummax()) / eq_df["equity"].cummax() * 100
    eq_df["peak"] = eq_df["equity"].cummax()

    daily_returns = eq_df["returns"].dropna().resample("D").sum()
    var_95 = daily_returns.quantile(0.05) if len(daily_returns) > 0 else 0
    cvar_95 = daily_returns[daily_returns <= var_95].mean() if len(daily_returns) > 0 and var_95 < 0 else 0
    volatility = daily_returns.std() * np.sqrt(365) * 100 if len(daily_returns) > 1 else 0
    sortino = (daily_returns.mean() / daily_returns[daily_returns < 0].std() * np.sqrt(365)) if len(daily_returns[daily_returns < 0]) > 1 else 0
    calmar = (result.total_return_pct / result.max_drawdown_pct) if result.max_drawdown_pct > 0 else 0

    fig_dd = go.Figure()
    fig_dd.add_trace(go.Scatter(x=eq_df.index, y=eq_df["drawdown"], fill="tozeroy",
                                fillcolor="rgba(255,71,87,0.2)", line=dict(color="#ff4757", width=1.5), name="回撤"))
    fig_dd.update_layout(**DARK_LAYOUT, height=400, xaxis_title="时间", yaxis_title="回撤 (%)", margin=DARK_MARGIN)

    fig_dd_hist = go.Figure()
    fig_dd_hist.add_trace(go.Histogram(x=eq_df["drawdown"].dropna(), nbinsx=30, marker_color="#ff6b81", marker_line_color="#ff4757"))
    fig_dd_hist.update_layout(**DARK_LAYOUT, height=400, xaxis_title="回撤 (%)", yaxis_title="频次", margin=DARK_MARGIN)

    returns = eq_df["returns"].dropna()
    fig_ret = go.Figure()
    if len(returns) > 0:
        fig_ret.add_trace(go.Histogram(x=returns * 100, nbinsx=50, marker_color="#4a90d9", marker_line_color="#6ab0ff"))
        fig_ret.add_vline(x=returns.mean() * 100, line_dash="dash", line_color="#ffa502",
                          annotation_text=f"均值: {returns.mean()*100:.3f}%")
        fig_ret.add_vline(x=0, line_dash="dot", line_color="#888")
    fig_ret.update_layout(**DARK_LAYOUT, height=400, xaxis_title="收益率 (%)", yaxis_title="频次", margin=DARK_MARGIN)

    fig_rs = go.Figure()
    if len(returns) > 30:
        rolling_sharpe = returns.rolling(30).mean() / returns.rolling(30).std() * np.sqrt(365 * 24)
        fig_rs.add_trace(go.Scatter(x=returns.index[30:], y=rolling_sharpe[30:],
                                    line=dict(color="#ffa502", width=1.5), name="滚动夏普"))
        fig_rs.add_hline(y=1, line_dash="dash", line_color="#00d4aa", annotation_text="夏普=1")
        fig_rs.add_hline(y=0, line_dash="dot", line_color="#888")
    fig_rs.update_layout(**DARK_LAYOUT, height=400, xaxis_title="时间", yaxis_title="夏普比率", margin=DARK_MARGIN)

    risk_metrics = [
        {"metric": "最大回撤", "value": f"-{result.max_drawdown_pct:.2f}%"},
        {"metric": "VaR (95%)", "value": f"{var_95*100:.2f}%"},
        {"metric": "CVaR / 期望损失 (95%)", "value": f"{cvar_95*100:.2f}%"},
        {"metric": "年化波动率", "value": f"{volatility:.2f}%"},
        {"metric": "夏普比率", "value": f"{result.sharpe_ratio:.2f}"},
        {"metric": "Sortino比率", "value": f"{sortino:.2f}"},
        {"metric": "Calmar比率", "value": f"{calmar:.2f}"},
        {"metric": "日均收益率", "value": f"{daily_returns.mean()*100:.4f}%"},
        {"metric": "日均波动率", "value": f"{daily_returns.std()*100:.4f}%"},
        {"metric": "最大单日亏损", "value": f"{daily_returns.min()*100:.2f}%"},
        {"metric": "最大单日盈利", "value": f"{daily_returns.max()*100:.2f}%"},
        {"metric": "正收益天数占比", "value": f"{(daily_returns > 0).mean()*100:.1f}%"},
    ]

    return {
        "summary": {
            "max_drawdown_pct": round(result.max_drawdown_pct, 2),
            "var_95": round(var_95 * 100, 2),
            "cvar_95": round(cvar_95 * 100, 2),
            "volatility": round(volatility, 2),
        },
        "risk_metrics": risk_metrics,
        "drawdown_chart": fig_to_json(fig_dd),
        "dd_dist_chart": fig_to_json(fig_dd_hist),
        "return_dist_chart": fig_to_json(fig_ret),
        "rolling_sharpe_chart": fig_to_json(fig_rs),
    }


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CryptoQuant 量化交易仪表盘</title>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0d0d1a; color: #e0e0f0; }
.sidebar { position:fixed; left:0; top:0; width:220px; height:100vh; background:#13132a; border-right:1px solid #2a2a4a; padding:20px 0; z-index:100; }
.sidebar h2 { text-align:center; padding:10px; font-size:18px; color:#00d4aa; border-bottom:1px solid #2a2a4a; margin-bottom:10px; }
.sidebar a { display:block; padding:12px 24px; color:#8888aa; text-decoration:none; font-size:14px; transition:all .2s; border-left:3px solid transparent; }
.sidebar a:hover, .sidebar a.active { color:#00d4aa; background:rgba(0,212,170,0.08); border-left-color:#00d4aa; }
.main { margin-left:220px; padding:24px 32px; min-height:100vh; }
.page { display:none; }
.page.active { display:block; }
h1 { font-size:24px; margin-bottom:20px; color:#e0e0f0; }
h2 { font-size:18px; margin:16px 0 12px; color:#c0c0d0; }
.metrics-row { display:grid; grid-template-columns:repeat(auto-fit, minmax(200px, 1fr)); gap:16px; margin-bottom:24px; }
.metric-card { background:linear-gradient(135deg,#1e1e2e,#2d2d44); border-radius:12px; padding:20px; border:1px solid #3d3d5c; }
.metric-card .label { font-size:13px; color:#8888aa; margin-bottom:6px; }
.metric-card .value { font-size:26px; font-weight:700; }
.metric-card .delta { font-size:13px; margin-top:4px; }
.positive { color:#00d4aa; }
.negative { color:#ff4757; }
.neutral { color:#ffa502; }
.charts-row { display:grid; grid-template-columns:1fr 1fr; gap:20px; margin-bottom:24px; }
.chart-box { background:#1a1a2e; border-radius:12px; padding:16px; border:1px solid #2a2a4a; }
.chart-full { grid-column:1/-1; }
table { width:100%; border-collapse:collapse; background:#1a1a2e; border-radius:8px; overflow:hidden; margin-top:12px; }
th { background:#2a2a4a; padding:10px 14px; text-align:left; font-size:13px; color:#8888aa; }
td { padding:10px 14px; border-top:1px solid #2a2a3a; font-size:13px; }
tr:hover td { background:rgba(0,212,170,0.04); }
.btn { padding:10px 24px; border:none; border-radius:8px; cursor:pointer; font-size:14px; font-weight:600; transition:all .2s; }
.btn-primary { background:#00d4aa; color:#0d0d1a; }
.btn-primary:hover { background:#00e8bb; }
.controls { display:flex; gap:12px; flex-wrap:wrap; align-items:center; margin-bottom:20px; }
.controls label { font-size:13px; color:#8888aa; }
.controls select, .controls input { background:#1e1e2e; color:#e0e0f0; border:1px solid #3d3d5c; border-radius:6px; padding:6px 12px; font-size:13px; }
.controls select:focus, .controls input:focus { outline:none; border-color:#00d4aa; }
.loading { text-align:center; padding:40px; color:#8888aa; }
.form-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); gap:16px; background:#1a1a2e; border-radius:12px; padding:20px; border:1px solid #2a2a4a; }
.form-group { display:flex; flex-direction:column; gap:6px; }
.form-group label { font-size:13px; color:#8888aa; font-weight:500; }
.form-group input, .form-group select { background:#13132a; color:#e0e0f0; border:1px solid #3d3d5c; border-radius:6px; padding:8px 12px; font-size:13px; }
.form-group input:focus, .form-group select:focus { outline:none; border-color:#00d4aa; }
.exchange-card { background:linear-gradient(135deg,#1e1e2e,#2d2d44); border-radius:12px; padding:20px; border:1px solid #3d3d5c; margin-bottom:12px; display:flex; justify-content:space-between; align-items:center; }
.exchange-info { flex:1; }
.exchange-info h3 { font-size:16px; color:#e0e0f0; margin-bottom:8px; }
.exchange-info p { font-size:13px; color:#8888aa; margin:2px 0; }
.exchange-actions { display:flex; gap:8px; }
.btn-sm { padding:6px 14px; font-size:12px; border:none; border-radius:6px; cursor:pointer; }
.btn-test { background:#4a90d9; color:#fff; }
.btn-edit { background:#ffa502; color:#0d0d1a; }
.btn-del { background:#ff4757; color:#fff; }
.alert { padding:12px 16px; border-radius:8px; margin-bottom:12px; font-size:13px; }
.alert-success { background:rgba(0,212,170,0.15); border:1px solid #00d4aa; color:#00d4aa; }
.alert-error { background:rgba(255,71,87,0.15); border:1px solid #ff4757; color:#ff4757; }
.badge { display:inline-block; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:600; }
.badge-sandbox { background:rgba(255,165,2,0.2); color:#ffa502; }
.badge-live { background:rgba(0,212,170,0.2); color:#00d4aa; }
</style>
</head>
<body>
<div class="sidebar">
  <h2>📊 CryptoQuant</h2>
  <a href="#" class="active" onclick="showPage('overview')">🏠 概览</a>
  <a href="#" onclick="showPage('backtest')">📈 回测分析</a>
  <a href="#" onclick="showPage('compare')">💰 交易分析</a>
  <a href="#" onclick="showPage('risk')">⚠️ 风险分析</a>
  <a href="#" onclick="showPage('live')">🔄 实时交易</a>
  <a href="#" onclick="showPage('exchanges')">⚙️ 交易所配置</a>
  <a href="#" onclick="showPage('sandbox')">🧪 虚拟盘交易</a>
</div>
<div class="main">
  <!-- Overview -->
  <div id="page-overview" class="page active">
    <h1>🏠 量化交易概览</h1>
    <div class="metrics-row" id="overview-metrics"></div>
    <div class="charts-row">
      <div class="chart-box chart-full"><h2>📈 权益曲线</h2><div id="chart-equity"></div></div>
    </div>
    <div class="charts-row">
      <div class="chart-box"><h2>📊 K线走势</h2><div id="chart-kline"></div></div>
      <div class="chart-box"><h2>📊 月度收益</h2><div id="chart-monthly"></div></div>
    </div>
  </div>
  <!-- Backtest -->
  <div id="page-backtest" class="page">
    <h1>📈 回测分析</h1>
    <div class="controls">
      <label>策略</label>
      <select id="bt-strategy"><option value="ma_cross">MA均线交叉</option><option value="rsi">RSI超买超卖</option><option value="grid">网格交易</option></select>
      <label>天数</label><input id="bt-days" type="number" value="180" min="30" max="365">
      <label>资金</label><input id="bt-capital" type="number" value="10000" min="100">
      <label>手续费</label><input id="bt-commission" type="number" value="0.001" step="0.0001">
      <label>滑点</label><input id="bt-slippage" type="number" value="0.0005" step="0.0001">
      <button class="btn btn-primary" onclick="runBacktest()">🚀 运行回测</button>
    </div>
    <div id="bt-params-ma" class="controls">
      <label>快线</label><input id="bt-fast" type="number" value="10">
      <label>慢线</label><input id="bt-slow" type="number" value="30">
    </div>
    <div id="bt-params-rsi" class="controls" style="display:none">
      <label>周期</label><input id="bt-rsi-period" type="number" value="14">
      <label>超卖</label><input id="bt-oversold" type="number" value="30">
      <label>超买</label><input id="bt-overbought" type="number" value="70">
    </div>
    <div id="bt-params-grid" class="controls" style="display:none">
      <label>网格数</label><input id="bt-grid-num" type="number" value="10">
      <label>范围%</label><input id="bt-grid-range" type="number" value="0.05" step="0.01">
    </div>
    <div class="metrics-row" id="bt-metrics"></div>
    <div class="charts-row">
      <div class="chart-box"><h2>权益曲线</h2><div id="bt-chart-equity"></div></div>
      <div class="chart-box"><h2>回撤曲线</h2><div id="bt-chart-drawdown"></div></div>
    </div>
    <div class="charts-row">
      <div class="chart-box"><h2>累计盈亏</h2><div id="bt-chart-pnl"></div></div>
      <div class="chart-box"><h2>盈亏分布</h2><div id="bt-chart-dist"></div></div>
    </div>
    <h2>📝 交易明细</h2>
    <div id="bt-trades-table"></div>
  </div>
  <!-- Compare -->
  <div id="page-compare" class="page">
    <h1>💰 交易分析 — 策略对比</h1>
    <div id="compare-table"></div>
    <div class="charts-row">
      <div class="chart-box"><h2>收益率对比</h2><div id="cmp-chart-return"></div></div>
      <div class="chart-box"><h2>夏普比率对比</h2><div id="cmp-chart-sharpe"></div></div>
    </div>
    <div class="charts-row">
      <div class="chart-box chart-full"><h2>权益曲线对比</h2><div id="cmp-chart-equity"></div></div>
    </div>
    <div class="charts-row">
      <div class="chart-box"><h2>胜率对比</h2><div id="cmp-chart-winrate"></div></div>
      <div class="chart-box"><h2>最大回撤对比</h2><div id="cmp-chart-drawdown"></div></div>
    </div>
  </div>
  <!-- Risk -->
  <div id="page-risk" class="page">
    <h1>⚠️ 风险分析</h1>
    <div class="metrics-row" id="risk-metrics"></div>
    <div class="charts-row">
      <div class="chart-box"><h2>📉 回撤曲线</h2><div id="risk-chart-dd"></div></div>
      <div class="chart-box"><h2>回撤分布</h2><div id="risk-chart-dd-dist"></div></div>
    </div>
    <div class="charts-row">
      <div class="chart-box"><h2>收益率分布</h2><div id="risk-chart-ret-dist"></div></div>
      <div class="chart-box"><h2>滚动夏普比率</h2><div id="risk-chart-rolling-sharpe"></div></div>
    </div>
    <h2>📋 风险指标汇总</h2>
    <div id="risk-table"></div>
  </div>
  <!-- Live -->
  <div id="page-live" class="page">
    <h1>🔄 实时交易</h1>
    <div class="controls">
      <label>策略</label>
      <select id="live-strategy"><option value="ma_cross">MA均线交叉</option><option value="rsi">RSI超买超卖</option><option value="grid">网格交易</option></select>
      <label>市场</label><select id="live-market"><option value="spot">现货</option><option value="swap">合约</option></select>
      <button class="btn btn-primary" onclick="loadLive()">🔄 刷新数据</button>
    </div>
    <div class="metrics-row" id="live-metrics"></div>
    <div class="charts-row">
      <div class="chart-box chart-full"><h2>📈 价格走势</h2><div id="live-chart-price"></div></div>
    </div>
    <h2>📋 最近交易记录</h2>
    <div id="live-trades-table"></div>
    <h2>⚠️ 风控状态</h2>
    <div class="metrics-row" id="live-risk-metrics"></div>
  </div>
  <!-- Exchange Config -->
  <div id="page-exchanges" class="page">
    <h1>⚙️ 交易所API配置</h1>
    <div class="controls">
      <button class="btn btn-primary" onclick="showAddExchange()">➕ 添加交易所</button>
      <button class="btn btn-primary" onclick="loadExchanges()">🔄 刷新</button>
    </div>
    <div id="exchange-list"></div>
    <div id="exchange-form" style="display:none">
      <h2 id="exchange-form-title">添加交易所</h2>
      <div class="form-grid">
        <div class="form-group">
          <label>配置名称 (唯一ID)</label>
          <input id="ex-config-id" type="text" placeholder="my_binance">
        </div>
        <div class="form-group">
          <label>交易所</label>
          <select id="ex-exchange-id"></select>
        </div>
        <div class="form-group">
          <label>API Key</label>
          <input id="ex-api-key" type="text" placeholder="输入API Key">
        </div>
        <div class="form-group">
          <label>Secret</label>
          <input id="ex-secret" type="password" placeholder="输入Secret">
        </div>
        <div class="form-group" id="ex-password-group" style="display:none">
          <label>Passphrase (OKX)</label>
          <input id="ex-password" type="password" placeholder="输入Passphrase">
        </div>
        <div class="form-group">
          <label>市场类型</label>
          <select id="ex-market-type"><option value="spot">现货</option><option value="swap">永续合约</option></select>
        </div>
        <div class="form-group">
          <label>沙箱模式 (测试网)</label>
          <select id="ex-sandbox"><option value="true">✅ 启用 (虚拟盘)</option><option value="false">❌ 禁用 (实盘)</option></select>
        </div>
        <div class="form-group">
          <label>请求频率限制 (ms)</label>
          <input id="ex-rate-limit" type="number" value="1000">
        </div>
      </div>
      <div class="controls" style="margin-top:16px">
        <button class="btn btn-primary" onclick="saveExchange()">💾 保存配置</button>
        <button class="btn" onclick="hideExchangeForm()" style="background:#3d3d5c;color:#e0e0f0">取消</button>
        <button class="btn" onclick="testConnection()" style="background:#4a90d9;color:#fff">🔌 测试连接</button>
      </div>
      <div id="ex-test-result" style="margin-top:12px"></div>
    </div>
  </div>
  <!-- Sandbox Trading -->
  <div id="page-sandbox" class="page">
    <h1>🧪 虚拟盘交易 (沙箱/测试网)</h1>
    <div class="controls">
      <label>选择交易所配置</label>
      <select id="sb-config"></select>
      <button class="btn btn-primary" onclick="loadSandbox()">🔄 加载账户</button>
    </div>
    <div id="sandbox-warning" style="display:none;background:rgba(255,165,2,0.1);border:1px solid #ffa502;border-radius:8px;padding:12px;margin-bottom:16px">
      ⚠️ <strong>沙箱模式</strong>：当前使用交易所测试网，资金为虚拟资金，不会影响真实账户。
    </div>
    <div class="metrics-row" id="sb-balance"></div>
    <h2>📝 下单</h2>
    <div class="form-grid" style="grid-template-columns:repeat(5,1fr)">
      <div class="form-group">
        <label>交易对</label>
        <input id="sb-symbol" type="text" value="BTC/USDT">
      </div>
      <div class="form-group">
        <label>方向</label>
        <select id="sb-side"><option value="buy">买入</option><option value="sell">卖出</option></select>
      </div>
      <div class="form-group">
        <label>类型</label>
        <select id="sb-type"><option value="market">市价</option><option value="limit">限价</option></select>
      </div>
      <div class="form-group">
        <label>数量</label>
        <input id="sb-amount" type="number" value="0.001" step="0.001">
      </div>
      <div class="form-group">
        <label>价格 (限价)</label>
        <input id="sb-price" type="number" placeholder="限价单填写">
      </div>
    </div>
    <div class="controls" style="margin-top:12px">
      <button class="btn btn-primary" onclick="placeOrder()" style="background:#00d4aa">📈 买入</button>
      <button class="btn" onclick="placeOrder()" style="background:#ff4757;color:#fff" id="btn-sell">📉 卖出</button>
    </div>
    <div id="sb-order-result" style="margin-top:12px"></div>
    <h2>📋 当前挂单</h2>
    <div id="sb-open-orders"></div>
    <h2>📊 持仓</h2>
    <div id="sb-positions"></div>
    <h2>📜 最近交易</h2>
    <div id="sb-trade-history"></div>
  </div>
</div>

<script>
function showPage(name) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.sidebar a').forEach(a => a.classList.remove('active'));
  document.getElementById('page-' + name).classList.add('active');
  event.target.classList.add('active');
  if (name === 'overview') loadOverview();
  if (name === 'compare') loadCompare();
  if (name === 'risk') loadRisk();
  if (name === 'exchanges') loadExchanges();
  if (name === 'sandbox') loadSandboxConfigs();
}

function renderChart(divId, chartJson) {
  Plotly.newPlot(document.getElementById(divId), chartJson.data, chartJson.layout, {responsive:true, displaylogo:false});
}

function metricCard(label, value, cls) {
  return '<div class="metric-card"><div class="label">' + label + '</div><div class="value ' + cls + '">' + value + '</div></div>';
}

function buildTable(data, cols) {
  if (!data || !data.length) return '<p style="color:#8888aa">暂无数据</p>';
  let html = '<table><tr>';
  cols.forEach(c => html += '<th>' + c.label + '</th>');
  html += '</tr>';
  data.forEach(row => {
    html += '<tr>';
    cols.forEach(c => {
      let v = row[c.key];
      let cls = '';
      if (c.color === 'pnl') cls = v >= 0 ? 'positive' : 'negative';
      html += '<td class="' + cls + '">' + v + '</td>';
    });
    html += '</tr>';
  });
  html += '</table>';
  return html;
}

function loadOverview() {
  fetch('/api/overview').then(r=>r.json()).then(d => {
    let m = d.metrics;
    document.getElementById('overview-metrics').innerHTML =
      metricCard('总收益率', m.total_return_pct + '%', m.total_return_pct>=0?'positive':'negative') +
      metricCard('夏普比率', m.sharpe_ratio, m.sharpe_ratio>1?'positive':'neutral') +
      metricCard('最大回撤', '-' + m.max_drawdown_pct + '%', 'negative') +
      metricCard('胜率', m.win_rate + '%', m.win_rate>=50?'positive':'negative') +
      metricCard('盈利因子', m.profit_factor, m.profit_factor>1?'positive':'negative') +
      metricCard('总交易', m.total_trades, 'neutral') +
      metricCard('平均盈利', '$' + m.avg_profit, 'positive') +
      metricCard('平均亏损', '$' + m.avg_loss, 'negative');
    renderChart('chart-equity', d.equity_chart);
    renderChart('chart-kline', d.kline_chart);
    renderChart('chart-monthly', d.monthly_chart);
  });
}

function runBacktest() {
  let sid = document.getElementById('bt-strategy').value;
  let params = {};
  if (sid === 'ma_cross') { params.fast_period = document.getElementById('bt-fast').value; params.slow_period = document.getElementById('bt-slow').value; }
  if (sid === 'rsi') { params.period = document.getElementById('bt-rsi-period').value; params.oversold = document.getElementById('bt-oversold').value; params.overbought = document.getElementById('bt-overbought').value; }
  if (sid === 'grid') { params.grid_num = document.getElementById('bt-grid-num').value; params.grid_range_pct = document.getElementById('bt-grid-range').value; }
  fetch('/api/backtest', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({ strategy:sid, days:+document.getElementById('bt-days').value, capital:+document.getElementById('bt-capital').value, commission:+document.getElementById('bt-commission').value, slippage:+document.getElementById('bt-slippage').value, params:params })
  }).then(r=>r.json()).then(d => {
    let m = d.metrics;
    document.getElementById('bt-metrics').innerHTML =
      metricCard('总收益率', m.total_return_pct+'%', m.total_return_pct>=0?'positive':'negative') +
      metricCard('夏普比率', m.sharpe_ratio, m.sharpe_ratio>1?'positive':'neutral') +
      metricCard('最大回撤', '-'+m.max_drawdown_pct+'%', 'negative') +
      metricCard('胜率', m.win_rate+'%', m.win_rate>=50?'positive':'negative') +
      metricCard('盈利因子', m.profit_factor, m.profit_factor>1?'positive':'negative') +
      metricCard('初始资金', '$'+m.initial_capital, 'neutral') +
      metricCard('最终资金', '$'+m.final_capital, m.final_capital>=m.initial_capital?'positive':'negative') +
      metricCard('平均盈利', '$'+m.avg_profit, 'positive') +
      metricCard('平均亏损', '$'+m.avg_loss, 'negative') +
      metricCard('总交易', m.total_trades, 'neutral');
    renderChart('bt-chart-equity', d.equity_chart);
    renderChart('bt-chart-drawdown', d.drawdown_chart);
    renderChart('bt-chart-pnl', d.pnl_chart);
    renderChart('bt-chart-dist', d.dist_chart);
    document.getElementById('bt-trades-table').innerHTML = buildTable(d.trades, [
      {key:'id',label:'序号'},{key:'side',label:'方向'},{key:'entry_time',label:'入场时间'},{key:'exit_time',label:'出场时间'},
      {key:'entry_price',label:'入场价'},{key:'exit_price',label:'出场价'},{key:'pnl',label:'盈亏',color:'pnl'},{key:'pnl_pct',label:'收益率',color:'pnl'}
    ]);
  });
}

document.getElementById('bt-strategy').addEventListener('change', function() {
  document.getElementById('bt-params-ma').style.display = this.value==='ma_cross'?'flex':'none';
  document.getElementById('bt-params-rsi').style.display = this.value==='rsi'?'flex':'none';
  document.getElementById('bt-params-grid').style.display = this.value==='grid'?'flex':'none';
});

function loadCompare() {
  fetch('/api/compare').then(r=>r.json()).then(d => {
    document.getElementById('compare-table').innerHTML = buildTable(d.compare, [
      {key:'name',label:'策略'},{key:'total_return_pct',label:'收益率',color:'pnl'},{key:'sharpe_ratio',label:'夏普'},
      {key:'max_drawdown_pct',label:'最大回撤'},{key:'win_rate',label:'胜率'},{key:'profit_factor',label:'盈利因子'},
      {key:'total_trades',label:'总交易'},{key:'avg_profit',label:'平均盈利'},{key:'avg_loss',label:'平均亏损'}
    ]);
    renderChart('cmp-chart-return', d.return_chart);
    renderChart('cmp-chart-sharpe', d.sharpe_chart);
    renderChart('cmp-chart-equity', d.equity_chart);
    renderChart('cmp-chart-winrate', d.winrate_chart);
    renderChart('cmp-chart-drawdown', d.drawdown_chart);
  });
}

function loadRisk() {
  fetch('/api/risk').then(r=>r.json()).then(d => {
    let s = d.summary;
    document.getElementById('risk-metrics').innerHTML =
      metricCard('最大回撤', '-'+s.max_drawdown_pct+'%', 'negative') +
      metricCard('VaR (95%)', s.var_95+'%', 'negative') +
      metricCard('CVaR (95%)', s.cvar_95+'%', 'negative') +
      metricCard('年化波动率', s.volatility+'%', 'neutral');
    renderChart('risk-chart-dd', d.drawdown_chart);
    renderChart('risk-chart-dd-dist', d.dd_dist_chart);
    renderChart('risk-chart-ret-dist', d.return_dist_chart);
    renderChart('risk-chart-rolling-sharpe', d.rolling_sharpe_chart);
    document.getElementById('risk-table').innerHTML = buildTable(d.risk_metrics, [
      {key:'metric',label:'指标'},{key:'value',label:'值'}
    ]);
  });
}

function loadLive() {
  let sid = document.getElementById('live-strategy').value;
  fetch('/api/live?strategy='+sid).then(r=>r.json()).then(d => {
    let m = d.metrics;
    document.getElementById('live-metrics').innerHTML =
      metricCard('当前权益', '$'+m.final_capital, m.total_return_pct>=0?'positive':'negative') +
      metricCard('总收益率', m.total_return_pct+'%', m.total_return_pct>=0?'positive':'negative') +
      metricCard('夏普比率', m.sharpe_ratio, m.sharpe_ratio>1?'positive':'neutral') +
      metricCard('总交易', m.total_trades, 'neutral');
    renderChart('live-chart-price', d.price_chart);
    document.getElementById('live-trades-table').innerHTML = buildTable(d.trades, [
      {key:'id',label:'序号'},{key:'side',label:'方向'},{key:'entry_price',label:'入场价'},
      {key:'exit_price',label:'出场价'},{key:'pnl',label:'盈亏',color:'pnl'},{key:'pnl_pct',label:'收益率',color:'pnl'}
    ]);
    let rc = d.risk_config;
    document.getElementById('live-risk-metrics').innerHTML =
      metricCard('最大仓位', rc.max_position_size_pct, 'neutral') +
      metricCard('止损线', '-'+rc.stop_loss_pct, 'negative') +
      metricCard('最大回撤限制', '-'+rc.max_drawdown_pct, 'negative') +
      metricCard('日损失限制', '-'+rc.max_daily_loss_pct, 'negative');
  });
}

let _editingConfigId = null;

function showAddExchange() {
  _editingConfigId = null;
  document.getElementById('exchange-form-title').textContent = '添加交易所';
  document.getElementById('ex-config-id').value = '';
  document.getElementById('ex-config-id').disabled = false;
  document.getElementById('ex-api-key').value = '';
  document.getElementById('ex-secret').value = '';
  document.getElementById('ex-password').value = '';
  document.getElementById('ex-sandbox').value = 'true';
  document.getElementById('ex-market-type').value = 'spot';
  document.getElementById('ex-rate-limit').value = '1000';
  document.getElementById('ex-test-result').innerHTML = '';
  document.getElementById('exchange-form').style.display = 'block';
  loadExchangeOptions();
}

function hideExchangeForm() {
  document.getElementById('exchange-form').style.display = 'none';
  _editingConfigId = null;
}

function loadExchangeOptions() {
  fetch('/api/exchanges/supported').then(r=>r.json()).then(d => {
    let sel = document.getElementById('ex-exchange-id');
    sel.innerHTML = '';
    d.forEach(e => {
      let opt = document.createElement('option');
      opt.value = e.id;
      opt.textContent = e.name + (e.has_sandbox ? ' (支持沙箱)' : '');
      sel.appendChild(opt);
    });
    sel.onchange = function() {
      document.getElementById('ex-password-group').style.display = this.value === 'okx' ? 'flex' : 'none';
    };
  });
}

function loadExchanges() {
  fetch('/api/exchanges').then(r=>r.json()).then(d => {
    let html = '';
    d.forEach(ex => {
      let badge = ex.sandbox ? '<span class="badge badge-sandbox">沙箱</span>' : '<span class="badge badge-live">实盘</span>';
      html += '<div class="exchange-card"><div class="exchange-info">' +
        '<h3>' + ex.name + ' ' + badge + '</h3>' +
        '<p>交易所: ' + ex.exchange_id + ' | 市场: ' + ex.market_type + '</p>' +
        '<p>API Key: ' + (ex.has_api_key ? '✅ 已配置' : '❌ 未配置') +
        ' | Secret: ' + (ex.has_secret ? '✅ 已配置' : '❌ 未配置') + '</p>' +
        '<p>更新: ' + (ex.updated_at || '-') + '</p>' +
        '</div><div class="exchange-actions">' +
        '<button class="btn-sm btn-test" onclick="testConn(\'' + ex.id + '\')">🔌 测试</button>' +
        '<button class="btn-sm btn-edit" onclick="editExchange(\'' + ex.id + '\')">✏️ 编辑</button>' +
        '<button class="btn-sm btn-del" onclick="delExchange(\'' + ex.id + '\')">🗑️ 删除</button>' +
        '</div></div>';
    });
    if (!d.length) html = '<p style="color:#8888aa">暂无交易所配置，点击上方按钮添加</p>';
    document.getElementById('exchange-list').innerHTML = html;
  });
}

function saveExchange() {
  let data = {
    name: document.getElementById('ex-config-id').value || document.getElementById('ex-exchange-id').value,
    exchange_id: document.getElementById('ex-exchange-id').value,
    api_key: document.getElementById('ex-api-key').value,
    secret: document.getElementById('ex-secret').value,
    password: document.getElementById('ex-password').value,
    market_type: document.getElementById('ex-market-type').value,
    sandbox: document.getElementById('ex-sandbox').value === 'true',
    rate_limit: +document.getElementById('ex-rate-limit').value,
  };
  let configId = _editingConfigId || document.getElementById('ex-config-id').value;
  if (!configId) { alert('请填写配置名称'); return; }
  fetch('/api/exchanges/' + encodeURIComponent(configId), {
    method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data)
  }).then(r=>r.json()).then(d => {
    if (d.success) {
      document.getElementById('ex-test-result').innerHTML = '<div class="alert alert-success">✅ 配置已保存</div>';
      hideExchangeForm();
      loadExchanges();
    } else {
      document.getElementById('ex-test-result').innerHTML = '<div class="alert alert-error">❌ ' + d.error + '</div>';
    }
  });
}

function editExchange(configId) {
  fetch('/api/exchanges/' + encodeURIComponent(configId)).then(r=>r.json()).then(d => {
    _editingConfigId = configId;
    document.getElementById('exchange-form-title').textContent = '编辑交易所: ' + configId;
    document.getElementById('ex-config-id').value = configId;
    document.getElementById('ex-config-id').disabled = true;
    document.getElementById('ex-api-key').value = d.api_key || '';
    document.getElementById('ex-secret').value = d.secret || '';
    document.getElementById('ex-password').value = d.password || '';
    document.getElementById('ex-market-type').value = d.market_type || 'spot';
    document.getElementById('ex-sandbox').value = d.sandbox ? 'true' : 'false';
    document.getElementById('ex-rate-limit').value = d.rate_limit || 1000;
    document.getElementById('ex-test-result').innerHTML = '';
    document.getElementById('exchange-form').style.display = 'block';
    loadExchangeOptions();
    setTimeout(() => {
      document.getElementById('ex-exchange-id').value = d.exchange_id || 'binance';
      document.getElementById('ex-password-group').style.display = d.exchange_id === 'okx' ? 'flex' : 'none';
    }, 500);
  });
}

function delExchange(configId) {
  if (!confirm('确定删除配置 "' + configId + '"？')) return;
  fetch('/api/exchanges/' + encodeURIComponent(configId), {method:'DELETE'}).then(r=>r.json()).then(d => {
    if (d.success) loadExchanges();
    else alert('删除失败: ' + d.error);
  });
}

function testConn(configId) {
  fetch('/api/exchanges/' + encodeURIComponent(configId) + '/test').then(r=>r.json()).then(d => {
    if (d.success) alert('✅ ' + d.message);
    else alert('❌ 连接失败: ' + d.error);
  });
}

function testConnection() {
  let configId = _editingConfigId || document.getElementById('ex-config-id').value;
  if (!configId) { alert('请先填写配置名称并保存'); return; }
  document.getElementById('ex-test-result').innerHTML = '<div class="alert" style="color:#ffa502">⏳ 测试连接中...</div>';
  saveExchange();
  setTimeout(() => {
    fetch('/api/exchanges/' + encodeURIComponent(configId) + '/test').then(r=>r.json()).then(d => {
      if (d.success) {
        document.getElementById('ex-test-result').innerHTML = '<div class="alert alert-success">✅ ' + d.message + (d.usdt_balance !== undefined ? '<br>USDT余额: ' + d.usdt_balance : '') + '</div>';
      } else {
        document.getElementById('ex-test-result').innerHTML = '<div class="alert alert-error">❌ 连接失败: ' + d.error + '</div>';
      }
    });
  }, 500);
}

function loadSandboxConfigs() {
  fetch('/api/exchanges').then(r=>r.json()).then(d => {
    let sel = document.getElementById('sb-config');
    sel.innerHTML = '';
    d.forEach(ex => {
      let opt = document.createElement('option');
      opt.value = ex.id;
      opt.textContent = ex.name + ' (' + ex.exchange_id + ')' + (ex.sandbox ? ' [沙箱]' : ' [实盘]');
      sel.appendChild(opt);
    });
  });
}

function loadSandbox() {
  let configId = document.getElementById('sb-config').value;
  if (!configId) { alert('请先选择交易所配置'); return; }
  fetch('/api/sandbox/balance?config_id=' + encodeURIComponent(configId)).then(r=>r.json()).then(d => {
    if (d.error) {
      document.getElementById('sb-balance').innerHTML = '<div class="alert alert-error">❌ ' + d.error + '</div>';
      return;
    }
    document.getElementById('sandbox-warning').style.display = d.sandbox ? 'block' : 'none';
    let balHtml = '';
    d.balances.forEach(b => {
      if (b.total > 0) balHtml += metricCard(b.currency, '可用: ' + b.free.toFixed(4) + ' | 总计: ' + b.total.toFixed(4), 'neutral');
    });
    if (!balHtml) balHtml = '<p style="color:#8888aa">无余额</p>';
    document.getElementById('sb-balance').innerHTML = balHtml;
    loadSandboxOrders();
    loadSandboxPositions();
  });
}

function placeOrder() {
  let configId = document.getElementById('sb-config').value;
  if (!configId) { alert('请先选择交易所配置'); return; }
  let side = document.getElementById('sb-side').value;
  let data = {
    config_id: configId,
    symbol: document.getElementById('sb-symbol').value,
    side: side,
    type: document.getElementById('sb-type').value,
    amount: +document.getElementById('sb-amount').value,
    price: +document.getElementById('sb-price').value || undefined,
  };
  fetch('/api/sandbox/order', {
    method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data)
  }).then(r=>r.json()).then(d => {
    if (d.success) {
      document.getElementById('sb-order-result').innerHTML = '<div class="alert alert-success">✅ 订单已提交: ' + d.order_id + '</div>';
      setTimeout(() => { loadSandbox(); loadSandboxOrders(); }, 1000);
    } else {
      document.getElementById('sb-order-result').innerHTML = '<div class="alert alert-error">❌ ' + d.error + '</div>';
    }
  });
}

function loadSandboxOrders() {
  let configId = document.getElementById('sb-config').value;
  if (!configId) return;
  fetch('/api/sandbox/orders?config_id=' + encodeURIComponent(configId) + '&symbol=' + document.getElementById('sb-symbol').value)
    .then(r=>r.json()).then(d => {
      if (d.orders && d.orders.length) {
        document.getElementById('sb-open-orders').innerHTML = buildTable(d.orders, [
          {key:'id',label:'订单ID'},{key:'symbol',label:'交易对'},{key:'side',label:'方向'},
          {key:'type',label:'类型'},{key:'price',label:'价格'},{key:'amount',label:'数量'},
          {key:'filled',label:'已成交'},{key:'status',label:'状态'}
        ]) + '<div class="controls" style="margin-top:8px"><button class="btn btn-sm btn-del" onclick="cancelAllOrders()">取消所有挂单</button></div>';
      } else {
        document.getElementById('sb-open-orders').innerHTML = '<p style="color:#8888aa">暂无挂单</p>';
      }
    });
}

function cancelAllOrders() {
  let configId = document.getElementById('sb-config').value;
  let symbol = document.getElementById('sb-symbol').value;
  fetch('/api/sandbox/orders/cancel', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({config_id: configId, symbol: symbol})
  }).then(r=>r.json()).then(d => {
    if (d.success) { alert('✅ 已取消 ' + d.canceled + ' 个挂单'); loadSandboxOrders(); }
    else alert('❌ ' + d.error);
  });
}

function loadSandboxPositions() {
  let configId = document.getElementById('sb-config').value;
  if (!configId) return;
  fetch('/api/sandbox/positions?config_id=' + encodeURIComponent(configId))
    .then(r=>r.json()).then(d => {
      if (d.positions && d.positions.length) {
        document.getElementById('sb-positions').innerHTML = buildTable(d.positions, [
          {key:'symbol',label:'交易对'},{key:'side',label:'方向'},{key:'size',label:'数量'},
          {key:'entry_price',label:'入场价'},{key:'mark_price',label:'标记价'},
          {key:'unrealized_pnl',label:'未实现盈亏',color:'pnl'},{key:'leverage',label:'杠杆'}
        ]);
      } else {
        document.getElementById('sb-positions').innerHTML = '<p style="color:#8888aa">暂无持仓（现货模式无持仓概念）</p>';
      }
    });
}

loadOverview();
</script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route("/api/overview")
def api_overview():
    return jsonify(get_cached("overview", build_overview_data))


@app.route("/api/backtest", methods=["POST"])
def api_backtest():
    data = request.json or {}
    return jsonify(build_backtest_data(
        strategy_id=data.get("strategy", "ma_cross"),
        days=data.get("days", 60),
        capital=data.get("capital", 10000),
        commission=data.get("commission", 0.001),
        slippage=data.get("slippage", 0.0005),
        params=data.get("params", {}),
    ))


@app.route("/api/compare")
def api_compare():
    return jsonify(get_cached("compare", build_compare_data))


@app.route("/api/risk")
def api_risk():
    return jsonify(get_cached("risk", build_risk_data))


@app.route("/api/config", methods=["GET", "POST"])
def api_config():
    cfg = settings.to_dict() if hasattr(settings, 'to_dict') else {}
    if request.method == "POST":
        data = request.json or {}
        for k, v in data.items():
            if hasattr(settings, k):
                setattr(settings, k, v)
        return jsonify({"success": True, "config": cfg})
    return jsonify(cfg)


@app.route("/api/live")
def api_live():
    strategy_id = request.args.get("strategy", "ma_cross")
    result, df = run_backtest(strategy_id, 7, 10000)

    sample = df.iloc[::2]
    fig_price = go.Figure()
    fig_price.add_trace(go.Scatter(x=sample.index, y=sample["close"],
                                   line=dict(color="#00d4aa", width=2), name="价格"))
    fig_price.update_layout(**DARK_LAYOUT, height=400, xaxis_title="时间", yaxis_title="价格 (USDT)", margin=DARK_MARGIN)

    trades = []
    for i, t in enumerate(result.trades[-10:]):
        trades.append({
            "id": i + 1, "side": t.side,
            "entry_price": round(t.entry_price, 2),
            "exit_price": round(t.exit_price, 2),
            "pnl": round(t.pnl, 2), "pnl_pct": round(t.pnl_pct, 2),
        })

    risk_config = settings.risk
    return jsonify({
        "metrics": {
            "final_capital": round(result.final_capital, 2),
            "total_return_pct": round(result.total_return_pct, 2),
            "sharpe_ratio": round(result.sharpe_ratio, 2),
            "total_trades": result.total_trades,
        },
        "price_chart": fig_to_json(fig_price),
        "trades": trades,
        "risk_config": {
            "max_position_size_pct": f"{risk_config.get('max_position_size_pct', 0):.0%}",
            "stop_loss_pct": f"{risk_config.get('stop_loss_pct', 0):.1%}",
            "max_drawdown_pct": f"{risk_config.get('max_drawdown_pct', 0):.1%}",
            "max_daily_loss_pct": f"{risk_config.get('max_daily_loss_pct', 0):.1%}",
        },
    })


@app.route("/api/exchanges", methods=["GET", "POST"])
def api_list_exchanges():
    if request.method == "POST":
        data = request.json or {}
        config_id = data.get("id", data.get("exchange_id", ""))
        if not config_id:
            return jsonify({"error": "缺少配置 ID"}), 400
        try:
            save_exchange_config(config_id, data)
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
    return jsonify(list_exchange_configs())


@app.route("/api/exchanges/supported", methods=["GET"])
def api_supported_exchanges():
    return jsonify(get_supported_exchanges())


@app.route("/api/exchanges/<config_id>", methods=["GET"])
def api_get_exchange(config_id):
    cfg = get_exchange_config(config_id)
    if not cfg:
        return jsonify({"error": f"配置 '{config_id}' 不存在"}), 404
    return jsonify(cfg)


@app.route("/api/exchanges/<config_id>", methods=["PUT"])
def api_save_exchange(config_id):
    data = request.json or {}
    try:
        save_exchange_config(config_id, data)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/exchanges/<config_id>", methods=["DELETE"])
def api_delete_exchange(config_id):
    ok = delete_exchange_config(config_id)
    return jsonify({"success": ok})


@app.route("/api/exchanges/<config_id>/test", methods=["GET"])
def api_test_exchange(config_id):
    return jsonify(test_exchange_connection(config_id))


@app.route("/api/sandbox/balance", methods=["GET"])
def api_sandbox_balance():
    config_id = request.args.get("config_id", "")
    cfg = get_exchange_config(config_id)
    if not cfg:
        return jsonify({"error": f"配置 '{config_id}' 不存在"})

    try:
        exchange = get_exchange_instance(config_id)
        raw = exchange.fetch_balance()
        balances = []
        for currency, amounts in raw.items():
            if currency in ("free", "used", "total", "info"):
                continue
            if isinstance(amounts, dict):
                free = float(amounts.get("free", 0) or 0)
                used = float(amounts.get("used", 0) or 0)
                total = float(amounts.get("total", 0) or 0)
                if total > 0:
                    balances.append({"currency": currency, "free": free, "used": used, "total": total})
        exchange.close()
        return jsonify({"balances": balances, "sandbox": cfg.get("sandbox", False)})
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/sandbox/order", methods=["POST"])
def api_sandbox_order():
    data = request.json or {}
    config_id = data.get("config_id", "")
    cfg = get_exchange_config(config_id)
    if not cfg:
        return jsonify({"success": False, "error": f"配置 '{config_id}' 不存在"})

    try:
        exchange = get_exchange_instance(config_id)
        symbol = data.get("symbol", "BTC/USDT")
        side = data.get("side", "buy")
        order_type = data.get("type", "market")
        amount = float(data.get("amount", 0))
        price = data.get("price")
        if price:
            price = float(price)

        result = exchange.create_order(symbol, order_type, side, amount, price)
        exchange.close()
        return jsonify({
            "success": True,
            "order_id": str(result.get("id", "")),
            "status": result.get("status", ""),
            "filled": result.get("filled", 0),
            "price": result.get("price", 0),
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/sandbox/orders", methods=["GET"])
def api_sandbox_orders():
    config_id = request.args.get("config_id", "")
    symbol = request.args.get("symbol", "BTC/USDT")
    cfg = get_exchange_config(config_id)
    if not cfg:
        return jsonify({"orders": []})

    try:
        exchange = get_exchange_instance(config_id)
        raw_orders = exchange.fetch_open_orders(symbol)
        orders = []
        for o in raw_orders:
            orders.append({
                "id": str(o.get("id", "")),
                "symbol": o.get("symbol", ""),
                "side": o.get("side", ""),
                "type": o.get("type", ""),
                "price": o.get("price", 0),
                "amount": o.get("amount", 0),
                "filled": o.get("filled", 0),
                "status": o.get("status", ""),
            })
        exchange.close()
        return jsonify({"orders": orders})
    except Exception as e:
        return jsonify({"orders": [], "error": str(e)})


@app.route("/api/sandbox/orders/cancel", methods=["POST"])
def api_sandbox_cancel_orders():
    data = request.json or {}
    config_id = data.get("config_id", "")
    symbol = data.get("symbol", "BTC/USDT")
    cfg = get_exchange_config(config_id)
    if not cfg:
        return jsonify({"success": False, "error": "配置不存在"})

    try:
        exchange = get_exchange_instance(config_id)
        open_orders = exchange.fetch_open_orders(symbol)
        canceled = 0
        for o in open_orders:
            try:
                exchange.cancel_order(o["id"], symbol)
                canceled += 1
            except Exception:
                pass
        exchange.close()
        return jsonify({"success": True, "canceled": canceled})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/sandbox/positions", methods=["GET"])
def api_sandbox_positions():
    config_id = request.args.get("config_id", "")
    cfg = get_exchange_config(config_id)
    if not cfg:
        return jsonify({"positions": []})

    if cfg.get("market_type") == "spot":
        return jsonify({"positions": []})

    try:
        exchange = get_exchange_instance(config_id)
        raw_positions = exchange.fetch_positions()
        positions = []
        for p in raw_positions:
            size = float(p.get("contracts", 0) or 0)
            if size > 0:
                positions.append({
                    "symbol": p.get("symbol", ""),
                    "side": p.get("side", ""),
                    "size": size,
                    "entry_price": float(p.get("entryPrice", 0) or 0),
                    "mark_price": float(p.get("markPrice", 0) or 0),
                    "unrealized_pnl": float(p.get("unrealizedPnl", 0) or 0),
                    "leverage": int(p.get("leverage", 1) or 1),
                })
        exchange.close()
        return jsonify({"positions": positions})
    except Exception as e:
        return jsonify({"positions": [], "error": str(e)})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8501, debug=False)
