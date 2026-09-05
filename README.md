# Activity Schedule Dashboard

Scrapes public drop-in activity schedules (skating, swimming, sports,
fitness) from municipal recreation portals and shows them in one unified,
filterable dashboard.

Currently configured for **Coquitlam**, **Port Coquitlam**, **Port Moody**
and **New Westminster** — around 600 sessions across 23 venues over the next
14 days. See [`config.py`](config.py) for how to add a calendar or a city.

Cities don't all run the same booking software, so the scraper is split by
platform: [`scraper.py`](scraper.py) picks a module per source, and
[`scraper_perfectmind.py`](scraper_perfectmind.py) and
[`scraper_activenet.py`](scraper_activenet.py) each return the same `Event`
objects. Nothing downstream knows or cares which portal an event came
from.

## How it works

- [`scraper_perfectmind.py`](scraper_perfectmind.py) replicates the browser
  flow the portal's own widget uses: load the calendar page to get a session
  + anti-forgery token, then POST that token to the portal's JSON API
  (`ClassesV2`) for a date range. No HTML scraping/parsing is needed — the
  portal returns structured JSON.
- [`scraper_activenet.py`](scraper_activenet.py) does the same for ActiveNet
  portals, which need no token — just a warm-up request for cookies, then a
  paged JSON search. Its one real complication is that ActiveNet returns
  *activities* rather than occurrences, so a recurring one is expanded
  across its weekdays.
- [`app.py`](app.py) is a small Flask app that fetches all configured
  calendars, caches the merged result in memory for 15 minutes
  (`CACHE_TTL_SECONDS` in `config.py`), and serves it as a dashboard page and
  a `/api/events` JSON endpoint.
- The dashboard (`templates/index.html` + `static/app.js`) lets you filter by
  activity type, area, location, keyword, and "open spots only", grouped by
  day — or shows the same filtered set on a map.

## Run it locally

Easiest: double-click **`Start Activity Dashboard.bat`**. It starts the
server, opens your browser to it, and prints your PC's LAN IP so you can
open the same dashboard from a phone on the same WiFi.

Or manually:

```bash
python -m pip install -r requirements.txt
python app.py
```

Then open http://localhost:8000. Click **Refresh** to force a fresh scrape
(otherwise it re-scrapes automatically after the cache expires).

## Deploying it (Render)

This repo includes a [`render.yaml`](render.yaml) so Render can configure
itself automatically. Steps:

1. **Push this repo to GitHub** (if you haven't already):
   - Create a new empty repository at [github.com/new](https://github.com/new)
     — don't check any of the "initialize with README/.gitignore" boxes.
   - Then, from this folder:
     ```bash
     git remote add origin https://github.com/<your-username>/<repo-name>.git
     git branch -M main
     git push -u origin main
     ```
2. **Create a Render account** at [render.com](https://render.com) (free,
   no credit card needed for the free tier).
3. On the Render dashboard, click **New +** → **Blueprint**, then connect
   the GitHub repo you just pushed. Render will read `render.yaml`
   automatically and set everything up — build command, start command, and
   the free plan.
4. Click **Apply** / **Deploy**. First deploy takes a few minutes. You'll
   get a public URL like `https://activity-schedule-dashboard.onrender.com`.

Note: on Render's free tier, the app "spins down" after 15 minutes with no
visitors and takes 30-60 seconds to wake back up on the next visit — normal
for a personal-use app, and Render's $7/month Starter plan removes that if
it ever becomes annoying.

(Note for local dev on Windows: `gunicorn`, used in production on Render,
doesn't run on Windows at all — that's expected. Keep using `python app.py`
or the `.bat` launcher locally; gunicorn only matters once it's on Render's
Linux servers.)

## Adding another city/portal

Cities on PerfectMind's `BookMe4` widget or on ActiveNet work as-is — add an
entry to `SOURCES` in `config.py` and give it the matching `platform`. The
comment at the top of that file has the steps for finding the ids each one
needs, including the public ActiveNet endpoint that lists a city's buildings
and categories.

Then add the city to `AREAS` and its venues to `FACILITY_COORDS`, both in
`config.py`. Neither is required for the schedule itself: a venue with no
coordinates simply gets no map pin, and a city with no area shows only under
"All areas".

A third booking platform (RecTrac, Amilia, Xplor, etc.) needs its own
module, since each has a different API shape. Write one exposing
`fetch_calendar_events()` and `build_login_url()`, then list it in
`PLATFORMS` in `scraper.py` — nothing else has to change.

### Which cities are on what

Not every neighbour is reachable. Metro Vancouver PerfectMind tenants exist
for Coquitlam, Port Moody, New Westminster, Maple Ridge, Delta, White Rock,
Surrey and North Vancouver (NVRC). Port Coquitlam and Burnaby are on
ActiveNet. Vancouver and Richmond are on neither.

## Configuration

All configuration is done through environment variables — nothing secret or
personal is stored in this repo. Copy [`.env.example`](.env.example) to `.env`
and fill it in for local development; on Render, the same variables are
declared in [`render.yaml`](render.yaml) and entered once in the dashboard.

None of them are required to browse schedules: the app boots and serves the
dashboard with none set. Each group only switches on an optional feature
(accounts, push notifications, email alerts, the scheduled watch check).

`.env` is gitignored and must never be committed.

## How alerting stays alive

Watch passes run from two places, deliberately:

1. **Inside the app** ([`autowatch.py`](autowatch.py)) — a background thread
   runs a pass every 5 minutes while the app is awake.
2. **An external scheduler** calling `/api/check-watches`.

The thread defers to the scheduler: if a pass ran in the last 4 minutes, by
anyone, it sits that turn out. So they never double up, and if the external
scheduler stops, the thread takes over within one interval.

This exists because the external-scheduler-only setup failed twice, the second
time silently. Render's free tier sleeps after ~15 minutes idle and takes ~31
seconds to wake; cron-job.org's timeout is a hard 30 seconds and it disables a
job after 25 consecutive failures. Every ping arriving while the app was asleep
failed, and about two hours of that switched the job off.

**The thread cannot keep the app awake** — Render spins down on inbound request
inactivity, and a busy thread doesn't count. So something external still has to
ping it. The point is that the pinger's job is now much easier: it only has to
keep the app awake, not drive every check on a strict timer. Point it at
`/api/watch-status`, which is public, needs no token, and answers in
milliseconds, rather than at `/api/check-watches`, which does a full scrape.

`/api/watch-status` reports `autowatch: true|false` so you can tell from
outside whether the loop is actually running.

## Areas, and picking one

Every event is tagged with an area — currently one per city — from
`CITY_AREAS`, which `config.py` builds out of `AREAS`. That tag drives three
things: the Area filter, the colour of a venue's ring on the map, and which
zone outline it falls inside.

Areas are keyed on the *city*, not the venue, so a venue that appears in a
portal tomorrow lands in the right area with no code change. Only
`FACILITY_COORDS` needs a new entry, and only for the map pin.

The map draws each area as a hull around its own venues rather than a
circle. A circle wide enough to cover Coquitlam's ten venues — Maillardville
in the south-west out to Smiling Creek in the north-east — is about 6.7 km
across, which swallows both Port Moody and Port Coquitlam whole. Hulls of
the same venues don't overlap at all.

On a first visit the app asks once for your location and preselects the
nearest area in the preferences dialog. It picks the area of the closest
*venue*, not the closest area centre: Port Moody's three venues average out
to a point that is nearer Coquitlam's centre than its own, so centres answer
"Coquitlam" while standing at Port Moody city hall. The prompt is shown at
most once ever — a refusal is remembered as firmly as a permission — nothing
waits on it for more than seven seconds, and every failure just leaves "All
areas" selected. The coordinates are compared against the venues already on
the page and then discarded; they are never sent anywhere.

## Unused accounts are deleted

An account that goes unused for six months is deleted, along with its watches,
filters and notification settings. A warning email goes out 30 days before
that, and signing in cancels it. The daily
[`purge-inactive`](.github/workflows/purge-inactive.yml) workflow drives this.

Two safeguards are deliberate:

- **Nothing is deleted until `RETENTION_ENABLED` is set.** Unset, the job
  reports which accounts it *would* warn and delete and changes nothing. Leave
  it that way for a few weeks and read the output before arming it.
- **An account is never deleted without a warning that actually sent.** The
  "warned" timestamp is only written once the email provider accepts the
  message, and deletion requires it — so if email breaks, deletions stall
  instead of happening silently.

Run `python test_retention.py` to exercise the rules against a throwaway
sqlite database. It never touches the real one.

## Tests

All three are plain scripts — no pytest, no network, no real database. Each
exits non-zero on failure.

```bash
python test_scrapers.py     # platform routing, and parsing captured API rows
python test_retention.py    # the deletion rules, against throwaway sqlite
python test_autowatch.py    # the in-app watch loop, with shortened intervals
```

## License

This project's own code is released under the [MIT License](LICENSE). The
third-party packages it depends on keep their own licenses — see
[`THIRD-PARTY-NOTICES.md`](THIRD-PARTY-NOTICES.md).

## Credits

Built with open-source software. Every third-party package and its license is
listed in [`THIRD-PARTY-NOTICES.md`](THIRD-PARTY-NOTICES.md) — chiefly
[Flask](https://flask.palletsprojects.com/), [SQLAlchemy](https://www.sqlalchemy.org/),
[Authlib](https://authlib.org/), [Requests](https://requests.readthedocs.io/),
[Gunicorn](https://gunicorn.org/) and [pywebpush](https://github.com/web-push-libs/pywebpush).

Schedule data comes from the public booking portals of the Cities of
Coquitlam, Port Coquitlam, Port Moody and New Westminster. This project is
unofficial and is not affiliated with, endorsed by, or operated by any of
those cities, or by PerfectMind or Active Network.
