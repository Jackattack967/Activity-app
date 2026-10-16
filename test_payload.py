"""What the dashboard actually ships to a browser.

Measured on live data at 2,299 sessions: 2.30MB of JSON inlined into the
page, 360KB once gzipped, of which the portals' own descriptions were a
third — and those are read one at a time, in the detail pane, long after
the page is up. Nothing in the stack compressed anything.

Both fixes are invisible from the outside until they regress, and the
regression is silent: the page still works, it is just several times
heavier. So these check the response, not the code.
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import app as webapp

FAIL = []


def check(label, got, want):
    ok = got == want
    print(f"  {'PASS' if ok else 'FAIL'}  {label}: got {got!r}, want {want!r}")
    if not ok:
        FAIL.append(label)


DESCRIPTION = "All levels welcome. Bring indoor shoes and a water bottle. " * 6


def event(n):
    return {
        "activity_type": "Swimming", "event_name": f"Public Swim {n}",
        "date": "2026-10-20", "day_of_week": "Tuesday",
        "start_time": "1:00 PM", "end_time": "2:00 PM",
        "facility": "Lane Pool", "location": "Hillcrest Aquatic Centre",
        "price": "$6", "spots": "3 spots left", "status": "Register",
        "source_name": "City of Vancouver", "calendar_label": "Drop-in",
        "course_id": str(n), "detail_url": f"https://example.invalid/{n}",
        "details": DESCRIPTION, "has_waitlist": False, "cancelled": False,
        "lat": 49.2, "lng": -123.1, "area": "Vancouver",
    }


# Fresh, so nothing decides to refresh behind the request.
webapp._cache.update(
    {"events": [event(n) for n in range(60)], "errors": [], "fetched_at": time.time()}
)


def never_scrape(sources, days):
    raise AssertionError("a request scraped when the cache was fresh")


webapp.scraper.fetch_all_events = never_scrape
client = webapp.app.test_client()

print("1. DESCRIPTIONS ARE NOT INLINED INTO THE PAGE")
html = client.get("/").get_data(as_text=True)
check("no description in the HTML", DESCRIPTION.strip() in html, False)
check("but the sessions are there", "Public Swim 7" in html, True)
# The schedule still has to carry what the cards and filters read.
for field in ("Hillcrest Aquatic Centre", "Drop-in", "3 spots left", "Vancouver"):
    check(f"{field!r} survives", field in html, True)

print("\n2. THE API STILL SERVES THEM, WHICH IS WHERE THE PAGE GETS THEM")
api = client.get("/api/events").get_json()
check("descriptions are in /api/events", DESCRIPTION in api["events"][0]["details"], True)
check("the cached dicts were not stripped", "details" in webapp._cache["events"][0], True)

print("\n3. RESPONSES ARE COMPRESSED")
gzipped = client.get("/", headers={"Accept-Encoding": "gzip"})
plain = client.get("/", headers={"Accept-Encoding": "identity"})
check("the page is gzipped", gzipped.headers.get("Content-Encoding"), "gzip")
check("not when the client cannot take it", plain.headers.get("Content-Encoding"), None)
check("and it is smaller", len(gzipped.get_data()) < len(plain.get_data()), True)

json_gz = client.get("/api/events", headers={"Accept-Encoding": "gzip"})
check("the JSON endpoint too", json_gz.headers.get("Content-Encoding"), "gzip")
# Caches key on this, and serving a gzipped body to a client that asked for
# plain text is how a proxy poisons a site for everyone behind it.
check("Vary names the header", "Accept-Encoding" in gzipped.headers.get("Vary", ""), True)

print("\n4. THE SAVING IS REAL, NOT A ROUNDING ERROR")
slim = len(client.get("/", headers={"Accept-Encoding": "identity"}).get_data())
webapp._annotate_favorites_original = webapp._annotate_favorites
try:
    webapp._annotate_favorites = lambda events, include_details=True: (
        webapp._annotate_favorites_original(events, include_details=True)
    )
    fat = len(client.get("/", headers={"Accept-Encoding": "identity"}).get_data())
finally:
    webapp._annotate_favorites = webapp._annotate_favorites_original
# On live data the page without descriptions measured 63% of the page with
# them. The bar here is a fifth, which both that and this fixture's shorter
# descriptions clear, so it fails when the field creeps back in rather than
# when a portal happens to be terse that week.
check("dropping descriptions removes a fifth of the page or more",
      slim < fat * 0.8, True)
print(f"         ({fat:,} bytes with them, {slim:,} without)")

print("\n" + ("ALL PASSED" if not FAIL else f"FAILURES: {FAIL}"))
sys.exit(1 if FAIL else 0)
