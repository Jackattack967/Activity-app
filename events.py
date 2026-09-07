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
# Portals announce a cancellation by editing the session's name and leaving
# everything else alone: "Canceled: Cycle Express", "CANCELLED - Cycle".
# The spot count is untouched, so a cancelled class keeps whatever number it
# had — in practice "1 spot left", which makes the sessions that are *not*
# happening look like the scarcest thing on the schedule.
#
# Both spellings appear (the American one comes from one portal, the
# Canadian from another), and a word boundary stops it matching "Cancellation Policy".
_CANCELLED_RE = re.compile(r"\bcancell?ed\b", re.I)


def is_cancelled(event_name: str) -> bool:
    """Whether the portal has renamed this session to announce it is off."""
    return bool(_CANCELLED_RE.search(event_name or ""))


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

    There is deliberately no "golf" rule either, for the opposite reason.
    Golf only reaches this app from calendars that are nothing but golf, so
    the source's own activity_type is already correct and a name rule would
    add nothing. It would, however, start mislabelling things the day a
    fitness calendar is added: Vancouver's portal offers "Exercise for Golf
    Conditioning", which is a fitness class, not golf.
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
    # Decided once here, from the name, rather than re-derived by every
    # consumer — the dashboard and the alerts must not disagree about
    # whether a session is happening.
    cancelled: bool = False
