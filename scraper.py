"""Picks the right scraper for each configured source, and runs them all.

The cities in `config.SOURCES` do not all run the same booking software.
Coquitlam, Port Moody and New Westminster are on PerfectMind; Port
Coquitlam is on ActiveNet. Each platform gets a module that knows how to
talk to it and returns the same `Event` objects, so nothing downstream —
the cache, the dashboard, the alert watcher — has to care which is which.

Adding a platform means writing one module with `fetch_calendar_events()`
and `build_login_url()`, then listing it in PLATFORMS below.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import scraper_activenet
import scraper_perfectmind

# Re-exported so callers can keep saying scraper.Event / scraper.classify_activity.
from events import Event, classify_activity  # noqa: F401

logger = logging.getLogger(__name__)

PLATFORMS = {
    "perfectmind": scraper_perfectmind,
    "activenet": scraper_activenet,
}

# What a source without an explicit "platform" is assumed to be. Every
# source predating multi-platform support was PerfectMind.
DEFAULT_PLATFORM = "perfectmind"


def _module_for(source: dict):
    name = source.get("platform", DEFAULT_PLATFORM)
    try:
        return PLATFORMS[name]
    except KeyError:
        raise ValueError(
            f"Unknown platform {name!r} for source "
            f"{source.get('source_name', '?')} / {source.get('calendar_label', '?')}. "
            f"Known platforms: {', '.join(sorted(PLATFORMS))}."
        ) from None


def fetch_calendar_events(source: dict, days_ahead: int) -> list[Event]:
    """Fetch and normalize events for a single source, whatever it runs on."""
    return _module_for(source).fetch_calendar_events(source, days_ahead)


def build_login_url(source: dict) -> str:
    """URL for that city's own official sign-in page."""
    return _module_for(source).build_login_url(source)


def fetch_all_events(sources: list[dict], days_ahead: int) -> tuple[list[Event], list[str]]:
    """Fetch events for every configured source, in parallel.

    Returns (events, errors). A failure on one source does not prevent the
    others from being returned. Error messages returned here are shown on
    the public dashboard, so they're deliberately generic — full details
    (exception, traceback) go to the server log instead.
    """
    all_events: list[Event] = []
    errors: list[str] = []

    with ThreadPoolExecutor(max_workers=min(len(sources), 8) or 1) as pool:
        future_to_source = {
            pool.submit(fetch_calendar_events, source, days_ahead): source
            for source in sources
        }
        for future in as_completed(future_to_source):
            source = future_to_source[future]
            label = f"{source['source_name']} / {source['calendar_label']}"
            try:
                all_events.extend(future.result())
            except Exception:  # noqa: BLE001 - surface any scrape failure, keep going
                logger.exception("Failed to fetch %s", label)
                errors.append(f"{label}: temporarily unavailable")

    all_events.sort(key=lambda e: (e.date, e.start_time))
    return all_events, errors
