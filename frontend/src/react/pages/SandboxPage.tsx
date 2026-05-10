import React, { useState, useEffect, useCallback } from 'react';
import { sandboxApi } from '../../shared/api';

const SandboxPage: React.FC = () => {
  const [configId, setConfigId] = useState('');
  const [balances, setBalances] = useState<any[]>([]);
  const [orders, setOrders] = useState<any[]>([]);
  const [positions, setPositions] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [orderForm, setOrderForm] = useState({ symbol: 'BTC/USDT', side: 'buy', price: '', amount: '' });

  const loadAll = useCallback(async () => {
    if (!configId) return;
    setLoading(true);
    try {
      const bal: any = await sandboxApi.getBalance(configId);
      setBalances(bal.balances || []);
      const pos: any = await sandboxApi.getPositions(configId);
      setPositions(pos.positions || []);
      const ord: any = await sandboxApi.getOrders(configId);
      setOrders(ord.orders || []);
    } catch (e) {
      console.error('Failed to load sandbox data:', e);
    } finally {
      setLoading(false);
    }
  }, [configId]);

  const placeOrder = async () => {
    try {
      await sandboxApi.placeOrder({ ...orderForm, config_id: configId });
      loadAll();
    } catch (e: any) {
      alert('下单失败: ' + (e.error || e.message));
    }
  };

  const cancelAll = async () => {
    if (confirm('确定取消所有挂单?')) {
      await sandboxApi.cancelAllOrders(configId);
      loadAll();
    }
  };

  useEffect(() => { loadAll(); }, [loadAll]);

  return (
    <div className="page-container">
      <h1 className="page-header">🧪 虚拟盘交易</h1>
      <div className="alert alert-warning">⚠️ 当前为虚拟盘模式，不会产生真实交易</div>
      <div className="controls">
        <label>交易所配置</label>
        <select value={configId} onChange={e => setConfigId(e.target.value)}>
          <option value="">请选择</option>
          <option value="binance_sandbox">Binance沙箱</option>
          <option value="okx_sandbox">OKX沙箱</option>
        </select>
        <button className="btn btn-primary" onClick={loadAll} disabled={!configId || loading}>🔄 加载账户</button>
      </div>
      {configId && (
        <>
          <div className="metrics-row">
            {balances.map((b, i) => (<div key={i} className="metric-card"><div className="metric-label">{b.asset}</div><div className="metric-value">{b.free?.toFixed(4)}</div><div className="metric-delta">可用</div></div>))}
          </div>
          <div className="form-grid">
            <div className="form-group"><label>交易对</label><select value={orderForm.symbol} onChange={e => setOrderForm({ ...orderForm, symbol: e.target.value })}><option value="BTC/USDT">BTC/USDT</option><option value="ETH/USDT">ETH/USDT</option></select></div>
            <div className="form-group"><label>方向</label><select value={orderForm.side} onChange={e => setOrderForm({ ...orderForm, side: e.target.value })}><option value="buy">买入</option><option value="sell">卖出</option></select></div>
            <div className="form-group"><label>价格</label><input type="number" value={orderForm.price} onChange={e => setOrderForm({ ...orderForm, price: e.target.value })} placeholder="留空为市价" /></div>
            <div className="form-group"><label>数量</label><input type="number" value={orderForm.amount} onChange={e => setOrderForm({ ...orderForm, amount: e.target.value })} placeholder="0.001" /></div>
          </div>
          <div style={{ marginTop: 12, display: 'flex', gap: 8 }}>
            <button className="btn btn-primary" onClick={placeOrder}>📤 下单</button>
            <button className="btn btn-danger" onClick={cancelAll}>❌ 取消所有挂单</button>
          </div>
          {orders.length > 0 && (
            <>
              <h2>📋 挂单列表</h2>
              <table className="data-table">
                <thead><tr><th>时间</th><th>交易对</th><th>方向</th><th>价格</th><th>数量</th><th>状态</th></tr></thead>
                <tbody>{orders.map((o: any, i: number) => (<tr key={i}><td>{o.timestamp}</td><td>{o.symbol}</td><td className={o.side === 'buy' ? 'positive' : 'negative'}>{o.side.toUpperCase()}</td><td>${o.price?.toLocaleString()}</td><td>{o.amount}</td><td><span className="badge badge-sandbox">{o.status}</span></td></tr>))}</tbody>
              </table>
            </>
          )}
          {positions.length > 0 && (
            <>
              <h2>📊 持仓列表</h2>
              <table className="data-table">
                <thead><tr><th>交易对</th><th>方向</th><th>数量</th><th>入场价</th><th>当前价</th><th>未实现盈亏</th></tr></thead>
                <tbody>{positions.map((p: any, i: number) => (<tr key={i}><td>{p.symbol}</td><td className={p.side === 'long' ? 'positive' : 'negative'}>{p.side.toUpperCase()}</td><td>{p.amount}</td><td>${p.entry_price?.toLocaleString()}</td><td>${p.current_price?.toLocaleString()}</td><td className={p.pnl >= 0 ? 'positive' : 'negative'}>${p.pnl?.toFixed(2)}</td></tr>))}</tbody>
              </table>
            </>
          )}
        </>
      )}
    </div>
  );
};

export default SandboxPage;
