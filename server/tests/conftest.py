from __future__ import annotations

import pytest

from geotrigger import create_app, db
from geotrigger.models import User


@pytest.fixture
def app():
    application = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite://",
            "SECRET_KEY": "test-secret",
            "WTF_CSRF_ENABLED": False,
        }
    )
    yield application
    with application.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def worker(app):
    with app.app_context():
        user = User(username="worker", is_admin=False)
        user.set_password("secret12")
        db.session.add(user)
        db.session.commit()
        return user.id


def auth_header(client, username="admin", password="changeme") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    token = response.get_json()["token"]
    return {"Authorization": f"Bearer {token}"}
