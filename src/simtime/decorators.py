from __future__ import annotations
from .events import EventType
from typing import Callable, Any, Optional
import types
import functools
import copy

DECLARED_DURATION_ATTR = "__sim_declared_duration_ms__"
MEASURE_SCALE_ATTR = "__sim_measure_scale__"
MEASURE_ADDITIONAL_TIME_ATTR = "__sim_measure_additional_time__"
PERIODIC_ATTR = "__sim_periodic_ms__"
RATE_ATTR = "__sim_rate__"


def prepare_func(
    event_type: EventType, func: Callable[..., Any], value: Optional[int] = None
) -> Callable[..., Any]:
    """
    Prepares a function for simulation by attaching event-type metadata.

    Returns a copy of the function with the appropriate attributes set.
    The original function is not mutated.

    Args:
        event_type: The type of simulation event.
        func: The function to prepare.
        value: Type-specific configuration:
            - DECLARED_DURATION: int duration in ms
            - MEASURED_DURATION: not used
            - PERIODIC: dict with 'every_ms' (required) and optional 'until'
            - RATE_BASED: dict with 'rate_per_ms', optional 'dist' and 'max_events'
    """
    if isinstance(func, types.FunctionType):
        new_func = types.FunctionType(
            func.__code__,
            func.__globals__,
            name=func.__name__,
            argdefs=func.__defaults__,
            closure=func.__closure__,
        )
        new_func = functools.update_wrapper(new_func, func)
        if hasattr(func, "__dict__"):
            new_func.__dict__.update(copy.deepcopy(func.__dict__))
    else:
        new_func = copy.deepcopy(func)

    # Clear any pre-existing sim attributes on the copy
    for attr in [DECLARED_DURATION_ATTR, MEASURE_SCALE_ATTR, PERIODIC_ATTR, RATE_ATTR, "__sim_prepared__"]:
        if hasattr(new_func, attr):
            delattr(new_func, attr)

    if event_type == EventType.DECLARED_DURATION:
        setattr(new_func, DECLARED_DURATION_ATTR, value)
    elif event_type == EventType.MEASURED_DURATION:
        setattr(new_func, MEASURE_SCALE_ATTR, 1.0)
    elif event_type == EventType.PERIODIC:
        if isinstance(value, dict):
            every_ms = value.get("every_ms")
            until = value.get("until")
            if every_ms is None:
                raise ValueError("every_ms must be provided for periodic events")
            setattr(new_func, PERIODIC_ATTR, every_ms)
            if until is not None:
                setattr(new_func, "until", until)
        else:
            raise ValueError(
                "Value for periodic events must be a dict with 'every_ms' and optional 'until' keys"
            )
    elif event_type == EventType.RATE_BASED:
        if not isinstance(value, dict):
            raise ValueError(
                "Value for rate-based events must be a dict with 'rate_per_ms', 'dist', and 'max_events' keys"
            )
        rate_per_ms = value.get("rate_per_ms")
        if rate_per_ms is None:
            raise ValueError("rate_per_ms must be provided for rate-based events")
        dist = value.get("dist", "uniform")
        max_events = value.get("max_events", None)
        setattr(
            new_func,
            RATE_ATTR,
            {"rate_per_ms": rate_per_ms, "dist": dist, "max_events": max_events},
        )
    else:
        raise ValueError(f"Unsupported event type: {event_type}")

    setattr(new_func, "__sim_prepared__", True)
    setattr(new_func, "__sim_event_type__", event_type)

    return new_func
