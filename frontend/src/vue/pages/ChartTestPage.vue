<template>
  <div class="page-container">
    <h1 class="page-header">
      <span class="page-header-icon">
        <Icons name="chart-line" :size="20" />
      </span>
      图表测试 - K线与月度收益
    </h1>

    <div class="controls">
      <button class="btn btn-primary" @click="startAutoUpdate" :disabled="isAutoUpdating">
        <Icons name="zap" :size="16" />
        {{ isAutoUpdating ? '自动更新中...' : '开始自动更新' }}
      </button>
      <button class="btn btn-secondary" @click="stopAutoUpdate" :disabled="!isAutoUpdating">
        <Icons name="x" :size="16" />
        停止更新
      </button>
      <button class="btn btn-ghost" @click="generateNewData">
        <Icons name="refresh-cw" :size="16" />
        手动刷新
      </button>
      <div class="update-info">
        <span class="update-count">已更新: {{ updateCount }} 次</span>
        <span class="update-interval">间隔: {{ updateInterval }}ms</span>
      </div>
    </div>

    <div class="charts-row">
      <div class="chart-box">
        <PlotlyChart :chart="klineChart" title="K线走势" style="height: 400px" />
      </div>
      <div class="chart-box">
        <PlotlyChart :chart="monthlyChart" title="月度收益" style="height: 400px" />
      </div>
    </div>

    <div class="metrics-row">
      <MetricCard label="当前价格" :value="currentPrice" type="currency" :delta="priceDelta" />
      <MetricCard label="今日涨跌" :value="dailyReturn" type="percent" :delta="dailyReturn" />
      <MetricCard label="本月收益" :value="monthlyReturn" type="percent" :delta="monthlyReturn" />
      <MetricCard label="夏普比率" :value="sharpeRatio" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue';
import PlotlyChart from '@components/PlotlyChart.vue';
import MetricCard from '@components/MetricCard.vue';
import Icons from '@components/Icons.vue';

const klineChart = ref<any>(null);
const monthlyChart = ref<any>(null);
const currentPrice = ref(0);
const priceDelta = ref(0);
const dailyReturn = ref(0);
const monthlyReturn = ref(0);
const sharpeRatio = ref(0);
const isAutoUpdating = ref(false);
const updateCount = ref(0);
const updateInterval = 3000;
let updateTimer: number | null = null;

const DARK_LAYOUT = {
  template: 'plotly_dark',
  paper_bgcolor: 'rgba(0,0,0,0)',
  plot_bgcolor: 'rgba(0,0,0,0)',
  font: { color: '#d1d5db', family: 'Inter, JetBrains Mono, sans-serif', size: 11 },
  margin: { l: 55, r: 18, t: 40, b: 42 },
  hoverlabel: {
    bgcolor: '#1f2937',
    bordercolor: '#374151',
    font: { color: '#f9fafb', size: 11.5, family: 'JetBrains Mono, monospace' },
  },
};

function generateDates(startDate: string, days: number): string[] {
  const dates: string[] = [];
  let current = new Date(startDate);
  for (let i = 0; i < days; i++) {
    dates.push(current.toISOString().split('T')[0]);
    current.setDate(current.getDate() + 1);
  }
  return dates;
}

function generateKlineData(): any {
  const dates = generateDates('2024-01-01', 120);
  const opens: number[] = [];
  const highs: number[] = [];
  const lows: number[] = [];
  const closes: number[] = [];
  const volumes: number[] = [];

  let price = 42000 + Math.random() * 5000;
  for (let i = 0; i < dates.length; i++) {
    const change = (Math.random() - 0.48) * 800;
    const open = price;
    const close = price + change;
    const high = Math.max(open, close) + Math.random() * 400;
    const low = Math.min(open, close) - Math.random() * 400;
    const volume = 15000 + Math.random() * 20000;

    opens.push(parseFloat(open.toFixed(2)));
    highs.push(parseFloat(high.toFixed(2)));
    lows.push(parseFloat(low.toFixed(2)));
    closes.push(parseFloat(close.toFixed(2)));
    volumes.push(parseFloat(volume.toFixed(2)));

    price = close;
  }

  return {
    data: [
      {
        x: dates,
        close: closes,
        decreasing: { line: { color: '#ef4444' } },
        high: highs,
        increasing: { line: { color: '#22c55e' } },
        line: { color: '#3b82f6', width: 1 },
        low: lows,
        open: opens,
        type: 'candlestick',
        name: 'BTC/USDT',
        xaxis: 'x',
        yaxis: 'y',
      },
      {
        x: dates,
        y: volumes,
        type: 'bar',
        name: '成交量',
        marker: { color: 'rgba(59, 130, 246, 0.3)' },
        xaxis: 'x',
        yaxis: 'y2',
      },
    ],
    layout: {
      ...DARK_LAYOUT,
      xaxis: {
        ...DARK_LAYOUT.xaxis,
        domain: [0, 1],
        rangeslider: { visible: false },
        showgrid: true,
        gridcolor: 'rgba(55, 65, 81, 0.35)',
        gridwidth: 0.5,
        tickfont: { size: 10.5, color: '#9ca3af' },
      },
      yaxis: {
        ...DARK_LAYOUT.yaxis,
        domain: [0.35, 1],
        showgrid: true,
        gridcolor: 'rgba(55, 65, 81, 0.35)',
        gridwidth: 0.5,
        tickfont: { size: 10.5, color: '#9ca3af' },
        tickprefix: '$',
      },
      yaxis2: {
        ...DARK_LAYOUT.yaxis,
        domain: [0, 0.25],
        showgrid: false,
        tickfont: { size: 10.5, color: '#9ca3af' },
      },
      showlegend: true,
      legend: {
        x: 0.01,
        y: 0.99,
        xanchor: 'left',
        yanchor: 'top',
        bgcolor: 'rgba(17, 24, 39, 0.9)',
        bordercolor: 'rgba(55, 65, 81, 0.5)',
        borderwidth: 1,
        font: { size: 10.5, color: '#d1d5db' },
        orientation: 'h',
      },
    },
  };
}

function generateMonthlyData(): any {
  const months = ['2024-01', '2024-02', '2024-03', '2024-04', '2024-05', '2024-06',
                  '2024-07', '2024-08', '2024-09', '2024-10', '2024-11', '2024-12'];

  const returns: number[] = [];
  for (let i = 0; i < 12; i++) {
    returns.push(parseFloat((Math.random() * 40 - 15).toFixed(2)));
  }

  const colors = returns.map(r => r >= 0 ? '#22c55e' : '#ef4444');

  return {
    data: [
      {
        x: months,
        y: returns,
        type: 'bar',
        name: '月度收益率',
        marker: { color: colors },
        text: returns.map(r => `${r.toFixed(1)}%`),
        textposition: 'outside',
        textfont: { size: 11, color: '#d1d5db', family: 'JetBrains Mono, monospace' },
        hovertemplate: '<b>%{x}</b><br>收益率: %{y:.2f}%<extra></extra>',
      },
    ],
    layout: {
      ...DARK_LAYOUT,
      xaxis: {
        ...DARK_LAYOUT.xaxis,
        showgrid: false,
        tickfont: { size: 10.5, color: '#9ca3af' },
      },
      yaxis: {
        ...DARK_LAYOUT.yaxis,
        showgrid: true,
        gridcolor: 'rgba(55, 65, 81, 0.35)',
        gridwidth: 0.5,
        tickfont: { size: 10.5, color: '#9ca3af' },
        ticksuffix: '%',
        zeroline: true,
        zerolinecolor: 'rgba(55, 65, 81, 0.6)',
      },
      showlegend: false,
      bargap: 0.3,
    },
  };
}

function generateNewData() {
  klineChart.value = generateKlineData();
  monthlyChart.value = generateMonthlyData();

  const lastKline = klineChart.value.data[0];
  currentPrice.value = lastKline.close[lastKline.close.length - 1];

  const dailyChange = (Math.random() - 0.48) * 5;
  dailyReturn.value = parseFloat(dailyChange.toFixed(2));

  const monthlyData = monthlyChart.value.data[0];
  monthlyReturn.value = monthlyData.y[monthlyData.y.length - 1];

  priceDelta.value = dailyReturn.value;
  sharpeRatio.value = parseFloat((Math.random() * 2 + 0.5).toFixed(2));

  updateCount.value++;
}

function startAutoUpdate() {
  if (isAutoUpdating.value) return;
  isAutoUpdating.value = true;
  updateTimer = window.setInterval(() => {
    generateNewData();
  }, updateInterval);
}

function stopAutoUpdate() {
  if (updateTimer) {
    clearInterval(updateTimer);
    updateTimer = null;
  }
  isAutoUpdating.value = false;
}

onMounted(() => {
  generateNewData();
});

onBeforeUnmount(() => {
  stopAutoUpdate();
});
</script>

<style scoped>
.update-info {
  display: flex;
  gap: 16px;
  margin-left: auto;
  font-size: 12px;
  color: var(--text-muted);
  font-family: 'JetBrains Mono', monospace;
}
</style>
