import csv
import json
import os
import pytest
from simtime.metric_store import MetricStore, MetricRecord, TempMetricRecord


# ── TempMetricRecord ──────────────────────────────────────────────────────────

def test_temp_metric_record_is_dataclass():
    rec = TempMetricRecord(id="x", value=42)
    assert rec.id == "x"
    assert rec.value == 42


def test_add_temp_stores_record_instance():
    ms = MetricStore()
    ms.add_temp("x", 99)
    stored = ms.get_temp("x")
    assert isinstance(stored, TempMetricRecord)
    assert stored.value == 99


def test_temp_metric_values_no_attribute_error():
    ms = MetricStore()
    ms.add_temp("a", 1)
    ms.add_temp("b", 2)
    # Must not raise AttributeError
    values = ms.temp_metric_values
    assert set(values) == {1, 2}


def test_get_temp_returns_none_for_missing():
    ms = MetricStore()
    assert ms.get_temp("nonexistent") is None


def test_remove_temp():
    ms = MetricStore()
    ms.add_temp("k", 5)
    ms.remove_temp("k")
    assert ms.get_temp("k") is None
    assert ms.temp_metric_count == 0


def test_remove_temp_idempotent():
    ms = MetricStore()
    ms.remove_temp("nope")  # must not raise


def test_temp_metric_ids():
    ms = MetricStore()
    ms.add_temp("a", 1)
    ms.add_temp("b", 2)
    assert set(ms.temp_metric_ids) == {"a", "b"}


def test_temp_metric_records():
    ms = MetricStore()
    ms.add_temp("x", 10)
    recs = ms.temp_metric_records
    assert len(recs) == 1
    assert isinstance(recs[0], TempMetricRecord)


# ── MetricRecord and add() ────────────────────────────────────────────────────

def test_add_and_retrieve_metric():
    ms = MetricStore()
    ms.add(category="perf", type="latency", name="req", value=123, tags={"host": "a"})
    assert ms.metric_count == 1
    rec = ms.metrics[0]
    assert isinstance(rec, MetricRecord)
    assert rec.value == 123


def test_metrics_returns_copy():
    ms = MetricStore()
    ms.add(category="c", type="t", name="n", value=1)
    copy = ms.metrics
    copy.clear()
    assert ms.metric_count == 1


def test_get_by_category():
    ms = MetricStore()
    ms.add(category="perf", type="lat", name="a", value=1)
    ms.add(category="perf", type="thr", name="b", value=2)
    ms.add(category="other", type="x", name="c", value=3)
    perf = ms.get_by_category("perf")
    assert len(perf) == 2
    assert all(r.category == "perf" for r in perf)


def test_get_by_category_empty():
    ms = MetricStore()
    assert ms.get_by_category("missing") == []


def test_categories_types_names():
    ms = MetricStore()
    ms.add(category="A", type="X", name="n1", value=1)
    ms.add(category="B", type="Y", name="n2", value=2)
    assert set(ms.categories) == {"A", "B"}
    assert set(ms.types) == {"X", "Y"}
    assert set(ms.names) == {"n1", "n2"}


def test_tags_aggregation():
    ms = MetricStore()
    ms.add(category="c", type="t", name="n", value=1, tags={"host": "a", "env": "prod"})
    ms.add(category="c", type="t", name="n", value=2, tags={"host": "b"})
    assert set(ms.tags) == {"host", "env"}


def test_tags_no_error_when_tags_none():
    ms = MetricStore()
    ms.add(category="c", type="t", name="n", value=1)  # tags=None
    assert ms.tags == []


# ── to_dicts() and export ─────────────────────────────────────────────────────

def test_to_dicts():
    ms = MetricStore()
    ms.add(category="perf", type="lat", name="req", value=42)
    dicts = ms.to_dicts()
    assert len(dicts) == 1
    assert dicts[0]["value"] == 42


def test_to_dataframe_requires_pandas():
    pytest.importorskip("pandas")
    ms = MetricStore()
    ms.add(category="c", type="t", name="n", value=7)
    df = ms.to_dataframe()
    assert len(df) == 1


def test_get_metrics_deprecated():
    pytest.importorskip("pandas")
    ms = MetricStore()
    ms.add(category="c", type="t", name="n", value=1)
    with pytest.warns(DeprecationWarning, match="to_dataframe"):
        ms.get_metrics()


def test_save_json(tmp_path):
    ms = MetricStore()
    ms.add(category="perf", type="lat", name="req", value=99)
    path = str(tmp_path / "metrics.json")
    ms.save_json(path)
    with open(path) as f:
        data = json.load(f)
    assert data[0]["value"] == 99


def test_save_csv_stdlib(tmp_path, monkeypatch):
    import simtime.metric_store as ms_mod
    monkeypatch.setattr(ms_mod, "pd", None)
    ms = MetricStore()
    ms.add(category="c", type="t", name="n", value=5)
    path = str(tmp_path / "metrics.csv")
    ms.save_csv(path)
    with open(path) as f:
        reader = list(csv.DictReader(f))
    assert reader[0]["value"] == "5"


def test_save_csv_empty_no_file(tmp_path, monkeypatch):
    import simtime.metric_store as ms_mod
    monkeypatch.setattr(ms_mod, "pd", None)
    ms = MetricStore()
    path = str(tmp_path / "metrics.csv")
    ms.save_csv(path)
    assert not os.path.exists(path)
