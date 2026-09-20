"""TEMPORARY. Why do Port Moody's two public-swim calendars fail?

They have been returning zero sessions in every live check, and have now
started raising instead. Both look like a calendar_id that no longer
resolves, but "temporarily unavailable" is deliberately vague on the
dashboard, so this asks what actually happens.

Delete once they are fixed.
"""

from __future__ import annotations

import config
import scraper_perfectmind as pm

SUSPECT = ("Public Swim - Rocky Point", "Public Swim - Westhill Pool")

for source in config.SOURCES:
    label = source.get("calendar_label", "")
    if source.get("source_name") != "City of Port Moody":
        continue
    print(f"\n=== {label}")
    print(f"    calendar_id {source['calendar_id']}")
    session = pm._build_session()
    url = (
        f"{source['base_url']}/{source['org_path']}/BookMe4BookingPages/Classes"
        f"?calendarId={source['calendar_id']}&widgetId={source['widget_id']}&embed=False"
    )
    try:
        resp = session.get(url, headers={"User-Agent": pm.USER_AGENT}, timeout=20)
        print(f"    page HTTP {resp.status_code}, {len(resp.text)} bytes")
        has_token = bool(pm.TOKEN_TAG_RE.search(resp.text))
        print(f"    anti-forgery token present: {has_token}")
        # The portal answers 200 with an error page for a calendar that has
        # been deleted, so the status code alone proves nothing.
        for needle in ("not found", "no longer", "error", "does not exist", "invalid"):
            if needle in resp.text.casefold():
                print(f"    page text mentions {needle!r}")
    except Exception as exc:  # noqa: BLE001
        print(f"    page request failed: {type(exc).__name__}: {exc}")
        continue

    try:
        events = pm.fetch_calendar_events(source, config.SCHEDULE_WINDOW_DAYS)
        print(f"    fetch returned {len(events)} events")
    except Exception as exc:  # noqa: BLE001
        print(f"    fetch raised {type(exc).__name__}: {exc}")

# What calendars does the widget itself still advertise? If the two above
# are gone from here, the ids in config are simply stale.
print("\n=== calendars the Port Moody widget still lists")
moody = next(s for s in config.SOURCES if s["source_name"] == "City of Port Moody")
session = pm._build_session()
resp = session.get(
    f"{moody['base_url']}/{moody['org_path']}/BookMe4?widgetId={moody['widget_id']}",
    headers={"User-Agent": pm.USER_AGENT},
    timeout=20,
)
print(f"    landing page HTTP {resp.status_code}")
import re

seen = set()
for match in re.finditer(r"calendarId=([0-9a-f-]{36})[^\"'>]*", resp.text):
    cid = match.group(1)
    if cid in seen:
        continue
    seen.add(cid)
    window = resp.text[max(0, match.start() - 400) : match.start() + 400]
    names = re.findall(r">([^<>{}]{4,60})<", window)
    label = next((n.strip() for n in names if n.strip() and "\n" not in n), "?")
    print(f"    {cid}  {label[:56]}")
print(f"    ({len(seen)} calendars advertised)")
