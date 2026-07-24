"""Entry point: check every configured showtime, notify on newly-available
prime seats, and persist state for the next run.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from odyssey_watch.config import Showtime, load_config
from odyssey_watch.notify import create_issue
from odyssey_watch.schedule import is_within_availability_window, to_theater_local
from odyssey_watch.scraper import SeatmapFetchError, fetch_seatmap_html
from odyssey_watch.seats import parse_seatmap, prime_available_seats
from odyssey_watch.state import load_state, newly_available, save_state

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = REPO_ROOT / "config" / "config.yaml"
DEFAULT_STATE_PATH = REPO_ROOT / "state" / "seen_seats.json"
DEFAULT_DISCOVERED_PATH = REPO_ROOT / "state" / "discovered_showtimes.json"
_DELAY_BETWEEN_FETCHES_SECONDS = 0.75


def _format_showtime(showtime_local: datetime) -> str:
    return showtime_local.strftime("%A, %B %-d at %-I:%M %p")


def _load_all_showtimes(config_showtimes: list[Showtime], discovered_path: Path) -> list[Showtime]:
    """Manually-configured showtimes plus whatever discover.py has found,
    deduped by showtime id (manual entries win on conflict).
    """
    by_id = {}
    if discovered_path.exists():
        with discovered_path.open() as f:
            for showtime_id, datetime_iso in json.load(f).items():
                by_id[int(showtime_id)] = Showtime(id=int(showtime_id), datetime_iso=datetime_iso)
    for showtime in config_showtimes:
        by_id[showtime.id] = showtime
    return list(by_id.values())


def run(config_path: Path, state_path: Path, discovered_path: Path, dry_run: bool) -> None:
    config = load_config(config_path)
    state = load_state(state_path)
    now = datetime.now(ZoneInfo(config.theater.timezone))
    all_showtimes = _load_all_showtimes(config.showtimes, discovered_path)

    for showtime in all_showtimes:
        showtime_local = to_theater_local(showtime.datetime_iso, config.theater.timezone)
        when = _format_showtime(showtime_local)

        if showtime_local < now:
            continue

        if not is_within_availability_window(showtime_local, config.availability_windows):
            print(f"{when}: outside your availability windows, skipping")
            continue

        try:
            html = fetch_seatmap_html(
                theater_id=config.theater.id,
                showtime_id=showtime.id,
                movie_id=config.movie.id,
                showtime_iso=showtime.datetime_iso,
            )
        except SeatmapFetchError as exc:
            print(f"warning: {exc}", file=sys.stderr)
            continue
        finally:
            time.sleep(_DELAY_BETWEEN_FETCHES_SECONDS)

        seats = parse_seatmap(html)
        prime = prime_available_seats(
            seats, config.prime_seats.rows, config.prime_seats.seat_number_range
        )
        current_labels = sorted(seat.label for seat in prime)

        key = str(showtime.id)
        previous_labels = state.get(key, [])
        new_labels = newly_available(previous_labels, current_labels)

        if new_labels:
            title = f"Prime seats open: {when} - {', '.join(new_labels)}"
            booking_url = (
                "https://www.cinemark.com/TicketSeatMap/"
                f"?TheaterId={config.theater.id}&ShowtimeId={showtime.id}"
                f"&CinemarkMovieId={config.movie.id}&Showtime={showtime.datetime_iso}"
            )
            body = (
                f"**{config.movie.name}** at **{config.theater.name}**\n\n"
                f"Showtime: {when} ({config.theater.timezone})\n\n"
                f"Newly available prime seats: {', '.join(new_labels)}\n\n"
                f"All currently available prime seats: {', '.join(current_labels) or 'none'}\n\n"
                f"[Book now]({booking_url})"
            )
            print(title)
            if not dry_run:
                url = create_issue(title, body)
                print(f"  -> {url}")
        else:
            print(f"{when}: no new prime seats ({len(current_labels)} available)")

        state[key] = current_labels

    if not dry_run:
        save_state(state_path, state)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Watch Cinemark for open Odyssey IMAX 70mm prime seats."
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE_PATH)
    parser.add_argument("--discovered", type=Path, default=DEFAULT_DISCOVERED_PATH)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't create issues or write state; just print what would happen.",
    )
    args = parser.parse_args()
    run(args.config, args.state, args.discovered, args.dry_run)


if __name__ == "__main__":
    main()
