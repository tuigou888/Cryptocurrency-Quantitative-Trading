import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import logging
from typing import Optional
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

from strategy.ma_cross import MACrossStrategy
from strategy.rsi import RSIStrategy
from strategy.grid import GridStrategy
from backtest.engine import BacktestEngine, BacktestResult
from config.settings import settings

STRATEGY_MAP = {
    "ma_cross": {"name": "MA均线交叉", "cls": MACrossStrategy},
    "rsi": {"name": "RSI超买超卖", "cls": RSIStrategy},
    "grid": {"name": "网格交易", "cls": GridStrategy},
}


def _make_response(chart_type: str, title: str, x_axis: dict, series: list,
                   subtitle: str = "", annotations: list = None) -> dict:
    return {
        "code": 0,
        "data": {
            "chart_type": chart_type,
            "title": title,
            "subtitle": subtitle,
            "x_axis": x_axis,
            "series": series,
            "annotations": annotations or [],
        },
        "message": "ok",
    }


def _fmt_ts(dt) -> str:
    if hasattr(dt, "isoformat"):
        return dt.isoformat()
    return str(dt)


def build_equity_curve(result: BacktestResult, benchmark_result: Optional[BacktestResult] = None,
                       initial_capital: float = 10000) -> dict:
    eq_df = pd.DataFrame(result.equity_curve)
    if eq_df.empty:
        return _make_response("equity_curve", "策略收益曲线", {"type": "datetime", "data": []}, [])

    timestamps = eq_df["timestamp"].apply(_fmt_ts).tolist()
    equities = [round(e, 4) for e in eq_df["equity"].tolist()]

    series = [{
        "name": "策略净值",
        "type": "line",
        "data": equities,
        "smooth": True,
        "symbol": "none",
        "lineStyle": {"color": "#00d4aa", "width": 2},
        "areaStyle": {"color": "rgba(0,212,170,0.08)"},
    }]

    annotations = [{
        "type": "initial_capital",
        "y": round(initial_capital, 2),
        "text": f"初始资金 ${initial_capital:,.0f}",
    }]

    if benchmark_result is not None:
        bench_df = pd.DataFrame(benchmark_result.equity_curve)
        if not bench_df.empty:
            bench_eq = [round(e, 4) for e in bench_df["equity"].tolist()]
            series.append({
                "name": "基准净值",
                "type": "line",
                "data": bench_eq,
                "smooth": False,
                "symbol": "none",
                "lineStyle": {"color": "#ffa502", "type": "dashed", "width": 1.5},
            })

    max_dd = result.max_drawdown_pct
    peak_idx = eq_df["equity"].idxmax()
    annotations.append({
        "type": "max_drawdown",
        "x": _fmt_ts(eq_df.loc[peak_idx, "timestamp"]),
        "y": round(eq_df.loc[peak_idx, "equity"], 4),
        "text": f"最大回撤 -{max_dd:.2f}%",
    })

    return _make_response(
        "equity_curve", "策略收益曲线",
        {"type": "datetime", "data": timestamps},
        series,
        subtitle=f"夏普: {result.sharpe_ratio:.2f}  胜率: {result.win_rate:.1f}%",
        annotations=annotations,
    )


def build_drawdown(result: BacktestResult) -> dict:
    eq_df = pd.DataFrame(result.equity_curve)
    if eq_df.empty:
        return _make_response("drawdown", "回撤曲线", {"type": "datetime", "data": []}, [])

    eq_df["drawdown_pct"] = (eq_df["equity"] - eq_df["equity"].cummax()) / eq_df["equity"].cummax() * 100

    timestamps = eq_df["timestamp"].apply(_fmt_ts).tolist()
    dd_values = [round(d, 2) for d in eq_df["drawdown_pct"].tolist()]

    max_dd_val = abs(min(dd_values))
    max_idx = eq_df["drawdown_pct"].idxmin()

    series = [{
        "name": "回撤",
        "type": "line",
        "data": dd_values,
        "symbol": "none",
        "lineStyle": {"color": "#ff4757", "width": 1.5},
        "areaStyle": {"color": "rgba(255,71,87,0.15)", "origin": "start"},
    }]

    annotations = [{
        "type": "max_drawdown_point",
        "x": _fmt_ts(eq_df.loc[max_idx, "timestamp"]),
        "y": round(eq_df.loc[max_idx, "drawdown_pct"], 2),
        "text": f"最大回撤 {eq_df.loc[max_idx, 'drawdown_pct']:.2f}%",
    }]

    return _make_response(
        "drawdown", "动态回撤曲线",
        {"type": "datetime", "data": timestamps},
        series,
        subtitle=f"最大回撤: -{max_dd_val:.2f}%",
        annotations=annotations,
    )


def build_monthly_returns_heatmap(result: BacktestResult) -> dict:
    eq_df = pd.DataFrame(result.equity_curve)
    if eq_df.empty or len(eq_df) < 24:
        return _make_response("monthly_heatmap", "月度收益热力图", {"type": "category", "data": []}, [],
                              subtitle="数据不足，需要至少24条记录")

    eq_df["timestamp"] = pd.to_datetime(eq_df["timestamp"])
    eq_df["month"] = eq_df["timestamp"].dt.to_period("M")
    monthly = eq_df.groupby("month").agg(start=("equity", "first"), end=("equity", "last"))
    monthly["pct"] = ((monthly["end"] - monthly["start"]) / monthly["start"] * 100).round(2)
    monthly = monthly.reset_index()

    years = sorted(set(m.start_time.year for m in monthly["month"]))
    months = list(range(1, 13))

    heatmap_data = []
    x_axis_data = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"]
    y_axis_data = [str(y) for y in years]

    for _, row in monthly.iterrows():
        p = row["month"]
        heatmap_data.append({
            "x": str(p.month),
            "y": str(p.year),
            "value": float(row["pct"]),
        })

    if abs(monthly["pct"].max()) > abs(monthly["pct"].min()):
        max_abs = abs(monthly["pct"].max())
    else:
        max_abs = abs(monthly["pct"].min())

    return _make_response(
        "monthly_heatmap", "月度收益热力图",
        {"type": "category", "data": x_axis_data},
        [{
            "name": "月度收益率",
            "type": "heatmap",
            "data": heatmap_data,
            "yAxisData": y_axis_data,
            "label": {"show": True, "formatter": "{c}%"},
            "emphasis": {"itemStyle": {"shadowBlur": 10, "shadowColor": "rgba(0,0,0,0.5)"}},
        }],
        subtitle=f"收益范围: {monthly['pct'].min():.1f}% ~ {monthly['pct'].max():.1f}%",
        annotations=[{
            "type": "visualMap",
            "min": round(-max_abs, 2),
            "max": round(max_abs, 2),
            "inRange": {"color": ["#ff4757", "#2a2a4a", "#00d4aa"]},
        }],
    )


def build_pnl_distribution(result: BacktestResult) -> dict:
    trade_pnls = [t.pnl for t in result.trades]
    if not trade_pnls:
        return _make_response("pnl_distribution", "交易盈亏分布", {"type": "value", "data": []}, [],
                              subtitle="暂无交易数据")

    hist, bin_edges = np.histogram(trade_pnls, bins=20)
    bin_centers = [round((bin_edges[i] + bin_edges[i + 1]) / 2, 2) for i in range(len(hist))]
    hist_data = [int(h) for h in hist]

    cum_pnl = np.cumsum(trade_pnls)
    cum_x = list(range(1, len(cum_pnl) + 1))

    series = [{
        "name": "盈亏分布",
        "type": "bar",
        "data": hist_data,
        "xAxisData": [str(c) for c in bin_centers],
        "itemStyle": {
            "color": "rgba(74,144,217,0.7)",
            "borderColor": "#6ab0ff",
            "borderWidth": 1,
        },
    }, {
        "name": "累计盈亏",
        "type": "line",
        "data": [round(c, 2) for c in cum_pnl.tolist()],
        "xAxisData": [str(i) for i in cum_x],
        "smooth": False,
        "symbol": "none",
        "lineStyle": {"color": "#ffa502", "width": 2},
        "yAxisIndex": 1,
    }]

    return _make_response(
        "pnl_distribution", "交易盈亏分布",
        {"type": "value", "data": [str(c) for c in bin_centers]},
        series,
        subtitle=f"交易笔数: {len(trade_pnls)} | 平均盈利: {np.mean([p for p in trade_pnls if p > 0] or [0]):.2f} | 平均亏损: {np.mean([p for p in trade_pnls if p <= 0] or [0]):.2f}",
        annotations=[{
            "type": "zero_line",
            "x": "0",
            "text": "盈亏分界线",
        }],
    )


def build_returns_bar(result: BacktestResult, freq: str = "daily") -> dict:
    eq_df = pd.DataFrame(result.equity_curve)
    if eq_df.empty or len(eq_df) < 2:
        return _make_response(f"{freq}_returns", f"{'日' if freq == 'daily' else '周' if freq == 'weekly' else '月'}收益率",
                              {"type": "category", "data": []}, [], subtitle="数据不足")

    eq_df["timestamp"] = pd.to_datetime(eq_df["timestamp"])
    eq_df.set_index("timestamp", inplace=True)
    returns = eq_df["equity"].pct_change().dropna()

    freq_map = {"daily": "D", "weekly": "W", "monthly": "M"}
    freq_label = {"daily": "日", "weekly": "周", "monthly": "月"}

    resampled = returns.resample(freq_map[freq]).sum()
    labels = [r.strftime("%Y-%m-%d") if freq == "daily" else
              r.strftime("%Y-W%W") if freq == "weekly" else
              r.strftime("%Y-%m") for r in resampled.index]
    values = [(v * 100).round(4) for v in resampled.values]

    colors = ["#00d4aa" if v >= 0 else "#ff4757" for v in values]

    return _make_response(
        f"{freq}_returns", f"{freq_label[freq]}收益率",
        {"type": "category", "data": labels},
        [{
            "name": f"{freq_label[freq]}收益率",
            "type": "bar",
            "data": values,
            "itemStyle": {"color": "transparent",
                          "borderColor": "sourceData",
                          "decal": {"symbol": "none"}},
            "_colors": colors,
        }],
        subtitle=f"平均{freq_label[freq]}收益率: {np.mean(values):.4f}% | 标准差: {np.std(values):.4f}%",
    )


def build_kline_chart(ohlcv_df: pd.DataFrame, symbol: str = "BTC/USDT") -> dict:
    if ohlcv_df.empty:
        return _make_response("kline", "K线走势", {"type": "datetime", "data": []}, [])

    df = ohlcv_df.iloc[::max(1, len(ohlcv_df) // 240)]
    dates = [d.strftime("%Y-%m-%d %H:%M") if hasattr(d, "strftime") else str(d)
             for d in df.index]

    ohlc_data = []
    vol_data = []
    for idx, (_, row) in enumerate(df.iterrows()):
        ohlc_data.append([
            round(float(row["open"]), 2),
            round(float(row["close"]), 2),
            round(float(row["low"]), 2),
            round(float(row["high"]), 2),
        ])
        vol_data.append(round(float(row["volume"]), 2))

    return _make_response(
        "kline", f"K线走势 - {symbol}",
        {"type": "category", "data": dates},
        [
            {
                "name": "K线",
                "type": "candlestick",
                "data": ohlc_data,
                "itemStyle": {
                    "color": "#00d4aa",
                    "color0": "#ff4757",
                    "borderColor": "#00d4aa",
                    "borderColor0": "#ff4757",
                },
            },
            {
                "name": "成交量",
                "type": "bar",
                "data": vol_data,
                "yAxisIndex": 1,
                "itemStyle": {
                    "color": "rgba(74,74,106,0.6)",
                    "borderColor": "rgba(74,74,106,0.6)",
                },
            },
        ],
        subtitle=f"数据点: {len(dates)} | O: {round(float(df['open'].iloc[0]), 2)} C: {round(float(df['close'].iloc[-1]), 2)}",
    )


def build_compare_charts(days: int = 60, capital: float = 10000) -> dict:
    results = {}
    for sid, info in STRATEGY_MAP.items():
        from dashboard.common import generate_sample_data
        strat = info["cls"]()
        strat.set_param("symbol", "BTC/USDT")
        df = generate_sample_data(days)
        engine = BacktestEngine(strat, df, initial_capital=capital)
        results[sid] = engine.run()

    compare_list = []
    for sid, r in results.items():
        compare_list.append({
            "id": sid,
            "name": STRATEGY_MAP[sid]["name"],
            "total_return_pct": round(r.total_return_pct, 2),
            "sharpe_ratio": round(r.sharpe_ratio, 2),
            "max_drawdown_pct": round(r.max_drawdown_pct, 2),
            "win_rate": round(r.win_rate, 1),
            "profit_factor": round(r.profit_factor, 2),
            "total_trades": r.total_trades,
        })

    names = [c["name"] for c in compare_list]

    charts = {
        "compare_list": compare_list,
    }

    charts["return_bar"] = _make_response(
        "compare_return", "策略收益率对比",
        {"type": "category", "data": names},
        [{
            "name": "总收益率",
            "type": "bar",
            "data": [round(c["total_return_pct"], 2) for c in compare_list],
            "itemStyle": {"color": "transparent"},
            "_colors": ["#00d4aa" if c["total_return_pct"] >= 0 else "#ff4757" for c in compare_list],
            "label": {"show": True, "position": "top",
                      "formatter": "sourceData"},
        }],
        subtitle="各策略总收益对比",
    )

    charts["sharpe_bar"] = _make_response(
        "compare_sharpe", "夏普比率对比",
        {"type": "category", "data": names},
        [{
            "name": "夏普比率",
            "type": "bar",
            "data": [round(c["sharpe_ratio"], 2) for c in compare_list],
            "itemStyle": {"color": "#4a90d9"},
            "label": {"show": True, "position": "top",
                      "formatter": "sourceData"},
        }],
        subtitle="各策略夏普比率对比",
    )

    eq_series = []
    for sid, r in results.items():
        eq_df = pd.DataFrame(r.equity_curve)
        if not eq_df.empty:
            eq_series.append({
                "name": STRATEGY_MAP[sid]["name"],
                "type": "line",
                "data": [round(e, 4) for e in eq_df["equity"].tolist()],
                "smooth": True,
                "symbol": "none",
            })

    charts["equity_lines"] = _make_response(
        "compare_equity", "多策略权益曲线对比",
        {"type": "datetime",
         "data": [e["timestamp"].isoformat() if hasattr(e["timestamp"], "isoformat") else str(e["timestamp"])
                  for e in results[list(results.keys())[0]].equity_curve]},
        eq_series,
        subtitle="初始资金: $" + str(capital),
    )

    charts["winrate_bar"] = _make_response(
        "compare_winrate", "胜率对比",
        {"type": "category", "data": names},
        [{
            "name": "胜率",
            "type": "bar",
            "data": [round(c["win_rate"], 1) for c in compare_list],
            "itemStyle": {"color": "#00d4aa"},
            "label": {"show": True, "position": "top",
                      "formatter": "sourceData"},
        }],
        subtitle="各策略胜率对比 (%)",
    )

    charts["mdd_bar"] = _make_response(
        "compare_maxdd", "最大回撤对比",
        {"type": "category", "data": names},
        [{
            "name": "最大回撤",
            "type": "bar",
            "data": [round(c["max_drawdown_pct"], 2) for c in compare_list],
            "itemStyle": {"color": "#ff4757"},
            "label": {"show": True, "position": "top",
                      "formatter": "sourceData"},
        }],
        subtitle="各策略最大回撤对比 (%)",
    )

    return charts


def build_risk_charts(result: BacktestResult) -> dict:
    eq_df = pd.DataFrame(result.equity_curve)
    if eq_df.empty:
        return {"drawdown_chart": {}, "return_dist_chart": {}, "rolling_sharpe_chart": {}}

    eq_df["timestamp"] = pd.to_datetime(eq_df["timestamp"])
    eq_df.set_index("timestamp", inplace=True)
    eq_df["returns"] = eq_df["equity"].pct_change()
    eq_df["drawdown_pct"] = (eq_df["equity"] - eq_df["equity"].cummax()) / eq_df["equity"].cummax() * 100

    daily_returns = eq_df["returns"].dropna().resample("D").sum()
    var_95 = daily_returns.quantile(0.05) if len(daily_returns) > 0 else 0
    cvar_95 = daily_returns[daily_returns <= var_95].mean() if len(daily_returns) > 0 and var_95 < 0 else 0
    volatility = daily_returns.std() * np.sqrt(365) * 100 if len(daily_returns) > 1 else 0
    sortino = (daily_returns.mean() / daily_returns[daily_returns < 0].std() * np.sqrt(365)) \
        if len(daily_returns[daily_returns < 0]) > 1 else 0
    calmar = (result.total_return_pct / result.max_drawdown_pct) if result.max_drawdown_pct > 0 else 0

    risk_metrics = [
        {"metric": "最大回撤", "value": f"-{result.max_drawdown_pct:.2f}%"},
        {"metric": "VaR (95%)", "value": f"{var_95 * 100:.2f}%"},
        {"metric": "CVaR / 期望损失 (95%)", "value": f"{cvar_95 * 100:.2f}%"},
        {"metric": "年化波动率", "value": f"{volatility:.2f}%"},
        {"metric": "夏普比率", "value": f"{result.sharpe_ratio:.2f}"},
        {"metric": "Sortino比率", "value": f"{sortino:.2f}"},
        {"metric": "Calmar比率", "value": f"{calmar:.2f}"},
        {"metric": "日均收益率", "value": f"{daily_returns.mean() * 100:.4f}%"},
        {"metric": "日均波动率", "value": f"{daily_returns.std() * 100:.4f}%"},
        {"metric": "最大单日亏损", "value": f"{daily_returns.min() * 100:.2f}%"},
        {"metric": "最大单日盈利", "value": f"{daily_returns.max() * 100:.2f}%"},
        {"metric": "正收益天数占比", "value": f"{(daily_returns > 0).mean() * 100:.1f}%"},
    ]

    charts = {
        "summary": {
            "max_drawdown_pct": round(result.max_drawdown_pct, 2),
            "var_95": round(var_95 * 100, 2),
            "cvar_95": round(cvar_95 * 100, 2),
            "volatility": round(volatility, 2),
        },
        "risk_metrics": risk_metrics,
    }

    charts["drawdown_chart"] = build_drawdown(result)

    returns = eq_df["returns"].dropna()
    if len(returns) > 0:
        hist, bin_edges = np.histogram(returns * 100, bins=50)
        bin_centers = [round((bin_edges[i] + bin_edges[i + 1]) / 2, 4) for i in range(len(hist))]
        charts["return_dist_chart"] = _make_response(
            "return_distribution", "收益率分布",
            {"type": "value", "data": [str(c) for c in bin_centers]},
            [{
                "name": "频次",
                "type": "bar",
                "data": [int(h) for h in hist],
                "itemStyle": {"color": "rgba(74,144,217,0.7)", "borderColor": "#6ab0ff", "borderWidth": 1},
            }],
            subtitle=f"均值: {returns.mean() * 100:.4f}%  偏度: {returns.skew():.2f}",
            annotations=[{"type": "mean_line", "x": str(round(returns.mean() * 100, 4)),
                          "text": f"均值: {returns.mean() * 100:.4f}%"}],
        )
    else:
        charts["return_dist_chart"] = {}

    if len(returns) > 30:
        rolling_sharpe = returns.rolling(30).mean() / returns.rolling(30).std() * np.sqrt(365 * 24)
        valid = rolling_sharpe[30:]
        charts["rolling_sharpe_chart"] = _make_response(
            "rolling_sharpe", "滚动夏普比率",
            {"type": "datetime", "data": [d.isoformat() if hasattr(d, "isoformat") else str(d) for d in valid.index]},
            [{
                "name": "滚动夏普",
                "type": "line",
                "data": [round(v, 4) for v in valid.values],
                "symbol": "none",
                "lineStyle": {"color": "#ffa502", "width": 1.5},
                "markLine": {"data": [{"yAxis": 1, "label": {"formatter": "夏普=1"}, "lineStyle": {"color": "#00d4aa"}},
                                      {"yAxis": 0, "label": {"formatter": "夏普=0"}, "lineStyle": {"color": "#888"}}]},
            }],
            subtitle=f"窗口: 30期 | 滚动夏普均值: {valid.mean():.2f}",
        )
    else:
        charts["rolling_sharpe_chart"] = {}

    return charts


def _lttb_downsample(x_data: list, y_data: list, threshold: int) -> tuple:
    if len(y_data) <= threshold:
        return x_data, y_data

    n = len(y_data)
    bucket_size = (n - 2) / (threshold - 2)

    result_x = [x_data[0]]
    result_y = [y_data[0]]

    for i in range(1, threshold - 1):
        start_idx = int((i - 1) * bucket_size) + 1
        end_idx = int(i * bucket_size) + 1
        if start_idx >= end_idx:
            continue

        max_area = -1.0
        max_idx = start_idx
        prev_y = y_data[int((i - 1) * bucket_size)]
        _avg_x = (float(start_idx) + float(end_idx - 1)) / 2
        _avg_y = sum(y_data[start_idx:end_idx]) / (end_idx - start_idx)

        for j in range(start_idx, end_idx):
            area = abs((prev_y - y_data[j]) * (j - int((i - 1) * bucket_size)))
            if area > max_area:
                max_area = area
                max_idx = j

        result_x.append(x_data[max_idx])
        result_y.append(y_data[max_idx])

    result_x.append(x_data[-1])
    result_y.append(y_data[-1])

    return result_x, result_y