<template>
  <div class="metric-card">
    <div class="metric-label">{{ label }}</div>
    <div :class="['metric-value', valueClass]">{{ formattedValue }}</div>
    <div v-if="delta" :class="['metric-delta', deltaClass]">
      {{ delta > 0 ? '▲' : '▼' }} {{ Math.abs(delta).toFixed(2) }}%
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';

const props = withDefaults(defineProps<{
  label: string;
  value: number | string;
  type?: 'number' | 'currency' | 'percent';
  delta?: number;
  positive?: boolean;
}>(), {
  type: 'number',
  delta: 0,
  positive: true,
});

const formattedValue = computed(() => {
  if (props.value == null) return '--';
  if (typeof props.value === 'string') return props.value;
  
  switch (props.type) {
    case 'currency':
      return `$${(props.value as number).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    case 'percent':
      return `${(props.value as number).toFixed(2)}%`;
    default:
      return (props.value as number).toLocaleString();
  }
});

const valueClass = computed(() => {
  if (props.delta == null) return 'neutral';
  if (props.delta > 0) return 'positive';
  if (props.delta < 0) return 'negative';
  return 'neutral';
});

const deltaClass = computed(() => {
  if (props.delta == null) return '';
  return props.delta >= 0 ? 'positive' : 'negative';
});
</script>
