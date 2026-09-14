from __future__ import annotations

from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from sqlalchemy import select

from geotrigger import db
from geotrigger.auth import api_login_required, current_bearer, issue_token, json_error, revoke_token
from geotrigger.models import Location, PresenceSession, User
from geotrigger.services import get_ping_interval_seconds, process_presence, session_duration_seconds
from geotrigger.util import parse_iso_datetime, public_user, summarize_sessions

api_bp = Blueprint("api", __name__)


@api_bp.get("/health")
def health():
    return jsonify({"status": "ok"})


@api_bp.post("/auth/login")
def login():
    payload = request.get_json(silent=True) or {}
    username = (payload.get("username") or "").strip()
    password = payload.get("password") or ""
    if not username or not password:
        return json_error("Username and password are required.")

    user = User.query.filter_by(username=username).first()
    if user is None or not user.check_password(password):
        return json_error("Invalid username or password.", 401)

    token = issue_token(user)
    return jsonify(
        {
            "token": token,
            "user": public_user(user),
            "ping_interval_seconds": get_ping_interval_seconds(),
        }
    )


@api_bp.post("/auth/logout")
@api_login_required
def logout(user: User):
    raw = current_bearer()
    if raw:
        revoke_token(raw)
    return jsonify({"ok": True})


@api_bp.get("/me")
@api_login_required
def me(user: User):
    return jsonify({"user": public_user(user), "ping_interval_seconds": get_ping_interval_seconds()})


@api_bp.get("/config")
@api_login_required
def config(user: User):
    locations = [loc.to_dict() for loc in Location.query.order_by(Location.name).all()]
    return jsonify(
        {
            "ping_interval_seconds": get_ping_interval_seconds(),
            "locations": locations,
        }
    )


@api_bp.get("/locations")
@api_login_required
def locations(user: User):
    return jsonify({"locations": [loc.to_dict() for loc in Location.query.order_by(Location.name).all()]})


@api_bp.post("/presence")
@api_login_required
def presence(user: User):
    payload = request.get_json(silent=True) or {}
    try:
        lat = float(payload["latitude"])
        lon = float(payload["longitude"])
    except (KeyError, TypeError, ValueError):
        return json_error("latitude and longitude are required numbers.")

    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return json_error("Coordinates are out of range.")

    accuracy = payload.get("accuracy_meters")
    try:
        accuracy_m = float(accuracy) if accuracy is not None else None
    except (TypeError, ValueError):
        return json_error("accuracy_meters must be a number.")

    recorded_at = None
    if payload.get("recorded_at"):
        try:
            recorded_at = parse_iso_datetime(payload["recorded_at"])
        except ValueError:
            return json_error("recorded_at must be an ISO-8601 timestamp.")

    matched = process_presence(
        user,
        lat,
        lon,
        recorded_at=recorded_at,
        accuracy_meters=accuracy_m,
    )
    return jsonify(
        {
            "matched_locations": [loc.to_dict() for loc in matched],
            "inside_location": bool(matched),
            "ping_interval_seconds": get_ping_interval_seconds(),
        }
    )


@api_bp.get("/summary")
@api_login_required
def summary(user: User):
    start, end, err = _parse_range()
    if err:
        return err
    sessions = _sessions_for(user.id, start, end)
    return jsonify(
        {
            "ping_interval_seconds": get_ping_interval_seconds(),
            "locations": summarize_sessions(sessions),
            "sessions": [_session_payload(s) for s in sessions],
        }
    )


def _parse_range():
    start = end = None
    try:
        if request.args.get("from"):
            start = parse_iso_datetime(request.args["from"])
        if request.args.get("to"):
            end = parse_iso_datetime(request.args["to"])
    except ValueError:
        return None, None, json_error("from/to must be ISO-8601 timestamps.")
    return start, end, None


def _sessions_for(user_id: int, start: datetime | None, end: datetime | None) -> list[PresenceSession]:
    query = select(PresenceSession).where(PresenceSession.user_id == user_id)
    if start is not None:
        query = query.where(PresenceSession.last_ping_at >= start)
    if end is not None:
        query = query.where(PresenceSession.started_at <= end)
    query = query.order_by(PresenceSession.started_at.desc())
    return list(db.session.scalars(query).all())


def _session_payload(session: PresenceSession) -> dict:
    return {
        "id": session.id,
        "location": session.location.to_dict(),
        "started_at": _iso(session.started_at),
        "last_ping_at": _iso(session.last_ping_at),
        "ended_at": _iso(session.ended_at) if session.ended_at else None,
        "open": session.ended_at is None,
        "duration_seconds": session_duration_seconds(session),
    }


def _iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()
