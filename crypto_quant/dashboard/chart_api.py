import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import logging
from flask import Blueprint, jsonify, request

from dashboard.chart_service import (
    build_equity_curve,
    build_drawdown,
    build_monthly_returns_heatmap,
    build_pnl_distribution,
    build_returns_bar,
    build_kline_chart,
    build_compare_charts,
    build_risk_charts,
    _lttb_downsample,
)
from dashboard.common import run_backtest, fetch_real_market_data, generate_sample_data

logger = logging.getLogger(__name__)

chart_bp = Blueprint("chart_v1", __name__, url_prefix="/api/v1/charts")


@chart_bp.route("/equity_curve")
def api_equity_curve():
    strategy_id = request.args.get("strategy_id", "ma_cross")
    days = int(request.args.get("days", 60))
    capital = int(request.args.get("capital", 10000))
    downsample = int(request.args.get("downsample", 0))

    result, _ = run_backtest(strategy_id, days, capital)
    data = build_equity_curve(result, initial_capital=capital)

    if downsample > 0 and data["data"]["series"]:
        for s in data["data"]["series"]:
            if len(s.get("data", [])) > downsample:
                x = data["data"]["x_axis"]["data"]
                y = s["data"]
                new_x, new_y = _lttb_downsample(x, y, downsample)
                s["data"] = new_y
                if s == data["data"]["series"][0]:
                    data["data"]["x_axis"]["data"] = new_x

    return jsonify(data)


@chart_bp.route("/drawdown")
def api_drawdown():
    strategy_id = request.args.get("strategy_id", "ma_cross")
    days = int(request.args.get("days", 60))
    capital = int(request.args.get("capital", 10000))

    result, _ = run_backtest(strategy_id, days, capital)
    return jsonify(build_drawdown(result))


@chart_bp.route("/monthly_heatmap")
def api_monthly_heatmap():
    strategy_id = request.args.get("strategy_id", "ma_cross")
    days = int(request.args.get("days", 60))
    capital = int(request.args.get("capital", 10000))

    result, _ = run_backtest(strategy_id, days, capital)
    return jsonify(build_monthly_returns_heatmap(result))


@chart_bp.route("/pnl_distribution")
def api_pnl_distribution():
    strategy_id = request.args.get("strategy_id", "ma_cross")
    days = int(request.args.get("days", 60))
    capital = int(request.args.get("capital", 10000))

    result, _ = run_backtest(strategy_id, days, capital)
    return jsonify(build_pnl_distribution(result))


@chart_bp.route("/returns")
def api_returns():
    strategy_id = request.args.get("strategy_id", "ma_cross")
    days = int(request.args.get("days", 60))
    capital = int(request.args.get("capital", 10000))
    freq = request.args.get("freq", "daily")

    result, _ = run_backtest(strategy_id, days, capital)
    return jsonify(build_returns_bar(result, freq))


@chart_bp.route("/kline")
def api_kline():
    days = int(request.args.get("days", 60))
    symbol = request.args.get("symbol", "BTC/USDT")
    timeframe = request.args.get("timeframe", "1h")

    df = fetch_real_market_data(days, symbol, timeframe)
    return jsonify(build_kline_chart(df, symbol))


@chart_bp.route("/compare")
def api_compare():
    days = int(request.args.get("days", 60))
    capital = int(request.args.get("capital", 10000))

    charts = build_compare_charts(days, capital)
    return jsonify({"code": 0, "data": charts, "message": "ok"})


@chart_bp.route("/risk")
def api_risk():
    strategy_id = request.args.get("strategy_id", "ma_cross")
    days = int(request.args.get("days", 60))
    capital = int(request.args.get("capital", 10000))

    result, _ = run_backtest(strategy_id, days, capital)
    charts = build_risk_charts(result)
    return jsonify({"code": 0, "data": charts, "message": "ok"})


@chart_bp.route("/bundle")
def api_bundle():
    strategy_id = request.args.get("strategy_id", "ma_cross")
    days = int(request.args.get("days", 60))
    capital = int(request.args.get("capital", 10000))

    result, df = run_backtest(strategy_id, days, capital)

    bundle = {
        "metrics": {
            "total_return_pct": round(result.total_return_pct, 2),
            "sharpe_ratio": round(result.sharpe_ratio, 2),
            "max_drawdown_pct": round(result.max_drawdown_pct, 2),
            "win_rate": round(result.win_rate, 1),
            "profit_factor": round(result.profit_factor, 2),
            "total_trades": result.total_trades,
            "initial_capital": round(result.initial_capital, 2),
            "final_capital": round(result.final_capital, 2),
        },
        "equity_curve": build_equity_curve(result, initial_capital=capital)["data"],
        "drawdown": build_drawdown(result)["data"],
        "monthly_heatmap": build_monthly_returns_heatmap(result)["data"],
        "pnl_distribution": build_pnl_distribution(result)["data"],
        "kline": build_kline_chart(df)["data"],
        "trades": [],
    }

    for t in result.trades:
        bundle["trades"].append({
            "id": bundle["trades"].__len__() + 1,
            "side": t.side,
            "entry_time": str(t.entry_time),
            "exit_time": str(t.exit_time),
            "entry_price": round(t.entry_price, 2),
            "exit_price": round(t.exit_price, 2),
            "pnl": round(t.pnl, 2),
            "pnl_pct": round(t.pnl_pct, 2),
        })

    return jsonify({"code": 0, "data": bundle, "message": "ok"})