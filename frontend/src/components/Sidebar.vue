<template>
  <aside class="sidebar" :class="{ collapsed: isCollapsed }">
    <div class="sidebar-header">
      <div class="sidebar-logo">
        <Icons name="layers" :size="22" />
        <span v-if="!isCollapsed" class="logo-text">CryptoQuant</span>
      </div>
      <button class="collapse-btn" @click="toggleCollapse" :title="isCollapsed ? '展开' : '收起'">
        <Icons :name="isCollapsed ? 'chevron-right' : 'chevron-down'" :size="14" />
      </button>
    </div>
    <nav class="sidebar-nav">
      <router-link
        v-for="item in navItems"
        :key="item.path"
        :to="item.path"
        :class="['nav-link', { active: route.path === item.path }]"
        :title="isCollapsed ? item.label : ''"
      >
        <span class="nav-icon">
          <Icons :name="item.icon" :size="18" />
        </span>
        <span v-if="!isCollapsed" class="nav-link-text">{{ item.label }}</span>
        <span v-if="!isCollapsed && item.badge" class="nav-badge">{{ item.badge }}</span>
      </router-link>
    </nav>
    <div class="sidebar-footer" v-if="!isCollapsed">
      <div class="system-status">
        <div class="status-dot-wrapper">
          <span class="status-dot"></span>
          <span class="status-text">系统运行中</span>
        </div>
      </div>
      <div class="version">v2.0.0</div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useRoute } from 'vue-router';
import Icons from './Icons.vue';

const route = useRoute();
const isCollapsed = ref(false);

function toggleCollapse() {
  isCollapsed.value = !isCollapsed.value;
}

const navItems = [
  { path: '/', label: '概览', icon: 'home' },
  { path: '/backtest', label: '回测分析', icon: 'chart-line' },
  { path: '/compare', label: '交易分析', icon: 'bar-chart' },
  { path: '/risk', label: '风险分析', icon: 'shield-alert' },
  { path: '/monthly-returns', label: '月度收益', icon: 'calendar' },
  { path: '/live', label: '实时交易', icon: 'activity' },
  { path: '/exchanges', label: '交易所配置', icon: 'settings' },
  { path: '/sandbox', label: '虚拟盘交易', icon: 'flask' },
];
</script>

<style scoped>
.sidebar {
  position: fixed;
  left: 0;
  top: 0;
  width: var(--sidebar-width);
  height: 100vh;
  background: var(--bg-secondary);
  border-right: 1px solid var(--border-color-subtle);
  display: flex;
  flex-direction: column;
  z-index: var(--z-sidebar);
  overflow-y: auto;
  overflow-x: hidden;
  transition: width var(--transition-normal) var(--ease-out);
}

.sidebar::-webkit-scrollbar {
  width: 0;
}

.sidebar.collapsed {
  width: var(--sidebar-collapsed-width);
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 16px;
  border-bottom: 1px solid var(--border-color-subtle);
}

.sidebar-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--color-success);
  font-weight: 700;
  font-size: 15px;
  letter-spacing: -0.02em;
}

.logo-text {
  white-space: nowrap;
  transition: opacity var(--transition-fast);
}

.collapse-btn {
  background: transparent;
  border: 1px solid transparent;
  color: var(--text-muted);
  cursor: pointer;
  padding: 6px;
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition-fast) var(--ease-default);
}

.collapse-btn:hover {
  background: var(--bg-hover);
  color: var(--color-success);
  border-color: var(--border-color-subtle);
}

.sidebar-nav {
  flex: 1;
  padding: 10px 8px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 12px;
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 12.5px;
  font-weight: 500;
  transition: all var(--transition-fast) var(--ease-default);
  border-radius: var(--radius-md);
  position: relative;
  white-space: nowrap;
}

.nav-link:hover {
  color: var(--text-primary);
  background: rgba(55, 65, 81, 0.12);
}

.nav-link.active {
  color: var(--color-success);
  background: var(--color-success-subtle);
}

.nav-link.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 18px;
  background: var(--color-success);
  border-radius: 0 2px 2px 0;
}

.nav-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 18px;
  height: 18px;
  opacity: 0.85;
}

.nav-link.active .nav-icon {
  opacity: 1;
}

.nav-link-text {
  transition: opacity var(--transition-fast);
}

.nav-badge {
  margin-left: auto;
  background: var(--color-danger);
  color: white;
  font-size: 9px;
  font-weight: 700;
  padding: 2px 5px;
  border-radius: 8px;
  min-width: 16px;
  text-align: center;
  line-height: 1;
}

.sidebar-footer {
  padding: 14px 12px;
  border-top: 1px solid var(--border-color-subtle);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.system-status {
  display: flex;
  align-items: center;
  justify-content: center;
}

.status-dot-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 10px;
  background: var(--color-success-subtle);
  border-radius: var(--radius-sm);
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-success);
  position: relative;
}

.status-dot::after {
  content: '';
  position: absolute;
  inset: -2px;
  border-radius: 50%;
  background: var(--color-success);
  opacity: 0.3;
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { transform: scale(1); opacity: 0.3; }
  50% { transform: scale(1.4); opacity: 0; }
}

.status-text {
  font-size: 11px;
  color: var(--color-success);
  font-weight: 500;
}

.version {
  font-size: 10px;
  color: var(--text-disabled);
  text-align: center;
  font-family: 'JetBrains Mono', monospace;
  letter-spacing: 0.02em;
}

/* 响应式 */
@media (max-width: 768px) {
  .sidebar {
    width: var(--sidebar-collapsed-width);
  }

  .logo-text,
  .nav-link-text,
  .sidebar-footer {
    display: none;
  }

  .collapse-btn {
    display: none;
  }

  .sidebar-header {
    justify-content: center;
    padding: 14px 0;
  }

  .nav-link {
    justify-content: center;
    padding: 10px;
  }

  .nav-link.active::before {
    display: none;
  }

  .nav-icon {
    width: 20px;
    height: 20px;
  }
}
</style>