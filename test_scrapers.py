"""Exercise the multi-platform scraper layer.

Run with:  .venv\\Scripts\\python.exe test_scrapers.py
Exits non-zero if anything fails.

Everything here is offline. The ActiveNet cases feed captured API rows
through the same normalisation the live scraper uses, so the parsing that
turns a portal's wording into an Event can be checked without hitting a
city's servers or depending on what happens to be scheduled today.
"""
import datetime as dt
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
import scraper
import scraper_activenet as an

FAIL = []


def check(label, got, want):
    ok = got == want
    print(f"  {'PASS' if ok else 'FAIL'}  {label}: got {got!r}, want {want!r}")
    if not ok:
        FAIL.append(label)


print("\n1. EVERY CONFIGURED SOURCE ROUTES TO A REAL SCRAPER")
for source in config.SOURCES:
    label = f"{source['source_name']} / {source['calendar_label']}"
    try:
        module = scraper._module_for(source)
        ok = hasattr(module, "fetch_calendar_events") and hasattr(module, "build_login_url")
    except Exception as exc:  # noqa: BLE001 - the point is to report it
        ok = f"raised {exc}"
    check(f"routes: {label}", ok, True)

check(
    "a source with no platform is PerfectMind",
    scraper._module_for({"source_name": "x", "calendar_label": "y"}).__name__,
    "scraper_perfectmind",
)

print("\n2. AN UNKNOWN PLATFORM FAILS LOUDLY, NOT SILENTLY")
# A typo in config.py must not mean a city quietly disappears from the site.
try:
    scraper._module_for({"platform": "rectrac", "source_name": "x", "calendar_label": "y"})
    check("unknown platform raises", False, True)
except ValueError as exc:
    check("unknown platform raises ValueError", True, True)
    check("names the bad platform", "rectrac" in str(exc), True)
    check("lists the known ones", "perfectmind" in str(exc), True)

print("\n3. TIMES ARRIVE IN THE FORMAT THE FRONT END PARSES")
# app.js reads times with /^(\d{1,2}):(\d{2})\s*(AM|PM)$/. Anything else is
# treated as unparseable, which silently hides a session as "finished".
for text, want in [
    ("8:30 AM", "8:30 AM"),
    ("12:45 PM", "12:45 PM"),
    ("Noon", "12:00 PM"),
    ("noon", "12:00 PM"),
    ("Midnight", "12:00 AM"),
    ("9 AM", "9:00 AM"),
    ("10:05 p.m.", "10:05 PM"),
]:
    check(f"time {text!r}", an._parse_time(text), want)

check("range with a dash", an._split_time_range("9:00 AM - Noon"), ("9:00 AM", "12:00 PM"))
check("range with 'to'", an._split_time_range("1:00 PM to 2:30 PM"), ("1:00 PM", "2:30 PM"))
check("range with no end", an._split_time_range("7:00 AM"), ("7:00 AM", ""))

print("\n4. OPENINGS ARE PHRASED THE WAY badgeInfo() READS THEM")
# badgeInfo in app.js decides open-vs-full from the words "full" / "spot".
check("zero openings", an._spots_and_status({"openings": "0"}), ("Full", "Full"))
check("one opening", an._spots_and_status({"openings": "1"}), ("1 spot left", "Register"))
check("many openings", an._spots_and_status({"openings": "19"}), ("19 spots left", "Register"))
check("negative treated as full", an._spots_and_status({"openings": "-2"}), ("Full", "Full"))
check("non-numeric passes through", an._spots_and_status({"openings": "Closed"}), ("Closed", "Closed"))
check("missing openings", an._spots_and_status({}), ("", ""))

print("\n5. OCCURRENCE DATES")
start = dt.date(2026, 9, 5)
window_end = start + dt.timedelta(days=14)

check(
    "single-day activity is one occurrence",
    an._occurrence_dates(
        {"date_range_start": "2026-09-05", "date_range_end": "", "days_of_week": "Sat"},
        start,
        window_end,
    ),
    [dt.date(2026, 9, 5)],
)
check(
    "a weekly activity expands across the window",
    an._occurrence_dates(
        {
            "date_range_start": "2026-09-01",
            "date_range_end": "2026-12-01",
            "days_of_week": "Tue",
        },
        start,
        window_end,
    ),
    [dt.date(2026, 9, 8), dt.date(2026, 9, 15)],
)
check(
    "two weekdays expand to both",
    len(
        an._occurrence_dates(
            {
                "date_range_start": "2026-09-01",
                "date_range_end": "2026-12-01",
                "days_of_week": "Mon, Wed",
            },
            start,
            window_end,
        )
    ),
    4,
)
check(
    "an activity that ended before the window is dropped",
    an._occurrence_dates(
        {"date_range_start": "2026-01-01", "date_range_end": "2026-02-01", "days_of_week": "Tue"},
        start,
        window_end,
    ),
    [],
)
check(
    "a range with no recognisable weekday yields nothing",
    an._occurrence_dates(
        {"date_range_start": "2026-09-01", "date_range_end": "2026-12-01", "days_of_week": ""},
        start,
        window_end,
    ),
    [],
)
check(
    "a missing start date is survivable",
    an._occurrence_dates({"date_range_start": "", "days_of_week": "Tue"}, start, window_end),
    [],
)
check(
    "a malformed date is survivable",
    an._occurrence_dates(
        {"date_range_start": "not-a-date", "days_of_week": "Tue"}, start, window_end
    ),
    [],
)

print("\n6. A ROW BECOMES AN EVENT THE REST OF THE APP UNDERSTANDS")
SOURCE = {
    "source_name": "City of Port Coquitlam",
    "platform": "activenet",
    "location": "Port Coquitlam Community Centre",
    "center_aliases": ("Port Coquitlam Cmty Centre",),
    "calendar_label": "Drop-in",
    "activity_type": "Other",
}
row = {
    "name": "Badminton All Levels Drop-in",
    "category": "Drop-in - Sport",
    "time_range": "8:30 AM - 10:30 AM",
    "openings": "4",
    "number": "119969",
    "desc": "<p>All levels welcome.</p>",
    "detail_url": "https://example.invalid/activity/1",
    "location": {"label": "Gymnasium 2"},
}
ev = an._normalize(row, SOURCE, dt.date(2026, 9, 5))
check("name", ev.event_name, "Badminton All Levels Drop-in")
# The sport comes from the title, not from the calendar's broad category.
check("activity type from the name", ev.activity_type, "Badminton")
check("date", ev.date, "2026-09-05")
check("day of week", ev.day_of_week, "Saturday")
check("start", ev.start_time, "8:30 AM")
check("end", ev.end_time, "10:30 AM")
check("spots", ev.spots, "4 spots left")
check("building", ev.location, "Port Coquitlam Community Centre")
check("room", ev.facility, "Gymnasium 2")
check("course id", ev.course_id, "119969")
check("html stripped from details", ev.details, "All levels welcome.")
check("no waitlist claimed", ev.has_waitlist, False)

print("\n7. THE BUILDING'S OWN NAME IS NOT REPEATED AS A ROOM")
# The portal labels most rows with an abbreviated form of the building.
# Showing that under a heading spelling it out in full looks like a bug.
for label in ["Port Coquitlam Cmty Centre", "Port Coquitlam Community Centre", "  port coquitlam cmty centre  "]:
    ev = an._normalize({**row, "location": {"label": label}}, SOURCE, dt.date(2026, 9, 5))
    check(f"{label.strip()!r} collapses to the building", ev.facility, "Port Coquitlam Community Centre")

ev = an._normalize(
    {**row, "location": {"label": "Program Location: Arena 3 (Purple)"}},
    SOURCE,
    dt.date(2026, 9, 5),
)
check("internal 'Program Location:' prefix dropped", ev.facility, "Arena 3 (Purple)")

print("\n8. CATEGORY FALLBACKS")
# Only used when the title names no specific sport.
for category, want in [
    ("Drop-in - Skating", "Skating"),
    ("Drop-in - Aquatics", "Swimming"),
    ("Drop-in - Fitness", "Fitness"),
    ("Drop-in - Seniors", "Adult"),
]:
    ev = an._normalize(
        {**row, "name": "Open Session", "category": category}, SOURCE, dt.date(2026, 9, 5)
    )
    check(f"{category}", ev.activity_type, want)

ev = an._normalize(
    {**row, "name": "Open Session", "category": "Something New"}, SOURCE, dt.date(2026, 9, 5)
)
check("an unmapped category falls back to the source's type", ev.activity_type, "Other")

print("\n9. EVERY VENUE IN THE COORDINATE TABLE BELONGS TO A KNOWN AREA")
# A venue with coordinates but no area would draw on the map and then
# vanish the moment any area filter is applied.
check(
    "every configured city has an area",
    sorted({s["source_name"] for s in config.SOURCES} - set(config.CITY_AREAS)),
    [],
)
check(
    "no area lists a city that isn't configured",
    sorted(set(config.CITY_AREAS) - {s["source_name"] for s in config.SOURCES}),
    [],
)
check(
    "area names are unique",
    len({a["name"] for a in config.AREAS}),
    len(config.AREAS),
)

print("\n" + ("ALL PASSED" if not FAIL else f"FAILURES: {FAIL}"))
sys.exit(1 if FAIL else 0)
