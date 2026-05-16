<template>
  <div class="page-container">
    <h1 class="page-header">
      <span class="page-header-icon">
        <Icons name="chart-line" :size="20" />
      </span>
      概览
    </h1>

    <div v-if="loading" class="loading">
      <div class="loading-spinner"></div>
      <p class="loading-text">加载数据中...</p>
    </div>

    <template v-else-if="bundle">
      <div class="metrics-row">
        <MetricCard
          label="总收益率"
          :value="bundle.metrics?.total_return_pct"
          type="percent"
          :delta="bundle.metrics?.total_return_pct"
        />
        <MetricCard
          label="最终资金"
          :value="bundle.metrics?.final_capital"
          type="currency"
        />
        <MetricCard
          label="胜率"
          :value="bundle.metrics?.win_rate"
          type="percent"
        />
        <MetricCard
          label="夏普比率"
          :value="bundle.metrics?.sharpe_ratio"
        />
        <MetricCard
          label="最大回撤"
          :value="bundle.metrics?.max_drawdown_pct"
          type="percent"
          :positive="false"
        />
      </div>

      <div class="charts-row">
        <div class="chart-box chart-full">
          <QuantChart :chartData="bundle.equity_curve" title="权益曲线" height="400px" :loading="loading" />
        </div>
      </div>

      <div class="charts-row">
        <div class="chart-box">
          <QuantChart :chartData="bundle.kline" title="K线走势" height="400px" :loading="loading" />
        </div>
        <div class="chart-box">
          <QuantChart :chartData="bundle.monthly_heatmap" title="月度收益热力图" height="400px" :loading="loading" />
        </div>
      </div>

      <div class="page-section">
        <h2 class="page-section-title">
          <Icons name="bar-chart" :size="18" />
          交易统计
        </h2>
        <div class="table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th>指标</th>
                <th>数值</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, index) in statsItems" :key="index">
                <td>{{ item.label }}</td>
                <td :class="item.class">{{ item.value }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>

    <div v-else class="empty-state">
      <Icons name="alert-triangle" :size="48" class="empty-state-icon" />
      <div class="empty-state-title">无法加载数据</div>
      <div class="empty-state-desc">请检查网络连接或稍后重试</div>
      <button class="btn btn-primary" @click="loadData">
        <Icons name="refresh-cw" :size="16" />
        重试
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import MetricCard from '@components/MetricCard.vue';
import QuantChart from '@components/QuantChart.vue';
import Icons from '@components/Icons.vue';
import { chartApi } from '@shared/chartApi';

const loading = ref(true);
const bundle = ref<any>(null);

const statsItems = computed(() => {
  if (!bundle.value?.metrics) return [];
  const m = bundle.value.metrics;
  return [
    { label: '盈利因子', value: m.profit_factor?.toFixed(2) ?? '--', class: '' },
    { label: '总交易次数', value: m.total_trades ?? '--', class: '' },
    { label: '初始资金', value: m.initial_capital ? `$${m.initial_capital.toLocaleString()}` : '--', class: '' },
    { label: '最终资金', value: m.final_capital ? `$${m.final_capital.toLocaleString()}` : '--', class: m.final_capital >= (m.initial_capital || 0) ? 'positive' : 'negative' },
  ];
});

async function loadData() {
  loading.value = true;
  try {
    const res = await chartApi.getBundle() as any;
    bundle.value = res.data;
  } catch (e) {
    console.error('加载概览失败:', e);
    bundle.value = null;
  } finally {
    loading.value = false;
  }
}

onMounted(() => { loadData(); });
</script>