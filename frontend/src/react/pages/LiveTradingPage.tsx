import React, { useState, useEffect, useCallback } from 'react';
import PlotlyChart from '../components/PlotlyChart';

const LiveTradingPage: React.FC = () => {
  const [strategy, setStrategy] = useState('ma_cross');
  const [symbol, setSymbol] = useState('BTC/USDT');
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`/api/live?strategy=${strategy}`);
      const json = await res.json();
      setData(json);
    } catch (e) { console.error('Failed to load live data:', e); }
    finally { setLoading(false); }
  }, [strategy]);

  useEffect(() => { loadData(); }, [loadData]);

  const priceData = data?.price_chart ? [{
    x: data.price_chart.map((p: any) => p.time),
    y: data.price_chart.map((p: any) => p.price),
    type: 'scatter', mode: 'lines', line: { color: '#00d4aa' },
  }] : [];

  return (
    <div className="page-container">
      <h1 className="page-header">🔄 实时交易</h1>
      <div className="controls">
        <label>策略</label>
        <select value={strategy} onChange={e => setStrategy(e.target.value)}>
          <option value="ma_cross">MA Cross</option><option value="rsi">RSI</option>
          <option value="grid">Grid</option><option value="macd">MACD</option>
        </select>
        <label>交易对</label>
        <select value={symbol} onChange={e => setSymbol(e.target.value)}>
          <option value="BTC/USDT">BTC/USDT</option><option value="ETH/USDT">ETH/USDT</option>
        </select>
        <button className="btn btn-primary" onClick={loadData} disabled={loading}>🔄 刷新</button>
      </div>
      {data && (<>
        <div className="metrics-row">
          <div className="metric-card"><div className="metric-label">当前价格</div><div className="metric-value">${data.metrics?.price?.toLocaleString()}</div></div>
          <div className="metric-card"><div className="metric-label">24h涨跌</div><div className={`metric-value ${data.metrics?.change_24h >= 0 ? 'positive' : 'negative'}`}>{data.metrics?.change_24h}%</div></div>
          <div className="metric-card"><div className="metric-label">今日盈亏</div><div className={`metric-value ${data.metrics?.pnl_today >= 0 ? 'positive' : 'negative'}`}>${data.metrics?.pnl_today}</div></div>
          <div className="metric-card"><div className="metric-label">持仓</div><div className="metric-value">{data.metrics?.position || '空仓'}</div></div>
        </div>
        <div className="charts-row">
          <div className="chart-box chart-full"><h2>📈 实时价格</h2><PlotlyChart data={priceData} /></div>
        </div>
        {data.trades && (
          <table className="data-table">
            <thead><tr><th>时间</th><th>交易对</th><th>方向</th><th>价格</th><th>数量</th><th>盈亏</th></tr></thead>
            <tbody>{data.trades.map((t: any, i: number) => (
              <tr key={i}><td>{t.timestamp}</td><td>{t.symbol}</td>
              <td className={t.side === 'buy' ? 'positive' : 'negative'}>{t.side.toUpperCase()}</td>
              <td>${t.price?.toLocaleString()}</td><td>{t.amount}</td>
              <td className={t.pnl >= 0 ? 'positive' : 'negative'}>${t.pnl?.toFixed(2)}</td></tr>
            ))}</tbody>
          </table>
        )}
      </>)}
    </div>
  );
};

export default LiveTradingPage;
