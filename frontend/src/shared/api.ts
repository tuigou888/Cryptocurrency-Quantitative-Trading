import axios from 'axios';

const apiClient = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    console.error('[API] Request error:', error);
    return Promise.reject(error);
  }
);

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => response.data,
  (error) => {
    console.error('[API] Response error:', error.response?.data || error.message);
    return Promise.reject(error.response?.data || { error: error.message });
  }
);

// ==================== 概览 API ====================
export const overviewApi = {
  getOverview: () => apiClient.get('/overview'),
};

// ==================== 回测 API ====================
export const backtestApi = {
  runBacktest: (params: {
    strategy: string;
    symbol: string;
    days: number;
    capital: number;
    commission: number;
    slippage: number;
    params: Record<string, any>;
  }) => apiClient.post('/backtest', params),
};

// ==================== 策略对比 API ====================
export const compareApi = {
  getComparison: () => apiClient.get('/compare'),
};

// ==================== 风险分析 API ====================
export const riskApi = {
  getRiskAnalysis: () => apiClient.get('/risk'),
};

// ==================== 实时交易 API ====================
export const liveApi = {
  getLiveData: (strategy: string) => apiClient.get(`/live?strategy=${strategy}`),
};

// ==================== 交易所配置 API ====================
export const exchangeApi = {
  listExchanges: () => apiClient.get('/exchanges'),
  getSupported: () => apiClient.get('/exchanges/supported'),
  getExchange: (id: string) => apiClient.get(`/exchanges/${id}`),
  createExchange: (data: any) => apiClient.post('/exchanges', data),
  updateExchange: (id: string, data: any) => apiClient.put(`/exchanges/${id}`, data),
  deleteExchange: (id: string) => apiClient.delete(`/exchanges/${id}`),
  testConnection: (id: string) => apiClient.get(`/exchanges/${id}/test`),
};

// ==================== 虚拟盘 API ====================
export const sandboxApi = {
  getBalance: (configId: string) => apiClient.get(`/sandbox/balance?config_id=${configId}`),
  placeOrder: (data: any) => apiClient.post('/sandbox/order', data),
  getOrders: (configId: string, symbol?: string) => 
    apiClient.get(`/sandbox/orders?config_id=${configId}${symbol ? `&symbol=${symbol}` : ''}`),
  cancelAllOrders: (configId: string) => apiClient.post('/sandbox/orders/cancel', { config_id: configId }),
  getPositions: (configId: string) => apiClient.get(`/sandbox/positions?config_id=${configId}`),
};

// ==================== 系统配置 API ====================
export const configApi = {
  getSystemConfig: () => apiClient.get('/config'),
  updateSystemConfig: (data: any) => apiClient.post('/config', data),
};

export default {
  overview: overviewApi,
  backtest: backtestApi,
  compare: compareApi,
  risk: riskApi,
  live: liveApi,
  exchange: exchangeApi,
  sandbox: sandboxApi,
  config: configApi,
};
