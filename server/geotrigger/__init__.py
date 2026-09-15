from __future__ import annotations

import fcntl
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from werkzeug.middleware.proxy_fix import ProxyFix

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(
        __name__,
        instance_relative_config=True,
        template_folder="templates",
        static_folder="static",
    )
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    os.makedirs(app.instance_path, exist_ok=True)

    from geotrigger.config import configure_app

    configure_app(app, test_config)

    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "web.login"
    login_manager.login_message = "Sign in to continue."

    from geotrigger import models  # noqa: F401
    from geotrigger.models import User

    @login_manager.user_loader
    def load_user(user_id: str) -> User | None:
        return db.session.get(User, int(user_id))

    from geotrigger.api import api_bp
    from geotrigger.web import web_bp

    csrf.exempt(api_bp)
    app.register_blueprint(web_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    from geotrigger.util import format_local, utc_iso

    app.jinja_env.filters["local_time"] = format_local
    app.jinja_env.filters["utc_iso"] = utc_iso

    with app.app_context():
        _init_database(app)

    from geotrigger.cli import register_cli

    register_cli(app)

    return app


@contextmanager
def _instance_lock(app: Flask):
    """Serialize schema init across gunicorn workers sharing one SQLite file."""
    lock_path = Path(app.instance_path) / ".init.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_path, "a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _init_database(app: Flask) -> None:
    with _instance_lock(app):
        try:
            db.create_all()
        except OperationalError as exc:
            if "already exists" not in str(exc).lower():
                raise
            db.session.rollback()
        _bootstrap_admin(app)


def _bootstrap_admin(app: Flask) -> None:
    from geotrigger.models import User

    if db.session.scalars(select(User).limit(1)).first() is not None:
        return

    if app.config.get("TESTING"):
        username, password = "admin", "changeme"
    else:
        username = os.environ.get("ADMIN_USERNAME", "admin").strip() or "admin"
        password = os.environ.get("ADMIN_PASSWORD", "changeme")
    admin = User(username=username, is_admin=True)
    admin.set_password(password)
    db.session.add(admin)
    db.session.commit()
    app.logger.warning(
        "Created initial admin user %r. Change the password before exposing the server.",
        username,
    )
