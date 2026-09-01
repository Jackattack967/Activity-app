"""Signed, stateless tokens for the unsubscribe links in alert emails.

An unsubscribe link has to work straight from an email client, without the
recipient signing in first — that is the whole point of it. So the link
carries a token naming the user rather than relying on a session cookie.

The token is signed with the app's secret key. That means it cannot be
forged, and it cannot be edited to name a different user without the
signature failing, so one person's link can never unsubscribe anyone else.
Nothing has to be stored in the database for a token to be valid.

There is deliberately no expiry: CASL requires an unsubscribe mechanism to
stay working for at least 60 days after the message is sent, and a token
that never goes stale satisfies that without any bookkeeping. Rotating
FLASK_SECRET_KEY invalidates every previously issued link, which is the one
thing to be aware of before changing it.
"""

from __future__ import annotations

import os

from itsdangerous import BadSignature, URLSafeSerializer

# Namespaces these tokens so a signature is only ever accepted for this one
# purpose, even though other features share the same secret key.
_SALT = "unsubscribe-v1"


def _serializer() -> URLSafeSerializer:
    secret = (os.environ.get("FLASK_SECRET_KEY") or "").strip()
    if not secret:
        raise RuntimeError(
            "FLASK_SECRET_KEY must be set to sign unsubscribe links. Without a "
            "stable key, links would stop working on every restart."
        )
    return URLSafeSerializer(secret, salt=_SALT)


def make_unsubscribe_token(user_id: int) -> str:
    """Token identifying one user, for embedding in an unsubscribe URL."""
    return _serializer().dumps({"uid": int(user_id)})


def read_unsubscribe_token(token: str) -> int | None:
    """The user id a token names, or None if it is missing, altered or forged."""
    if not token:
        return None
    try:
        data = _serializer().loads(token)
    except (BadSignature, RuntimeError):
        return None
    uid = data.get("uid") if isinstance(data, dict) else None
    return uid if isinstance(uid, int) else None
