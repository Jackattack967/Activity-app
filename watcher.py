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
import html
import json
import logging
import os

from urllib.parse import quote

import requests
from pywebpush import WebPushException, webpush

from models import EventState, Favorite, PushSubscription, WatchRun, db
from tokens import make_unsubscribe_token

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


def public_base_url() -> str:
    """Absolute base URL of this deployment, for links inside emails.

    Render sets RENDER_EXTERNAL_URL automatically, so this normally needs no
    configuration; PUBLIC_BASE_URL overrides it for a custom domain.
    """
    base = (
        os.environ.get("PUBLIC_BASE_URL")
        or os.environ.get("RENDER_EXTERNAL_URL")
        or ""
    ).strip()
    return base.rstrip("/")


def sender_identity() -> tuple[str, str] | None:
    """(name, mailing address) identifying the sender, or None if unset.

    CASL requires every commercial electronic message to identify who sent
    it and give a mailing address where they can be reached. Both come from
    the environment so a real postal address is never committed to the repo.
    """
    name = (os.environ.get("SENDER_NAME") or "").strip()
    address = (os.environ.get("SENDER_MAILING_ADDRESS") or "").strip()
    if not name or not address:
        return None
    return name, address


def email_compliance_gap() -> str | None:
    """Why alert email cannot lawfully be sent, or None if it can.

    Alert emails are commercial electronic messages under CASL, which
    requires a working unsubscribe mechanism and sender identification in
    the message itself. If either is unavailable the message would be
    unlawful to send, so sending is refused rather than sent incomplete.
    """
    if not public_base_url():
        return (
            "neither PUBLIC_BASE_URL nor RENDER_EXTERNAL_URL is set, so no "
            "unsubscribe link can be built"
        )
    if sender_identity() is None:
        return "SENDER_NAME and SENDER_MAILING_ADDRESS are not both set"
    return None


def email_provider() -> str | None:
    """Which email provider is configured, if any.

    Brevo is preferred: its free tier verifies a single sender address and
    then delivers to any recipient, whereas an unverified Resend account can
    only reach the account owner's own address.
    """
    if os.environ.get("BREVO_API_KEY"):
        return "brevo"
    if os.environ.get("RESEND_API_KEY"):
        return "resend"
    return None


def send_email(to_address: str, event: dict, user_id: int) -> bool:
    """Email one 'a spot opened' alert. Best-effort: a mail failure must
    never abort the watch run or block push delivery."""
    provider = email_provider()
    if provider is None:
        return False

    gap = email_compliance_gap()
    if gap is not None:
        logger.error(
            "Refusing to send alert email: %s. Alert emails must carry an "
            "unsubscribe link and a sender mailing address, so none will be "
            "sent until this is configured. Push alerts are unaffected.",
            gap,
        )
        return False

    sender_name, sender_address = sender_identity()
    unsubscribe_url = (
        f"{public_base_url()}/unsubscribe"
        f"?token={quote(make_unsubscribe_token(user_id), safe='')}"
    )

    name = event.get("event_name", "Activity")
    when = f"{event.get('day_of_week', '')} {event.get('start_time', '')}".strip()
    where = event.get("facility") or event.get("location", "")
    spots = event.get("spots") or "Open"
    url = event.get("detail_url") or ""

    body = f"""
      <p><strong>{html.escape(name)}</strong> just opened up.</p>
      <p>
        {html.escape(when)}<br>
        {html.escape(where)}<br>
        {html.escape(spots)}
      </p>
      <p><a href="{html.escape(url)}">Register on the {html.escape(event.get('source_name', 'city'))} site &rarr;</a></p>
      <p style="color:#6b7280;font-size:12px">
        Spots go quickly — this link opens the city's official registration page.
      </p>
      <hr style="border:none;border-top:1px solid #e2e5ea;margin:20px 0">
      <p style="color:#6b7280;font-size:12px">
        You are receiving this because you turned on email alerts for
        Activity Schedule Dashboard.
        <a href="{html.escape(unsubscribe_url)}">Unsubscribe from these emails</a>.
        Browser notifications, if you use them, are unaffected.
      </p>
      <p style="color:#6b7280;font-size:12px">
        {html.escape(sender_name)}<br>
        {html.escape(sender_address)}
      </p>
    """

    subject = f"Spot open: {name}"
    sender = os.environ.get("ALERT_FROM_EMAIL", "onboarding@resend.dev")

    # Lets Gmail and other clients show their own unsubscribe button, and
    # honours the one-click convention (RFC 8058) by POSTing to the same URL.
    # Bulk senders without these are far more likely to be filtered as spam.
    unsubscribe_headers = {
        "List-Unsubscribe": f"<{unsubscribe_url}>",
        "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
    }

    if provider == "brevo":
        url_endpoint = "https://api.brevo.com/v3/smtp/email"
        headers = {
            "api-key": os.environ["BREVO_API_KEY"],
            "content-type": "application/json",
            "accept": "application/json",
        }
        payload = {
            "sender": {"email": sender, "name": "Activity Schedule Dashboard"},
            "to": [{"email": to_address}],
            "subject": subject,
            "htmlContent": f"<html><body>{body}</body></html>",
            "headers": unsubscribe_headers,
        }
    else:
        url_endpoint = "https://api.resend.com/emails"
        headers = {
            "Authorization": f"Bearer {os.environ['RESEND_API_KEY']}",
            "Content-Type": "application/json",
        }
        payload = {
            "from": sender,
            "to": [to_address],
            "subject": subject,
            "html": body,
            "headers": unsubscribe_headers,
        }

    try:
        resp = requests.post(url_endpoint, headers=headers, json=payload, timeout=15)
        if resp.status_code >= 400:
            logger.warning(
                "%s rejected the alert email to %s: %s %s",
                provider,
                to_address,
                resp.status_code,
                resp.text[:300],
            )
            return False
        return True
    except Exception:
        logger.exception("Failed to send alert email via %s", provider)
        return False


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

    if getattr(user, "email_alerts", False) and user.email:
        if send_email(user.email, event, user.id):
            sent += 1

    return sent


def check_watches(events: list[dict]) -> dict:
    """Compare current availability against stored state and alert on opens.

    `events` is the freshly scraped, normalized event list.
    """
    today = dt.date.today().isoformat()

    # Only users' favourites matter, so build the watcher index up front and
    # skip any occurrence nobody is watching. Keyed by activity (name at a
    # venue) rather than course id, so one star covers every recurring slot
    # of that activity — including ones published after it was starred.
    # A favourite with no venue recorded is keyed with None to match any.
    watchers: dict[tuple, list] = {}
    # Single-session watches are held separately: they name a date, and they
    # are consumed once they fire rather than watching forever.
    session_watchers: dict[tuple, list] = {}
    for fav in Favorite.query.all():
        if fav.scope == "session":
            session_watchers.setdefault(
                (
                    fav.source_name or "",
                    fav.event_name or "",
                    fav.location or "",
                    fav.session_date or "",
                ),
                [],
            ).append(fav)
            continue
        location = fav.location or None
        watchers.setdefault(
            (fav.source_name or "", fav.event_name or "", location), []
        ).append(fav.user)

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
            event_name = event.get("event_name") or ""
            location = event.get("location") or ""
            # Exact venue match, plus legacy favourites recorded without one.
            recipients = watchers.get((source_name, event_name, location), [])
            recipients = recipients + watchers.get((source_name, event_name, None), [])

            # One-off watches for exactly this date, consumed on firing.
            one_offs = session_watchers.pop(
                (source_name, event_name, location, date), []
            )
            recipients = recipients + [f.user for f in one_offs]

            for user in {u.id: u for u in recipients}.values():
                notifications += notify_user(user, event)

            for fav in one_offs:
                db.session.delete(fav)

        if state.was_open != open_now:
            state.was_open = open_now
            state.updated_at = dt.datetime.utcnow()

    # Occurrences in the past can never re-open; drop them so the table does
    # not grow without bound.
    EventState.query.filter(EventState.date < today).delete(synchronize_session=False)

    # A one-off watch for a date that has been and gone can never fire, so
    # retire it rather than leaving dead entries in someone's starred list.
    expired = Favorite.query.filter(
        Favorite.scope == "session",
        Favorite.session_date != "",
        Favorite.session_date < today,
    ).delete(synchronize_session=False)
    if expired:
        logger.info("Retired %d expired one-off watch(es)", expired)

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
