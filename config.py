# Municipal recreation portals to scrape.
#
# Cities do not all run the same booking software, so each entry names the
# "platform" it is on and scraper.py hands it to the matching module. Two
# are supported:
#
#   "perfectmind" — Coquitlam, Port Moody, New Westminster. Keys: base_url,
#       org_path, widget_id, calendar_id. One entry per calendar.
#   "activenet"   — Port Coquitlam, Burnaby, Vancouver, West Vancouver.
#       Keys: base_url, org_path, and then either a building (center_id +
#       location, one entry per building) or a name search (keyword, with
#       an optional "exclude" pattern). A search is the fallback for a
#       portal whose drop-ins are buried in a much larger course
#       catalogue — see the Vancouver entries. With no "location" the
#       venue is read from each row instead of configured.
#       Narrow with category_ids, type_ids, or neither — see below.
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
    # Port Moody's two public-swim calendars used to be here and are gone.
    # Both now answer "Calendar is not allowed for the widget", and the
    # city's own public-swimming page still links to those same dead ids,
    # as does its swim-lessons page to two others. So there is no working
    # swim calendar to point at — this is Port Moody's outage, not a stale
    # id here, and it cost the dashboard a red "temporarily unavailable"
    # banner on every visit. They come back when the city republishes them.
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
    # Three more of Port Moody's drop-in calendars, found while working out
    # what had happened to the swims. They were never configured, and they
    # carry most of what the city actually publishes: the fitness one alone
    # returns more sessions than every other Port Moody calendar together.
    #
    # Two live ones are deliberately left out. "Weight Room" is orientation
    # appointments rather than sessions to attend, and "Childminding" is a
    # service you book while you use the building, not an activity — both
    # would be noise on a schedule of things to turn up to.
    {
        "source_name": "City of Port Moody",
        "base_url": "https://cityofportmoody.perfectmind.com",
        "org_path": "Contacts",
        "widget_id": "15f6af07-39c5-473e-b053-96653f77a406",
        "calendar_id": "e63d05c2-8f38-4a38-9df7-b0f2e46ffe14",
        "calendar_label": "Drop-in Fitness",
        "activity_type": "Fitness",
    },
    {
        "source_name": "City of Port Moody",
        "base_url": "https://cityofportmoody.perfectmind.com",
        "org_path": "Contacts",
        "widget_id": "15f6af07-39c5-473e-b053-96653f77a406",
        "calendar_id": "e0c249df-26d1-4953-98b5-5b5c2d9db684",
        # Mixed, like Coquitlam's adult calendar: table tennis and tai chi
        # beside bridge and board games, so classify_activity names the
        # ones it recognises and the rest fall here.
        "calendar_label": "Drop-in Adult & Senior Recreation",
        "activity_type": "Adult",
    },
    {
        "source_name": "City of Port Moody",
        "base_url": "https://cityofportmoody.perfectmind.com",
        "org_path": "Contacts",
        "widget_id": "15f6af07-39c5-473e-b053-96653f77a406",
        "calendar_id": "00218b3e-d8db-47c2-b327-a9d118239a65",
        "calendar_label": "Drop-in Early Years",
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
    # North Vancouver Recreation & Culture, which runs recreation for both
    # the City and the District of North Vancouver — one portal, both.
    #
    # NVRC publishes eighteen calendars across eight widgets, and a
    # calendar only renders under the widget it belongs to. These four are
    # the ones carrying drop-ins; the other fourteen are registration
    # pages for lessons and courses and return nothing here.
    *(
        {
            "source_name": "North Vancouver Recreation & Culture",
            "base_url": "https://nvrc.perfectmind.com",
            "org_path": "23734/Clients",
            # Not the widget NVRC's own landing pages advertise: that one
            # refuses every calendar below. This is the one its schedule
            # links actually use.
            "widget_id": "a28b2c65-61af-407f-80d1-eaa58f30a94a",
            "calendar_id": calendar_id,
            "calendar_label": label,
            "activity_type": activity_type,
        }
        for calendar_id, label, activity_type in (
            ("fabf60eb-7cf3-40c3-8004-79e50fdc6db0", "Swim Schedules", "Swimming"),
            ("9290cb7e-d450-4972-b327-b89aa12b2a69", "Skate Schedules", "Skating"),
            ("d313e7d8-0d72-4e0b-92c5-98d8017ab64e", "Open Gym Schedules", "Sports"),
            (
                "443499b3-3e7d-454d-acae-4e02474fef9f",
                "Fitness Studio Workouts",
                "Fitness",
            ),
        )
    ),
    # City of Richmond, on PerfectMind. Ice only, because ice is all its
    # PerfectMind tenant publishes as drop-ins — a crawl of the city's own
    # recreation pages found five calendars and these are the two with
    # anything in them.
    #
    # Everything here is named "REGISTERED VISIT - ...", which is Richmond
    # saying a drop-in needs booking ahead, the same thing Coquitlam means
    # by "pre-registration recommended". Richmond also keeps an ActiveNet
    # tenant (org "cityofrichmond"), which is the likely home of its pool
    # and gym schedules and is not configured here yet.
    *(
        {
            "source_name": "City of Richmond",
            "base_url": "https://richmondcity.perfectmind.com",
            "org_path": "23650/Clients",
            "widget_id": "15f6af07-39c5-473e-b053-96653f77a406",
            "calendar_id": calendar_id,
            "calendar_label": label,
            "activity_type": "Skating",
        }
        for calendar_id, label in (
            ("8bd697eb-ee1e-4067-b6bb-be1901a7753d", "Richmond Ice Centre"),
            ("5bc32e4a-6607-47f5-8513-53b2dbc4f83e", "Minoru Arenas"),
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
    # City of Vancouver, on ActiveNet, but configured by *search* rather
    # than by building — the only city here that needs it.
    #
    # Vancouver publishes about 6,900 activities in a fortnight and almost
    # all of them are registered courses: swim lessons, skating levels, art
    # classes. Its drop-ins are in there too, but the portal offers no
    # "drop-in" filter to ask for them, and pulling the Aquatics, Skating
    # and Sports categories whole would mean fetching roughly 120 pages of
    # lesson listings to find a few dozen drop-ins. So each entry below is
    # a name search instead, which is a handful of pages each.
    #
    # Searches are allowed to overlap; scraper.py drops an occurrence that
    # two of them both return. "Open Gym Drop-In" answers two of these.
    #
    # No "location" key, deliberately: a search that is not pinned to one
    # building gets rows from all of them, so each row names its own venue.
    *(
        {
            "source_name": "City of Vancouver",
            "platform": "activenet",
            "base_url": "https://anc.ca.apm.activecommunities.com",
            "org_path": "vancouver",
            "keyword": keyword,
            "category_ids": category_ids,
            "exclude": exclude,
            "calendar_label": f"Drop-in — {keyword}",
            "activity_type": activity_type,
        }
        for keyword, category_ids, activity_type, exclude in (
            ("Public Skate", ["24"], "Skating", None),
            # No category filter on the swims: Vancouver files some of them
            # outside Aquatics, and narrowing to that category returned
            # nothing at all.
            ("Public Swim", [], "Swimming", None),
            # "Length Swim" also matches the block where the lanes are
            # handed to lessons and the swim club, which is the opposite of
            # a drop-in.
            ("Length Swim", [], "Swimming", r"lesson|swim club"),
            ("Drop-in", ["27"], "Sports", None),
            ("Open Gym", ["27"], "Sports", None),
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
    # Port Moody's adult and senior drop-ins run here, not at the complex.
    "Kyle Centre": (49.276125, -122.857062),
    # Port Moody's adult and senior drop-ins run here rather than at the
    # rec complex. No coordinates yet, so no pin — see
    # VENUES_AWAITING_COORDS, which cannot enforce it for a PerfectMind
    # source because those learn their venue names by scraping.
    # "Kyle Centre": (?, ?),
    "Westhill Pool": (49.284250, -122.879587),
    # City of Port Coquitlam
    "Port Coquitlam Community Centre": (49.260084, -122.777032),
    # OSM has no building here; this is Laurier Ave at the rec centre's
    # block, so the marker is on the right street rather than the door.
    "Hyde Creek Recreation Centre": (49.274791, -122.763090),
    # The youth centre sits inside Leigh Square Community Arts Village.
    "Outlet": (49.261973, -122.780310),
    # North Vancouver Recreation & Culture
    # Each of these matched its own name in OpenStreetMap, in the right
    # municipality — the standard the two West Vancouver holdouts below
    # could not meet.
    "Karen Magnussen Community Recreation Centre": (49.330594, -123.045920),
    "Harry Jerome Community Recreation Centre": (49.331010, -123.070851),
    "Ron Andrews Community Recreation Centre": (49.314197, -123.000898),
    "Delbrook Community Recreation Centre": (49.336054, -123.092038),
    "Parkgate Community Centre": (49.318080, -122.970497),
    "Lions Gate Community Recreation Centre": (49.326476, -123.121378),
    "John Braithwaite Community Centre": (49.312434, -123.080647),
    # City of Richmond
    "Richmond Ice Centre": (49.136387, -123.066688),
    "Minoru Arenas": (49.164468, -123.142951),
    # City of New Westminster
    "Moody Park Arena": (49.215617, -122.926213),
    "təməsew̓txʷ Aquatic and Community Centre": (49.221138, -122.907594),
    "Queen's Park Sportsplex": (49.213589, -122.903744),
    # Appears only in the ice season, so it was missing until skating
    # returned to New Westminster's schedule.
    "Queen's Park Arena": (49.214878, -122.905853),
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
    # City of Vancouver
    # Geocoded once from OpenStreetMap and pinned here, like the rest.
    # Vancouver abbreviates "Community Centre" to "Cmty Centre" in its
    # portal, and these keys must match what the portal sends.
    "Britannia Cmty Centre": (49.275064, -123.070369),
    # Inside the Britannia complex; OSM has the site, not the pool.
    "Britannia Pool": (49.275064, -123.070369),
    "Britannia Rink": (49.276053, -123.070612),
    "Champlain Heights Cmty Centre": (49.214722, -123.031898),
    "Coal Harbour Cmty Centre": (49.290415, -123.125114),
    "Douglas Park Cmty Centre": (49.252205, -123.122463),
    "Dunbar Cmty Centre": (49.243717, -123.186028),
    "False Creek Cmty Centre": (49.269444, -123.134088),
    "Hastings Cmty Centre": (49.280623, -123.039427),
    "Hillcrest Aquatic Centre": (49.243813, -123.107061),
    "Hillcrest Cmty Centre": (49.243738, -123.107859),
    "Hillcrest Rink": (49.244196, -123.107837),
    "Kensington Cmty Centre": (49.237313, -123.074928),
    "Kerrisdale Cmty Centre": (49.233140, -123.156936),
    "Kerrisdale Cyclone Taylor Arena": (49.235290, -123.154027),
    "Killarney Cmty Centre": (49.226921, -123.043439),
    "Killarney Pool": (49.227212, -123.044156),
    "Killarney Rink": (49.226726, -123.043453),
    "Kitsilano Cmty Centre": (49.261525, -123.162090),
    "Kitsilano Rink": (49.262370, -123.161986),
    "Lord Byng Pool": (49.259503, -123.192778),
    "Marpole-Oakridge Cmty Centre": (49.214859, -123.129049),
    "Mount Pleasant Cmty Centre": (49.264141, -123.100050),
    "Renfrew Park Cmty Centre": (49.251235, -123.042921),
    # Shares its building with the community centre above.
    "Renfrew Park Pool": (49.251235, -123.042921),
    "Roundhouse Cmty Arts and Rec Centre": (49.273401, -123.121939),
    "Strathcona Cmty Centre": (49.279644, -123.091713),
    "Sunset Cmty Centre": (49.222835, -123.101171),
    "Sunset Rink": (49.223226, -123.098210),
    "Templeton Park Pool": (49.278296, -123.058986),
    "Thunderbird Cmty Centre": (49.263999, -123.031292),
    "Trout Lake Cmty Centre": (49.254863, -123.065207),
    # OSM point is the complex's fitness centre, same building.
    "Trout Lake Rink": (49.255288, -123.065129),
    "West End Cmty Centre": (49.290204, -123.136251),
    "West End Rink": (49.290159, -123.135966),
    # District of West Vancouver
    # From OpenStreetMap, like the rest, and each checked against the
    # municipality in the result rather than taken on trust: a plain search
    # for "West Vancouver Aquatic Centre" confidently returns Vancouver's
    # West End one, four kilometres and a different city away.
    "West Vancouver Community Centre": (49.331351, -123.169198),
    "West Vancouver Ice Arena": (49.332142, -123.170307),
    "West Vancouver Seniors' Activity Centre": (49.330729, -123.168810),
    "Gleneagles Community Centre": (49.364069, -123.277799),
    # The clubhouse rather than the middle of the course, for the reason
    # given against Burnaby's two above.
    "Gleneagles Golf Course": (49.363878, -123.279143),
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
        # District of West Vancouver. Neither is in OpenStreetMap under any
        # name tried. Both eventually returned *something* — but only by
        # being handed a street address guessed from memory, and what came
        # back was a stretch of Marine Drive for the first and an apartment
        # block called Esquimalt Towers for the second. Every coordinate
        # above matched its own venue by name; these did not, and a pin on
        # the wrong building is worse than no pin at all.
        "West Vancouver Aquatic Centre",
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
    {"name": "Vancouver", "cities": ("City of Vancouver",)},
    {"name": "West Vancouver", "cities": ("District of West Vancouver",)},
    {
        "name": "North Vancouver",
        # One commission serves the City and the District alike, so this is
        # the rare area whose name is not a city's.
        "cities": ("North Vancouver Recreation & Culture",),
    },
    {"name": "Richmond", "cities": ("City of Richmond",)},
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
