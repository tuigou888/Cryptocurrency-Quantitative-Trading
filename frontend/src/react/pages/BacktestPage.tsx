import React, { useState, useEffect, useCallback } from 'react';
import PlotlyChart from '../components/PlotlyChart';

interface BacktestPageProps {}

const STRATEGY_PARAMS: Record<string, Array<{ key: string; label: string; type: string; min?: number; max?: number; step?: number }>> = {
  ma_cross: [
    { key: 'fast_period', label: '快速均线周期', type: 'number', min: 5, max: 50 },
    { key: 'slow_period', label: '慢速均线', type: 'number', min: 20, max: 100 },
  ],
  rsi: [
    { key: 'period', label: 'RSI周期', type: 'number', min: 7, max: 21 },
    { key: 'oversold', label: '超卖阈值', type: 'number', min: 20, max: 40 },
    { key: 'overbought', label: '超买阈值', type: 'number', min: 60, max: 80 },
  ],
  grid: [
    { key: 'grid_num', label: '网格数量', type: 'number', min: 5, max: 20 },
    { key: 'grid_range_pct', label: '价格范围%', type: 'number', step: 0.01, min: 0.01, max: 0.2 },
    { key: 'amount_per_grid', label: '每格数量', type: 'number', step: 0.001, min: 0.001 },
  ],
  macd: [
    { key: 'fast_period', label: '快线', type: 'number', min: 6, max: 20 },
    { key: 'slow_period', label: '慢线', type: 'number', min: 20, max: 40 },
    { key: 'signal_period', label: '信号', type: 'number', min: 5, max: 15 },
  ],
};

const BacktestPage: React.FC<BacktestPageProps> = () => {
  const [strategy, setStrategy] = useState('ma_cross');
  const [params, setParams] = useState<Record<string, any>>({ fast_period: 10, slow_period: 30 });
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [days, setDays] = useState(180);
  const [capital, setCapital] = useState(10000);

  const handleParamChange = (key: string, value: any) => {
    setParams(prev => ({ ...prev, [key]: value }));
  };

  const runBacktest = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/backtest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ strategy, symbol: 'BTC/USDT', days, capital, commission: 0.001, slippage: 0.0005, params }),
      });
      const data = await res.json();
      setResult(data);
    } catch (e) { console.error('Backtest failed:', e); }
    finally { setLoading(false); }
  }, [strategy, params, days, capital]);

  const equityChartData = result?.equity_curve ? [{
    x: result.equity_curve.map((p: any) => p.date),
    y: result.equity_curve.map((p: any) => p.equity),
    type: 'scatter', mode: 'lines', fill: 'tozeroy',
    line: { color: '#00d4aa' }, fillcolor: 'rgba(0, 212, 170, 0.08)',
  }] : [];

  const drawdownData = result?.drawdown_chart ? [{
    x: result.drawdown_chart.map((p: any) => p.date),
    y: result.drawdown_chart.map((p: any) => p.drawdown),
    type: 'scatter', mode: 'lines', fill: 'tozeroy',
    line: { color: '#ff4757' },
  }] : [];

  return (
    <div className="page-container">
      <h1 className="page-header">📈 回测分析</h1>
      <div className="controls">
        <label>策略</label>
        <select value={strategy} onChange={e => { setStrategy(e.target.value); setParams({}); }}>
          <option value="ma_cross">MA均线交叉</option>
          <option value="rsi">RSI超买超卖</option>
          <option value="grid">网格交易</option>
          <option value="macd">MACD动量</option>
        </select>
        <label>天数</label>
        <input type="number" value={days} onChange={e => setDays(Number(e.target.value))} min={30} max={365} />
        <label>资金</label>
        <input type="number" value={capital} onChange={e => setCapital(Number(e.target.value))} min={100} />
        <button className="btn btn-primary" onClick={runBacktest} disabled={loading}>{loading ? '⏳ 运行中...' : '🚀 运行回测'}</button>
      </div>
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 12 }}>
        {STRATEGY_PARAMS[strategy]?.map(p => (
          <div key={p.key} style={{ display: 'inline-flex', alignItems: 'center' }}>
            <label style={{ marginRight: 4 }}>{p.label}</label>
            <input type={p.type} value={params[p.key] ?? ''} onChange={e => handleParamChange(p.key, p.type === 'number' ? Number(e.target.value) : e.target.value)} min={p.min} max={p.max} step={p.step || 1} style={{ width: 80 }} />
          </div>
        ))}
      </div>
      {result && (<>
        <div className="metrics-row">
          <div className="metric-card"><div className="metric-label">总收益率</div><div className={`metric-value ${result.metrics.total_return >= 0 ? 'positive' : 'negative'}`}>{result.metrics.total_return}%</div></div>
          <div className="metric-card"><div className="metric-label">年化收益</div><div className="metric-value">{result.metrics.annualized_return}%</div></div>
          <div className="metric-card"><div className="metric-label">夏普比率</div><div className="metric-value">{result.metrics.sharpe_ratio}</div></div>
          <div className="metric-card"><div className="metric-label">最大回撤</div><div className="metric-value negative">{result.metrics.max_drawdown}%</div></div>
          <div className="metric-card"><div className="metric-label">胜率</div><div className="metric-value">{result.metrics.win_rate}%</div></div>
        </div>
        <div className="charts-row">
          <div className="chart-box"><h2>权益曲线</h2><PlotlyChart data={equityChartData} /></div>
          <div className="chart-box"><h2>回撤曲线</h2><PlotlyChart data={drawdownData} /></div>
        </div>
        {result.trades && result.trades.length > 0 && (
          <table className="data-table">
            <thead><tr><th>入场日期</th><th>出场日期</th><th>方向</th><th>入场价</th><th>出场价</th><th>盈亏</th></tr></thead>
            <tbody>{result.trades.map((t: any, i: number) => (
              <tr key={i}><td>{t.entry_date}</td><td>{t.exit_date}</td>
              <td className={t.side === 'long' ? 'positive' : 'negative'}>{t.side.toUpperCase()}</td>
              <td>${t.entry_price?.toLocaleString()}</td><td>${t.exit_price?.toLocaleString()}</td>
              <td className={t.pnl >= 0 ? 'positive' : 'negative'}>${t.pnl?.toFixed(2)}</td></tr>
            ))}</tbody>
          </table>
        )}
      </>)}
    </div>
  );
};

export default BacktestPage;
