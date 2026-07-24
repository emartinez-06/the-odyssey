from datetime import datetime, timedelta
from pathlib import Path

from odyssey_watch.discover import _prune_past, _target_weekdays, parse_showtimes_for_movie
from odyssey_watch.config import Config, Movie, PrimeSeats, Theater

FIXTURE = Path(__file__).parent / "fixtures" / "theater_day_sample.html"


def _make_config(availability_windows: dict) -> Config:
    return Config(
        theater=Theater(id=207, name="Test Theater", timezone="America/Chicago", detail_path="tx-dallas/x"),
        movie=Movie(id=104867, name="The Odyssey (IMAX 70mm)"),
        showtimes=[],
        prime_seats=PrimeSeats(rows=["E"], seat_number_range=(1, 26)),
        availability_windows=availability_windows,
        discovery_lookahead_days=32,
    )


def test_parse_showtimes_for_movie_filters_by_movie_id():
    html = FIXTURE.read_text()
    found = parse_showtimes_for_movie(html, movie_id=104867)

    assert found == {
        "640213": "2026-08-18T11:30:00",
        "640214": "2026-08-18T15:15:00",
    }


def test_parse_showtimes_for_movie_ignores_other_movies():
    html = FIXTURE.read_text()
    found = parse_showtimes_for_movie(html, movie_id=108919)

    assert found == {"633584": "2026-08-18T12:30:00"}


def test_target_weekdays_only_includes_days_with_windows():
    config = _make_config(
        {
            "monday": [],
            "friday": [["15:00", "19:30"]],
            "saturday": [["11:00", "20:00"]],
            "sunday": [],
        }
    )

    assert _target_weekdays(config) == {4, 5}  # Friday=4, Saturday=5


def test_target_weekdays_empty_when_no_windows_configured():
    config = _make_config({})

    assert _target_weekdays(config) == set()


def test_prune_past_drops_showtimes_before_now():
    past = (datetime.now() - timedelta(days=1)).isoformat()
    future = (datetime.now() + timedelta(days=1)).isoformat()

    result = _prune_past({"1": past, "2": future})

    assert result == {"2": future}
