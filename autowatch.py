"""Run watch passes from inside the app, instead of only when asked to.

Why this exists
---------------
Alerting used to depend entirely on an external scheduler calling
/api/check-watches every five minutes. That turned out to be fragile in a way
that is worth writing down, because the failure is not obvious:

  * Render's free tier sleeps after ~15 minutes with no inbound request, and
    a cold start measured 31.5 seconds.
  * cron-job.org's execution timeout is a hard 30 seconds, and it disables a
    job automatically after more than 25 consecutive failures.

So every ping that arrives while the app is asleep times out — 1.5 seconds
over the limit — and 25 of those in a row (about two hours at five-minute
intervals) switches the job off for good. That is exactly what happened on
2026-08-31 and again on 2026-09-01, the second time silently.

A thread inside the app cannot be disabled by a third party and has no
timeout, so while the app is awake, alerting now runs on its own.

What this does NOT fix
----------------------
This thread cannot keep the app awake: Render spins down on inbound *request*
inactivity, and a busy background thread does not count. So something
external still has to wake the app in the morning.

The difference is the bar that external waker has to clear. It used to have
to fire reliably every five minutes, all day — which GitHub Actions demonstrably
does not do, dropping most of a */10 schedule. Now it only has to land once,
some time in the morning. That is a bar the throttled scheduler actually meets.

Deferring to the external scheduler
-----------------------------------
When the external cron *is* healthy, this thread should stay out of its way
rather than double every scrape. Before running, it checks how long ago the
last pass was — by any caller — and skips if that was recent. So the two
arrange themselves automatically: the cron drives things while it works, and
this takes over within one interval when it stops.
"""

from __future__ import annotations

import datetime as dt
import logging
import os
import threading
import time

from models import WatchRun, db

logger = logging.getLogger(__name__)

# How often the thread considers running a pass.
INTERVAL = int(os.environ.get("AUTOWATCH_INTERVAL_SECONDS", "300"))
# Skip if any pass — this thread's or the external scheduler's — ran more
# recently than this. Slightly below INTERVAL so that ordinary jitter does
# not make the thread skip its own turn.
MIN_GAP = int(os.environ.get("AUTOWATCH_MIN_GAP_SECONDS", "240"))
# The app has just booted when the thread starts, and something woke it —
# quite possibly the first traffic in hours. Check soon rather than idling
# for a full interval first.
INITIAL_DELAY = int(os.environ.get("AUTOWATCH_INITIAL_DELAY_SECONDS", "60"))

# Serialises passes within this process, so the thread and an inbound
# /api/check-watches request can never scrape and alert at the same time.
# Without this, two concurrent passes could both see the same closed -> open
# transition and both notify for it.
_pass_lock = threading.Lock()
_started = False


def enabled() -> bool:
    """On by default; AUTOWATCH_ENABLED=false turns it off.

    Worth being able to turn off without a deploy: if this thread ever
    misbehaves, alerting should be able to fall back to the external
    scheduler alone.
    """
    return (os.environ.get("AUTOWATCH_ENABLED") or "true").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }


def started() -> bool:
    """Whether the background thread is running in this process."""
    return _started


def seconds_since_last_run() -> float | None:
    """Age of the shared heartbeat, or None if nothing has ever run.

    Read from the database rather than from a variable in this process, so
    it accounts for passes run by the external scheduler too.
    """
    run = db.session.get(WatchRun, 1)
    if run is None or run.ran_at is None:
        return None
    return (dt.datetime.utcnow() - run.ran_at).total_seconds()


def run_pass(fn):
    """Run one watch pass, never concurrently with another in this process."""
    with _pass_lock:
        return fn()


def _loop(app, fn) -> None:
    time.sleep(INITIAL_DELAY)
    while True:
        try:
            with app.app_context():
                since = seconds_since_last_run()
                if since is not None and since < MIN_GAP:
                    logger.debug(
                        "autowatch: skipping, a pass ran %.0fs ago", since
                    )
                else:
                    result = run_pass(fn)
                    logger.info("autowatch: ran a watch pass: %s", result)
        except Exception:
            # A failed pass must never kill the thread — that would put us
            # straight back to depending on the external scheduler alone,
            # and silently, which is the whole problem this solves.
            logger.exception("autowatch: watch pass failed; continuing")
            try:
                with app.app_context():
                    db.session.rollback()
            except Exception:
                logger.exception("autowatch: could not roll back after failure")

        time.sleep(INTERVAL)


def start(app, fn) -> bool:
    """Start the background thread. Returns whether it was started.

    Safe to call more than once; only the first call does anything.
    """
    global _started

    if not enabled():
        logger.info("autowatch: disabled by AUTOWATCH_ENABLED")
        return False
    if _started:
        return False

    # A daemon thread so it never holds up shutdown. Losing a pass on
    # restart costs nothing: the next one recomputes everything from the
    # portal and the stored state.
    #
    # Note this starts one thread per process. The service runs
    # --workers 1, so that is one thread; if the worker count is ever
    # raised, the MIN_GAP check above keeps the extra threads from
    # duplicating work rather than leaving them to fight.
    thread = threading.Thread(
        target=_loop, args=(app, fn), name="autowatch", daemon=True
    )
    thread.start()
    _started = True
    logger.info(
        "autowatch: started; a pass every %ss unless one ran in the last %ss",
        INTERVAL,
        MIN_GAP,
    )
    return True
