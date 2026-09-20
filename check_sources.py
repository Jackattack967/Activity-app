"""Fetch every configured source and report what each one actually returned.

Adding a city is config, and config can be wrong in a way nothing notices: a
source whose ids are subtly off doesn't raise, it just returns nothing, and
"this building published no drop-ins today" looks exactly the same. The
dashboard can't tell those apart either — it shows a quieter city.

So this asks the portals directly and prints the answer per source, plus a
sample of what came back, which is what says whether a filter is pulling in
things it shouldn't (registered courses in a drop-in app, most of all).

    python check_sources.py                  # every source
    python check_sources.py vancouver        # sources whose city matches
    python check_sources.py --sample 30 west # more example rows

It reads live portals, so it takes a minute and needs a network connection.
Nothing is written and no account is involved.
"""

from __future__ import annotations

import argparse
import collections
import html
import json
import re
import sys

import config
import scraper
from scraper_activenet import CATEGORY_ACTIVITY_TYPES as CATEGORY_MAP

# A registered course says so in its own name. This is a hint for a human
# reading the output, not a filter — nothing here changes what the app
# fetches, and a term landing in the wrong column is a prompt to look, not
# a bug.
COURSE_HINTS = re.compile(
    r"\b(lesson|lessons|level \d|preschool|camp|certificat|instructor|"
    r"leadership|course|clinic|academy|training|club|birthday)\b",
    re.I,
)
DROPIN_HINTS = re.compile(
    r"\b(drop.?in|public|leisure|open|everyone welcome|casual|stick|shinny)\b",
    re.I,
)


def probe_raw(sources: list[dict], per_org: int = 3, pages: int = 2) -> None:
    """Print the raw fields an ActiveNet portal actually sends.

    The normalized Event deliberately doesn't carry the portal's own
    category, so when a city arrives mostly typed "Other" there is nothing
    in the report above that says which category names to map. This asks
    the portal directly, for a sample of buildings per city.

    It also counts how many rows are single-day against multi-week, which
    is the question behind "is this a drop-in or a ten-week course" for a
    portal that publishes no drop-in flag of its own.
    """
    import datetime as dt
    import scraper_activenet as an

    by_org: dict[tuple[str, str], list[dict]] = {}
    for source in sources:
        if source.get("platform") != "activenet":
            continue
        by_org.setdefault((source["source_name"], source["org_path"]), []).append(source)

    for (city, org_path), org_sources in by_org.items():
        print(f"\n{'=' * 70}\n{city}  (raw sample from {org_path})\n{'=' * 70}")
        categories: collections.Counter = collections.Counter()
        spans: collections.Counter = collections.Counter()
        examples: list[str] = []
        sample_row: dict | None = None

        session = an._build_session()
        try:
            an._warm_up(session, org_sources[0])
        except Exception as exc:  # noqa: BLE001 - a probe, not the app
            print(f"  could not reach the portal: {exc}")
            continue

        today = dt.date.today()
        window_end = today + dt.timedelta(days=config.SCHEDULE_WINDOW_DAYS)
        for source in org_sources[:per_org]:
            for page in range(1, pages + 1):
                try:
                    data = an._search_page(session, source, today, window_end, page)
                except Exception as exc:  # noqa: BLE001
                    print(f"  {source['location']} page {page}: {exc}")
                    break
                items = (data.get("body") or {}).get("activity_items") or []
                if not items:
                    break
                for raw in items:
                    if sample_row is None:
                        sample_row = raw
                    category = (raw.get("category") or "").strip()
                    categories[category] += 1

                    start = (raw.get("date_range_start") or "").strip()
                    end = (raw.get("date_range_end") or "").strip()
                    if not end or end == start:
                        spans["one day"] += 1
                    else:
                        try:
                            days = (
                                dt.date.fromisoformat(end) - dt.date.fromisoformat(start)
                            ).days
                        except ValueError:
                            spans["unparseable"] += 1
                            continue
                        spans["2-13 days" if days < 14 else "14+ days"] += 1

                    if len(examples) < 12:
                        examples.append(
                            f"    {(raw.get('name') or '')[:44]:<44} | "
                            f"{category[:26]:<26} | {start}..{end or start} | "
                            f"{(raw.get('days_of_week') or '')[:12]}"
                        )

        print("\n  Categories the portal sent, and whether we map them:")
        for category, count in categories.most_common():
            mapped = CATEGORY_MAP.get(html.unescape(category))
            flag = f"-> {mapped}" if mapped else "-> UNMAPPED, becomes 'Other'"
            print(f"  {count:>6}  {category or '(none)'!s:<34} {flag}")

        print("\n  How long each activity runs (a drop-in is usually one day):")
        for span, count in spans.most_common():
            print(f"  {count:>6}  {span}")

        print("\n  Example rows (name | category | dates | weekdays):")
        for line in examples:
            print(line)

        # The fields above are the ones this app already reads. When a
        # portal sends no category at all — as Vancouver and West Vancouver
        # do — the useful question becomes what it sends *instead*, and the
        # only honest way to answer that is to look at a whole row.
        if sample_row is not None:
            print("\n  Every field on one row:")
            for key in sorted(sample_row):
                value = sample_row[key]
                if isinstance(value, (dict, list)):
                    value = json.dumps(value)[:160]
                text = str(value).replace("\n", " ")[:160]
                print(f"    {key:<32} {text}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "match",
        nargs="?",
        default="",
        help="only sources whose city or venue contains this text",
    )
    parser.add_argument(
        "--sample", type=int, default=15, help="example event names to print"
    )
    parser.add_argument(
        "--days", type=int, default=config.SCHEDULE_WINDOW_DAYS, help="days ahead"
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="also show the portal's own category names and date ranges",
    )
    args = parser.parse_args()

    needle = args.match.casefold()
    sources = [
        s
        for s in config.SOURCES
        if needle in s["source_name"].casefold()
        or needle in s.get("location", "").casefold()
        or needle in s["calendar_label"].casefold()
    ]
    if not sources:
        print(f"No source matches {args.match!r}.")
        return 1

    print(f"Fetching {len(sources)} source(s) over {args.days} days...\n")
    events, errors = scraper.fetch_all_events(sources, args.days)

    # Per source, so a single mis-configured building is visible rather than
    # averaged away by its neighbours.
    counts: dict[tuple[str, str], int] = collections.Counter()
    for event in events:
        counts[(event.source_name, event.calendar_label)] += 1

    empty = []
    print(f"{'sessions':>9}  source")
    print(f"{'-' * 9}  {'-' * 60}")
    for source in sources:
        key = (source["source_name"], source["calendar_label"])
        count = counts.get(key, 0)
        if not count:
            empty.append(key)
        print(f"{count:>9}  {key[0]} / {key[1]}")

    print(f"\n{len(events)} sessions in total, from {len(sources) - len(empty)} "
          f"of {len(sources)} sources.")

    if errors:
        print(f"\n{len(errors)} source(s) failed outright:")
        for error in errors:
            print(f"  ! {error}")

    if empty:
        print(f"\n{len(empty)} source(s) returned nothing. That is normal for a "
              "seasonal\nvenue (an outdoor pool in winter) and a red flag for "
              "anything else:")
        for name, label in empty[: args.sample]:
            print(f"  · {name} / {label}")
        if len(empty) > args.sample:
            print(f"  ... and {len(empty) - args.sample} more")

    # Venues learned by scraping can't be checked the way configured ones
    # are: a PerfectMind source never names its building, so a venue that
    # is missing from FACILITY_COORDS — or spelled a hair differently from
    # the key there — costs a map pin and says nothing about it. This is
    # the only place that difference becomes visible.
    venues = {e.location for e in events if e.location}
    unmapped = sorted(venues - set(config.FACILITY_COORDS))
    if unmapped:
        print(
            f"\n{len(unmapped)} of {len(venues)} venue(s) have no map pin. Either the"
            "\nvenue is new, or its name here differs from the key in"
            "\nFACILITY_COORDS — which looks identical on the map, and isn't:"
        )
        for venue in unmapped:
            declared = " (declared in VENUES_AWAITING_COORDS)" * (
                venue in config.VENUES_AWAITING_COORDS
            )
            print(f"  · {venue}{declared}")

    by_type = collections.Counter(e.activity_type for e in events)
    if by_type:
        print("\nActivity types:")
        for activity_type, count in by_type.most_common():
            print(f"{count:>9}  {activity_type}")
        if by_type.get("Other"):
            print(
                "\n  'Other' means a category no scraper_activenet."
                "CATEGORY_ACTIVITY_TYPES\n  entry names, and no sport in the "
                "title either. A large count here is\n  a mapping to add, not "
                "a scrape that failed."
            )

    names = [e.event_name for e in events]
    # Grouped by city, because "the filter is too wide" is a statement about
    # one city's config, and a single merged list can't say whose.
    courses_by_city: dict[str, set[str]] = collections.defaultdict(set)
    total_by_city: dict[str, set[str]] = collections.defaultdict(set)
    for event in events:
        total_by_city[event.source_name].add(event.event_name)
        if COURSE_HINTS.search(event.event_name):
            courses_by_city[event.source_name].add(event.event_name)

    if courses_by_city:
        print(
            "\nNames that look like registered courses rather than drop-ins.\n"
            "A high share for a city means that city's filter is too wide:"
        )
        for city in sorted(total_by_city, key=lambda c: -len(courses_by_city[c])):
            course_count = len(courses_by_city[city])
            share = course_count / max(len(total_by_city[city]), 1)
            print(
                f"  {course_count:>5} of {len(total_by_city[city]):>5} distinct "
                f"names ({share:>4.0%})  {city}"
            )
        worst = max(courses_by_city, key=lambda c: len(courses_by_city[c]))
        print(f"\n  Examples from {worst}:")
        for name in sorted(courses_by_city[worst])[: args.sample]:
            print(f"  ? {name}")

    unsure = sorted(
        {n for n in names if not COURSE_HINTS.search(n) and not DROPIN_HINTS.search(n)}
    )
    distinct = sorted(set(names))
    print(
        f"\nA sample of what came back "
        f"({min(args.sample, len(distinct))} of {len(distinct)} distinct names):"
    )
    for name in distinct[: args.sample]:
        print(f"  · {name}")
    if unsure:
        print(
            f"\n({len(unsure)} name(s) read as neither obviously drop-in nor "
            "obviously a\ncourse — those are the ones worth eyeballing.)"
        )

    if args.raw:
        probe_raw(sources)

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
