"""TEMPORARY. Geocode the venues still without a pin, and check each one.

The previous pass proved a plain name search cannot be trusted: "West
Vancouver Aquatic Centre" returns Vancouver's West End aquatic centre,
confidently, four kilometres and a municipality away. So every result here
must name the municipality it is supposed to be in, and anything that does
not is reported as a miss rather than written down.

Covers the two West Vancouver venues still missing plus every venue the
newly added North Vancouver and Richmond calendars turned out to use.

Delete once the results are in config.
"""

from __future__ import annotations

import time
from urllib.parse import quote

import config
import scraper_perfectmind as pm

session = pm._build_session()

# venue -> (municipality that must appear in the result, queries to try)
WANTED = {
    "West Vancouver Aquatic Centre": (
        "West Vancouver",
        ("2121 Marine Drive, West Vancouver, BC",
         "West Vancouver Aquatic Centre, Marine Drive, West Vancouver",
         "Aquatic Centre, Ambleside, West Vancouver"),
    ),
    "West Vancouver Youth Hub": (
        "West Vancouver",
        ("Youth Hub, Marine Drive, West Vancouver, BC",
         "1750 Esquimalt Avenue, West Vancouver, BC",
         "West Vancouver Community Centre, West Vancouver, BC"),
    ),
    # North Vancouver, from the NVRC calendars now configured.
    "Karen Magnussen Community Recreation Centre": (
        "North Vancouver", ("Karen Magnussen Community Recreation Centre, North Vancouver, BC",)),
    "Harry Jerome Community Recreation Centre": (
        "North Vancouver", ("Harry Jerome Community Recreation Centre, North Vancouver, BC",)),
    "Ron Andrews Community Recreation Centre": (
        "North Vancouver", ("Ron Andrews Community Recreation Centre, North Vancouver, BC",)),
    "Delbrook Community Recreation Centre": (
        "North Vancouver", ("Delbrook Community Recreation Centre, North Vancouver, BC",)),
    "Lynn Creek Community Recreation Centre": (
        "North Vancouver", ("Lynn Creek Community Recreation Centre, North Vancouver, BC",)),
    "Parkgate Community Centre": (
        "North Vancouver", ("Parkgate Community Centre, North Vancouver, BC",)),
    "Lions Gate Community Recreation Centre": (
        "North Vancouver", ("Lions Gate Community Recreation Centre, North Vancouver, BC",)),
    "John Braithwaite Community Centre": (
        "North Vancouver", ("John Braithwaite Community Centre, North Vancouver, BC",)),
    # Richmond.
    "Richmond Ice Centre": ("Richmond", ("Richmond Ice Centre, Richmond, BC",)),
    "Minoru Arenas": (
        "Richmond", ("Minoru Arenas, Richmond, BC", "Minoru Centre for Active Living, Richmond, BC")),
}

print("Every result must name its own municipality. Anything else is a miss.\n")
good, missed = [], []
for venue, (municipality, queries) in WANTED.items():
    for query in queries:
        try:
            resp = session.get(
                "https://nominatim.openstreetmap.org/search"
                f"?q={quote(query)}&format=json&limit=3&countrycodes=ca"
                "&addressdetails=1",
                headers={"User-Agent": pm.USER_AGENT, "Accept": "application/json"},
                timeout=25,
            )
            hits = resp.json()
        except Exception as exc:  # noqa: BLE001
            time.sleep(1.1)
            continue
        time.sleep(1.1)
        for hit in hits:
            name = hit.get("display_name", "")
            address = hit.get("address") or {}
            place = " ".join(
                str(address.get(k, ""))
                for k in ("city", "town", "village", "municipality", "suburb", "county")
            )
            if municipality.casefold() not in (name + " " + place).casefold():
                print(f"    {venue}: rejected {name[:64]!r} (not in {municipality})")
                continue
            good.append((venue, float(hit["lat"]), float(hit["lon"]), name))
            break
        else:
            continue
        break
    else:
        missed.append(venue)

print("\n=== CONFIRMED (the result names the right municipality)")
for venue, lat, lon, name in good:
    print(f'    "{venue}": ({lat:.6f}, {lon:.6f}),')
    print(f"        # {name[:92]}")

print("\n=== STILL MISSING")
for venue in missed:
    print(f"    {venue}")
if not missed:
    print("    none")
