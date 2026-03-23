import warnings
import pytest
from simtime import TimeSimulator, EventType, prepare_func
from simtime.exceptions import SchedulingError, SimTimeWarning


def make_func(retval=None, event_type=EventType.DECLARED_DURATION, value=10):
    def f():
        return retval
    return prepare_func(event_type, f, value=value)


# ── now() and basic creation ──────────────────────────────────────────────────

def test_now_starts_at_zero():
    sim = TimeSimulator()
    assert sim.now() == 0


def test_pending_count_empty():
    sim = TimeSimulator()
    assert sim.pending_count() == 0


def test_pending_count_after_schedule(sim, declared_func):
    ev = sim.create_event("e", declared_func)
    sim.schedule(ev, at=5)
    assert sim.pending_count() == 1


# ── create_event validation ───────────────────────────────────────────────────

def test_create_event_requires_prepared_func(sim):
    def raw(): pass
    with pytest.raises(ValueError, match="prepare_func"):
        sim.create_event("e", raw)


def test_create_event_returns_event(sim, declared_func):
    from simtime import Event
    ev = sim.create_event("test", declared_func)
    assert isinstance(ev, Event)
    assert ev.name == "test"


# ── schedule() ────────────────────────────────────────────────────────────────

def test_schedule_returns_event(sim, declared_func):
    ev = sim.create_event("e", declared_func)
    result = sim.schedule(ev, at=10)
    assert result is ev


def test_schedule_raises_on_wrong_type(sim):
    with pytest.raises(TypeError):
        sim.schedule("not an event")  # type: ignore


def test_schedule_raises_on_past(sim, declared_func):
    # Advance time first
    f = declared_func
    ev = sim.create_event("e", f)
    sim.schedule(ev, at=5)
    sim.run(until_time=10)

    f2 = make_func()
    ev2 = sim.create_event("e2", f2)
    with pytest.raises(SchedulingError):
        sim.schedule(ev2, at=1)


def test_schedule_warns_past_until_time(sim, declared_func):
    ev = sim.create_event("e", declared_func)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result = sim.schedule(ev, at=5, )
        # schedule the run with until_time=3 after to trigger the warning path
    # Try through run context
    sim2 = TimeSimulator()
    f = make_func()
    ev2 = sim2.create_event("e", f)
    sim2.schedule(ev2, at=1)
    sim2.run(until_time=3)
    # Schedule after run (until_time still set to 3)
    f3 = make_func()
    ev3 = sim2.create_event("late", f3)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result = sim2.schedule(ev3, at=10)
    assert len(w) == 1
    assert issubclass(w[0].category, SimTimeWarning)
    assert result is ev3  # still returns the event


def test_schedule_with_delay(sim, declared_func):
    ev = sim.create_event("e", declared_func)
    sim.schedule(ev, delay=7)
    assert ev.at == 7


def test_schedule_at_overrides_delay(sim, declared_func):
    ev = sim.create_event("e", declared_func)
    sim.schedule(ev, at=15, delay=7)
    assert ev.at == 15


# ── run() mechanics ───────────────────────────────────────────────────────────

def test_run_executes_event(sim, declared_func):
    ev = sim.create_event("e", declared_func)
    sim.schedule(ev, at=5)
    sim.run(until_time=20)
    assert ev.finished is True
    assert ev.result == "declared"


def test_run_until_time_stops_early():
    sim = TimeSimulator()
    results = []
    def task():
        results.append(sim.now())
    t = prepare_func(EventType.DECLARED_DURATION, task, value=0)
    for i in [5, 10, 15, 20]:
        ev = sim.create_event(f"t{i}", t)
        sim.schedule(ev, at=i)
    sim.run(until_time=12)
    assert results == [5, 10]


def test_run_until_events():
    sim = TimeSimulator()
    results = []
    def task():
        results.append(1)
    t = prepare_func(EventType.DECLARED_DURATION, task, value=0)
    for i in range(1, 6):
        ev = sim.create_event(f"t{i}", t)
        sim.schedule(ev, at=i)
    sim.run(until_events=3)
    assert len(results) == 3


def test_run_stop_condition():
    sim = TimeSimulator()
    results = []
    def task():
        results.append(sim.now())
    t = prepare_func(EventType.DECLARED_DURATION, task, value=0)
    for i in range(1, 11):
        ev = sim.create_event(f"t{i}", t)
        sim.schedule(ev, at=i)
    sim.run(stop_condition=lambda s: s.now() >= 5)
    # Stop condition checked before processing, so t=5 should not run
    assert 5 not in results
    assert results == [1, 2, 3, 4]


def test_stop_method():
    sim = TimeSimulator()
    count = [0]
    def task():
        count[0] += 1
        if count[0] == 2:
            sim.stop()
    t = prepare_func(EventType.DECLARED_DURATION, task, value=0)
    for i in range(1, 6):
        ev = sim.create_event(f"t{i}", t)
        sim.schedule(ev, at=i)
    sim.run()
    assert count[0] == 2


def test_time_advances_correctly(sim, declared_func):
    ev = sim.create_event("e", declared_func)
    sim.schedule(ev, at=42)
    sim.run(until_time=100)
    assert sim.now() == 42


# ── jump_to_next_event=False (step mode) ─────────────────────────────────────

def test_step_mode_processes_t0_events():
    """Events scheduled at t=0 must execute in step mode."""
    sim = TimeSimulator(step_ms=1, jump_to_next_event=False)
    executed = []
    def task():
        executed.append(sim.now())
    t = prepare_func(EventType.DECLARED_DURATION, task, value=0)
    ev = sim.create_event("e", t)
    sim.schedule(ev, at=0)
    sim.run(until_time=5)
    assert 0 in executed


def test_step_mode_advances_by_step_ms():
    sim = TimeSimulator(step_ms=5, jump_to_next_event=False)
    times = []
    def task():
        times.append(sim.now())
    t = prepare_func(EventType.DECLARED_DURATION, task, value=0)
    for ts in [0, 5, 10]:
        ev = sim.create_event(f"t{ts}", t)
        sim.schedule(ev, at=ts)
    sim.run(until_time=15)
    assert times == [0, 5, 10]


# ── periodic events ───────────────────────────────────────────────────────────

def test_periodic_event_repeats(sim, periodic_func):
    times = []
    def task():
        times.append(sim.now())
    t = prepare_func(EventType.PERIODIC, task, value={"every_ms": 5})
    ev = sim.create_event("p", t)
    sim.schedule(ev, at=0)
    sim.run(until_time=20)
    assert times == [0, 5, 10, 15]


# ── callbacks ────────────────────────────────────────────────────────────────

def test_callback_event_fires_after_parent():
    sim = TimeSimulator()
    order = []
    def parent():
        order.append("parent")
    def child():
        order.append("child")

    p = prepare_func(EventType.DECLARED_DURATION, parent, value=0)
    c = prepare_func(EventType.DECLARED_DURATION, child, value=0)

    cb_ev = sim.create_event("child", c)
    parent_ev = sim.create_event("parent", p, callback_event=cb_ev)
    sim.schedule(parent_ev, at=1)
    sim.run(until_time=10)
    assert order == ["parent", "child"]


# ── error handling ────────────────────────────────────────────────────────────

def test_error_in_event_captured():
    sim = TimeSimulator()
    def bad():
        raise RuntimeError("oops")
    t = prepare_func(EventType.DECLARED_DURATION, bad, value=0)
    ev = sim.create_event("bad", t)
    sim.schedule(ev, at=1)
    sim.run()  # must not raise
    assert ev.error is not None
    assert "oops" in str(ev.error)
    record = sim.recorder.records[0]
    assert "oops" in record.error


def test_error_does_not_stop_subsequent_events():
    sim = TimeSimulator()
    results = []
    def bad():
        raise ValueError("fail")
    def good():
        results.append(True)
    tb = prepare_func(EventType.DECLARED_DURATION, bad, value=0)
    tg = prepare_func(EventType.DECLARED_DURATION, good, value=0)
    ev1 = sim.create_event("bad", tb)
    ev2 = sim.create_event("good", tg)
    sim.schedule(ev1, at=1)
    sim.schedule(ev2, at=2)
    sim.run()
    assert results == [True]


# ── async events ──────────────────────────────────────────────────────────────

def test_async_event_executes():
    import asyncio
    sim = TimeSimulator()
    async def async_task():
        return "async_result"
    t = prepare_func(EventType.DECLARED_DURATION, async_task, value=5)
    ev = sim.create_event("async", t)
    sim.schedule(ev, at=1)
    sim.run()
    assert ev.result == "async_result"


# ── reset() ──────────────────────────────────────────────────────────────────

def test_reset_clears_state():
    sim = TimeSimulator(seed=1)
    def task(): pass
    t = prepare_func(EventType.DECLARED_DURATION, task, value=0)
    ev = sim.create_event("e", t)
    sim.schedule(ev, at=5)
    sim.run(until_time=10)
    assert sim.now() == 5
    assert len(sim.recorder.records) == 1

    sim.reset()
    assert sim.now() == 0
    assert len(sim.recorder.records) == 0
    assert sim.pending_count() == 0


def test_reset_allows_rerun():
    sim = TimeSimulator(seed=42)
    results = []
    def task():
        results.append(sim.now())
    t = prepare_func(EventType.DECLARED_DURATION, task, value=0)

    for _ in range(2):
        results.clear()
        ev = sim.create_event("e", t)
        sim.schedule(ev, at=3)
        sim.run(until_time=10)
        sim.reset()

    assert results == [3]


# ── add_measured_time() ───────────────────────────────────────────────────────

def test_add_measured_time_requires_prepared_func():
    sim = TimeSimulator()
    def raw(): pass
    with pytest.raises(ValueError):
        sim.add_measured_time(raw, 50)


def test_add_measured_time_affects_duration():
    sim = TimeSimulator()
    def fast(): pass
    t = prepare_func(EventType.MEASURED_DURATION, fast)
    sim.add_measured_time(t, 500)
    ev = sim.create_event("e", t)
    sim.schedule(ev, at=0)
    sim.run()
    record = sim.recorder.records[0]
    # Real duration is near 0; added 500 ms of simulated time
    assert record.duration_sim >= 500


# ── seed reproducibility ──────────────────────────────────────────────────────

def test_seed_produces_reproducible_results():
    def run_with_seed(s):
        sim = TimeSimulator(seed=s)
        times = []
        def task():
            times.append(sim.now())
        t = prepare_func(EventType.RATE_BASED, task, value={"rate_per_ms": 0.1, "dist": "poisson", "max_events": 5})
        ev = sim.create_event("r", t)
        sim.schedule(ev, at=0)
        sim.run(until_time=1000)
        return times

    assert run_with_seed(99) == run_with_seed(99)
    assert run_with_seed(1) != run_with_seed(2)
