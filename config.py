# Municipal recreation portals to scrape.
#
# Each entry describes one PerfectMind "drop-in" calendar. A city's PerfectMind
# widget can expose several calendars (e.g. skating vs. swimming, or
# "no registration required" vs. "pre-registration recommended"); add one
# entry per calendar you want pulled into the dashboard.
#
# To find these values for a new city/calendar:
#   1. Open the city's PerfectMind widget URL in a browser.
#   2. Click through to the drop-in category you want (e.g. "Skating").
#   3. The resulting URL looks like:
#        https://<subdomain>.perfectmind.com/<org_id>/Clients/BookMe4BookingPages/Classes
#          ?calendarId=<CALENDAR_ID>&widgetId=<WIDGET_ID>&embed=False
#      Copy base_url, org_id, calendar_id and widget_id from that URL.
#
# "timezone" is optional per source (IANA name, e.g. "America/Vancouver") and
# defaults to America/Vancouver if omitted — it's used to compute "today" for
# the schedule's date range in the venue's own local time, not the scraping
# server's. Only add it explicitly for a source outside that timezone.

SOURCES = [
    {
        "source_name": "City of Coquitlam",
        "base_url": "https://cityofcoquitlam.perfectmind.com",
        "org_id": "23902",
        "widget_id": "15f6af07-39c5-473e-b053-96653f77a406",
        "calendar_id": "b7685f76-3d81-4fac-b270-60659b414ff6",
        "calendar_label": "Skating",
        "activity_type": "Skating",
    },
    {
        "source_name": "City of Coquitlam",
        "base_url": "https://cityofcoquitlam.perfectmind.com",
        "org_id": "23902",
        "widget_id": "15f6af07-39c5-473e-b053-96653f77a406",
        "calendar_id": "4f07c977-74de-46ab-9d0a-2397f83f254f",
        "calendar_label": "Skating (pre-registration recommended)",
        "activity_type": "Skating",
    },
    {
        "source_name": "City of Coquitlam",
        "base_url": "https://cityofcoquitlam.perfectmind.com",
        "org_id": "23902",
        "widget_id": "15f6af07-39c5-473e-b053-96653f77a406",
        "calendar_id": "a6e0b3e0-c226-4aa3-82e0-68d61538d5fd",
        "calendar_label": "Swimming (pre-registration recommended)",
        "activity_type": "Swimming",
    },
]

# How many days ahead to pull the schedule for.
SCHEDULE_WINDOW_DAYS = 14

# How long fetched results are cached in memory before re-scraping (seconds).
CACHE_TTL_SECONDS = 15 * 60
