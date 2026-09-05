"""Scraper for ActiveNet (Active Network) municipal recreation portals.

Port Coquitlam and several other cities run ActiveNet rather than
PerfectMind. The shape of the data is different enough to need its own
module, but the flow is simpler than PerfectMind's:

  1. GET the portal's home page once, to pick up the session cookies its
     REST layer expects. No token is needed.
  2. POST a search filter to /rest/activities/list. It returns JSON.

Two differences from PerfectMind matter, and both are handled here so the
rest of the app never has to know which portal an event came from:

  * ActiveNet returns *activities*, not occurrences. Most drop-ins are
    published as a single-day activity, which is already one occurrence,
    but a recurring one spans a date range plus a set of weekdays and has
    to be expanded — see _occurrence_dates().
  * Its building/room split is the other way round. A search filtered by
    `center_ids` is guaranteed to be inside that one building, and the
    per-item label is then the room. So the building name comes from the
    source's "location" and the label becomes the facility, which is what
    the dashboard means by those two words.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import re
from zoneinfo import ZoneInfo

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from events import Event, classify_activity

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "activity-schedule-dashboard/1.0 (+local scraper for public drop-in schedules)"
)

# The API caps a page at 20 regardless of what is asked for, so a busy
# centre needs a dozen or so requests. The cap stops a runaway loop if the
# portal ever stops reporting a sane total_page.
PAGE_SIZE = 20
MAX_PAGES = 25

DEFAULT_TIMEZONE = "America/Vancouver"

# "activity_select_param": 2 is what the portal's own search page sends. It
# selects activities rather than the other bookable things (facilities,
# memberships) that share this endpoint.
_ACTIVITY_SELECT_PARAM = 2

_WEEKDAYS = {
    "mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6,
}

# ActiveNet's own category names, mapped onto the activity types this
# dashboard already uses so that Port Coquitlam's chips line up with
# Coquitlam's rather than sitting beside them as near-duplicates.
CATEGORY_ACTIVITY_TYPES = {
    "Drop-in - Aquatics": "Swimming",
    "Drop-in - Skating": "Skating",
    "Drop-in - Sport": "Sports",
    "Drop-in - Fitness": "Fitness",
    "Drop-in - Youth Services": "Youth",
    "Drop-in - Children Services": "All Ages",
    "Drop-in - Seniors": "Adult",
}

_TAG_RE = re.compile(r"<[^>]+>")

# Some rooms are booked under an internal label ("Program Location: Arena 3
# (Purple)") where the prefix is scheduling bookkeeping, not a place name.
_PROGRAM_LOCATION_RE = re.compile(r"^\s*program location:\s*", re.I)


def _build_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/plain, */*",
        }
    )
    return session


def build_login_url(source: dict) -> str:
    """URL for the portal's own official sign-in page.

    As with PerfectMind, we never handle credentials — this only sends the
    user to the city's real sign-in page in their own browser.
    """
    return f"{source['base_url']}/{source['org_path']}/signin?onlineSiteId=0&locale=en-US"


def _warm_up(session: requests.Session, source: dict) -> None:
    """Fetch the home page so the REST endpoints accept us.

    The API answers 200 with an empty result set for a cookie-less caller,
    which would look like "this centre has no drop-ins" rather than like a
    failure — so this is not optional.
    """
    resp = session.get(
        f"{source['base_url']}/{source['org_path']}/home?onlineSiteId=0",
        timeout=20,
    )
    resp.raise_for_status()


def _search_page(
    session: requests.Session,
    source: dict,
    date_from: dt.date,
    date_to: dt.date,
    page: int,
) -> dict:
    body = {
        "activity_search_pattern": {
            "activity_select_param": _ACTIVITY_SELECT_PARAM,
            "date_after": date_from.isoformat(),
            "date_before": date_to.isoformat(),
            "activity_category_ids": list(source.get("category_ids", [])),
            "center_ids": [source["center_id"]] if source.get("center_id") else [],
        },
        "activity_transfer_pattern": {},
    }
    resp = session.post(
        f"{source['base_url']}/{source['org_path']}/rest/activities/list?locale=en-US",
        headers={
            "Content-Type": "application/json;charset=UTF-8",
            "page_info": json.dumps(
                {"order_by": "", "page_number": page, "total_records_per_page": PAGE_SIZE}
            ),
        },
        data=json.dumps(body),
        timeout=25,
    )
    resp.raise_for_status()
    return resp.json()


def _parse_time(text: str) -> str:
    """Normalise one side of a time range to the "1:30 PM" the front end parses.

    The portal writes noon and midnight as words, and the dashboard's own
    time parser only understands digits — an unrecognised time would make a
    session look like it had already finished and silently vanish.
    """
    cleaned = (text or "").strip()
    lowered = cleaned.lower()
    if lowered == "noon":
        return "12:00 PM"
    if lowered == "midnight":
        return "12:00 AM"
    match = re.match(r"^(\d{1,2})(?::(\d{2}))?\s*([AaPp])\.?[Mm]\.?$", cleaned)
    if not match:
        return cleaned
    hour, minute, half = match.group(1), match.group(2) or "00", match.group(3).upper()
    return f"{int(hour)}:{minute} {half}M"


def _split_time_range(text: str) -> tuple[str, str]:
    parts = re.split(r"\s+-\s+|\s+to\s+", (text or "").strip(), maxsplit=1)
    if len(parts) == 2:
        return _parse_time(parts[0]), _parse_time(parts[1])
    return _parse_time(parts[0]) if parts else "", ""


def _occurrence_dates(raw: dict, window_start: dt.date, window_end: dt.date) -> list[dt.date]:
    """Every date this activity actually runs inside the window.

    Single-day drop-ins — which is nearly all of them — have no end date and
    resolve to exactly one date. A recurring activity is expanded across its
    weekdays, which is the best that can be done from a search result: the
    portal only lists true per-date occurrences on each activity's own
    detail page, and fetching hundreds of those on every scrape would cost
    far more than the handful of recurring rows is worth.

    That expansion can therefore show a session on a date the city later
    cancelled. Every card links back to the portal, which is authoritative.
    """
    start_text = (raw.get("date_range_start") or "").strip()
    if not start_text:
        return []
    try:
        start = dt.date.fromisoformat(start_text)
    except ValueError:
        return []

    end_text = (raw.get("date_range_end") or "").strip()
    if not end_text:
        end = start
    else:
        try:
            end = dt.date.fromisoformat(end_text)
        except ValueError:
            end = start

    first = max(start, window_start)
    last = min(end, window_end)
    if first > last:
        return []
    if start == end:
        return [start]

    weekdays = {
        _WEEKDAYS[token.strip()[:3].lower()]
        for token in re.split(r"[,/&]| and ", raw.get("days_of_week") or "")
        if token.strip()[:3].lower() in _WEEKDAYS
    }
    if not weekdays:
        return []

    span = (last - first).days
    return [
        day
        for day in (first + dt.timedelta(days=n) for n in range(span + 1))
        if day.weekday() in weekdays
    ]


def _spots_and_status(raw: dict) -> tuple[str, str]:
    """Openings, phrased the way the rest of the app already reads them.

    The dashboard decides open-vs-full from the wording of `spots` ("Full",
    "3 spots left"), because that is what PerfectMind hands over. ActiveNet
    gives a plain integer, so it is phrased here rather than teaching the
    front end a second dialect.
    """
    text = str(raw.get("openings") or "").strip()
    try:
        openings = int(text)
    except ValueError:
        # Not a number (the portal sometimes writes a word here) — pass it
        # through and let the badge show it verbatim.
        return text, text
    if openings <= 0:
        return "Full", "Full"
    return f"{openings} spot{'' if openings == 1 else 's'} left", "Register"


def _normalize(raw: dict, source: dict, day: dt.date) -> Event:
    start_time, end_time = _split_time_range(raw.get("time_range") or "")
    spots, status = _spots_and_status(raw)

    # Filtering the search by center_id means every row is inside that
    # building, so the row's own label is the room within it — except when
    # the portal just repeats the building's name, usually in an
    # abbreviated form ("Port Coquitlam Cmty Centre"). Those are listed in
    # the source's center_aliases and collapse to the proper name, so a
    # card never shows a shortened spelling of the heading above it.
    room = ((raw.get("location") or {}).get("label") or "").strip()
    room = _PROGRAM_LOCATION_RE.sub("", room).strip()
    location = source["location"]
    if room.casefold() in {
        alias.casefold() for alias in (location, *source.get("center_aliases", ()))
    }:
        room = ""

    event_name = (raw.get("name") or "").strip()
    fallback = CATEGORY_ACTIVITY_TYPES.get(
        (raw.get("category") or "").strip(), source.get("activity_type", "Other")
    )

    return Event(
        activity_type=classify_activity(event_name, fallback),
        event_name=event_name,
        date=day.isoformat(),
        day_of_week=day.strftime("%A"),
        start_time=start_time,
        end_time=end_time,
        facility=room or location,
        location=location,
        price=(raw.get("search_from_price_desc") or "").strip(),
        spots=spots,
        status=status,
        source_name=source["source_name"],
        calendar_label=source["calendar_label"],
        course_id=str(raw.get("number") or "").strip(),
        details=_TAG_RE.sub("", raw.get("desc") or "").strip(),
        detail_url=(raw.get("detail_url") or "").strip(),
        # ActiveNet's search results carry no waitlist flag; the portal
        # shows it on the activity's own page. Claiming one either way here
        # would be a guess, so the card simply does not offer it.
        has_waitlist=False,
    )


def fetch_calendar_events(source: dict, days_ahead: int) -> list[Event]:
    """Fetch and normalize drop-ins for a single ActiveNet centre."""
    # Same reasoning as the PerfectMind module: "today" is the venue's own
    # calendar date, not the scraping server's and not UTC.
    tz = ZoneInfo(source.get("timezone", DEFAULT_TIMEZONE))
    window_start = dt.datetime.now(tz).date()
    window_end = window_start + dt.timedelta(days=days_ahead)

    session = _build_session()
    _warm_up(session, source)

    events: list[Event] = []
    seen_ids: set[str] = set()

    for page in range(1, MAX_PAGES + 1):
        data = _search_page(session, source, window_start, window_end, page)
        items = (data.get("body") or {}).get("activity_items") or []
        if not items:
            break

        for raw in items:
            activity_id = str(raw.get("id") or "")
            if activity_id and activity_id in seen_ids:
                continue
            if activity_id:
                seen_ids.add(activity_id)
            for day in _occurrence_dates(raw, window_start, window_end):
                events.append(_normalize(raw, source, day))

        page_info = (data.get("headers") or {}).get("page_info") or {}
        if page >= (page_info.get("total_page") or 0):
            break
    else:
        logger.warning(
            "Hit the %d-page pagination cap for %s / %s — some events may "
            "have been left out. Consider raising MAX_PAGES.",
            MAX_PAGES,
            source["source_name"],
            source["calendar_label"],
        )

    return events
