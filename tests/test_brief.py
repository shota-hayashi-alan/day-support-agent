from datetime import date

from day_agent.brief import build_context, free_slots, morning_brief
from day_agent.store import Store

TODAY = date(2026, 10, 27)  # 火曜


def test_free_slots_between_events():
    evs = [{"start": "10:00", "end": "11:00"}, {"start": "12:00", "end": "13:00"}]
    assert free_slots(evs) == [("08:00", "10:00"), ("11:00", "12:00"), ("13:00", "22:00")]


def test_free_slots_skips_short_gap_and_overlap():
    evs = [{"start": "08:10", "end": "12:00"}, {"start": "11:00", "end": "12:15"},
           {"start": "12:30", "end": "21:50"}]
    assert free_slots(evs) == []


def test_context_contents(tmp_path):
    st = Store(tmp_path / "s.json")
    st.add_event("会議", "2026-10-27", "10:00", "11:00")
    st.add_event("歯医者", "2026-10-28", "09:00", "10:00")
    st.add_wish("英語", "high", 30, "2026-10-26")
    text = build_context(st, st, TODAY)
    assert "火曜日" in text and "10:00-11:00 会議" in text
    assert "09:00-10:00 歯医者" in text           # 明日の予定
    assert "1日超過" in text and "30分" in text


def test_plain_brief_needs_no_client(tmp_path):
    st = Store(tmp_path / "s.json")
    out = morning_brief(st, today=TODAY, plain=True)
    assert "今日の予定" in out and "- なし" in out


def test_ai_brief_uses_client(tmp_path):
    class Resp:
        content = [type("B", (), {"type": "text", "text": "おはよう"})()]

    class Msgs:
        def create(self, **kw):
            self.kw = kw
            return Resp()

    client = type("C", (), {"messages": Msgs()})()
    st = Store(tmp_path / "s.json")
    assert morning_brief(st, client=client, today=TODAY) == "おはよう"
    assert "今日の予定" in client.messages.kw["messages"][0]["content"]
