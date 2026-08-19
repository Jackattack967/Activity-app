"""Basic web dashboard for local municipal drop-in activity schedules."""

from __future__ import annotations

import dataclasses
import os
import threading
import time
from pathlib import Path

from dotenv import load_dotenv

# Explicit path (not cwd-relative) so this works the same whether launched
# via `python app.py`, the .bat launcher, or gunicorn from anywhere.
load_dotenv(Path(__file__).resolve().parent / ".env")

from flask import Flask, jsonify, render_template, request
from flask_login import current_user
from werkzeug.middleware.proxy_fix import ProxyFix

import config
import scraper
from auth import auth_bp, init_auth
from models import Favorite, Preference, db

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ["FLASK_SECRET_KEY"]
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ["DATABASE_URL"]
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}

# Render terminates TLS at its proxy and forwards plain HTTP internally.
# Without this, url_for(_external=True) builds the OAuth redirect URI as
# http:// — which won't match the https:// URI registered with Google.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

db.init_app(app)
init_auth(app)
app.register_blueprint(auth_bp)

with app.app_context():
    db.create_all()

_cache_lock = threading.Lock()
_cache: dict = {"events": [], "errors": [], "fetched_at": 0.0}


def _get_events(force: bool = False) -> dict:
    with _cache_lock:
        is_stale = (time.time() - _cache["fetched_at"]) > config.CACHE_TTL_SECONDS
        if force or is_stale or not _cache["fetched_at"]:
            events, errors = scraper.fetch_all_events(
                config.SOURCES, config.SCHEDULE_WINDOW_DAYS
            )
            _cache["events"] = [dataclasses.asdict(e) for e in events]
            _cache["errors"] = errors
            _cache["fetched_at"] = time.time()
        return {
            "events": _cache["events"],
            "errors": _cache["errors"],
            "fetched_at": _cache["fetched_at"],
        }


def _favorited_course_ids() -> set[tuple[str, str]]:
    if not current_user.is_authenticated:
        return set()
    return {(f.source_name, f.course_id) for f in current_user.favorites}


def _annotate_favorites(events: list[dict]) -> list[dict]:
    # Cached event dicts are shared across all requests/users — never mutate
    # them in place, or one user's favorite would leak into everyone's view.
    favorited = _favorited_course_ids()
    return [
        {**e, "is_favorited": (e.get("source_name"), e.get("course_id")) in favorited}
        for e in events
    ]


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


@app.route("/api/events")
def api_events():
    force = request.args.get("refresh") == "1"
    data = _get_events(force=force)
    return jsonify({**data, "events": _annotate_favorites(data["events"])})


@app.route("/api/preferences", methods=["GET", "POST"])
def api_preferences():
    if not current_user.is_authenticated:
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
        db.session.commit()
        return jsonify({"ok": True})

    pref = current_user.preference
    if pref is None:
        return jsonify(None)
    return jsonify(
        {"activity": pref.activity, "location": pref.location, "openOnly": pref.open_only}
    )


@app.route("/api/favorites", methods=["GET", "POST"])
def api_favorites():
    if not current_user.is_authenticated:
        return jsonify({"error": "not authenticated"}), 401

    if request.method == "POST":
        body = request.get_json(force=True) or {}
        source_name = (body.get("source_name") or "").strip()
        course_id = (body.get("course_id") or "").strip()
        event_name = (body.get("event_name") or "").strip()
        if not source_name or not course_id:
            return jsonify({"error": "source_name and course_id are required"}), 400

        existing = Favorite.query.filter_by(
            user_id=current_user.id, source_name=source_name, course_id=course_id
        ).first()
        if existing:
            db.session.delete(existing)
            db.session.commit()
            return jsonify({"favorited": False})

        db.session.add(
            Favorite(
                user_id=current_user.id,
                source_name=source_name,
                course_id=course_id,
                event_name=event_name,
            )
        )
        db.session.commit()
        return jsonify({"favorited": True})

    return jsonify(
        [
            {"source_name": f.source_name, "course_id": f.course_id, "event_name": f.event_name}
            for f in current_user.favorites
        ]
    )


@app.context_processor
def inject_user():
    return {
        "logged_in": current_user.is_authenticated,
        "current_user_name": current_user.name if current_user.is_authenticated else None,
        "current_user_picture": current_user.picture_url if current_user.is_authenticated else None,
    }


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    # 0.0.0.0 so devices on the same WiFi (e.g. a phone) can reach this too,
    # not just the PC it's running on.
    app.run(debug=True, host="0.0.0.0", port=port, use_reloader=False)
