from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import BooleanField, FloatField, IntegerField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, Optional


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(max=80)])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Sign in")


class LocationForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=120)])
    latitude = FloatField("Latitude", validators=[DataRequired(), NumberRange(min=-90, max=90)])
    longitude = FloatField("Longitude", validators=[DataRequired(), NumberRange(min=-180, max=180)])
    radius_meters = IntegerField(
        "Radius (meters)",
        validators=[DataRequired(), NumberRange(min=1, max=50_000)],
        default=100,
    )
    submit = SubmitField("Save location")


class UserForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(min=2, max=80)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6, max=128)])
    is_admin = BooleanField("Administrator")
    submit = SubmitField("Create user")


class PasswordResetForm(FlaskForm):
    password = PasswordField("New password", validators=[DataRequired(), Length(min=6, max=128)])
    submit = SubmitField("Update password")


class SettingsForm(FlaskForm):
    ping_interval_seconds = IntegerField(
        "Ping interval (seconds)",
        validators=[DataRequired(), NumberRange(min=30, max=3600)],
        default=300,
    )
    map_api_key = StringField("Map tile API key", validators=[Optional(), Length(max=512)])
    submit = SubmitField("Save settings")


class ReportFilterForm(FlaskForm):
    from_date = StringField("From", validators=[Optional()])
    to_date = StringField("To", validators=[Optional()])
    submit = SubmitField("Filter")
