<template>
  <aside class="sidebar">
    <div class="sidebar-logo">📊 CryptoQuant</div>
    <nav class="sidebar-nav">
      <a
        v-for="item in navItems"
        :key="item.page"
        :class="['nav-link', { active: activePage === item.page }]"
        @click="handleClick(item.page)"
      >
        {{ item.icon }} {{ item.label }}
      </a>
    </nav>
  </aside>
</template>

<script setup lang="ts">
interface NavItem {
  page: string;
  label: string;
  icon: string;
}

const props = defineProps<{
  activePage: string;
}>();

const emit = defineEmits<{
  (e: 'navigate', page: string): void;
}>();

const navItems: NavItem[] = [
  { page: 'overview', label: '概览', icon: '🏠' },
  { page: 'backtest', label: '回测分析', icon: '📈' },
  { page: 'compare', label: '交易分析', icon: '💰' },
  { page: 'risk', label: '风险分析', icon: '⚠️' },
  { page: 'live', label: '实时交易', icon: '🔄' },
  { page: 'exchanges', label: '交易所配置', icon: '⚙️' },
  { page: 'sandbox', label: '虚拟盘交易', icon: '🧪' },
];

function handleClick(page: string) {
  emit('navigate', page);
}
</script>
