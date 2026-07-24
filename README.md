# The Odyssey Seat Watcher

![Python](https://img.shields.io/badge/python-3.12%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

A small, cron-driven watcher for Cinemark's *The Odyssey* IMAX 70mm showtimes.
It automatically discovers showtimes as Cinemark publishes them, polls their seat maps, and opens a GitHub Issue - which GitHub emails to you - the moment a "prime" seat opens up.
You control which showtimes are even worth checking with a per-day-of-week availability schedule, so a seat freeing up on a Tuesday at 2:30am doesn't page you if you're never free then.

## How it works

Two things made this possible without browser automation or fighting Cinemark's bot protection:

- **Seat maps** (`/TicketSeatMap/?TheaterId=...&ShowtimeId=...&CinemarkMovieId=...&Showtime=...`) are fully server-rendered. Each seat is a `<button>` with an `info` attribute like `"F,13,5,12,640213"` (row, seat number, row index, column index, showtime id) and an `available` attribute of `"True"` or `"False"`. A plain HTTP GET with a normal User-Agent returns the whole layout - this page sits behind Cloudflare's baseline protection only.
- **Showtime discovery** uses each theater's own page (`/theatres/<slug>?showDate=YYYY-MM-DD`) rather than Cinemark's movie-listing pages. The listing pages pick a theater via geolocation/DataDome and don't respond reliably to a bare HTTP client; a theater's own page is pinned by its URL slug instead, and returns that specific theater's full showtime list - including every movie's `ShowtimeId` - for any date, with no cookies or challenge required.

Two scheduled jobs do the work:

**`discover.py`** (hourly): walks a lookahead window of dates - limited to the days of the week you've actually configured an availability window for - fetching each date's page for your theater and recording every showtime found for the movie into `state/discovered_showtimes.json`.

**`main.py`** (every 10 minutes):

1. Loads `config/config.yaml` (your theater, prime-seat definition, and weekly availability windows) plus every showtime `discover.py` has found.
2. Skips any showtime already in the past, or whose start time falls outside your availability windows for that day of week.
3. Fetches and parses the seat map for everything left.
4. Diffs the currently-available prime seats against `state/seen_seats.json`, written by the previous run.
5. Opens a GitHub Issue for any showtime with seats that are newly available (not ones you were already notified about).
6. Commits the updated state file back to the repo.

GitHub Actions runs both on a schedule, so no server or always-on machine is required.

## Setup

1. Edit `config/config.yaml`:
   - `theater` - your Cinemark theater's id, display name, IANA timezone, and `detail_path` (the part of the theater's own URL after `cinemark.com/theatres/` - find your theater at [cinemark.com/theatres](https://www.cinemark.com/theatres)).
   - `discovery.lookahead_days` - how far ahead to look for new showtimes (defaults to 32; Cinemark opens tickets on a rolling ~26-day window).
   - `prime_seats` - which rows and seat-number range count as a "prime" seat worth a notification.
   - `availability_windows` - per day of week, the local-time ranges during which a newly-available showtime should actually notify you. An empty list for a day means "never notify for showtimes on that day" **and** "never bother discovering showtimes on that day" - discovery only checks days that have at least one window configured.
   - `showtimes` - normally left empty. Only use this to pin a specific showtime `discover.py` hasn't picked up yet, or to track a different movie/theater by hand.
2. Push to `main`. The workflows in `.github/workflows/` start running on their schedules automatically once they're on the default branch.
   - If you forked this repo instead of using it directly, GitHub disables Actions on forks by default - enable it from the repo's **Actions** tab first.
   - GitHub also auto-disables scheduled workflows after 60 days with no repository activity; a push (like a state-file commit, or any manual commit) resets that clock.
3. Watch the repo's **Issues** tab, or just your email - GitHub notifies repository owners by email when a new issue opens, with no extra configuration.

No secrets or credentials are required.
Both workflows use the repository's built-in `GITHUB_TOKEN` to open issues and push state files.

## Configuration reference

```yaml
theater:
  id: 207                              # Cinemark TheaterId
  name: "Cinemark Dallas XD and IMAX"
  timezone: "America/Chicago"          # IANA tz name, used to interpret showtime clock times
  detail_path: "tx-dallas/cinemark-dallas-xd-and-imax"

movie:
  id: 104867                           # Cinemark CinemarkMovieId
  name: "The Odyssey (IMAX 70mm)"

discovery:
  lookahead_days: 32

showtimes: []                          # optional manual pins/overrides - see Setup above

prime_seats:
  rows: ["E", "F", "G", "H", "J", "K"]
  seat_number_range: [1, 26]

availability_windows:
  friday: [["14:55", "15:35"], ["18:40", "19:20"]]
  saturday: [["11:10", "11:50"], ["14:55", "15:35"], ["18:40", "19:20"]]
  # ...one list per day; each entry is a [start, end] 24-hour "HH:MM" pair
```

## Local development

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest
```

Run the watcher locally without opening issues or writing state:

```sh
.venv/bin/python -m odyssey_watch.main --dry-run
```

Point it at different files with `--config`, `--state`, and `--discovered`.

Run discovery locally (this does write `state/discovered_showtimes.json`, there's no dry-run flag since it's non-destructive by nature):

```sh
.venv/bin/python -m odyssey_watch.discover
```

## Project structure

```
config/config.yaml               Theater, prime-seat rules, availability windows, manual showtime pins
odyssey_watch/
  discover.py                    Finds newly-published showtimes via the theater's own page
  scraper.py                     Fetches a showtime's seat map HTML
  seats.py                       Parses seats, matches "prime" seats
  schedule.py                    Day-of-week / time-window filtering
  state.py                       Tracks previously-seen available seats
  notify.py                      Opens a GitHub Issue
  config.py                      Loads config.yaml
  main.py                        Orchestrates a single watch run
state/seen_seats.json            Watcher's memory of what's already been notified
state/discovered_showtimes.json  Showtimes discover.py has found
tests/                           pytest suite, with captured-structure HTML fixtures
.github/workflows/
  watch.yml                      Seat-check run, every 10 minutes
  discover.yml                   Showtime-discovery run, hourly
```

## Limitations

- Discovery only looks at days of the week with a configured availability window, since there's no reason to discover showtimes you'd never be notified about. Add a window for a day (even a narrow one) before showtimes on that day will be found at all.
- Polling cadence (10 minutes for seat checks, hourly for discovery) balances prompt notifications against being a reasonable citizen toward Cinemark's servers; adjust the cron schedules in `.github/workflows/` if you want them tighter or looser.
- `watch.yml` and `discover.yml` both commit to `main` independently; each retries its push with a rebase a couple of times if the other one lands first.

## License

[MIT](LICENSE)
