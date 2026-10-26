import json

import pytest

from day_agent.store import Store
from day_agent.tools import run_tool


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path / "s.json")


def test_event_roundtrip_and_sort(store):
    store.add_event("B", "2026-10-27", "14:00", "15:00")
    store.add_event("A", "2026-10-27", "09:00", "10:00")
    assert [e["title"] for e in store.list_events("2026-10-27")] == ["A", "B"]
    assert Store(store.path).list_events("2026-10-27")[0]["title"] == "A"


def test_conflict_detected(store):
    store.add_event("会議", "2026-10-27", "10:00", "11:00")
    out = json.loads(run_tool(store, "add_event", {
        "title": "歯医者", "date": "2026-10-27", "start": "10:30", "end": "11:30"}))
    assert len(out["conflicts"]) == 1


def test_no_conflict_when_adjacent(store):
    store.add_event("会議", "2026-10-27", "10:00", "11:00")
    assert store.find_conflicts("2026-10-27", "11:00", "12:00") == []


def test_bad_time_returns_error(store):
    out = json.loads(run_tool(store, "add_event", {
        "title": "x", "date": "2026-10-27", "start": "25:00"}))
    assert "error" in out


def test_wish_order_and_complete(store):
    store.add_wish("低", "low")
    store.add_wish("期限あり", "low", deadline="2026-11-01")
    w = store.add_wish("高", "high")
    assert [x["title"] for x in store.list_wishes()] == ["期限あり", "高", "低"]
    store.complete_wish(w["id"])
    assert "高" not in [x["title"] for x in store.list_wishes()]
