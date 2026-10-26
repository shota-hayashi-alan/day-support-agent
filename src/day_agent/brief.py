"""朝のブリーフィング: 今日の予定・空き時間・やりたいことをまとめる。"""
from __future__ import annotations

from datetime import date, timedelta

from .habits import HabitTracker
from .store import DATE_FMT, Store
from .tools import WEEKDAYS

DAY_START, DAY_END = "08:00", "22:00"
MIN_SLOT_MIN = 30

BRIEF_PROMPT = """以下は、ユーザーの今日の予定・空き時間・やりたいことです。
朝のブリーフィングとして、次の構成で簡潔な日本語にまとめてください。
1. 今日のひとこと(予定の多さや注意点)
2. 今日の予定
3. おすすめの1日の過ごし方(空き時間にやりたいことを具体的に割り当てる。無理は禁物)
4. 期限が近いもの・気になる点
5. 習慣の週目標に対して遅れているものがあれば、空き時間に具体的に組み込む
予定を勝手に追加・変更しないこと。データにない情報は作らないこと。

{context}"""


def _mins(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def _hhmm(mins: int) -> str:
    return f"{mins // 60:02d}:{mins % 60:02d}"


def free_slots(events: list[dict]) -> list[tuple[str, str]]:
    """DAY_START〜DAY_END の中で、MIN_SLOT_MIN 分以上の空き時間を返す。"""
    cursor, limit = _mins(DAY_START), _mins(DAY_END)
    slots = []
    for e in sorted(events, key=lambda e: e["start"]):
        s = _mins(e["start"])
        e_end = _mins(e["end"]) if e["end"] else s
        if s - cursor >= MIN_SLOT_MIN:
            slots.append((_hhmm(cursor), _hhmm(min(s, limit))))
        cursor = max(cursor, e_end)
    if limit - cursor >= MIN_SLOT_MIN:
        slots.append((_hhmm(cursor), _hhmm(limit)))
    return slots


def _fmt_event(e: dict) -> str:
    span = e["start"] + (f"-{e['end']}" if e["end"] else "")
    return f"{span} {e['title']}" + (f" ({e['note']})" if e["note"] else "")


def _fmt_wish(w: dict, today: date) -> str:
    parts = [f"[{w['priority']}] {w['title']}"]
    if w["est_minutes"]:
        parts.append(f"{w['est_minutes']}分")
    if w["deadline"]:
        days = (date.fromisoformat(w["deadline"]) - today).days
        parts.append(f"期限 {w['deadline']}(" + (
            f"{-days}日超過" if days < 0 else "今日" if days == 0 else f"あと{days}日") + ")")
    return " / ".join(parts)


def _fmt_habit(p: dict) -> str:
    u = "分" if p["unit"] == "min" else "回"
    goal = f"{p['this_week']:g}/{p['weekly_target']:g}{u}" if p["weekly_target"] \
        else f"{p['this_week']:g}{u}"
    status = "達成!" if p["achieved"] else (
        f"残り{p['remaining']:g}{u}・今日含め{p['days_left_this_week'] + 1}日" if p["weekly_target"] else "")
    return f"- {p['habit']}: {goal} {status} 連続{p['streak_days']}日".replace("  ", " ")


def build_context(store: Store, calendar, today: date) -> str:
    """AIに渡す(または --plain でそのまま表示する)素材テキスト。"""
    d = today.strftime(DATE_FMT)
    tomorrow = (today + timedelta(days=1)).strftime(DATE_FMT)
    events = calendar.list_events(d)
    lines = [f"■ 日付: {d} ({WEEKDAYS[today.weekday()]}曜日)", "", "■ 今日の予定"]
    lines += [f"- {_fmt_event(e)}" for e in events] or ["- なし"]
    lines += ["", f"■ 空き時間 ({DAY_START}-{DAY_END}, {MIN_SLOT_MIN}分以上)"]
    lines += [f"- {a}-{b}" for a, b in free_slots(events)] or ["- なし"]
    lines += ["", "■ 明日の予定"]
    lines += [f"- {_fmt_event(e)}" for e in calendar.list_events(tomorrow)] or ["- なし"]
    lines += ["", "■ やりたいこと(未完了、期限・優先度順)"]
    lines += [f"- {_fmt_wish(w, today)}" for w in store.list_wishes()] or ["- なし"]
    habits = HabitTracker(store).all_progress(today)
    if habits:
        lines += ["", "■ 習慣の今週の進捗"]
        lines += [_fmt_habit(p) for p in habits]
    return "\n".join(lines)


def morning_brief(store: Store, calendar=None, client=None, today: date | None = None,
                  plain: bool = False) -> str:
    today = today or date.today()
    context = build_context(store, calendar or store, today)
    if plain:
        return context
    import anthropic
    from .agent import MODEL
    client = client or anthropic.Anthropic()
    resp = client.messages.create(
        model=MODEL, max_tokens=1500,
        messages=[{"role": "user", "content": BRIEF_PROMPT.format(context=context)}])
    return "".join(b.text for b in resp.content if b.type == "text")
