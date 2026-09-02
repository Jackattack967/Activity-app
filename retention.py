"""Deleting accounts that nobody uses any more.

Holding someone's data forever because they signed up once and drifted away
is exactly what privacy law asks you not to do: PIPEDA says personal
information should be kept only as long as it is needed for the purpose it
was collected for. An account that has not been touched in six months is no
longer serving that purpose.

The rule, in order:

  * Inactive for RETENTION_INACTIVE_DAYS - RETENTION_WARN_DAYS  -> warn once.
  * Warned, and RETENTION_WARN_DAYS have passed since            -> delete.
  * Signed in or used the app at any point                       -> reset.

Two safety properties are deliberate and worth not "simplifying" away:

1. **No deletion without a warning that actually sent.** deletion_warned_at
   is only stamped when the provider accepted the message, and deletion
   requires that stamp. If email breaks, deletions stall — which is the
   correct failure direction for something irreversible.

2. **Dry run unless explicitly armed.** RETENTION_ENABLED must be set before
   anything is deleted or any warning goes out. Until then the job reports
   what it would have done, so the date arithmetic can be watched against
   real data before it is trusted with real accounts.
"""

from __future__ import annotations

import datetime as dt
import logging
import os

import watcher
from models import Favorite, Preference, PushSubscription, User, db

logger = logging.getLogger(__name__)

# Six months of no use. Overridable so the window can be tuned without a
# code change, and so tests can use a short one.
INACTIVE_DAYS = int(os.environ.get("RETENTION_INACTIVE_DAYS", "180"))
# How much notice someone gets. This is subtracted from the window rather
# than added to it: the promise is "deleted after six months", and the
# warning lands 30 days before that, not 30 days after.
WARN_DAYS = int(os.environ.get("RETENTION_WARN_DAYS", "30"))


def is_armed() -> bool:
    """Whether the job may actually change anything."""
    return (os.environ.get("RETENTION_ENABLED") or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def purge_user(user: User) -> dict:
    """Delete one account and everything belonging to it.

    Dependants are removed explicitly rather than through cascade, matching
    the user-initiated deletion path: a misconfigured relationship should
    not be able to leave someone's data behind after we have reported it
    gone. Does not commit — the caller decides the transaction boundary.
    """
    user_id = user.id
    removed = {
        "favorites": Favorite.query.filter_by(user_id=user_id).delete(),
        "preferences": Preference.query.filter_by(user_id=user_id).delete(),
        "push_subscriptions": PushSubscription.query.filter_by(
            user_id=user_id
        ).delete(),
    }
    db.session.delete(user)
    return removed


def run(dry_run: bool | None = None) -> dict:
    """One retention pass: warn the newly-idle, delete the long-warned.

    Safe to call as often as you like. Warnings are sent once because
    deletion_warned_at is checked, and an account that comes back has that
    stamp cleared, so returning users re-enter the cycle from the start.
    """
    if dry_run is None:
        dry_run = not is_armed()

    now = dt.datetime.utcnow()
    warn_cutoff = now - dt.timedelta(days=INACTIVE_DAYS - WARN_DAYS)
    idle_cutoff = now - dt.timedelta(days=INACTIVE_DAYS)
    warned_cutoff = now - dt.timedelta(days=WARN_DAYS)

    result = {
        "dry_run": dry_run,
        "inactive_days": INACTIVE_DAYS,
        "warn_days": WARN_DAYS,
        "warned": 0,
        "warn_failed": 0,
        "deleted": 0,
        "would_warn": [],
        "would_delete": [],
    }

    # --- Warn ---------------------------------------------------------
    # last_seen_at is NULL only for rows written before the column existed
    # and never migrated; treat those as unknown rather than ancient, since
    # guessing "ancient" would delete them.
    due_warning = User.query.filter(
        User.last_seen_at.isnot(None),
        User.last_seen_at <= warn_cutoff,
        User.deletion_warned_at.is_(None),
    ).all()

    for user in due_warning:
        result["would_warn"].append(user.id)
        if dry_run:
            continue
        days_left = INACTIVE_DAYS - (now - user.last_seen_at).days
        # Never promise less notice than the policy gives, even if the job
        # was down for a while and this warning is going out late.
        days_left = max(days_left, 1)
        if watcher.send_deletion_warning(user, days_left):
            user.deletion_warned_at = now
            result["warned"] += 1
        else:
            # Left unstamped on purpose: it will be retried next run, and
            # until it succeeds this account cannot be deleted.
            result["warn_failed"] += 1

    # --- Delete -------------------------------------------------------
    due_deletion = User.query.filter(
        User.last_seen_at.isnot(None),
        User.last_seen_at <= idle_cutoff,
        User.deletion_warned_at.isnot(None),
        User.deletion_warned_at <= warned_cutoff,
    ).all()

    for user in due_deletion:
        result["would_delete"].append(user.id)
        if dry_run:
            continue
        removed = purge_user(user)
        logger.info(
            "Retention: deleted inactive account %s (last seen %s, warned %s): %s",
            user.id,
            user.last_seen_at,
            user.deletion_warned_at,
            removed,
        )
        result["deleted"] += 1

    if dry_run:
        db.session.rollback()
        logger.info(
            "Retention dry run: would warn %s account(s) %s and delete %s "
            "account(s) %s. Set RETENTION_ENABLED=true to act on this.",
            len(result["would_warn"]),
            result["would_warn"],
            len(result["would_delete"]),
            result["would_delete"],
        )
    else:
        db.session.commit()
        logger.info(
            "Retention: warned %s, failed to warn %s, deleted %s",
            result["warned"],
            result["warn_failed"],
            result["deleted"],
        )

    return result
