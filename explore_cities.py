"""TEMPORARY. Collect what is still missing, without anyone clicking.

Two jobs that were going to be asked of a person, both of which CI can do
because it has the internet access this repo's sandbox does not:

  1. Richmond's and NVRC's drop-in calendar ids, by crawling the cities'
     own websites — the trick that worked on Port Moody, which turned up
     27 calendars including three nobody knew about.
  2. Coordinates for the venues with no map pin, from OpenStreetMap, which
     is where every coordinate already in config.py came from.

Delete once both have landed in config.
"""

from __future__ import annotations

import json
import re
import time
from urllib.parse import quote, urljoin

import config
import scraper_perfectmind as pm

session = pm._build_session()
HEADERS = {"User-Agent": pm.USER_AGENT}

CITIES = (
    (
        "City of Richmond",
        "https://richmondcity.perfectmind.com",
        "23650/Clients",
        "15f6af07-39c5-473e-b053-96653f77a406",
        ("https://www.richmond.ca/parks-recreation/about/schedules.htm",
         "https://www.richmond.ca/parks-recreation/registration.htm",
         "https://www.richmond.ca/parks-recreation.htm"),
    ),
    (
        "North Vancouver Recreation & Culture",
        "https://nvrc.perfectmind.com",
        "23734/Clients",
        "191b3742-8801-4eb9-bbfa-abb28439f20c",
        ("https://www.nvrc.ca/drop-in-schedules",
         "https://www.nvrc.ca/",
         "https://www.nvrc.ca/swimming",
         "https://www.nvrc.ca/skating"),
    ),
)


def looks_like_a_calendar(text: str) -> bool:
    return len(text) > 20000 and bool(pm.TOKEN_TAG_RE.search(text)) and "Error Page" not in text


for name, base_url, org_path, widget_id, roots in CITIES:
    print(f"\n{'=' * 72}\n{name}\n{'=' * 72}")
    pages, found = set(), {}
    queue = list(roots)
    while queue and len(pages) < 30:
        url = queue.pop(0)
        if url in pages:
            continue
        pages.add(url)
        try:
            page = session.get(url, headers=HEADERS, timeout=20)
        except Exception:  # noqa: BLE001
            continue
        for cid in re.findall(r"calendarId=([0-9a-f-]{36})", page.text):
            found.setdefault(cid, url)
        # Widget ids the city publishes may differ from the guess above.
        for wid in set(re.findall(r"widgetId=([0-9a-f-]{36})", page.text)):
            found.setdefault(f"widget:{wid}", url)
        if url in roots:
            for href in re.findall(r'href="([^"]+)"', page.text):
                link = urljoin(url, href.replace("&amp;", "&"))
                if re.search(r"drop.?in|schedule|swim|skat|fitness|recreation", link, re.I):
                    if link.startswith(("https://www.richmond.ca", "https://www.nvrc.ca")):
                        queue.append(link)
    widgets = {k.split(":", 1)[1] for k in found if k.startswith("widget:")}
    calendars = {k: v for k, v in found.items() if not k.startswith("widget:")}
    print(f"  crawled {len(pages)} pages; {len(calendars)} calendar ids, "
          f"{len(widgets)} widget ids")
    for wid in sorted(widgets):
        print(f"    widgetId {wid}{'  (the one assumed)' if wid == widget_id else ''}")

    for cid, where in sorted(calendars.items()):
        source = {
            "source_name": name,
            "base_url": base_url,
            "org_path": org_path,
            "widget_id": widget_id,
            "calendar_id": cid,
            "calendar_label": "probe",
            "activity_type": "Other",
        }
        try:
            resp = session.get(
                f"{base_url}/{org_path}/BookMe4BookingPages/Classes"
                f"?calendarId={cid}&widgetId={widget_id}&embed=False",
                headers=HEADERS,
                timeout=20,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"\n    {cid}  request failed: {type(exc).__name__}")
            continue
        title = ""
        match = re.search(r"<title>\s*(.*?)\s*</title>", resp.text, re.S | re.I)
        if match:
            title = re.sub(r"\s+", " ", match.group(1))[:66]
        print(f"\n    {cid}\n        title: {title}")
        if not looks_like_a_calendar(resp.text):
            print(f"        not a live calendar ({len(resp.text)} bytes)")
            continue
        try:
            events = pm.fetch_calendar_events(source, config.SCHEDULE_WINDOW_DAYS)
        except Exception as exc:  # noqa: BLE001
            print(f"        fetch raised {type(exc).__name__}")
            continue
        print(f"        {len(events)} events")
        for ev in events[:5]:
            print(f"          {ev.date} {ev.start_time:>8}  "
                  f"{ev.event_name[:34]:<34} @ {ev.location[:30]}")

print(f"\n{'=' * 72}\nCOORDINATES FOR THE VENUES WITH NO PIN\n{'=' * 72}")
# OpenStreetMap's own geocoder, which is where every coordinate already in
# config.py came from. Its usage policy asks for an identifying User-Agent
# and no more than one request a second; both are honoured here, and this
# runs once rather than on any schedule.
NEEDED = sorted(config.VENUES_AWAITING_COORDS) + ["Kyle Centre, Port Moody"]
for venue in NEEDED:
    query = venue if "," in venue else f"{venue}, British Columbia, Canada"
    try:
        resp = session.get(
            "https://nominatim.openstreetmap.org/search"
            f"?q={quote(query)}&format=json&limit=1&countrycodes=ca",
            headers={"User-Agent": pm.USER_AGENT, "Accept": "application/json"},
            timeout=25,
        )
        hits = resp.json()
    except Exception as exc:  # noqa: BLE001
        print(f'    "{venue}": lookup failed ({type(exc).__name__})')
        time.sleep(1.1)
        continue
    if not hits:
        print(f'    "{venue}": NOT FOUND — needs doing by hand')
    else:
        hit = hits[0]
        print(f'    "{venue}": ({float(hit["lat"]):.6f}, {float(hit["lon"]):.6f}),')
        print(f'        # {hit.get("display_name", "")[:90]}')
    time.sleep(1.1)
