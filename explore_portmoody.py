"""TEMPORARY. Identify Port Moody's live calendars and find the swims.

The crawl found four calendar ids on the city's own recreation pages, all
on the widget already in config — so the widget was never wrong and the two
ids in config are simply dead. What those four are is still unknown, and
only a "Classes" calendar is the drop-in kind this scraper reads.

This names each one and shows what it returns, and crawls one level deeper
in case the swim schedules sit on a page the first pass did not reach.

Delete once config is fixed.
"""

from __future__ import annotations

import re
from urllib.parse import urljoin

import config
import scraper_perfectmind as pm

session = pm._build_session()
HEADERS = {"User-Agent": pm.USER_AGENT}
MOODY = next(s for s in config.SOURCES if s["source_name"] == "City of Port Moody")
KNOWN = {s["calendar_id"] for s in config.SOURCES if s["source_name"] == "City of Port Moody"}

print("=== 1. CRAWL THE RECREATION SECTION FOR EVERY CALENDAR ID")
roots = [
    "https://www.portmoody.ca/parks-recreation-and-environment/recreation/",
    "https://www.portmoody.ca/parks-recreation-and-environment/recreation/recreation-guide-and-registration/",
    "https://www.portmoody.ca/parks-recreation-and-environment/facilities-fields-and-rentals/",
]
seen_pages, found = set(), {}
queue = list(roots)
while queue and len(seen_pages) < 25:
    url = queue.pop(0)
    if url in seen_pages:
        continue
    seen_pages.add(url)
    try:
        page = session.get(url, headers=HEADERS, timeout=20)
    except Exception:  # noqa: BLE001
        continue
    for cid in re.findall(r"calendarId=([0-9a-f-]{36})", page.text):
        found.setdefault(cid, url)
    if url in roots:
        for href in re.findall(r'href="([^"]+)"', page.text):
            link = urljoin(url, href.replace("&amp;", "&"))
            if link.startswith(url) and link not in seen_pages:
                queue.append(link)
print(f"    crawled {len(seen_pages)} pages, found {len(found)} calendar ids")

print("\n=== 2. WHAT EACH ONE IS, AND WHAT IT RETURNS")
for cid, where in sorted(found.items()):
    probe = {**MOODY, "calendar_id": cid}
    try:
        resp = session.get(
            f"{MOODY['base_url']}/{MOODY['org_path']}/BookMe4BookingPages/Classes"
            f"?calendarId={cid}&widgetId={MOODY['widget_id']}&embed=False",
            headers=HEADERS,
            timeout=20,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"\n    {cid}  request failed: {type(exc).__name__}")
        continue

    title = ""
    for pattern in (r"<title>\s*(.*?)\s*</title>", r'id="calendarName"[^>]*>\s*(.*?)\s*<'):
        match = re.search(pattern, resp.text, re.S | re.I)
        if match:
            title = re.sub(r"\s+", " ", match.group(1))[:70]
            break
    mark = "  <- already in config" if cid in KNOWN else ""
    print(f"\n    {cid}{mark}")
    print(f"        title: {title}")
    print(f"        found on: {where.rsplit('/', 2)[-2]}")
    if "Error Page" in resp.text:
        print("        DEAD: error page")
        continue
    try:
        events = pm.fetch_calendar_events(probe, config.SCHEDULE_WINDOW_DAYS)
    except Exception as exc:  # noqa: BLE001
        print(f"        fetch raised {type(exc).__name__}")
        continue
    print(f"        {len(events)} events in {config.SCHEDULE_WINDOW_DAYS} days")
    for ev in events[:6]:
        print(f"          {ev.date} {ev.start_time:>8}  {ev.event_name[:38]:<38} @ {ev.location[:28]}")
