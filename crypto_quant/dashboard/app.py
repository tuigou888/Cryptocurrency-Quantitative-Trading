import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

from dashboard.common import (
    sidebar_nav, generate_sample_data, run_backtest_with_data,
    STRATEGY_MAP, metric_card,
)

page, exchange, symbol, timeframe, capital = sidebar_nav()

if page == "🏠 概览":
    st.title("🏠 量化交易概览")
    st.markdown("---")

    with st.spinner("正在运行回测生成数据..."):
        df = generate_sample_data(symbol, days=180)
        result = run_backtest_with_data("MA均线交叉", df, capital)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("总收益率", f"{result.total_return_pct:+.2f}%",
                   delta=f"${result.total_return:+,.2f}",
                   delta_color="normal" if result.total_return >= 0 else "inverse")
    with col2:
        st.metric("夏普比率", f"{result.sharpe_ratio:.2f}",
                   delta="优秀" if result.sharpe_ratio > 2 else ("良好" if result.sharpe_ratio > 1 else "一般"),
                   delta_color="normal")
    with col3:
        st.metric("最大回撤", f"-{result.max_drawdown_pct:.2f}%",
                   delta=f"-${result.max_drawdown:,.2f}",
                   delta_color="inverse")
    with col4:
        st.metric("胜率", f"{result.win_rate:.1f}%",
                   delta=f"{result.winning_trades}胜 / {result.losing_trades}负",
                   delta_color="normal" if result.win_rate >= 50 else "inverse")

    st.markdown("---")
    col5, col6, col7, col8 = st.columns(4)
    with col5:
        st.metric("盈利因子", f"{result.profit_factor:.2f}",
                   delta="盈利" if result.profit_factor > 1 else "亏损")
    with col6:
        st.metric("总交易次数", f"{result.total_trades}")
    with col7:
        st.metric("平均盈利", f"${result.avg_profit:,.2f}", delta_color="normal")
    with col8:
        st.metric("平均亏损", f"${result.avg_loss:,.2f}", delta_color="inverse")

    st.markdown("---")
    st.subheader("📈 权益曲线")
    equity_df = pd.DataFrame(result.equity_curve)
    if not equity_df.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=equity_df["timestamp"], y=equity_df["equity"],
            name="权益", line=dict(color="#00d4aa", width=2),
            fill="tozeroy", fillcolor="rgba(0,212,170,0.1)",
        ))
        fig.add_hline(y=capital, line_dash="dash", line_color="#ffa502",
                      annotation_text=f"初始资金 ${capital:,.0f}")
        fig.update_layout(
            xaxis_title="时间", yaxis_title="权益 (USDT)",
            template="plotly_dark", height=400,
            margin=dict(l=60, r=20, t=30, b=40),
        )
        st.plotly_chart(fig, use_container_width=True)

    col_left, col_right = st.columns(2)
    with col_left:
        st.subheader("📊 价格走势与信号")
        fig_price = make_subplots(rows=2, cols=1, shared_xaxes=True,
                                  vertical_spacing=0.03, row_heights=[0.7, 0.3])
        sample_df = df.iloc[::4]
        fig_price.add_trace(go.Candlestick(
            x=sample_df.index, open=sample_df["open"], high=sample_df["high"],
            low=sample_df["low"], close=sample_df["close"],
            name="K线", increasing_line_color="#00d4aa", decreasing_line_color="#ff4757",
        ), row=1, col=1)
        fig_price.add_trace(go.Bar(
            x=sample_df.index, y=sample_df["volume"],
            name="成交量", marker_color="#4a4a6a",
        ), row=2, col=1)
        fig_price.update_layout(
            template="plotly_dark", height=400,
            xaxis_rangeslider_visible=False,
            margin=dict(l=60, r=20, t=30, b=40),
        )
        st.plotly_chart(fig_price, use_container_width=True)

    with col_right:
        st.subheader("📊 月度收益分布")
        if not equity_df.empty and len(equity_df) > 24:
            equity_df["month"] = pd.to_datetime(equity_df["timestamp"]).dt.to_period("M")
            monthly = equity_df.groupby("month").agg(
                start=("equity", "first"), end=("equity", "last")
            )
            monthly["return_pct"] = (monthly["end"] - monthly["start"]) / monthly["start"] * 100
            monthly = monthly.reset_index()
            monthly["month_str"] = monthly["month"].astype(str)
            colors = ["#00d4aa" if r >= 0 else "#ff4757" for r in monthly["return_pct"]]
            fig_month = go.Figure(go.Bar(
                x=monthly["month_str"], y=monthly["return_pct"],
                marker_color=colors, text=[f"{r:+.1f}%" for r in monthly["return_pct"]],
                textposition="auto",
            ))
            fig_month.update_layout(
                template="plotly_dark", height=400,
                xaxis_title="月份", yaxis_title="收益率 (%)",
                margin=dict(l=60, r=20, t=30, b=40),
            )
            st.plotly_chart(fig_month, use_container_width=True)
        else:
            st.info("数据不足，无法计算月度收益")

elif page == "📈 回测分析":
    st.title("📈 回测分析")
    st.markdown("---")

    with st.sidebar:
        st.markdown("### 回测参数")
        bt_strategy = st.selectbox("策略", list(STRATEGY_MAP.keys()), index=0)
        bt_days = st.slider("回测天数", 30, 365, 180)
        bt_commission = st.slider("手续费率", 0.0, 0.005, 0.001, step=0.0001, format="%.4f")
        bt_slippage = st.slider("滑点", 0.0, 0.002, 0.0005, step=0.0001, format="%.4f")

        strategy_params = {}
        if bt_strategy == "MA均线交叉":
            strategy_params["fast_period"] = st.slider("快线周期", 5, 50, 10)
            strategy_params["slow_period"] = st.slider("慢线周期", 20, 200, 30)
        elif bt_strategy == "RSI超买超卖":
            strategy_params["period"] = st.slider("RSI周期", 5, 50, 14)
            strategy_params["oversold"] = st.slider("超卖阈值", 10, 40, 30)
            strategy_params["overbought"] = st.slider("超买阈值", 60, 90, 70)
        elif bt_strategy == "网格交易":
            strategy_params["grid_num"] = st.slider("网格数量", 5, 50, 10)
            strategy_params["grid_range_pct"] = st.slider("网格范围 (%)", 0.01, 0.2, 0.05, step=0.01)

    if st.button("🚀 运行回测", type="primary", use_container_width=True):
        with st.spinner("回测运行中..."):
            df = generate_sample_data(symbol, days=bt_days)
            from strategy.base import BaseStrategy
            strategy_cls = STRATEGY_MAP[bt_strategy]
            strat = strategy_cls(**strategy_params)
            strat.set_param("symbol", symbol)
            engine = BacktestEngine(strat, df, initial_capital=capital,
                                    commission=bt_commission, slippage=bt_slippage)
            result = engine.run()

        st.session_state["bt_result"] = result
        st.session_state["bt_df"] = df

    if "bt_result" in st.session_state:
        result = st.session_state["bt_result"]
        df = st.session_state["bt_df"]

        st.subheader(f"📋 回测结果 — {bt_strategy}")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("总收益率", f"{result.total_return_pct:+.2f}%")
        c2.metric("夏普比率", f"{result.sharpe_ratio:.2f}")
        c3.metric("最大回撤", f"-{result.max_drawdown_pct:.2f}%")
        c4.metric("胜率", f"{result.win_rate:.1f}%")
        c5.metric("盈利因子", f"{result.profit_factor:.2f}")

        c6, c7, c8, c9, c10 = st.columns(5)
        c6.metric("初始资金", f"${result.initial_capital:,.0f}")
        c7.metric("最终资金", f"${result.final_capital:,.0f}")
        c8.metric("总交易", f"{result.total_trades}")
        c9.metric("平均盈利", f"${result.avg_profit:,.2f}")
        c10.metric("平均亏损", f"${result.avg_loss:,.2f}")

        st.markdown("---")
        col_eq, col_dd = st.columns(2)
        with col_eq:
            st.subheader("权益曲线")
            eq_df = pd.DataFrame(result.equity_curve)
            if not eq_df.empty:
                fig_eq = go.Figure()
                fig_eq.add_trace(go.Scatter(
                    x=eq_df["timestamp"], y=eq_df["equity"],
                    name="权益", line=dict(color="#00d4aa", width=2),
                    fill="tozeroy", fillcolor="rgba(0,212,170,0.08)",
                ))
                fig_eq.add_hline(y=capital, line_dash="dash", line_color="#ffa502")
                fig_eq.update_layout(template="plotly_dark", height=350,
                                     xaxis_title="时间", yaxis_title="权益 (USDT)",
                                     margin=dict(l=60, r=20, t=30, b=40))
                st.plotly_chart(fig_eq, use_container_width=True)

        with col_dd:
            st.subheader("回撤曲线")
            if not eq_df.empty:
                eq_df["drawdown"] = (eq_df["equity"] - eq_df["equity"].cummax()) / eq_df["equity"].cummax() * 100
                fig_dd = go.Figure()
                fig_dd.add_trace(go.Scatter(
                    x=eq_df["timestamp"], y=eq_df["drawdown"],
                    name="回撤", line=dict(color="#ff4757", width=1.5),
                    fill="tozeroy", fillcolor="rgba(255,71,87,0.15)",
                ))
                fig_dd.update_layout(template="plotly_dark", height=350,
                                     xaxis_title="时间", yaxis_title="回撤 (%)",
                                     margin=dict(l=60, r=20, t=30, b=40))
                st.plotly_chart(fig_dd, use_container_width=True)

        st.markdown("---")
        col_pnl, col_dist = st.columns(2)
        with col_pnl:
            st.subheader("累计盈亏")
            if result.trades:
                trade_pnls = [t.pnl for t in result.trades]
                cum_pnl = np.cumsum(trade_pnls)
                fig_pnl = go.Figure()
                fig_pnl.add_trace(go.Bar(
                    x=list(range(1, len(trade_pnls) + 1)),
                    y=trade_pnls,
                    name="单笔盈亏",
                    marker_color=["#00d4aa" if p >= 0 else "#ff4757" for p in trade_pnls],
                ))
                fig_pnl.add_trace(go.Scatter(
                    x=list(range(1, len(cum_pnl) + 1)),
                    y=cum_pnl,
                    name="累计盈亏",
                    line=dict(color="#ffa502", width=2),
                    yaxis="y2",
                ))
                fig_pnl.update_layout(
                    template="plotly_dark", height=350,
                    yaxis2=dict(overlaying="y", side="right"),
                    margin=dict(l=60, r=60, t=30, b=40),
                    barmode="group",
                )
                st.plotly_chart(fig_pnl, use_container_width=True)

        with col_dist:
            st.subheader("盈亏分布")
            if result.trades:
                trade_pnls = [t.pnl for t in result.trades]
                fig_dist = go.Figure()
                fig_dist.add_trace(go.Histogram(
                    x=trade_pnls, nbinsx=20,
                    marker_color="#4a90d9",
                    marker_line_color="#6ab0ff",
                ))
                fig_dist.add_vline(x=0, line_dash="dash", line_color="#ffa502")
                fig_dist.update_layout(
                    template="plotly_dark", height=350,
                    xaxis_title="盈亏 (USDT)", yaxis_title="频次",
                    margin=dict(l=60, r=20, t=30, b=40),
                )
                st.plotly_chart(fig_dist, use_container_width=True)

        st.markdown("---")
        st.subheader("📝 交易明细")
        if result.trades:
            trade_rows = []
            for i, t in enumerate(result.trades):
                trade_rows.append({
                    "序号": i + 1,
                    "方向": t.side,
                    "入场时间": t.entry_time,
                    "出场时间": t.exit_time,
                    "入场价": f"${t.entry_price:,.2f}",
                    "出场价": f"${t.exit_price:,.2f}",
                    "数量": f"{t.amount:.6f}",
                    "盈亏": f"${t.pnl:+,.2f}",
                    "收益率": f"{t.pnl_pct:+.2f}%",
                    "手续费": f"${t.commission:,.2f}",
                })
            st.dataframe(pd.DataFrame(trade_rows), use_container_width=True, hide_index=True)
    else:
        st.info("👈 请在左侧设置参数后点击「运行回测」")

elif page == "💰 交易分析":
    st.title("💰 交易分析")
    st.markdown("---")

    with st.spinner("加载数据..."):
        df = generate_sample_data(symbol, days=180)
        results = {}
        for name in STRATEGY_MAP:
            results[name] = run_backtest_with_data(name, df, capital)

    st.subheader("📊 策略对比")
    compare_rows = []
    for name, r in results.items():
        compare_rows.append({
            "策略": name,
            "总收益率": f"{r.total_return_pct:+.2f}%",
            "夏普比率": f"{r.sharpe_ratio:.2f}",
            "最大回撤": f"-{r.max_drawdown_pct:.2f}%",
            "胜率": f"{r.win_rate:.1f}%",
            "盈利因子": f"{r.profit_factor:.2f}",
            "总交易": r.total_trades,
            "盈利交易": r.winning_trades,
            "亏损交易": r.losing_trades,
            "平均盈利": f"${r.avg_profit:,.2f}",
            "平均亏损": f"${r.avg_loss:,.2f}",
        })
    st.dataframe(pd.DataFrame(compare_rows), use_container_width=True, hide_index=True)

    st.markdown("---")
    col_bar1, col_bar2 = st.columns(2)
    with col_bar1:
        st.subheader("收益率对比")
        fig_cmp = go.Figure()
        fig_cmp.add_trace(go.Bar(
            x=list(results.keys()),
            y=[r.total_return_pct for r in results.values()],
            marker_color=["#00d4aa" if r.total_return_pct >= 0 else "#ff4757" for r in results.values()],
            text=[f"{r.total_return_pct:+.2f}%" for r in results.values()],
            textposition="auto",
        ))
        fig_cmp.update_layout(template="plotly_dark", height=350,
                              yaxis_title="收益率 (%)", margin=dict(l=60, r=20, t=30, b=40))
        st.plotly_chart(fig_cmp, use_container_width=True)

    with col_bar2:
        st.subheader("夏普比率对比")
        fig_sharpe = go.Figure()
        fig_sharpe.add_trace(go.Bar(
            x=list(results.keys()),
            y=[r.sharpe_ratio for r in results.values()],
            marker_color="#4a90d9",
            text=[f"{r.sharpe_ratio:.2f}" for r in results.values()],
            textposition="auto",
        ))
        fig_sharpe.update_layout(template="plotly_dark", height=350,
                                 yaxis_title="夏普比率", margin=dict(l=60, r=20, t=30, b=40))
        st.plotly_chart(fig_sharpe, use_container_width=True)

    st.markdown("---")
    st.subheader("📈 权益曲线对比")
    fig_all_eq = go.Figure()
    for name, r in results.items():
        eq_df = pd.DataFrame(r.equity_curve)
        if not eq_df.empty:
            fig_all_eq.add_trace(go.Scatter(
                x=eq_df["timestamp"], y=eq_df["equity"],
                name=name, line=dict(width=2),
            ))
    fig_all_eq.add_hline(y=capital, line_dash="dash", line_color="#ffa502",
                         annotation_text="初始资金")
    fig_all_eq.update_layout(template="plotly_dark", height=450,
                             xaxis_title="时间", yaxis_title="权益 (USDT)",
                             margin=dict(l=60, r=20, t=30, b=40))
    st.plotly_chart(fig_all_eq, use_container_width=True)

    col_radar1, col_radar2 = st.columns(2)
    with col_radar1:
        st.subheader("胜率与盈亏比")
        fig_wr = go.Figure()
        fig_wr.add_trace(go.Bar(
            x=list(results.keys()),
            y=[r.win_rate for r in results.values()],
            marker_color="#00d4aa",
            name="胜率 (%)",
        ))
        fig_wr.update_layout(template="plotly_dark", height=350,
                             yaxis_title="胜率 (%)", margin=dict(l=60, r=20, t=30, b=40))
        st.plotly_chart(fig_wr, use_container_width=True)

    with col_radar2:
        st.subheader("最大回撤对比")
        fig_mdd = go.Figure()
        fig_mdd.add_trace(go.Bar(
            x=list(results.keys()),
            y=[r.max_drawdown_pct for r in results.values()],
            marker_color="#ff4757",
            name="最大回撤 (%)",
        ))
        fig_mdd.update_layout(template="plotly_dark", height=350,
                              yaxis_title="最大回撤 (%)", margin=dict(l=60, r=20, t=30, b=40))
        st.plotly_chart(fig_mdd, use_container_width=True)

elif page == "⚠️ 风险分析":
    st.title("⚠️ 风险分析")
    st.markdown("---")

    with st.spinner("加载数据..."):
        df = generate_sample_data(symbol, days=180)
        result = run_backtest_with_data("MA均线交叉", df, capital)

    eq_df = pd.DataFrame(result.equity_curve)
    if not eq_df.empty:
        eq_df["returns"] = eq_df["equity"].pct_change()
        eq_df["drawdown"] = (eq_df["equity"] - eq_df["equity"].cummax()) / eq_df["equity"].cummax() * 100
        eq_df["peak"] = eq_df["equity"].cummax()

    col_r1, col_r2, col_r3, col_r4 = st.columns(4)
    with col_r1:
        st.metric("最大回撤", f"-{result.max_drawdown_pct:.2f}%")
    with col_r2:
        daily_returns = eq_df["returns"].dropna().resample("D").sum() if not eq_df.empty else pd.Series()
        var_95 = daily_returns.quantile(0.05) if len(daily_returns) > 0 else 0
        st.metric("VaR (95%)", f"{var_95*100:.2f}%")
    with col_r3:
        cvar_95 = daily_returns[daily_returns <= var_95].mean() if len(daily_returns) > 0 and var_95 < 0 else 0
        st.metric("CVaR (95%)", f"{cvar_95*100:.2f}%")
    with col_r4:
        volatility = daily_returns.std() * np.sqrt(365) * 100 if len(daily_returns) > 1 else 0
        st.metric("年化波动率", f"{volatility:.2f}%")

    st.markdown("---")
    col_dd_curve, col_dd_dist = st.columns(2)
    with col_dd_curve:
        st.subheader("📉 回撤曲线")
        fig_dd = go.Figure()
        fig_dd.add_trace(go.Scatter(
            x=eq_df["timestamp"], y=eq_df["drawdown"],
            fill="tozeroy", fillcolor="rgba(255,71,87,0.2)",
            line=dict(color="#ff4757", width=1.5), name="回撤",
        ))
        fig_dd.update_layout(template="plotly_dark", height=400,
                             xaxis_title="时间", yaxis_title="回撤 (%)",
                             margin=dict(l=60, r=20, t=30, b=40))
        st.plotly_chart(fig_dd, use_container_width=True)

    with col_dd_dist:
        st.subheader("回撤分布")
        fig_dd_hist = go.Figure()
        fig_dd_hist.add_trace(go.Histogram(
            x=eq_df["drawdown"].dropna(), nbinsx=30,
            marker_color="#ff6b81", marker_line_color="#ff4757",
        ))
        fig_dd_hist.update_layout(template="plotly_dark", height=400,
                                  xaxis_title="回撤 (%)", yaxis_title="频次",
                                  margin=dict(l=60, r=20, t=30, b=40))
        st.plotly_chart(fig_dd_hist, use_container_width=True)

    st.markdown("---")
    col_ret_dist, col_qq = st.columns(2)
    with col_ret_dist:
        st.subheader("收益率分布")
        returns = eq_df["returns"].dropna()
        if len(returns) > 0:
            fig_ret = go.Figure()
            fig_ret.add_trace(go.Histogram(
                x=returns * 100, nbinsx=50,
                marker_color="#4a90d9", marker_line_color="#6ab0ff",
                name="收益率",
            ))
            mean_ret = returns.mean() * 100
            fig_ret.add_vline(x=mean_ret, line_dash="dash", line_color="#ffa502",
                              annotation_text=f"均值: {mean_ret:.3f}%")
            fig_ret.add_vline(x=0, line_dash="dot", line_color="#888")
            fig_ret.update_layout(template="plotly_dark", height=400,
                                  xaxis_title="收益率 (%)", yaxis_title="频次",
                                  margin=dict(l=60, r=20, t=30, b=40))
            st.plotly_chart(fig_ret, use_container_width=True)

    with col_qq:
        st.subheader("滚动夏普比率")
        if len(returns) > 30:
            rolling_sharpe = returns.rolling(window=30).mean() / returns.rolling(window=30).std() * np.sqrt(365 * 24)
            fig_rs = go.Figure()
            fig_rs.add_trace(go.Scatter(
                x=returns.index[30:], y=rolling_sharpe[30:],
                line=dict(color="#ffa502", width=1.5), name="滚动夏普",
            ))
            fig_rs.add_hline(y=1, line_dash="dash", line_color="#00d4aa",
                             annotation_text="夏普=1")
            fig_rs.add_hline(y=0, line_dash="dot", line_color="#888")
            fig_rs.update_layout(template="plotly_dark", height=400,
                                 xaxis_title="时间", yaxis_title="夏普比率",
                                 margin=dict(l=60, r=20, t=30, b=40))
            st.plotly_chart(fig_rs, use_container_width=True)

    st.markdown("---")
    st.subheader("📋 风险指标汇总")
    risk_metrics = []
    if len(daily_returns) > 1:
        risk_metrics = [
            {"指标": "最大回撤", "值": f"-{result.max_drawdown_pct:.2f}%"},
            {"指标": "VaR (95%)", "值": f"{var_95*100:.2f}%"},
            {"指标": "CVaR / 期望损失 (95%)", "值": f"{cvar_95*100:.2f}%"},
            {"指标": "年化波动率", "值": f"{volatility:.2f}%"},
            {"指标": "夏普比率", "值": f"{result.sharpe_ratio:.2f}"},
            {"指标": "Sortino比率", "值": f"{(daily_returns.mean() / daily_returns[daily_returns<0].std() * np.sqrt(365)):.2f}" if len(daily_returns[daily_returns<0]) > 0 else "N/A"},
            {"指标": "Calmar比率", "值": f"{(result.total_return_pct / result.max_drawdown_pct):.2f}" if result.max_drawdown_pct > 0 else "N/A"},
            {"指标": "日均收益率", "值": f"{daily_returns.mean()*100:.4f}%"},
            {"指标": "日均波动率", "值": f"{daily_returns.std()*100:.4f}%"},
            {"指标": "最大单日亏损", "值": f"{daily_returns.min()*100:.2f}%"},
            {"指标": "最大单日盈利", "值": f"{daily_returns.max()*100:.2f}%"},
            {"指标": "正收益天数占比", "值": f"{(daily_returns > 0).mean()*100:.1f}%"},
        ]
    st.dataframe(pd.DataFrame(risk_metrics), use_container_width=True, hide_index=True)

elif page == "🔄 实时交易":
    st.title("🔄 实时交易")
    st.markdown("---")

    st.subheader("⚙️ 交易配置")
    col_t1, col_t2, col_t3 = st.columns(3)
    with col_t1:
        live_strategy = st.selectbox("策略", list(STRATEGY_MAP.keys()), key="live_strat")
        live_mode = st.toggle("模拟盘", value=True)
    with col_t2:
        live_market = st.selectbox("市场类型", ["spot", "swap"])
        live_leverage = st.slider("杠杆倍数", 1, 20, 1) if live_market == "swap" else 1
    with col_t3:
        if st.button("🚀 启动交易引擎", type="primary", use_container_width=True):
            st.session_state["engine_running"] = True
            st.success("交易引擎已启动！")
        if st.button("⏹️ 停止交易引擎", use_container_width=True):
            st.session_state["engine_running"] = False
            st.warning("交易引擎已停止")

    st.markdown("---")

    if st.session_state.get("engine_running"):
        st.subheader("📊 当前状态")
        with st.spinner("获取数据中..."):
            df = generate_sample_data(symbol, days=7)
            result = run_backtest_with_data(live_strategy, df, capital)

        col_s1, col_s2, col_s3, col_s4 = st.columns(4)
        col_s1.metric("当前权益", f"${result.final_capital:,.2f}",
                       delta=f"{result.total_return_pct:+.2f}%")
        col_s2.metric("持仓方向", "多仓" if result.total_trades > 0 else "空仓")
        col_s3.metric("未实现盈亏", f"${result.total_return:+,.2f}")
        col_s4.metric("运行模式", "模拟盘" if live_mode else "实盘")

        st.markdown("---")
        st.subheader("📈 实时价格")
        fig_live = go.Figure()
        fig_live.add_trace(go.Scatter(
            x=df.index, y=df["close"],
            line=dict(color="#00d4aa", width=2), name="价格",
        ))
        fig_live.update_layout(template="plotly_dark", height=400,
                               xaxis_title="时间", yaxis_title="价格 (USDT)",
                               margin=dict(l=60, r=20, t=30, b=40))
        st.plotly_chart(fig_live, use_container_width=True)

        st.subheader("📋 最近交易记录")
        if result.trades:
            trade_rows = []
            for i, t in enumerate(result.trades[-10:]):
                trade_rows.append({
                    "时间": t.exit_time or t.entry_time,
                    "方向": t.side,
                    "入场价": f"${t.entry_price:,.2f}",
                    "出场价": f"${t.exit_price:,.2f}" if t.exit_price else "-",
                    "盈亏": f"${t.pnl:+,.2f}",
                    "收益率": f"{t.pnl_pct:+.2f}%",
                })
            st.dataframe(pd.DataFrame(trade_rows), use_container_width=True, hide_index=True)
        else:
            st.info("暂无交易记录")

        st.subheader("⚠️ 风控状态")
        risk_config = settings.risk
        rc1, rc2, rc3, rc4 = st.columns(4)
        rc1.metric("最大仓位比例", f"{risk_config.get('max_position_size_pct', 0):.0%}")
        rc2.metric("止损线", f"-{risk_config.get('stop_loss_pct', 0):.1%}")
        rc3.metric("最大回撤限制", f"-{risk_config.get('max_drawdown_pct', 0):.1%}")
        rc4.metric("日损失限制", f"-{risk_config.get('max_daily_loss_pct', 0):.1%}")
    else:
        st.info("👈 请配置参数后点击「启动交易引擎」开始交易")
