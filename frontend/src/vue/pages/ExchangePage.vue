<template>
  <div class="page-container">
    <h1 class="page-header">
      <span class="page-header-icon">
        <Icons name="settings" :size="20" />
      </span>
      交易所配置
    </h1>

    <div class="controls">
      <button class="btn btn-primary" @click="showAdd = true">
        <Icons name="plus" :size="16" />
        添加交易所
      </button>
      <button class="btn btn-secondary" @click="loadExchanges">
        <Icons name="refresh-cw" :size="16" />
        刷新
      </button>
    </div>

    <div v-if="loading" class="loading">
      <div class="loading-spinner"></div>
      <p class="loading-text">加载交易所列表...</p>
    </div>

    <template v-else>
      <div v-if="exchanges.length > 0" class="exchange-grid">
        <div v-for="ex in exchanges" :key="ex.id" class="exchange-card">
          <div class="exchange-header">
            <div class="exchange-info">
              <div class="exchange-name">{{ ex.name }}</div>
              <div class="exchange-status" :class="ex.status">
                <span class="status-dot"></span>
                {{ ex.status === 'connected' ? '已连接' : '未连接' }}
              </div>
            </div>
            <div class="exchange-actions">
              <button class="btn btn-sm btn-secondary" @click="testConn(ex.id)" title="测试连接">
                <Icons name="activity" :size="14" />
              </button>
              <button class="btn btn-sm btn-danger" @click="delEx(ex.id)" title="删除">
                <Icons name="trash" :size="14" />
              </button>
            </div>
          </div>
        </div>
      </div>

      <div v-else class="empty-state">
        <Icons name="settings" :size="48" class="empty-state-icon" />
        <div class="empty-state-title">暂无交易所配置</div>
        <div class="empty-state-desc">点击添加按钮配置交易所API</div>
      </div>

      <div v-if="showAdd" class="modal-overlay" @click="showAdd = false">
        <div class="modal-content" @click.stop>
          <div class="modal-header">
            <h3>添加交易所</h3>
            <button class="btn btn-ghost btn-sm" @click="showAdd = false">
              <Icons name="x" :size="16" />
            </button>
          </div>
          <div class="form-grid">
            <div class="form-group">
              <label>名称</label>
              <input v-model="form.name" placeholder="自定义名称" />
            </div>
            <div class="form-group">
              <label>交易所</label>
              <select v-model="form.exchange_id">
                <option value="binance">Binance</option>
                <option value="okx">OKX</option>
                <option value="bybit">Bybit</option>
              </select>
            </div>
            <div class="form-group">
              <label>API Key</label>
              <input v-model="form.api_key" placeholder="输入API Key" />
            </div>
            <div class="form-group">
              <label>Secret</label>
              <input v-model="form.secret" type="password" placeholder="输入Secret" />
            </div>
          </div>
          <div class="button-row">
            <button class="btn btn-primary" @click="saveExchange">
              <Icons name="check" :size="16" />
              保存
            </button>
            <button class="btn btn-secondary" @click="showAdd = false">
              <Icons name="x" :size="16" />
              取消
            </button>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import Icons from '@components/Icons.vue';
import { exchangeApi } from '@shared/api';

const exchanges = ref<any[]>([]);
const loading = ref(true);
const showAdd = ref(false);
const form = ref({ name: '', exchange_id: 'binance', api_key: '', secret: '' });

async function loadExchanges() {
  loading.value = true;
  try { 
    exchanges.value = await exchangeApi.listExchanges() || []; 
  } catch (e) { 
    console.error(e); 
  } finally { 
    loading.value = false; 
  }
}

async function saveExchange() {
  try { 
    if (form.value.name) { 
      await exchangeApi.createExchange(form.value); 
      showAdd.value = false; 
      loadExchanges(); 
    } 
  } catch (e: any) { 
    alert('失败: ' + (e.error || e.message)); 
  }
}

async function delEx(id: string) { 
  if (confirm('确定删除该交易所配置?')) { 
    await exchangeApi.deleteExchange(id); 
    loadExchanges(); 
  } 
}

async function testConn(id: string) { 
  try { 
    const res: any = await exchangeApi.testConnection(id); 
    alert(res.message || '连接成功'); 
  } catch (e: any) { 
    alert('连接失败: ' + (e.error || e.message)); 
  } 
}

onMounted(() => { loadExchanges(); });
</script>

<style scoped>
.exchange-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}

.exchange-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color-subtle);
  border-radius: var(--radius-lg);
  padding: 20px;
  transition: all var(--transition-normal) var(--ease-out);
}

.exchange-card:hover {
  border-color: var(--border-color);
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}

.exchange-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.exchange-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.exchange-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.exchange-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.exchange-status.connected {
  color: var(--color-success);
}

.exchange-status.connected .status-dot {
  background: var(--color-success);
  box-shadow: 0 0 6px var(--color-success-glow);
}

.exchange-status:not(.connected) {
  color: var(--color-danger);
}

.exchange-status:not(.connected) .status-dot {
  background: var(--color-danger);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}

.exchange-actions {
  display: flex;
  gap: 8px;
}

.modal-overlay {
  background: rgba(0, 0, 0, 0.6);
}

.modal-content {
  background: var(--bg-secondary);
  padding: 24px;
  max-width: 480px;
}

.modal-header {
  margin-bottom: 20px;
}

.modal-header h3 {
  font-size: 18px;
}
</style>
