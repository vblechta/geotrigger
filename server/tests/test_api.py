from datetime import datetime, timedelta, timezone

from geotrigger import db
from geotrigger.models import Location, PresenceSession
from tests.conftest import auth_header


ORIGIN = datetime(2026, 1, 1, 8, 0, tzinfo=timezone.utc)


def _add_site(app, name="Depot", lat=50.087, lon=14.421, radius=80):
    with app.app_context():
        loc = Location(name=name, latitude=lat, longitude=lon, radius_meters=radius)
        db.session.add(loc)
        db.session.commit()
        return loc.id


def test_login_ok(client):
    response = client.post("/api/auth/login", json={"username": "admin", "password": "changeme"})
    assert response.status_code == 200
    body = response.get_json()
    assert body["token"]
    assert body["user"]["is_admin"] is True
    assert body["ping_interval_seconds"] == 300


def test_login_rejected(client):
    response = client.post("/api/auth/login", json={"username": "admin", "password": "nope"})
    assert response.status_code == 401


def test_config_requires_auth(client):
    assert client.get("/api/config").status_code == 401


def test_config_lists_locations(app, client):
    _add_site(app)
    headers = auth_header(client)
    body = client.get("/api/config", headers=headers).get_json()
    assert body["ping_interval_seconds"] == 300
    assert body["locations"][0]["name"] == "Depot"
    assert body["locations"][0]["radius_meters"] == 80


def test_presence_outside_does_not_open_session(app, client):
    _add_site(app)
    headers = auth_header(client)
    response = client.post(
        "/api/presence",
        json={"latitude": 51.0, "longitude": 14.0, "recorded_at": ORIGIN.isoformat()},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.get_json()["inside_location"] is False
    with app.app_context():
        assert PresenceSession.query.count() == 0


def test_presence_inside_opens_and_extends_session(app, client, worker):
    _add_site(app)
    headers = auth_header(client, "worker", "secret12")
    first = client.post(
        "/api/presence",
        json={"latitude": 50.087, "longitude": 14.421, "recorded_at": ORIGIN.isoformat()},
        headers=headers,
    )
    assert first.get_json()["inside_location"] is True

    later = ORIGIN + timedelta(seconds=300)
    client.post(
        "/api/presence",
        json={"latitude": 50.08705, "longitude": 14.421, "recorded_at": later.isoformat()},
        headers=headers,
    )
    summary = client.get("/api/summary", headers=headers).get_json()
    assert len(summary["sessions"]) == 1
    assert summary["sessions"][0]["duration_seconds"] == 600
    assert summary["locations"][0]["seconds"] == 600


def test_stale_gap_starts_new_session(app, client, worker):
    _add_site(app)
    headers = auth_header(client, "worker", "secret12")
    client.post(
        "/api/presence",
        json={"latitude": 50.087, "longitude": 14.421, "recorded_at": ORIGIN.isoformat()},
        headers=headers,
    )
    resume = ORIGIN + timedelta(seconds=901)
    client.post(
        "/api/presence",
        json={"latitude": 50.087, "longitude": 14.421, "recorded_at": resume.isoformat()},
        headers=headers,
    )
    summary = client.get("/api/summary", headers=headers).get_json()
    assert len(summary["sessions"]) == 2
