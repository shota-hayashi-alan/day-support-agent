"""習慣トラッカー: 目標(週ごと)・記録・進捗・ストリーク。"""
from __future__ import annotations

from datetime import date, timedelta

from .store import DATE_FMT, Store

UNITS = ("min", "times")


def week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())  # 月曜始まり


class HabitTracker:
    def __init__(self, store: Store):
        self.store = store
        store.data.setdefault("habits", [])
        store.data.setdefault("logs", [])

    # --- 習慣の定義 ---
    def find(self, ref) -> dict | None:
        """ID または 名前/別名(完全一致) で習慣を探す。"""
        for h in self.store.data["habits"]:
            if h["id"] == ref or ref in [h["name"], *h["aliases"]]:
                return h
        return None

    def create(self, name: str, unit: str = "min", weekly_target: float = 0,
               aliases: list[str] | None = None) -> dict:
        if unit not in UNITS:
            raise ValueError("unit は min / times のいずれか")
        if self.find(name):
            raise ValueError(f"'{name}' は既にあります")
        h = {"id": self.store._new_id(), "name": name, "unit": unit,
             "weekly_target": weekly_target, "aliases": aliases or []}
        self.store.data["habits"].append(h)
        self.store._save()
        return h

    def update(self, ref, weekly_target: float | None = None,
               unit: str | None = None) -> dict:
        h = self._must(ref)
        if unit is not None:
            if unit not in UNITS:
                raise ValueError("unit は min / times のいずれか")
            h["unit"] = unit
        if weekly_target is not None:
            h["weekly_target"] = weekly_target
        self.store._save()
        return h

    def _must(self, ref) -> dict:
        h = self.find(ref)
        if not h:
            raise ValueError(f"習慣 '{ref}' が見つかりません")
        return h

    # --- 記録 ---
    def log(self, ref, on: str, amount: float | None = None, source: str = "manual",
            ext_id: str | None = None) -> dict | None:
        """記録を追加。amount省略時は times=1 / min は必須。同一 (source, ext_id) は重複として None。"""
        h = self._must(ref)
        date.fromisoformat(on)
        if amount is None:
            if h["unit"] == "min":
                raise ValueError("分単位の習慣は amount(分)が必要です")
            amount = 1
        if amount <= 0:
            raise ValueError("amount は正の数にしてください")
        if ext_id is not None and any(
                l["habit_id"] == h["id"] and l["source"] == source and l["ext_id"] == ext_id
                for l in self.store.data["logs"]):
            return None
        entry = {"habit_id": h["id"], "date": on, "amount": amount,
                 "source": source, "ext_id": ext_id}
        self.store.data["logs"].append(entry)
        self.store._save()
        return entry

    def _daily(self, habit_id: int) -> dict[str, float]:
        out: dict[str, float] = {}
        for l in self.store.data["logs"]:
            if l["habit_id"] == habit_id:
                out[l["date"]] = out.get(l["date"], 0) + l["amount"]
        return out

    # --- 進捗 ---
    def progress(self, ref, today: date) -> dict:
        h = self._must(ref)
        daily = self._daily(h["id"])
        ws = week_start(today)
        days = [(ws + timedelta(days=i)).strftime(DATE_FMT) for i in range(7)]
        done = sum(daily.get(d, 0) for d in days)
        target = h["weekly_target"]
        return {"habit": h["name"], "unit": h["unit"], "weekly_target": target,
                "this_week": done, "remaining": max(target - done, 0),
                "achieved": bool(target) and done >= target,
                "days_done_this_week": sum(1 for d in days if daily.get(d)),
                "days_left_this_week": 6 - today.weekday(),
                "streak_days": self._streak(daily, today)}

    @staticmethod
    def _streak(daily: dict[str, float], today: date) -> int:
        """連続日数。今日まだ未実施でも昨日までの連続は途切れない。"""
        d = today if daily.get(today.strftime(DATE_FMT)) else today - timedelta(days=1)
        n = 0
        while daily.get(d.strftime(DATE_FMT)):
            n += 1
            d -= timedelta(days=1)
        return n

    def all_progress(self, today: date) -> list[dict]:
        return [self.progress(h["id"], today) for h in self.store.data["habits"]]
