<template>
  <div class="page-container">
    <h1 class="page-header">🏠 量化交易概览</h1>
    <div v-if="loading" class="loading">
      <div class="loading-spinner"></div>
      <p>加载中...</p>
    </div>
    <template v-else-if="data">
      <div class="metrics-row">
        <MetricCard label="总权益" :value="data.key_metrics.total_equity" type="currency" :delta="data.key_metrics.pnl_percent" />
        <MetricCard label="总盈亏" :value="data.key_metrics.total_pnl" type="currency" :delta="data.key_metrics.pnl_percent" />
        <MetricCard label="胜率" :value="data.key_metrics.win_rate" type="percent" />
        <MetricCard label="夏普比率" :value="data.key_metrics.sharpe_ratio" />
        <MetricCard label="最大回撤" :value="data.key_metrics.max_drawdown" type="percent" :delta="-data.key_metrics.max_drawdown" :positive="false" />
      </div>
      <div class="charts-row">
        <div class="chart-box chart-full">
          <h2>📈 权益曲线</h2>
          <PlotlyChart :data="equityChartData" />
        </div>
      </div>
      <div class="charts-row">
        <div class="chart-box">
          <h2>📊 月度收益</h2>
          <PlotlyChart :data="monthlyChartData" />
        </div>
        <div class="chart-box">
          <h2>🤖 活跃策略</h2>
          <table class="data-table">
            <thead><tr><th>策略名称</th><th>状态</th><th>盈亏</th><th>交易次数</th></tr></thead>
            <tbody>
              <tr v-for="s in data.active_strategies" :key="s.name">
                <td>{{ s.name }}</td>
                <td><span :class="['badge', s.status === 'running' ? 'badge-running' : 'badge-stopped']">{{ s.status }}</span></td>
                <td :class="s.pnl >= 0 ? 'positive' : 'negative'">${{ s.pnl.toFixed(2) }}</td>
                <td>{{ s.trades }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <div class="page-section">
        <h2>📝 最近交易</h2>
        <table class="data-table">
          <thead><tr><th>时间</th><th>交易对</th><th>方向</th><th>价格</th><th>数量</th><th>盈亏</th></tr></thead>
          <tbody>
            <tr v-for="t in data.recent_trades" :key="t.timestamp">
              <td>{{ t.timestamp }}</td><td>{{ t.symbol }}</td>
              <td :class="t.side === 'buy' ? 'positive' : 'negative'">{{ t.side.toUpperCase() }}</td>
              <td>${{ t.price.toLocaleString() }}</td><td>{{ t.amount }}</td>
              <td :class="t.pnl >= 0 ? 'positive' : 'negative'">${{ t.pnl.toFixed(2) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
    <div v-else class="loading">
      <p>无法加载数据</p>
      <button class="btn btn-primary" @click="loadData">🔄 重试</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import MetricCard from '@components/MetricCard.vue';
import PlotlyChart from '@components/PlotlyChart.vue';
import { overviewApi } from '@shared/api';

interface OverviewData {
  key_metrics: {
    total_equity: number;
    total_pnl: number;
    pnl_percent: number;
    win_rate: number;
    sharpe_ratio: number;
    max_drawdown: number;
  };
  equity_curve: Array<{ date: string; equity: number }>;
  monthly_returns: Array<{ month: string; return: number }>;
  active_strategies: Array<{ name: string; status: string; pnl: number; trades: number }>;
  recent_trades: Array<{ timestamp: string; symbol: string; side: string; price: number; amount: number; pnl: number }>;
}

const loading = ref(true);
const data = ref<OverviewData | null>(null);

const equityChartData = computed(() => {
  if (!data.value?.equity_curve) return [];
  return [{
    x: data.value.equity_curve.map(p => p.date),
    y: data.value.equity_curve.map(p => p.equity),
    type: 'scatter',
    mode: 'lines',
    fill: 'tozeroy',
    line: { color: '#00d4aa', width: 2 },
    fillcolor: 'rgba(0, 212, 170, 0.08)',
  }];
});

const monthlyChartData = computed(() => {
  if (!data.value?.monthly_returns) return [];
  return [{
    x: data.value.monthly_returns.map(m => m.month),
    y: data.value.monthly_returns.map(m => m.return),
    type: 'bar',
    marker: {
      color: data.value!.monthly_returns.map(m => m.return >= 0 ? '#00d4aa' : '#ff4757'),
    },
    text: data.value!.monthly_returns.map(m => `${m.return.toFixed(1)}%`),
    textposition: 'auto',
  }];
});

async function loadData() {
  loading.value = true;
  try {
    const res = await overviewApi.getOverview() as any;
    data.value = res;
  } catch (e) {
    console.error('Failed to load overview data:', e);
  } finally {
    loading.value = false;
  }
}

onMounted(() => { loadData(); });
</script>
