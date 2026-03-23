from __future__ import annotations
import random
import inspect
from typing import Callable


def exp_interarrival(rate_per_ms: float) -> int:
    """Returns an exponentially distributed interarrival time in ms."""
    return max(0, int(random.expovariate(rate_per_ms)))


def is_coroutine_function(func: Callable) -> bool:
    return inspect.iscoroutinefunction(func)
