<template>
  <div class="page-container">
    <h1 class="page-header">
      <span class="page-header-icon">
        <Icons name="activity" :size="20" />
      </span>
      实时交易
    </h1>

    <div class="controls">
      <button class="btn btn-primary" @click="loadData" :disabled="loading">
        <Icons v-if="loading" name="refresh-cw" :size="16" class="spin" />
        <Icons v-else name="refresh-cw" :size="16" />
        {{ loading ? '刷新中...' : '刷新数据' }}
      </button>
      <span class="hint">
        <Icons name="info" :size="14" />
        当前显示 MA Cross 策略模拟数据
      </span>
    </div>

    <div v-if="data">
      <div class="metrics-row">
        <MetricCard label="最终资金" :value="data.metrics?.final_capital" type="currency" />
        <MetricCard
          label="收益率"
          :value="data.metrics?.total_return_pct"
          type="percent"
          :delta="data.metrics?.total_return_pct"
        />
        <MetricCard label="夏普比率" :value="data.metrics?.sharpe_ratio" />
        <MetricCard label="交易次数" :value="data.metrics?.total_trades" />
      </div>

      <div class="charts-row">
        <div class="chart-box chart-full">
          <QuantChart :chartData="data.kline" title="实时价格" height="400px" :loading="loading" />
        </div>
      </div>

      <div v-if="data.trades && data.trades.length > 0" class="page-section">
        <h2 class="page-section-title">
          <Icons name="bar-chart" :size="18" />
          交易记录
        </h2>
        <div class="table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>方向</th>
                <th>入场价</th>
                <th>出场价</th>
                <th>入场时间</th>
                <th>出场时间</th>
                <th>盈亏</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(t, i) in data.trades" :key="i">
                <td class="font-mono">{{ t.id }}</td>
                <td>
                  <span class="direction-badge" :class="t.side">
                    {{ t.side === 'long' ? '多' : '空' }}
                  </span>
                </td>
                <td class="font-mono">${{ formatNumber(t.entry_price) }}</td>
                <td class="font-mono">${{ formatNumber(t.exit_price) }}</td>
                <td>{{ t.entry_time }}</td>
                <td>{{ t.exit_time }}</td>
                <td :class="t.pnl >= 0 ? 'positive' : 'negative'" class="font-mono">
                  ${{ t.pnl?.toFixed(2) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <div v-else-if="!loading" class="empty-state">
      <Icons name="activity" :size="48" class="empty-state-icon" />
      <div class="empty-state-title">暂无交易数据</div>
      <div class="empty-state-desc">点击刷新按钮加载实时交易数据</div>
      <button class="btn btn-primary" @click="loadData">
        <Icons name="refresh-cw" :size="16" />
        开始加载
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import MetricCard from '@components/MetricCard.vue';
import QuantChart from '@components/QuantChart.vue';
import Icons from '@components/Icons.vue';
import { chartApi } from '@shared/chartApi';

const loading = ref(false);
const data = ref<any>(null);

function formatNumber(num: number): string {
  return num?.toLocaleString() ?? '-';
}

async function loadData() {
  loading.value = true;
  try {
    const res = await chartApi.getBundle({ strategy_id: 'ma_cross', days: 7 }) as any;
    data.value = res.data;
  } catch (e) {
    console.error('加载实时数据失败:', e);
    data.value = null;
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  loadData();
});
</script>

<style scoped>
.hint {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--text-muted);
}

.direction-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 3px 10px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.direction-badge.long {
  background: rgba(34, 197, 94, 0.15);
  color: var(--color-success);
}

.direction-badge.short {
  background: rgba(239, 68, 68, 0.15);
  color: var(--color-danger);
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.table-wrapper {
  overflow-x: auto;
}
</style>