from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Callable, TypeVar

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    max_attempts: int = 3
    initial_delay_seconds: float = 0.25
    max_delay_seconds: float = 5.0
    backoff_factor: float = 2.0
    jitter_ratio: float = 0.2


def run_with_retry(operation_name: str, operation: Callable[[], T], policy: RetryPolicy | None = None) -> T:
    active_policy = policy or RetryPolicy()
    if active_policy.max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")

    delay = active_policy.initial_delay_seconds
    last_error: Exception | None = None

    for attempt in range(1, active_policy.max_attempts + 1):
        try:
            return operation()
        except Exception as exc:  # pragma: no cover - runtime/network/database dependent
            last_error = exc
            if attempt >= active_policy.max_attempts:
                break
            jitter = random.uniform(0, delay * active_policy.jitter_ratio)
            time.sleep(delay + jitter)
            delay = min(delay * active_policy.backoff_factor, active_policy.max_delay_seconds)

    if last_error is None:
        raise RuntimeError(f"{operation_name} failed without raising an exception")
    raise RuntimeError(f"{operation_name} failed after {active_policy.max_attempts} attempts") from last_error
