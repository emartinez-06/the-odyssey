from pathlib import Path

from odyssey_watch.seats import parse_seatmap, prime_available_seats

FIXTURE = Path(__file__).parent / "fixtures" / "seatmap_sample.html"


def test_parse_seatmap_reads_every_seat_button():
    html = FIXTURE.read_text()
    seats = parse_seatmap(html)

    assert len(seats) == 7
    labels = {seat.label: seat.available for seat in seats}
    assert labels == {
        "A7": True,
        "A8": False,
        "D13": True,
        "F13": True,
        "F14": False,
        "G13": True,
        "G26": True,
    }


def test_parse_seatmap_ignores_non_seat_elements():
    html = FIXTURE.read_text()
    seats = parse_seatmap(html)

    assert "E20" not in {seat.label for seat in seats}


def test_prime_available_seats_filters_by_row_and_range_and_availability():
    html = FIXTURE.read_text()
    seats = parse_seatmap(html)

    prime = prime_available_seats(seats, rows=["E", "F", "G", "H"], seat_number_range=(10, 17))

    assert {seat.label for seat in prime} == {"F13", "G13"}


def test_prime_available_seats_excludes_unavailable_seats_in_range():
    html = FIXTURE.read_text()
    seats = parse_seatmap(html)

    prime = prime_available_seats(seats, rows=["F"], seat_number_range=(14, 14))

    assert prime == []
