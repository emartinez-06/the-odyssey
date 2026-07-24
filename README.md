# The Odyssey Seat Watcher

![Python](https://img.shields.io/badge/python-3.12%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

A small, cron-driven watcher for Cinemark's *The Odyssey* IMAX 70mm showtimes.
It polls the public seat map for a list of showtimes you configure, and opens a GitHub Issue - which GitHub emails to you - the moment a "prime" middle seat opens up.
You control which showtimes are even worth checking with a per-day-of-week availability schedule, so a seat freeing up on a Tuesday at 2:30am doesn't page you if you're never free then.

## How it works

Cinemark's seat map (`/TicketSeatMap/?TheaterId=...&ShowtimeId=...&CinemarkMovieId=...&Showtime=...`) is fully server-rendered.
Each seat is a `<button>` with an `info` attribute like `"F,13,5,12,640213"` (row, seat number, row index, column index, showtime id) and an `available` attribute of `"True"` or `"False"`.
No client-side API call or browser automation is needed - a plain HTTP GET with a normal User-Agent returns the whole seat layout, and it sits behind Cloudflare's baseline protection only (unlike Cinemark's movie listing pages, which are behind DataDome and don't respond reliably to a bare HTTP client).

Every run, the watcher:

1. Loads `config/config.yaml` - your theater, the showtimes you care about, your "prime seat" definition, and your weekly availability windows.
2. Skips any showtime that's already in the past, or whose start time falls outside your availability windows for that day of week.
3. Fetches and parses the seat map for everything left.
4. Diffs the currently-available prime seats against `state/seen_seats.json`, which was written by the previous run.
5. Opens a GitHub Issue for any showtime with seats that are newly available (not ones you were already notified about).
6. Commits the updated state file back to the repo.

GitHub Actions runs this on a schedule (every 10 minutes by default), so no server or always-on machine is required.

## Setup

1. Edit `config/config.yaml`:
   - `theater` - your Cinemark theater's id, display name, and IANA timezone.
   - `showtimes` - the specific showtimes to watch. See the comment in the file for how to find a `ShowtimeId` for a new date.
   - `prime_seats` - which rows and seat-number range count as a "prime middle" seat worth a notification.
   - `availability_windows` - per day of week, the local-time ranges during which a newly-available showtime should actually notify you. An empty list for a day means "never notify for showtimes on that day."
2. Push to `main`. The workflow in `.github/workflows/watch.yml` starts running on its schedule automatically once it's on the default branch.
   - If you forked this repo instead of using it directly, GitHub disables Actions on forks by default - enable it from the repo's **Actions** tab first.
   - GitHub also auto-disables scheduled workflows after 60 days with no repository activity; a push (like a state-file commit, or any manual commit) resets that clock.
3. Watch the repo's **Issues** tab, or just your email - GitHub notifies repository owners by email when a new issue opens, with no extra configuration.

No secrets or credentials are required.
The workflow uses the repository's built-in `GITHUB_TOKEN` to open issues and push the state file.

## Configuration reference

```yaml
theater:
  id: 207                              # Cinemark TheaterId
  name: "Cinemark Dallas XD and IMAX"
  timezone: "America/Chicago"          # IANA tz name, used to interpret showtime clock times

movie:
  id: 104867                           # Cinemark CinemarkMovieId
  name: "The Odyssey (IMAX 70mm)"

showtimes:
  - id: 640213                         # Cinemark ShowtimeId
    datetime: "2026-08-18T11:30:00"    # local time, no UTC offset - matches Cinemark's own format

prime_seats:
  rows: ["E", "F", "G", "H"]
  seat_number_range: [10, 17]

availability_windows:
  friday: [["00:00", "23:59"]]
  saturday: [["00:00", "23:59"]]
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

Point it at a different config or state file with `--config` and `--state`.

## Project structure

```
config/config.yaml           Theater, showtimes, prime-seat rules, availability windows
odyssey_watch/
  scraper.py                 Fetches a showtime's seat map HTML
  seats.py                   Parses seats, matches "prime" seats
  schedule.py                Day-of-week / time-window filtering
  state.py                   Tracks previously-seen available seats
  notify.py                  Opens a GitHub Issue
  config.py                  Loads config.yaml
  main.py                    Orchestrates a single watch run
state/seen_seats.json        Watcher's memory of what's already been notified
tests/                       pytest suite, including a captured-structure HTML fixture
.github/workflows/watch.yml  Scheduled run, every 10 minutes
```

## Limitations

- Only tracks showtimes explicitly listed in `config/config.yaml` - there's no automatic discovery of new dates, since Cinemark's movie listing pages sit behind bot protection that a plain scraper can't clear reliably. Add new showtimes by hand as they go on sale.
- Polling every 10 minutes is a balance between prompt notifications and being a reasonable citizen toward Cinemark's servers; adjust the cron schedule in `watch.yml` if you want it tighter or looser.

## License

[MIT](LICENSE)
