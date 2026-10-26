"""Google Health API (v4) クライアント。読み取り専用。"""
from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from pathlib import Path

BASE = "https://health.googleapis.com/v4"
SCOPES = ["https://www.googleapis.com/auth/googlehealth.activity_and_fitness.readonly"]
# exercise は1ページ最大25件(公式仕様)
EXERCISE_PAGE_SIZE = 25


class HealthApiError(RuntimeError):
    pass


def authorized_session(credentials_file: str | None = None,
                       token_file: str | None = None):
    """OAuth(ブラウザ認可)済みの requests セッションを返す。トークンは初回のみ作成。"""
    from google.auth.transport.requests import AuthorizedSession, Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    cred_path = Path(credentials_file or os.environ.get(
        "GOOGLE_CREDENTIALS", "credentials.json"))
    tok_path = Path(token_file or os.environ.get(
        "GOOGLE_HEALTH_TOKEN", "data/health_token.json"))
    creds = None
    if tok_path.exists():
        creds = Credentials.from_authorized_user_file(str(tok_path), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            creds = InstalledAppFlow.from_client_secrets_file(
                str(cred_path), SCOPES).run_local_server(port=0)
        tok_path.parent.mkdir(parents=True, exist_ok=True)
        tok_path.write_text(creds.to_json())
        tok_path.chmod(0o600)
    return AuthorizedSession(creds)


class HealthClient:
    def __init__(self, session):
        self.session = session

    def list_exercises(self, start: date, end: date) -> list[dict]:
        """start〜end(両端含む)に開始した運動の生データ点を、全ページ分返す。"""
        flt = (f'exercise.interval.civil_start_time >= "{start.isoformat()}" AND '
               f'exercise.interval.civil_start_time < "{(end + timedelta(days=1)).isoformat()}"')
        return self._list("exercise", flt, EXERCISE_PAGE_SIZE)

    def _list(self, data_type: str, flt: str, page_size: int) -> list[dict]:
        url = f"{BASE}/users/me/dataTypes/{data_type}/dataPoints"
        params = {"filter": flt, "pageSize": page_size}
        points: list[dict] = []
        while True:
            resp = self.session.get(url, params=params)
            if resp.status_code != 200:
                raise HealthApiError(f"{resp.status_code}: {resp.text[:500]}")
            body = resp.json()
            points += body.get("dataPoints", [])
            token = body.get("nextPageToken")
            if not token:
                return points
            params = {**params, "pageToken": token}


EXERCISE_HABIT = "運動"


def _seconds(value: str | None) -> float:
    """'4231s' / '1615.200s' のような Duration 文字列を秒に変換する。"""
    return float(value.rstrip("s")) if value else 0.0


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def exercise_record(point: dict) -> dict:
    """運動の生データ点を、習慣の取り込み用レコードに変換する。

    date: 開始時刻を端末のUTCオフセットで現地日付に直したもの。
    amount: 実際に動いていた時間(activeDuration)を分で。無ければ区間の長さ。
    """
    ex = point["exercise"]
    iv = ex["interval"]
    start = _parse_time(iv["startTime"])
    local = start + timedelta(seconds=_seconds(iv.get("startUtcOffset")))
    seconds = _seconds(ex.get("activeDuration"))
    if not seconds:
        seconds = (_parse_time(iv["endTime"]) - start).total_seconds()
    return {"id": point["name"].rsplit("/", 1)[-1],
            "date": local.date().isoformat(),
            "habit": EXERCISE_HABIT,
            "amount": round(seconds / 60, 1),
            "type": ex.get("exerciseType", "")}


class GoogleHealthSource:
    """直近 days 日の運動を、「運動」習慣の記録として供給する Source。"""

    name = "google_health"

    def __init__(self, client: HealthClient, days: int = 14,
                 exclude_types: set[str] | None = None, min_minutes: float = 10,
                 today: date | None = None):
        self.client, self.days = client, days
        self.exclude_types = {t.upper() for t in (exclude_types or set())}
        self.min_minutes = min_minutes
        self.today = today or date.today()

    def records(self) -> list[dict]:
        points = self.client.list_exercises(
            self.today - timedelta(days=self.days - 1), self.today)
        out = []
        for p in points:
            r = exercise_record(p)
            if r["type"].upper() in self.exclude_types or r["amount"] < self.min_minutes:
                continue
            out.append({k: r[k] for k in ("id", "date", "habit", "amount")})
        return out
