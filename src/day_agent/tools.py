"""Claudに渡すツール定義と実行ディスパッチ。"""
from __future__ import annotations

import json
from datetime import date, timedelta

from .store import Store

TOOLS = [
    {"name": "add_event",
     "description": "予定をカレンダーに追加する。同時間帯に既存の予定があれば conflicts として返す。",
     "input_schema": {"type": "object", "properties": {
         "title": {"type": "string"},
         "date": {"type": "string", "description": "YYYY-MM-DD"},
         "start": {"type": "string", "description": "HH:MM"},
         "end": {"type": "string", "description": "HH:MM (任意)"},
         "note": {"type": "string"}},
         "required": ["title", "date", "start"]}},
    {"name": "list_events",
     "description": "指定期間の予定を一覧する。date_to省略時は1日分。",
     "input_schema": {"type": "object", "properties": {
         "date_from": {"type": "string"}, "date_to": {"type": "string"}},
         "required": ["date_from"]}},
    {"name": "delete_event",
     "description": "予定をIDで削除する。",
     "input_schema": {"type": "object", "properties": {"event_id": {"type": ["integer", "string"]}},
                      "required": ["event_id"]}},
    {"name": "add_wish",
     "description": "「やりたいこと」リストに項目を追加する。",
     "input_schema": {"type": "object", "properties": {
         "title": {"type": "string"},
         "priority": {"type": "string", "enum": ["high", "medium", "low"]},
         "est_minutes": {"type": "integer", "description": "所要時間の目安(分)"},
         "deadline": {"type": "string", "description": "YYYY-MM-DD"}},
         "required": ["title"]}},
    {"name": "list_wishes",
     "description": "未完了のやりたいことを期限・優先度順に一覧する。",
     "input_schema": {"type": "object", "properties": {
         "include_done": {"type": "boolean"}}}},
    {"name": "complete_wish",
     "description": "やりたいことを完了にする。",
     "input_schema": {"type": "object", "properties": {"wish_id": {"type": "integer"}},
                      "required": ["wish_id"]}},
    {"name": "get_today",
     "description": "今日の日付と曜日を返す。",
     "input_schema": {"type": "object", "properties": {}}},
]

WEEKDAYS = "月火水木金土日"


def run_tool(store: Store, name: str, args: dict, calendar=None) -> str:
    try:
        return json.dumps(_dispatch(store, calendar or store, name, args),
                          ensure_ascii=False)
    except Exception as e:  # ツール内エラーはモデルに返して自己修正させる
        return json.dumps({"error": str(e)}, ensure_ascii=False)


def _dispatch(store: Store, cal, name: str, a: dict):
    if name == "add_event":
        conflicts = cal.find_conflicts(a["date"], a["start"], a.get("end"))
        ev = cal.add_event(a["title"], a["date"], a["start"], a.get("end"),
                             a.get("note", ""))
        return {"added": ev, "conflicts": conflicts}
    if name == "list_events":
        return cal.list_events(a["date_from"], a.get("date_to"))
    if name == "delete_event":
        return {"deleted": cal.delete_event(a["event_id"])}
    if name == "add_wish":
        return store.add_wish(a["title"], a.get("priority", "medium"),
                              a.get("est_minutes"), a.get("deadline"))
    if name == "list_wishes":
        return store.list_wishes(a.get("include_done", False))
    if name == "complete_wish":
        return {"completed": store.complete_wish(a["wish_id"])}
    if name == "get_today":
        t = date.today()
        return {"date": t.isoformat(), "weekday": WEEKDAYS[t.weekday()],
                "tomorrow": (t + timedelta(days=1)).isoformat()}
    raise ValueError(f"unknown tool: {name}")
