import pytest
from simtime import TimeSimulator, EventType, prepare_func


@pytest.fixture
def sim():
    return TimeSimulator(seed=42)


@pytest.fixture
def declared_func():
    def f():
        return "declared"
    return prepare_func(EventType.DECLARED_DURATION, f, value=10)


@pytest.fixture
def measured_func():
    def f():
        return "measured"
    return prepare_func(EventType.MEASURED_DURATION, f)


@pytest.fixture
def periodic_func():
    def f():
        return "periodic"
    return prepare_func(EventType.PERIODIC, f, value={"every_ms": 5})


@pytest.fixture
def rate_func():
    def f():
        return "rate"
    return prepare_func(EventType.RATE_BASED, f, value={"rate_per_ms": 0.1, "dist": "constant", "max_events": 3})
