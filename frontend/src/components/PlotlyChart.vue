<script setup lang="ts">
import { ref, onMounted, watch, onBeforeUnmount, computed } from 'vue';
import Icons from './Icons.vue';

const props = withDefaults(defineProps<{
  data?: any[];
  layout?: any;
  config?: any;
  chart?: any;
  style?: Record<string, string>;
  title?: string;
  loading?: boolean;
}>(), {
  layout: () => ({}),
  config: () => ({ responsive: false, displaylogo: false }),
  style: () => ({ width: '100%', height: '300px' }),
  title: '',
  loading: false,
});

const chartContainer = ref<HTMLElement | null>(null);
const isLoaded = ref(false);
const hasError = ref(false);

let plotlyLoadPromise: Promise<any> | null = null;

function loadPlotly(): Promise<any> {
  if ((window as any).Plotly) {
    return Promise.resolve((window as any).Plotly);
  }
  if (plotlyLoadPromise) return plotlyLoadPromise;

  plotlyLoadPromise = new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = 'https://cdn.plot.ly/plotly-2.27.0.min.js';
    script.async = true;
    script.onload = () => resolve((window as any).Plotly);
    script.onerror = () => {
      hasError.value = true;
      reject(new Error('Failed to load Plotly'));
    };
    document.head.appendChild(script);
  });
  return plotlyLoadPromise;
}

const defaultLayout = computed(() => ({
  template: 'plotly_dark',
  paper_bgcolor: 'rgba(0,0,0,0)',
  plot_bgcolor: 'rgba(0,0,0,0)',
  font: { 
    color: '#d1d5db',
    family: 'Inter, JetBrains Mono, Microsoft YaHei, sans-serif',
    size: 11,
  },
  margin: { l: 55, r: 18, t: 40, b: 42 },
  xaxis: {
    gridcolor: 'rgba(55, 65, 81, 0.35)',
    gridwidth: 0.5,
    zerolinecolor: 'rgba(55, 65, 81, 0.5)',
    tickfont: { size: 10.5, color: '#9ca3af' },
    tickformatstops: [{ dtickrange: [null, 86400000], value: '%m-%d' }, { dtickrange: [86400000, null], value: '%Y-%m' }],
    ticklen: 3,
    tickcolor: 'rgba(55, 65, 81, 0.4)',
  },
  yaxis: {
    gridcolor: 'rgba(55, 65, 81, 0.35)',
    gridwidth: 0.5,
    zerolinecolor: 'rgba(55, 65, 81, 0.5)',
    tickfont: { size: 10.5, color: '#9ca3af' },
    ticklen: 3,
    tickcolor: 'rgba(55, 65, 81, 0.4)',
  },
  hoverlabel: {
    bgcolor: '#1f2937',
    bordercolor: '#374151',
    font: { color: '#f9fafb', size: 11.5, family: 'JetBrains Mono, monospace' },
    namelength: -1,
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
    itemclick: 'toggleothers',
    itemdoubleclick: 'toggle',
  },
  bargap: 0.15,
  bargroupgap: 0.08,
  width: undefined,
  height: undefined,
}));

function getChartSpec() {
  if (props.chart && props.chart.data) {
    return { 
      data: props.chart.data, 
      layout: { ...defaultLayout.value, ...(props.chart.layout || {}) } 
    };
  }
  if (props.data && props.data.length > 0) {
    return { data: props.data, layout: { ...defaultLayout.value, ...props.layout } };
  }
  return null;
}

let renderTimer: number | null = null;
let lastDataHash: string | null = null;

function computeDataHash(spec: any): string {
  try {
    return JSON.stringify(spec.data);
  } catch {
    return '';
  }
}

async function renderChart(force = false) {
  if (!chartContainer.value) return;
  const spec = getChartSpec();
  if (!spec) {
    isLoaded.value = false;
    return;
  }

  const currentDataHash = computeDataHash(spec);
  if (!force && isLoaded.value && lastDataHash === currentDataHash) {
    return;
  }

  try {
    const Plotly = await loadPlotly();
    isLoaded.value = true;
    hasError.value = false;
    
    const rect = chartContainer.value.getBoundingClientRect();
    const layout = {
      ...spec.layout,
      width: rect.width,
      height: rect.height,
    };
    
    const config = { 
      responsive: false, 
      displaylogo: false,
      displayModeBar: true,
      modeBarButtonsToRemove: ['lasso2d', 'select2d'],
      ...props.config 
    };
    
    if (isLoaded.value && lastDataHash !== null) {
      await Plotly.react(chartContainer.value, spec.data, layout, config);
    } else {
      await Plotly.newPlot(chartContainer.value, spec.data, layout, config);
    }
    
    lastDataHash = currentDataHash;
  } catch (e) {
    console.error('Failed to render Plotly chart:', e);
    hasError.value = true;
    isLoaded.value = false;
  }
}

function handleWindowResize() {
  if (renderTimer) clearTimeout(renderTimer);
  renderTimer = window.setTimeout(() => {
    renderChart();
  }, 300);
}

watch(() => [props.data, props.chart, props.layout], () => {
  if (renderTimer) clearTimeout(renderTimer);
  renderTimer = window.setTimeout(() => {
    renderChart(false);
  }, 200);
}, { deep: true });

onMounted(() => {
  renderChart(true);
  window.addEventListener('resize', handleWindowResize);
});

onBeforeUnmount(() => {
  if (renderTimer) clearTimeout(renderTimer);
  window.removeEventListener('resize', handleWindowResize);
  if (chartContainer.value && (window as any).Plotly) {
    (window as any).Plotly.purge(chartContainer.value);
  }
});
</script>

<template>
  <div class="plotly-chart-wrapper">
    <div v-if="title" class="chart-title">
      <Icons name="activity" :size="16" />
      <span>{{ title }}</span>
    </div>
    <div ref="chartContainer" class="plotly-chart-container" :style="style">
      <div v-if="!isLoaded && !hasError" class="plotly-loading">
        <div class="loading-spinner"></div>
        <span class="loading-text">加载图表...</span>
      </div>
      <div v-else-if="hasError" class="plotly-error">
        <Icons name="alert-triangle" :size="24" />
        <span>图表加载失败</span>
        <button class="btn btn-sm btn-secondary" @click="renderChart">重试</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.plotly-chart-wrapper {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.chart-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 8px;
}

.plotly-chart-container {
  flex: 1;
  min-height: 250px;
  position: relative;
  overflow: visible;
}

.plotly-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 250px;
  gap: 12px;
  color: var(--text-secondary);
}

.plotly-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 250px;
  gap: 12px;
  color: var(--color-danger);
}
</style>
