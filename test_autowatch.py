"""Exercise the in-app watch loop.

Run with:  .venv\\Scripts\\python.exe test_autowatch.py
Exits non-zero if anything fails.

Uses a throwaway sqlite database and a stub pass that only counts calls, so
nothing here scrapes a city portal or sends an alert. Intervals are shortened
to seconds via the environment, which is why they are configurable at all.
"""
import datetime as dt
import os
import sys
import time

# Must be set before autowatch is imported — it reads these at import time.
os.environ["AUTOWATCH_INTERVAL_SECONDS"] = "1"
os.environ["AUTOWATCH_MIN_GAP_SECONDS"] = "3"
os.environ["AUTOWATCH_INITIAL_DELAY_SECONDS"] = "0"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from models import WatchRun, db
import autowatch

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
db.init_app(app)

FAIL = []


def check(label, got, want):
    ok = got == want
    print(f"  {'PASS' if ok else 'FAIL'}  {label}: got {got!r}, want {want!r}")
    if not ok:
        FAIL.append(label)


def set_heartbeat(seconds_ago):
    """Pretend a pass ran this many seconds ago, by any caller."""
    run = db.session.get(WatchRun, 1) or WatchRun(id=1)
    run.ran_at = dt.datetime.utcnow() - dt.timedelta(seconds=seconds_ago)
    db.session.add(run)
    db.session.commit()


calls = []
# One loop runs for the whole test, and this switches what its pass does.
# Starting a second loop instead would make the two fight over the shared
# heartbeat — which is correct behaviour, but not what is being tested here.
behaviour = {"mode": "ok"}


def fake_pass():
    calls.append(time.time())
    if behaviour["mode"] == "boom":
        raise RuntimeError("simulated scrape failure")
    # Stamp the heartbeat the way a real pass does, so the skip logic sees it.
    set_heartbeat(0)
    return {"checked": 0}


with app.app_context():
    db.create_all()

    print("\n1. CONFIG READ FROM ENVIRONMENT")
    check("interval", autowatch.INTERVAL, 1)
    check("min gap", autowatch.MIN_GAP, 3)
    check("enabled by default", autowatch.enabled(), True)
    check("not started yet", autowatch.started(), False)

    print("\n2. DEFERS TO A RECENT PASS BY SOMEONE ELSE")
    # Simulates the external scheduler having just run.
    set_heartbeat(0)
    check("age is ~0s", int(autowatch.seconds_since_last_run()), 0)

autowatch.start(app, fake_pass)
check("started", autowatch.started(), True)

# Heartbeat is fresh, so the loop should sit out its first few turns.
time.sleep(2.2)
check("no pass ran while heartbeat was fresh", len(calls), 0)

print("\n3. TAKES OVER ONCE THE HEARTBEAT GOES STALE")
with app.app_context():
    set_heartbeat(60)  # as if the external scheduler died a minute ago
time.sleep(2.2)
ran = len(calls)
check("took over", ran >= 1, True)

print("\n4. DOES NOT RUN FLAT OUT ONCE IT HAS TAKEN OVER")
# Its own passes stamp the heartbeat, so MIN_GAP should throttle it.
time.sleep(2.2)
check("throttled by its own heartbeat", len(calls) - ran <= 1, True)

print("\n5. START IS IDEMPOTENT")
check("second start is a no-op", autowatch.start(app, fake_pass), False)

print("\n6. A FAILING PASS DOES NOT KILL THE THREAD")
# The same loop, now raising every time. A failing pass never stamps the
# heartbeat, so it stays stale and the loop should retry on every turn.
behaviour["mode"] = "boom"
with app.app_context():
    set_heartbeat(60)
before = len(calls)
time.sleep(3.5)
after = len(calls)
check("kept running after an exception", after - before >= 2, True)
behaviour["mode"] = "ok"

print("\n7. CAN BE TURNED OFF WITHOUT A DEPLOY")
os.environ["AUTOWATCH_ENABLED"] = "false"
check("disabled by env", autowatch.enabled(), False)
autowatch._started = False
check("start refuses when disabled", autowatch.start(app, fake_pass), False)

print("\n" + ("ALL PASSED" if not FAIL else f"FAILURES: {FAIL}"))
sys.exit(1 if FAIL else 0)
