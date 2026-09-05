"""The shape of one drop-in session, shared by every scraper.

This lives apart from the scrapers so that each platform module can build
an Event without importing another platform's scraper. `scraper.py` is the
dispatcher that picks a module per source; if Event lived there, every
scraper would have to import the dispatcher that imports it, and Python
would refuse the circle.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Several drop-in calendars are mixed bags — one "Adult" calendar carries
# badminton, basketball, chess, art studio and movie matinees alike. Tagging
# every event with its calendar's category would therefore file chess under
# sports, so the specific sport is recognised from the event name and only
# unrecognised events fall back to the calendar's configured type.
#
# Ordered: the first match wins, so put more specific patterns first.
_ACTIVITY_PATTERNS = (
    ("Badminton", re.compile(r"\bbadminton\b", re.I)),
    ("Basketball", re.compile(r"\bbasketball\b", re.I)),
    ("Soccer", re.compile(r"\bsoccer\b|\bfutsal\b", re.I)),
    ("Volleyball", re.compile(r"\bvolleyball\b", re.I)),
    ("Pickleball", re.compile(r"\bpickleball\b", re.I)),
    ("Table Tennis", re.compile(r"\btable tennis\b|\bping[- ]?pong\b", re.I)),
)


def classify_activity(event_name: str, fallback: str) -> str:
    """Name-derived activity type, falling back to the calendar's category.

    Note there is deliberately no rule mapping "hockey" to skating: the
    sports calendars contain *floor* hockey, which is not on ice.
    """
    for activity, pattern in _ACTIVITY_PATTERNS:
        if pattern.search(event_name or ""):
            return activity
    return fallback


@dataclass
class Event:
    activity_type: str
    event_name: str
    date: str  # ISO YYYY-MM-DD
    day_of_week: str
    start_time: str
    end_time: str
    facility: str
    location: str
    price: str
    spots: str
    status: str
    source_name: str
    calendar_label: str
    course_id: str = ""
    details: str = ""
    detail_url: str = ""
    # True when the portal offers its own waitlist for this (full) session.
    has_waitlist: bool = False
