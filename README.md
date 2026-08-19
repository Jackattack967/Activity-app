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
