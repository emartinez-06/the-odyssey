"""Tracks which prime seats have already been seen available, per showtime."""

from __future__ import annotations

import json
from pathlib import Path

State = dict[str, list[str]]


def load_state(path: Path) -> State:
    if not path.exists():
        return {}
    with path.open() as f:
        return json.load(f)


def save_state(path: Path, state: State) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        json.dump(state, f, indent=2, sort_keys=True)
        f.write("\n")


def newly_available(previous_labels: list[str], current_labels: list[str]) -> list[str]:
    """Seat labels that are available now but weren't seen on the last run."""
    previous = set(previous_labels)
    return sorted(label for label in current_labels if label not in previous)
