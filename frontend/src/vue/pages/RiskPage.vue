<template>
  <div class="page-container">
    <h1 class="page-header">⚠️ 风险分析</h1>
    <div v-if="loading" class="loading"><div class="loading-spinner"></div><p>加载中...</p></div>
    <template v-else-if="data">
      <div class="metrics-row">
        <MetricCard label="VaR 95%" :value="data.var_95" type="percent" :delta="-Math.abs(data.var_95)" :positive="false" />
        <MetricCard label="CVaR 95%" :value="data.cvar_95" type="percent" :delta="-Math.abs(data.cvar_95)" :positive="false" />
        <MetricCard label="波动率" :value="data.volatility" type="percent" />
        <MetricCard label="偏度" :value="data.skewness" />
        <MetricCard label="峰度" :value="data.kurtosis" />
      </div>
      <div class="charts-row">
        <div class="chart-box"><h2>📉 回撤走势</h2><PlotlyChart :data="ddChartData" /></div>
        <div class="chart-box"><h2>📈 滚动夏普</h2><PlotlyChart :data="sharpeChartData" /></div>
      </div>
      <div class="page-section">
        <h2>风险指标</h2>
        <table class="data-table">
          <thead><tr><th>指标</th><th>值</th><th>评估</th></tr></thead>
          <tbody>
            <tr><td>VaR (95%)</td><td>{{ data.var_95 }}%</td><td :class="data.var_95 > -3 ? 'positive' : 'negative'">{{ data.var_95 > -3 ? '低风险' : '高风险' }}</td></tr>
            <tr><td>CVaR (95%)</td><td>{{ data.cvar_95 }}%</td><td :class="data.cvar_95 > -5 ? 'positive' : 'negative'">{{ data.cvar_95 > -5 ? '可接受' : '需关注' }}</td></tr>
            <tr><td>波动率</td><td>{{ data.volatility }}%</td><td>{{ data.volatility < 30 ? '正常' : '偏高' }}</td></tr>
            <tr><td>偏度</td><td>{{ data.skewness }}</td><td>{{ data.skewness > 0 ? '正偏(有利)' : '负偏(不利)' }}</td></tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import MetricCard from '@components/MetricCard.vue';
import PlotlyChart from '@components/PlotlyChart.vue';
import { riskApi } from '@shared/api';

const data = ref<any>(null);
const loading = ref(true);

onMounted(async () => {
  try { data.value = await riskApi.getRiskAnalysis(); } catch (e) { console.error(e); }
  finally { loading.value = false; }
});

const ddChartData = computed(() => data.value?.drawdown_chart ? [{ x: data.value.drawdown_chart.map((p: any) => p.date), y: data.value.drawdown_chart.map((p: any) => p.drawdown), type: 'scatter', mode: 'lines', fill: 'tozeroy', line: { color: '#ff4757' } }] : []);
const sharpeChartData = computed(() => data.value?.rolling_sharpe ? [{ x: data.value.rolling_sharpe.map((p: any) => p.date), y: data.value.rolling_sharpe.map((p: any) => p.sharpe), type: 'scatter', mode: 'lines', line: { color: '#ffa502' } }] : []);
</script>
