# Activity Schedule Dashboard

Scrapes public drop-in activity schedules (skating, swimming, etc.) from a
municipal PerfectMind recreation portal and shows them in one unified,
filterable dashboard.

Currently configured for **City of Coquitlam** (Skating + Swimming, next 14
days). See [`config.py`](config.py) for how to point it at additional
calendars or another PerfectMind-based city.

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

## Run it

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Then open http://localhost:5000. Click **Refresh** to force a fresh scrape
(otherwise it re-scrapes automatically after the cache expires).

## Adding another city/portal

Only cities using PerfectMind's `BookMe4` widget work as-is. To add one:

1. Open that city's PerfectMind widget in a browser.
2. Click through to the drop-in category you want.
3. Copy `calendarId` and `widgetId` from the resulting URL, and the
   `base_url`/`org_id` from the domain and path.
4. Add an entry to `SOURCES` in `config.py`.

A different booking platform (ActiveNet, RecTrac, Amilia, etc.) would need
its own scraper module, since each has a different API/HTML shape.
