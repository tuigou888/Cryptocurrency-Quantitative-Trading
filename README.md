# Cryptocurrency-Quantitative-Trading

专业虚拟货币量化交易系统，支持多交易所、多策略、回测与实盘交易。

## 功能特性

- **多交易所支持**: Binance、OKX、Bybit
- **多种策略**: MA均线交叉、RSI、MACD、网格交易
- **回测系统**: 基于历史数据的策略回测
- **实盘交易**: 支持模拟盘和实盘交易
- **风险管理**: 仓位管理、止损止盈、最大回撤控制
- **专业前端**: Vue + React 双框架，现代化UI设计

## 技术栈

### 后端

| 技术 | 用途 |
|------|------|
| Python 3.10+ | 核心语言 |
| Flask | Web框架 |
| Pandas/NumPy | 数据分析 |
| CCXT | 交易所接口 |
| SQLAlchemy | 数据库ORM |
| pytest | 测试框架 |

### 前端

| 技术 | 用途 |
|------|------|
| Vue 3 | 展示分析模块 |
| React 18 | 核心交易模块 |
| Vite 5 | 构建工具 |
| TypeScript | 类型安全 |
| Plotly.js | 图表库 |
| Inter + JetBrains Mono | 专业字体 |

## 项目结构

```
crypto_quant/
├── backtest/          # 回测引擎
├── config/            # 配置文件
├── core/              # 核心引擎
├── data/              # 数据管理
├── exchange/          # 交易所接口
├── execution/         # 订单执行
├── notification/      # 通知服务
├── portfolio/         # 资产管理
├── risk/              # 风险管理
├── strategy/          # 交易策略
├── utils/             # 工具函数
├── main.py            # CLI入口
└── .env               # 环境变量(需创建)
```

## 快速开始

### 1. 后端安装

```bash
# 克隆项目
git clone <repository-url>
cd Cryptocurrency-Quantitative-Trading

# 安装Python依赖
pip install -r crypto_quant/requirements.txt

# 配置环境变量
cp crypto_quant/.env.example crypto_quant/.env
# 编辑 .env 填入你的API密钥
```

### 2. 前端安装

```bash
cd frontend

# 安装依赖
npm install

# 开发模式
npm run dev

# 构建生产版本
npm run build
```

### 3. 启动服务

```bash
# 启动后端 (8501端口)
cd crypto_quant
python main.py api

# 前端开发服务器 (3000端口)
cd frontend
npm run dev
```

## 前端页面

| 页面 | 路由 | 说明 |
|------|------|------|
| 概览 | `/` | 策略运行概览、权益曲线、交易统计 |
| 回测分析 | `/backtest` | 策略参数配置、历史回测 |
| 交易分析 | `/compare` | 多策略对比分析 |
| 风险分析 | `/risk` | 风险指标、回撤分析 |
| 实时交易 | `/live` | 实时交易监控 |
| 交易所配置 | `/exchanges` | 交易所API配置管理 |
| 虚拟盘交易 | `/sandbox` | 模拟交易界面 |

## 交易策略

### MA均线交叉策略

| 参数 | 默认值 | 说明 |
|------|--------|------|
| fast_period | 10 | 快速均线周期 |
| slow_period | 30 | 慢速均线周期 |

**信号**:
- 金叉(快速均线上穿慢速均线) → 买入
- 死叉(快速均线下穿慢速均线) → 卖出

### RSI策略

| 参数 | 默认值 | 说明 |
|------|--------|------|
| period | 14 | RSI计算周期 |
| oversold | 30 | 超卖阈值 |
| overbought | 70 | 超买阈值 |

### 网格策略

| 参数 | 默认值 | 说明 |
|------|--------|------|
| grid_num | 10 | 网格数量 |
| grid_range_pct | 0.05 | 价格范围百分比 |

## CLI命令

```bash
# 查看状态
python crypto_quant/main.py status

# 获取K线数据
python crypto_quant/main.py fetch -e binance -s BTC/USDT -t 1h -n 500

# 运行回测
python crypto_quant/main.py backtest -st ma_cross -s BTC/USDT -c 10000

# 启动交易
python crypto_quant/main.py trade -st ma_cross -s BTC/USDT --dry-run
```

## 设计系统

前端采用专业金融UI设计系统：

### 色彩系统

```css
--bg-primary: #020617;     /* 深色背景 */
--color-success: #22c55e;  /* 成功/做多 */
--color-danger: #ef4444;   /* 危险/做空 */
--color-warning: #f59e0b;  /* 警告/中性 */
```

### 响应式断点

| 设备 | 断点 |
|------|------|
| 桌面 | >1024px |
| 平板 | 768-1024px |
| 手机 | <768px |

## 配置说明

### 交易所配置

编辑 `crypto_quant/config/exchanges.yaml` 或使用前端界面配置。

### 风险管理

| 参数 | 默认值 | 说明 |
|------|--------|------|
| max_position_size_pct | 10% | 最大单币种仓位 |
| stop_loss_pct | 5% | 止损比例 |
| take_profit_pct | 10% | 止盈比例 |
| max_drawdown_pct | 20% | 最大回撤限制 |

## 注意事项

1. **实盘交易风险**: 实盘交易存在风险，务必先在模拟盘充分测试
2. **API密钥安全**: 不要将API密钥提交到公开仓库
3. **参数优化**: 不同交易对可能需要不同的策略参数
4. **网络稳定**: 实盘交易需要稳定的网络连接

## 文档

| 文档 | 说明 |
|------|------|
| [README](README.md) | 项目主文档 |
| [EVALUATION](EVALUATION.md) | 项目评估报告 |
| [IMPROVEMENT](IMPROVEMENT_REPORT.md) | 改进报告 |
| [前端架构](frontend/ARCHITECTURE.md) | 前端技术架构 |

## 许可证

MIT License
