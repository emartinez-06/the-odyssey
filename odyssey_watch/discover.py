"""Discovers newly-published Odyssey showtimes at the configured theater.

Cinemark's movie-listing pages (`/movies/...`) sit behind DataDome and only
show a theater's showtimes once a client-side geolocation/ZIP-search flow
has run - not reliable for a plain HTTP client. The theater's own detail
page (`/theatres/<slug>?showDate=YYYY-MM-DD`), by contrast, is pinned to a
specific theater by its URL slug rather than the requester's location, and
responds to a bare GET with no challenge. This walks a lookahead window of
dates - limited to the days of the week that actually have an availability
window configured, since there's no reason to discover showtimes you'd
never be notified about - and records every showtime found for the movie.
"""

from __future__ import annotations

import json
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import requests
from bs4 import BeautifulSoup

from odyssey_watch.config import Config, load_config

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = REPO_ROOT / "config" / "config.yaml"
DEFAULT_DISCOVERED_PATH = REPO_ROOT / "state" / "discovered_showtimes.json"

_THEATER_URL = "https://www.cinemark.com/theatres/{detail_path}"
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
_TIMEOUT_SECONDS = 20
_DELAY_BETWEEN_FETCHES_SECONDS = 0.5

_WEEKDAY_NAMES = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]


def _target_weekdays(config: Config) -> set[int]:
    return {
        i
        for i, name in enumerate(_WEEKDAY_NAMES)
        if config.availability_windows.get(name)
    }


def fetch_theater_day_html(detail_path: str, day: date) -> str:
    url = _THEATER_URL.format(detail_path=detail_path)
    headers = {"User-Agent": _USER_AGENT}
    response = requests.get(
        url, params={"showDate": day.isoformat()}, headers=headers, timeout=_TIMEOUT_SECONDS
    )
    response.raise_for_status()
    return response.text


def parse_showtimes_for_movie(html: str, movie_id: int) -> dict[str, str]:
    """Returns {showtime_id: datetime_iso} for every showtime of movie_id found."""
    soup = BeautifulSoup(html, "html.parser")
    found: dict[str, str] = {}
    for link in soup.find_all("a", href=True):
        if "TicketSeatMap" not in link["href"]:
            continue
        query = parse_qs(urlparse(link["href"]).query)
        showtime_ids = query.get("ShowtimeId")
        movie_ids = query.get("CinemarkMovieId")
        showtimes = query.get("Showtime")
        if not (showtime_ids and movie_ids and showtimes):
            continue
        if int(movie_ids[0]) != movie_id:
            continue
        found[showtime_ids[0]] = showtimes[0]
    return found


def discover(config: Config, lookahead_days: int) -> dict[str, str]:
    weekdays = _target_weekdays(config)
    if not weekdays:
        print("No days have an availability window configured; nothing to discover.")
        return {}

    discovered: dict[str, str] = {}
    today = date.today()
    for offset in range(lookahead_days):
        day = today + timedelta(days=offset)
        if day.weekday() not in weekdays:
            continue
        try:
            html = fetch_theater_day_html(config.theater.detail_path, day)
        except requests.exceptions.RequestException as exc:
            print(f"warning: failed to fetch {day.isoformat()}: {exc}", file=sys.stderr)
            continue
        finally:
            time.sleep(_DELAY_BETWEEN_FETCHES_SECONDS)
        found = parse_showtimes_for_movie(html, config.movie.id)
        if found:
            print(f"{day.isoformat()} ({day.strftime('%A')}): {len(found)} showtime(s)")
        discovered.update(found)
    return discovered


def _prune_past(showtimes: dict[str, str]) -> dict[str, str]:
    now = datetime.now()
    return {k: v for k, v in showtimes.items() if datetime.fromisoformat(v) >= now}


def _load_json(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    with path.open() as f:
        return json.load(f)


def _save_json(path: Path, data: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")


def run(config_path: Path, discovered_path: Path) -> None:
    config = load_config(config_path)

    newly_found = discover(config, config.discovery_lookahead_days)
    existing = _load_json(discovered_path)
    merged = _prune_past({**existing, **newly_found})

    added = set(merged) - set(existing)
    if added:
        print(f"Discovered {len(added)} new showtime(s): {', '.join(sorted(added))}")
    else:
        print("No new showtimes discovered.")

    _save_json(discovered_path, merged)


def main() -> None:
    run(DEFAULT_CONFIG_PATH, DEFAULT_DISCOVERED_PATH)


if __name__ == "__main__":
    main()
