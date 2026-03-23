from __future__ import annotations
import itertools
import heapq
import random
import asyncio
import time
import warnings
from typing import Any, Callable, Optional, Dict, List, Tuple
from .events import Event, EventType, ScheduledItem
from .recorder import Recorder, EventRecord
from .metric_store import MetricStore
from .exceptions import SchedulingError, SimTimeWarning
from .utils import is_coroutine_function, exp_interarrival
from .decorators import DECLARED_DURATION_ATTR, MEASURE_SCALE_ATTR, MEASURE_ADDITIONAL_TIME_ATTR, PERIODIC_ATTR, RATE_ATTR


class TimeSimulator:
    def __init__(
        self,
        step_ms: int = 1,
        jump_to_next_event: bool = True,
        scale_real_to_sim: float = 1.0,
        seed: Optional[int] = None,
    ):
        self.step_ms = step_ms
        self.jump_to_next_event = jump_to_next_event
        self.scale_real_to_sim = scale_real_to_sim
        self.seed = seed

        # When stepping (not jumping), start before t=0 so the first step reaches t=0
        self._now = 0 if jump_to_next_event else -step_ms
        self._stop = False
        self._until_time = None
        self._until_events = None

        self._pq: List[ScheduledItem] = []
        self._order_counter = itertools.count()
        self._event_id_counter = itertools.count()

        self.recorder = Recorder()
        self.metrics_store = MetricStore()

        if seed is not None:
            random.seed(seed)

    # ------------ Public API ------------

    def now(self) -> int:
        """Return the current simulation time in ms."""
        return self._now

    def pending_count(self) -> int:
        """Return the number of events currently waiting in the queue."""
        return len(self._pq)

    def create_event(
        self,
        name: str,
        func: Callable[..., Any],
        args: Tuple[Any, ...] = (),
        kwargs: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        callback_event: Optional[Event] = None,
    ) -> Event:
        """
        Create an event object from a prepared function.

        The function must have been prepared with prepare_func() first.
        Call schedule() to enqueue the returned event.
        """
        if not getattr(func, "__sim_prepared__", False):
            raise ValueError(
                "Function must be prepared with prepare_func() before creating an event."
            )

        event_type = getattr(func, "__sim_event_type__", None)
        if event_type is None:
            raise ValueError("Function must have an event type set with prepare_func().")

        return Event(
            id=next(self._event_id_counter),
            name=name,
            func=func,
            at=self._now + 1,
            event_type=event_type,
            args=args,
            kwargs=kwargs if kwargs is not None else {},
            metadata=metadata if metadata is not None else {},
            callback_event=callback_event,
        )

    def schedule(
        self,
        event: Event,
        at: Optional[int] = None,
        delay: Optional[int] = None,
    ) -> Event:
        """
        Schedule an event at an absolute time or after a delay from now.

        Args:
            event: The event to schedule.
            at: Absolute simulation time to run the event.
            delay: ms from now to run the event. Ignored if at is provided.

        Returns:
            The scheduled event.

        Raises:
            TypeError: If event is not an Event instance.
            SchedulingError: If the event is scheduled in the past.
        """
        if not isinstance(event, Event):
            raise TypeError("event must be an instance of Event")

        timestamp = at if at is not None else self._now + (delay or 0)
        event.at = timestamp

        if timestamp < self._now:
            raise SchedulingError(
                f"Event '{event.name}' (id={event.id}) cannot be scheduled at t={timestamp} "
                f"which is before the current time t={self._now}."
            )

        if self._until_time is not None and timestamp >= self._until_time:
            warnings.warn(
                f"Event '{event.name}' scheduled at t={timestamp} is at or after the "
                f"simulation end time t={self._until_time}. It will not execute.",
                SimTimeWarning,
                stacklevel=2,
            )
            return event

        heapq.heappush(
            self._pq,
            ScheduledItem(timestamp=timestamp, order=next(self._order_counter), event=event),
        )
        return event

    def run(
        self,
        *,
        until_time: Optional[int] = None,
        until_events: Optional[int] = None,
        stop_condition: Optional[Callable[..., bool]] = None,
    ) -> None:
        """
        Run the simulation.

        Args:
            until_time: Stop after simulation time reaches this value.
            until_events: Stop after this many events have executed.
            stop_condition: Callable(sim) -> bool; stop when it returns True.
        """
        self._until_time = until_time
        self._until_events = until_events
        self._stop = False

        events_run = 0
        while self._pq and not self._stop:
            next_ts = self._pq[0].timestamp

            # Stop before advancing if the next event is at or past the time limit
            if until_time is not None and next_ts >= until_time:
                break

            if self.jump_to_next_event:
                self._now = next_ts
            else:
                self._now += self.step_ms

            # Stop condition is evaluated after advancing time so callers can
            # gate on the current simulation clock value.
            if stop_condition and stop_condition(self):
                break

            batch: List[Event] = []
            while self._pq and self._pq[0].timestamp <= self._now:
                batch.append(heapq.heappop(self._pq).event)

            for event in batch:
                self._execute_event(event)
                events_run += 1
                if until_events is not None and events_run >= until_events:
                    self._stop = True
                    break

    def stop(self) -> None:
        """Signal the simulation to stop after the current batch."""
        self._stop = True

    def reset(self) -> None:
        """
        Reset the simulator to its initial state.

        Clears the event queue, recorder, metrics store, and resets the clock.
        Useful for running repeated benchmarks without creating a new instance.
        """
        self._now = 0 if self.jump_to_next_event else -self.step_ms
        self._stop = False
        self._until_time = None
        self._until_events = None
        self._pq.clear()
        self._order_counter = itertools.count()
        self._event_id_counter = itertools.count()
        self.recorder = Recorder()
        self.metrics_store = MetricStore()
        if self.seed is not None:
            random.seed(self.seed)

    def add_measured_time(self, function: Callable[..., Any], value: int) -> None:
        """
        Add extra simulated time to a MEASURED_DURATION function.

        This is added on top of the scaled real execution time when the event runs.

        Args:
            function: A function previously prepared with prepare_func(MEASURED_DURATION, ...).
            value: Additional simulation time in ms to add.
        """
        if not getattr(function, "__sim_prepared__", False):
            raise ValueError("Function must be prepared with prepare_func() before adding measured time.")
        setattr(function, MEASURE_ADDITIONAL_TIME_ATTR, value)

    # ------------ Internal helpers ------------

    def _execute_event(self, event: Event) -> None:
        start_sim = self._now
        event.started = True
        real_start = time.perf_counter()
        result = None
        try:
            if is_coroutine_function(event.func):
                result = asyncio.run(event.func(*event.args, **event.kwargs))
            else:
                result = event.func(*event.args, **event.kwargs)

            real_dur = time.perf_counter() - real_start

            sim_duration = 0
            if event.event_type == EventType.DECLARED_DURATION:
                sim_duration = getattr(event.func, DECLARED_DURATION_ATTR, 0) or 0
            elif event.event_type == EventType.MEASURED_DURATION:
                scale = getattr(event.func, MEASURE_SCALE_ATTR, self.scale_real_to_sim)
                sim_duration = int(scale * real_dur * 1000)
                sim_duration += getattr(event.func, MEASURE_ADDITIONAL_TIME_ATTR, 0)

            end_sim = start_sim + sim_duration
            self._complete_event(event, start_sim, end_sim, real_dur, result)

            # Reschedule periodic events
            if event.event_type == EventType.PERIODIC:
                every_ms = getattr(event.func, PERIODIC_ATTR, None)
                if every_ms is not None:
                    next_time = start_sim + every_ms
                    if next_time > self._now:
                        next_event = self.create_event(
                            event.name,
                            event.func,
                            args=event.args,
                            kwargs=event.kwargs,
                            metadata=event.metadata,
                            callback_event=event.callback_event,
                        )
                        self.schedule(next_event, at=next_time)

            # Reschedule rate-based events
            if event.event_type == EventType.RATE_BASED and hasattr(event.func, RATE_ATTR):
                info = getattr(event.func, RATE_ATTR)
                rate = info["rate_per_ms"]
                dist = info["dist"]
                max_events = info["max_events"]
                count = event.metadata.get("_generated", 0)
                if max_events is None or count < max_events:
                    if dist == "poisson":
                        inter = exp_interarrival(rate)
                    elif dist == "uniform":
                        inter = random.randint(0, int(1 / rate))
                    elif dist == "normal":
                        mu = 1 / rate
                        inter = max(0, int(random.gauss(mu, mu / 3)))
                    elif dist == "constant":
                        inter = int(1 / rate)
                    else:
                        raise ValueError(f"Unsupported distribution: '{dist}'")

                    event.metadata["_generated"] = count + 1
                    self.schedule(event, at=end_sim + inter)

        except Exception as exc:
            real_dur = time.perf_counter() - real_start
            event.error = exc
            self._complete_event(event, start_sim, self._now, real_dur, result=None, error=exc)

    def _complete_event(
        self,
        ev: Event,
        start_sim: int,
        end_sim: int,
        real_dur: Optional[float],
        result: Any,
        error: Optional[BaseException] = None,
    ) -> None:
        ev.finished = True
        ev.real_duration = real_dur
        ev.result = result
        ev.error = error

        self.recorder.add(EventRecord(
            event_id=ev.id,
            name=ev.name,
            type=ev.event_type.name,
            start_sim=start_sim,
            end_sim=end_sim,
            duration_sim=end_sim - start_sim,
            duration_real=real_dur,
            result=result,
            error=str(error) if error else None,
            metadata=ev.metadata,
        ))

        if ev.callback_event:
            self.schedule(ev.callback_event, at=end_sim + 1)
