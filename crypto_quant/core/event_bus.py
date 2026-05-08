from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Optional


class EventType(Enum):
    TICK = "tick"
    SIGNAL = "signal"
    ORDER_FILLED = "order_filled"
    ORDER_REJECTED = "order_rejected"
    RISK_ALERT = "risk_alert"
    POSITION_OPENED = "position_opened"
    POSITION_CLOSED = "position_closed"
    STRATEGY_START = "strategy_start"
    STRATEGY_STOP = "strategy_stop"
    ERROR = "error"


@dataclass
class Event:
    event_type: EventType
    data: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


class EventBus:
    def __init__(self):
        self._handlers = {}

    def subscribe(self, event_type: EventType, handler: Callable):
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: EventType, handler: Callable):
        if event_type in self._handlers:
            self._handlers[event_type] = [h for h in self._handlers[event_type] if h != handler]

    def publish(self, event: Event):
        handlers = self._handlers.get(event.event_type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                from utils.logger import logger
                logger.error(f"Event handler error for {event.event_type}: {e}")

    def clear(self):
        self._handlers.clear()
