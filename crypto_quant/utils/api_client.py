import time
import random
from functools import wraps
from typing import Callable, Any, Optional, Type
from datetime import datetime, timedelta
from enum import Enum

from utils.logger import logger


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout_seconds: float = 60.0,
        half_open_max_calls: int = 3,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = timedelta(seconds=recovery_timeout_seconds)
        self.half_open_max_calls = half_open_max_calls

        self._failure_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._state = CircuitState.CLOSED
        self._half_open_calls = 0

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            if self._last_failure_time and datetime.now() - self._last_failure_time >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
        return self._state

    @property
    def failure_count(self) -> int:
        return self._failure_count

    def can_execute(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.HALF_OPEN:
            return self._half_open_calls < self.half_open_max_calls
        return False

    def record_failure(self):
        self._failure_count += 1
        self._last_failure_time = datetime.now()

        if self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
            logger.warning(f"Circuit breaker opened after {self._failure_count} failures")

    def record_success(self):
        if self.state == CircuitState.HALF_OPEN:
            self._half_open_calls += 1
            if self._half_open_calls >= self.half_open_max_calls:
                self._failure_count = 0
                self._state = CircuitState.CLOSED
                logger.info("Circuit breaker closed after successful half-open calls")
        elif self.state == CircuitState.CLOSED:
            self._failure_count = max(0, self._failure_count - 1)


def with_exponential_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    exceptions: tuple = (Exception,),
):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == max_retries:
                        logger.error(f"{func.__name__} failed after {max_retries + 1} attempts: {e}")
                        raise

                    delay = min(base_delay * (exponential_base ** attempt), max_delay)

                    if jitter:
                        delay = delay * (0.5 + random.random() * 0.5)

                    logger.warning(
                        f"{func.__name__} attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    time.sleep(delay)

            raise last_exception

        return wrapper
    return decorator


def with_circuit_breaker(
    circuit_breaker: CircuitBreaker,
    fallback: Optional[Callable] = None,
    exceptions: tuple = (Exception,),
):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            if not circuit_breaker.can_execute():
                if fallback:
                    logger.warning(f"Circuit breaker open, using fallback for {func.__name__}")
                    return fallback(*args, **kwargs)
                raise RuntimeError(f"Circuit breaker open for {func.__name__}")

            try:
                result = func(*args, **kwargs)
                circuit_breaker.record_success()
                return result
            except exceptions as e:
                circuit_breaker.record_failure()
                raise

        return wrapper
    return decorator


class ApiClient:
    def __init__(
        self,
        name: str = "api_client",
        max_retries: int = 3,
        base_delay: float = 1.0,
        circuit_breaker: Optional[CircuitBreaker] = None,
    ):
        self.name = name
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.circuit_breaker = circuit_breaker or CircuitBreaker()

    def request(
        self,
        func: Callable,
        *args,
        exceptions: tuple = (Exception,),
        fallback: Any = None,
        **kwargs,
    ) -> Any:
        if not self.circuit_breaker.can_execute():
            if fallback is not None:
                logger.warning(f"[{self.name}] Circuit breaker open, returning fallback")
                return fallback
            raise RuntimeError(f"[{self.name}] Circuit breaker is open")

        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                result = func(*args, **kwargs)
                self.circuit_breaker.record_success()
                return result
            except exceptions as e:
                last_exception = e

                if attempt == self.max_retries:
                    self.circuit_breaker.record_failure()
                    logger.error(f"[{self.name}] Request failed after {self.max_retries + 1} attempts: {e}")
                    if fallback is not None:
                        return fallback
                    raise

                delay = self.base_delay * (2 ** attempt)
                delay = min(delay, 30.0)
                delay = delay * (0.5 + random.random() * 0.5)

                logger.warning(
                    f"[{self.name}] Attempt {attempt + 1} failed: {e}. "
                    f"Retrying in {delay:.2f}s..."
                )
                time.sleep(delay)

        if fallback is not None:
            return fallback
        raise last_exception