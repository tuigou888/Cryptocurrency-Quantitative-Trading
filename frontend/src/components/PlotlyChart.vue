<template>
  <div ref="chartContainer" class="plotly-chart-container"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, onBeforeUnmount } from 'vue';

interface ChartData {
  data: any[];
  layout?: any;
  config?: any;
}

const props = withDefaults(defineProps<{
  data: any[];
  layout?: any;
  config?: any;
  style?: Record<string, string>;
}>(), {
  layout: () => ({}),
  config: () => ({ responsive: true, displaylogo: false }),
  style: () => ({ width: '100%', height: '300px' }),
});

const chartContainer = ref<HTMLElement | null>(null);
let plotlyLoaded = false;

const defaultLayout = {
  template: 'plotly_dark',
  paper_bgcolor: 'rgba(0,0,0,0)',
  plot_bgcolor: 'rgba(0,0,0,0)',
  font: { color: '#c0c0d0' },
  margin: { l: 60, r: 20, t: 40, b: 40 },
};

function loadPlotly(): Promise<any> {
  return new Promise((resolve, reject) => {
    if (window.Plotly) {
      resolve(window.Plotly);
      return;
    }
    const script = document.createElement('script');
    script.src = 'https://cdn.plot.ly/plotly-2.27.0.min.js';
    script.onload = () => resolve(window.Plotly);
    script.onerror = reject;
    document.head.appendChild(script);
  });
}

async function renderChart() {
  if (!chartContainer.value || props.data.length === 0) return;
  
  try {
    const Plotly = await loadPlotly();
    plotlyLoaded = true;
    
    const layout = { ...defaultLayout, ...props.layout };
    const config = { responsive: true, displaylogo: false, ...props.config };
    
    Plotly.newPlot(chartContainer.value, props.data, layout, config);
  } catch (e) {
    console.error('Failed to load Plotly:', e);
  }
}

watch(() => props.data, () => {
  if (plotlyLoaded) {
    renderChart();
  }
}, { deep: true });

watch(() => props.layout, () => {
  if (plotlyLoaded) {
    renderChart();
  }
}, { deep: true });

onMounted(() => {
  renderChart();
});

onBeforeUnmount(() => {
  if (chartContainer.value && window.Plotly) {
    window.Plotly.purge(chartContainer.value);
  }
});
</script>

<style scoped>
.plotly-chart-container {
  width: 100%;
  min-height: 300px;
}
</style>
