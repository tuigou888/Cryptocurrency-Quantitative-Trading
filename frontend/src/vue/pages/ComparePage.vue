<template>
  <div class="page-container">
    <h1 class="page-header">
      <span class="page-header-icon">
        <Icons name="bar-chart" :size="20" />
      </span>
      交易分析
    </h1>

    <div v-if="loading" class="loading">
      <div class="loading-spinner"></div>
      <p class="loading-text">加载对比数据中...</p>
    </div>

    <template v-else-if="chartData">
      <div class="metrics-row">
        <MetricCard
          v-for="s in chartData.compare_list"
          :key="s.id"
          :label="s.name"
          :value="`${s.total_return_pct}%`"
          :delta="s.total_return_pct"
        />
      </div>

      <div class="charts-row">
        <div class="chart-box">
          <QuantChart :chartData="chartData.return_bar" title="收益率对比" height="350px" :loading="loading" />
        </div>
        <div class="chart-box">
          <QuantChart :chartData="chartData.sharpe_bar" title="夏普比率对比" height="350px" :loading="loading" />
        </div>
      </div>

      <div class="charts-row">
        <div class="chart-box chart-full">
          <QuantChart :chartData="chartData.equity_lines" title="权益曲线对比" height="450px" :loading="loading" />
        </div>
      </div>

      <div class="charts-row">
        <div class="chart-box">
          <QuantChart :chartData="chartData.winrate_bar" title="胜率对比" height="350px" :loading="loading" />
        </div>
        <div class="chart-box">
          <QuantChart :chartData="chartData.mdd_bar" title="最大回撤对比" height="350px" :loading="loading" />
        </div>
      </div>

      <div class="page-section">
        <h2 class="page-section-title">
          <Icons name="bar-chart" :size="18" />
          策略对比详情
        </h2>
        <div class="table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th>策略</th>
                <th>收益率</th>
                <th>夏普</th>
                <th>回撤</th>
                <th>胜率</th>
                <th>盈利因子</th>
                <th>交易次数</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="s in chartData.compare_list" :key="s.id">
                <td class="font-medium">{{ s.name }}</td>
                <td :class="s.total_return_pct >= 0 ? 'positive' : 'negative'" class="font-mono">
                  {{ s.total_return_pct }}%
                </td>
                <td class="font-mono">{{ s.sharpe_ratio }}</td>
                <td class="negative font-mono">{{ s.max_drawdown_pct }}%</td>
                <td class="font-mono">{{ s.win_rate }}%</td>
                <td class="font-mono">{{ s.profit_factor }}</td>
                <td class="font-mono">{{ s.total_trades }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>

    <div v-else class="empty-state">
      <Icons name="bar-chart" :size="48" class="empty-state-icon" />
      <div class="empty-state-title">无法加载对比数据</div>
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
    const res = await chartApi.getCompare() as any;
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

.font-medium {
  font-weight: 500;
}
</style>