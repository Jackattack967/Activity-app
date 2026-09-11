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
import re
import sys

import config
import scraper

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
    courses = sorted({n for n in names if COURSE_HINTS.search(n)})
    if courses:
        print(
            f"\n{len(courses)} distinct name(s) look like registered courses "
            "rather than\ndrop-ins. If this list is long, the source's filter "
            "is too wide:"
        )
        for name in courses[: args.sample]:
            print(f"  ? {name}")
        if len(courses) > args.sample:
            print(f"  ... and {len(courses) - args.sample} more")

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

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
