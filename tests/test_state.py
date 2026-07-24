from odyssey_watch.state import newly_available


def test_newly_available_returns_only_seats_not_seen_before():
    previous = ["F13", "G13"]
    current = ["F13", "G13", "G14"]

    assert newly_available(previous, current) == ["G14"]


def test_newly_available_returns_nothing_when_unchanged():
    previous = ["F13", "G13"]
    current = ["F13", "G13"]

    assert newly_available(previous, current) == []


def test_newly_available_handles_seats_reappearing_after_disappearing():
    previous = []
    current = ["F13"]

    assert newly_available(previous, current) == ["F13"]


def test_newly_available_ignores_seats_that_disappeared():
    previous = ["F13", "G13"]
    current = ["F13"]

    assert newly_available(previous, current) == []
