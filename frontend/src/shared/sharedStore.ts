/**
 * 跨框架共享状态存储
 * 基于localStorage/sessionStorage实现Vue和React之间的状态同步
 */

const STORAGE_KEY = 'crypto_quant_shared_state';

interface SharedState {
  activePage: string;
  selectedExchange: string | null;
  selectedSymbol: string;
  selectedStrategy: string | null;
  backtestParams: Record<string, any>;
  theme: 'dark' | 'light';
  language: 'zh-CN' | 'en-US';
  sandboxConfigId: string | null;
  lastRefreshTime: number | null;
}

const defaultState: SharedState = {
  activePage: 'overview',
  selectedExchange: 'binance',
  selectedSymbol: 'BTC/USDT',
  selectedStrategy: null,
  backtestParams: {
    days: 180,
    capital: 10000,
    commission: 0.001,
    slippage: 0.0005,
  },
  theme: 'dark',
  language: 'zh-CN',
  sandboxConfigId: null,
  lastRefreshTime: null,
};

class SharedStore {
  private state: SharedState;
  private listeners: Map<string, Set<(state: SharedState) => void>>;

  constructor() {
    this.state = this.loadFromStorage();
    this.listeners = new Map();
  }

  private loadFromStorage(): SharedState {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        return { ...defaultState, ...JSON.parse(stored) };
      }
    } catch (e) {
      console.warn('Failed to load shared state from storage:', e);
    }
    return { ...defaultState };
  }

  private saveToStorage(): void {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(this.state));
    } catch (e) {
      console.warn('Failed to save shared state to storage:', e);
    }
  }

  getState(): SharedState {
    return { ...this.state };
  }

  get<K extends keyof SharedState>(key: K): SharedState[K] {
    return this.state[key];
  }

  set<K extends keyof SharedState>(key: K, value: SharedState[K]): void {
    this.state[key] = value;
    this.saveToStorage();
    this.notify(key);
  }

  update(updates: Partial<SharedState>): void {
    this.state = { ...this.state, ...updates };
    this.saveToStorage();
    Object.keys(updates).forEach(key => this.notify(key as keyof SharedState));
  }

  subscribe<K extends keyof SharedState>(key: K, callback: (state: SharedState) => void): () => void {
    if (!this.listeners.has(key)) {
      this.listeners.set(key, new Set());
    }
    this.listeners.get(key)!.add(callback);

    // 立即执行一次获取当前状态
    callback(this.state);

    return () => {
      this.listeners.get(key)?.delete(callback);
    };
  }

  private notify<K extends keyof SharedState>(key: K): void {
    const subs = this.listeners.get(key);
    if (subs) {
      subs.forEach(cb => cb(this.state));
    }
  }

  reset(): void {
    this.state = { ...defaultState };
    this.saveToStorage();
    Object.keys(defaultState).forEach(key => {
      this.notify(key as keyof SharedState);
    });
  }
}

export const sharedStore = new SharedStore();
export default sharedStore;
