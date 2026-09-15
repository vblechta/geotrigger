from __future__ import annotations

import os
from collections import defaultdict
from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from geotrigger.models import PresenceSession, User
from geotrigger.services import session_duration_seconds


def public_user(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "is_admin": user.is_admin,
    }


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def utc_iso(value: datetime | None) -> str:
    if value is None:
        return ""
    return ensure_utc(value).isoformat()


def local_tz():
    name = (os.environ.get("TZ") or "").strip()
    if name:
        try:
            return ZoneInfo(name)
        except ZoneInfoNotFoundError:
            pass
    return datetime.now().astimezone().tzinfo or timezone.utc


def to_local(value: datetime) -> datetime:
    return ensure_utc(value).astimezone(local_tz())


def format_local(value: datetime | None) -> str:
    if value is None:
        return ""
    return to_local(value).strftime("%Y-%m-%d %H:%M")


def parse_iso_datetime(value: str) -> datetime:
    text = value.strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def parse_date_boundary(value: str | None, end: bool = False) -> datetime | None:
    if not value:
        return None
    try:
        day = datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None
    clock = time.max if end else time.min
    local = datetime.combine(day, clock, tzinfo=local_tz())
    return local.astimezone(timezone.utc)


def format_duration(seconds: int) -> str:
    seconds = max(0, int(seconds))
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}h {minutes:02d}m"
    if minutes:
        return f"{minutes}m {secs:02d}s"
    return f"{secs}s"


def summarize_sessions(sessions: list[PresenceSession]) -> list[dict]:
    totals: dict[int, dict] = defaultdict(lambda: {"seconds": 0, "visits": 0, "location": None})
    for session in sessions:
        bucket = totals[session.location_id]
        bucket["location"] = session.location
        bucket["seconds"] += session_duration_seconds(session)
        bucket["visits"] += 1
    rows = []
    for bucket in totals.values():
        loc = bucket["location"]
        rows.append(
            {
                "id": loc.id,
                "name": loc.name,
                "latitude": loc.latitude,
                "longitude": loc.longitude,
                "radius_meters": loc.radius_meters,
                "seconds": bucket["seconds"],
                "visits": bucket["visits"],
                "duration_label": format_duration(bucket["seconds"]),
            }
        )
    rows.sort(key=lambda item: item["seconds"], reverse=True)
    return rows
