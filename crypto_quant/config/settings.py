import os
import yaml
from pathlib import Path
from dotenv import load_dotenv
from config import CONFIG_DIR

load_dotenv()


def _resolve_env(value):
    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
        env_key = value[2:-1]
        return os.environ.get(env_key, "")
    return value


def _resolve_dict(d):
    result = {}
    for k, v in d.items():
        if isinstance(v, dict):
            result[k] = _resolve_dict(v)
        elif isinstance(v, list):
            result[k] = [_resolve_dict(i) if isinstance(i, dict) else _resolve_env(i) for i in v]
        else:
            result[k] = _resolve_env(v)
    return result


class Settings:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._loaded = False
        return cls._instance

    def __init__(self):
        if self._loaded:
            return
        self._loaded = True
        self._config = {}
        self.reload()

    def reload(self):
        config_path = CONFIG_DIR / "exchanges.yaml"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                self._config = _resolve_dict(yaml.safe_load(f) or {})

    @property
    def exchanges(self):
        return self._config.get("exchanges", {})

    @property
    def trading(self):
        return self._config.get("trading", {})

    @property
    def risk(self):
        return self._config.get("risk", {})

    @property
    def backtest(self):
        return self._config.get("backtest", {})

    @property
    def notification(self):
        return self._config.get("notification", {})

    @property
    def data(self):
        return self._config.get("data", {})

    def get(self, key, default=None):
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            if value is None:
                return default
        return value

    def to_dict(self):
        return {
            "exchanges": self.exchanges,
            "trading": self.trading,
            "risk": self.risk,
            "backtest": self.backtest,
            "notification": self.notification,
            "data": self.data,
        }


settings = Settings()
