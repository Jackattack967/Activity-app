# Activity Schedule Dashboard

Scrapes public drop-in activity schedules (skating, swimming, sports,
fitness, golf) from municipal recreation portals and shows them in one
unified, filterable dashboard.

Currently configured for **Coquitlam**, **Port Coquitlam**, **Port Moody**,
**New Westminster**, **Burnaby** and **West Vancouver**. The first five were
measured at around 790 sessions across 24 venues over a 14-day window; West
Vancouver is new and has not been counted. See [`config.py`](config.py) for
how to add a calendar or a city.

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

The ids themselves come out of the portal in a browser — no scripts, no
account. [`docs/collecting-portal-ids.md`](docs/collecting-portal-ids.md)
walks through it click by click for both platforms.

A third booking platform (RecTrac, Amilia, Xplor, etc.) needs its own
module, since each has a different API shape. Write one exposing
`fetch_calendar_events()` and `build_login_url()`, then list it in
`PLATFORMS` in `scraper.py` — nothing else has to change.

### Which cities are on what

Metro Vancouver is split between the two platforms this app already speaks,
so most neighbours are reachable with config alone:

| City | Platform | Portal |
| --- | --- | --- |
| Coquitlam, Port Moody, New Westminster | PerfectMind | configured |
| Port Coquitlam, Burnaby | ActiveNet | configured |
| West Vancouver | ActiveNet | configured |
| Vancouver (Park Board) | ActiveNet | `anc.ca.apm.activecommunities.com/vancouver` |
| Richmond | PerfectMind | `richmondcity.perfectmind.com/23650/Clients` |
| North Vancouver (NVRC, city + district) | PerfectMind | `nvrc.perfectmind.com/23734/Clients` |
| Maple Ridge, Delta, White Rock, Surrey | PerfectMind | not yet configured |

Richmond also keeps an ActiveNet tenant (`cityofrichmond`) alongside its
PerfectMind one; its own website links to PerfectMind, so that's the one to
read.

Burnaby is configured for golf only, which is the one activity no other
city here publishes. Its pools, rinks and gyms are on the same ActiveNet
tenant and would be config alone, but they roughly double the size of the
dashboard, so they are left out until they are actually wanted.

### Golf, and what is missing from it

Golf comes from Burnaby's two municipal courses, Burnaby Mountain and
Riverway, and — since West Vancouver was added — from Gleneagles, whichever
of its golf programs the portal publishes as drop-ins. It is **lessons and
clinics, not tee times**. Those are real
bookable sessions with real remaining-spot counts, which is what a watch
needs in order to tell you a place has opened up.

Booking a plain round is a different system, at every course here. Both
Burnaby and Vancouver run their tee sheets on CPS Golf (`golfburnaby.cps.golf`, `golfvancouver.cps.golf`),
which answers every automated request with an HTTP 403 from Cloudflare.
Getting around that would mean defeating bot protection the vendor has
deliberately turned on, so this app doesn't read tee times at all — use the
courses' own sites for those.

The Tri-Cities have no municipal golf to add. Coquitlam, Port Coquitlam and
Port Moody run no city courses, and Port Coquitlam's portal has no golf
category; the courses near them (Carnoustie, Westwood Plateau, Vancouver
Golf Club) are private clubs, not city facilities. Vancouver's portal has no
golf either — only two gym classes named after it.

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

An area with fewer than three visible venues has no hull, and gets a small
circle on each venue instead of one circle between them. Burnaby is why:
its two golf courses are 7.9 km apart, so a single circle at their midpoint
would tint a part of the city containing neither, with both pins outside
their own area. Widening it to reach them would take a 4.4 km radius, which
crosses the river and swallows two of New Westminster's venues — the same
problem hulls were introduced to solve.

Panning is fenced to Canada (`MAP_MAX_BOUNDS` in `static/app.js`), and the
map will not zoom out past the point where the whole country is on screen.
That floor is not a constant: Leaflet's `getBoundsZoom` is asked what zoom
fits the fence in the map box as it currently is, because the box is 60vh
and the answer therefore depends on the screen. It also depends on the
fence, so changing one changes the other automatically. Canada is very tall
in Web Mercator — the projection stretches Ellesmere Island at 83°N far
more than the border at 49°N — so it is the height, not the width, that
decides: a hardcoded zoom 4 fitted the width of a desktop map but showed
only about a third of the country's height. Every venue is in Metro
Vancouver, so the rest of the world is
somewhere this app has nothing to say about — and panning there still pulls
tiles from OpenStreetMap's donated servers, whose [usage policy](https://operations.osmfoundation.org/policies/tiles/)
asks that their capacity not be spent on demand nobody made. The fence is
drawn at Canada rather than at the Lower Mainland so that adding a city
never means moving it. `test_scrapers.py` reads those bounds out of the
JavaScript and checks every venue falls inside them, which is what catches
a longitude typed without its minus sign.

On a first visit the app asks once for your location and preselects the
nearest area in the preferences dialog. It picks the area of the closest
*venue*, not the closest area centre: Port Moody's three venues average out
to a point that is nearer Coquitlam's centre than its own, so centres answer
"Coquitlam" while standing at Port Moody city hall. The prompt is shown at
most once ever — a refusal is remembered as firmly as a permission — nothing
waits on it for more than seven seconds, and every failure just leaves "All
areas" selected. The coordinates are compared against the venues already on
the page and then discarded; they are never sent anywhere.

## Dark mode

Every colour on the site is a CSS custom property, and the two themes differ
only in what those tokens resolve to — no component restyles itself per
theme. There are three states, not two: no `data-theme` attribute at all
(follow the operating system, the default), `data-theme="light"`, and
`data-theme="dark"`. The media query is written as
`:root:not([data-theme="light"])` so an explicit light choice still beats a
dark OS.

**Menu → Theme** cycles Auto → Light → Dark and remembers the choice. A
small inline script in `templates/_theme.html` applies it before the first
paint — without it, someone who chose dark gets a white flash on every
navigation. That partial is included by all four page templates, which are
standalone documents with no shared base, and it also sets `theme-color`
(the browser's own chrome on a phone), which the media-query form of that
tag cannot do once a manual override exists.

A few tokens are deliberately not symmetrical. `--green`, `--red` and
`--text-muted` are read as text, so they lighten on a dark ground — but the
same hues also fill the danger button and the map markers, which carry white
text and must stay dark. Those fills are separate `-solid` tokens.
Collapsing the two is how a dark mode ends up with white-on-pink buttons.

OpenStreetMap only serves a light basemap, so dark mode inverts it in the
browser (`--tile-filter`) rather than fetching different tiles. Leaflet's own
controls — zoom buttons, scale bar, attribution — are restyled with
`.leaflet-container`-prefixed selectors, because Leaflet's rules are more
specific than a bare class and quietly win otherwise.

## Feedback

The Feedback button in the header emails what someone writes to
`FEEDBACK_EMAIL`, or to `CONTACT_EMAIL` if that isn't set. If neither is set,
or no email provider is configured, the button isn't rendered at all — a
button that silently discards what someone took the trouble to write is worse
than no button.

Nothing is stored. The message goes to an inbox and nowhere else, which keeps
a free-text field written by the public out of the database entirely.

Two things about it are deliberate:

- **Everything is HTML-escaped.** The body is HTML sent from this app's own
  address, so unescaped input would let a stranger compose the markup of a
  mail that appears to come from you — a phishing kit, not a bug.
- **It is rate limited on two axes**, because it is an unauthenticated
  endpoint that causes email to be sent: three per sender per hour so one
  person can't flood the inbox, and forty in total per hour so a script can't
  burn the provider's daily allowance and take the spot-open alerts down with
  it. The counters are in memory, which is enough at one gunicorn worker.

Run `python test_feedback.py` to exercise the limits and the escaping. It
swaps the delivery function for one that records, so it never sends.

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

All four are plain scripts — no pytest, no network, no real database. Each
exits non-zero on failure.

```bash
python test_scrapers.py     # platform routing, and parsing captured API rows
python test_feedback.py     # feedback rate limits and HTML escaping
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
Coquitlam, Port Coquitlam, Port Moody, New Westminster and Burnaby. This project is
unofficial and is not affiliated with, endorsed by, or operated by any of
those cities, or by PerfectMind or Active Network.
