"""TEMPORARY. Recover Port Moody's current public-swim calendar ids.

Established: the two ids in config return an identical 15,116-byte error
page while working calendars return ~31,800 bytes, so those calendars are
gone rather than empty. What is not yet known is what replaced them.

The widget's landing page yielded no calendarId links to the first pass, so
this looks at what it actually contains.

Delete once the ids are fixed.
"""

from __future__ import annotations

import re

import config
import scraper_perfectmind as pm

MOODY = next(s for s in config.SOURCES if s["source_name"] == "City of Port Moody")
session = pm._build_session()
HEADERS = {"User-Agent": pm.USER_AGENT}

print("=== 1. WHAT THE ERROR PAGE ACTUALLY SAYS")
dead = next(
    s
    for s in config.SOURCES
    if s.get("calendar_label") == "Public Swim - Rocky Point"
)
resp = session.get(
    f"{dead['base_url']}/{dead['org_path']}/BookMe4BookingPages/Classes"
    f"?calendarId={dead['calendar_id']}&widgetId={dead['widget_id']}&embed=False",
    headers=HEADERS,
    timeout=20,
)
text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", resp.text, flags=re.S | re.I)
text = re.sub(r"<[^>]+>", " ", text)
text = re.sub(r"\s+", " ", text).strip()
print(f"    {text[:600]}")

print("\n=== 2. EVERY GUID ON THE WIDGET LANDING PAGE, WITH ITS LABEL")
resp = session.get(
    f"{MOODY['base_url']}/{MOODY['org_path']}/BookMe4?widgetId={MOODY['widget_id']}",
    headers=HEADERS,
    timeout=20,
)
print(f"    landing page HTTP {resp.status_code}, {len(resp.text)} bytes")
guids = {}
for match in re.finditer(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", resp.text):
    guid = match.group(0)
    if guid in guids:
        continue
    window = resp.text[max(0, match.start() - 300) : match.start() + 300]
    labels = [
        n.strip()
        for n in re.findall(r">\s*([A-Za-z][^<>{}]{3,60}?)\s*<", window)
        if n.strip() and not n.strip().startswith(("var ", "function"))
    ]
    guids[guid] = labels[:3]
for guid, labels in guids.items():
    marker = " <- in config" if any(
        guid == s.get("calendar_id") or guid == s.get("widget_id")
        for s in config.SOURCES
    ) else ""
    print(f"    {guid}{marker}")
    for label in labels:
        print(f"        {label[:70]}")
print(f"    ({len(guids)} distinct GUIDs)")

print("\n=== 3. ANY 'SWIM' TEXT ON THE LANDING PAGE")
for match in re.finditer(r"[Ss]wim[A-Za-z ]{0,40}", resp.text):
    snippet = match.group(0).strip()
    if len(snippet) > 4:
        print(f"    {snippet[:70]}")
