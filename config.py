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
#        https://<subdomain>.perfectmind.com/<org_path>/BookMe4BookingPages/Classes
#          ?calendarId=<CALENDAR_ID>&widgetId=<WIDGET_ID>&embed=False
#      Copy base_url, calendar_id and widget_id from that URL. org_path is
#      whatever sits between the domain and "BookMe4..." — different cities
#      use different values here (Coquitlam: "23902/Clients", Port Moody:
#      just "Contacts") — copy it exactly as it appears, including any slash.
#
# "timezone" is optional per source (IANA name, e.g. "America/Vancouver") and
# defaults to America/Vancouver if omitted — it's used to compute "today" for
# the schedule's date range in the venue's own local time, not the scraping
# server's. Only add it explicitly for a source outside that timezone.

SOURCES = [
    {
        "source_name": "City of Coquitlam",
        "base_url": "https://cityofcoquitlam.perfectmind.com",
        "org_path": "23902/Clients",
        "widget_id": "15f6af07-39c5-473e-b053-96653f77a406",
        "calendar_id": "b7685f76-3d81-4fac-b270-60659b414ff6",
        "calendar_label": "Skating",
        "activity_type": "Skating",
    },
    {
        "source_name": "City of Coquitlam",
        "base_url": "https://cityofcoquitlam.perfectmind.com",
        "org_path": "23902/Clients",
        "widget_id": "15f6af07-39c5-473e-b053-96653f77a406",
        "calendar_id": "4f07c977-74de-46ab-9d0a-2397f83f254f",
        "calendar_label": "Skating (pre-registration recommended)",
        "activity_type": "Skating",
    },
    {
        "source_name": "City of Coquitlam",
        "base_url": "https://cityofcoquitlam.perfectmind.com",
        "org_path": "23902/Clients",
        "widget_id": "15f6af07-39c5-473e-b053-96653f77a406",
        "calendar_id": "a6e0b3e0-c226-4aa3-82e0-68d61538d5fd",
        "calendar_label": "Swimming (pre-registration recommended)",
        "activity_type": "Swimming",
    },
    {
        "source_name": "City of Port Moody",
        "base_url": "https://cityofportmoody.perfectmind.com",
        "org_path": "Contacts",
        "widget_id": "15f6af07-39c5-473e-b053-96653f77a406",
        "calendar_id": "23606733-2ecf-4fb0-8fbf-d80a45d29c6d",
        "calendar_label": "Public Swim - Rocky Point",
        "activity_type": "Swimming",
    },
    {
        "source_name": "City of Port Moody",
        "base_url": "https://cityofportmoody.perfectmind.com",
        "org_path": "Contacts",
        "widget_id": "15f6af07-39c5-473e-b053-96653f77a406",
        "calendar_id": "97cc9ef0-3e47-46a7-ba0f-bc6015233c7c",
        "calendar_label": "Public Swim - Westhill Pool",
        "activity_type": "Swimming",
    },
    {
        "source_name": "City of Port Moody",
        "base_url": "https://cityofportmoody.perfectmind.com",
        "org_path": "Contacts",
        "widget_id": "15f6af07-39c5-473e-b053-96653f77a406",
        "calendar_id": "da287199-756a-422e-8fbc-b2e5063b77f8",
        "calendar_label": "Drop-in Ice Sports",
        "activity_type": "Skating",
    },
    # Court and gym sports (badminton, basketball, soccer, volleyball,
    # pickleball). These calendars are mixed — the same "Adult" calendar also
    # carries chess and movie matinees — so "activity_type" here is only the
    # fallback; scraper.classify_activity names the specific sport from the
    # event title.
    {
        "source_name": "City of Port Moody",
        "base_url": "https://cityofportmoody.perfectmind.com",
        "org_path": "Contacts",
        "widget_id": "15f6af07-39c5-473e-b053-96653f77a406",
        "calendar_id": "f0d6be4f-5434-4db5-961a-7f864c4b3265",
        "calendar_label": "Drop-in Adult & Senior Sports",
        "activity_type": "Sports",
    },
    {
        "source_name": "City of Port Moody",
        "base_url": "https://cityofportmoody.perfectmind.com",
        "org_path": "Contacts",
        "widget_id": "15f6af07-39c5-473e-b053-96653f77a406",
        "calendar_id": "008df9ef-8184-4ccb-8bd8-81bd52129eff",
        "calendar_label": "Drop-in Children & Family",
        "activity_type": "All Ages",
    },
    {
        "source_name": "City of Coquitlam",
        "base_url": "https://cityofcoquitlam.perfectmind.com",
        "org_path": "23902/Clients",
        "widget_id": "15f6af07-39c5-473e-b053-96653f77a406",
        "calendar_id": "e827dd8f-aa12-4dcd-9cdb-5cf4fcf24c30",
        "calendar_label": "Adult drop-in (pre-registration recommended)",
        "activity_type": "Adult",
    },
    {
        "source_name": "City of Coquitlam",
        "base_url": "https://cityofcoquitlam.perfectmind.com",
        "org_path": "23902/Clients",
        "widget_id": "15f6af07-39c5-473e-b053-96653f77a406",
        "calendar_id": "755afede-4c5a-49f0-ba97-7daedfb1aa4b",
        "calendar_label": "All ages drop-in (pre-registration recommended)",
        "activity_type": "All Ages",
    },
    {
        "source_name": "City of Coquitlam",
        "base_url": "https://cityofcoquitlam.perfectmind.com",
        "org_path": "23902/Clients",
        "widget_id": "15f6af07-39c5-473e-b053-96653f77a406",
        "calendar_id": "318d5236-c907-4009-8e63-9221625dd015",
        "calendar_label": "Youth drop-in (pre-registration recommended)",
        "activity_type": "Youth",
    },
    {
        "source_name": "City of Coquitlam",
        "base_url": "https://cityofcoquitlam.perfectmind.com",
        "org_path": "23902/Clients",
        "widget_id": "15f6af07-39c5-473e-b053-96653f77a406",
        "calendar_id": "592e7282-1885-4092-9cd3-4f787d4b4b5f",
        "calendar_label": "Court reservations",
        "activity_type": "Court Booking",
    },
]

# How many days ahead to pull the schedule for.
SCHEDULE_WINDOW_DAYS = 14

# How long fetched results are cached in memory before re-scraping (seconds).
CACHE_TTL_SECONDS = 15 * 60
