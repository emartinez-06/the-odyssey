"""Loads and validates the watcher's YAML configuration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Theater:
    id: int
    name: str
    timezone: str
    detail_path: str


@dataclass(frozen=True)
class Movie:
    id: int
    name: str


@dataclass(frozen=True)
class Showtime:
    id: int
    datetime_iso: str


@dataclass(frozen=True)
class PrimeSeats:
    rows: list[str]
    seat_number_range: tuple[int, int]


@dataclass(frozen=True)
class Config:
    theater: Theater
    movie: Movie
    showtimes: list[Showtime]
    prime_seats: PrimeSeats
    availability_windows: dict[str, list[list[str]]]
    discovery_lookahead_days: int


def load_config(path: Path) -> Config:
    with path.open() as f:
        raw = yaml.safe_load(f)

    theater = Theater(**raw["theater"])
    movie = Movie(**raw["movie"])
    showtimes = [
        Showtime(id=s["id"], datetime_iso=s["datetime"]) for s in raw.get("showtimes", [])
    ]
    prime = raw["prime_seats"]
    prime_seats = PrimeSeats(
        rows=list(prime["rows"]),
        seat_number_range=tuple(prime["seat_number_range"]),
    )
    availability_windows = raw.get("availability_windows", {})
    discovery_lookahead_days = raw.get("discovery", {}).get("lookahead_days", 32)

    return Config(
        theater=theater,
        movie=movie,
        showtimes=showtimes,
        prime_seats=prime_seats,
        availability_windows=availability_windows,
        discovery_lookahead_days=discovery_lookahead_days,
    )
