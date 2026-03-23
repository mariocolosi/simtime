import csv
import json
import os
import pytest
from simtime.recorder import Recorder, EventRecord


def make_record(event_id=0, name="test", sim_start=0, sim_end=10):
    return EventRecord(
        event_id=event_id,
        name=name,
        type="DECLARED_DURATION",
        start_sim=sim_start,
        end_sim=sim_end,
        duration_sim=sim_end - sim_start,
        duration_real=0.001,
        result="ok",
        error=None,
        metadata={},
    )


def test_add_and_access_records():
    r = Recorder()
    rec = make_record()
    r.add(rec)
    assert len(r.records) == 1
    assert r.records[0] is rec


def test_records_returns_copy():
    r = Recorder()
    r.add(make_record())
    copy = r.records
    copy.clear()
    assert len(r.records) == 1


def test_to_dicts():
    r = Recorder()
    r.add(make_record(event_id=7, name="foo"))
    dicts = r.to_dicts()
    assert len(dicts) == 1
    assert dicts[0]["event_id"] == 7
    assert dicts[0]["name"] == "foo"


def test_to_dicts_returns_copies():
    r = Recorder()
    r.add(make_record())
    d = r.to_dicts()
    d[0]["name"] = "mutated"
    assert r.records[0].name == "test"


def test_to_dataframe_requires_pandas():
    pd = pytest.importorskip("pandas")
    r = Recorder()
    r.add(make_record())
    df = r.to_dataframe()
    assert len(df) == 1
    assert list(df["name"]) == ["test"]


def test_get_records_deprecated():
    pytest.importorskip("pandas")
    r = Recorder()
    r.add(make_record())
    with pytest.warns(DeprecationWarning, match="to_dataframe"):
        r.get_records()


def test_save_json(tmp_path):
    r = Recorder()
    r.add(make_record(event_id=3))
    path = str(tmp_path / "out.json")
    r.save_json(path)
    with open(path) as f:
        data = json.load(f)
    assert data[0]["event_id"] == 3


def test_save_csv_stdlib(tmp_path, monkeypatch):
    """save_csv should work even without pandas."""
    import simtime.recorder as recorder_mod
    monkeypatch.setattr(recorder_mod, "pd", None)
    r = Recorder()
    r.add(make_record(event_id=5))
    path = str(tmp_path / "out.csv")
    r.save_csv(path)
    with open(path) as f:
        reader = list(csv.DictReader(f))
    assert reader[0]["event_id"] == "5"


def test_save_csv_empty_file_not_created(tmp_path, monkeypatch):
    """save_csv on empty recorder should not write a file (stdlib path)."""
    import simtime.recorder as recorder_mod
    monkeypatch.setattr(recorder_mod, "pd", None)
    r = Recorder()
    path = str(tmp_path / "out.csv")
    r.save_csv(path)
    assert not os.path.exists(path)
