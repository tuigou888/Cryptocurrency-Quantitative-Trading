# CryptoQuant 前端架构文档

## 📐 Vue 3 + React 18 双框架架构

### 技术栈

| 技术 | 用途 | 版本 |
|------|------|------|
| **Vue 3** | 展示分析模块 | 3.4.x |
| **React 18** | 核心交易模块 | 18.2.x |
| **Vite 5** | 构建工具 | 5.0.x |
| **Vue Router** | Vue路由 | 4.2.x |
| **React Router** | React路由 | 6.21.x |
| **Plotly.js** | 图表库 | 2.27.x |
| **Axios** | HTTP客户端 | 1.6.x |
| **Mitt** | 事件总线 | 3.0.x |
| **TypeScript** | 类型安全 | 5.3.x |
| **Inter** | UI字体 | - |
| **JetBrains Mono** | 数字字体 | - |

### 架构边界

```
┌────────────────────────────────────────────────────────────────────┐
│                         CryptoQuant Frontend                        │
├────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                      共享层 (Shared)                          │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐           │  │
│  │  │ EventBus   │  │ SharedStore│  │ API Client │           │  │
│  │  │ (mitt)     │  │(localStorage│  │ (axios)    │           │  │
│  │  └────────────┘  └────────────┘  └────────────┘           │  │
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
│   │   ├── Icons.vue                   # SVG图标组件
│   │   ├── Sidebar.vue                 # 侧边栏导航
│   │   ├── MetricCard.vue              # 指标卡片
│   │   └── PlotlyChart.vue            # Plotly图表容器
│   │
│   ├── vue/                            # Vue 3页面
│   │   └── pages/
│   │       ├── OverviewPage.vue        # 概览页
│   │       ├── BacktestPage.vue        # 回测分析页
│   │       ├── LiveTradingPage.vue     # 实时交易页
│   │       ├── RiskPage.vue            # 风险分析页
│   │       ├── ComparePage.vue         # 交易分析页
│   │       ├── ExchangePage.vue        # 交易所配置页
│   │       └── SandboxPage.vue         # 虚拟盘交易页
│   │
│   └── styles/
│       └── global.css                  # 全局样式(设计系统)
│
└── tests/                              # 测试文件
```

---

## 🎨 设计系统

### 设计令牌

#### 色彩系统

```css
:root {
  /* 背景色 */
  --bg-primary: #020617;        /* 主背景 */
  --bg-secondary: #0f172a;      /* 次级背景 */
  --bg-tertiary: #1e293b;       /* 卡片背景 */
  --bg-card: #1e293b;           /* 卡片 */
  --bg-card-hover: #334155;     /* 卡片悬停 */
  --bg-input: #0f172a;          /* 输入框 */

  /* 边框 */
  --border-color: #334155;
  --border-color-light: #475569;
  --border-color-subtle: rgba(148, 163, 184, 0.1);

  /* 文字 */
  --text-primary: #f8fafc;
  --text-secondary: #94a3b8;
  --text-muted: #64748b;
  --text-disabled: #475569;

  /* 功能色 */
  --color-success: #22c55e;
  --color-danger: #ef4444;
  --color-warning: #f59e0b;
  --color-info: #3b82f6;

  /* 金融专用色 */
  --color-long: #22c55e;        /* 做多 */
  --color-short: #ef4444;       /* 做空 */
  --color-neutral: #f59e0b;     /* 中性 */
}
```

#### 布局系统

```css
:root {
  --sidebar-width: 240px;
  --sidebar-collapsed-width: 64px;
  --header-height: 64px;
  --radius-sm: 6px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-xl: 16px;
}
```

#### 动画系统

```css
:root {
  --transition-fast: 150ms;
  --transition-normal: 250ms;
  --transition-slow: 350ms;
  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
  --ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1);
}
```

### 响应式断点

| 断点 | 设备类型 | 布局 |
|------|---------|------|
| >1024px | 桌面端 | 双列图表、四列指标 |
| 768-1024px | 平板端 | 单列图表、双列指标 |
| 480-768px | 大屏手机 | 单列全宽、折叠侧边栏 |
| 360-480px | 小屏手机 | 紧凑布局 |
| <360px | 超小屏 | 最小可用布局 |

### 微交互动画

| 动画类型 | 效果 | 持续时间 |
|----------|------|---------|
| 页面进入 | 淡入+上移 | 400ms |
| 卡片交错 | 依次延迟进入 | 50ms/卡片 |
| 按钮波纹 | 点击波纹扩散 | 300ms |
| 导航下划线 | 悬停滑入 | 300ms |
| 模态框 | 淡入+上滑 | 200-300ms |
| 状态脉冲 | 指示灯呼吸效果 | 2s循环 |

---

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

---

### 开发规范

#### Vue组件规范

```vue
<template>
  <div class="page-container">
    <h1 class="page-header">
      <span class="page-header-icon">
        <Icons name="chart-line" :size="20" />
      </span>
      页面标题
    </h1>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import Icons from '@components/Icons.vue';

interface PageData { /* ... */ }

const data = ref<PageData | null>(null);

async function loadData() { /* ... */ }

onMounted(() => { loadData(); });
</script>

<style scoped>
/* 使用全局CSS变量，无需重复定义颜色 */
</style>
```

#### React组件规范

```tsx
import React, { useState, useEffect } from 'react';
import Icons from '@components/Icons.vue';

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

---

### 构建命令

```bash
# 安装依赖
npm install

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

---

### 部署流程

1. `npm run build` 生成 `dist/` 目录
2. 将 `dist/` 部署到静态文件服务器
3. 配置代理 `/api/*` → Flask后端 `http://localhost:8501`
4. 访问 `http://localhost:3000`

---

### 性能优化

1. **代码分割**: Vite manualChunks将Vue/React/Chart库分开打包
2. **懒加载**: 页面组件按需加载
3. **图表优化**: Plotly.js按需加载图表类型
4. **缓存策略**: SharedStore使用localStorage缓存
5. **响应式图片**: 根据设备像素比加载合适分辨率

---

### 兼容性说明

- 浏览器支持: Chrome 90+, Firefox 88+, Safari 14+, Edge 90+
- Node.js版本: 18+
- Python后端: Flask 2.3+ (API接口保持不变)
- 支持触控设备和减少动画偏好设置

---

*最后更新: 2026-05-12*
