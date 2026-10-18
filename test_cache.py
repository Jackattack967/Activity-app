"""The schedule cache must never make a page load wait for a scrape.

The failure this guards against was not a crash. It was the site going
unresponsive for tens of seconds, several times an hour, because the cache
lock was held across the scrape and one gunicorn worker served requests one
at a time. Everything here is about *when* callers block, so every check
measures that rather than inspecting the cache.
"""

import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import app as webapp
import config

FAIL = []


def check(label, got, want):
    ok = got == want
    print(f"  {'PASS' if ok else 'FAIL'}  {label}: got {got!r}, want {want!r}")
    if not ok:
        FAIL.append(label)


class FakeScraper:
    """Stands in for the portals, and can be held mid-scrape on demand."""

    def __init__(self, duration=0.0):
        self.calls = 0
        self.duration = duration
        self.started = threading.Event()
        self.release = threading.Event()
        self.release.set()

    def __call__(self, sources, days):
        self.calls += 1
        self.started.set()
        if self.duration:
            time.sleep(self.duration)
        self.release.wait(timeout=5)
        return [], []


def quiesce():
    """Wait until no scrape is in flight.

    Sections here start background refreshes on purpose, and one still
    running when the next section sets up its cache will publish over it —
    which looks like the code losing data rather than the test racing it.
    """
    for _ in range(100):
        if webapp._scrape_lock.acquire(blocking=False):
            webapp._scrape_lock.release()
            return
        time.sleep(0.05)
    raise AssertionError("a scrape was still running after 5s")


def reset(fake):
    quiesce()
    webapp._cache.update({"events": [], "errors": [], "fetched_at": 0.0})
    webapp.scraper.fetch_all_events = fake


print("1. THE FIRST REQUEST AFTER A BOOT HAS TO WAIT")
# There is nothing to serve instead, and an empty dashboard is worse than a
# slow one. This is the only page load that may block.
fake = FakeScraper()
reset(fake)
webapp._get_events()
check("it scraped", fake.calls, 1)
check("and the cache is populated", webapp._cache["fetched_at"] > 0, True)

print("\n2. A FRESH CACHE IS SERVED WITHOUT SCRAPING AT ALL")
fake = FakeScraper()
webapp.scraper.fetch_all_events = fake
webapp._cache.update({"events": [{"x": 1}], "errors": [], "fetched_at": time.time()})
data = webapp._get_events()
check("no scrape", fake.calls, 0)
check("the cached schedule came back", data["events"], [{"x": 1}])

print("\n3. A STALE CACHE IS SERVED IMMEDIATELY, AND REFRESHED BEHIND IT")
# The heart of it. The caller must get the old schedule now, not the new
# one in twenty seconds.
fake = FakeScraper(duration=0.3)
webapp.scraper.fetch_all_events = fake
stale = time.time() - config.CACHE_TTL_SECONDS - 60
webapp._cache.update({"events": [{"old": True}], "errors": [], "fetched_at": stale})

started = time.perf_counter()
data = webapp._get_events()
elapsed = time.perf_counter() - started

check("returned the stale schedule", data["events"], [{"old": True}])
check("without waiting for the scrape", elapsed < 0.1, True)
check("but a refresh did start", fake.started.wait(timeout=2), True)
quiesce()

print("\n4. A SLOW SCRAPE NEVER BLOCKS A PAGE LOAD")
# The actual regression test. While a scrape is in flight — which is what a
# watch pass does every five minutes — other callers must still be served.
fake = FakeScraper()
fake.release.clear()
webapp.scraper.fetch_all_events = fake
# Older than the coalescing window, so the forced refresh below really
# scrapes, but far younger than the TTL, so the page load is a plain cache
# read rather than a background refresh.
webapp._cache.update({
    "events": [{"served": True}],
    "errors": [],
    "fetched_at": time.time() - webapp.FORCED_REFRESH_COALESCE_SECONDS - 1,
})

scraping = threading.Thread(target=webapp._get_events, kwargs={"force": True})
scraping.start()
check("the scrape is under way", fake.started.wait(timeout=2), True)

started = time.perf_counter()
data = webapp._get_events()
elapsed = time.perf_counter() - started
check("a page load is served during it", data["events"], [{"served": True}])
check("and is not made to wait", elapsed < 0.1, True)

fake.release.set()
scraping.join(timeout=5)
quiesce()

print("\n5. CONCURRENT FORCED REFRESHES COALESCE INTO ONE SCRAPE")
# Without this, the watch pass, the external scheduler and anyone holding
# down the Refresh button stack scrapes onto nine cities' portals.
fake = FakeScraper(duration=0.2)
reset(fake)
threads = [
    threading.Thread(target=webapp._get_events, kwargs={"force": True})
    for _ in range(4)
]
for thread in threads:
    thread.start()
for thread in threads:
    thread.join(timeout=10)
check("four callers, one scrape", fake.calls, 1)

print("\n6. A FORCED REFRESH STILL SCRAPES ONCE THE RESULT IS OLD")
# Coalescing must not turn into "never refresh": past the window, a caller
# asking for fresh data gets a real scrape.
fake = FakeScraper()
webapp.scraper.fetch_all_events = fake
webapp._cache.update({
    "events": [{"x": 1}],
    "errors": [],
    "fetched_at": time.time() - webapp.FORCED_REFRESH_COALESCE_SECONDS - 1,
})
webapp._get_events(force=True)
check("it scraped", fake.calls, 1)

print("\n7. A TOTAL PORTAL OUTAGE KEEPS THE LAST GOOD SCHEDULE")
# Pre-existing behaviour, re-checked because the rewrite moved the code
# that implements it.
def all_sources_failed(sources, days):
    return [], ["City of Vancouver / Drop-in — Public Swim: temporarily unavailable"]

webapp.scraper.fetch_all_events = all_sources_failed
kept = time.time() - 60
webapp._cache.update({"events": [{"keep": True}], "errors": [], "fetched_at": kept})
data = webapp._get_events(force=True)
check("the schedule survives", data["events"], [{"keep": True}])
check("the errors are reported", len(data["errors"]), 1)
check("and it is not marked as freshly fetched", webapp._cache["fetched_at"], kept)

print("\n8. THE DATABASE URL NAMES ITS DRIVER")
# SQLAlchemy 2.1 changed what "postgresql://" resolves to — psycopg v3
# rather than psycopg2 — and this app declares psycopg2-binary. A rebuild
# that picked up the new default took out sign-in, favourites and every
# alert, with nothing in this repository having changed. Naming the driver
# is what stops a dependency's default from deciding that again.
for given, want in [
    ("postgresql://u:p@host/db", "postgresql+psycopg2://u:p@host/db"),
    # Still handed out by some providers; SQLAlchemy has rejected it since 1.4.
    ("postgres://u:p@host/db", "postgresql+psycopg2://u:p@host/db"),
    # Already explicit, in either direction: left exactly as it is.
    ("postgresql+psycopg2://u:p@host/db", "postgresql+psycopg2://u:p@host/db"),
    ("postgresql+psycopg://u:p@host/db", "postgresql+psycopg://u:p@host/db"),
    ("sqlite:///local.db", "sqlite:///local.db"),
]:
    check(f"{given.split('://')[0]}://", webapp._name_the_driver(given), want)

# The query string Neon and friends require must survive untouched.
check(
    "options and flags are preserved",
    webapp._name_the_driver("postgresql://u:p@h/db?sslmode=require&x=1"),
    "postgresql+psycopg2://u:p@h/db?sslmode=require&x=1",
)


print("\n" + ("ALL PASSED" if not FAIL else f"FAILURES: {FAIL}"))
sys.exit(1 if FAIL else 0)
