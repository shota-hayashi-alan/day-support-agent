"""外部データの取り込み。データ源は Source を実装して差し替える。

Source は `records()` で次の形の dict を返す:
  {"id": 一意ID, "date": "YYYY-MM-DD", "habit": 習慣名/別名, "amount": 数値(省略可)}
(source, id) が同じ記録は二重登録されない。
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable, Protocol

from .habits import HabitTracker


class Source(Protocol):
    name: str

    def records(self) -> Iterable[dict]: ...


class FileSource:
    """JSON(配列) または CSV(列: id,date,habit,amount)。
    スマホのショートカット、IFTTT、各種アプリのエクスポートの受け皿に使える。"""

    name = "file"

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def records(self) -> list[dict]:
        text = self.path.read_text(encoding="utf-8")
        if self.path.suffix.lower() == ".json":
            return json.loads(text)
        return list(csv.DictReader(text.splitlines()))


def sync(tracker: HabitTracker, source: Source) -> dict:
    added, duplicate, errors = 0, 0, []
    for i, r in enumerate(source.records()):
        try:
            amount = r.get("amount")
            amount = float(amount) if amount not in (None, "") else None
            ext = str(r["id"]) if r.get("id") not in (None, "") else None
            if tracker.log(r["habit"], r["date"], amount, source.name, ext):
                added += 1
            else:
                duplicate += 1
        except (KeyError, ValueError) as e:
            errors.append(f"{i + 1}件目: {e}")
    return {"added": added, "duplicate": duplicate, "errors": errors}
