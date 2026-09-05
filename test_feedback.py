"""Exercise the feedback endpoint's guards.

Run with:  .venv\\Scripts\\python.exe test_feedback.py
Exits non-zero if anything fails.

Nothing here sends an email: the delivery function is swapped for one that
records what it was asked to send. That matters more than usual, because the
real one would put a message in a real inbox from a real address.

app.py cannot be imported — it reads .env, connects to the production
database and starts the watch thread — so the rate limiter is loaded out of
it by name instead. The same reason the other test files build their own
Flask app rather than reusing the real one.
"""
import ast
import datetime as dt
import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

FAIL = []


def check(label, got, want):
    ok = got == want
    print(f"  {'PASS' if ok else 'FAIL'}  {label}: got {got!r}, want {want!r}")
    if not ok:
        FAIL.append(label)


def load_from_app(*names):
    """Pull named top-level definitions out of app.py without executing it."""
    source = open(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.py"),
        encoding="utf-8",
    ).read()
    tree = ast.parse(source)
    wanted = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names:
            # Strip decorators — @app.route needs the app object we are avoiding.
            node.decorator_list = []
            wanted.append(node)
        elif isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id in names for t in node.targets
        ):
            wanted.append(node)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id in names:
            wanted.append(node)
    module = types.ModuleType("app_shim")
    module.__dict__.update(dt=dt, threading=__import__("threading"))
    exec(compile(ast.Module(wanted, []), "<app_shim>", "exec"), module.__dict__)
    return module


shim = load_from_app(
    "_FEEDBACK_WINDOW",
    "_FEEDBACK_MAX_PER_SENDER",
    "_FEEDBACK_MAX_TOTAL",
    "_feedback_lock",
    "_feedback_log",
    "_feedback_allowed",
)

print("\n1. RATE LIMIT: ONE SENDER CANNOT FLOOD THE INBOX")
shim._feedback_log.clear()
allowed = [shim._feedback_allowed("1.2.3.4") for _ in range(6)]
check("first three accepted", allowed[:3], [True, True, True])
check("the rest refused", allowed[3:], [False, False, False])

print("\n2. ONE SENDER'S LIMIT DOESN'T BLOCK EVERYONE ELSE")
check("a different sender still gets through", shim._feedback_allowed("5.6.7.8"), True)

print("\n3. RATE LIMIT: A GLOBAL CAP PROTECTS THE EMAIL QUOTA")
# Alert emails and feedback share one provider allowance, so a flood of
# feedback must not be able to silence the spot-open alerts.
shim._feedback_log.clear()
accepted = sum(1 for i in range(200) if shim._feedback_allowed(f"10.0.0.{i % 256}"))
check("total accepted is capped", accepted, shim._FEEDBACK_MAX_TOTAL)

print("\n4. THE WINDOW EXPIRES, SO THE LIMIT ISN'T PERMANENT")
shim._feedback_log.clear()
for _ in range(shim._FEEDBACK_MAX_PER_SENDER):
    shim._feedback_allowed("9.9.9.9")
check("blocked while the window is open", shim._feedback_allowed("9.9.9.9"), False)
# Rewind the recorded times past the window rather than sleeping an hour.
old = dt.datetime.utcnow() - shim._FEEDBACK_WINDOW - dt.timedelta(minutes=1)
shim._feedback_log[:] = [(old, who) for _, who in shim._feedback_log]
check("allowed again once they age out", shim._feedback_allowed("9.9.9.9"), True)

print("\n5. THE EMAIL ITSELF")
os.environ["FEEDBACK_EMAIL"] = "owner@example.invalid"
import watcher

sent = []
watcher._deliver_email = lambda to, subject, body, headers=None: (
    sent.append({"to": to, "subject": subject, "body": body, "headers": headers}) or True
)

check("reports success", watcher.send_feedback("The map is blank", "Problem"), True)
check("addressed to the operator", sent[-1]["to"], "owner@example.invalid")
check("subject is labelled", sent[-1]["subject"], "[Feedback] Problem")
check("message is in the body", "The map is blank" in sent[-1]["body"], True)
check("no Reply-To when none given", sent[-1]["headers"], None)

watcher.send_feedback("Add squash", "Idea", "someone@example.invalid")
check("Reply-To set when given", sent[-1]["headers"], {"Reply-To": "someone@example.invalid"})

print("\n6. A STRANGER'S TEXT CANNOT WRITE THE EMAIL'S HTML")
# This is the one that matters. The body is HTML sent from this app's own
# address, so unescaped input would be a phishing kit rather than a bug.
watcher.send_feedback(
    '<a href="http://evil.invalid">Reset your password</a><script>x</script>',
    "Problem",
    '"><b>spoof</b>@example.invalid',
)
body = sent[-1]["body"]
check("no live anchor tag", "<a href=" in body, False)
check("no script tag", "<script>" in body, False)
check("escaped instead", "&lt;a href=" in body, True)
check("the text is still readable", "Reset your password" in body, True)
check("the reply address is escaped too", "<b>spoof</b>" in body, False)

print("\n7. NO DESTINATION MEANS NO SILENT SUCCESS")
os.environ.pop("FEEDBACK_EMAIL", None)
had_contact = os.environ.pop("CONTACT_EMAIL", None)
check("refuses rather than pretending", watcher.send_feedback("hello", "Idea"), False)
if had_contact is not None:
    os.environ["CONTACT_EMAIL"] = had_contact

print("\n" + ("ALL PASSED" if not FAIL else f"FAILURES: {FAIL}"))
sys.exit(1 if FAIL else 0)
