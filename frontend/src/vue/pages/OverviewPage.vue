<template>
  <div class="page-container">
    <h1 class="page-header">🏠 量化交易概览</h1>
    <div v-if="loading" class="loading">
      <div class="loading-spinner"></div>
      <p>加载中...</p>
    </div>
    <template v-else-if="data">
      <div class="metrics-row">
        <MetricCard label="总收益率" :value="data.metrics.total_return_pct" type="percent" :delta="data.metrics.total_return_pct" />
        <MetricCard label="最终资金" :value="data.metrics.final_capital" type="currency" />
        <MetricCard label="胜率" :value="data.metrics.win_rate" type="percent" />
        <MetricCard label="夏普比率" :value="data.metrics.sharpe_ratio" />
        <MetricCard label="最大回撤" :value="data.metrics.max_drawdown_pct" type="percent" :positive="false" />
      </div>
      <div class="charts-row">
        <div class="chart-box chart-full">
          <h2>📈 权益曲线</h2>
          <PlotlyChart :chart="data.equity_chart" style="height: 400px" />
        </div>
      </div>
      <div class="charts-row">
        <div class="chart-box">
          <h2>📊 K线走势</h2>
          <PlotlyChart :chart="data.kline_chart" style="height: 400px" />
        </div>
        <div class="chart-box">
          <h2>📊 月度收益</h2>
          <PlotlyChart :chart="data.monthly_chart" style="height: 400px" />
        </div>
      </div>
      <div class="page-section">
        <h2>📝 交易统计</h2>
        <table class="data-table">
          <thead><tr><th>指标</th><th>数值</th></tr></thead>
          <tbody>
            <tr><td>盈利因子</td><td>{{ data.metrics.profit_factor }}</td></tr>
            <tr><td>总交易次数</td><td>{{ data.metrics.total_trades }}</td></tr>
            <tr><td>盈利交易</td><td>{{ data.metrics.winning_trades }}</td></tr>
            <tr><td>亏损交易</td><td>{{ data.metrics.losing_trades }}</td></tr>
            <tr><td>平均盈利</td><td class="positive">${{ data.metrics.avg_profit }}</td></tr>
            <tr><td>平均亏损</td><td class="negative">${{ data.metrics.avg_loss }}</td></tr>
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
import { ref, onMounted } from 'vue';
import MetricCard from '@components/MetricCard.vue';
import PlotlyChart from '@components/PlotlyChart.vue';
import { overviewApi } from '@shared/api';

interface OverviewData {
  metrics: {
    total_return_pct: number;
    sharpe_ratio: number;
    max_drawdown_pct: number;
    win_rate: number;
    profit_factor: number;
    total_trades: number;
    avg_profit: number;
    avg_loss: number;
    winning_trades: number;
    losing_trades: number;
    final_capital: number;
    initial_capital: number;
  };
  equity_chart: any;
  kline_chart: any;
  monthly_chart: any;
}

const loading = ref(true);
const data = ref<OverviewData | null>(null);

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