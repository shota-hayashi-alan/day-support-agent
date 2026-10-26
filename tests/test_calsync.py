from datetime import date

import pytest

from day_agent.calsync import CalendarHabitSource, parse_title
from day_agent.habits import HabitTracker
from day_agent.store import Store
from day_agent.sync import sync

TODAY = date(2026, 10, 28)


@pytest.mark.parametrize("title,expected", [
    ("✅ピアノ 30分", ("ピアノ", 30)),
    ("✅英語 1時間", ("英語", 60)),
    ("✅英語1.5h", ("英語", 90)),
    ("✅ 小説の執筆・45min", ("小説の執筆", 45)),
    ("✅運動", ("運動", None)),
    ("✔️ピアノ 20m", ("ピアノ", 20)),
])
def test_parse_title(title, expected):
    assert parse_title(title) == expected


def test_parse_ignores_non_marked():
    assert parse_title("ピアノ 30分") is None
    assert parse_title("会議 ✅") is None


class Cal:
    def __init__(self, events):
        self.events, self.range = events, None

    def list_events(self, a, b):
        self.range = (a, b)
        return self.events


def ev(i, title, date_="2026-10-27", start="19:00", end="19:30", note=""):
    return {"id": i, "title": title, "date": date_, "start": start, "end": end, "note": note}


@pytest.fixture
def ht(tmp_path):
    h = HabitTracker(Store(tmp_path / "s.json"))
    h.create("ピアノの練習", "min", 120, ["ピアノ"])
    h.create("英語", "min", 150)
    h.create("筋トレ", "times", 3)
    return h


def test_end_to_end(ht):
    cal = Cal([
        ev("e1", "✅ピアノ 30分"),                       # 分はタイトルから
        ev("e2", "✅英語", start="07:00", end="07:45"),   # 分は予定の長さから
        ev("e3", "✅ピアノ練習 20分", date_="2026-10-26"),  # 別名を含む → ピアノの練習
        ev("e4", "✅筋トレ"),                             # 回数の習慣は1回
        ev("e5", "歯医者"),                               # ✅なし → 無視
    ])
    res = sync(ht, CalendarHabitSource(cal, ht, today=TODAY))
    assert res == {"added": 4, "duplicate": 0, "errors": []}
    assert cal.range == ("2026-10-15", "2026-10-28")
    wk = {p["habit"]: p["this_week"] for p in ht.all_progress(TODAY)}
    assert wk == {"ピアノの練習": 50, "英語": 45, "筋トレ": 1}
    assert sync(ht, CalendarHabitSource(cal, ht, today=TODAY))["duplicate"] == 4


def test_errors_are_reported(ht):
    cal = Cal([ev("x1", "✅ヨガ 30分"),                    # 未登録の習慣
               ev("x2", "✅英語", end=None, note="終日")])  # 分が決められない
    res = sync(ht, CalendarHabitSource(cal, ht, today=TODAY))
    assert res["added"] == 0 and len(res["errors"]) == 2
