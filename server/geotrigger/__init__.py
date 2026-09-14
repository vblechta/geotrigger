from __future__ import annotations

import os
from datetime import datetime, timezone

from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import select
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

    with app.app_context():
        db.create_all()
        _bootstrap_admin(app)

    from geotrigger.cli import register_cli

    register_cli(app)

    return app


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
