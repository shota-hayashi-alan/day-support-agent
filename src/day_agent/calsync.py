"""Googleカレンダーの「✅ 習慣名 30分」という予定を、習慣の実績として取り込む。

書き方の例:  ✅ピアノ 30分 / ✅英語 1時間 / ✅運動 (分は予定の長さから) / ✅筋トレ (回数の習慣は1回)
"""
from __future__ import annotations

import re
from datetime import date, timedelta

from .habits import HabitTracker

MARKS = ("✅", "✔", "☑")
_AMOUNT = re.compile(
    r"(\d+(?:\.\d+)?)\s*(時間|hours?|hrs?|h|分|mins?|m)(?![a-z])", re.IGNORECASE)


def parse_title(title: str) -> tuple[str, float | None] | None:
    """'✅ピアノ 30分' → ('ピアノ', 30.0)。✅で始まらなければ None。量が無ければ量は None。"""
    t = title.strip()
    if not t.startswith(MARKS):
        return None
    t = t.lstrip("".join(MARKS) + "️").strip()
    amount = None
    m = None
    for m in _AMOUNT.finditer(t):  # 最後に出てくるものを採用
        pass
    if m:
        value, unit = float(m.group(1)), m.group(2).lower()
        amount = value * 60 if unit in ("時間", "h", "hr", "hrs", "hour", "hours") else value
        t = (t[:m.start()] + t[m.end():]).strip()
    return t.strip(" ・-:：/"), amount


def _resolve(tracker: HabitTracker, text: str) -> dict | None:
    """完全一致、無ければ『本文に含まれる最長の名前/別名』で習慣を探す。"""
    h = tracker.find(text)
    if h:
        return h
    low = text.lower()
    best, best_len = None, 0
    for h in tracker.store.data["habits"]:
        for name in (h["name"], *h["aliases"]):
            if name.lower() in low and len(name) > best_len:
                best, best_len = h, len(name)
    return best


def _duration_minutes(ev: dict) -> float | None:
    if not ev["end"] or ev["note"].startswith("終日"):
        return None
    mins = (int(ev["end"][:2]) * 60 + int(ev["end"][3:])
            - int(ev["start"][:2]) * 60 - int(ev["start"][3:]))
    return float(mins) if mins > 0 else None


class CalendarHabitSource:
    name = "calendar"

    def __init__(self, calendar, tracker: HabitTracker, days: int = 14,
                 today: date | None = None):
        self.calendar, self.tracker, self.days = calendar, tracker, days
        self.today = today or date.today()

    def records(self) -> list[dict]:
        start = self.today - timedelta(days=self.days - 1)
        out = []
        for ev in self.calendar.list_events(start.isoformat(), self.today.isoformat()):
            parsed = parse_title(ev["title"])
            if not parsed:
                continue
            text, amount = parsed
            habit = _resolve(self.tracker, text)
            if habit and amount is None and habit["unit"] == "min":
                amount = _duration_minutes(ev)  # 無ければ後段で「分が必要」エラーになる
            out.append({"id": ev["id"], "date": ev["date"],
                        "habit": habit["name"] if habit else text or ev["title"],
                        "amount": amount if habit and habit["unit"] == "min" else None})
        return out
