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
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from zoneinfo import ZoneInfo

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# Matches the whole <input> tag first, then pulls value= out of it, so this
# doesn't break if the portal ever reorders the tag's attributes.
TOKEN_TAG_RE = re.compile(r'<input[^>]*name="__RequestVerificationToken"[^>]*>')
VALUE_ATTR_RE = re.compile(r'value="([^"]*)"')

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "activity-schedule-dashboard/1.0 (+local scraper for public drop-in schedules)"
)

MAX_PAGES = 5  # safety cap on "load more" pagination per calendar

DEFAULT_TIMEZONE = "America/Vancouver"


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
    return session


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


def _get_session_and_token(session: requests.Session, source: dict) -> str:
    url = (
        f"{source['base_url']}/{source['org_id']}/Clients/BookMe4BookingPages/Classes"
        f"?calendarId={source['calendar_id']}&widgetId={source['widget_id']}&embed=False"
    )
    resp = session.get(url, headers={"User-Agent": USER_AGENT}, timeout=20)
    resp.raise_for_status()
    tag_match = TOKEN_TAG_RE.search(resp.text)
    value_match = VALUE_ATTR_RE.search(tag_match.group(0)) if tag_match else None
    if not value_match:
        raise RuntimeError(
            f"Could not find anti-forgery token on {url}; the portal's page "
            "structure may have changed."
        )
    return value_match.group(1)


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

    event_id = raw.get("EventId", "")
    detail_url = (
        f"{source['base_url']}/{source['org_id']}/Clients/BookMe4LandingPages/Class"
        f"?widgetId={source['widget_id']}&redirectedFromEmbededMode=False"
        f"&classId={event_id}&occurrenceDate={occurrence}"
        if event_id and occurrence
        else ""
    )

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
        detail_url=detail_url,
    )


def fetch_calendar_events(
    source: dict, days_ahead: int
) -> list[Event]:
    """Fetch and normalize events for a single calendar source."""
    # Use the venue's local calendar date, not the scraping server's (Render
    # isn't necessarily in Pacific time) and not UTC — otherwise "today"
    # can silently shift by a day depending on where/when this runs.
    tz = ZoneInfo(source.get("timezone", DEFAULT_TIMEZONE))
    today_local = dt.datetime.now(tz).date()
    date_from = dt.datetime.combine(today_local, dt.time.min)
    date_to = date_from + dt.timedelta(days=days_ahead)

    session = _build_session()
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
    else:
        logger.warning(
            "Hit the %d-page pagination cap for %s / %s — some events may "
            "have been left out. Consider raising MAX_PAGES.",
            MAX_PAGES,
            source["source_name"],
            source["calendar_label"],
        )

    return events


def fetch_all_events(sources: list[dict], days_ahead: int) -> tuple[list[Event], list[str]]:
    """Fetch events for every configured source, in parallel.

    Returns (events, errors). A failure on one source does not prevent the
    others from being returned. Error messages returned here are shown on
    the public dashboard, so they're deliberately generic — full details
    (exception, traceback) go to the server log instead.
    """
    all_events: list[Event] = []
    errors: list[str] = []

    with ThreadPoolExecutor(max_workers=min(len(sources), 5) or 1) as pool:
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
