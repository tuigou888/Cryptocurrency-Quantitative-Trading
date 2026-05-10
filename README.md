# Cryptocurrency-Quantitative-Trading

虚拟货币量化交易系统，支持多交易所、多策略、回测与实盘交易。

## 功能特性

- **多交易所支持**: Binance、OKX、Bybit
- **多种策略**: 均线交叉(MACD)、RSI、网格交易
- **回测系统**: 基于历史数据的策略回测
- **实盘交易**: 支持模拟盘和实盘交易
- **风险管理**: 仓位管理、止损止盈、最大回撤控制
- **数据管理**: K线数据获取、存储与管理
- **实时通知**: Telegram 消息推送

## 项目结构

```
crypto_quant/
├── backtest/          # 回测引擎
├── config/            # 配置文件
│   ├── settings.py    # 配置加载器
│   └── exchanges.yaml # 交易所配置
├── core/              # 核心引擎
│   ├── engine.py      # 交易引擎
│   └── event_bus.py   # 事件总线
├── data/              # 数据管理
│   ├── manager.py     # 数据管理器
│   └── storage.py     # 数据存储
├── exchange/          # 交易所接口
│   ├── base.py        # 基础接口定义
│   └── ccxt_connector.py # CCXT连接器
├── execution/         # 订单执行
│   └── order_manager.py
├── notification/       # 通知服务
│   └── notifier.py
├── portfolio/         # 资产管理
│   └── tracker.py
├── risk/              # 风险管理
│   └── manager.py
├── strategy/          # 交易策略
│   ├── base.py        # 策略基类
│   ├── ma_cross.py    # 均线交叉策略
│   ├── rsi.py         # RSI策略
│   └── grid.py        # 网格策略
├── utils/             # 工具函数
│   └── logger.py      # 日志工具
├── main.py            # CLI入口
└── .env               # 环境变量(需创建)
```

## 安装

### 环境要求

- Python 3.10+
- Windows/Linux/macOS

### 安装依赖

```bash
pip install -r crypto_quant/requirements.txt
```

### 配置环境变量

复制 `.env.example` 为 `.env`，并填入你的API密钥：

```env
# Binance
BINANCE_API_KEY=your_binance_api_key
BINANCE_SECRET=your_binance_secret

# OKX
OKX_API_KEY=your_okx_api_key
OKX_SECRET=your_okx_secret
OKX_PASSPHRASE=your_okx_passphrase

# Bybit
BYBIT_API_KEY=your_bybit_api_key
BYBIT_SECRET=your_bybit_secret

# Telegram通知(可选)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
```

## 使用方法

### 查看系统状态

```bash
python crypto_quant/main.py status
```

### 获取市场行情

```bash
# 查看交易对列表
python crypto_quant/main.py markets -e binance -m spot

# 获取实时行情
python crypto_quant/main.py ticker -e binance -s BTC/USDT
```

### 获取历史数据

```bash
python crypto_quant/main.py fetch -e binance -s BTC/USDT -t 1h -n 500
```

### 策略回测

```bash
# 均线交叉策略(默认)
python crypto_quant/main.py backtest -st ma_cross -s BTC/USDT -t 1h -c 10000

# RSI策略
python crypto_quant/main.py backtest -st rsi -s BTC/USDT -t 1h -c 10000

# 网格策略
python crypto_quant/main.py backtest -st grid -s BTC/USDT -t 1h -c 10000

# 自定义策略参数
python crypto_quant/main.py backtest -st ma_cross -s ETH/USDT -p fast_period=20 -p slow_period=50
```

### 获取策略信号

```bash
python crypto_quant/main.py signal -st ma_cross -s BTC/USDT
```

### 启动交易

```bash
# 模拟盘交易(默认)
python crypto_quant/main.py trade -st ma_cross -s BTC/USDT --dry-run

# 实盘交易
python crypto_quant/main.py trade -st ma_cross -s BTC/USDT --live
```

## 交易策略

### 均线交叉策略 (MA_Cross)

通过快速均线与慢速均线的交叉来判断买卖信号。

| 参数 | 默认值 | 说明 |
|------|--------|------|
| fast_period | 10 | 快速均线周期 |
| slow_period | 30 | 慢速均线周期 |

**原理**:
- 金叉(快速均线上穿慢速均线) → 买入信号
- 死叉(快速均线下穿慢速均线) → 卖出信号

### RSI策略

基于相对强弱指数(RSI)的超买超卖策略。

| 参数 | 默认值 | 说明 |
|------|--------|------|
| period | 14 | RSI计算周期 |
| oversold | 30 | 超卖阈值 |
| overbought | 70 | 超买阈值 |

**原理**:
- RSI < 30 → 超卖 → 买入信号
- RSI > 70 → 超买 → 卖出信号

### 网格策略 (Grid)

在指定价格范围内设置网格，低买高卖。

| 参数 | 默认值 | 说明 |
|------|--------|------|
| grid_num | 10 | 网格数量 |
| grid_range_pct | 0.05 | 价格范围百分比 |
| amount_per_grid | 0.001 | 每格交易数量 |

**原理**:
- 价格低于中心价 → 买入
- 价格高于中心价 → 卖出

## 配置说明

### exchanges.yaml

交易所API配置，支持 Binance、OKX、Bybit。

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

## 技术栈

- **交易所接口**: CCXT
- **数据分析**: Pandas, NumPy
- **技术指标**: TA-Lib
- **数据库**: SQLite (通过 SQLAlchemy)
- **任务调度**: APScheduler
- **CLI界面**: Click, Rich
