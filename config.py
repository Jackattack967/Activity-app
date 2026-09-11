# Municipal recreation portals to scrape.
#
# Cities do not all run the same booking software, so each entry names the
# "platform" it is on and scraper.py hands it to the matching module. Two
# are supported:
#
#   "perfectmind" — Coquitlam, Port Moody, New Westminster. Keys: base_url,
#       org_path, widget_id, calendar_id. One entry per calendar.
#   "activenet"   — Port Coquitlam, Burnaby, West Vancouver. Keys: base_url,
#       org_path, center_id, location, and one or both of category_ids and
#       type_ids. One entry per *building*, because ActiveNet searches are
#       filtered by building rather than by calendar. See
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
#      listing every "center" (building), "category" and "type" with their
#      ids. Load the home page first: the endpoint answers blank for a
#      caller it has not seen before.
#   3. Add one entry per building you care about, with the building's proper
#      name as "location" and whichever of these narrows the search best:
#        category_ids — for portals whose categories are themselves drop-in
#          ("Drop-in - Aquatics"), as Port Coquitlam's are.
#        type_ids     — for portals that keep drop-ins on a separate axis
#          ("Daily Activities and Drop-Ins"), as West Vancouver does. This
#          is the better filter where it exists: it is the portal's own
#          answer to "what can I just turn up to", so registered courses
#          stay out without having to name every category by hand.
#      Either may be omitted; omitting both fetches everything the building
#      publishes, which is rarely what you want.
#
# docs/collecting-portal-ids.md walks through both platforms click by click.
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
    # City of Burnaby, also on ActiveNet. Only its two golf courses are
    # listed: golf is the one thing Burnaby publishes that no other city in
    # this app does, and its pools and rinks are a separate, much larger
    # addition that can be made in this file alone whenever it is wanted.
    #
    # These are lessons and clinics, not walk-on drop-ins. Booking an actual
    # round at either course happens on a tee sheet the city runs on other
    # software, which this app deliberately does not read — see README. What
    # is here is every golf program Burnaby takes registrations for, each
    # with its real remaining-spot count, which is what a watch needs to be
    # able to tell you that a place has opened up.
    *(
        {
            "source_name": "City of Burnaby",
            "platform": "activenet",
            "base_url": "https://anc.ca.apm.activecommunities.com",
            "org_path": "burnaby",
            "center_id": center_id,
            "location": location,
            # Every row at these two centres is already golf, so the category
            # is belt-and-braces rather than a real narrowing. It is named
            # anyway, so that if Burnaby ever books something else out of the
            # clubhouse it does not silently arrive labelled "Golf".
            "category_ids": ["55"],
            "calendar_label": f"Golf — {location}",
            "activity_type": "Golf",
        }
        for center_id, location in (
            ("126", "Burnaby Mountain Golf Course"),
            ("34", "Riverway Golf Course"),
        )
    ),
    # District of West Vancouver, on ActiveNet.
    #
    # Filtered by type rather than by category. West Vancouver's categories
    # describe the subject ("Skating: Public Skate", "Sports: Badminton")
    # and say nothing about whether a thing is droppable-into, so naming
    # categories would drag in ten-week registered courses. The portal
    # already answers that question on its own axis: type 6, "Daily
    # Activities and Drop-Ins". Filtering on it means a category West
    # Vancouver invents next month arrives on its own rather than being
    # silently excluded by a list here that nobody remembered to update.
    #
    # Only recreation buildings are listed. The portal also exposes the art
    # museum, the Ferry Building gallery, Municipal Hall, a secondary school
    # and three parks; each is one line away if it ever publishes drop-ins
    # worth having.
    #
    # The portal's own names for two of these are bare ("Aquatic Centre",
    # "Ice Arena") and would read as nobody's building on a dashboard that
    # spans nine cities, so they are given their full names here and the
    # portal's spelling is kept as an alias — see center_aliases in
    # scraper_activenet.py.
    *(
        {
            "source_name": "District of West Vancouver",
            "platform": "activenet",
            "base_url": "https://anc.ca.apm.activecommunities.com",
            "org_path": "westvanrec",
            "center_id": center_id,
            "location": location,
            "center_aliases": aliases,
            "type_ids": ["6"],
            "calendar_label": f"Drop-in — {location}",
            # Reached whenever the row's category is not one of the ones
            # scraper_activenet.CATEGORY_ACTIVITY_TYPES names.
            "activity_type": "Other",
        }
        for center_id, location, aliases in (
            ("42", "West Vancouver Community Centre", ()),
            ("32", "West Vancouver Aquatic Centre", ("Aquatic Centre",)),
            ("37", "West Vancouver Ice Arena", ("Ice Arena",)),
            ("51", "Gleneagles Community Centre", ()),
            ("43", "Gleneagles Golf Course", ()),
            (
                "34",
                "West Vancouver Seniors' Activity Centre",
                ("Seniors' Activity Centre",),
            ),
            ("29", "West Vancouver Youth Hub", ("Youth Hub",)),
        )
    ),
]

# How many days ahead to pull the schedule for.
SCHEDULE_WINDOW_DAYS = 14

# How long fetched results are cached in memory before re-scraping (seconds).
CACHE_TTL_SECONDS = 15 * 60

# How many sources are fetched at once.
#
# A cold request blocks on the whole scrape, so this is what decides how long
# the first visitor after a cache expiry waits. It matters more with every
# city added: sources are per-calendar on PerfectMind and per-building on
# ActiveNet, so a handful of cities is already dozens of sources, and at a
# fixed worker count the wait grows with them.
#
# Kept well below the source count on purpose. Every source of a given city
# hits that city's one portal, so this is also how hard this app leans on
# somebody else's server; a dozen or so parallel requests is ordinary
# browsing traffic, and a hundred is not.
SCRAPE_MAX_WORKERS = 16

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
    # City of Burnaby
    # Both points are the clubhouse, not the middle of the course. A golf
    # course is a big polygon and its centroid lands out on the fairways;
    # the clubhouse is where a lesson actually meets. For Riverway that is
    # a ~400 m difference, which is the width of the course.
    "Burnaby Mountain Golf Course": (49.264966, -122.942888),
    "Riverway Golf Course": (49.200628, -122.990303),
    # Outdoor pools, mapped to their park's centre rather than the pool
    # itself — OSM has the park but not the pool building.
    "Hume Park": (49.235173, -122.890505),
    "Moody Park": (49.213314, -122.929143),
}

# Venues that are deliberately not in FACILITY_COORDS yet.
#
# A venue missing from the table above gets no map pin, which is a fine
# failure — but it is also exactly what a typo in a source's "location"
# looks like, and a typo costs the pin silently and forever. So the two are
# told apart by being written down: test_scrapers.py requires every
# ActiveNet venue to be either mapped or listed here, and nowhere else.
#
# Everything here still appears in the schedule, in the filters and in
# search; only the map is missing it. Clearing an entry is one line: look
# the building up in Google Maps, right-click it, copy the coordinates from
# the top of the menu into FACILITY_COORDS, and delete the name from here.
VENUES_AWAITING_COORDS = frozenset(
    {
        # District of West Vancouver
        "West Vancouver Community Centre",
        "West Vancouver Aquatic Centre",
        "West Vancouver Ice Arena",
        "Gleneagles Community Centre",
        "Gleneagles Golf Course",
        "West Vancouver Seniors' Activity Centre",
        "West Vancouver Youth Hub",
    }
)

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
    {"name": "Burnaby", "cities": ("City of Burnaby",)},
    {"name": "West Vancouver", "cities": ("District of West Vancouver",)},
)

# Built once at import: {source_name -> area name}, so annotating an event
# is a dict lookup rather than a scan over AREAS.
CITY_AREAS = {
    city: area["name"] for area in AREAS for city in area["cities"]
}

# Broad activity groups, offered only as a starting preference.
#
# The filter bar above the schedule still offers all fourteen activity types
# individually — nothing is lost. These exist because the first-run dialog
# was asking a question with fourteen answers, most of which nobody chooses:
# "Adult" is snooker and computer help, "All Ages" is gymnastics and
# childminding, "Youth" is two chess games. Those are calendar labels, not
# choices, and they made the real choices harder to see.
#
# A group whose types are None collects everything the named groups didn't
# claim. That entry is what keeps this list honest: an activity type a
# portal invents next month appears there on its own rather than quietly
# becoming unreachable from this dialog.
ACTIVITY_GROUPS = (
    ("Skating", ("Skating",)),
    ("Swimming", ("Swimming",)),
    (
        "Court & team sports",
        (
            "Badminton",
            "Basketball",
            "Pickleball",
            "Volleyball",
            "Table Tennis",
            "Soccer",
            "Sports",
            "Court Booking",
        ),
    ),
    ("Fitness classes", ("Fitness",)),
    ("Golf", ("Golf",)),
    ("Everything else", None),
)
