"""Exercise retention.run() against a real (sqlite) database.

Run with:  .venv\\Scripts\\python.exe test_retention.py
Exits non-zero if anything fails, so CI can run it as-is.

Deliberately builds its own tiny Flask app on an in-memory sqlite database
instead of importing app.py. Importing app.py would read .env, connect to the
real Postgres and run ensure_schema against it — a test must never be able to
touch production data, least of all a test about deleting accounts.

No email can escape either: send_deletion_warning is replaced with a stub, so
a bug here cannot mail a real person that their account is about to go.
"""
import datetime as dt
import os
import sys

os.environ["RETENTION_INACTIVE_DAYS"] = "180"
os.environ["RETENTION_WARN_DAYS"] = "30"
os.environ.pop("RETENTION_ENABLED", None)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from models import Favorite, PushSubscription, User, db
import retention
import watcher

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
db.init_app(app)

sent = []
watcher.send_deletion_warning = lambda user, days: (sent.append((user.id, days)), True)[1]

now = dt.datetime.utcnow()
FAIL = []


def check(label, got, want):
    ok = got == want
    print(f"  {'PASS' if ok else 'FAIL'}  {label}: got {got!r}, want {want!r}")
    if not ok:
        FAIL.append(label)


def mkuser(sub, days_idle, warned_days_ago=None):
    u = User(google_sub=sub, email=f"{sub}@example.com", name=sub)
    u.created_at = now - dt.timedelta(days=400)
    u.last_seen_at = now - dt.timedelta(days=days_idle)
    if warned_days_ago is not None:
        u.deletion_warned_at = now - dt.timedelta(days=warned_days_ago)
    db.session.add(u)
    return u


with app.app_context():
    db.create_all()

    active = mkuser("active", 3)
    almost = mkuser("almost", 149)          # one day short of the warn line
    due_warn = mkuser("due_warn", 151)      # past the warn line, never warned
    warned_recently = mkuser("warned_recently", 181, warned_days_ago=2)
    warned_long = mkuser("warned_long", 181, warned_days_ago=31)
    never_warned_old = mkuser("never_warned_old", 900)  # ancient but unwarned
    unknown = mkuser("unknown", 0)
    unknown.last_seen_at = None
    db.session.commit()

    # Give one deletable user dependent rows, to prove they go too.
    db.session.add(Favorite(user_id=warned_long.id, source_name="s",
                            event_name="Public Swim", location="Rec Centre"))
    db.session.add(PushSubscription(user_id=warned_long.id, endpoint="https://x/1",
                                    p256dh="k", auth="a"))
    db.session.commit()

    print("\n1. DRY RUN (default, unarmed)")
    r = retention.run()
    check("dry_run flag", r["dry_run"], True)
    # Only the not-yet-warned: an existing warning is never re-sent.
    check("would warn", sorted(r["would_warn"]),
          sorted([due_warn.id, never_warned_old.id]))
    check("would delete", sorted(r["would_delete"]), [warned_long.id])
    check("nothing actually warned", r["warned"], 0)
    check("nothing actually deleted", r["deleted"], 0)
    check("no email sent in dry run", len(sent), 0)
    check("all users still present", User.query.count(), 7)

    print("\n   ...wait: would_warn includes already-warned users?")
    check("warned_recently should NOT be re-warned",
          warned_recently.id in r["would_warn"], False)

    print("\n2. ARMED RUN")
    os.environ["RETENTION_ENABLED"] = "true"
    r = retention.run()
    check("dry_run flag", r["dry_run"], False)
    check("emails sent", len(sent), r["warned"])
    check("warned_long deleted", User.query.filter_by(google_sub="warned_long").count(), 0)
    check("its favorites deleted",
          Favorite.query.filter_by(user_id=warned_long.id).count(), 0)
    check("its push subs deleted",
          PushSubscription.query.filter_by(user_id=warned_long.id).count(), 0)
    check("active user untouched",
          User.query.filter_by(google_sub="active").count(), 1)
    check("almost-idle user untouched",
          User.query.filter_by(google_sub="almost").first().deletion_warned_at, None)
    check("unknown last_seen never touched",
          User.query.filter_by(google_sub="unknown").first().deletion_warned_at, None)
    check("ancient-but-unwarned survives this run",
          User.query.filter_by(google_sub="never_warned_old").count(), 1)

    print("\n3. WARNING EMAIL FAILS -> no deletion possible")
    watcher.send_deletion_warning = lambda user, days: False
    fresh = mkuser("mailfail", 900)
    db.session.commit()
    retention.run()
    u = User.query.filter_by(google_sub="mailfail").first()
    check("still exists", u is not None, True)
    check("not stamped as warned", u.deletion_warned_at, None)

    print("\n4. COMING BACK CANCELS DELETION")
    watcher.send_deletion_warning = lambda user, days: (sent.append((user.id, days)), True)[1]
    back = User.query.filter_by(google_sub="never_warned_old").first()
    retention.run()
    check("was warned", back.deletion_warned_at is not None, True)
    back.last_seen_at = dt.datetime.utcnow()   # simulates sign-in
    back.deletion_warned_at = None
    db.session.commit()
    r = retention.run()
    check("no longer due for deletion", back.id in r["would_delete"], False)
    check("no longer due for warning", back.id in r["would_warn"], False)

print("\n" + ("ALL PASSED" if not FAIL else f"FAILURES: {FAIL}"))
sys.exit(1 if FAIL else 0)
