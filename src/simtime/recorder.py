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
class EventRecord:
    event_id: int
    name: str
    type: str
    start_sim: int
    end_sim: int
    duration_sim: int
    duration_real: Optional[float]
    result: Any
    error: Optional[str]
    metadata: Dict[str, Any]


class Recorder:
    def __init__(self):
        self._records: List[EventRecord] = []

    def add(self, record: EventRecord) -> None:
        self._records.append(record)

    def to_dicts(self) -> List[Dict[str, Any]]:
        """Return records as a list of dicts. No external dependencies required."""
        return [r.__dict__.copy() for r in self._records]

    def to_dataframe(self):
        """Return records as a pandas DataFrame. Requires pandas."""
        if pd is None:
            raise ImportError("pandas is required for to_dataframe()")
        return pd.DataFrame(self.to_dicts())

    def get_records(self):
        """Deprecated: use to_dataframe() instead."""
        warnings.warn(
            "get_records() is deprecated, use to_dataframe() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.to_dataframe()

    def save_csv(self, path: str) -> None:
        """Save records to a CSV file. Uses pandas if available, else stdlib csv."""
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
        """Save records to a JSON file."""
        with open(path, "w") as f:
            json.dump(self.to_dicts(), f, indent=2, default=str)

    @property
    def records(self) -> List[EventRecord]:
        return list(self._records)
