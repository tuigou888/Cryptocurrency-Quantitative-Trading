import React, { useState, useEffect, useCallback } from 'react';
import PlotlyChart from '../components/PlotlyChart';

const LiveTradingPage: React.FC = () => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/live');
      const json = await res.json();
      setData(json);
    } catch (e) { console.error('Failed to load live data:', e); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const m = data?.metrics;

  return (
    <div className="page-container">
      <h1 className="page-header">🔄 实时交易</h1>
      <div className="controls">
        <button className="btn btn-primary" onClick={loadData} disabled={loading}>🔄 刷新</button>
        <span style={{ marginLeft: 12, color: '#888', fontSize: 13 }}>当前显示 MA Cross 策略模拟数据</span>
      </div>
      {data && (<>
        <div className="metrics-row">
          <div className="metric-card"><div className="metric-label">最终资金</div><div className="metric-value">${m?.final_capital?.toLocaleString()}</div></div>
          <div className="metric-card"><div className="metric-label">收益率</div><div className={`metric-value ${(m?.total_return_pct ?? 0) >= 0 ? 'positive' : 'negative'}`}>{m?.total_return_pct}%</div></div>
          <div className="metric-card"><div className="metric-label">夏普比率</div><div className="metric-value">{m?.sharpe_ratio}</div></div>
          <div className="metric-card"><div className="metric-label">交易次数</div><div className="metric-value">{m?.total_trades}</div></div>
        </div>
        <div className="charts-row">
          <div className="chart-box chart-full"><h2>📈 实时价格</h2><PlotlyChart chart={data.price_chart} style={{ height: 400 }} /></div>
        </div>
        {data.trades && data.trades.length > 0 && (
          <table className="data-table">
            <thead><tr><th>ID</th><th>方向</th><th>入场价</th><th>出场价</th><th>入场时间</th><th>出场时间</th><th>盈亏</th></tr></thead>
            <tbody>{data.trades.map((t: any, i: number) => (
              <tr key={i}><td>{t.id}</td>
              <td className={t.side === 'long' ? 'positive' : 'negative'}>{t.side?.toUpperCase()}</td>
              <td>${t.entry_price?.toLocaleString()}</td>
              <td>${t.exit_price?.toLocaleString()}</td>
              <td>{t.entry_time}</td><td>{t.exit_time}</td>
              <td className={t.pnl >= 0 ? 'positive' : 'negative'}>${t.pnl?.toFixed(2)}</td></tr>
            ))}</tbody>
          </table>
        )}
      </>)}
      {!data && !loading && (
        <div style={{ padding: 40, textAlign: 'center', color: '#888' }}>
          <p>暂无交易数据</p>
          <button className="btn btn-primary" onClick={loadData}>🔄 开始加载</button>
        </div>
      )}
    </div>
  );
};

export default LiveTradingPage;