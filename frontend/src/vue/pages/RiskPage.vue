<template>
  <div class="page-container">
    <h1 class="page-header">
      <span class="page-header-icon">
        <Icons name="shield-alert" :size="20" />
      </span>
      风险分析
    </h1>

    <div v-if="loading" class="loading">
      <div class="loading-spinner"></div>
      <p class="loading-text">加载风险数据中...</p>
    </div>

    <template v-else-if="chartData">
      <div class="metrics-row">
        <MetricCard label="VaR 95%" :value="chartData.summary.var_95" type="percent" :delta="-Math.abs(chartData.summary.var_95)" :positive="false" />
        <MetricCard label="CVaR 95%" :value="chartData.summary.cvar_95" type="percent" :delta="-Math.abs(chartData.summary.cvar_95)" :positive="false" />
        <MetricCard label="波动率" :value="chartData.summary.volatility" type="percent" />
        <MetricCard label="最大回撤" :value="chartData.summary.max_drawdown_pct" type="percent" :positive="false" />
      </div>

      <div class="charts-row">
        <div class="chart-box">
          <QuantChart :chartData="chartData.drawdown_chart" title="回撤走势" height="400px" :loading="loading" />
        </div>
        <div class="chart-box">
          <QuantChart :chartData="chartData.rolling_sharpe_chart" title="滚动夏普" height="400px" :loading="loading" />
        </div>
      </div>

      <div class="charts-row">
        <div class="chart-box">
          <QuantChart :chartData="chartData.return_dist_chart" title="收益分布" height="400px" :loading="loading" />
        </div>
        <div class="chart-box">
          <QuantChart :chartData="chartData.drawdown_chart" title="回撤曲线" height="400px" :loading="loading" />
        </div>
      </div>

      <div class="page-section">
        <h2 class="page-section-title">
          <Icons name="bar-chart" :size="18" />
          风险指标
        </h2>
        <div class="table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th>指标</th>
                <th>值</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="m in chartData.risk_metrics" :key="m.metric">
                <td>{{ m.metric }}</td>
                <td class="font-mono">{{ m.value }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>

    <div v-else class="empty-state">
      <Icons name="shield-alert" :size="48" class="empty-state-icon" />
      <div class="empty-state-title">无法加载风险数据</div>
      <div class="empty-state-desc">请检查网络连接或稍后重试</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import MetricCard from '@components/MetricCard.vue';
import QuantChart from '@components/QuantChart.vue';
import Icons from '@components/Icons.vue';
import { chartApi } from '@shared/chartApi';

const chartData = ref<any>(null);
const loading = ref(true);

onMounted(async () => {
  try {
    const res = await chartApi.getRisk() as any;
    chartData.value = res.data;
  } catch (e) {
    console.error(e);
    chartData.value = null;
  } finally {
    loading.value = false;
  }
});
</script>

<style scoped>
.table-wrapper {
  overflow-x: auto;
}
</style>