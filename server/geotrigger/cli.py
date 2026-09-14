from __future__ import annotations

import click
from flask import Flask
from sqlalchemy import select

from geotrigger import db
from geotrigger.models import User
from geotrigger.services import set_ping_interval_seconds


def register_cli(app: Flask) -> None:
    @app.cli.command("create-user")
    @click.option("--username", prompt=True)
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
    @click.option("--admin", is_flag=True, default=False)
    def create_user(username: str, password: str, admin: bool) -> None:
        if db.session.scalars(select(User).where(User.username == username)).first():
            raise click.ClickException(f"User {username!r} already exists.")
        user = User(username=username.strip(), is_admin=admin)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f"Created {'admin' if admin else 'user'} {username!r}.")

    @app.cli.command("set-interval")
    @click.argument("seconds", type=int)
    def set_interval(seconds: int) -> None:
        set_ping_interval_seconds(seconds)
        click.echo(f"Ping interval set to {seconds} seconds.")
