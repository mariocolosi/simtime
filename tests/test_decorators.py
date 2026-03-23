import pytest
from simtime import EventType, prepare_func
from simtime.decorators import (
    DECLARED_DURATION_ATTR,
    MEASURE_SCALE_ATTR,
    PERIODIC_ATTR,
    RATE_ATTR,
)


def base_func():
    return 1


def test_prepare_func_does_not_mutate_original():
    original = base_func
    prepare_func(EventType.DECLARED_DURATION, original, value=50)
    assert not hasattr(original, "__sim_prepared__")
    assert not hasattr(original, DECLARED_DURATION_ATTR)


def test_prepare_func_declared_duration():
    f = prepare_func(EventType.DECLARED_DURATION, base_func, value=42)
    assert getattr(f, "__sim_prepared__") is True
    assert getattr(f, "__sim_event_type__") == EventType.DECLARED_DURATION
    assert getattr(f, DECLARED_DURATION_ATTR) == 42


def test_prepare_func_measured_duration():
    f = prepare_func(EventType.MEASURED_DURATION, base_func)
    assert getattr(f, "__sim_prepared__") is True
    assert getattr(f, "__sim_event_type__") == EventType.MEASURED_DURATION
    assert getattr(f, MEASURE_SCALE_ATTR) == 1.0


def test_prepare_func_periodic_sets_every_ms():
    f = prepare_func(EventType.PERIODIC, base_func, value={"every_ms": 10})
    assert getattr(f, PERIODIC_ATTR) == 10


def test_prepare_func_periodic_requires_dict():
    with pytest.raises(ValueError, match="must be a dict"):
        prepare_func(EventType.PERIODIC, base_func, value=10)


def test_prepare_func_periodic_requires_every_ms():
    with pytest.raises(ValueError, match="every_ms must be provided"):
        prepare_func(EventType.PERIODIC, base_func, value={"until": 100})


def test_prepare_func_rate_based():
    f = prepare_func(EventType.RATE_BASED, base_func, value={"rate_per_ms": 0.5, "dist": "poisson"})
    rate_info = getattr(f, RATE_ATTR)
    assert rate_info["rate_per_ms"] == 0.5
    assert rate_info["dist"] == "poisson"
    assert rate_info["max_events"] is None


def test_prepare_func_rate_based_requires_dict():
    with pytest.raises(ValueError, match="must be a dict"):
        prepare_func(EventType.RATE_BASED, base_func, value=0.5)


def test_prepare_func_rate_based_requires_rate_per_ms():
    with pytest.raises(ValueError, match="rate_per_ms must be provided"):
        prepare_func(EventType.RATE_BASED, base_func, value={"dist": "poisson"})


def test_prepare_func_unsupported_type_raises():
    # GENERIC etc. are removed; passing an int enum value not in EventType should fail
    with pytest.raises(Exception):
        prepare_func(999, base_func)  # type: ignore


def test_no_circular_reference_on_prepared_func():
    f = prepare_func(EventType.DECLARED_DURATION, base_func, value=5)
    assert not hasattr(f, "__sim_func__"), "Circular __sim_func__ reference must not exist"


def test_prepared_func_has_no_sim_func_attr():
    """Removing __sim_func__ means no hidden self-reference on prepared functions."""
    f = prepare_func(EventType.DECLARED_DURATION, base_func, value=5)
    assert not hasattr(f, "__sim_func__")
    # Also confirm expected attrs are present
    assert getattr(f, "__sim_prepared__") is True


def test_prepare_func_preserves_function_behavior():
    def add(a, b):
        return a + b
    f = prepare_func(EventType.DECLARED_DURATION, add, value=1)
    assert f(2, 3) == 5
