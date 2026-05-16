import axios from 'axios'

const apiClient = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

apiClient.interceptors.response.use(
  (response) => response.data,
  (error) => {
    console.error('[ChartAPI] 响应错误:', error.response?.data || error.message)
    return Promise.reject(error.response?.data || { error: error.message })
  },
)

export const chartApi = {
  getEquityCurve: (params?: {
    strategy_id?: string
    days?: number
    capital?: number
    downsample?: number
  }) => apiClient.get('/charts/equity_curve', { params }),

  getDrawdown: (params?: {
    strategy_id?: string
    days?: number
    capital?: number
  }) => apiClient.get('/charts/drawdown', { params }),

  getMonthlyHeatmap: (params?: {
    strategy_id?: string
    days?: number
    capital?: number
  }) => apiClient.get('/charts/monthly_heatmap', { params }),

  getPnlDistribution: (params?: {
    strategy_id?: string
    days?: number
    capital?: number
  }) => apiClient.get('/charts/pnl_distribution', { params }),

  getReturns: (params?: {
    strategy_id?: string
    days?: number
    capital?: number
    freq?: 'daily' | 'weekly' | 'monthly'
  }) => apiClient.get('/charts/returns', { params }),

  getKline: (params?: {
    days?: number
    symbol?: string
    timeframe?: string
  }) => apiClient.get('/charts/kline', { params }),

  getCompare: (params?: {
    days?: number
    capital?: number
  }) => apiClient.get('/charts/compare', { params }),

  getRisk: (params?: {
    strategy_id?: string
    days?: number
    capital?: number
  }) => apiClient.get('/charts/risk', { params }),

  getBundle: (params?: {
    strategy_id?: string
    days?: number
    capital?: number
  }) => apiClient.get('/charts/bundle', { params }),
}

export default chartApi