from datetime import datetime
from zoneinfo import ZoneInfo

from odyssey_watch.schedule import is_within_availability_window, to_theater_local

CHICAGO = ZoneInfo("America/Chicago")


def _dt(iso: str) -> datetime:
    return datetime.fromisoformat(iso).replace(tzinfo=CHICAGO)


def test_saturday_full_day_window_matches_any_time():
    windows = {"saturday": [["00:00", "23:59"]]}
    saturday_early = _dt("2026-08-15T07:45:00")
    saturday_late = _dt("2026-08-15T22:45:00")

    assert is_within_availability_window(saturday_early, windows)
    assert is_within_availability_window(saturday_late, windows)


def test_empty_day_window_never_matches():
    windows = {"monday": []}
    monday_230am = _dt("2026-08-17T02:30:00")

    assert not is_within_availability_window(monday_230am, windows)


def test_missing_day_key_never_matches():
    windows = {"friday": [["00:00", "23:59"]]}
    monday = _dt("2026-08-17T12:00:00")

    assert not is_within_availability_window(monday, windows)


def test_partial_day_window_respects_boundaries():
    windows = {"tuesday": [["17:00", "23:59"]]}
    before_window = _dt("2026-08-18T11:30:00")
    inside_window = _dt("2026-08-18T19:00:00")

    assert not is_within_availability_window(before_window, windows)
    assert is_within_availability_window(inside_window, windows)


def test_to_theater_local_attaches_theater_timezone():
    result = to_theater_local("2026-08-18T11:30:00", "America/Chicago")

    assert result == datetime(2026, 8, 18, 11, 30, tzinfo=CHICAGO)
    assert result.tzinfo is not None
