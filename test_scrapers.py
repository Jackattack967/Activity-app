"""Exercise the multi-platform scraper layer.

Run with:  .venv\\Scripts\\python.exe test_scrapers.py
Exits non-zero if anything fails.

Everything here is offline. The ActiveNet cases feed captured API rows
through the same normalisation the live scraper uses, so the parsing that
turns a portal's wording into an Event can be checked without hitting a
city's servers or depending on what happens to be scheduled today.
"""
import datetime as dt
import json
import os
import re
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

print("\n10. GOLF IS TYPED BY ITS SOURCE, NOT BY ITS NAME")
GOLF_SOURCE = {
    "source_name": "City of Burnaby",
    "platform": "activenet",
    "location": "Riverway Golf Course",
    "calendar_label": "Golf — Riverway Golf Course",
    "activity_type": "Golf",
}
golf_row = {
    "name": "Jr Golf | Play (age 8-10) | Skills Development | 8 weeks",
    "category": "Golf",
    "time_range": "11:00 AM - 12:30 PM",
    "openings": "2",
    "number": "126745",
    "desc": "<p>An 8-week program.</p>",
    "detail_url": "https://example.invalid/activity/2",
    "location": {},
}
ev = an._normalize(golf_row, GOLF_SOURCE, dt.date(2026, 9, 12))
check("Burnaby's 'Golf' category maps to the Golf type", ev.activity_type, "Golf")
check("the course is the building", ev.location, "Riverway Golf Course")
# Burnaby labels no room inside the clubhouse, so without the fallback the
# card's second line would be blank.
check("an unlabelled room falls back to the course", ev.facility, "Riverway Golf Course")
check("spots still read the way badgeInfo() expects", ev.spots, "2 spots left")

ev = an._normalize({**golf_row, "category": ""}, GOLF_SOURCE, dt.date(2026, 9, 12))
check("still Golf when the row names no category", ev.activity_type, "Golf")

# The point of this section. classify_activity has no "golf" rule on
# purpose: a name rule cannot tell a golf lesson from a gym class named
# after one, and "Exercise for Golf Conditioning" is a real class in
# Vancouver's portal. If someone later adds a \bgolf\b pattern to
# _ACTIVITY_PATTERNS to "fix" golf, this is the test that should stop them.
FITNESS_SOURCE = {**GOLF_SOURCE, "activity_type": "Fitness"}
ev = an._normalize(
    {**golf_row, "name": "Exercise for Golf Conditioning", "category": "Group Fitness"},
    FITNESS_SOURCE,
    dt.date(2026, 9, 12),
)
check("a fitness class named after golf stays fitness", ev.activity_type, "Fitness")

print("\n11. EVERY ACTIVENET VENUE CAN BE PUT ON THE MAP")
# An ActiveNet source names its building in config rather than reading it
# from the portal, so a typo there is invisible: the events still arrive and
# only the map marker quietly goes missing. PerfectMind sources are not
# checked here, because they learn their venue names by scraping.
#
# A venue may legitimately have no coordinates yet — it simply gets no pin —
# but it has to say so in VENUES_AWAITING_COORDS. That is the whole point:
# an unmapped venue and a mistyped one look identical on the map, so the
# deliberate one is the one that is written down.
_activenet_venues = {
    s["location"] for s in config.SOURCES if s.get("platform") == "activenet"
}
check(
    "every ActiveNet venue is either mapped or declared unmapped",
    sorted(
        _activenet_venues
        - set(config.FACILITY_COORDS)
        - config.VENUES_AWAITING_COORDS
    ),
    [],
)
# The other direction: an entry left behind here after its coordinates land,
# or a name that no source uses, would quietly re-open the gap this closes.
check(
    "nothing is both mapped and declared unmapped",
    sorted(config.VENUES_AWAITING_COORDS & set(config.FACILITY_COORDS)),
    [],
)
check(
    "no stale names are declared unmapped",
    sorted(config.VENUES_AWAITING_COORDS - _activenet_venues),
    [],
)

print("\n12. THE ACTIVITY GROUPS STAY A CLEAN SPLIT")
# The preferences dialog offers these as one-of-many, so a type claimed by
# two groups would make two different answers select the same sessions.
claimed = [t for _, types in config.ACTIVITY_GROUPS if types for t in types]
check("no activity type is claimed by two groups", len(claimed), len(set(claimed)))
check(
    "exactly one group is the catch-all complement",
    sum(1 for _, types in config.ACTIVITY_GROUPS if types is None),
    1,
)
check("the catch-all is listed last", config.ACTIVITY_GROUPS[-1][1], None)
check("golf is offered as a starting preference", "Golf" in claimed, True)


print("\n13. EVERY VENUE IS INSIDE THE MAP'S FENCE")
# The map fences panning to Canada, so a venue outside that fence would be
# unreachable: fitBounds would try to frame it and maxBounds would refuse to
# go there, leaving the map stuck against its own edge. The numbers are read
# out of app.js rather than repeated here, so there is only one copy of them
# and this cannot drift.
_js = open(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "app.js"),
    encoding="utf-8",
).read()
_num = r"(-?\d+(?:\.\d+)?)"
_fence = re.search(
    rf"MAP_MAX_BOUNDS\s*=\s*\[\s*\[\s*{_num}\s*,\s*{_num}\s*\]\s*,"
    rf"\s*\[\s*{_num}\s*,\s*{_num}\s*\]",
    _js,
)
check("the fence is readable from app.js", _fence is not None, True)
south, west, north, east = (float(g) for g in _fence.groups())
check("the fence is the right way up", (south < north, west < east), (True, True))

outside = sorted(
    name
    for name, (lat, lng) in config.FACILITY_COORDS.items()
    if not (south <= lat <= north and west <= lng <= east)
)
check("no venue sits outside it", outside, [])

# A longitude typed without its minus sign is the mistake this really
# guards against: 122 E instead of 122 W is in inner Mongolia, and the only
# symptom would be a map that will not stay where it is put.
check(
    "a sign-flipped longitude would be caught",
    (west <= 122.79 <= east),
    False,
)

_home = re.search(rf"MAP_HOME\s*=\s*\[\s*{_num}\s*,\s*{_num}\s*\]", _js)
check("the fallback view is readable", _home is not None, True)
home_lat, home_lng = (float(g) for g in _home.groups())
check(
    "the fallback view is inside the fence too",
    south <= home_lat <= north and west <= home_lng <= east,
    True,
)


print("\n14. AVAILABILITY HAS THREE ANSWERS, NOT TWO")
# These four statuses are the complete set the configured portals actually
# produced when this was written (801 sessions across five cities).
#
# "More Info" is the important one: 212 of those 801 carried it, with no
# spot count at all — most of Coquitlam's and New Westminster's drop-in
# skating and swimming. It means the portal publishes no capacity for that
# session, which is not the same as the session being full.
#
# The front end therefore asks two different questions of the same event.
# "Is it full?" drives the Hide-full-sessions filter, and unknown capacity
# is not full, so those sessions stay on the page. "Is it open?" drives the
# alerts below, and unknown capacity is not a spot opening up, so it never
# fires one. Collapsing the two is what made that filter hide a quarter of
# the schedule.
import watcher

for spots, status, want, why in [
    ("4 spots left", "Register", True, "a real count"),
    ("1 spot left", "Register", True, "singular count"),
    ("Full", "Full", False, "explicitly full"),
    ("", "Register", True, "no count, but registration is open"),
    ("", "Closed", False, "explicitly closed"),
    ("", "More Info", False, "capacity unknown - cannot be an opening"),
    ("", "", False, "nothing known at all"),
]:
    got = watcher.is_open({"spots": spots, "status": status})
    check(f"{why}: spots={spots!r} status={status!r}", got, want)

# A watch can only fire on a transition into open. Unknown-capacity
# sessions never report open, so a star on one can never alert — that is a
# limitation of the portal's data, and the test exists to record it rather
# than to have it rediscovered as a bug.
check(
    "an unknown-capacity session never looks open",
    any(watcher.is_open({"spots": "", "status": "More Info"}) for _ in range(3)),
    False,
)


print("\n15. A CANCELLED SESSION IS NEVER AN OPENING")
# Portals announce a cancellation by renaming the session and leaving its
# spot count alone. All four cancelled sessions on the live schedule read
# "1 spot left", so before this they were both the most urgent-looking rows
# on the page and, worse, genuinely open as far as the watcher was
# concerned — a star on one would have sent a real "a spot opened" alert.
import events

for name, want in [
    ("Canceled: Cycle Express", True),          # spelling from one portal
    ("CANCELLED - Shallow Aquafit", True),      # and from another
    ("Canceled: Cycle & Strength", True),
    ("cancelled yoga", True),
    ("Family Skate", False),
    ("Adult Stick, Ring & Puck", False),
    # Must not fire on a word that merely starts the same way.
    ("Cancellation Policy Workshop", False),
    ("", False),
]:
    check(f"is_cancelled({name!r})", events.is_cancelled(name), want)

# The whole point: the stale count must not win.
check(
    "a cancelled session with a spot count is not open",
    watcher.is_open({"spots": "1 spot left", "status": "More Info", "cancelled": True}),
    False,
)
check(
    "the same session without the flag still would be",
    watcher.is_open({"spots": "1 spot left", "status": "More Info", "cancelled": False}),
    True,
)
check(
    "a missing flag is treated as not cancelled",
    watcher.is_open({"spots": "1 spot left", "status": "More Info"}),
    True,
)

# And the scrapers have to stamp it, or nothing above ever runs.
ev = an._normalize(
    {**golf_row, "name": "CANCELLED - Shallow Aquafit"}, GOLF_SOURCE, dt.date(2026, 9, 12)
)
check("the scraper stamps it onto the event", ev.cancelled, True)
ev = an._normalize(golf_row, GOLF_SOURCE, dt.date(2026, 9, 12))
check("and leaves an ordinary session alone", ev.cancelled, False)


print("\n16. A DROP-IN-ONLY SEARCH IS SENT WHEN THE PORTAL OFFERS ONE")
# West Vancouver's categories name the subject, not whether you can turn up
# ("Skating: Public Skate" and "Skating: Skate Lessons" are siblings), so
# its sources filter on the portal's separate "Daily Activities and
# Drop-Ins" type instead. If that filter stops being sent, the dashboard
# fills up with ten-week registered courses nobody can drop into — which
# looks like a busy city, not like a bug.
_sent = {}


class _FakeResponse:
    @staticmethod
    def raise_for_status():
        return None

    @staticmethod
    def json():
        return {"body": {"activity_items": []}, "headers": {"page_info": {"total_page": 1}}}


class _FakeSession:
    def post(self, url, headers=None, data=None, timeout=None):
        _sent.update(json.loads(data)["activity_search_pattern"])
        return _FakeResponse()


WESTVAN_SOURCE = next(
    s for s in config.SOURCES if s["source_name"] == "District of West Vancouver"
)
an._search_page(
    _FakeSession(), WESTVAN_SOURCE, dt.date(2026, 9, 11), dt.date(2026, 9, 25), 1
)
check("the drop-in type filter reaches the portal", _sent.get("activity_type_ids"), ["6"])
check("and the building filter still does", _sent.get("center_ids"), [WESTVAN_SOURCE["center_id"]])

# Port Coquitlam narrows by category instead and names no type. Sending an
# empty list there is what keeps its search as wide as it has always been.
POCO_SOURCE = next(
    s for s in config.SOURCES if s["source_name"] == "City of Port Coquitlam"
)
an._search_page(_FakeSession(), POCO_SOURCE, dt.date(2026, 9, 11), dt.date(2026, 9, 25), 1)
check("a source with no type filter still sends the key", _sent.get("activity_type_ids"), [])
check(
    "and keeps its categories",
    _sent.get("activity_category_ids"),
    POCO_SOURCE["category_ids"],
)

# Every West Vancouver source has to carry the filter, not just the first.
check(
    "no West Vancouver building is left unfiltered",
    sorted(
        s["location"]
        for s in config.SOURCES
        if s["source_name"] == "District of West Vancouver" and not s.get("type_ids")
    ),
    [],
)

print("\n17. A PORTAL'S OWN SPELLING IS NOT THE DASHBOARD'S")
# Two things each portal does to names that would otherwise leak onto cards.

# Vancouver sorts its buildings with a leading bullet. That is display
# bookkeeping inside their picker, so a row labelled with it is still just
# repeating the building it was already filtered to.
STARRED = {**WESTVAN_SOURCE, "location": "Britannia Community Centre"}
ev = an._normalize(
    {**row, "location": {"label": "*Britannia Community Centre"}},
    STARRED,
    dt.date(2026, 9, 11),
)
check("a bulleted building name still collapses", ev.facility, "Britannia Community Centre")

# West Vancouver's own names for two buildings are bare — "Aquatic Centre"
# belongs to nobody on a dashboard spanning nine cities — so config renames
# them and keeps the portal's spelling as an alias.
ev = an._normalize(
    {**row, "location": {"label": "Aquatic Centre"}},
    next(
        s
        for s in config.SOURCES
        if s.get("location") == "West Vancouver Aquatic Centre"
    ),
    dt.date(2026, 9, 11),
)
check("the portal's bare name collapses to the full one", ev.facility, "West Vancouver Aquatic Centre")

# Categories arrive HTML-escaped from some portals and plain from others.
# Matching the escaped form would drop every Vancouver fitness session to
# the "Other" chip.
ev = an._normalize(
    {**row, "name": "Open Gym", "category": "Sports: Table Tennis"},
    WESTVAN_SOURCE,
    dt.date(2026, 9, 11),
)
check("a West Vancouver category maps to a known type", ev.activity_type, "Table Tennis")
for written, want in [
    ("Health and Fitness: Group Fitness", "Fitness"),
    ("Skating: Public Skate", "Skating"),
    ("Swimming: Aquafit", "Swimming"),
    ("Sports: Golf", "Golf"),
    ("Gymnastics: Gymnastics Drop-ins", "All Ages"),
]:
    ev = an._normalize(
        {**row, "name": "Open Session", "category": written},
        WESTVAN_SOURCE,
        dt.date(2026, 9, 11),
    )
    check(f"{written!r}", ev.activity_type, want)
# Vancouver publishes its category entity-encoded. Matching the escaped
# text would send every Vancouver fitness session to the "Other" chip.
ev = an._normalize(
    {**row, "name": "Open Session", "category": "Fitness &amp; Health"},
    {**WESTVAN_SOURCE, "activity_type": "Other"},
    dt.date(2026, 9, 11),
)
check("an escaped category is unescaped before lookup", ev.activity_type, "Fitness")
ev = an._normalize(
    {**row, "name": "Open Session", "category": "Fitness & Health"},
    {**WESTVAN_SOURCE, "activity_type": "Other"},
    dt.date(2026, 9, 11),
)
check("and the plain spelling still works", ev.activity_type, "Fitness")


print("\n" + ("ALL PASSED" if not FAIL else f"FAILURES: {FAIL}"))
sys.exit(1 if FAIL else 0)
