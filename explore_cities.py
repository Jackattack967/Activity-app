"""TEMPORARY. Pair NVRC's calendars with their widgets, and finish the map.

Two gaps from the last run.

NVRC publishes seven widgets, and the probe tried every calendar against
one of them, so eleven of fourteen came back as error pages. A BookMe4 URL
carries both ids together, so they are collected as pairs here; any
calendar seen without a widget is tried against all seven.

Four venues did not resolve on OpenStreetMap under the names this app uses
for them. Those names were chosen to read well on a dashboard spanning
seven cities, not to match a map, so the fallback is the name the portal
itself uses plus the street the city publishes.

Delete once both have landed in config.
"""

from __future__ import annotations

import re
import time
from urllib.parse import quote, urljoin

import config
import scraper_perfectmind as pm

session = pm._build_session()
HEADERS = {"User-Agent": pm.USER_AGENT}

NVRC = ("https://nvrc.perfectmind.com", "23734/Clients")
ROOTS = (
    "https://www.nvrc.ca/drop-in-schedules",
    "https://www.nvrc.ca/",
    "https://www.nvrc.ca/swimming",
    "https://www.nvrc.ca/skating",
    "https://www.nvrc.ca/fitness",
    "https://www.nvrc.ca/sports",
)


def live(text: str) -> bool:
    return len(text) > 20000 and bool(pm.TOKEN_TAG_RE.search(text)) and "Error Page" not in text


print("=== 1. NVRC: CALENDARS PAIRED WITH THE WIDGET THEY BELONG TO")
pairs, lone_calendars, widgets, pages = set(), set(), set(), set()
queue = list(ROOTS)
while queue and len(pages) < 30:
    url = queue.pop(0)
    if url in pages:
        continue
    pages.add(url)
    try:
        page = session.get(url, headers=HEADERS, timeout=20)
    except Exception:  # noqa: BLE001
        continue
    text = page.text.replace("&amp;", "&")
    # Both orders appear in the wild.
    for cid, wid in re.findall(r"calendarId=([0-9a-f-]{36})&widgetId=([0-9a-f-]{36})", text):
        pairs.add((cid, wid))
    for wid, cid in re.findall(r"widgetId=([0-9a-f-]{36})&calendarId=([0-9a-f-]{36})", text):
        pairs.add((cid, wid))
    lone_calendars.update(re.findall(r"calendarId=([0-9a-f-]{36})", text))
    widgets.update(re.findall(r"widgetId=([0-9a-f-]{36})", text))
    if url in ROOTS:
        for href in re.findall(r'href="([^"]+)"', page.text):
            link = urljoin(url, href.replace("&amp;", "&"))
            if link.startswith("https://www.nvrc.ca") and re.search(
                r"drop.?in|schedule|swim|skat|fitness|gym|sport", link, re.I
            ):
                queue.append(link)

lone_calendars -= {cid for cid, _ in pairs}
candidates = sorted(pairs) + [(cid, wid) for cid in sorted(lone_calendars) for wid in sorted(widgets)]
print(f"    {len(pages)} pages, {len(pairs)} paired, {len(lone_calendars)} unpaired "
      f"x {len(widgets)} widgets = {len(candidates)} combinations")

seen_live = {}
for cid, wid in candidates:
    if cid in seen_live:
        continue
    source = {
        "source_name": "North Vancouver Recreation & Culture",
        "base_url": NVRC[0], "org_path": NVRC[1],
        "widget_id": wid, "calendar_id": cid,
        "calendar_label": "probe", "activity_type": "Other",
    }
    try:
        resp = session.get(
            f"{NVRC[0]}/{NVRC[1]}/BookMe4BookingPages/Classes"
            f"?calendarId={cid}&widgetId={wid}&embed=False",
            headers=HEADERS, timeout=15,
        )
    except Exception:  # noqa: BLE001
        continue
    if not live(resp.text):
        continue
    title = ""
    match = re.search(r"<title>\s*(.*?)\s*</title>", resp.text, re.S | re.I)
    if match:
        title = re.sub(r"\s+", " ", match.group(1))[:60]
    try:
        events = pm.fetch_calendar_events(source, config.SCHEDULE_WINDOW_DAYS)
    except Exception as exc:  # noqa: BLE001
        print(f"\n    {cid} / {wid}\n        {title}\n        fetch raised {type(exc).__name__}")
        continue
    seen_live[cid] = True
    print(f"\n    calendar {cid}\n    widget   {wid}")
    print(f"        {title}  -> {len(events)} events")
    for ev in events[:4]:
        print(f"          {ev.date} {ev.start_time:>8}  {ev.event_name[:34]:<34} @ {ev.location[:30]}")

print("\n=== 2. THE FOUR VENUES OPENSTREETMAP DID NOT RECOGNISE")
ATTEMPTS = {
    "West Vancouver Aquatic Centre": (
        "West Vancouver Aquatic Centre", "Aquatic Centre, West Vancouver, BC",
        "2121 Marine Drive, West Vancouver, BC",
    ),
    "West Vancouver Ice Arena": (
        "West Vancouver Ice Arena", "Ice Arena, West Vancouver, BC",
        "786 22nd Street, West Vancouver, BC",
    ),
    "West Vancouver Seniors' Activity Centre": (
        "West Vancouver Seniors Activity Centre",
        "Seniors Activity Centre, West Vancouver, BC",
        "695 21st Street, West Vancouver, BC",
    ),
    "West Vancouver Youth Hub": (
        "West Vancouver Youth Hub", "Youth Hub, West Vancouver, BC",
        "Gleneagles Community Centre, West Vancouver, BC",
    ),
}
for venue, queries in ATTEMPTS.items():
    print(f"\n    {venue}")
    for query in queries:
        try:
            resp = session.get(
                "https://nominatim.openstreetmap.org/search"
                f"?q={quote(query)}&format=json&limit=1&countrycodes=ca",
                headers={"User-Agent": pm.USER_AGENT, "Accept": "application/json"},
                timeout=25,
            )
            hits = resp.json()
        except Exception as exc:  # noqa: BLE001
            print(f"        {query!r}: failed ({type(exc).__name__})")
            time.sleep(1.1)
            continue
        if hits:
            hit = hits[0]
            print(f'        via {query!r}:')
            print(f'        "{venue}": ({float(hit["lat"]):.6f}, {float(hit["lon"]):.6f}),')
            print(f'            # {hit.get("display_name", "")[:88]}')
            time.sleep(1.1)
            break
        print(f"        {query!r}: no match")
        time.sleep(1.1)
    else:
        print("        still nothing — this one needs a human with a map")
