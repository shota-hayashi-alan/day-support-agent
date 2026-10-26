"""ローカルJSONによる予定・やりたいことの保存。"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

DATE_FMT = "%Y-%m-%d"
TIME_FMT = "%H:%M"


def default_path() -> Path:
    return Path(os.environ.get("DAY_AGENT_DATA", "data/store.json"))


class Store:
    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path else default_path()
        self.data = {"events": [], "wishes": [], "next_id": 1}
        if self.path.exists():
            self.data = json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def _new_id(self) -> int:
        i = self.data["next_id"]
        self.data["next_id"] = i + 1
        return i

    # --- 予定 ---
    def add_event(self, title: str, date: str, start: str, end: str | None = None,
                  note: str = "") -> dict:
        datetime.strptime(date, DATE_FMT)
        datetime.strptime(start, TIME_FMT)
        if end:
            datetime.strptime(end, TIME_FMT)
            if end <= start:
                raise ValueError("終了時刻は開始時刻より後にしてください")
        ev = {"id": self._new_id(), "title": title, "date": date,
              "start": start, "end": end, "note": note}
        self.data["events"].append(ev)
        self._save()
        return ev

    def list_events(self, date_from: str, date_to: str | None = None) -> list[dict]:
        date_to = date_to or date_from
        evs = [e for e in self.data["events"] if date_from <= e["date"] <= date_to]
        return sorted(evs, key=lambda e: (e["date"], e["start"]))

    def delete_event(self, event_id: int) -> bool:
        before = len(self.data["events"])
        self.data["events"] = [e for e in self.data["events"] if e["id"] != event_id]
        changed = len(self.data["events"]) != before
        if changed:
            self._save()
        return changed

    def find_conflicts(self, date: str, start: str, end: str | None) -> list[dict]:
        end = end or start
        return [e for e in self.list_events(date)
                if start < (e["end"] or e["start"]) and e["start"] < end
                or (start == e["start"])]

    # --- やりたいこと ---
    def add_wish(self, title: str, priority: str = "medium",
                 est_minutes: int | None = None, deadline: str | None = None) -> dict:
        if priority not in ("high", "medium", "low"):
            raise ValueError("priority は high / medium / low のいずれか")
        if deadline:
            datetime.strptime(deadline, DATE_FMT)
        w = {"id": self._new_id(), "title": title, "priority": priority,
             "est_minutes": est_minutes, "deadline": deadline, "done": False}
        self.data["wishes"].append(w)
        self._save()
        return w

    def list_wishes(self, include_done: bool = False) -> list[dict]:
        order = {"high": 0, "medium": 1, "low": 2}
        ws = [w for w in self.data["wishes"] if include_done or not w["done"]]
        return sorted(ws, key=lambda w: (w["deadline"] or "9999", order[w["priority"]]))

    def complete_wish(self, wish_id: int) -> bool:
        for w in self.data["wishes"]:
            if w["id"] == wish_id:
                w["done"] = True
                self._save()
                return True
        return False
