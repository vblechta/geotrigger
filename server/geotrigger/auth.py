from __future__ import annotations

import hashlib
import secrets
from functools import wraps

from flask import Response, jsonify, request
from sqlalchemy import select

from geotrigger import db, utcnow
from geotrigger.models import ApiToken, User


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def issue_token(user: User) -> str:
    raw = secrets.token_urlsafe(32)
    db.session.add(ApiToken(user_id=user.id, token_hash=hash_token(raw)))
    db.session.commit()
    return raw


def revoke_token(raw: str) -> None:
    token = db.session.scalars(select(ApiToken).where(ApiToken.token_hash == hash_token(raw))).first()
    if token is not None:
        db.session.delete(token)
        db.session.commit()


def user_from_request() -> User | None:
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    raw = header.removeprefix("Bearer ").strip()
    if not raw:
        return None
    token = db.session.scalars(select(ApiToken).where(ApiToken.token_hash == hash_token(raw))).first()
    if token is None:
        return None
    token.last_used_at = utcnow()
    db.session.commit()
    return token.user


def current_bearer() -> str | None:
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    raw = header.removeprefix("Bearer ").strip()
    return raw or None


def api_login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = user_from_request()
        if user is None:
            return jsonify({"error": "Authentication required."}), 401
        return fn(user, *args, **kwargs)

    return wrapper


def json_error(message: str, status: int = 400) -> tuple[Response, int]:
    return jsonify({"error": message}), status
