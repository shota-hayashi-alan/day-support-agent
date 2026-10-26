import json
from datetime import date

import pytest

from day_agent.brief import build_context
from day_agent.habits import HabitTracker
from day_agent.store import Store
from day_agent.sync import FileSource, sync
from day_agent.tools import run_tool

WED = date(2026, 10, 28)  # 水曜


@pytest.fixture
def ht(tmp_path):
    h = HabitTracker(Store(tmp_path / "s.json"))
    h.create("運動", "min", 150, ["exercise"])
    return h


def test_progress_counts_only_this_week(ht):
    ht.log("運動", "2026-10-25", 60)   # 先週日曜
    ht.log("運動", "2026-10-26", 40)   # 今週月曜
    ht.log("exercise", "2026-10-28", 30)  # 別名
    p = ht.progress("運動", WED)
    assert (p["this_week"], p["remaining"], p["days_done_this_week"]) == (70, 80, 2)
    assert p["days_left_this_week"] == 4 and not p["achieved"]


def test_streak_survives_unlogged_today(ht):
    for d in ("2026-10-26", "2026-10-27"):
        ht.log("運動", d, 10)
    assert ht.progress("運動", WED)["streak_days"] == 2
    ht.log("運動", "2026-10-28", 10)
    assert ht.progress("運動", WED)["streak_days"] == 3


def test_validation(ht):
    with pytest.raises(ValueError):
        ht.log("運動", "2026-10-28")  # 分の習慣は量が必要
    with pytest.raises(ValueError):
        ht.log("存在しない", "2026-10-28", 5)
    with pytest.raises(ValueError):
        ht.create("運動")


def test_times_unit_defaults_to_one(tmp_path):
    h = HabitTracker(Store(tmp_path / "s.json"))
    h.create("筋トレ", "times", 3)
    h.log("筋トレ", "2026-10-28")
    assert h.progress("筋トレ", WED)["this_week"] == 1


def test_sync_file_dedupes_and_reports_errors(ht, tmp_path):
    f = tmp_path / "in.json"
    f.write_text(json.dumps([
        {"id": "a1", "date": "2026-10-27", "habit": "運動", "amount": 45},
        {"id": "a2", "date": "2026-10-28", "habit": "運動", "amount": "30"},
        {"id": "x", "date": "2026-10-28", "habit": "不明", "amount": 5}]))
    assert sync(ht, FileSource(f)) == {"added": 2, "duplicate": 0,
                                       "errors": ["3件目: 習慣 '不明' が見つかりません"]}
    assert sync(ht, FileSource(f))["duplicate"] == 2
    assert ht.progress("運動", WED)["this_week"] == 75


def test_sync_csv(ht, tmp_path):
    f = tmp_path / "in.csv"
    f.write_text("id,date,habit,amount\nc1,2026-10-27,運動,20\n")
    assert sync(ht, FileSource(f))["added"] == 1


def test_tools_and_persistence(tmp_path):
    st = Store(tmp_path / "s.json")
    run_tool(st, "create_habit", {"name": "英語", "weekly_target": 100})
    out = json.loads(run_tool(st, "log_habit", {"habit": "英語", "amount": 25}))
    assert out["progress"]["this_week"] == 25
    assert HabitTracker(Store(tmp_path / "s.json")).find("英語")


def test_brief_includes_habits(ht):
    ht.log("運動", "2026-10-28", 150)
    text = build_context(ht.store, ht.store, WED)
    assert "運動: 150/150分 達成!" in text and "連続1日" in text
