# Collecting the ids for a new city

Everything in [`config.py`](../config.py) is public information, but the
portals don't advertise it — you have to pull it out of the booking site
itself. This is how, using nothing but a browser. No developer tools, no
scripts, no account.

You only ever need to do this once per city (or once per calendar you want
to add to a city that's already configured).

---

## Step 1 — work out which software the city runs

Open the city's "register for programs" or "drop-in schedule" page and look
at the address bar after it redirects:

| The address contains | The platform is | What you'll collect |
| --- | --- | --- |
| `something.perfectmind.com` | **PerfectMind** | one URL per calendar |
| `apm.activecommunities.com` | **ActiveNet** | one JSON page per city |
| anything else | neither — needs a new scraper module | — |

A few cities run both, usually because they migrated and left the old one
up. Prefer whichever one their own website links to today.

---

## Step 2a — PerfectMind: copy one URL per calendar

PerfectMind splits a city's drop-ins into *calendars* — "Drop-in Skating",
"Drop-in Swimming", and so on. Each is a separate entry in `SOURCES`, and
each needs its own `calendar_id`.

1. Open the city's PerfectMind **start page**. It looks like:

   ```
   https://<city>.perfectmind.com/<org_path>/BookMe4?widgetId=<WIDGET_ID>
   ```

   If the schedule is embedded inside the city's own website, right-click
   the embedded schedule and choose **"Open frame in new tab"** to get the
   real address.

2. The start page lists the categories as links — "Drop-In Skating",
   "Drop-In Swimming", "Drop-In Fitness". **Click one.**

3. The address bar now reads:

   ```
   https://<city>.perfectmind.com/<org_path>/BookMe4BookingPages/Classes
     ?calendarId=<CALENDAR_ID>&widgetId=<WIDGET_ID>&embed=False
   ```

   Copy that whole URL. That single URL contains three of the four values a
   source needs:

   | Config key | Where it is in the URL |
   | --- | --- |
   | `base_url` | `https://<city>.perfectmind.com` |
   | `org_path` | everything between the domain and `BookMe4...` — copy it **exactly**, including any `/Clients` |
   | `calendar_id` | the `calendarId=` value |
   | `widget_id` | the `widgetId=` value |

4. Go back and repeat for every drop-in category you want. Skating,
   swimming, fitness and the sports/court calendars are the useful ones;
   skip registered-program calendars (lessons, camps, memberships), which
   aren't drop-ins.

That's it — a handful of copied URLs is the whole job. If you'd rather do it
in one shot, press **Ctrl+U** on the start page to view its source and copy
the whole thing; every calendar link is in there.

> Note: the `widgetId` is often the same across cities
> (`15f6af07-39c5-473e-b053-96653f77a406` is PerfectMind's stock drop-in
> widget and a lot of BC cities use it unchanged) — but not always, so copy
> it from the URL rather than assuming.

---

## Step 2b — ActiveNet: copy one JSON page

ActiveNet is filtered by *building* ("center") and *category* rather than by
calendar, and it publishes both lists as a public JSON page. One address
gives you everything.

1. Open the city's portal home page once, so the site sets its cookies:

   ```
   https://anc.ca.apm.activecommunities.com/<org_path>/home
   ```

2. Then, in the same tab, open:

   ```
   https://anc.ca.apm.activecommunities.com/<org_path>/rest/activities/filters?locale=en-US
   ```

3. You'll get a wall of JSON. Select all (**Ctrl+A**), copy (**Ctrl+C**),
   and that's what gets pasted back. Firefox shows a tidy collapsible view
   with a **Raw Data** tab — either is fine.

What's in there: a list of **centers** (the buildings, each with an `id` and
a `name`), a list of **categories**, and sometimes a list of **types**. The
building's proper name becomes `location` and its id becomes `center_id`;
the other two are the ways to narrow what gets pulled, and which one to use
depends on the city:

- If the categories are themselves drop-in — Port Coquitlam's read
  `Drop-in - Aquatics`, `Drop-in - Skating` — use those ids as
  `category_ids`.
- If the categories only name the subject — West Vancouver's read
  `Skating: Public Skate` and `Skating: Skate Lessons` side by side — look
  in **types** for `Daily Activities and Drop-Ins` and use its id as
  `type_ids` instead. That's the portal's own answer to "what can I just
  turn up to", so it stays right when the city adds a category later.

The `types` list is one of the things that comes back empty if you skipped
the home page in step 1, so if you see no types, reload and check again
before concluding the city has none.

If the page comes back empty or errors, you skipped step 1 — the endpoint
answers blank for a browser it hasn't seen before, which looks like "this
city has no programs" rather than like a failure.

Some cities sit on `anc.apm.activecommunities.com` or plain
`ca.apm.activecommunities.com` instead of `anc.ca.apm...`. If one host 404s,
try the others; whichever one loads is the `base_url`.

---

## Step 3 — coordinates for the map

`FACILITY_COORDS` in `config.py` maps a venue's name to a latitude and
longitude. It's hardcoded on purpose: the list changes about never, so
geocoding at runtime would mean a network call on every scrape to learn
something already known.

To add one: open the venue in Google Maps, right-click the building, and the
top item of the menu is `49.252663, -122.847580` — click it to copy. Use the
**building**, not the middle of a park or golf course; the marker is meant
to be where you'd actually walk in.

Missing coordinates are not an error. A venue that isn't in the table simply
gets no map pin — its sessions still show in the schedule.

---

## Step 4 — the rest of `config.py`

With the ids in hand:

- add one entry per calendar/building to `SOURCES`
- add the city to `AREAS` (this drives the "Area" filter and the map
  colours), and give the area a colour in `AREA_COLORS` in
  [`static/app.js`](../static/app.js)
- add its venues to `FACILITY_COORDS`

Neither `AREAS` nor `FACILITY_COORDS` is required for the schedule itself: a
city with no area shows only under "All areas", and a venue with no
coordinates gets no pin.

---

## The four cities being added now

Exact addresses, so there's nothing to work out:

### City of Vancouver — ActiveNet, org `vancouver`

1. <https://anc.ca.apm.activecommunities.com/vancouver/home>
2. <https://anc.ca.apm.activecommunities.com/vancouver/rest/activities/filters?locale=en-US>

(If neither loads, Vancouver also answers on
`https://ca.apm.activecommunities.com/vancouver/...` — same paths.)

### District of West Vancouver — ActiveNet, org `westvanrec`

1. <https://anc.ca.apm.activecommunities.com/westvanrec/home>
2. <https://anc.ca.apm.activecommunities.com/westvanrec/rest/activities/filters?locale=en-US>

### City of Richmond — PerfectMind, org `23650/Clients`

Start page:
<https://richmondcity.perfectmind.com/23650/Clients/BookMe4?widgetId=15f6af07-39c5-473e-b053-96653f77a406>

Click into each drop-in category and copy the address bar (Step 2a).

### North Vancouver Recreation & Culture — PerfectMind, org `23734/Clients`

NVRC runs recreation for both the City *and* the District of North
Vancouver, so it is one portal covering both. Start page:
<https://nvrc.perfectmind.com/23734/Clients/BookMe4?widgetId=191b3742-8801-4eb9-bbfa-abb28439f20c>

Click into each drop-in category and copy the address bar (Step 2a).
