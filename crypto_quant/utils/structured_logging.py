import logging
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Any, Dict
from dataclasses import asdict, is_dataclass


class JsonFormatter(logging.Formatter):
    """
    JSON 结构化日志格式化器。
    输出包含: timestamp, level, name, message, extra_fields。
    """

    def __init__(self, include_extra: bool = True):
        super().__init__()
        self.include_extra = include_extra

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        if self.include_extra and hasattr(record, "extra_fields"):
            log_entry["fields"] = record.extra_fields

        if hasattr(record, "trade_id"):
            log_entry["trade_id"] = record.trade_id
        if hasattr(record, "strategy"):
            log_entry["strategy"] = record.strategy
        if hasattr(record, "symbol"):
            log_entry["symbol"] = record.symbol
        if hasattr(record, "pnl"):
            log_entry["pnl"] = record.pnl

        return json.dumps(log_entry, ensure_ascii=False, default=str)


class StructuredLogger:
    """
    结构化日志记录器，支持：
    - JSON 输出到文件
    - 彩色控制台输出
    - 审计追踪
    - 上下文字段注入
    """

    def __init__(
        self,
        name: str = "crypto_quant",
        level: int = logging.INFO,
        log_file: Optional[Path] = None,
        audit_file: Optional[Path] = None,
    ):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        self.logger.handlers.clear()

        self._context: Dict[str, Any] = {}
        self._audit_file = audit_file

        formatter = JsonFormatter(include_extra=True)
        console_formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)-8s %(name)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(logging.INFO)
        self.logger.addHandler(console_handler)

        if log_file:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setFormatter(formatter)
            file_handler.setLevel(logging.DEBUG)
            self.logger.addHandler(file_handler)

        if self._audit_file:
            self._audit_file.parent.mkdir(parents=True, exist_ok=True)

    def set_context(self, **kwargs):
        self._context.update(kwargs)

    def clear_context(self):
        self._context.clear()

    def _make_record(self, level: int, message: str, **kwargs):
        record = self.logger.makeRecord(
            self.logger.name,
            level,
            "(unknown)",
            0,
            message,
            (),
            None,
        )
        record.extra_fields = {**self._context, **kwargs}
        return record

    def _log(self, level: int, message: str, **kwargs):
        record = self._make_record(level, message, **kwargs)
        self.logger.handle(record)

    def debug(self, message: str, **kwargs):
        self._log(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs):
        self._log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs):
        self._log(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs):
        self._log(logging.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs):
        self._log(logging.CRITICAL, message, **kwargs)

    def audit(self, action: str, entity: str, entity_id: str, details: Optional[Dict] = None):
        """
        审计日志：记录所有关键业务操作。
        用于合规追踪和审计。
        """
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "action": action,
            "entity": entity,
            "entity_id": entity_id,
            "details": details or {},
            **{k: v for k, v in self._context.items() if k not in ("action", "entity", "entity_id")},
        }

        if self._audit_file:
            with open(self._audit_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")

        self.info(f"AUDIT: {action} {entity}[{entity_id}]", audit=True, **entry)

    def log_trade(self, trade_id: str, action: str, symbol: str, side: str, amount: float, price: float, pnl: Optional[float] = None, **kwargs):
        self.info(
            f"Trade {action}: {side} {amount} {symbol} @ {price}",
            trade_id=trade_id,
            symbol=symbol,
            side=side,
            amount=amount,
            price=price,
            pnl=pnl,
            **kwargs,
        )


def setup_structured_logging(
    name: str = "crypto_quant",
    level: int = logging.INFO,
    log_dir: Optional[Path] = None,
) -> StructuredLogger:
    if log_dir is None:
        from config import LOG_DIR
        log_dir = LOG_DIR

    log_file = log_dir / "trading.json.log" if log_dir else None
    audit_file = log_dir / "audit.json.log" if log_dir else None

    return StructuredLogger(name=name, level=level, log_file=log_file, audit_file=audit_file)


structured_logger = setup_structured_logging()
