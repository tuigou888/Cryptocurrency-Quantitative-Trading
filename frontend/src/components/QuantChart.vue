<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch, computed, nextTick } from 'vue'
import * as echarts from 'echarts'
import type { EChartsOption, ECharts } from 'echarts'
import Icons from './Icons.vue'

interface ChartData {
  chart_type: string
  title: string
  subtitle: string
  x_axis: { type: string; data: any[] }
  series: any[]
  annotations: any[]
}

const props = withDefaults(defineProps<{
  chartData: ChartData | null
  loading?: boolean
  height?: string
  largeThreshold?: number
  title?: string
}>(), {
  loading: false,
  height: '400px',
  largeThreshold: 5000,
  title: '',
})

const displayTitle = computed(() => props.title || props.chartData?.title || '')

const emit = defineEmits<{
  retry: []
}>()

const chartContainer = ref<HTMLElement | null>(null)
let chartInstance: ECharts | null = null
const hasError = ref(false)
const isRendered = ref(false)
let resizeObserver: ResizeObserver | null = null

function colorPositive(): string {
  return '#00d4aa'
}

function colorNegative(): string {
  return '#ff4757'
}

function countTotalDataPoints(chartData: ChartData): number {
  let total = 0
  for (const s of chartData.series || []) {
    if (s.data && Array.isArray(s.data)) {
      if (s.type === 'candlestick' && Array.isArray(s.data[0])) {
        total += s.data.length * 4
      } else if (s.type === 'heatmap') {
        total += s.data.length * 3
      } else {
        total += s.data.length
      }
    }
  }
  return total
}

function transformToEChartsOption(chartData: ChartData): EChartsOption {
  const ct = chartData.chart_type
  const textColor = '#c0c0d0'
  const gridColor = 'rgba(55,65,81,0.35)'
  const dataPointCount = countTotalDataPoints(chartData)
  const useLarge = dataPointCount > props.largeThreshold

  const baseGrid = {
    left: 65,
    right: 25,
    top: 60,
    bottom: 50,
  }

  const baseTooltip: any = {
    trigger: 'axis',
    backgroundColor: 'rgba(23,23,42,0.95)',
    borderColor: '#3d3d5c',
    textStyle: { color: '#e0e0f0', fontSize: 12 },
    axisPointer: {
      type: 'cross',
      crossStyle: { color: '#666' },
      label: {
        backgroundColor: '#2a2a4a',
        color: '#e0e0f0',
      },
    },
  }

  const baseXAxis: any = {
    type: chartData.x_axis.type === 'datetime' ? 'time' : 'category',
    data: chartData.x_axis.data,
    axisLine: { lineStyle: { color: gridColor } },
    axisTick: { lineStyle: { color: gridColor } },
    axisLabel: { color: '#9ca3af', fontSize: 10.5 },
    splitLine: { show: false },
  }

  const baseYAxis: any = {
    type: 'value',
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: { color: '#9ca3af', fontSize: 10.5 },
    splitLine: { lineStyle: { color: gridColor, type: 'dashed' } },
  }

  const commonSeriesOpts: any = {}
  if (useLarge) {
    commonSeriesOpts.large = true
    commonSeriesOpts.sampling = 'lttb'
  }

  if (ct === 'equity_curve') {
    const series = chartData.series.map((s: any, idx: number) => {
      const isBench = s.name && s.name.includes('基准')
      return {
        name: s.name,
        type: 'line',
        data: s.data,
        smooth: s.smooth !== false,
        showSymbol: false,
        symbol: 'none',
        lineStyle: s.lineStyle || (isBench
          ? { color: '#ffa502', type: 'dashed', width: 1.5 }
          : { color: colorPositive(), width: 2 }),
        areaStyle: s.areaStyle
          ? (idx === 0 ? { color: 'rgba(0,212,170,0.08)' } : undefined)
          : undefined,
        ...commonSeriesOpts,
      }
    })

    const markLines: any = {}
    for (const ann of chartData.annotations || []) {
      if (ann.type === 'initial_capital') {
        markLines.yAxis = ann.y
        markLines.lineStyle = { color: '#ffa502', type: 'dashed' }
        markLines.label = { formatter: `初始资金 $${ann.y.toLocaleString()}` }
      }
    }
    if (markLines.yAxis !== undefined) {
      series[0].markLine = { silent: true, data: [markLines] }
    }

    return {
      backgroundColor: 'transparent',
      title: {
        text: chartData.title,
        subtext: chartData.subtitle || '',
        left: 'center',
        textStyle: { color: '#e0e0f0', fontSize: 15 },
        subtextStyle: { color: '#8888aa', fontSize: 11 },
      },
      tooltip: { ...baseTooltip, trigger: 'axis' },
      legend: {
        data: chartData.series.map((s: any) => s.name),
        bottom: 0,
        textStyle: { color: textColor, fontSize: 11 },
      },
      grid: baseGrid,
      xAxis: baseXAxis,
      yAxis: { ...baseYAxis, name: '权益 (USDT)', nameTextStyle: { color: textColor } },
      dataZoom: [{ type: 'inside' }, { type: 'slider', bottom: 25 }],
      series,
    }
  }

  if (ct === 'drawdown') {
    return {
      backgroundColor: 'transparent',
      title: {
        text: chartData.title,
        subtext: chartData.subtitle || '',
        left: 'center',
        textStyle: { color: '#e0e0f0', fontSize: 15 },
        subtextStyle: { color: '#8888aa', fontSize: 11 },
      },
      tooltip: { ...baseTooltip, trigger: 'axis' },
      grid: baseGrid,
      xAxis: baseXAxis,
      yAxis: {
        ...baseYAxis,
        name: '回撤 (%)',
        nameTextStyle: { color: textColor },
        max: 0,
        axisLabel: { color: '#9ca3af', fontSize: 10.5, formatter: '{value}%' },
      },
      dataZoom: [{ type: 'inside' }, { type: 'slider', bottom: 25 }],
      series: [{
        name: chartData.series[0]?.name || '回撤',
        type: 'line',
        data: chartData.series[0]?.data || [],
        showSymbol: false,
        symbol: 'none',
        lineStyle: { color: colorNegative(), width: 1.5 },
        areaStyle: { color: 'rgba(255,71,87,0.15)' },
        ...commonSeriesOpts,
      }],
    }
  }

  if (ct === 'monthly_heatmap') {
    const s = chartData.series[0]
    if (!s || !s.data || s.data.length === 0) {
      return {
        backgroundColor: 'transparent',
        title: { text: chartData.title, left: 'center', textStyle: { color: '#e0e0f0' } },
        graphic: { type: 'text', left: 'center', top: 'center', style: { text: '数据不足', fill: '#8888aa' } },
      }
    }

    const yAxisData = s.yAxisData || []
    const xAxisData = chartData.x_axis.data || []
    const visualMapAnn = chartData.annotations?.find((a: any) => a.type === 'visualMap') || {}
    const heatData = s.data.map((d: any) => [d.x, d.y, d.value])

    return {
      backgroundColor: 'transparent',
      title: {
        text: chartData.title,
        subtext: chartData.subtitle || '',
        left: 'center',
        textStyle: { color: '#e0e0f0', fontSize: 15 },
        subtextStyle: { color: '#8888aa', fontSize: 11 },
      },
      tooltip: {
        position: 'top',
        backgroundColor: 'rgba(23,23,42,0.95)',
        borderColor: '#3d3d5c',
        textStyle: { color: '#e0e0f0' },
        formatter: (params: any) => {
          return `${params.value[1]}年${params.value[0]}月: ${params.value[2]}%`
        },
      },
      grid: { left: 80, right: 30, top: 60, bottom: 60 },
      xAxis: {
        type: 'category',
        data: xAxisData,
        splitArea: { show: true },
        axisLabel: { color: '#9ca3af', fontSize: 10.5, formatter: '{value}月' },
      },
      yAxis: {
        type: 'category',
        data: yAxisData,
        splitArea: { show: true },
        axisLabel: { color: '#9ca3af', fontSize: 10.5 },
      },
      visualMap: {
        min: visualMapAnn.min || -10,
        max: visualMapAnn.max || 10,
        calculable: true,
        orient: 'horizontal',
        left: 'center',
        bottom: 10,
        inRange: { color: visualMapAnn.inRange?.color || ['#ff4757', '#2a2a4a', '#00d4aa'] },
        textStyle: { color: '#9ca3af' },
      },
      series: [{
        name: s.name || '月度收益率',
        type: 'heatmap',
        data: heatData,
        label: {
          show: s.label?.show !== false,
          color: '#e0e0f0',
          fontSize: 10,
          formatter: (p: any) => `${p.value[2]}%`,
        },
        emphasis: {
          itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.5)' },
        },
      }],
    }
  }

  if (ct === 'pnl_distribution') {
    const barSeries = chartData.series.find((s: any) => s.type === 'bar')
    const lineSeries = chartData.series.find((s: any) => s.type === 'line')

    const barData = (barSeries?.data || []).map((v: number, i: number) => {
      return { value: v, itemStyle: { color: 'rgba(74,144,217,0.7)', borderColor: '#6ab0ff', borderWidth: 1 } }
    })

    return {
      backgroundColor: 'transparent',
      title: {
        text: chartData.title,
        subtext: chartData.subtitle || '',
        left: 'center',
        textStyle: { color: '#e0e0f0', fontSize: 15 },
        subtextStyle: { color: '#8888aa', fontSize: 11 },
      },
      tooltip: { ...baseTooltip, trigger: 'axis' },
      legend: {
        data: ['盈亏分布', '累计盈亏'],
        bottom: 0,
        textStyle: { color: textColor, fontSize: 11 },
      },
      grid: { ...baseGrid, right: 70 },
      xAxis: {
        type: 'category',
        data: barSeries?.xAxisData || chartData.x_axis.data,
        axisLabel: { color: '#9ca3af', fontSize: 10 },
        name: '盈亏 (USDT)',
        nameTextStyle: { color: textColor },
      },
      yAxis: [
        { ...baseYAxis, name: '频次', nameTextStyle: { color: textColor } },
        {
          ...baseYAxis,
          name: '累计盈亏 (USDT)',
          nameTextStyle: { color: textColor },
          axisLabel: { color: '#9ca3af', fontSize: 10.5 },
          splitLine: { show: false },
        },
      ],
      series: [
        {
          name: '盈亏分布',
          type: 'bar',
          data: barData,
          xAxisIndex: 0,
          yAxisIndex: 0,
          ...commonSeriesOpts,
        },
        {
          name: '累计盈亏',
          type: 'line',
          data: lineSeries?.data || [],
          xAxisIndex: 0,
          yAxisIndex: 1,
          showSymbol: false,
          symbol: 'none',
          lineStyle: { color: '#ffa502', width: 2 },
          ...commonSeriesOpts,
        },
      ],
    }
  }

  if (ct === 'daily_returns' || ct === 'weekly_returns' || ct === 'monthly_returns') {
    const s = chartData.series[0]
    const colors = s?._colors || (s?.data || []).map((v: number) => v >= 0 ? colorPositive() : colorNegative())
    const barData = (s?.data || []).map((v: number, i: number) => ({
      value: v,
      itemStyle: { color: colors[i] },
    }))

    return {
      backgroundColor: 'transparent',
      title: {
        text: chartData.title,
        subtext: chartData.subtitle || '',
        left: 'center',
        textStyle: { color: '#e0e0f0', fontSize: 15 },
        subtextStyle: { color: '#8888aa', fontSize: 11 },
      },
      tooltip: { ...baseTooltip, trigger: 'axis' },
      grid: baseGrid,
      xAxis: {
        type: 'category',
        data: chartData.x_axis.data,
        axisLabel: {
          color: '#9ca3af',
          fontSize: 10,
          rotate: chartData.x_axis.data.length > 60 ? 45 : 0,
        },
      },
      yAxis: {
        ...baseYAxis,
        name: '收益率 (%)',
        nameTextStyle: { color: textColor },
        axisLabel: { color: '#9ca3af', fontSize: 10.5, formatter: '{value}%' },
      },
      dataZoom: chartData.x_axis.data.length > 30
        ? [{ type: 'inside' }, { type: 'slider', bottom: 25 }]
        : undefined,
      series: [{
        name: chartData.series[0]?.name || '收益率',
        type: 'bar',
        data: barData,
        ...commonSeriesOpts,
      }],
    }
  }

  if (ct === 'kline') {
    return {
      backgroundColor: 'transparent',
      title: {
        text: chartData.title,
        subtext: chartData.subtitle || '',
        left: 'center',
        textStyle: { color: '#e0e0f0', fontSize: 15 },
        subtextStyle: { color: '#8888aa', fontSize: 11 },
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross' },
        backgroundColor: 'rgba(23,23,42,0.95)',
        borderColor: '#3d3d5c',
        textStyle: { color: '#e0e0f0', fontSize: 12 },
      },
      legend: {
        data: ['K线', '成交量'],
        bottom: 0,
        textStyle: { color: textColor, fontSize: 11 },
      },
      grid: [
        { left: 65, right: 25, top: 60, height: '55%' },
        { left: 65, right: 25, top: '72%', height: '16%' },
      ],
      xAxis: [
        {
          type: 'category',
          data: chartData.x_axis.data,
          axisLabel: { color: '#9ca3af', fontSize: 10, rotate: 30 },
          gridIndex: 0,
          splitLine: { show: false },
        },
        {
          type: 'category',
          data: chartData.x_axis.data,
          axisLabel: { show: false },
          gridIndex: 1,
          splitLine: { show: false },
        },
      ],
      yAxis: [
        {
          type: 'value',
          scale: true,
          splitLine: { lineStyle: { color: gridColor, type: 'dashed' } },
          axisLabel: { color: '#9ca3af', fontSize: 10 },
          gridIndex: 0,
        },
        {
          type: 'value',
          splitLine: { show: false },
          axisLabel: { color: '#9ca3af', fontSize: 9 },
          gridIndex: 1,
        },
      ],
      dataZoom: [
        { type: 'inside', xAxisIndex: [0, 1] },
        { type: 'slider', xAxisIndex: [0, 1], bottom: 25 },
      ],
      series: [
        {
          name: 'K线',
          type: 'candlestick',
          data: chartData.series[0]?.data || [],
          xAxisIndex: 0,
          yAxisIndex: 0,
          itemStyle: {
            color: colorPositive(),
            color0: colorNegative(),
            borderColor: colorPositive(),
            borderColor0: colorNegative(),
          },
          ...commonSeriesOpts,
        },
        {
          name: '成交量',
          type: 'bar',
          data: chartData.series[1]?.data || [],
          xAxisIndex: 1,
          yAxisIndex: 1,
          itemStyle: { color: 'rgba(74,74,106,0.6)' },
          ...commonSeriesOpts,
        },
      ],
    }
  }

  if (ct === 'compare_return' || ct === 'compare_sharpe' || ct === 'compare_winrate' || ct === 'compare_maxdd') {
    const s = chartData.series[0]
    const isReturn = ct === 'compare_return'
    const barData = (s?.data || []).map((v: number, i: number) => {
      let color = s?.itemStyle?.color || '#4a90d9'
      if (isReturn) {
        color = (s?._colors || [])[i] || (v >= 0 ? colorPositive() : colorNegative())
      }
      return { value: v, itemStyle: { color } }
    })

    const yLabel = ct === 'compare_return' ? '收益率 (%)'
      : ct === 'compare_sharpe' ? '夏普比率'
      : ct === 'compare_winrate' ? '胜率 (%)'
      : '最大回撤 (%)'

    return {
      backgroundColor: 'transparent',
      title: {
        text: chartData.title,
        subtext: chartData.subtitle || '',
        left: 'center',
        textStyle: { color: '#e0e0f0', fontSize: 15 },
        subtextStyle: { color: '#8888aa', fontSize: 11 },
      },
      tooltip: { ...baseTooltip, trigger: 'axis' },
      grid: baseGrid,
      xAxis: {
        type: 'category',
        data: chartData.x_axis.data,
        axisLabel: { color: '#9ca3af', fontSize: 10.5 },
        axisTick: { alignWithLabel: true },
      },
      yAxis: { ...baseYAxis, name: yLabel, nameTextStyle: { color: textColor } },
      series: [{
        name: chartData.series[0]?.name || '',
        type: 'bar',
        data: barData,
        label: s?.label?.show !== false
          ? { show: true, position: 'top', color: '#9ca3af', fontSize: 10, formatter: (p: any) => `${p.value}${isReturn || ct === 'compare_winrate' || ct === 'compare_maxdd' ? '%' : ''}` }
          : undefined,
        ...commonSeriesOpts,
      }],
    }
  }

  if (ct === 'compare_equity') {
    const colors = ['#00d4aa', '#4a90d9', '#ffa502', '#ff4757', '#a29bfe', '#fd79a8']
    const series = chartData.series.map((s: any, idx: number) => ({
      name: s.name,
      type: 'line',
      data: s.data,
      smooth: true,
      showSymbol: false,
      symbol: 'none',
      lineStyle: { color: colors[idx % colors.length], width: 2 },
      ...commonSeriesOpts,
    }))

    return {
      backgroundColor: 'transparent',
      title: {
        text: chartData.title,
        subtext: chartData.subtitle || '',
        left: 'center',
        textStyle: { color: '#e0e0f0', fontSize: 15 },
        subtextStyle: { color: '#8888aa', fontSize: 11 },
      },
      tooltip: { ...baseTooltip, trigger: 'axis' },
      legend: {
        data: chartData.series.map((s: any) => s.name),
        bottom: 0,
        textStyle: { color: textColor, fontSize: 11 },
      },
      grid: baseGrid,
      xAxis: baseXAxis,
      yAxis: { ...baseYAxis, name: '权益 (USDT)', nameTextStyle: { color: textColor } },
      dataZoom: [{ type: 'inside' }, { type: 'slider', bottom: 25 }],
      series,
    }
  }

  if (ct === 'return_distribution') {
    const barData = (chartData.series[0]?.data || []).map((v: number) => ({
      value: v,
      itemStyle: { color: 'rgba(74,144,217,0.7)', borderColor: '#6ab0ff', borderWidth: 1 },
    }))

    const meanAnn = chartData.annotations?.find((a: any) => a.type === 'mean_line')
    const markLines: any[] = []
    if (meanAnn) {
      markLines.push({
        xAxis: parseFloat(meanAnn.x),
        lineStyle: { color: '#ffa502', type: 'dashed' },
        label: { formatter: meanAnn.text, color: '#ffa502' },
      })
    }

    return {
      backgroundColor: 'transparent',
      title: {
        text: chartData.title,
        subtext: chartData.subtitle || '',
        left: 'center',
        textStyle: { color: '#e0e0f0', fontSize: 15 },
        subtextStyle: { color: '#8888aa', fontSize: 11 },
      },
      tooltip: { ...baseTooltip, trigger: 'axis' },
      grid: baseGrid,
      xAxis: {
        type: 'category',
        data: chartData.x_axis.data,
        axisLabel: { color: '#9ca3af', fontSize: 9, rotate: 30 },
        name: '收益率 (%)',
        nameTextStyle: { color: textColor },
      },
      yAxis: { ...baseYAxis, name: '频次', nameTextStyle: { color: textColor } },
      series: [{
        name: '频次',
        type: 'bar',
        data: barData,
        markLine: markLines.length > 0 ? { silent: true, symbol: 'none', data: markLines } : undefined,
        barWidth: '90%',
        ...commonSeriesOpts,
      }],
    }
  }

  if (ct === 'rolling_sharpe') {
    const s = chartData.series[0]
    return {
      backgroundColor: 'transparent',
      title: {
        text: chartData.title,
        subtext: chartData.subtitle || '',
        left: 'center',
        textStyle: { color: '#e0e0f0', fontSize: 15 },
        subtextStyle: { color: '#8888aa', fontSize: 11 },
      },
      tooltip: { ...baseTooltip, trigger: 'axis' },
      grid: baseGrid,
      xAxis: baseXAxis,
      yAxis: { ...baseYAxis, name: '夏普比率', nameTextStyle: { color: textColor } },
      dataZoom: [{ type: 'inside' }, { type: 'slider', bottom: 25 }],
      series: [{
        name: s?.name || '滚动夏普',
        type: 'line',
        data: s?.data || [],
        showSymbol: false,
        symbol: 'none',
        lineStyle: { color: '#ffa502', width: 1.5 },
        markLine: s?.markLine ? {
          silent: true,
          symbol: 'none',
          data: s.markLine.data || [],
        } : undefined,
        ...commonSeriesOpts,
      }],
    }
  }

  return {
    backgroundColor: 'transparent',
    title: { text: chartData.title || '', left: 'center', textStyle: { color: '#e0e0f0' } },
    graphic: { type: 'text', left: 'center', top: 'center', style: { text: `图表类型 ${ct} 暂未适配`, fill: '#8888aa' } },
  }
}

function renderChart() {
  if (!chartContainer.value) return
  if (!props.chartData || !props.chartData.series) {
    isRendered.value = false
    return
  }

  try {
    if (!chartInstance) {
      chartInstance = echarts.init(chartContainer.value, undefined, {
        renderer: 'canvas',
      })
    }

    const option = transformToEChartsOption(props.chartData)
    chartInstance.setOption(option, { notMerge: true })
    isRendered.value = true
    hasError.value = false
  } catch (e) {
    console.error('[QuantChart] 渲染失败:', e)
    hasError.value = true
    isRendered.value = false
  }
}

function handleResize() {
  if (chartInstance) {
    chartInstance.resize()
  }
}

function handleRetry() {
  hasError.value = false
  emit('retry')
  nextTick(() => renderChart())
}

watch(() => props.chartData, () => {
  nextTick(() => renderChart())
}, { deep: true })

onMounted(() => {
  nextTick(() => renderChart())

  if (chartContainer.value) {
    resizeObserver = new ResizeObserver(() => {
      handleResize()
    })
    resizeObserver.observe(chartContainer.value)
  }

  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  if (resizeObserver) {
    resizeObserver.disconnect()
    resizeObserver = null
  }
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
})

const containerStyle = computed(() => ({
  width: '100%',
  height: props.height,
  position: 'relative' as const,
}))
</script>

<template>
  <div class="quant-chart-wrapper">
    <div v-if="displayTitle" class="chart-title">
      <Icons name="activity" :size="16" />
      <span>{{ displayTitle }}</span>
    </div>
    <div ref="chartContainer" :style="containerStyle">
      <div v-if="!isRendered && !hasError && !loading" class="chart-placeholder">
        <span class="placeholder-text">请加载图表数据</span>
      </div>
      <div v-if="loading" class="chart-loading">
        <div class="loading-spinner"></div>
        <span class="loading-text">加载图表...</span>
      </div>
      <div v-if="hasError" class="chart-error">
        <Icons name="alert-triangle" :size="24" />
        <span>图表渲染失败</span>
        <button class="btn btn-sm btn-primary" @click="handleRetry">重试</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.quant-chart-wrapper {
  width: 100%;
  display: flex;
  flex-direction: column;
}

.chart-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary, #8888aa);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 8px;
}

.chart-placeholder,
.chart-loading,
.chart-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 250px;
  gap: 12px;
  color: var(--text-secondary, #8888aa);
}

.chart-error {
  color: var(--color-danger, #ff4757);
}

.loading-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid rgba(0, 212, 170, 0.2);
  border-top-color: #00d4aa;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-text {
  font-size: 13px;
  color: #8888aa;
}

.btn-sm {
  padding: 6px 14px;
  font-size: 12px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
}

.btn-primary {
  background: #00d4aa;
  color: #0d0d1a;
}
</style>