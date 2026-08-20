"""Watch favourited activities and alert their watchers when a spot opens.

Called on a schedule by an external pinger hitting /api/check-watches (the
free Render tier sleeps, so the app cannot poll itself). Each run:

  1. Scrapes current schedules.
  2. Compares each occurrence's availability to the last-seen state.
  3. For every closed -> open transition, notifies the users who favourited
     that recurring activity.

Deliberately conservative: an occurrence we have never seen before is only
recorded, never alerted on, so the first run (or a newly published session)
does not blast out a backlog of notifications.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import os

from pywebpush import WebPushException, webpush

from models import EventState, Favorite, PushSubscription, WatchRun, db

logger = logging.getLogger(__name__)


def is_open(event: dict) -> bool:
    """Whether a session can be registered for right now.

    Mirrors the badge logic in static/app.js so the dashboard and the alerts
    never disagree about what "open" means.
    """
    spots = (event.get("spots") or "").strip().lower()
    status = (event.get("status") or "").strip()
    if "full" in spots:
        return False
    if "spot" in spots:
        return True
    return status == "Register"


def send_push(subscription: PushSubscription, payload: dict) -> bool:
    """Returns False if the subscription is dead and should be removed."""
    try:
        webpush(
            subscription_info={
                "endpoint": subscription.endpoint,
                "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
            },
            data=json.dumps(payload),
            vapid_private_key=os.environ["VAPID_PRIVATE_KEY"],
            vapid_claims={"sub": os.environ.get("VAPID_CLAIM_EMAIL", "mailto:admin@example.com")},
        )
        return True
    except WebPushException as exc:
        # 404/410 mean the browser dropped the subscription for good.
        status = getattr(exc.response, "status_code", None)
        if status in (404, 410):
            logger.info("Dropping expired push subscription %s", subscription.id)
            return False
        logger.warning("Push failed for subscription %s: %s", subscription.id, exc)
        return True
    except Exception:
        logger.exception("Unexpected error sending push to %s", subscription.id)
        return True


def notify_user(user, event: dict) -> int:
    """Push an 'a spot opened' alert to every device a user has registered."""
    payload = {
        "title": f"Spot open: {event.get('event_name', 'Activity')}",
        "body": (
            f"{event.get('day_of_week', '')} {event.get('start_time', '')} · "
            f"{event.get('facility') or event.get('location', '')} · "
            f"{event.get('spots') or 'Open'}"
        ).strip(" ·"),
        "url": event.get("detail_url") or "/",
    }

    sent = 0
    for sub in list(user.push_subscriptions):
        if send_push(sub, payload):
            sent += 1
        else:
            db.session.delete(sub)
    return sent


def check_watches(events: list[dict]) -> dict:
    """Compare current availability against stored state and alert on opens.

    `events` is the freshly scraped, normalized event list.
    """
    today = dt.date.today().isoformat()

    # Only users' favourites matter, so build the watcher index up front and
    # skip any occurrence nobody is watching.
    watchers: dict[tuple[str, str], list] = {}
    for fav in Favorite.query.all():
        watchers.setdefault((fav.source_name, fav.course_id), []).append(fav.user)

    prior = {
        (s.source_name, s.course_id, s.date): s
        for s in EventState.query.filter(EventState.date >= today).all()
    }

    checked = 0
    transitions = 0
    notifications = 0

    for event in events:
        source_name = event.get("source_name")
        course_id = event.get("course_id")
        date = event.get("date")
        if not source_name or not course_id or not date or date < today:
            continue

        key = (source_name, course_id, date)
        open_now = is_open(event)
        state = prior.get(key)

        if state is None:
            # First sighting — record only, never alert.
            db.session.add(
                EventState(
                    source_name=source_name,
                    course_id=course_id,
                    date=date,
                    was_open=open_now,
                )
            )
            continue

        checked += 1
        if open_now and not state.was_open:
            transitions += 1
            for user in watchers.get((source_name, course_id), []):
                notifications += notify_user(user, event)

        if state.was_open != open_now:
            state.was_open = open_now
            state.updated_at = dt.datetime.utcnow()

    # Occurrences in the past can never re-open; drop them so the table does
    # not grow without bound.
    EventState.query.filter(EventState.date < today).delete(synchronize_session=False)

    # Heartbeat: a single row, overwritten each run, so the dashboard can show
    # whether the scheduler is actually calling us.
    run = WatchRun.query.get(1) or WatchRun(id=1)
    run.ran_at = dt.datetime.utcnow()
    run.checked = checked
    run.transitions = transitions
    run.notifications_sent = notifications
    db.session.add(run)

    db.session.commit()

    return {
        "checked": checked,
        "transitions": transitions,
        "notifications_sent": notifications,
        "watched_activities": len(watchers),
    }
