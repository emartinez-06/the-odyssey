"""Filters showtimes down to the ones that fall inside the user's free time."""

from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo

_WEEKDAY_NAMES = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]


def _parse_hhmm(value: str) -> time:
    hour, minute = value.split(":")
    return time(int(hour), int(minute))


def is_within_availability_window(
    showtime_local: datetime, windows: dict[str, list[list[str]]]
) -> bool:
    """Whether a timezone-aware, theater-local showtime start time falls
    inside one of the configured free-time windows for that day of week.

    An empty or missing list of windows for a day means "never notify for
    showtimes on that day".
    """
    day_name = _WEEKDAY_NAMES[showtime_local.weekday()]
    day_windows = windows.get(day_name, [])
    showtime_clock = showtime_local.time()
    for start_str, end_str in day_windows:
        start, end = _parse_hhmm(start_str), _parse_hhmm(end_str)
        if start <= showtime_clock <= end:
            return True
    return False


def to_theater_local(showtime_naive_iso: str, theater_timezone: str) -> datetime:
    """Attach the theater's own timezone to a Cinemark showtime timestamp.

    Cinemark's `Showtime` query param (e.g. "2026-08-18T11:30:00") is a
    naive timestamp already expressed in the theater's local time, with no
    UTC offset given - so we attach tzinfo directly rather than convert.
    """
    naive = datetime.fromisoformat(showtime_naive_iso)
    return naive.replace(tzinfo=ZoneInfo(theater_timezone))
