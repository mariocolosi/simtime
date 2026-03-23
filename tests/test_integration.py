"""End-to-end simulation scenarios."""
import pytest
from simtime import TimeSimulator, EventType, prepare_func


def test_full_declared_duration_simulation():
    sim = TimeSimulator()
    log = []

    def task():
        log.append(sim.now())

    t = prepare_func(EventType.DECLARED_DURATION, task, value=5)
    for start in [0, 5, 10]:
        ev = sim.create_event(f"task@{start}", t)
        sim.schedule(ev, at=start)

    sim.run(until_time=20)

    assert log == [0, 5, 10]
    records = sim.recorder.records
    assert len(records) == 3
    # Each declared duration of 5 ms means end_sim = start_sim + 5
    assert records[0].duration_sim == 5
    assert records[0].error is None


def test_measured_duration_recorded():
    sim = TimeSimulator(scale_real_to_sim=1000.0)

    def quick(): pass

    t = prepare_func(EventType.MEASURED_DURATION, quick)
    ev = sim.create_event("m", t)
    sim.schedule(ev, at=0)
    sim.run()

    record = sim.recorder.records[0]
    # Real duration is very small; sim duration should still be >= 0
    assert record.duration_sim >= 0
    assert record.duration_real is not None and record.duration_real >= 0


def test_add_measured_time_integration():
    sim = TimeSimulator()

    def quick(): pass

    t = prepare_func(EventType.MEASURED_DURATION, quick)
    sim.add_measured_time(t, 200)
    ev = sim.create_event("m", t)
    sim.schedule(ev, at=0)
    sim.run()

    record = sim.recorder.records[0]
    assert record.duration_sim >= 200


def test_error_in_event_captured_in_record():
    sim = TimeSimulator()

    def broken():
        raise RuntimeError("sim error")

    t = prepare_func(EventType.DECLARED_DURATION, broken, value=0)
    ev = sim.create_event("err", t)
    sim.schedule(ev, at=1)
    sim.run()

    assert len(sim.recorder.records) == 1
    record = sim.recorder.records[0]
    assert "sim error" in record.error


def test_callback_chain():
    sim = TimeSimulator()
    order = []

    def first(): order.append(1)
    def second(): order.append(2)
    def third(): order.append(3)

    f1 = prepare_func(EventType.DECLARED_DURATION, first, value=0)
    f2 = prepare_func(EventType.DECLARED_DURATION, second, value=0)
    f3 = prepare_func(EventType.DECLARED_DURATION, third, value=0)

    ev3 = sim.create_event("third", f3)
    ev2 = sim.create_event("second", f2, callback_event=ev3)
    ev1 = sim.create_event("first", f1, callback_event=ev2)
    sim.schedule(ev1, at=1)
    sim.run(until_time=10)

    assert order == [1, 2, 3]


def test_async_event_integration():
    import asyncio
    sim = TimeSimulator()

    async def async_work():
        return 42

    t = prepare_func(EventType.DECLARED_DURATION, async_work, value=10)
    ev = sim.create_event("async", t)
    sim.schedule(ev, at=0)
    sim.run(until_time=20)

    assert ev.result == 42
    assert sim.recorder.records[0].duration_sim == 10


def test_periodic_with_metrics():
    sim = TimeSimulator()

    def tick():
        sim.metrics_store.add(
            category="timing", type="tick", name="count", value=sim.now()
        )

    t = prepare_func(EventType.PERIODIC, tick, value={"every_ms": 10})
    ev = sim.create_event("tick", t)
    sim.schedule(ev, at=0)
    sim.run(until_time=30)

    records = sim.metrics_store.metrics
    assert len(records) == 3
    assert [r.value for r in records] == [0, 10, 20]


def test_rate_based_max_events():
    sim = TimeSimulator(seed=0)
    count = [0]

    def arrive():
        count[0] += 1

    t = prepare_func(EventType.RATE_BASED, arrive, value={
        "rate_per_ms": 0.5, "dist": "constant", "max_events": 4
    })
    ev = sim.create_event("a", t)
    sim.schedule(ev, at=0)
    sim.run(until_time=100)

    # Initial event + 4 reschedules = 5 total executions
    assert count[0] == 5


def test_to_dicts_export_no_pandas(monkeypatch):
    import simtime.recorder as recorder_mod
    import simtime.metric_store as ms_mod
    monkeypatch.setattr(recorder_mod, "pd", None)
    monkeypatch.setattr(ms_mod, "pd", None)

    sim = TimeSimulator()

    def task(): pass

    t = prepare_func(EventType.DECLARED_DURATION, task, value=5)
    ev = sim.create_event("e", t)
    sim.schedule(ev, at=1)
    sim.metrics_store.add(category="c", type="t", name="n", value=1)
    sim.run()

    assert len(sim.recorder.to_dicts()) == 1
    assert len(sim.metrics_store.to_dicts()) == 1


def test_seed_produces_identical_runs():
    def run(seed):
        sim = TimeSimulator(seed=seed)
        results = []

        def arrive():
            results.append(sim.now())

        t = prepare_func(EventType.RATE_BASED, arrive, value={
            "rate_per_ms": 0.2, "dist": "poisson", "max_events": 5
        })
        ev = sim.create_event("a", t)
        sim.schedule(ev, at=0)
        sim.run(until_time=500)
        return results

    assert run(7) == run(7)
