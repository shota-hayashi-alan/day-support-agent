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
