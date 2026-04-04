"""Circuit breaker pattern for external service calls."""

import time

import structlog

logger = structlog.get_logger()


class CircuitBreakerOpen(Exception):
    """Raised when circuit breaker is open."""

    def __init__(self):
        super().__init__("Circuit breaker is open — service unavailable")


class CircuitBreaker:
    """Circuit breaker with closed → open → half_open states.

    - Opens after `failure_threshold` consecutive failures
    - Half-opens after `recovery_timeout` seconds
    - Closes after `success_threshold` successes in half-open state
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        success_threshold: int = 1,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        self._state = "closed"  # closed | open | half_open
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: float = 0

    @property
    def state(self) -> str:
        if self._state == "open":
            if time.monotonic() - self._last_failure_time >= self.recovery_timeout:
                self._state = "half_open"
                self._success_count = 0
                logger.info("circuit_breaker_half_open")
        return self._state

    def check(self) -> None:
        """Check if requests are allowed. Raises CircuitBreakerOpen if not."""
        if self.state == "open":
            raise CircuitBreakerOpen()

    def record_success(self) -> None:
        """Record a successful call."""
        if self._state == "half_open":
            self._success_count += 1
            if self._success_count >= self.success_threshold:
                self._state = "closed"
                self._failure_count = 0
                logger.info("circuit_breaker_closed")
        else:
            self._failure_count = 0

    def record_failure(self) -> None:
        """Record a failed call."""
        self._failure_count += 1
        self._last_failure_time = time.monotonic()

        if self._failure_count >= self.failure_threshold:
            self._state = "open"
            logger.warning("circuit_breaker_opened", failures=self._failure_count)

        if self._state == "half_open":
            self._state = "open"
            logger.warning("circuit_breaker_reopened_from_half_open")
