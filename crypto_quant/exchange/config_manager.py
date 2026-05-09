import json
from pathlib import Path
from datetime import datetime
from typing import Optional

import ccxt

from exchange.base import OrderSide, OrderType, MarketType
from utils.logger import logger

CONFIG_FILE = Path(__file__).resolve().parent.parent / "data" / "exchange_configs.json"


def _load_configs() -> dict:
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_configs(configs: dict):
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(configs, f, indent=2, ensure_ascii=False)


def list_exchange_configs() -> list:
    configs = _load_configs()
    result = []
    for eid, cfg in configs.items():
        result.append({
            "id": eid,
            "name": cfg.get("name", eid),
            "exchange_id": cfg.get("exchange_id", eid),
            "sandbox": cfg.get("sandbox", False),
            "market_type": cfg.get("market_type", "spot"),
            "has_api_key": bool(cfg.get("api_key", "")),
            "has_secret": bool(cfg.get("secret", "")),
            "created_at": cfg.get("created_at", ""),
            "updated_at": cfg.get("updated_at", ""),
        })
    return result


def get_exchange_config(config_id: str) -> Optional[dict]:
    configs = _load_configs()
    return configs.get(config_id)


def save_exchange_config(config_id: str, data: dict) -> dict:
    configs = _load_configs()
    now = datetime.now().isoformat()
    if config_id in configs:
        data["updated_at"] = now
        data["created_at"] = configs[config_id].get("created_at", now)
    else:
        data["created_at"] = now
        data["updated_at"] = now
    configs[config_id] = data
    _save_configs(configs)
    return data


def delete_exchange_config(config_id: str) -> bool:
    configs = _load_configs()
    if config_id in configs:
        del configs[config_id]
        _save_configs(configs)
        return True
    return False


def test_exchange_connection(config_id: str) -> dict:
    cfg = get_exchange_config(config_id)
    if not cfg:
        return {"success": False, "error": f"配置 '{config_id}' 不存在"}

    try:
        exchange = _create_exchange_from_config(cfg)
        exchange.fetch_markets()
        ticker = exchange.fetch_ticker("BTC/USDT")
        balance = exchange.fetch_balance()
        usdt_free = balance.get("free", {}).get("USDT", 0) or 0
        exchange.close()
        return {
            "success": True,
            "message": f"连接成功！BTC/USDT 最新价: {ticker.get('last', 'N/A')}",
            "btc_price": ticker.get("last", 0),
            "usdt_balance": usdt_free,
            "sandbox": cfg.get("sandbox", False),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def _create_exchange_from_config(cfg: dict) -> ccxt.Exchange:
    exchange_id = cfg.get("exchange_id", "binance")
    exchange_class = getattr(ccxt, exchange_id, None)
    if not exchange_class:
        raise ValueError(f"ccxt 不支持交易所 '{exchange_id}'")

    config = {
        "apiKey": cfg.get("api_key", ""),
        "secret": cfg.get("secret", ""),
        "enableRateLimit": True,
        "rateLimit": cfg.get("rate_limit", 1000),
        "options": cfg.get("options", {}),
    }

    if exchange_id == "okx" and cfg.get("password"):
        config["password"] = cfg["password"]

    if cfg.get("sandbox", False):
        config["options"]["sandboxMode"] = True

    exchange = exchange_class(config)

    market_type = cfg.get("market_type", "spot")
    if market_type in ("swap", "future"):
        exchange.options["defaultType"] = "swap"
    else:
        exchange.options["defaultType"] = "spot"

    return exchange


def get_exchange_instance(config_id: str) -> Optional[ccxt.Exchange]:
    cfg = get_exchange_config(config_id)
    if not cfg:
        return None
    return _create_exchange_from_config(cfg)


def get_supported_exchanges() -> list:
    exchanges = []
    for eid in ccxt.exchanges:
        try:
            ex = getattr(ccxt, eid)
            has_sandbox = bool(ex.has.get("sandboxMode", False))
            exchanges.append({
                "id": eid,
                "name": eid.replace("_", " ").title(),
                "has_sandbox": has_sandbox,
            })
        except Exception:
            continue
    return sorted(exchanges, key=lambda x: x["id"])
