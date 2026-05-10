<template>
    <div class="page-container">
        <h1 class="page-header">⚙️ 交易所配置</h1>
        <div class="controls">
            <button class="btn btn-primary" @click="showAdd = true">➕ 添加</button>
            <button class="btn" @click="loadExchanges">🔄 刷新</button>
        </div>
        <div v-if="loading" class="loading">
            <div class="loading-spinner"></div>
        </div>
        <template v-else>
            <div class="metrics-row">
                <div v-for="ex in exchanges" :key="ex.id" class="metric-card" style="padding: 16px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div><strong>{{ ex.name }}</strong><br /><span
                                :class="ex.status === 'connected' ? 'positive' : 'negative'">{{ ex.status }}</span>
                        </div>
                        <div style="display: flex; gap: 8px;">
                            <button class="btn-sm btn-info" @click="testConn(ex.id)">测试</button>
                            <button class="btn-sm btn-danger" @click="delEx(ex.id)">删除</button>
                        </div>
                    </div>
                </div>
            </div>
            <div v-if="showAdd" class="form-grid" style="margin-top: 20px;">
                <div class="form-group"><label>名称</label><input v-model="form.name" /></div>
                <div class="form-group"><label>交易所</label><select v-model="form.exchange_id">
                        <option value="binance">Binance</option>
                        <option value="okx">OKX</option>
                        <option value="bybit">Bybit</option>
                    </select></div>
                <div class="form-group"><label>API Key</label><input v-model="form.api_key" /></div>
                <div class="form-group"><label>Secret</label><input v-model="form.secret" type="password" /></div>
                <button class="btn btn-primary" @click="saveExchange">💾 保存</button>
                <button class="btn" @click="showAdd = false">取消</button>
            </div>
        </template>
    </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { exchangeApi } from '@shared/api';

const exchanges = ref<any[]>([]);
const loading = ref(true);
const showAdd = ref(false);
const form = ref({ name: '', exchange_id: 'binance', api_key: '', secret: '' });

async function loadExchanges() {
    loading.value = true;
    try { exchanges.value = await exchangeApi.listExchanges() || []; } catch (e) { console.error(e); }
    finally { loading.value = false; }
}
async function saveExchange() {
    try { if (form.value.name) { await exchangeApi.createExchange(form.value); showAdd.value = false; loadExchanges(); } } catch (e: any) { alert('失败: ' + (e.error || e.message)); }
}
async function delEx(id: string) { if (confirm('确定删除?')) { await exchangeApi.deleteExchange(id); loadExchanges(); } }
async function testConn(id: string) { try { const res: any = await exchangeApi.testConnection(id); alert(res.message || '成功'); } catch (e: any) { alert('失败: ' + (e.error || e.message)); } }

onMounted(() => { loadExchanges(); });
</script>
