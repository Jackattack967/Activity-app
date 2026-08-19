"""Basic web dashboard for local municipal drop-in activity schedules."""

from __future__ import annotations

import dataclasses
import threading
import time

from flask import Flask, jsonify, render_template, request

import config
import scraper

app = Flask(__name__)

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


@app.route("/")
def index():
    data = _get_events()
    activity_types = sorted({e["activity_type"] for e in data["events"]})
    locations = sorted({e["location"] for e in data["events"] if e["location"]})
    login_url = scraper.build_login_url(config.SOURCES[0]) if config.SOURCES else None
    return render_template(
        "index.html",
        events=data["events"],
        errors=data["errors"],
        fetched_at=data["fetched_at"],
        activity_types=activity_types,
        locations=locations,
        window_days=config.SCHEDULE_WINDOW_DAYS,
        login_url=login_url,
    )


@app.route("/api/events")
def api_events():
    force = request.args.get("refresh") == "1"
    data = _get_events(force=force)
    return jsonify(data)


if __name__ == "__main__":
    import os

    port = int(os.environ.get("PORT", 8000))
    # 0.0.0.0 so devices on the same WiFi (e.g. a phone) can reach this too,
    # not just the PC it's running on.
    app.run(debug=True, host="0.0.0.0", port=port, use_reloader=False)
