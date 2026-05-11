<template>
  <div class="page-container">
    <h1 class="page-header">💰 交易分析</h1>
    <div v-if="loading" class="loading"><div class="loading-spinner"></div><p>加载中...</p></div>
    <template v-else-if="data">
      <div class="metrics-row">
        <MetricCard v-for="s in data.compare" :key="s.id" :label="s.name" :value="`${s.total_return_pct}%`" />
      </div>
      <div class="charts-row">
        <div class="chart-box"><h2>收益率对比</h2><PlotlyChart :chart="data.return_chart" style="height: 350px" /></div>
        <div class="chart-box"><h2>夏普比率对比</h2><PlotlyChart :chart="data.sharpe_chart" style="height: 350px" /></div>
      </div>
      <div class="charts-row">
        <div class="chart-box chart-full"><h2>权益曲线对比</h2><PlotlyChart :chart="data.equity_chart" style="height: 450px" /></div>
      </div>
      <div class="charts-row">
        <div class="chart-box"><h2>胜率对比</h2><PlotlyChart :chart="data.winrate_chart" style="height: 350px" /></div>
        <div class="chart-box"><h2>最大回撤对比</h2><PlotlyChart :chart="data.drawdown_chart" style="height: 350px" /></div>
      </div>
      <table class="data-table">
        <thead><tr><th>策略</th><th>收益率</th><th>夏普</th><th>回撤</th><th>胜率</th><th>盈利因子</th><th>交易次数</th></tr></thead>
        <tbody>
          <tr v-for="s in data.compare" :key="s.id">
            <td>{{ s.name }}</td>
            <td :class="s.total_return_pct >= 0 ? 'positive' : 'negative'">{{ s.total_return_pct }}%</td>
            <td>{{ s.sharpe_ratio }}</td>
            <td class="negative">{{ s.max_drawdown_pct }}%</td>
            <td>{{ s.win_rate }}%</td>
            <td>{{ s.profit_factor }}</td>
            <td>{{ s.total_trades }}</td>
          </tr>
        </tbody>
      </table>
    </template>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue';
import MetricCard from '@components/MetricCard.vue';
import PlotlyChart from '@components/PlotlyChart.vue';
import { compareApi } from '@shared/api';

const data = ref<any>(null);
const loading = ref(true);

onMounted(async () => {
  try { data.value = await compareApi.getComparison(); } catch (e) { console.error(e); }
  finally { loading.value = false; }
});
</script>