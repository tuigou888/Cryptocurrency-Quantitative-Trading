<template>
  <div class="page-container">
    <h1 class="page-header">
      <span class="page-header-icon">
        <Icons name="flask" :size="20" />
      </span>
      虚拟盘交易
    </h1>
    <div class="alert alert-warning">
      <Icons name="alert-triangle" :size="16" />
      <span>当前为虚拟盘模式，不会产生真实交易</span>
    </div>

    <div class="controls">
      <div class="control-group">
        <label>交易所配置</label>
        <select v-model="configId">
          <option value="">请选择</option>
          <option value="binance_sandbox">Binance沙箱</option>
          <option value="okx_sandbox">OKX沙箱</option>
        </select>
      </div>
      <button class="btn btn-primary" @click="loadAll" :disabled="!configId || loading">
        <Icons v-if="loading" name="refresh-cw" :size="16" class="spin" />
        <Icons v-else name="refresh-cw" :size="16" />
        {{ loading ? '加载中...' : '加载账户' }}
      </button>
    </div>

    <div v-if="loading" class="loading">
      <div class="loading-spinner"></div>
      <p class="loading-text">加载账户数据中...</p>
    </div>

    <template v-else-if="configId">
      <div v-if="balances.length > 0" class="metrics-row">
        <div v-for="(b, i) in balances" :key="i" class="metric-card">
          <div class="metric-label">{{ b.asset }}</div>
          <div class="metric-value">{{ b.free?.toFixed(4) }}</div>
          <div class="metric-delta">可用</div>
        </div>
      </div>

      <div class="page-section">
        <h2 class="page-section-title">
          <Icons name="sliders" :size="18" />
          下单
        </h2>
        <div class="form-grid">
          <div class="form-group">
            <label>交易对</label>
            <select v-model="orderForm.symbol">
              <option value="BTC/USDT">BTC/USDT</option>
              <option value="ETH/USDT">ETH/USDT</option>
            </select>
          </div>
          <div class="form-group">
            <label>方向</label>
            <select v-model="orderForm.side">
              <option value="buy">买入</option>
              <option value="sell">卖出</option>
            </select>
          </div>
          <div class="form-group">
            <label>价格</label>
            <input type="number" v-model="orderForm.price" placeholder="留空为市价" />
          </div>
          <div class="form-group">
            <label>数量</label>
            <input type="number" v-model="orderForm.amount" placeholder="0.001" />
          </div>
        </div>

        <div class="button-row">
          <button class="btn btn-primary" @click="placeOrder" :disabled="loading">
            <Icons name="trending-up" :size="16" />
            下单
          </button>
          <button class="btn btn-danger" @click="cancelAll" :disabled="loading">
            <Icons name="x" :size="16" />
            取消所有挂单
          </button>
        </div>
      </div>

      <div v-if="orders.length > 0" class="page-section">
        <h2 class="page-section-title">
          <Icons name="list" :size="18" />
          挂单列表
        </h2>
        <div class="table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th>时间</th>
                <th>交易对</th>
                <th>方向</th>
                <th>价格</th>
                <th>数量</th>
                <th>状态</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(o, i) in orders" :key="i">
                <td>{{ o.timestamp }}</td>
                <td>{{ o.symbol }}</td>
                <td :class="o.side === 'buy' ? 'positive' : 'negative'">{{ o.side.toUpperCase() }}</td>
                <td>${{ formatNumber(o.price) }}</td>
                <td>{{ o.amount }}</td>
                <td><span class="badge badge-sandbox">{{ o.status }}</span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div v-if="positions.length > 0" class="page-section">
        <h2 class="page-section-title">
          <Icons name="pie-chart" :size="18" />
          持仓列表
        </h2>
        <div class="table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th>交易对</th>
                <th>方向</th>
                <th>数量</th>
                <th>入场价</th>
                <th>当前价</th>
                <th>未实现盈亏</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(p, i) in positions" :key="i">
                <td>{{ p.symbol }}</td>
                <td :class="p.side === 'long' ? 'positive' : 'negative'">{{ p.side.toUpperCase() }}</td>
                <td>{{ p.amount }}</td>
                <td>${{ formatNumber(p.entry_price) }}</td>
                <td>${{ formatNumber(p.current_price) }}</td>
                <td :class="p.pnl >= 0 ? 'positive' : 'negative'">${{ p.pnl?.toFixed(2) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>

    <div v-else class="empty-state">
      <Icons name="flask" :size="48" class="empty-state-icon" />
      <div class="empty-state-title">选择交易所配置</div>
      <div class="empty-state-desc">请选择沙箱交易所配置以开始虚拟交易</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue';
import Icons from '@components/Icons.vue';
import { sandboxApi } from '@shared/api';

const configId = ref('');
const balances = ref<any[]>([]);
const orders = ref<any[]>([]);
const positions = ref<any[]>([]);
const loading = ref(false);
const orderForm = ref({
  symbol: 'BTC/USDT',
  side: 'buy',
  price: '',
  amount: '',
});

function formatNumber(num: number): string {
  return num?.toLocaleString() ?? '-';
}

async function loadAll() {
  if (!configId.value) return;
  loading.value = true;
  try {
    const [bal, pos, ord] = await Promise.all([
      sandboxApi.getBalance(configId.value) as Promise<any>,
      sandboxApi.getPositions(configId.value) as Promise<any>,
      sandboxApi.getOrders(configId.value) as Promise<any>,
    ]);
    balances.value = bal.balances || [];
    positions.value = pos.positions || [];
    orders.value = ord.orders || [];
  } catch (e) {
    console.error('Failed to load sandbox data:', e);
  } finally {
    loading.value = false;
  }
}

async function placeOrder() {
  try {
    await sandboxApi.placeOrder({
      ...orderForm.value,
      config_id: configId.value,
    });
    loadAll();
  } catch (e: any) {
    alert('下单失败: ' + (e.error || e.message));
  }
}

async function cancelAll() {
  if (confirm('确定取消所有挂单?')) {
    await sandboxApi.cancelAllOrders(configId.value);
    loadAll();
  }
}

watch(configId, () => {
  if (configId.value) {
    loadAll();
  }
});

onMounted(() => {
  if (configId.value) {
    loadAll();
  }
});
</script>
