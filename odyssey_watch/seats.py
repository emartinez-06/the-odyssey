"""Seat parsing and prime-seat matching for Cinemark's TicketSeatMap page."""

from __future__ import annotations

import re
from dataclasses import dataclass

from bs4 import BeautifulSoup

_INFO_RE = re.compile(r"^([A-Z]+),(\d+),(\d+),(\d+),(\d+)$")


@dataclass(frozen=True)
class Seat:
    row: str
    number: int
    available: bool

    @property
    def label(self) -> str:
        return f"{self.row}{self.number}"


def parse_seatmap(html: str) -> list[Seat]:
    """Extract every bookable seat from a Cinemark TicketSeatMap page.

    Cinemark renders the seat map server-side as a flat list of <button>
    elements, each carrying an `info` attribute shaped like
    "Row,SeatNumber,RowIndex,ColIndex,ShowtimeId" and an `available`
    attribute of "True" or "False". Non-seat elements (aisles, empty
    spaces) don't carry an `info` attribute and are skipped.
    """
    soup = BeautifulSoup(html, "html.parser")
    seats: list[Seat] = []
    for button in soup.find_all("button", class_="seatBlock"):
        info = button.get("info")
        if not info:
            continue
        match = _INFO_RE.match(info)
        if not match:
            continue
        row, number, _row_idx, _col_idx, _showtime_id = match.groups()
        available = button.get("available") == "True"
        seats.append(Seat(row=row, number=int(number), available=available))
    return seats


def is_prime(seat: Seat, rows: list[str], seat_number_range: tuple[int, int]) -> bool:
    """Whether a seat falls inside the configured "prime middle" block."""
    low, high = seat_number_range
    return seat.row in rows and low <= seat.number <= high


def prime_available_seats(
    seats: list[Seat], rows: list[str], seat_number_range: tuple[int, int]
) -> list[Seat]:
    """Seats that are both currently bookable and inside the prime block."""
    return [s for s in seats if s.available and is_prime(s, rows, seat_number_range)]
