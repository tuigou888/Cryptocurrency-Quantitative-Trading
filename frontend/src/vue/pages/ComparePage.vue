<template>
  <div class="page-container">
    <h1 class="page-header">💰 交易分析</h1>
    <div v-if="loading" class="loading"><div class="loading-spinner"></div><p>加载中...</p></div>
    <template v-else-if="comparison.length">
      <div class="metrics-row">
        <MetricCard v-for="s in comparison" :key="s.name" :label="s.name" :value="`${s.return}%`" />
      </div>
      <div class="charts-row">
        <div class="chart-box"><h2>收益率对比</h2><PlotlyChart :data="returnChartData" /></div>
        <div class="chart-box"><h2>夏普比率对比</h2><PlotlyChart :data="sharpeChartData" /></div>
      </div>
      <table class="data-table">
        <thead><tr><th>策略</th><th>收益率</th><th>夏普</th><th>回撤</th></tr></thead>
        <tbody><tr v-for="s in comparison" :key="s.name"><td>{{ s.name }}</td><td>{{ s.return }}%</td><td>{{ s.sharpe }}</td><td>{{ s.max_dd }}%</td></tr></tbody>
      </table>
    </template>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import MetricCard from '@components/MetricCard.vue';
import PlotlyChart from '@components/PlotlyChart.vue';
import { compareApi } from '@shared/api';

const comparison = ref<any[]>([]);
const loading = ref(true);

onMounted(async () => {
  try {
    const data: any = await compareApi.getComparison();
    comparison.value = data.summary ? Object.entries(data.summary).map(([name, s]: [string, any]) => ({ name, ...s })) : [];
  } catch (e) { console.error(e); }
  finally { loading.value = false; }
});

const returnChartData = computed(() => comparison.value.length ? [{ x: comparison.value.map(s => s.name), y: comparison.value.map(s => s.return), type: 'bar', marker: { color: '#4a90d9' } }] : []);
const sharpeChartData = computed(() => comparison.value.length ? [{ x: comparison.value.map(s => s.name), y: comparison.value.map(s => s.sharpe), type: 'bar', marker: { color: '#00d4aa' } }] : []);
</script>
