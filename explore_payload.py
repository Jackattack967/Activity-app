"""TEMPORARY. Measure what the dashboard actually ships to a browser.

The schedule is inlined into index.html as JSON. Nine cities and a
fortnight later, nobody has measured it, and the fix differs depending on
the answer: if the bulk is one fat field, drop that field; if it is spread
evenly, the page has to load in two stages; and if compression alone takes
care of it, do that first and leave the shape alone.

Delete once the payload change is made.
"""

from __future__ import annotations

import dataclasses
import gzip
import json

import config
import scraper

events, errors = scraper.fetch_all_events(config.SOURCES, config.SCHEDULE_WINDOW_DAYS)
rows = [dataclasses.asdict(e) for e in events]
# What app.py adds before the template sees it.
for row in rows:
    lat, lng = config.FACILITY_COORDS.get(row.get("location") or "", (None, None))
    row.update(lat=lat, lng=lng, area=config.CITY_AREAS.get(row.get("source_name") or "", ""))

def size(obj) -> int:
    return len(json.dumps(obj, separators=(",", ":")).encode())

def gz(obj) -> int:
    return len(gzip.compress(json.dumps(obj, separators=(",", ":")).encode(), 6))

total, total_gz = size(rows), gz(rows)
print(f"{len(rows)} sessions, {len(errors)} source error(s)\n")
print(f"  inlined JSON        {total:>9,} bytes   ({total/1024/1024:.2f} MB)")
print(f"  the same, gzipped   {total_gz:>9,} bytes   ({total_gz/1024:.0f} KB)")
print(f"  compression ratio   {total/max(total_gz,1):>9.1f}x\n")

print("  Bytes by field, largest first:")
fields = sorted(rows[0], key=lambda f: -sum(len(str(r.get(f) or "")) for r in rows))
for field in fields:
    used = sum(len(str(r.get(f := field) or "")) for r in rows)
    filled = sum(1 for r in rows if r.get(field))
    print(f"    {field:<16} {used:>9,}  {used/total:>5.1%}   set on {filled/len(rows):>4.0%} of rows")

without_details = [{k: v for k, v in r.items() if k != "details"} for r in rows]
print(f"\n  without `details`   {size(without_details):>9,} bytes "
      f"({size(without_details)/total:.0%} of the whole), "
      f"gzipped {gz(without_details):,}")

dates = sorted({r["date"] for r in rows if r["date"]})
for days in (1, 2, 3):
    window = set(dates[:days])
    subset = [r for r in rows if r["date"] in window]
    print(f"  first {days} day(s)      {size(subset):>9,} bytes, {len(subset)} sessions")

lengths = sorted(len(r.get("details") or "") for r in rows)
if lengths:
    print(f"\n  `details` length: median {lengths[len(lengths)//2]}, "
          f"max {lengths[-1]}, empty on "
          f"{sum(1 for n in lengths if n == 0)/len(lengths):.0%} of rows")
