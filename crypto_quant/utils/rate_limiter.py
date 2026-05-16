from datetime import datetime, timedelta
from typing import Optional
from collections import deque
import time


class RateLimiter:
    """
    滑动窗口速率限制器。
    防止 API 调用超出交易所限制。
    """

    def __init__(self, calls: int = 10, period: float = 60.0):
        self.calls = calls
        self.period = period
        self._timestamps = deque()

    def allow(self) -> bool:
        now = datetime.now()
        cutoff = now - timedelta(seconds=self.period)

        while self._timestamps and self._timestamps[0] < cutoff:
            self._timestamps.popleft()

        if len(self._timestamps) < self.calls:
            self._timestamps.append(now)
            return True
        return False

    def wait_and_allow(self) -> float:
        """等待直到允许调用，返回等待秒数"""
        while True:
            if self.allow():
                return 0.0

            if self._timestamps:
                wait_time = self.period - (datetime.now() - self._timestamps[0]).total_seconds()
                if wait_time > 0:
                    time.sleep(min(wait_time, 1.0))
                    continue
            return 0.0

    def reset(self):
        self._timestamps.clear()

    @property
    def remaining(self) -> int:
        now = datetime.now()
        cutoff = now - timedelta(seconds=self.period)
        active = sum(1 for ts in self._timestamps if ts >= cutoff)
        return max(0, self.calls - active)
