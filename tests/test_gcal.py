from datetime import timedelta

from day_agent.gcal import GoogleCalendar, _to_event


class FakeEvents:
    def __init__(self):
        self.items, self.last_list, self.n = [], None, 0

    def insert(self, calendarId, body):
        self.n += 1
        item = {"id": f"g{self.n}", **body}
        self.items.append(item)
        return type("R", (), {"execute": lambda s: item})()

    def list(self, **kw):
        self.last_list = kw
        return type("R", (), {"execute": lambda s: {"items": self.items}})()


class FakeService:
    def __init__(self):
        self.ev = FakeEvents()

    def events(self):
        return self.ev


def test_add_and_list_roundtrip():
    svc = FakeService()
    cal = GoogleCalendar(svc)
    ev = cal.add_event("歯医者", "2026-10-27", "10:00", "11:00")
    assert (ev["date"], ev["start"], ev["end"]) == ("2026-10-27", "10:00", "11:00")
    assert cal.list_events("2026-10-27")[0]["title"] == "歯医者"
    assert svc.ev.last_list["timeMin"].startswith("2026-10-27T00:00:00+09:00")


def test_default_one_hour_and_conflict():
    cal = GoogleCalendar(FakeService())
    cal.add_event("会議", "2026-10-27", "10:00")  # 終了省略 → 11:00
    assert len(cal.find_conflicts("2026-10-27", "10:30", "11:30")) == 1
    assert cal.find_conflicts("2026-10-27", "11:00", "12:00") == []


def test_all_day_event():
    ev = _to_event({"id": "x", "summary": "祝日",
                    "start": {"date": "2026-11-03"}, "end": {"date": "2026-11-04"}})
    assert ev["start"] == "00:00" and "終日" in ev["note"]
