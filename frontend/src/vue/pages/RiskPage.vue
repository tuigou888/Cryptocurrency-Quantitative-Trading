<template>
  <div class="page-container">
    <h1 class="page-header">⚠️ 风险分析</h1>
    <div v-if="loading" class="loading"><div class="loading-spinner"></div><p>加载中...</p></div>
    <template v-else-if="data">
      <div class="metrics-row">
        <MetricCard label="VaR 95%" :value="data.summary.var_95" type="percent" :delta="-Math.abs(data.summary.var_95)" :positive="false" />
        <MetricCard label="CVaR 95%" :value="data.summary.cvar_95" type="percent" :delta="-Math.abs(data.summary.cvar_95)" :positive="false" />
        <MetricCard label="波动率" :value="data.summary.volatility" type="percent" />
        <MetricCard label="最大回撤" :value="data.summary.max_drawdown_pct" type="percent" :positive="false" />
      </div>
      <div class="charts-row">
        <div class="chart-box"><h2>📉 回撤走势</h2><PlotlyChart :chart="data.drawdown_chart" style="height: 400px" /></div>
        <div class="chart-box"><h2>📈 滚动夏普</h2><PlotlyChart :chart="data.rolling_sharpe_chart" style="height: 400px" /></div>
      </div>
      <div class="charts-row">
        <div class="chart-box"><h2>📊 收益分布</h2><PlotlyChart :chart="data.return_dist_chart" style="height: 400px" /></div>
        <div class="chart-box"><h2>📊 回撤分布</h2><PlotlyChart :chart="data.dd_dist_chart" style="height: 400px" /></div>
      </div>
      <div class="page-section">
        <h2>风险指标</h2>
        <table class="data-table">
          <thead><tr><th>指标</th><th>值</th></tr></thead>
          <tbody>
            <tr v-for="m in data.risk_metrics" :key="m.metric">
              <td>{{ m.metric }}</td><td>{{ m.value }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue';
import MetricCard from '@components/MetricCard.vue';
import PlotlyChart from '@components/PlotlyChart.vue';
import { riskApi } from '@shared/api';

const data = ref<any>(null);
const loading = ref(true);

onMounted(async () => {
  try { data.value = await riskApi.getRiskAnalysis(); } catch (e) { console.error(e); }
  finally { loading.value = false; }
});
</script>