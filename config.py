# Municipal recreation portals to scrape.
#
# Cities do not all run the same booking software, so each entry names the
# "platform" it is on and scraper.py hands it to the matching module. Two
# are supported:
#
#   "perfectmind" — Coquitlam, Port Moody, New Westminster. Keys: base_url,
#       org_path, widget_id, calendar_id. One entry per calendar.
#   "activenet"   — Port Coquitlam. Keys: base_url, org_path, center_id,
#       category_ids, location. One entry per *building*, because ActiveNet
#       searches are filtered by building rather than by calendar. See
#       scraper_activenet.py for why the building name is configured here.
#
# A source with no "platform" is treated as PerfectMind, which is what every
# source was before the second platform existed.
#
# --- Finding the values for a new PerfectMind city/calendar ---
#
# A city's PerfectMind widget can expose several calendars (e.g. skating vs.
# swimming, or "no registration required" vs. "pre-registration
# recommended"); add one entry per calendar you want pulled in.
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
# --- Finding the values for a new ActiveNet city ---
#
#   1. Open the city's registration portal; it redirects to
#        https://anc.ca.apm.activecommunities.com/<org_path>/home
#   2. GET /<org_path>/rest/activities/filters?locale=en-US — public JSON
#      listing every "center" (building) and "category" with their ids.
#   3. Add one entry per building you care about, with the drop-in category
#      ids you want and the building's proper name as "location".
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
    # City of New Westminster. Same PerfectMind widget as the Tri-Cities
    # above, so it needed no new scraping code — only these four entries.
    {
        "source_name": "City of New Westminster",
        "base_url": "https://cityofnewwestminster.perfectmind.com",
        "org_path": "23693/Clients",
        "widget_id": "50a33660-b4f7-44d9-9256-e10effec8641",
        "calendar_id": "db250b43-ef6b-43c5-979e-3f3d1dab2d67",
        "calendar_label": "Drop-in Skating",
        "activity_type": "Skating",
    },
    {
        "source_name": "City of New Westminster",
        "base_url": "https://cityofnewwestminster.perfectmind.com",
        "org_path": "23693/Clients",
        "widget_id": "50a33660-b4f7-44d9-9256-e10effec8641",
        "calendar_id": "f744a9cd-27f0-4c58-be71-af01b805395d",
        "calendar_label": "Drop-in Swimming",
        "activity_type": "Swimming",
    },
    {
        "source_name": "City of New Westminster",
        "base_url": "https://cityofnewwestminster.perfectmind.com",
        "org_path": "23693/Clients",
        "widget_id": "50a33660-b4f7-44d9-9256-e10effec8641",
        "calendar_id": "3a348c3b-a440-4c39-accc-bd13228f6f5b",
        "calendar_label": "Drop-in Fitness",
        "activity_type": "Fitness",
    },
    {
        "source_name": "City of New Westminster",
        "base_url": "https://cityofnewwestminster.perfectmind.com",
        "org_path": "23693/Clients",
        "widget_id": "50a33660-b4f7-44d9-9256-e10effec8641",
        "calendar_id": "3987edf1-0b8a-4aef-b3a2-8de368def17d",
        "calendar_label": "Drop-in Gymnastics",
        "activity_type": "All Ages",
    },
    # City of Port Coquitlam, on ActiveNet rather than PerfectMind. One
    # entry per building, each pulling every drop-in category the portal
    # publishes; scraper_activenet.CATEGORY_ACTIVITY_TYPES turns those
    # categories into the same activity types the other cities use.
    *(
        {
            "source_name": "City of Port Coquitlam",
            "platform": "activenet",
            "base_url": "https://anc.ca.apm.activecommunities.com",
            "org_path": "cityofportcoquitlam",
            "center_id": center_id,
            "location": location,
            "center_aliases": aliases,
            # Aquatics, Skating, Fitness, Youth, Sport, Seniors, Children.
            "category_ids": ["48", "49", "50", "51", "52", "53", "57"],
            "calendar_label": f"Drop-in — {location}",
            # Only reached if the portal invents a category we don't map.
            "activity_type": "Other",
        }
        for center_id, location, aliases in (
            ("55", "Port Coquitlam Community Centre", ("Port Coquitlam Cmty Centre",)),
            ("23", "Hyde Creek Recreation Centre", ("Hyde Creek Rec Centre",)),
            ("36", "Outlet", ()),
        )
    ),
]

# How many days ahead to pull the schedule for.
SCHEDULE_WINDOW_DAYS = 14

# How long fetched results are cached in memory before re-scraping (seconds).
CACHE_TTL_SECONDS = 15 * 60

# Where each venue physically is, for the map view.
#
# Keyed on an event's `location`, not its `facility`. `facility` is the room
# inside the building ("Pinetree Gymnasium 1", "Pinetree Room 5/6" — nine of
# them at Pinetree alone); `location` is the building itself, which is what
# has an address and a place on a map. It is also what the app already treats
# as venue identity when matching favourites.
#
# Hardcoded on purpose. There are twelve of these and the list changes about
# never, so geocoding at runtime would mean a network call and an API
# dependency on every scrape to learn something that is already known.
# Coordinates came from OpenStreetMap/Nominatim, checked against the cities'
# own facility pages. Regenerate by hand if a venue is ever added.
#
# A location missing from here simply gets no marker — see _with_coords() in
# app.py. Nothing breaks; the venue just doesn't appear on the map.
FACILITY_COORDS = {
    # City of Coquitlam
    "Centennial Activity Centre": (49.252663, -122.847580),
    # OSM has no entry by name; this is 1655 Winslow Ave, in Blue Mountain Park.
    "Dogwood Pavilion": (49.254886, -122.848746),
    "Glen Pine Pavilion": (49.283203, -122.794938),
    "Maillardville Community Centre": (49.240876, -122.859060),
    "Mundy Park Pool": (49.257724, -122.833978),
    "Pinetree Community Centre": (49.289383, -122.791355),
    # Separate building from the Sport & Leisure Complex, ~150m down the street.
    "Poirier Forum": (49.254214, -122.847228),
    "Poirier Sport & Leisure Complex": (49.254579, -122.845262),
    # Runs inside Smiling Creek Elementary, 3456 Princeton Ave.
    "Smiling Creek Activity Centre": (49.297896, -122.750289),
    # On the west side of Summit Middle School, 1450 Parkway Blvd; this is the
    # school's own point, so the marker sits a little east of the entrance.
    "Summit Community Centre": (49.295495, -122.806609),
    # City of Port Moody
    "Port Moody Recreation Complex": (49.283211, -122.831651),
    "Rocky Point Pool": (49.279625, -122.849257),
    "Westhill Pool": (49.284250, -122.879587),
    # City of Port Coquitlam
    "Port Coquitlam Community Centre": (49.260084, -122.777032),
    # OSM has no building here; this is Laurier Ave at the rec centre's
    # block, so the marker is on the right street rather than the door.
    "Hyde Creek Recreation Centre": (49.274791, -122.763090),
    # The youth centre sits inside Leigh Square Community Arts Village.
    "Outlet": (49.261973, -122.780310),
    # City of New Westminster
    "Moody Park Arena": (49.215617, -122.926213),
    "təməsew̓txʷ Aquatic and Community Centre": (49.221138, -122.907594),
    "Queen's Park Sportsplex": (49.213589, -122.903744),
    "Queensborough Community Centre": (49.185876, -122.943506),
    # Street-level only; Century House is mid-block on Eighth Street.
    "Century House": (49.201950, -122.912396),
    # Outdoor pools, mapped to their park's centre rather than the pool
    # itself — OSM has the park but not the pool building.
    "Hume Park": (49.235173, -122.890505),
    "Moody Park": (49.213314, -122.929143),
}

# Which part of the region each city's venues belong to.
#
# This drives the "Area" filter and the map's colour coding, and it is what
# "where you live" selects. Keyed on source_name because every event carries
# one, so a venue that appears in a portal tomorrow lands in the right area
# with no extra work — unlike FACILITY_COORDS, which needs a new entry.
#
# An area may cover several cities (a future "North Shore" would hold both
# North Vancouvers), which is why cities is a tuple rather than a string.
# Order is the order the filter lists them in.
AREAS = (
    {"name": "Coquitlam", "cities": ("City of Coquitlam",)},
    {"name": "Port Coquitlam", "cities": ("City of Port Coquitlam",)},
    {"name": "Port Moody", "cities": ("City of Port Moody",)},
    {"name": "New Westminster", "cities": ("City of New Westminster",)},
)

# Built once at import: {source_name -> area name}, so annotating an event
# is a dict lookup rather than a scan over AREAS.
CITY_AREAS = {
    city: area["name"] for area in AREAS for city in area["cities"]
}
