<template>
  <div class="metric-card" :class="[borderClass, { 'has-delta': delta !== undefined && delta !== 0 }]">
    <div class="metric-label">{{ label }}</div>
    <div :class="['metric-value', valueClass]" v-html="formattedValue"></div>
    <div v-if="delta !== undefined && delta !== 0" :class="['metric-delta', deltaClass]">
      <Icons :name="delta > 0 ? 'arrow-up' : 'arrow-down'" :size="14" class="metric-delta-icon" />
      <span>{{ Math.abs(delta).toFixed(2) }}%</span>
    </div>
    <div v-else-if="delta === 0" class="metric-delta neutral">
      <Icons name="minus" :size="14" class="metric-delta-icon" />
      <span>0.00%</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import Icons from './Icons.vue';

const props = withDefaults(defineProps<{
  label: string;
  value: number | string;
  type?: 'number' | 'currency' | 'percent';
  delta?: number;
  positive?: boolean;
  decimals?: number;
}>(), {
  type: 'number',
  delta: undefined,
  positive: true,
  decimals: 2,
});

const formattedValue = computed(() => {
  if (props.value == null || props.value === '') return '--';
  if (typeof props.value === 'string') return props.value;

  const num = props.value as number;
  switch (props.type) {
    case 'currency': {
      const fmt = new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: props.decimals,
        maximumFractionDigits: props.decimals,
      });
      return fmt.format(num);
    }
    case 'percent':
      return `${num.toFixed(props.decimals)}<span class="unit">%</span>`;
    default:
      return new Intl.NumberFormat('en-US', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 6,
      }).format(num);
  }
});

const valueClass = computed(() => {
  if (props.delta == null) return 'neutral';
  if (props.delta > 0) return props.positive !== false ? 'positive' : 'negative';
  if (props.delta < 0) return props.positive !== false ? 'negative' : 'positive';
  return 'neutral';
});

const deltaClass = computed(() => {
  if (props.delta == null) return '';
  if (props.delta > 0) return props.positive !== false ? 'positive' : 'negative';
  if (props.delta < 0) return props.positive !== false ? 'negative' : 'positive';
  return 'neutral';
});

const borderClass = computed(() => {
  if (props.delta == null) return '';
  if (props.delta > 0) return props.positive !== false ? 'success-border' : 'danger-border';
  if (props.delta < 0) return props.positive !== false ? 'danger-border' : 'success-border';
  return '';
});
</script>

<style scoped>
.metric-card { position: relative; overflow: hidden; }
.metric-card.has-delta { padding-bottom: 14px; }
.metric-delta { margin-top: 6px; }
.metric-delta-icon { stroke-width: 2.5; }
.unit {
  font-size: 0.75em;
  opacity: 0.75;
  margin-left: 2px;
  font-weight: 500;
}
</style>