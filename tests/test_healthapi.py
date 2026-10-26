from datetime import date

import pytest

from day_agent.healthapi import HealthApiError, HealthClient


class Resp:
    def __init__(self, code, body):
        self.status_code, self._b, self.text = code, body, str(body)

    def json(self):
        return self._b


class FakeSession:
    def __init__(self, *resps):
        self.resps, self.calls = list(resps), []

    def get(self, url, params):
        self.calls.append((url, dict(params)))
        return self.resps.pop(0)


def test_pagination_and_filter():
    s = FakeSession(Resp(200, {"dataPoints": [{"a": 1}], "nextPageToken": "T"}),
                    Resp(200, {"dataPoints": [{"a": 2}]}))
    pts = HealthClient(s).list_exercises(date(2026, 10, 26), date(2026, 10, 27))
    assert pts == [{"a": 1}, {"a": 2}]
    url, p1 = s.calls[0]
    assert url == "https://health.googleapis.com/v4/users/me/dataTypes/exercise/dataPoints"
    assert p1["filter"] == ('exercise.interval.civil_start_time >= "2026-10-26" AND '
                            'exercise.interval.civil_start_time < "2026-10-28"')
    assert p1["pageSize"] == 25 and "pageToken" not in p1
    assert s.calls[1][1]["pageToken"] == "T"


def test_error_raises_with_body():
    with pytest.raises(HealthApiError, match="403"):
        HealthClient(FakeSession(Resp(403, {"error": "x"}))).list_exercises(
            date(2026, 10, 26), date(2026, 10, 26))


def test_empty_is_ok():
    assert HealthClient(FakeSession(Resp(200, {}))).list_exercises(
        date(2026, 10, 26), date(2026, 10, 26)) == []


# --- 実データ(Fitbit Air)の形に基づく変換テスト ---
from day_agent.healthapi import GoogleHealthSource, exercise_record  # noqa: E402
from day_agent.habits import HabitTracker  # noqa: E402
from day_agent.store import Store  # noqa: E402
from day_agent.sync import sync  # noqa: E402


def pt(pid, typ, start, end, active=None):
    ex = {"interval": {"startTime": start, "startUtcOffset": "32400s",
                       "endTime": end, "endUtcOffset": "32400s"},
          "exerciseType": typ}
    if active:
        ex["activeDuration"] = active
    return {"name": f"users/1/dataTypes/exercise/dataPoints/{pid}", "exercise": ex}


SWIM = pt("a", "SWIMMING", "2026-10-25T10:23:13.400Z", "2026-10-25T11:47:18.400Z", "5045s")
WALK = pt("b", "WALKING", "2026-10-25T05:50:24Z", "2026-10-25T06:05:24Z", "900s")
LATE = pt("c", "WORKOUT", "2026-10-17T23:40:34Z", "2026-10-17T23:55:37Z", "903s")
TINY = pt("d", "STRENGTH_TRAINING", "2026-10-25T01:00:00Z", "2026-10-25T01:05:00Z", "300s")
DEC = pt("e", "WALKING", "2026-10-17T08:39:24.800Z", "2026-10-17T09:06:20Z", "1615.200s")


def test_record_uses_active_duration_in_minutes():
    r = exercise_record(SWIM)
    assert (r["id"], r["date"], r["amount"], r["type"]) == ("a", "2026-10-25", 84.1, "SWIMMING")
    assert exercise_record(DEC)["amount"] == 26.9


def test_record_date_uses_local_offset_across_midnight():
    # UTC 23:40 は日本時間では翌日 08:40
    assert exercise_record(LATE)["date"] == "2026-10-18"


def test_record_falls_back_to_interval_length():
    r = exercise_record(pt("f", "YOGA", "2026-10-25T00:00:00Z", "2026-10-25T00:30:00Z"))
    assert r["amount"] == 30.0


class Client:
    def __init__(self, pts):
        self.pts, self.range = pts, None

    def list_exercises(self, start, end):
        self.range = (start, end)
        return self.pts


def test_source_filters_short_and_excluded():
    c = Client([SWIM, WALK, TINY, LATE])
    src = GoogleHealthSource(c, days=14, exclude_types={"walking"}, today=date(2026, 10, 26))
    assert [r["id"] for r in src.records()] == ["a", "c"]  # 5分の筋トレと散歩は除外
    assert c.range == (date(2026, 10, 13), date(2026, 10, 26))


def test_end_to_end_sync_is_idempotent(tmp_path):
    ht = HabitTracker(Store(tmp_path / "s.json"))
    ht.create("運動", "min", 150)
    src = GoogleHealthSource(Client([SWIM, WALK]), today=date(2026, 10, 26))
    assert sync(ht, src)["added"] == 2
    assert sync(ht, src) == {"added": 0, "duplicate": 2, "errors": []}
    assert ht.progress("運動", date(2026, 10, 25))["this_week"] == 99.1  # 日曜時点の週: 84.1 + 15
