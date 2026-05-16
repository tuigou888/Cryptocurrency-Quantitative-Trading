import { createRouter, createWebHistory } from 'vue-router';

const routes = [
  {
    path: '/',
    name: 'overview',
    component: () => import('../vue/pages/OverviewPage.vue'),
    meta: { title: '概览' },
  },
  {
    path: '/backtest',
    name: 'backtest',
    component: () => import('../vue/pages/BacktestPage.vue'),
    meta: { title: '回测分析' },
  },
  {
    path: '/compare',
    name: 'compare',
    component: () => import('../vue/pages/ComparePage.vue'),
    meta: { title: '交易分析' },
  },
  {
    path: '/risk',
    name: 'risk',
    component: () => import('../vue/pages/RiskPage.vue'),
    meta: { title: '风险分析' },
  },
  {
    path: '/live',
    name: 'live',
    component: () => import('../vue/pages/LiveTradingPage.vue'),
    meta: { title: '实时交易' },
  },
  {
    path: '/exchanges',
    name: 'exchanges',
    component: () => import('../vue/pages/ExchangePage.vue'),
    meta: { title: '交易所配置' },
  },
  {
    path: '/sandbox',
    name: 'sandbox',
    component: () => import('../vue/pages/SandboxPage.vue'),
    meta: { title: '虚拟盘交易' },
  },
  {
    path: '/monthly-returns',
    name: 'monthly-returns',
    component: () => import('../vue/pages/MonthlyReturnsPage.vue'),
    meta: { title: '月度收益' },
  },
  {
    path: '/chart-test',
    name: 'chart-test',
    component: () => import('../vue/pages/ChartTestPage.vue'),
    meta: { title: '图表测试' },
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;
