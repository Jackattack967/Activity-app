"""Database models: signed-in users, their saved preferences, and favorites."""

from __future__ import annotations

import datetime as dt

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    google_sub = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(255))
    picture_url = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=dt.datetime.utcnow)

    preference = db.relationship(
        "Preference", backref="user", uselist=False, cascade="all, delete-orphan"
    )
    favorites = db.relationship(
        "Favorite", backref="user", cascade="all, delete-orphan"
    )


class Preference(db.Model):
    __tablename__ = "preferences"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True
    )
    activity = db.Column(db.String(50), default="all")
    location = db.Column(db.String(255), default="")
    open_only = db.Column(db.Boolean, default=False)


class Favorite(db.Model):
    """A starred recurring activity, identified by its stable course_id
    (not the per-occurrence event id, which changes every date)."""

    __tablename__ = "favorites"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    source_name = db.Column(db.String(100), nullable=False)
    course_id = db.Column(db.String(50), nullable=False)
    event_name = db.Column(db.String(255), nullable=False)

    __table_args__ = (
        db.UniqueConstraint(
            "user_id", "source_name", "course_id", name="uq_favorite_user_course"
        ),
    )
