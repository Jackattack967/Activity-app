"""Basic web dashboard for local municipal drop-in activity schedules."""

from __future__ import annotations

import dataclasses
import datetime as dt
import logging
import os
import secrets
import threading
import time
from pathlib import Path

from dotenv import load_dotenv

# Explicit path (not cwd-relative) so this works the same whether launched
# via `python app.py`, the .bat launcher, or gunicorn from anywhere.
load_dotenv(Path(__file__).resolve().parent / ".env")

from flask import Flask, jsonify, render_template, request, send_from_directory
from flask_login import current_user
from werkzeug.middleware.proxy_fix import ProxyFix

import config
import scraper
import watcher
from auth import auth_bp, init_auth
from models import Favorite, Preference, PushSubscription, WatchRun, db, ensure_schema

logger = logging.getLogger(__name__)

app = Flask(__name__)

# Render terminates TLS at its proxy and forwards plain HTTP internally.
# Without this, url_for(_external=True) builds the OAuth redirect URI as
# http:// — which won't match the https:// URI registered with Google.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# Accounts are an optional layer: the schedule dashboard is the core of this
# app and must keep working even if the database or Google credentials are
# missing/misconfigured. Rather than refusing to boot (which takes the whole
# site down over an optional feature), log loudly and run without accounts.
ACCOUNT_ENV_VARS = (
    "DATABASE_URL",
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
    "FLASK_SECRET_KEY",
)
missing_env = [name for name in ACCOUNT_ENV_VARS if not os.environ.get(name)]

app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(32)

ACCOUNTS_ENABLED = False
if missing_env:
    logger.error(
        "Accounts disabled — missing environment variable(s): %s. The schedule "
        "dashboard will still work, but sign-in, synced preferences, and "
        "favorites are unavailable until these are set.",
        ", ".join(missing_env),
    )
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ["DATABASE_URL"]
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}
    try:
        db.init_app(app)
        init_auth(app)
        app.register_blueprint(auth_bp)
        with app.app_context():
            db.create_all()
            ensure_schema()
        ACCOUNTS_ENABLED = True
    except Exception:
        logger.exception(
            "Accounts disabled — failed to initialize the database or Google "
            "sign-in. The schedule dashboard will still work."
        )

_cache_lock = threading.Lock()
_cache: dict = {"events": [], "errors": [], "fetched_at": 0.0}


def _get_events(force: bool = False) -> dict:
    with _cache_lock:
        is_stale = (time.time() - _cache["fetched_at"]) > config.CACHE_TTL_SECONDS
        if force or is_stale or not _cache["fetched_at"]:
            events, errors = scraper.fetch_all_events(
                config.SOURCES, config.SCHEDULE_WINDOW_DAYS
            )
            fresh = [dataclasses.asdict(e) for e in events]
            if not fresh and errors and _cache["events"]:
                # Every source failed. That means the portals were
                # unreachable, not that every session was cancelled — so
                # keep showing the last good schedule rather than blanking
                # the dashboard. fetched_at is left alone so the staleness
                # check retries on the next request.
                logger.warning(
                    "Scrape returned no events with %d source error(s); "
                    "keeping the previously cached schedule.",
                    len(errors),
                )
                _cache["errors"] = errors
            else:
                _cache["events"] = fresh
                _cache["errors"] = errors
                _cache["fetched_at"] = time.time()
        return {
            "events": _cache["events"],
            "errors": _cache["errors"],
            "fetched_at": _cache["fetched_at"],
        }


def _is_logged_in() -> bool:
    """Safe to call even when accounts are disabled (no login manager)."""
    if not ACCOUNTS_ENABLED:
        return False
    try:
        return current_user.is_authenticated
    except Exception:
        return False


def _activity_key(source_name: str, event_name: str, location: str) -> tuple:
    """Identity of a watchable activity: its name at a particular venue.

    Deliberately not the course id — the portal issues one per recurring
    slot, so a single activity spans many of them.
    """
    return (source_name or "", event_name or "", location or "")


def _favorited_keys() -> tuple[set, set]:
    """(activity-wide watches, single-session watches) for the current user."""
    if not _is_logged_in():
        return set(), set()
    activity_keys, session_keys = set(), set()
    for f in current_user.favorites:
        if f.scope == "session":
            session_keys.add(
                (f.source_name or "", f.event_name or "", f.location or "", f.session_date or "")
            )
            continue
        activity_keys.add(_activity_key(f.source_name, f.event_name, f.location))
        if not f.location:
            # Legacy star with no venue recorded: match the name anywhere.
            activity_keys.add((f.source_name or "", f.event_name or "", None))
    return activity_keys, session_keys


def _annotate_favorites(events: list[dict]) -> list[dict]:
    # Cached event dicts are shared across all requests/users — never mutate
    # them in place, or one user's favorite would leak into everyone's view.
    activity_keys, session_keys = _favorited_keys()
    out = []
    for e in events:
        source = e.get("source_name") or ""
        name = e.get("event_name") or ""
        location = e.get("location") or ""
        watched_activity = (
            (source, name, location) in activity_keys
            or (source, name, None) in activity_keys
        )
        watched_session = (source, name, location, e.get("date") or "") in session_keys
        out.append(
            {
                **e,
                "is_favorited": watched_activity or watched_session,
                # Lets the UI say which kind of watch is in effect.
                "favorite_scope": "activity"
                if watched_activity
                else ("session" if watched_session else None),
            }
        )
    return out


def _login_links() -> list[dict]:
    """One login link per distinct city (not per calendar)."""
    seen = set()
    links = []
    for source in config.SOURCES:
        key = (source["source_name"], source["base_url"], source["org_path"])
        if key in seen:
            continue
        seen.add(key)
        links.append(
            {"name": source["source_name"], "url": scraper.build_login_url(source)}
        )
    return links


@app.route("/")
def index():
    data = _get_events()
    events = _annotate_favorites(data["events"])
    activity_types = sorted({e["activity_type"] for e in events})
    locations = sorted({e["location"] for e in events if e["location"]})
    source_names = sorted({s["source_name"] for s in config.SOURCES})
    return render_template(
        "index.html",
        events=events,
        errors=data["errors"],
        fetched_at=data["fetched_at"],
        activity_types=activity_types,
        locations=locations,
        window_days=config.SCHEDULE_WINDOW_DAYS,
        login_links=_login_links(),
        source_names=source_names,
    )


@app.route("/api/watch-status")
def api_watch_status():
    """Is the external scheduler actually calling /api/check-watches?

    Public and read-only: it exposes only whether the watcher ran and its
    aggregate counts, never anything about who is watching what.
    """
    # Whether each alert channel is configured server-side. Booleans about
    # deployment config only — no keys, and nothing about any user.
    channels = {
        "push_configured": bool(os.environ.get("VAPID_PUBLIC_KEY")),
        "email_configured": watcher.email_provider() is not None,
        "email_provider": watcher.email_provider(),
    }

    if not ACCOUNTS_ENABLED:
        return jsonify({"configured": False, "last_run": None, **channels})

    run = WatchRun.query.get(1)
    if run is None or run.ran_at is None:
        return jsonify({"configured": True, "last_run": None, **channels})

    age = (dt.datetime.utcnow() - run.ran_at).total_seconds()
    return jsonify(
        {
            "configured": True,
            "last_run": run.ran_at.isoformat() + "Z",
            "seconds_ago": int(age),
            "checked": run.checked,
            "transitions": run.transitions,
            "notifications_sent": run.notifications_sent,
            # The scheduler is meant to run every 5 min; allow generous slack
            # for cold starts before calling it stalled.
            "healthy": age < 30 * 60,
            **channels,
        }
    )


@app.route("/sw.js")
def service_worker():
    """Serve the service worker from the site root.

    A worker's scope defaults to the directory it is served from, so at
    /static/sw.js it would only control /static/ — never this site's pages.
    navigator.serviceWorker.ready would then never resolve on "/", which
    breaks push subscription.
    """
    response = send_from_directory(
        app.static_folder, "sw.js", mimetype="application/javascript"
    )
    response.headers["Service-Worker-Allowed"] = "/"
    # The worker must be revalidated so push/notification changes reach
    # browsers that already installed an older copy.
    response.headers["Cache-Control"] = "no-cache"
    return response


@app.route("/api/events")
def api_events():
    force = request.args.get("refresh") == "1"
    data = _get_events(force=force)
    return jsonify({**data, "events": _annotate_favorites(data["events"])})


@app.route("/api/preferences", methods=["GET", "POST"])
def api_preferences():
    if not _is_logged_in():
        return jsonify({"error": "not authenticated"}), 401

    if request.method == "POST":
        body = request.get_json(force=True) or {}
        pref = current_user.preference
        if pref is None:
            pref = Preference(user_id=current_user.id)
            db.session.add(pref)
        pref.activity = body.get("activity") or "all"
        pref.location = body.get("location") or ""
        pref.open_only = bool(body.get("openOnly"))
        if "emailAlerts" in body:
            current_user.email_alerts = bool(body.get("emailAlerts"))
        db.session.commit()
        return jsonify({"ok": True})

    pref = current_user.preference
    if pref is None:
        return jsonify({"emailAlerts": bool(current_user.email_alerts)})
    return jsonify(
        {
            "activity": pref.activity,
            "location": pref.location,
            "openOnly": pref.open_only,
            "emailAlerts": bool(current_user.email_alerts),
        }
    )


@app.route("/api/favorites", methods=["GET", "POST"])
def api_favorites():
    if not _is_logged_in():
        return jsonify({"error": "not authenticated"}), 401

    if request.method == "POST":
        body = request.get_json(force=True) or {}
        source_name = (body.get("source_name") or "").strip()
        event_name = (body.get("event_name") or "").strip()
        location = (body.get("location") or "").strip()
        course_id = (body.get("course_id") or "").strip() or None
        scope = "session" if body.get("scope") == "session" else "activity"
        session_date = (body.get("date") or "").strip() if scope == "session" else ""
        if not source_name or not event_name:
            return jsonify({"error": "source_name and event_name are required"}), 400
        if scope == "session" and not session_date:
            return jsonify({"error": "date is required for a session watch"}), 400

        # Any existing watch covering this event is cleared, whichever kind it
        # is — so a second click always means "stop watching this", and you
        # can't end up with overlapping activity and session watches.
        existing = [
            f
            for f in Favorite.query.filter_by(
                user_id=current_user.id,
                source_name=source_name,
                event_name=event_name,
            ).all()
            if (f.location == location or not f.location)
            and (f.scope != "session" or f.session_date == session_date or not session_date)
        ]
        if existing:
            for f in existing:
                db.session.delete(f)
            db.session.commit()
            return jsonify({"favorited": False, "scope": None})

        db.session.add(
            Favorite(
                user_id=current_user.id,
                source_name=source_name,
                event_name=event_name,
                location=location,
                course_id=course_id,
                scope=scope,
                session_date=session_date,
            )
        )
        db.session.commit()
        return jsonify({"favorited": True, "scope": scope})

    return jsonify(
        [
            {
                "source_name": f.source_name,
                "event_name": f.event_name,
                "location": f.location,
                "scope": f.scope,
                "date": f.session_date or None,
            }
            for f in current_user.favorites
        ]
    )


@app.route("/api/push/subscribe", methods=["POST"])
def api_push_subscribe():
    if not _is_logged_in():
        return jsonify({"error": "not authenticated"}), 401

    body = request.get_json(force=True) or {}
    endpoint = (body.get("endpoint") or "").strip()
    keys = body.get("keys") or {}
    p256dh = (keys.get("p256dh") or "").strip()
    auth_key = (keys.get("auth") or "").strip()
    if not endpoint or not p256dh or not auth_key:
        return jsonify({"error": "endpoint and keys are required"}), 400

    existing = PushSubscription.query.filter_by(endpoint=endpoint).first()
    if existing:
        # Re-subscribing on a device that already registered: make sure it
        # belongs to whoever is signed in now, and refresh the keys.
        existing.user_id = current_user.id
        existing.p256dh = p256dh
        existing.auth = auth_key
    else:
        db.session.add(
            PushSubscription(
                user_id=current_user.id,
                endpoint=endpoint,
                p256dh=p256dh,
                auth=auth_key,
            )
        )
    db.session.commit()

    # Confirmation push: proves the whole delivery path works end to end at
    # the moment of setup, rather than leaving the user to wonder until a
    # spot happens to open days later.
    sub = PushSubscription.query.filter_by(endpoint=endpoint).first()
    delivered = False
    if sub is not None:
        delivered = watcher.send_push(
            sub,
            {
                "title": "Alerts are on",
                "body": "You'll get a notification here when a spot opens in a starred activity.",
                "url": "/",
            },
        )
    return jsonify({"ok": True, "test_notification_delivered": delivered})


@app.route("/api/push/unsubscribe", methods=["POST"])
def api_push_unsubscribe():
    if not _is_logged_in():
        return jsonify({"error": "not authenticated"}), 401

    body = request.get_json(force=True) or {}
    endpoint = (body.get("endpoint") or "").strip()
    PushSubscription.query.filter_by(
        user_id=current_user.id, endpoint=endpoint
    ).delete()
    db.session.commit()
    return jsonify({"ok": True})


@app.route("/api/check-watches", methods=["GET", "POST"])
def api_check_watches():
    """Run one watch pass. Called by an external scheduler on a timer, since
    the free Render tier sleeps and cannot poll itself."""
    if not ACCOUNTS_ENABLED:
        return jsonify({"error": "accounts disabled"}), 503

    # Strip whitespace on both sides: pasting env values into dashboards and
    # cron UIs very easily picks up a stray space or newline, which would
    # otherwise fail authentication for no visible reason.
    expected = (os.environ.get("WATCH_CHECK_TOKEN") or "").strip()
    supplied = (
        request.args.get("token") or request.headers.get("X-Watch-Token") or ""
    ).strip()
    if not expected:
        logger.error("WATCH_CHECK_TOKEN is not set — refusing to run watch check.")
        return jsonify({"error": "watch checks not configured"}), 503
    if not secrets.compare_digest(supplied, expected):
        return jsonify({"error": "invalid token"}), 403

    # Force a fresh scrape: comparing against cached data would make alert
    # latency the cache TTL rather than the scheduler's interval. This also
    # refreshes the shared cache, so page loads stay fast *and* current.
    data = _get_events(force=True)
    try:
        result = watcher.check_watches(data["events"])
    except Exception:
        logger.exception("Watch check failed")
        db.session.rollback()
        return jsonify({"error": "watch check failed"}), 500
    return jsonify(result)


@app.context_processor
def inject_user():
    logged_in = _is_logged_in()
    return {
        "accounts_enabled": ACCOUNTS_ENABLED,
        "logged_in": logged_in,
        "current_user_name": current_user.name if logged_in else None,
        "current_user_picture": current_user.picture_url if logged_in else None,
        "vapid_public_key": os.environ.get("VAPID_PUBLIC_KEY", ""),
        "push_enabled": bool(os.environ.get("VAPID_PUBLIC_KEY")) and ACCOUNTS_ENABLED,
        "email_alerts_available": watcher.email_provider() is not None,
    }


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    # 0.0.0.0 so devices on the same WiFi (e.g. a phone) can reach this too,
    # not just the PC it's running on.
    app.run(debug=True, host="0.0.0.0", port=port, use_reloader=False)
