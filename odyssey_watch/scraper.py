"""Fetches Cinemark's TicketSeatMap page for a given showtime.

The seat map is served fully server-rendered (no client-side API call to
reverse-engineer), and - unlike Cinemark's movie listing pages, which sit
behind DataDome - it responds to a plain HTTP GET with no cookies or JS
challenge required. A realistic browser User-Agent is enough.
"""

from __future__ import annotations

import time

import requests

_SEATMAP_URL = "https://www.cinemark.com/TicketSeatMap/"
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
_TIMEOUT_SECONDS = 20
_RATE_LIMIT_RETRIES = 2
_RATE_LIMIT_BACKOFF_SECONDS = 4


class SeatmapFetchError(RuntimeError):
    """Raised when the seat map page can't be retrieved or looks unparseable."""


def fetch_seatmap_html(
    theater_id: int, showtime_id: int, movie_id: int, showtime_iso: str
) -> str:
    params = {
        "TheaterId": theater_id,
        "ShowtimeId": showtime_id,
        "CinemarkMovieId": movie_id,
        "Showtime": showtime_iso,
    }
    headers = {
        "User-Agent": _USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    response = None
    for attempt in range(_RATE_LIMIT_RETRIES + 1):
        try:
            response = requests.get(
                _SEATMAP_URL, params=params, headers=headers, timeout=_TIMEOUT_SECONDS
            )
        except requests.exceptions.RequestException as exc:
            if attempt == _RATE_LIMIT_RETRIES:
                raise SeatmapFetchError(
                    f"showtime {showtime_id}: request failed ({exc})"
                ) from exc
            time.sleep(_RATE_LIMIT_BACKOFF_SECONDS * (attempt + 1))
            continue
        if response.status_code != 429 or attempt == _RATE_LIMIT_RETRIES:
            break
        time.sleep(_RATE_LIMIT_BACKOFF_SECONDS * (attempt + 1))

    if response.status_code != 200:
        raise SeatmapFetchError(
            f"showtime {showtime_id}: HTTP {response.status_code} from Cinemark"
        )
    if "seatBlock" not in response.text:
        raise SeatmapFetchError(
            f"showtime {showtime_id}: response didn't contain a seat map "
            "(the showtime may have expired or been pulled from sale)"
        )
    return response.text
