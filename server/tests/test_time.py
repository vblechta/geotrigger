from datetime import datetime, timezone

from geotrigger.util import format_local, parse_date_boundary, utc_iso


def test_format_local_prague_winter(monkeypatch):
    monkeypatch.setenv("TZ", "Europe/Prague")
    value = datetime(2026, 1, 15, 23, 0, tzinfo=timezone.utc)
    assert format_local(value) == "2026-01-16 00:00"


def test_utc_iso_marks_naive_as_utc():
    value = datetime(2026, 1, 15, 12, 0)
    assert utc_iso(value).startswith("2026-01-15T12:00:00")
    assert utc_iso(value).endswith("+00:00") or utc_iso(value).endswith("Z")


def test_parse_date_boundary_uses_local_day(monkeypatch):
    monkeypatch.setenv("TZ", "Europe/Prague")
    start = parse_date_boundary("2026-07-01", end=False)
    assert start == datetime(2026, 6, 30, 22, 0, tzinfo=timezone.utc)
