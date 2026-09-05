"""Database models: signed-in users, their saved preferences, and favorites."""

from __future__ import annotations

import datetime as dt

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Columns added to tables that already exist in a deployed database.
# db.create_all() only creates missing *tables*, never missing columns, so
# new fields on an existing model need an explicit (idempotent) migration.
_ADDITIVE_MIGRATIONS = (
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS "
    "email_alerts BOOLEAN NOT NULL DEFAULT FALSE",
    # Favourites moved from per-course to per-activity matching.
    "ALTER TABLE favorites ADD COLUMN IF NOT EXISTS "
    "location VARCHAR(255) NOT NULL DEFAULT ''",
    "ALTER TABLE favorites ALTER COLUMN course_id DROP NOT NULL",
    # Watches can be activity-wide or a single dated session.
    "ALTER TABLE favorites ADD COLUMN IF NOT EXISTS "
    "scope VARCHAR(20) NOT NULL DEFAULT 'activity'",
    "ALTER TABLE favorites ADD COLUMN IF NOT EXISTS "
    "session_date VARCHAR(10) NOT NULL DEFAULT ''",
    "ALTER TABLE favorites DROP CONSTRAINT IF EXISTS uq_favorite_user_activity",
    # Retention needs to know when an account was last used. Existing rows
    # have no history, so they are seeded from created_at — the earliest
    # defensible guess, and one that can only delay a deletion, never
    # trigger one early.
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMP",
    "UPDATE users SET last_seen_at = created_at WHERE last_seen_at IS NULL",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS deletion_warned_at TIMESTAMP",
    # The dashboard covers more than one city now, so a saved filter
    # includes which area to show. Empty means all of them.
    "ALTER TABLE preferences ADD COLUMN IF NOT EXISTS "
    "area VARCHAR(100) NOT NULL DEFAULT ''",
    """
    DO $$ BEGIN
      IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'uq_favorite_user_watch'
      ) THEN
        ALTER TABLE favorites ADD CONSTRAINT uq_favorite_user_watch
          UNIQUE (user_id, source_name, event_name, location, scope, session_date);
      END IF;
    END $$;
    """,
)


def ensure_schema() -> None:
    """Apply additive schema changes. Safe to run on every startup."""
    for statement in _ADDITIVE_MIGRATIONS:
        db.session.execute(db.text(statement))
    db.session.commit()


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    google_sub = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(255))
    picture_url = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=dt.datetime.utcnow)
    # Opt-in: alerts go out by push unless the user also asks for email.
    email_alerts = db.Column(db.Boolean, nullable=False, default=False)

    # Last time this account was actually used, refreshed on sign-in and on
    # authenticated requests. This is the only signal retention has: without
    # it "inactive" could only mean "signed up long ago", which would delete
    # people who use the app every week.
    last_seen_at = db.Column(db.DateTime, default=dt.datetime.utcnow)
    # When the "your account is about to be deleted" email went out. NULL
    # means no warning has been sent, and retention refuses to delete an
    # account that has not been warned — so a mail outage stalls deletion
    # instead of silently destroying accounts nobody was told about.
    deletion_warned_at = db.Column(db.DateTime)

    preference = db.relationship(
        "Preference", backref="user", uselist=False, cascade="all, delete-orphan"
    )
    favorites = db.relationship(
        "Favorite", backref="user", cascade="all, delete-orphan"
    )
    push_subscriptions = db.relationship(
        "PushSubscription", backref="user", cascade="all, delete-orphan"
    )


class Preference(db.Model):
    __tablename__ = "preferences"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True
    )
    activity = db.Column(db.String(50), default="all")
    location = db.Column(db.String(255), default="")
    area = db.Column(db.String(100), default="")
    open_only = db.Column(db.Boolean, default=False)


class Favorite(db.Model):
    """A watched activity, matched by name and venue rather than by course id.

    The portal issues a separate course id per recurring slot, so "Stick,
    Ring & Puck" at one complex spans eleven of them — starring by course id
    meant clicking the same activity eleven times and still missing any slot
    published later. Matching on (name, location) collapses those into one
    star while keeping genuinely different venues apart: Public Swim at Rocky
    Point stays distinct from Public Swim at Westhill.

    course_id is retained only as a record of what was originally starred.
    """

    __tablename__ = "favorites"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    source_name = db.Column(db.String(100), nullable=False)
    event_name = db.Column(db.String(255), nullable=False)
    location = db.Column(db.String(255), nullable=False, default="")
    course_id = db.Column(db.String(50))

    # "activity" watches every session of this activity indefinitely.
    # "session" watches one dated occurrence and removes itself once it has
    # alerted, or once that date has passed.
    scope = db.Column(db.String(20), nullable=False, default="activity")
    # Empty for activity-wide watches; the ISO date for one-off ones. Empty
    # rather than NULL so the uniqueness constraint actually applies —
    # Postgres treats NULLs as distinct.
    session_date = db.Column(db.String(10), nullable=False, default="")

    __table_args__ = (
        db.UniqueConstraint(
            "user_id",
            "source_name",
            "event_name",
            "location",
            "scope",
            "session_date",
            name="uq_favorite_user_watch",
        ),
    )


class EventState(db.Model):
    """Last-seen availability of a single occurrence, so the watcher can spot
    a closed -> open transition. Stored once globally rather than per user:
    availability is a property of the session, not of who is watching it.
    """

    __tablename__ = "event_states"

    id = db.Column(db.Integer, primary_key=True)
    source_name = db.Column(db.String(100), nullable=False)
    course_id = db.Column(db.String(50), nullable=False)
    date = db.Column(db.String(10), nullable=False)  # ISO YYYY-MM-DD
    was_open = db.Column(db.Boolean, nullable=False, default=False)
    updated_at = db.Column(db.DateTime, default=dt.datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint(
            "source_name", "course_id", "date", name="uq_event_state_occurrence"
        ),
    )


class WatchRun(db.Model):
    """Heartbeat for the watcher: a single row, overwritten on every run.

    Exists so "is my alerting actually running?" is answerable from the
    dashboard itself, rather than from the external scheduler's logs.
    """

    __tablename__ = "watch_runs"

    id = db.Column(db.Integer, primary_key=True)
    ran_at = db.Column(db.DateTime, default=dt.datetime.utcnow)
    checked = db.Column(db.Integer, default=0)
    transitions = db.Column(db.Integer, default=0)
    notifications_sent = db.Column(db.Integer, default=0)


class PushSubscription(db.Model):
    """A browser/PWA push endpoint belonging to a user. One user can have
    several (phone, laptop, ...)."""

    __tablename__ = "push_subscriptions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    endpoint = db.Column(db.String(500), unique=True, nullable=False)
    p256dh = db.Column(db.String(200), nullable=False)
    auth = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=dt.datetime.utcnow)
