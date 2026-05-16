<template>
  <div class="page-container">
    <h1 class="page-header">
      <span class="page-header-icon">
        <Icons name="chart-line" :size="20" />
      </span>
      回测分析
    </h1>

    <div class="controls">
      <div class="control-group">
        <label>策略</label>
        <select v-model="strategy" @change="onStrategyChange">
          <option value="ma_cross">MA均线交叉</option>
          <option value="rsi">RSI超买超卖</option>
          <option value="grid">网格交易</option>
        </select>
      </div>
      <div class="control-group">
        <label>天数</label>
        <input type="number" v-model.number="days" min="7" max="365" />
      </div>
      <div class="control-group">
        <label>资金</label>
        <input type="number" v-model.number="capital" min="100" />
      </div>
      <button class="btn btn-primary" @click="loadBundle" :disabled="loading">
        <Icons v-if="loading" name="refresh-cw" :size="16" class="spin" />
        <Icons v-else name="zap" :size="16" />
        {{ loading ? '运行中...' : '运行回测' }}
      </button>
    </div>

    <div class="params-row">
      <div v-for="p in currentParams" :key="p.key" class="param-item">
        <label>{{ p.label }}</label>
        <input
          :type="p.type"
          v-model.number="params[p.key]"
          :min="p.min"
          :max="p.max"
          :step="p.step || 1"
        />
      </div>
    </div>

    <div v-if="bundle">
      <div class="metrics-row">
        <MetricCard
          label="总收益率"
          :value="bundle.metrics?.total_return_pct"
          type="percent"
          :delta="bundle.metrics?.total_return_pct"
        />
        <MetricCard label="夏普比率" :value="bundle.metrics?.sharpe_ratio" />
        <MetricCard label="最大回撤" :value="bundle.metrics?.max_drawdown_pct" type="percent" :positive="false" />
        <MetricCard label="胜率" :value="bundle.metrics?.win_rate" type="percent" />
        <MetricCard label="盈利因子" :value="bundle.metrics?.profit_factor" />
      </div>

      <div class="charts-row">
        <div class="chart-box">
          <QuantChart :chartData="bundle.equity_curve" title="权益曲线" height="350px" :loading="loading" />
        </div>
        <div class="chart-box">
          <QuantChart :chartData="bundle.drawdown" title="回撤曲线" height="350px" :loading="loading" />
        </div>
      </div>

      <div class="charts-row">
        <div class="chart-box">
          <QuantChart :chartData="bundle.pnl_distribution" title="盈亏分布" height="350px" :loading="loading" />
        </div>
        <div class="chart-box chart-full">
          <QuantChart :chartData="bundle.monthly_heatmap" title="月度收益热力图" height="350px" :loading="loading" />
        </div>
      </div>

      <div v-if="bundle.trades && bundle.trades.length > 0" class="page-section">
        <h2 class="page-section-title">
          <Icons name="bar-chart" :size="18" />
          交易记录
        </h2>
        <div class="table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th>入场时间</th>
                <th>出场时间</th>
                <th>方向</th>
                <th>入场价</th>
                <th>出场价</th>
                <th>盈亏</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(t, i) in bundle.trades" :key="i">
                <td>{{ t.entry_time }}</td>
                <td>{{ t.exit_time }}</td>
                <td :class="t.side === 'long' ? 'positive' : 'negative'">
                  <span class="direction-badge" :class="t.side">
                    {{ t.side === 'long' ? '多' : '空' }}
                  </span>
                </td>
                <td class="font-mono">${{ formatNumber(t.entry_price) }}</td>
                <td class="font-mono">${{ formatNumber(t.exit_price) }}</td>
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
      <Icons name="chart-line" :size="48" class="empty-state-icon" />
      <div class="empty-state-title">开始回测</div>
      <div class="empty-state-desc">选择策略参数并点击运行回测按钮</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import MetricCard from '@components/MetricCard.vue';
import QuantChart from '@components/QuantChart.vue';
import Icons from '@components/Icons.vue';
import { chartApi } from '@shared/chartApi';

const STRATEGY_PARAMS: Record<string, Array<{ key: string; label: string; type: string; min?: number; max?: number; step?: number }>> = {
  ma_cross: [
    { key: 'fast_period', label: '快速均线周期', type: 'number', min: 5, max: 50 },
    { key: 'slow_period', label: '慢速均线', type: 'number', min: 20, max: 100 },
  ],
  rsi: [
    { key: 'period', label: 'RSI周期', type: 'number', min: 7, max: 21 },
    { key: 'oversold', label: '超卖阈值', type: 'number', min: 20, max: 40 },
    { key: 'overbought', label: '超买阈值', type: 'number', min: 60, max: 80 },
  ],
  grid: [
    { key: 'grid_num', label: '网格数量', type: 'number', min: 5, max: 20 },
    { key: 'grid_range_pct', label: '价格范围%', type: 'number', step: 0.01, min: 0.01, max: 0.2 },
  ],
};

const DEFAULT_PARAMS: Record<string, Record<string, number>> = {
  ma_cross: { fast_period: 10, slow_period: 30 },
  rsi: { period: 14, oversold: 30, overbought: 70 },
  grid: { grid_num: 10, grid_range_pct: 0.1 },
};

const strategy = ref('ma_cross');
const params = ref<Record<string, number>>(DEFAULT_PARAMS.ma_cross);
const loading = ref(false);
const bundle = ref<any>(null);
const days = ref(60);
const capital = ref(10000);

const currentParams = computed(() => STRATEGY_PARAMS[strategy.value] || []);

function onStrategyChange() {
  params.value = { ...DEFAULT_PARAMS[strategy.value] };
}

function formatNumber(num: number): string {
  return num?.toLocaleString() ?? '-';
}

async function loadBundle() {
  loading.value = true;
  try {
    const res = await chartApi.getBundle({
      strategy_id: strategy.value,
      days: days.value,
      capital: capital.value,
    }) as any;
    bundle.value = res.data;
  } catch (e) {
    console.error('回测失败:', e);
    bundle.value = null;
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.param-item label {
  font-size: 12px;
  color: var(--text-secondary);
  font-weight: 500;
  white-space: nowrap;
}

.param-item input {
  width: 80px;
  padding: 7px 10px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-input);
  color: var(--text-primary);
  font-family: 'JetBrains Mono', monospace;
  font-size: 12.5px;
  transition: all var(--transition-fast) var(--ease-default);
}

.param-item input:focus {
  outline: none;
  border-color: var(--color-success);
  box-shadow: 0 0 0 2px var(--color-success-subtle);
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
  background: var(--color-success-subtle);
  color: var(--color-success);
  border: 1px solid rgba(34, 197, 94, 0.2);
}

.direction-badge.short {
  background: var(--color-danger-subtle);
  color: var(--color-danger);
  border: 1px solid rgba(239, 68, 68, 0.2);
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.table-wrapper {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}
</style>