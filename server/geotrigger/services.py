from __future__ import annotations

from datetime import datetime, timedelta, timezone

from flask import current_app
from sqlalchemy import select

from geotrigger import db, utcnow
from geotrigger.geo import is_inside
from geotrigger.models import AppSetting, Location, PresencePing, PresenceSession, User


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)

PING_INTERVAL_KEY = "ping_interval_seconds"
MAP_API_KEY = "map_api_key"


def _get_setting(key: str, default: str = "") -> str:
    row = db.session.get(AppSetting, key)
    if row is None:
        return default
    return row.value


def _set_setting(key: str, value: str) -> None:
    row = db.session.get(AppSetting, key)
    if row is None:
        db.session.add(AppSetting(key=key, value=value))
    else:
        row.value = value
    db.session.commit()


def get_ping_interval_seconds() -> int:
    raw = _get_setting(PING_INTERVAL_KEY, "")
    if not raw:
        return int(current_app.config["DEFAULT_PING_INTERVAL_SECONDS"])
    return int(raw)


def set_ping_interval_seconds(seconds: int) -> None:
    minimum = int(current_app.config["MIN_PING_INTERVAL_SECONDS"])
    maximum = int(current_app.config["MAX_PING_INTERVAL_SECONDS"])
    _set_setting(PING_INTERVAL_KEY, str(max(minimum, min(maximum, int(seconds)))))


def get_map_api_key() -> str:
    return _get_setting(MAP_API_KEY, "").strip()


def set_map_api_key(key: str) -> None:
    _set_setting(MAP_API_KEY, (key or "").strip())


def matching_locations(lat: float, lon: float) -> list[Location]:
    locations = db.session.scalars(select(Location)).all()
    return [loc for loc in locations if is_inside(lat, lon, loc.latitude, loc.longitude, loc.radius_meters)]


def process_presence(
    user: User,
    lat: float,
    lon: float,
    recorded_at: datetime | None = None,
    accuracy_meters: float | None = None,
) -> list[Location]:
    """Record a heartbeat. Opens, extends, or closes presence sessions."""
    recorded_at = _aware(recorded_at or utcnow())
    interval = get_ping_interval_seconds()
    matched = matching_locations(lat, lon)
    matched_ids = {loc.id for loc in matched}
    stale_before = recorded_at - timedelta(seconds=interval * 2)

    open_sessions = db.session.scalars(
        select(PresenceSession).where(
            PresenceSession.user_id == user.id,
            PresenceSession.ended_at.is_(None),
        )
    ).all()

    still_open_ids: set[int] = set()
    for session in open_sessions:
        in_this_location = session.location_id in matched_ids
        recently_seen = _aware(session.last_ping_at) >= stale_before
        if in_this_location and recently_seen:
            session.last_ping_at = max(_aware(session.last_ping_at), recorded_at)
            still_open_ids.add(session.location_id)
        else:
            session.ended_at = session.last_ping_at

    for loc in matched:
        if loc.id in still_open_ids:
            continue
        db.session.add(
            PresenceSession(
                user_id=user.id,
                location_id=loc.id,
                started_at=recorded_at,
                last_ping_at=recorded_at,
                interval_seconds=interval,
            )
        )

    for loc in matched:
        db.session.add(
            PresencePing(
                user_id=user.id,
                location_id=loc.id,
                latitude=lat,
                longitude=lon,
                accuracy_meters=accuracy_meters,
                recorded_at=recorded_at,
            )
        )

    db.session.commit()
    return matched


def session_duration_seconds(session: PresenceSession) -> int:
    elapsed = (_aware(session.last_ping_at) - _aware(session.started_at)).total_seconds()
    return max(session.interval_seconds, int(elapsed) + session.interval_seconds)
