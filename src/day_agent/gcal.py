"""Googleカレンダー連携。Store と同じ予定インターフェースを提供する。"""
from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path

from .store import DATE_FMT, TIME_FMT, overlapping

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
TZ = os.environ.get("DAY_AGENT_TZ", "Asia/Tokyo")


def _to_event(item: dict) -> dict:
    """Google API のイベントを、ローカルの予定dictに変換する。"""
    s, e = item["start"], item["end"]
    if "dateTime" in s:
        sdt = datetime.fromisoformat(s["dateTime"])
        edt = datetime.fromisoformat(e["dateTime"])
        date, start = sdt.strftime(DATE_FMT), sdt.strftime(TIME_FMT)
        end = edt.strftime(TIME_FMT) if edt.date() == sdt.date() else "23:59"
        note = item.get("description", "")
    else:  # 終日イベント
        date, start, end = s["date"], "00:00", None
        note = ("終日 " + item.get("description", "")).strip()
    return {"id": item["id"], "title": item.get("summary", "(無題)"),
            "date": date, "start": start, "end": end, "note": note}


class GoogleCalendar:
    def __init__(self, service, calendar_id: str = "primary"):
        self.service = service
        self.calendar_id = calendar_id

    @classmethod
    def from_oauth(cls, credentials_file: str | None = None,
                   token_file: str | None = None) -> "GoogleCalendar":
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build

        cred_path = Path(credentials_file or os.environ.get(
            "GOOGLE_CREDENTIALS", "credentials.json"))
        tok_path = Path(token_file or os.environ.get(
            "GOOGLE_TOKEN", "data/token.json"))
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
        return cls(build("calendar", "v3", credentials=creds))

    def add_event(self, title: str, date: str, start: str, end: str | None = None,
                  note: str = "") -> dict:
        sdt = datetime.strptime(f"{date} {start}", f"{DATE_FMT} {TIME_FMT}")
        if end:
            edt = datetime.strptime(f"{date} {end}", f"{DATE_FMT} {TIME_FMT}")
            if edt <= sdt:
                raise ValueError("終了時刻は開始時刻より後にしてください")
        else:
            edt = sdt + timedelta(hours=1)
        body = {"summary": title, "description": note,
                "start": {"dateTime": sdt.isoformat(), "timeZone": TZ},
                "end": {"dateTime": edt.isoformat(), "timeZone": TZ}}
        item = self.service.events().insert(
            calendarId=self.calendar_id, body=body).execute()
        return _to_event(item)

    def list_events(self, date_from: str, date_to: str | None = None) -> list[dict]:
        date_to = date_to or date_from
        lo = datetime.strptime(date_from, DATE_FMT)
        hi = datetime.strptime(date_to, DATE_FMT) + timedelta(days=1)
        # timeMin/Max にはタイムゾーン付き(RFC3339)が必要。TZ名からオフセットを得る。
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(TZ)
        resp = self.service.events().list(
            calendarId=self.calendar_id,
            timeMin=lo.replace(tzinfo=tz).isoformat(),
            timeMax=hi.replace(tzinfo=tz).isoformat(),
            singleEvents=True, orderBy="startTime", maxResults=250).execute()
        evs = [_to_event(i) for i in resp.get("items", [])
               if i.get("status") != "cancelled"]
        return sorted(evs, key=lambda e: (e["date"], e["start"]))

    def delete_event(self, event_id) -> bool:
        from googleapiclient.errors import HttpError
        try:
            self.service.events().delete(
                calendarId=self.calendar_id, eventId=str(event_id)).execute()
            return True
        except HttpError as e:
            if e.resp.status in (404, 410):
                return False
            raise

    def find_conflicts(self, date: str, start: str, end: str | None) -> list[dict]:
        return overlapping(self.list_events(date), start, end)
