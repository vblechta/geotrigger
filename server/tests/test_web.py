from geotrigger import db
from geotrigger.models import Location
from geotrigger.services import get_map_api_key, get_ping_interval_seconds


def test_login_page(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert b"GeoTrigger" in response.data


def test_dashboard_requires_login(client):
    response = client.get("/")
    assert response.status_code in (302, 401)


def test_non_admin_cannot_open_locations(client, worker):
    client.post("/login", data={"username": "worker", "password": "secret12"})
    response = client.get("/locations")
    assert response.status_code == 403


def test_admin_creates_location_and_sets_interval(app, client):
    client.post("/login", data={"username": "admin", "password": "changeme"})
    response = client.post(
        "/locations/new",
        data={
            "name": "Warehouse",
            "latitude": "50.1",
            "longitude": "14.4",
            "radius_meters": "120",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        loc = Location.query.filter_by(name="Warehouse").one()
        assert loc.radius_meters == 120

    settings = client.post(
        "/settings",
        data={"ping_interval_seconds": "120", "map_api_key": "test-map-key"},
        follow_redirects=True,
    )
    assert settings.status_code == 200
    with app.app_context():
        assert get_ping_interval_seconds() == 120
        assert get_map_api_key() == "test-map-key"
    dashboard = client.get("/")
    assert b'data-map-key="test-map-key"' in dashboard.data


def test_admin_creates_user(client):
    client.post("/login", data={"username": "admin", "password": "changeme"})
    response = client.post(
        "/users",
        data={"username": "field1", "password": "hunter2", "is_admin": ""},
        follow_redirects=True,
    )
    assert response.status_code == 200
    login = client.post("/api/auth/login", json={"username": "field1", "password": "hunter2"})
    assert login.status_code == 200
