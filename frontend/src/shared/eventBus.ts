import mitt from 'mitt';

/**
 * 跨框架事件总线
 * 用于Vue和React组件之间的通信
 */
type Events = {
  // 导航事件
  'navigate': { page: string };
  // 策略选择事件
  'strategy:selected': { name: string; params?: Record<string, any> };
  // 回测完成事件
  'backtest:complete': { result: any };
  // 交易执行事件
  'trade:executed': { order: any };
  // 风控警告
  'risk:alert': { message: string; level: string };
  // 全局配置更新
  'config:updated': { key: string; value: any };
  // 数据刷新
  'data:refresh': { target: string };
  // 交易所连接状态
  'exchange:status': { id: string; connected: boolean };
};

export const eventBus = mitt<Events>();

export const EventBus = {
  on: eventBus.on,
  off: eventBus.off,
  emit: eventBus.emit,
};

export default EventBus;
