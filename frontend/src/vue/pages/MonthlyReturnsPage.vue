<template>
  <div class="page-container">
    <h1 class="page-header">
      <span class="page-header-icon">
        <Icons name="calendar" :size="20" />
      </span>
      月度收益分析
    </h1>

    <div class="controls">
      <div class="control-group">
        <label>展示模式</label>
        <select v-model="mode" @change="handleModeChange">
          <option value="year">按年查看 (月度收益)</option>
          <option value="month">按月查看 (每日收益)</option>
        </select>
      </div>

      <div class="control-group">
        <label>年份</label>
        <select v-model="selectedYear" @change="updateData">
          <option v-for="year in availableYears" :key="year" :value="year">{{ year }}</option>
        </select>
      </div>

      <div class="control-group" v-if="mode === 'month'">
        <label>月份</label>
        <select v-model="selectedMonth" @change="updateData">
          <option v-for="m in 12" :key="m" :value="m">{{ m }}月</option>
        </select>
      </div>

      <button class="btn btn-primary" @click="updateData">
        <Icons name="refresh-cw" :size="16" />
        刷新数据
      </button>
    </div>

    <div class="metrics-row">
      <MetricCard label="总收益率" :value="metrics.totalReturn" type="percent" :delta="metrics.totalReturn" />
      <MetricCard label="最大收益" :value="metrics.maxReturn" type="percent" positive />
      <MetricCard label="最大亏损" :value="metrics.minReturn" type="percent" :positive="false" />
      <MetricCard label="胜率" :value="metrics.winRate" type="percent" />
    </div>

    <div class="chart-box">
      <PlotlyChart :chart="chart" :title="chartTitle" style="height: 500px" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import PlotlyChart from '@components/PlotlyChart.vue';
import MetricCard from '@components/MetricCard.vue';
import Icons from '@components/Icons.vue';

const mode = ref<'year' | 'month'>('year');
const selectedYear = ref(2024);
const selectedMonth = ref(1);
const availableYears = [2021, 2022, 2023, 2024, 2025];

const metrics = ref({
  totalReturn: 0,
  maxReturn: 0,
  minReturn: 0,
  winRate: 0,
});

const chart = ref<any>(null);

const chartTitle = computed(() => {
  return mode.value === 'year' 
    ? `${selectedYear.value}年 月度收益率`
    : `${selectedYear.value}年 ${selectedMonth.value}月 日收益率`;
});

function generateReturns(count: number, mean = 0, std = 5): number[] {
  const data: number[] = [];
  for (let i = 0; i < count; i++) {
    const u1 = Math.random();
    const u2 = Math.random();
    const z = Math.sqrt(-2.0 * Math.log(u1)) * Math.cos(2.0 * Math.PI * u2);
    data.push(parseFloat((mean + z * std).toFixed(2)));
  }
  return data;
}

function updateData() {
  let labels: string[] = [];
  let values: number[] = [];

  if (mode.value === 'year') {
    const monthNames = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月'];
    labels = monthNames;
    values = generateReturns(12, 2, 8);
  } else {
    const daysInMonth = new Date(selectedYear.value, selectedMonth.value, 0).getDate();
    labels = Array.from({ length: daysInMonth }, (_, i) => `${i + 1}日`);
    values = generateReturns(daysInMonth, 0.5, 3);
  }

  const colors = values.map(v => v >= 0 ? '#22c55e' : '#ef4444');
  const positiveCount = values.filter(v => v >= 0).length;
  const totalReturn = values.reduce((a, b) => a + b, 0);

  chart.value = {
    data: [
      {
        x: labels,
        y: values,
        type: 'bar',
        name: '收益率',
        cliponaxis: false,
        marker: { 
          color: colors,
          line: { width: 0 }
        },
        text: values.map(v => `${v.toFixed(1)}%`),
        textposition: 'outside',
        textfont: { 
          size: 9.5, 
          color: '#cbd5e1',
          family: 'JetBrains Mono, monospace'
        },
        hovertemplate: '<b>%{x}</b><br>收益率: %{y:.2f}%<extra></extra>',
        width: mode.value === 'year' ? 0.6 : 0.8,
      }
    ],
    layout: {
      template: 'plotly_dark',
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: 'rgba(0,0,0,0)',
      font: { 
        color: '#d1d5db',
        family: 'Inter, sans-serif',
        size: 12,
      },
      margin: { l: 55, r: 20, t: 50, b: 90 },
      xaxis: {
        gridcolor: 'rgba(51, 65, 85, 0.3)',
        zerolinecolor: 'rgba(51, 65, 85, 0.5)',
        tickfont: { size: 10.5, color: '#9ca3af' },
        ticklen: 3,
        tickcolor: 'rgba(55, 65, 81, 0.4)',
        fixedrange: true,
        domain: [0, 1],
      },
      yaxis: {
        gridcolor: 'rgba(55, 65, 81, 0.35)',
        gridwidth: 0.5,
        zerolinecolor: 'rgba(71, 85, 105, 0.6)',
        tickfont: { size: 10.5, color: '#9ca3af' },
        ticklen: 3,
        tickcolor: 'rgba(55, 65, 81, 0.4)',
        ticksuffix: '%',
        zeroline: true,
        fixedrange: true,
        tickangle: -30,
        range: [
          Math.min(-5, Math.min(...values) * 1.3 - 3),
          Math.max(5, Math.max(...values) * 1.25 + 5),
        ],
      },
      showlegend: false,
      bargap: 0.2,
    }
  };

  metrics.value = {
    totalReturn: parseFloat(totalReturn.toFixed(2)),
    maxReturn: parseFloat(Math.max(...values).toFixed(2)),
    minReturn: parseFloat(Math.min(...values).toFixed(2)),
    winRate: parseFloat(((positiveCount / values.length) * 100).toFixed(1)),
  };
}

function handleModeChange() {
  selectedMonth.value = 1;
  updateData();
}

onMounted(() => {
  updateData();
});
</script>
