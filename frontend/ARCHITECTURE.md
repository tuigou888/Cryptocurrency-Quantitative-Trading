# CryptoQuant 前端架构文档

## 📐 Vue 3 + React 18 双框架架构

### 技术栈

| 技术 | 用途 | 版本 |
|------|------|------|
| **Vue 3** | 展示分析模块 | 3.4.x |
| **React 18** | 核心交易模块 | 18.2.x |
| **Vite 5** | 构建工具 | 5.0.x |
| **Pinia** | Vue状态管理 | 2.1.x |
| **Zustand** | React状态管理 | 4.4.x |
| **Vue Router** | Vue路由 | 4.2.x |
| **React Router** | React路由 | 6.21.x |
| **Plotly.js** | 图表库 | 2.27.x |
| **Axios** | HTTP客户端 | 1.6.x |
| **Mitt** | 事件总线 | 3.0.x |
| **TypeScript** | 类型安全 | 5.3.x |

### 架构边界

```
┌────────────────────────────────────────────────────────────────────┐
│                         CryptoQuant Frontend                        │
├────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                      共享层 (Shared)                          │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐             │  │
│  │  │ EventBus   │  │ SharedStore│  │ API Client │             │  │
│  │  │ (mitt)     │  │(localStorage│  │ (axios)    │             │  │
│  │  └────────────┘  └────────────┘  └────────────┘             │  │
│  └──────────────────────────┬───────────────────────────────────┘  │
│                             │                                      │
│  ┌──────────────────────────┴───────────────────────────────────┐  │
│  │                    框架桥接层 (Bridge)                         │  │
│  │  ┌─────────────────────────────────────────────────────────┐ │  │
│  │  │  main.ts - 页面注册表、Vue/React挂载/卸载管理             │ │  │
│  │  └─────────────────────────────────────────────────────────┘ │  │
│  └──────────────────────────┬───────────────────────────────────┘  │
│                             │                                      │
│  ┌──────────────────────────┴───────────────────────────────────┐  │
│  │                  Vue 3 页面层 (展示分析)                        │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │  │
│  │  │ Overview │  │ Compare  │  │  Risk    │  │ Exchange │     │  │
│  │  │  概览页  │  │ 交易分析 │  │ 风险分析 │  │  配置页  │     │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘     │  │
│  │  特点: 数据可视化为主, 状态简单, 适合Vue响应式                  │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                 React 18 页面层 (核心交易)                      │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐                    │  │
│  │  │ Backtest │  │   Live   │  │ Sandbox  │                    │  │
│  │  │ 回测分析 │  │ 实时交易 │  │ 虚拟盘   │                    │  │
│  │  └──────────┘  └──────────┘  └──────────┘                    │  │
│  │  特点: 复杂状态管理, 表单交互, 适合React+Hooks                   │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
```

### 目录结构

```
frontend/
├── index.html                          # 入口HTML
├── package.json                        # 依赖配置
├── vite.config.ts                      # Vite构建配置
├── tsconfig.json                       # TypeScript配置
│
├── src/
│   ├── main.ts                         # 应用入口(桥接层)
│   ├── App.vue                         # Vue主组件(布局+导航)
│   │
│   ├── shared/                         # 共享模块
│   │   ├── eventBus.ts                 # 跨框架事件总线
│   │   ├── sharedStore.ts              # 跨框架状态存储
│   │   └── api.ts                      # API服务层
│   │
│   ├── components/                     # 共享Vue组件
│   │   ├── Sidebar.vue                 # 侧边栏导航
│   │   ├── MetricCard.vue              # 指标卡片
│   │   └── PlotlyChart.vue             # Plotly图表容器
│   │
│   ├── vue/                            # Vue 3页面
│   │   ├── pages/
│   │   │   ├── OverviewPage.vue        # 概览页
│   │   │   ├── ComparePage.vue         # 交易分析页
│   │   │   ├── RiskPage.vue            # 风险分析页
│   │   │   └── ExchangePage.vue        # 交易所配置页
│   │   └── composables/
│   │       ├── useCharts.ts            # 图表组合式函数
│   │       └── useApi.ts               # API组合式函数
│   │
│   ├── react/                          # React 18页面
│   │   ├── pages/
│   │   │   ├── BacktestPage.tsx        # 回测分析页
│   │   │   ├── LiveTradingPage.tsx     # 实时交易页
│   │   │   └── SandboxPage.tsx         # 虚拟盘交易页
│   │   ├── components/
│   │   │   ├── StrategyParams.tsx      # 策略参数面板
│   │   │   ├── OrderForm.tsx           # 下单表单
│   │   │   └── PositionTable.tsx       # 持仓表格
│   │   └── hooks/
│   │       ├── useBacktest.ts          # 回测Hook
│   │       └── useTrading.ts           # 交易Hook
│   │
│   └── styles/
│       └── global.css                  # 全局样式
│
└── tests/                              # 测试文件
    ├── vue/                            # Vue组件测试
    ├── react/                          # React组件测试
    └── shared/                         # 共享模块测试
```

### 通信机制

#### 1. EventBus (跨框架事件)

```typescript
// 发布事件 (任何框架)
EventBus.emit('strategy:selected', { name: 'MA_Cross', params: {...} });

// 订阅事件 (任何框架)
EventBus.on('strategy:selected', (data) => {
  console.log('Strategy selected:', data);
});
```

#### 2. SharedStore (跨框架状态)

```typescript
// 设置状态
sharedStore.set('selectedStrategy', 'MA_Cross');

// 订阅状态变化
sharedStore.subscribe('selectedStrategy', (state) => {
  console.log('Strategy changed:', state.selectedStrategy);
});
```

#### 3. Props传递 (父组件→子组件)

Vue和React各自使用标准的props机制在框架内传递数据。

### 开发规范

#### Vue组件规范

```vue
<!-- 使用Composition API + TypeScript -->
<template>
  <div class="page-container">
    <!-- 模板内容 -->
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';

// 类型定义
interface PageData { /* ... */ }

// 状态
const data = ref<PageData | null>(null);

// 方法
async function loadData() { /* ... */ }

// 生命周期
onMounted(() => { loadData(); });
</script>
```

#### React组件规范

```tsx
// 使用函数组件 + Hooks + TypeScript
import React, { useState, useEffect } from 'react';

interface Props {
  symbol: string;
}

const Component: React.FC<Props> = ({ symbol }) => {
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    // 加载数据
  }, [symbol]);

  return <div>{/* JSX */}</div>;
};

export default Component;
```

### 构建命令

```bash
# 开发模式
npm run dev

# 构建生产版本
npm run build

# 运行测试
npm run test

# 代码格式化
npm run format

# 代码检查
npm run lint
```

### 部署流程

1. `npm run build` 生成 `dist/` 目录
2. 将 `dist/` 部署到静态文件服务器
3. 配置代理 `/api/*` → Flask后端 `http://localhost:8501`
4. 访问 `http://localhost:3000`

### 测试方案

```bash
# 单元测试
vitest run src/shared/

# 组件测试
vitest run src/vue/pages/
vitest run src/react/pages/

# 覆盖率报告
vitest run --coverage
```

### 性能优化

1. **代码分割**: Vite manualChunks将Vue/React/Chart库分开打包
2. **懒加载**: 页面组件按需加载
3. **图表优化**: Plotly.js按需加载图表类型
4. **缓存策略**: SharedStore使用localStorage缓存

### 迁移指南

从原Flask模板迁移到新架构:

1. **HTML模板** → Vue/React组件
2. **原生JS函数** → Vue composables / React hooks
3. **Plotly后端生成** → Plotly前端渲染
4. **DOM状态管理** → Pinia / Zustand

### 兼容性说明

- 浏览器支持: Chrome 90+, Firefox 88+, Safari 14+
- Node.js版本: 18+
- Python后端: Flask 2.3+ (API接口保持不变)
