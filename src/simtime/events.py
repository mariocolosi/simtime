from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional, Tuple, Coroutine
from enum import Enum, auto


class EventType(Enum):
    DECLARED_DURATION = auto()
    MEASURED_DURATION = auto()
    PERIODIC = auto()
    RATE_BASED = auto()


@dataclass(order=True)
class ScheduledItem:
    timestamp: int
    order: int
    event: "Event" = field(compare=False)


@dataclass
class Event:
    id: int
    name: str
    func: Callable[..., Any]
    at: int
    duration_ms: Optional[int] = None
    event_type: EventType = EventType.DECLARED_DURATION
    args: Tuple[Any, ...] = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    callback_event: Optional[Event] = None

    # Runtime fields
    started: bool = False
    finished: bool = False
    real_duration: Optional[float] = None
    result: Any = None
    error: Optional[BaseException] = None
