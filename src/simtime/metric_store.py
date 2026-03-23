from __future__ import annotations
import csv
import json
import warnings
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

try:
    import pandas as pd
except ImportError:
    pd = None


@dataclass
class MetricRecord:
    category: str
    type: str
    name: str
    value: Any
    tags: Optional[Dict[str, Any]] = None


@dataclass
class TempMetricRecord:
    id: str
    value: Any


class MetricStore:
    def __init__(self):
        self._metrics: List[MetricRecord] = []
        self._temp_metrics: Dict[str, TempMetricRecord] = {}

    def add(self, category: str, type: str, name: str, value: Any, tags: Optional[Dict[str, Any]] = None) -> None:
        """Add a persistent metric record."""
        record = MetricRecord(category=category, type=type, name=name, value=value, tags=tags)
        self._metrics.append(record)

    def add_temp(self, id: str, value: Any) -> None:
        """Add or update a temporary metric by id."""
        self._temp_metrics[id] = TempMetricRecord(id=id, value=value)

    def get_temp(self, id: str) -> Optional[TempMetricRecord]:
        """Return the TempMetricRecord for the given id, or None."""
        return self._temp_metrics.get(id)

    def remove_temp(self, id: str) -> None:
        """Remove a temporary metric by id."""
        self._temp_metrics.pop(id, None)

    def get_by_category(self, category: str) -> List[MetricRecord]:
        """Return all metrics with the given category."""
        return [m for m in self._metrics if m.category == category]

    def to_dicts(self) -> List[Dict[str, Any]]:
        """Return metrics as a list of dicts. No external dependencies required."""
        return [r.__dict__.copy() for r in self._metrics]

    def to_dataframe(self):
        """Return metrics as a pandas DataFrame. Requires pandas."""
        if pd is None:
            raise ImportError("pandas is required for to_dataframe()")
        return pd.DataFrame(self.to_dicts())

    def get_metrics(self):
        """Deprecated: use to_dataframe() instead."""
        warnings.warn(
            "get_metrics() is deprecated, use to_dataframe() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.to_dataframe()

    def save_csv(self, path: str) -> None:
        """Save metrics to a CSV file. Uses pandas if available, else stdlib csv."""
        if pd is not None:
            self.to_dataframe().to_csv(path, index=False)
        else:
            rows = self.to_dicts()
            if not rows:
                return
            with open(path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)

    def save_json(self, path: str) -> None:
        """Save metrics to a JSON file."""
        with open(path, "w") as f:
            json.dump(self.to_dicts(), f, indent=2, default=str)

    @property
    def metrics(self) -> List[MetricRecord]:
        return list(self._metrics)

    @property
    def temp_metrics(self) -> Dict[str, TempMetricRecord]:
        return dict(self._temp_metrics)

    @property
    def temp_metric_ids(self) -> List[str]:
        return list(self._temp_metrics.keys())

    @property
    def temp_metric_values(self) -> List[Any]:
        return [tm.value for tm in self._temp_metrics.values()]

    @property
    def temp_metric_records(self) -> List[TempMetricRecord]:
        return list(self._temp_metrics.values())

    @property
    def temp_metric_count(self) -> int:
        return len(self._temp_metrics)

    @property
    def metric_count(self) -> int:
        return len(self._metrics)

    @property
    def categories(self) -> List[str]:
        return list(set(m.category for m in self._metrics))

    @property
    def types(self) -> List[str]:
        return list(set(m.type for m in self._metrics))

    @property
    def names(self) -> List[str]:
        return list(set(m.name for m in self._metrics))

    @property
    def tags(self) -> List[str]:
        return list(set(tag for m in self._metrics for tag in (m.tags or {}).keys()))
