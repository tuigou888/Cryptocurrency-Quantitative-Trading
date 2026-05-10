import React from 'react';
import ReactDOM from 'react-dom/client';
import { createApp } from 'vue';
import App from './App.vue';
import './styles/global.css';

// React组件
import BacktestPage from './react/pages/BacktestPage';
import LiveTradingPage from './react/pages/LiveTradingPage';
import SandboxPage from './react/pages/SandboxPage';

// Vue组件
import OverviewPage from './vue/pages/OverviewPage.vue';
import ComparePage from './vue/pages/ComparePage.vue';
import RiskPage from './vue/pages/RiskPage.vue';
import ExchangePage from './vue/pages/ExchangePage.vue';

// 页面注册表
const pageComponents: Record<string, any> = {
  // Vue页面
  overview: { framework: 'vue', component: OverviewPage },
  compare: { framework: 'vue', component: ComparePage },
  risk: { framework: 'vue', component: RiskPage },
  exchanges: { framework: 'vue', component: ExchangePage },
  // React页面
  backtest: { framework: 'react', component: BacktestPage },
  live: { framework: 'react', component: LiveTradingPage },
  sandbox: { framework: 'react', component: SandboxPage },
};

// Vue/React挂载容器管理
const vueInstances: Map<string, any> = new Map();
const reactRoots: Map<string, any> = new Map();

// 页面渲染函数
function renderPage(pageName: string) {
  // 清理所有页面
  const pages = document.querySelectorAll('.page');
  pages.forEach(p => p.classList.remove('active'));
  
  // 隐藏或销毁旧实例
  cleanupPage(pageName);
  
  const pageConfig = pageComponents[pageName];
  if (!pageConfig) {
    console.warn(`Page "${pageName}" not found`);
    return;
  }

  const containerId = `page-${pageName}`;
  let container = document.getElementById(containerId);
  
  if (!container) {
    container = document.createElement('div');
    container.id = containerId;
    container.className = 'page active';
    container.dataset.framework = pageConfig.framework;
    document.getElementById('pages-container')?.appendChild(container);
  } else {
    container.classList.add('active');
  }

  if (pageConfig.framework === 'vue') {
    mountVue(containerId, pageConfig.component);
  } else {
    mountReact(containerId, pageConfig.component);
  }
}

function mountVue(containerId: string, component: any) {
  if (vueInstances.has(containerId)) {
    vueInstances.get(containerId).unmount();
  }
  const container = document.getElementById(containerId);
  if (container) {
    container.innerHTML = '';
    const app = createApp(component);
    app.mount(container);
    vueInstances.set(containerId, app);
  }
}

function mountReact(containerId: string, component: any) {
  if (reactRoots.has(containerId)) {
    reactRoots.get(containerId).unmount();
  }
  const container = document.getElementById(containerId);
  if (container) {
    container.innerHTML = '';
    const root = ReactDOM.createRoot(container);
    root.render(React.createElement(component));
    reactRoots.set(containerId, root);
  }
}

function cleanupPage(pageName: string) {
  const containerId = `page-${pageName}`;
  if (vueInstances.has(containerId)) {
    vueInstances.get(containerId).unmount();
    vueInstances.delete(containerId);
  }
  if (reactRoots.has(containerId)) {
    reactRoots.get(containerId).unmount();
    reactRoots.delete(containerId);
  }
}

// 初始化应用
function initApp() {
  // 创建页面容器
  const pagesContainer = document.createElement('div');
  pagesContainer.id = 'pages-container';
  document.body.appendChild(pagesContainer);
  
  // 创建Vue主应用（负责布局和导航）
  const root = document.createElement('div');
  root.id = 'vue-app';
  document.body.appendChild(root);
  
  const app = createApp(App);
  app.mount('#vue-app');
  
  // 注册全局页面渲染函数
  (window as any).renderPage = renderPage;
  (window as any).pageComponents = pageComponents;
  
  // 默认加载概览页
  setTimeout(() => renderPage('overview'), 100);
}

export { renderPage, mountVue, mountReact, cleanupPage, pageComponents };
export default initApp;

// 启动应用
initApp();
