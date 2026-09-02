# Activity Schedule Dashboard

Scrapes public drop-in activity schedules (skating, swimming, etc.) from a
municipal PerfectMind recreation portal and shows them in one unified,
filterable dashboard.

Currently configured for **City of Coquitlam** and **City of Port Moody**
(Skating + Swimming, next 14 days). See [`config.py`](config.py) for how to
point it at additional calendars or another PerfectMind-based city.

## How it works

- [`scraper.py`](scraper.py) replicates the browser flow the portal's own
  widget uses: load the calendar page to get a session + anti-forgery token,
  then POST that token to the portal's JSON API (`ClassesV2`) for a date
  range. No HTML scraping/parsing is needed — the portal returns structured
  JSON.
- [`app.py`](app.py) is a small Flask app that fetches all configured
  calendars, caches the merged result in memory for 15 minutes
  (`CACHE_TTL_SECONDS` in `config.py`), and serves it as a dashboard page and
  a `/api/events` JSON endpoint.
- The dashboard (`templates/index.html` + `static/app.js`) lets you filter by
  activity type, location, keyword, and "open spots only", grouped by day.

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

Only cities using PerfectMind's `BookMe4` widget work as-is. To add one:

1. Open that city's PerfectMind widget in a browser.
2. Click through to the drop-in category you want.
3. Copy `calendarId` and `widgetId` from the resulting URL, and the
   `base_url`/`org_path` from the domain and path (see the comment at the
   top of `config.py` — this part varies between cities).
4. Add an entry to `SOURCES` in `config.py`.

A different booking platform (ActiveNet, RecTrac, Amilia, etc.) would need
its own scraper module, since each has a different API/HTML shape.

## Configuration

All configuration is done through environment variables — nothing secret or
personal is stored in this repo. Copy [`.env.example`](.env.example) to `.env`
and fill it in for local development; on Render, the same variables are
declared in [`render.yaml`](render.yaml) and entered once in the dashboard.

None of them are required to browse schedules: the app boots and serves the
dashboard with none set. Each group only switches on an optional feature
(accounts, push notifications, email alerts, the scheduled watch check).

`.env` is gitignored and must never be committed.

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

Schedule data comes from the public booking portals of the City of Coquitlam
and the City of Port Moody. This project is unofficial and is not affiliated
with, endorsed by, or operated by either city or by PerfectMind.
