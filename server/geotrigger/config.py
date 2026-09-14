from __future__ import annotations

import os
import secrets
from pathlib import Path

from flask import Flask
from dotenv import load_dotenv


def configure_app(app: Flask, test_config: dict | None = None) -> None:
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    load_dotenv()

    secret_path = Path(app.instance_path) / "secret_key"
    if os.environ.get("SECRET_KEY"):
        secret_key = os.environ["SECRET_KEY"]
    elif secret_path.exists():
        secret_key = secret_path.read_text(encoding="utf-8").strip()
    else:
        secret_key = secrets.token_hex(32)
        secret_path.write_text(secret_key, encoding="utf-8")

    db_url = os.environ.get("DATABASE_URL", "sqlite:///geotrigger.db")
    if db_url.startswith("sqlite:///") and not db_url.startswith("sqlite:////"):
        # Store SQLite files in the instance folder unless an absolute path is given.
        relative = db_url.removeprefix("sqlite:///")
        if not os.path.isabs(relative):
            db_url = "sqlite:///" + str(Path(app.instance_path) / relative)

    app.config.from_mapping(
        SECRET_KEY=secret_key,
        SQLALCHEMY_DATABASE_URI=db_url,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        WTF_CSRF_TIME_LIMIT=None,
        DEFAULT_PING_INTERVAL_SECONDS=300,
        MIN_PING_INTERVAL_SECONDS=30,
        MAX_PING_INTERVAL_SECONDS=3600,
    )

    if test_config:
        app.config.update(test_config)
