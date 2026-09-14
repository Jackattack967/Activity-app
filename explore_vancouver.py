"""TEMPORARY. Probe Vancouver's ActiveNet search for a drop-in axis.

Vancouver publishes no activity "types" and sends no category, and nothing
on a row marks a drop-in: allow_drop_in_reg is False on genuine drop-ins in
every city checked. This tries the remaining server-side knobs directly
rather than guessing at them, and prints enough real names to judge by eye.

Delete once Vancouver's config is settled.
"""

from __future__ import annotations

import datetime as dt
import json

import scraper_activenet as an

ORG = {
    "source_name": "City of Vancouver",
    "base_url": "https://anc.ca.apm.activecommunities.com",
    "org_path": "vancouver",
    "center_id": "39",  # Hillcrest Community Centre
    "location": "Hillcrest Community Centre",
    "calendar_label": "probe",
    "activity_type": "Other",
}

session = an._build_session()
an._warm_up(session, ORG)

today = dt.date.today()
end = today + dt.timedelta(days=14)


def post(body: dict, page: int = 1) -> dict:
    resp = session.post(
        f"{ORG['base_url']}/{ORG['org_path']}/rest/activities/list?locale=en-US",
        headers={
            "Content-Type": "application/json;charset=UTF-8",
            "page_info": json.dumps(
                {"order_by": "", "page_number": page, "total_records_per_page": 20}
            ),
        },
        data=json.dumps(body),
        timeout=25,
    )
    resp.raise_for_status()
    return resp.json()


def describe(label: str, pattern: dict) -> None:
    body = {"activity_search_pattern": pattern, "activity_transfer_pattern": {}}
    try:
        data = post(body)
    except Exception as exc:  # noqa: BLE001
        print(f"\n--- {label}: FAILED {exc}")
        return
    info = (data.get("headers") or {}).get("page_info") or {}
    items = (data.get("body") or {}).get("activity_items") or []
    print(f"\n--- {label}: {info.get('total_records', '?')} records")
    for raw in items[:8]:
        print(
            f"      {(raw.get('name') or '')[:52]:<52} "
            f"{raw.get('date_range_start')}..{raw.get('date_range_end') or ''} "
            f"{(raw.get('days_of_week') or '')[:10]}"
        )


print("=" * 72)
print("1. WHAT THE FILTERS ENDPOINT SAYS FROM A WARMED SERVER SESSION")
print("=" * 72)
resp = session.get(
    f"{ORG['base_url']}/{ORG['org_path']}/rest/activities/filters?locale=en-US",
    timeout=25,
)
filters = (resp.json().get("body") or {})
for key in ("types", "othercategories", "seasons", "sites", "departments", "terms"):
    print(f"  {key:<18} {json.dumps(filters.get(key))[:300]}")

print()
print("=" * 72)
print("2. DOES activity_select_param CHANGE WHAT COMES BACK?")
print("=" * 72)
base = {
    "date_after": today.isoformat(),
    "date_before": end.isoformat(),
    "activity_category_ids": [],
    "center_ids": [ORG["center_id"]],
}
for param in (0, 1, 2, 3):
    describe(f"activity_select_param={param}", {**base, "activity_select_param": param})

print()
print("=" * 72)
print("3. DOES A TYPE FILTER WORK EVEN THOUGH NONE ARE ADVERTISED?")
print("=" * 72)
for type_id in ("1", "6"):
    describe(
        f"activity_type_ids=[{type_id}]",
        {**base, "activity_select_param": 2, "activity_type_ids": [type_id]},
    )

print()
print("=" * 72)
print("4. WHAT HILLCREST ACTUALLY PUBLISHES (60 names, to judge by eye)")
print("=" * 72)
seen = []
for page in range(1, 6):
    data = post(
        {
            "activity_search_pattern": {
                **base,
                "activity_select_param": 2,
                "activity_category_ids": ["23", "24", "27", "28"],
            },
            "activity_transfer_pattern": {},
        },
        page=page,
    )
    items = (data.get("body") or {}).get("activity_items") or []
    if not items:
        break
    for raw in items:
        seen.append(
            f"  {(raw.get('name') or '')[:50]:<50} "
            f"{raw.get('date_range_start')}..{raw.get('date_range_end') or ''} "
            f"{(raw.get('days_of_week') or '')[:10]:<10} "
            f"{raw.get('time_range')}"
        )
for line in seen[:60]:
    print(line)
