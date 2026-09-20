"""TEMPORARY. Last automatic attempt to find Port Moody's swim schedule.

Previous attempt got two things wrong. It called every candidate widget a
hit because it only looked for one refusal string, when an unknown widget
returns a *different* error page (15,074 bytes) from a forbidden calendar
(15,116) — both errors, neither a calendar. And it guessed five URLs on
portmoody.ca, all of which 404.

So: judge a page by what a working one looks like (~31,800 bytes, a token,
no "Error Page"), and find the city's real recreation pages by crawling
from its home page rather than guessing.

Delete once this is settled, either way.
"""

from __future__ import annotations

import re
from urllib.parse import urljoin

import config
import scraper_perfectmind as pm

session = pm._build_session()
HEADERS = {"User-Agent": pm.USER_AGENT}
ROCKY = next(
    s for s in config.SOURCES if s.get("calendar_label") == "Public Swim - Rocky Point"
)
WORKING = next(
    s for s in config.SOURCES if s.get("calendar_label") == "Drop-in Ice Sports"
)


def looks_like_a_calendar(text: str) -> bool:
    """What a page that actually renders a calendar looks like."""
    return (
        len(text) > 20000
        and bool(pm.TOKEN_TAG_RE.search(text))
        and "Error Page" not in text
    )


print("=== 0. CALIBRATION: a known-good page and a known-bad one")
for label, source in (("working (Ice Sports)", WORKING), ("broken (Rocky Point)", ROCKY)):
    resp = session.get(
        f"{source['base_url']}/{source['org_path']}/BookMe4BookingPages/Classes"
        f"?calendarId={source['calendar_id']}&widgetId={source['widget_id']}&embed=False",
        headers=HEADERS,
        timeout=20,
    )
    print(
        f"    {label:<22} {len(resp.text):>6} bytes  "
        f"calendar={looks_like_a_calendar(resp.text)}"
    )

print("\n=== 1. PORT MOODY'S REAL PAGES, CRAWLED FROM THE HOME PAGE")
home = "https://www.portmoody.ca/"
try:
    page = session.get(home, headers=HEADERS, timeout=25)
    print(f"    home page HTTP {page.status_code}, {len(page.text)} bytes")
except Exception as exc:  # noqa: BLE001
    print(f"    home page failed: {type(exc).__name__}: {exc}")
    raise SystemExit

links = {
    urljoin(home, href)
    for href in re.findall(r'href="([^"]+)"', page.text)
    if not href.startswith(("mailto:", "tel:", "#"))
}
interesting = sorted(
    l
    for l in links
    if l.startswith("https://www.portmoody.ca")
    and re.search(r"recreat|swim|schedule|pool|drop|arena|activit", l, re.I)
)
print(f"    {len(links)} links on the home page, {len(interesting)} recreation-ish:")
for link in interesting[:20]:
    print(f"      {link}")

print("\n=== 2. PERFECTMIND LINKS ON THOSE PAGES")
found = {}
for link in interesting[:12]:
    try:
        sub = session.get(link, headers=HEADERS, timeout=20)
    except Exception as exc:  # noqa: BLE001
        print(f"    {link} -> {type(exc).__name__}")
        continue
    hits = set(re.findall(r"https?://[^\"'\s<>]*perfectmind[^\"'\s<>]*", sub.text))
    if hits:
        print(f"    {link} -> {len(hits)} link(s)")
    for hit in hits:
        found.setdefault(hit.replace("&amp;", "&"), link)

if not found:
    print("    none found on any crawled page")
for link in sorted(found):
    cal = re.search(r"calendarId=([0-9a-f-]{36})", link)
    wid = re.search(r"widgetId=([0-9a-f-]{36})", link)
    print(f"\n    {link[:150]}")
    if cal:
        print(f"        calendarId {cal.group(1)}")
    if wid:
        print(f"        widgetId   {wid.group(1)}")
    if cal and wid:
        try:
            probe = session.get(
                f"{ROCKY['base_url']}/{ROCKY['org_path']}/BookMe4BookingPages/Classes"
                f"?calendarId={cal.group(1)}&widgetId={wid.group(1)}&embed=False",
                headers=HEADERS,
                timeout=20,
            )
            print(
                f"        renders a calendar: {looks_like_a_calendar(probe.text)} "
                f"({len(probe.text)} bytes)"
            )
        except Exception as exc:  # noqa: BLE001
            print(f"        probe failed: {type(exc).__name__}")
