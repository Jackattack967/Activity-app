"""TEMPORARY. Map the last venues, and say which city each belongs to.

check_sources.py's new venue report turned up four buildings nobody had
mapped, including one in Vancouver that the coordinate table missed
entirely. Two of them — "Canlan Sports", "Civic Centre" — are too generic
to look up without knowing whose they are, so this says which source each
came from before trying.

Same rule as before: a result must name its own municipality *and* its own
venue, because a municipality check alone let an apartment block through.

Delete once the results are in config.
"""

from __future__ import annotations

import collections
import time
from urllib.parse import quote

import config
import scraper
import scraper_perfectmind as pm

session = pm._build_session()
TARGETS = {"Canlan Sports", "Civic Centre", "Kerrisdale Pool",
           "Lynn Creek Community Recreation Centre"}

print("=== 1. WHICH SOURCE EACH UNMAPPED VENUE CAME FROM")
events, _ = scraper.fetch_all_events(config.SOURCES, config.SCHEDULE_WINDOW_DAYS)
owners = collections.defaultdict(collections.Counter)
for ev in events:
    if ev.location in TARGETS:
        owners[ev.location][ev.source_name] += 1
for venue in sorted(TARGETS):
    who = owners.get(venue)
    print(f"    {venue}: {dict(who) if who else 'not seen this run'}")

CITY = {
    "City of Vancouver": "Vancouver",
    "City of Richmond": "Richmond",
    "North Vancouver Recreation & Culture": "North Vancouver",
    "District of West Vancouver": "West Vancouver",
    "City of Burnaby": "Burnaby",
    "City of Coquitlam": "Coquitlam",
    "City of Port Coquitlam": "Port Coquitlam",
    "City of Port Moody": "Port Moody",
    "City of New Westminster": "New Westminster",
}

print("\n=== 2. LOOKED UP IN THE CITY THAT OWNS THEM")
for venue in sorted(TARGETS):
    who = owners.get(venue)
    if not who:
        print(f"\n    {venue}: skipped, no owning source seen")
        continue
    municipality = CITY.get(who.most_common(1)[0][0], "")
    print(f"\n    {venue}  ({municipality})")
    for query in (
        f"{venue}, {municipality}, BC",
        f"{venue}, {municipality}, British Columbia, Canada",
    ):
        try:
            resp = session.get(
                "https://nominatim.openstreetmap.org/search"
                f"?q={quote(query)}&format=json&limit=3&countrycodes=ca",
                headers={"User-Agent": pm.USER_AGENT, "Accept": "application/json"},
                timeout=25,
            )
            hits = resp.json()
        except Exception as exc:  # noqa: BLE001
            print(f"        {query!r}: failed ({type(exc).__name__})")
            time.sleep(1.1)
            continue
        time.sleep(1.1)
        for hit in hits:
            name = hit.get("display_name", "")
            first = name.split(",")[0].strip().casefold()
            # Must name the venue itself, not just land in the right city.
            venue_words = {w for w in venue.casefold().split() if len(w) > 3}
            if not venue_words & set(first.replace("-", " ").split()):
                print(f"        rejected {name[:66]!r} (does not name the venue)")
                continue
            if municipality.casefold() not in name.casefold():
                print(f"        rejected {name[:66]!r} (wrong municipality)")
                continue
            print(f'        "{venue}": ({float(hit["lat"]):.6f}, {float(hit["lon"]):.6f}),')
            print(f"            # {name[:88]}")
            break
        else:
            continue
        break
    else:
        print("        no acceptable match")
