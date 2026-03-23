# SimTime

SimTime is a Python library for discrete-event simulation, supporting flexible event scheduling, detailed event recording, and custom metric collection. It is designed for simulating time-based processes, both synchronous and asynchronous, with periodic, rate-based, declared, or measured duration events.

---

## Features

- **Discrete-event simulation engine** with customizable event queue and time advancement.
- **Flexible event scheduling**: absolute time, after delay, periodic, rate-based, or with custom callbacks.
- **Support for synchronous and asynchronous (coroutine) event functions**.
- **Detailed event recording**: logs of timing, results, errors, and metadata.
- **Custom metric collection and management** during simulation.
- **Export results**: events and metrics exportable as CSV/JSON (pandas optional; stdlib fallback included).

---

## Installation

```sh
pip install simtime

# Optional: enable pandas-based DataFrame export
pip install "simtime[pandas]"
```

---

## Quick Start

```python
from simtime import TimeSimulator, EventType, prepare_func

# Define an event function
def my_event():
    print("Event executed!")

# Prepare the function for simulation (required)
my_event = prepare_func(EventType.DECLARED_DURATION, my_event, value=10)

# Create the simulator
sim = TimeSimulator()

# Create and schedule the event at simulation time 10
event = sim.create_event("my_event", my_event)
sim.schedule(event, at=10)

# Run the simulation until time 20
sim.run(until_time=20)
```

---

## Event Types and Scheduling

### Declared Duration

The event's simulated duration is a fixed value set at preparation time.

```python
def task():
    print("Task with declared duration")

task = prepare_func(EventType.DECLARED_DURATION, task, value=50)  # 50 ms simulated
event = sim.create_event("task", task)
sim.schedule(event, at=0)
```

### Measured Duration

The event's simulated duration is scaled from its real wall-clock execution time.

```python
def measured_task():
    # Real computation here
    pass

measured_task = prepare_func(EventType.MEASURED_DURATION, measured_task)
event = sim.create_event("measured", measured_task)
sim.schedule(event, at=0)
```

### Periodic

The event is automatically rescheduled at a fixed interval.

```python
def periodic_task():
    print("Periodic event")

periodic_task = prepare_func(EventType.PERIODIC, periodic_task, value={"every_ms": 5})
event = sim.create_event("periodic", periodic_task)
sim.schedule(event, at=0)
sim.run(until_time=20)  # fires at t=0, 5, 10, 15
```

### Rate-Based

Events are generated at a statistical arrival rate using a chosen distribution.

```python
def rate_task():
    print("Rate-based event")

rate_task = prepare_func(
    EventType.RATE_BASED,
    rate_task,
    value={"rate_per_ms": 0.1, "dist": "poisson", "max_events": 10}
)
event = sim.create_event("rate", rate_task)
sim.schedule(event, at=0)
```

Supported distributions: `"poisson"`, `"uniform"`, `"normal"`, `"constant"`.

### Asynchronous Events

Async functions are supported for all event types.

```python
import asyncio

async def async_task():
    await asyncio.sleep(0.01)
    return "done"

async_task = prepare_func(EventType.DECLARED_DURATION, async_task, value=10)
event = sim.create_event("async", async_task)
sim.schedule(event, at=0)
```

---

## Event Recording and Metrics

### Accessing Event Records

```python
for record in sim.recorder.records:
    print(record)

# As a list of dicts (no pandas needed)
dicts = sim.recorder.to_dicts()

# As a pandas DataFrame (requires pandas)
df = sim.recorder.to_dataframe()
```

### Exporting Events

```python
sim.recorder.save_csv("events.csv")
sim.recorder.save_json("events.json")
```

### Using the Metric Store

```python
sim.metrics_store.add(
    category="performance",
    type="latency",
    name="request_latency",
    value=123,
    tags={"endpoint": "/api"}
)

# Filter by category
perf_metrics = sim.metrics_store.get_by_category("performance")

sim.metrics_store.save_csv("metrics.csv")
sim.metrics_store.save_json("metrics.json")
```

### Temporary Metrics

Temporary metrics are keyed by id and can be updated or removed during simulation.

```python
sim.metrics_store.add_temp("in_flight", 0)
record = sim.metrics_store.get_temp("in_flight")
print(record.value)
sim.metrics_store.remove_temp("in_flight")
```

---

## API Reference

### `TimeSimulator`

```python
TimeSimulator(
    step_ms: int = 1,
    jump_to_next_event: bool = True,
    scale_real_to_sim: float = 1.0,
    seed: Optional[int] = None,
)
```

| Method | Description |
|--------|-------------|
| `now() -> int` | Current simulation time in ms. |
| `pending_count() -> int` | Number of events waiting in the queue. |
| `create_event(name, func, args, kwargs, metadata, callback_event) -> Event` | Create an event from a prepared function. |
| `schedule(event, at=None, delay=None) -> Event` | Enqueue an event. |
| `run(until_time=None, until_events=None, stop_condition=None)` | Run the simulation. |
| `stop()` | Signal the simulation to stop after the current batch. |
| `reset()` | Reset clock, queue, recorder, and metrics to initial state. |
| `add_measured_time(function, value)` | Add extra simulated ms to a `MEASURED_DURATION` function. |
| `recorder` | `Recorder` instance for event logs. |
| `metrics_store` | `MetricStore` instance for metrics. |

### `prepare_func`

```python
prepare_func(event_type: EventType, func, value=None) -> Callable
```

Prepares a function for simulation. Returns a copy; the original is not mutated.

### `Recorder`

| Method/Property | Description |
|-----------------|-------------|
| `records` | List of `EventRecord` objects (copy). |
| `to_dicts() -> list[dict]` | Records as plain dicts (no pandas needed). |
| `to_dataframe()` | Records as pandas DataFrame. Requires pandas. |
| `save_csv(path)` | Save to CSV (uses stdlib if pandas absent). |
| `save_json(path)` | Save to JSON. |

### `MetricStore`

| Method/Property | Description |
|-----------------|-------------|
| `add(category, type, name, value, tags=None)` | Add a persistent metric. |
| `get_by_category(category) -> list[MetricRecord]` | Filter metrics by category. |
| `add_temp(id, value)` | Add/update a temporary metric. |
| `get_temp(id) -> TempMetricRecord \| None` | Retrieve a temporary metric. |
| `remove_temp(id)` | Remove a temporary metric. |
| `metrics` | All persistent `MetricRecord` objects (copy). |
| `to_dicts() -> list[dict]` | Metrics as plain dicts. |
| `to_dataframe()` | Metrics as pandas DataFrame. Requires pandas. |
| `save_csv(path)` | Save to CSV. |
| `save_json(path)` | Save to JSON. |

---

## Advanced Usage

- **Reproducible simulations**: Pass `seed=42` to `TimeSimulator`.
- **Step-by-step time advance**: Set `jump_to_next_event=False` and configure `step_ms`.
- **Custom stop conditions**: `run(stop_condition=lambda sim: sim.now() >= 100)`.
- **Event chaining**: Pass a `callback_event` to `create_event`; it fires after the parent completes.
- **Reset and rerun**: Call `sim.reset()` between benchmark runs instead of creating a new instance.

---

## Requirements

- Python 3.9+
- Optional: `pandas>=1.3` for DataFrame export
