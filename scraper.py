"""Scraper for PerfectMind-based municipal recreation booking widgets.

PerfectMind (used by many BC municipalities, including Coquitlam) renders its
drop-in schedules through a JSON API rather than static HTML. The flow is:

  1. GET the calendar's "Classes" page. This returns server-rendered HTML
     containing a hidden anti-forgery token, and sets a session cookie.
  2. POST that token (plus the session cookie) to the ClassesV2 endpoint
     with a date range filter. It returns JSON with the schedule.

This module reproduces that flow with `requests` instead of a browser.
"""

from __future__ import annotations

import datetime as dt
import logging
import re
from dataclasses import dataclass, field

import requests

logger = logging.getLogger(__name__)

TOKEN_RE = re.compile(
    r'name="__RequestVerificationToken"[^>]*value="([^"]+)"'
)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "activity-schedule-dashboard/1.0 (+local scraper for public drop-in schedules)"
)

MAX_PAGES = 5  # safety cap on "load more" pagination per calendar


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


def _get_session_and_token(session: requests.Session, source: dict) -> str:
    url = (
        f"{source['base_url']}/{source['org_id']}/Clients/BookMe4BookingPages/Classes"
        f"?calendarId={source['calendar_id']}&widgetId={source['widget_id']}&embed=False"
    )
    resp = session.get(url, headers={"User-Agent": USER_AGENT}, timeout=20)
    resp.raise_for_status()
    match = TOKEN_RE.search(resp.text)
    if not match:
        raise RuntimeError(
            f"Could not find anti-forgery token on {url}; the portal's page "
            "structure may have changed."
        )
    return match.group(1)


def _fetch_classes_page(
    session: requests.Session,
    source: dict,
    token: str,
    date_from: dt.datetime,
    date_to: dt.datetime,
    page: int,
) -> dict:
    post_url = (
        f"{source['base_url']}/{source['org_id']}/Clients/BookMe4BookingPagesV2/ClassesV2"
    )
    body = {
        "calendarId": source["calendar_id"],
        "widgetId": source["widget_id"],
        "page": str(page),
        "values[0][Name]": "Date Range",
        "values[0][Value]": date_from.strftime("%Y-%m-%dT00:00:00.000Z"),
        "values[0][Value2]": date_to.strftime("%Y-%m-%dT00:00:00.000Z"),
        "values[0][ValueKind]": "6",
        "__RequestVerificationToken": token,
    }
    resp = session.post(
        post_url,
        data=body,
        headers={
            "User-Agent": USER_AGENT,
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
        },
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json()


def _normalize(raw: dict, source: dict) -> Event:
    occurrence = raw.get("OccurrenceDate", "")
    if len(occurrence) == 8:
        iso_date = f"{occurrence[0:4]}-{occurrence[4:6]}-{occurrence[6:8]}"
        day_of_week = dt.date(
            int(occurrence[0:4]), int(occurrence[4:6]), int(occurrence[6:8])
        ).strftime("%A")
    else:
        iso_date = ""
        day_of_week = ""

    status = raw.get("BookButtonText") or ""
    if not status:
        status = "Closed" if not raw.get("Spots") else raw.get("Spots", "")

    return Event(
        activity_type=source["activity_type"],
        event_name=raw.get("EventName", "").strip(),
        date=iso_date,
        day_of_week=day_of_week,
        start_time=raw.get("FormattedStartTime", ""),
        end_time=raw.get("FormattedEndTime", ""),
        facility=raw.get("Facility") or raw.get("Location") or "",
        location=raw.get("Location", ""),
        price=raw.get("PriceRange", ""),
        spots=raw.get("Spots", ""),
        status=status,
        source_name=source["source_name"],
        calendar_label=source["calendar_label"],
        course_id=raw.get("CourseIdTrimmed", ""),
        details=(raw.get("Details") or "").strip(),
    )


def fetch_calendar_events(
    source: dict, days_ahead: int
) -> list[Event]:
    """Fetch and normalize events for a single calendar source."""
    date_from = dt.datetime.utcnow()
    date_to = date_from + dt.timedelta(days=days_ahead)

    session = requests.Session()
    token = _get_session_and_token(session, source)

    events: list[Event] = []
    seen_event_ids: set[str] = set()

    for page in range(MAX_PAGES):
        data = _fetch_classes_page(session, source, token, date_from, date_to, page)
        classes = data.get("classes", [])
        if not classes:
            break

        new_count = 0
        for raw in classes:
            event_id = raw.get("EventId", "")
            if event_id and event_id in seen_event_ids:
                continue
            if event_id:
                seen_event_ids.add(event_id)
            events.append(_normalize(raw, source))
            new_count += 1

        if new_count == 0:
            break  # this page was all duplicates; nothing more to gain

    return events


def fetch_all_events(sources: list[dict], days_ahead: int) -> tuple[list[Event], list[str]]:
    """Fetch events for every configured source.

    Returns (events, errors). A failure on one source does not prevent the
    others from being returned.
    """
    all_events: list[Event] = []
    errors: list[str] = []

    for source in sources:
        try:
            all_events.extend(fetch_calendar_events(source, days_ahead))
        except Exception as exc:  # noqa: BLE001 - surface any scrape failure, keep going
            label = f"{source['source_name']} / {source['calendar_label']}"
            logger.exception("Failed to fetch %s", label)
            errors.append(f"{label}: {exc}")

    all_events.sort(key=lambda e: (e.date, e.start_time))
    return all_events, errors
