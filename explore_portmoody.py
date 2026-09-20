"""TEMPORARY. Find which widget may still show Port Moody's public swims.

The error is explicit: "Calendar is not allowed for the widget." So the
calendar is not necessarily gone — the widget in config is no longer
permitted to render it. Port Moody's landing page for that widget mentions
"swim" nowhere, which fits.

Two ways to find where it went, both cheap:
  1. That landing page carries 33 GUIDs. Some are widget ids. Try each as
     a widget for the swim calendar and see which renders.
  2. Read Port Moody's own website and take whatever PerfectMind links it
     publishes today, which is what a visitor would follow.

Delete once the ids are fixed.
"""

from __future__ import annotations

import re

import config
import scraper_perfectmind as pm

session = pm._build_session()
HEADERS = {"User-Agent": pm.USER_AGENT}
MOODY = next(s for s in config.SOURCES if s["source_name"] == "City of Port Moody")
ROCKY = next(
    s for s in config.SOURCES if s.get("calendar_label") == "Public Swim - Rocky Point"
)
ERROR_MARKER = "not allowed for the widget"

print("=== 1. IS THERE A WIDGET THAT STILL RENDERS THE SWIM CALENDAR?")
resp = session.get(
    f"{MOODY['base_url']}/{MOODY['org_path']}/BookMe4?widgetId={MOODY['widget_id']}",
    headers=HEADERS,
    timeout=20,
)
guids = sorted(
    set(
        re.findall(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", resp.text
        )
    )
)
guids = [g for g in guids if g != "00000000-0000-0000-0000-000000000000"]
print(f"    trying {len(guids)} candidate widget ids against the Rocky Point calendar")
for guid in guids:
    try:
        probe = session.get(
            f"{ROCKY['base_url']}/{ROCKY['org_path']}/BookMe4BookingPages/Classes"
            f"?calendarId={ROCKY['calendar_id']}&widgetId={guid}&embed=False",
            headers=HEADERS,
            timeout=15,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"    {guid}  request failed: {type(exc).__name__}")
        continue
    if ERROR_MARKER in probe.text:
        continue  # the same refusal; not it
    print(f"    {guid}  -> {len(probe.text)} bytes, NO refusal. Candidate.")
print("    (done; silence above means every candidate was refused too)")

print("\n=== 2. WHAT PORT MOODY'S OWN SITE LINKS TO TODAY")
PAGES = (
    "https://www.portmoody.ca/en/parks-and-recreation/drop-in-schedules.aspx",
    "https://www.portmoody.ca/en/parks-and-recreation/swimming.aspx",
    "https://www.portmoody.ca/en/parks-and-recreation/recreation-schedules.aspx",
    "https://www.portmoody.ca/en/parks-and-recreation/arenas-and-pools.aspx",
    "https://www.portmoody.ca/en/parks-and-recreation.aspx",
)
found = {}
for url in PAGES:
    try:
        page = session.get(url, headers=HEADERS, timeout=20)
    except Exception as exc:  # noqa: BLE001
        print(f"    {url} -> {type(exc).__name__}")
        continue
    hits = re.findall(r"https?://[^\"'\s<>]*perfectmind[^\"'\s<>]*", page.text)
    print(f"    {url} -> HTTP {page.status_code}, {len(hits)} PerfectMind link(s)")
    for hit in hits:
        found.setdefault(hit, url)

for link in sorted(found):
    print(f"\n    {link}")
    cal = re.search(r"calendarId=([0-9a-f-]{36})", link)
    wid = re.search(r"widgetId=([0-9a-f-]{36})", link)
    if cal:
        print(f"        calendarId {cal.group(1)}")
    if wid:
        print(f"        widgetId   {wid.group(1)}")
