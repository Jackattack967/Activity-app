"""Google sign-in via Authlib (OpenID Connect) + Flask-Login session wiring.

We never see or store a password — Google authenticates the user and hands
back a verified identity (a stable "sub" id, email, name, picture), which is
all we persist.
"""

from __future__ import annotations

import os

from authlib.integrations.flask_client import OAuth
from flask import Blueprint, redirect, url_for
from flask_login import LoginManager, login_user, logout_user

from models import User, db

login_manager = LoginManager()
oauth = OAuth()

auth_bp = Blueprint("auth", __name__)


def init_auth(app):
    login_manager.init_app(app)
    oauth.init_app(app)
    oauth.register(
        name="google",
        client_id=os.environ["GOOGLE_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )


@login_manager.user_loader
def load_user(user_id: str):
    return db.session.get(User, int(user_id))


@auth_bp.route("/login/google")
def login_google():
    redirect_uri = url_for("auth.google_callback", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@auth_bp.route("/login/google/callback")
def google_callback():
    token = oauth.google.authorize_access_token()
    userinfo = token.get("userinfo") or {}
    google_sub = userinfo.get("sub")
    if not google_sub:
        return redirect(url_for("index"))

    user = User.query.filter_by(google_sub=google_sub).first()
    if user is None:
        user = User(
            google_sub=google_sub,
            email=userinfo.get("email", ""),
            name=userinfo.get("name", ""),
            picture_url=userinfo.get("picture", ""),
        )
        db.session.add(user)
        db.session.commit()

    login_user(user)
    return redirect(url_for("index"))


@auth_bp.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("index"))
