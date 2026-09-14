from __future__ import annotations

from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import select

from geotrigger import db
from geotrigger.forms import LocationForm, LoginForm, PasswordResetForm, SettingsForm, UserForm
from geotrigger.models import Location, PresenceSession, User
from geotrigger.services import (
    get_map_api_key,
    get_ping_interval_seconds,
    session_duration_seconds,
    set_map_api_key,
    set_ping_interval_seconds,
)
from geotrigger.util import format_duration, parse_date_boundary, summarize_sessions

web_bp = Blueprint("web", __name__)


def admin_required(fn):
    from functools import wraps

    @wraps(fn)
    @login_required
    def wrapper(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return fn(*args, **kwargs)

    return wrapper


@web_bp.app_context_processor
def inject_globals():
    return {
        "ping_interval_seconds": get_ping_interval_seconds,
        "map_api_key": get_map_api_key(),
    }


@web_bp.app_errorhandler(403)
def forbidden(_e):
    return render_template("error.html", code=403, message="You need administrator access for this page."), 403


@web_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("web.dashboard"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data.strip()).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            return redirect(request.args.get("next") or url_for("web.dashboard"))
        flash("Invalid username or password.", "error")
    return render_template("login.html", form=form)


@web_bp.post("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("web.login"))


@web_bp.get("/")
@login_required
def dashboard():
    sessions = db.session.scalars(
        select(PresenceSession)
        .where(PresenceSession.user_id == current_user.id)
        .order_by(PresenceSession.started_at.desc())
        .limit(50)
    ).all()
    locations = db.session.scalars(select(Location).order_by(Location.name)).all()
    summary = summarize_sessions(
        db.session.scalars(select(PresenceSession).where(PresenceSession.user_id == current_user.id)).all()
    )
    return render_template(
        "dashboard.html",
        sessions=sessions,
        locations=locations,
        location_payloads=[loc.to_dict() for loc in locations],
        summary=summary,
        format_duration=format_duration,
        duration_seconds=session_duration_seconds,
    )


@web_bp.route("/locations", methods=["GET"])
@admin_required
def locations():
    items = db.session.scalars(select(Location).order_by(Location.name)).all()
    return render_template(
        "locations.html",
        locations=items,
        location_payloads=[loc.to_dict() for loc in items],
    )


@web_bp.route("/locations/new", methods=["GET", "POST"])
@admin_required
def location_new():
    form = LocationForm()
    if form.validate_on_submit():
        if Location.query.filter_by(name=form.name.data.strip()).first():
            flash("A location with that name already exists.", "error")
        else:
            db.session.add(
                Location(
                    name=form.name.data.strip(),
                    latitude=form.latitude.data,
                    longitude=form.longitude.data,
                    radius_meters=form.radius_meters.data,
                )
            )
            db.session.commit()
            flash("Location created.", "ok")
            return redirect(url_for("web.locations"))
    return render_template("location_form.html", form=form, title="New location")


@web_bp.route("/locations/<int:location_id>/edit", methods=["GET", "POST"])
@admin_required
def location_edit(location_id: int):
    location = db.session.get(Location, location_id) or abort(404)
    form = LocationForm(obj=location)
    if form.validate_on_submit():
        clash = Location.query.filter(Location.name == form.name.data.strip(), Location.id != location.id).first()
        if clash:
            flash("A location with that name already exists.", "error")
        else:
            location.name = form.name.data.strip()
            location.latitude = form.latitude.data
            location.longitude = form.longitude.data
            location.radius_meters = form.radius_meters.data
            db.session.commit()
            flash("Location updated.", "ok")
            return redirect(url_for("web.locations"))
    return render_template("location_form.html", form=form, title=f"Edit {location.name}", location=location)


@web_bp.post("/locations/<int:location_id>/delete")
@admin_required
def location_delete(location_id: int):
    location = db.session.get(Location, location_id) or abort(404)
    db.session.delete(location)
    db.session.commit()
    flash("Location deleted.", "ok")
    return redirect(url_for("web.locations"))


@web_bp.route("/users", methods=["GET", "POST"])
@admin_required
def users():
    form = UserForm()
    reset_form = PasswordResetForm()
    if form.validate_on_submit():
        if User.query.filter_by(username=form.username.data.strip()).first():
            flash("That username is taken.", "error")
        else:
            user = User(username=form.username.data.strip(), is_admin=bool(form.is_admin.data))
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            flash("User created.", "ok")
            return redirect(url_for("web.users"))
    people = db.session.scalars(select(User).order_by(User.username)).all()
    return render_template("users.html", form=form, reset_form=reset_form, users=people)


@web_bp.post("/users/<int:user_id>/password")
@admin_required
def user_password(user_id: int):
    user = db.session.get(User, user_id) or abort(404)
    form = PasswordResetForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash(f"Password updated for {user.username}.", "ok")
    else:
        flash("Password must be at least 6 characters.", "error")
    return redirect(url_for("web.users"))


@web_bp.post("/users/<int:user_id>/delete")
@admin_required
def user_delete(user_id: int):
    user = db.session.get(User, user_id) or abort(404)
    if user.id == current_user.id:
        flash("You cannot delete your own account.", "error")
        return redirect(url_for("web.users"))
    admin_count = User.query.filter_by(is_admin=True).count()
    if user.is_admin and admin_count <= 1:
        flash("Cannot delete the last administrator.", "error")
        return redirect(url_for("web.users"))
    db.session.delete(user)
    db.session.commit()
    flash("User deleted.", "ok")
    return redirect(url_for("web.users"))


@web_bp.route("/settings", methods=["GET", "POST"])
@admin_required
def settings():
    form = SettingsForm()
    if request.method == "GET":
        form.ping_interval_seconds.data = get_ping_interval_seconds()
        form.map_api_key.data = get_map_api_key()
    if form.validate_on_submit():
        set_ping_interval_seconds(form.ping_interval_seconds.data)
        set_map_api_key(form.map_api_key.data or "")
        flash("Settings saved. Android clients pick up a new ping interval on the next config refresh.", "ok")
        return redirect(url_for("web.settings"))
    return render_template("settings.html", form=form, interval=get_ping_interval_seconds())


@web_bp.route("/reports", methods=["GET"])
@admin_required
def reports():
    start = parse_date_boundary(request.args.get("from"), end=False)
    end = parse_date_boundary(request.args.get("to"), end=True)
    query = select(PresenceSession)
    if start:
        query = query.where(PresenceSession.last_ping_at >= start)
    if end:
        query = query.where(PresenceSession.started_at <= end)
    sessions = db.session.scalars(query.order_by(PresenceSession.started_at.desc())).all()

    by_user: dict[int, dict] = {}
    for session in sessions:
        bucket = by_user.setdefault(
            session.user_id,
            {"user": session.user, "seconds": 0, "locations": {}},
        )
        seconds = session_duration_seconds(session)
        bucket["seconds"] += seconds
        loc_bucket = bucket["locations"].setdefault(
            session.location_id,
            {"location": session.location, "seconds": 0},
        )
        loc_bucket["seconds"] += seconds

    rows = sorted(by_user.values(), key=lambda item: item["user"].username)
    return render_template(
        "reports.html",
        rows=rows,
        sessions=sessions[:100],
        format_duration=format_duration,
        duration_seconds=session_duration_seconds,
        from_date=request.args.get("from", ""),
        to_date=request.args.get("to", ""),
    )
