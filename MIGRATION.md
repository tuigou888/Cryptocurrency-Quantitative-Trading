# 图表层迁移文档：Plotly → ECharts

## 概述

将量化交易项目的可视化层从 **Plotly (后端渲染 JSON)** 改造为 **Plotly (后端数据处理) + ECharts (前端渲染)** 的现代化前后端分离架构。

### 核心变化

| 维度 | 迁移前 | 迁移后 |
|---|---|---|
| 后端图表 | Plotly `go.Figure` → `plotly.io.to_json()` | 自定义标准 JSON Schema |
| 前端图表 | Plotly.js CDN 动态加载渲染 | ECharts 5.x npm 安装 |
| API 响应 | `{ data: [...], layout: {...} }` (Plotly 格式) | `{ code: 0, data: { chart_type, x_axis, series, ... } }` |
| 数据计算 | 与图表渲染耦合在 `dashboard/app.py` | 分离到 `chart_service.py` |

---

## 修改的文件列表

### 新增文件

| 文件 | 用途 |
|---|---|
| `crypto_quant/dashboard/chart_service.py` | 标准化图表数据生成模块 |
| `crypto_quant/dashboard/chart_api.py` | 新 v1 API 路由 (Blueprint) |
| `frontend/src/components/QuantChart.vue` | ECharts 通用图表组件 |
| `frontend/src/shared/chartApi.ts` | 前端 API 客户端 |
| `frontend/public/demo.html` | 独立验证页 (CDN 引入 ECharts) |
| `MIGRATION.md` | 本文档 |

### 修改文件

| 文件 | 变更 |
|---|---|
| `crypto_quant/dashboard/app.py` | 注册 `chart_bp` Blueprint (3 行新增) |
| `frontend/vite.config.ts` | `optimizeDeps.include` 新增 `echarts` |
| `frontend/package.json` | 新增依赖 `echarts` |
| `frontend/src/vue/pages/BacktestPage.vue` | 替换 PlotlyChart → QuantChart，调用 `/api/v1/charts/bundle` |
| `frontend/src/vue/pages/OverviewPage.vue` | 替换 PlotlyChart → QuantChart，调用 `/api/v1/charts/bundle` |
| `frontend/src/vue/pages/RiskPage.vue` | 替换 PlotlyChart → QuantChart，调用 `/api/v1/charts/risk` |
| `frontend/src/vue/pages/ComparePage.vue` | 替换 PlotlyChart → QuantChart，调用 `/api/v1/charts/compare` |
| `frontend/src/vue/pages/LiveTradingPage.vue` | 替换 PlotlyChart → QuantChart，调用 `/api/v1/charts/bundle` |

### 保留不变（向后兼容）

- `crypto_quant/dashboard/app.py` 中原有 Plotly 图表生成函数和路由**完整保留**
- `frontend/src/components/PlotlyChart.vue` **保留**未删除
- 原有 `/api/overview`、`/api/backtest` 等路由**继续可用**

---

## 新增 API 端点列表

所有端点前缀: `/api/v1/charts`

| 方法 | 端点 | 参数 | 返回图表类型 |
|---|---|---|---|
| GET | `/equity_curve` | `strategy_id`, `days`, `capital`, `downsample` | 权益曲线 (line + area) |
| GET | `/drawdown` | `strategy_id`, `days`, `capital` | 回撤曲线 (line, 负值红色填充) |
| GET | `/monthly_heatmap` | `strategy_id`, `days`, `capital` | 月度收益热力图 (heatmap) |
| GET | `/pnl_distribution` | `strategy_id`, `days`, `capital` | 盈亏分布 (bar + line 双Y轴) |
| GET | `/returns` | `strategy_id`, `days`, `capital`, `freq` | 日/周/月收益率 (bar) |
| GET | `/kline` | `days`, `symbol`, `timeframe` | K线 + 成交量 (candlestick + bar) |
| GET | `/compare` | `days`, `capital` | 策略对比 (bar + line) |
| GET | `/risk` | `strategy_id`, `days`, `capital` | 风险分析 (回撤/收益分布/滚动夏普) |
| GET | `/bundle` | `strategy_id`, `days`, `capital` | 捆绑包 (所有图表+指标+交易记录) |

### 统一响应格式

```json
{
  "code": 0,
  "data": {
    "chart_type": "equity_curve",
    "title": "策略收益曲线",
    "subtitle": "夏普: 1.23  胜率: 55.0%",
    "x_axis": { "type": "datetime", "data": ["2024-01-01T00:00:00", ...] },
    "series": [
      {
        "name": "策略净值",
        "type": "line",
        "data": [10000.0, 10012.3, ...],
        "smooth": true,
        "symbol": "none",
        "lineStyle": { "color": "#00d4aa", "width": 2 },
        "areaStyle": { "color": "rgba(0,212,170,0.08)" }
      }
    ],
    "annotations": [
      { "type": "initial_capital", "y": 10000, "text": "初始资金 $10,000" }
    ]
  },
  "message": "ok"
}
```

---

## 前端组件调用示例

### QuantChart.vue 基本用法

```vue
<template>
  <QuantChart
    :chartData="equityData"
    title="权益曲线"
    height="400px"
    :loading="loading"
    @retry="reloadData"
  />
</template>

<script setup lang="ts">
import { ref } from 'vue'
import QuantChart from '@components/QuantChart.vue'
import { chartApi } from '@shared/chartApi'

const equityData = ref(null)
const loading = ref(false)

async function loadEquity() {
  loading.value = true
  try {
    const res = await chartApi.getEquityCurve({
      strategy_id: 'ma_cross',
      days: 60,
      capital: 10000,
      downsample: 2000,
    })
    equityData.value = res.data
  } finally {
    loading.value = false
  }
}
</script>
```

### 使用 Bundle 端点（推荐，减少请求数）

```typescript
const res = await chartApi.getBundle({
  strategy_id: 'ma_cross',
  days: 60,
  capital: 10000,
})

// res.data 包含:
// - metrics: { total_return_pct, sharpe_ratio, max_drawdown_pct, ... }
// - equity_curve: ECharts-ready 权益曲线数据
// - drawdown: ECharts-ready 回撤曲线数据
// - monthly_heatmap: ECharts-ready 热力图数据
// - pnl_distribution: ECharts-ready 盈亏分布数据
// - kline: ECharts-ready K线数据
// - trades: 交易记录数组
```

---

## 大数据量降采样

当图表数据点超过 5000 时，`QuantChart` 组件自动启用 ECharts 的 `large` 模式和 `lttb` 采样。

如需在后端主动降采样，使用 `downsample` 参数：

```
GET /api/v1/charts/equity_curve?strategy_id=ma_cross&days=365&downsample=2000
```

后端使用 LTTB (Largest Triangle Three Buckets) 算法将数据压缩至目标阈值。

---

## 本地验证步骤

### 1. 启动后端

```bash
cd crypto_quant
python -m dashboard.app
# 后端运行在 http://localhost:8501
```

### 2. 启动前端

```bash
cd frontend
npm run dev
# 前端运行在 http://localhost:3000
```

### 3. 验证 API

浏览器访问后端 API 确认 JSON 格式正确：

```
http://localhost:8501/api/v1/charts/equity_curve?strategy_id=ma_cross&days=60&capital=10000
```

应返回 `{ "code": 0, "data": { "chart_type": "equity_curve", ... } }`

### 4. 使用 Demo 页验证图表渲染

浏览器打开 `http://localhost:3000/demo.html`

该页面使用 ECharts CDN 独立渲染所有 6 类图表，不依赖 Vue 框架。

### 5. 使用 Vue 前端完整验证

浏览器打开 `http://localhost:3000`，依次查看：
- 概览页：权益曲线、K线、月度热力图
- 回测分析：运行回测后查看权益、回撤、盈亏分布、热力图
- 交易分析：策略对比图表
- 风险分析：回撤、滚动夏普、收益分布
- 实时交易：价格K线

---

## 严禁事项（已确保合规）

- [x] 未修改核心量化逻辑（回测引擎、订单撮合、指标计算、仓位管理）
- [x] 前端不直接解析 Plotly 完整 Figure JSON
- [x] 前端不做复杂数据计算（回撤、收益统计保留在后端）
- [x] 原有 `/api/overview`、`/api/backtest` 等路由完整保留