"""Circuit breaker pattern for handling external service failures."""

import asyncio
import time
from enum import Enum
from typing import Optional, Callable, Any, Dict
from functools import wraps
from loguru import logger

from src.domain.exceptions import ExternalServiceError


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Service is failing, reject calls
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """
    Circuit breaker implementation for external services.

    Prevents cascading failures by temporarily blocking calls to failing services.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception
    ):
        """
        Initialize circuit breaker.

        Args:
            name: Name of the service
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before trying half-open
            expected_exception: Exception type to catch
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.success_count = 0

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return True

        return time.time() - self.last_failure_time >= self.recovery_timeout

    def _record_success(self) -> None:
        """Record a successful call."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= 2:  # Need 2 successful calls to fully close
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
                logger.info(f"Circuit breaker '{self.name}' closed (service recovered)")

    def _record_failure(self) -> None:
        """Record a failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            # Failed during recovery attempt, reopen
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker '{self.name}' reopened (recovery failed)")
        elif self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(
                f"Circuit breaker '{self.name}' opened "
                f"(failures: {self.failure_count}/{self.failure_threshold})"
            )

    def _check_state(self) -> None:
        """Check and update circuit state."""
        if self.state == CircuitState.OPEN and self._should_attempt_reset():
            self.state = CircuitState.HALF_OPEN
            self.success_count = 0
            logger.info(f"Circuit breaker '{self.name}' half-open (attempting recovery)")

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.

        Args:
            func: Async function to call
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            ExternalServiceError: If circuit is open
        """
        self._check_state()

        if self.state == CircuitState.OPEN:
            raise ExternalServiceError(
                self.name,
                f"Service {self.name} is temporarily unavailable (circuit open)",
                {
                    "failure_count": self.failure_count,
                    "retry_after": self.recovery_timeout
                }
            )

        try:
            result = await func(*args, **kwargs)
            self._record_success()
            return result

        except self.expected_exception as e:
            self._record_failure()
            raise

    def get_status(self) -> Dict[str, Any]:
        """Get current circuit breaker status."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure": self.last_failure_time,
            "can_retry": self._should_attempt_reset() if self.state == CircuitState.OPEN else True
        }

    def reset(self) -> None:
        """Manually reset the circuit breaker."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        logger.info(f"Circuit breaker '{self.name}' manually reset")


def with_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    expected_exception: type = Exception
):
    """
    Decorator to add circuit breaker to async functions.

    Args:
        name: Circuit breaker name
        failure_threshold: Number of failures before opening
        recovery_timeout: Seconds before retry
        expected_exception: Exception type to catch
    """
    circuit = CircuitBreaker(name, failure_threshold, recovery_timeout, expected_exception)

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await circuit.call(func, *args, **kwargs)

        # Attach circuit breaker for status checks
        wrapper.circuit_breaker = circuit
        return wrapper

    return decorator


class CircuitBreakerManager:
    """Manages multiple circuit breakers."""

    def __init__(self):
        """Initialize the circuit breaker manager."""
        self.breakers: Dict[str, CircuitBreaker] = {}

    def add_breaker(self, breaker: CircuitBreaker) -> None:
        """Add a circuit breaker to manage."""
        self.breakers[breaker.name] = breaker

    def get_breaker(self, name: str) -> Optional[CircuitBreaker]:
        """Get a circuit breaker by name."""
        return self.breakers.get(name)

    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all circuit breakers."""
        return {
            name: breaker.get_status()
            for name, breaker in self.breakers.items()
        }

    def reset_all(self) -> None:
        """Reset all circuit breakers."""
        for breaker in self.breakers.values():
            breaker.reset()

    def reset(self, name: str) -> bool:
        """
        Reset a specific circuit breaker.

        Args:
            name: Name of the breaker to reset

        Returns:
            True if reset, False if breaker not found
        """
        breaker = self.breakers.get(name)
        if breaker:
            breaker.reset()
            return True
        return False