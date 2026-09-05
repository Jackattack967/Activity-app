(function () {
  "use strict";

  // Wire up the preferences modal's escape hatches FIRST, standalone and
  // independent of everything else below. If anything later in this file
  // throws, these must still work so the modal can never truly trap someone.
  const preferencesModal = document.getElementById("preferences-modal");
  const prefCloseBtn = document.getElementById("pref-close-btn");

  function closePreferencesModal() {
    if (preferencesModal) preferencesModal.hidden = true;
  }

  if (prefCloseBtn) prefCloseBtn.addEventListener("click", closePreferencesModal);
  if (preferencesModal) {
    preferencesModal.addEventListener("click", (e) => {
      if (e.target === preferencesModal) closePreferencesModal();
    });
  }
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && preferencesModal && !preferencesModal.hidden) {
      closePreferencesModal();
    }
  });

  // Header menu. Wired up here, before runApp(), so the menu still opens even
  // if something later fails — it holds Preferences, Alerts and Log out.
  const menuBtn = document.getElementById("menu-btn");
  const menuPanel = document.getElementById("main-menu");

  function closeMenu() {
    if (!menuPanel) return;
    menuPanel.hidden = true;
    if (menuBtn) menuBtn.setAttribute("aria-expanded", "false");
  }

  if (menuBtn && menuPanel) {
    menuBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      const open = menuPanel.hidden;
      menuPanel.hidden = !open;
      menuBtn.setAttribute("aria-expanded", String(open));
    });

    // Clicking a menu entry acts and then dismisses; clicking inside the
    // panel otherwise (e.g. the status text) should not close it. The alerts
    // toggle is the exception — it changes label to report the result, which
    // you'd never see if the menu closed out from under it.
    menuPanel.addEventListener("click", (e) => {
      const item = e.target.closest(".menu-item");
      if (item && item.id !== "alerts-btn") closeMenu();
      else e.stopPropagation();
    });

    document.addEventListener("click", closeMenu);
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") closeMenu();
    });
  }

  try {
    runApp();
  } catch (err) {
    console.error("Activity dashboard failed to initialize:", err);
  }

  function runApp() {
    const dayGroupsEl = document.getElementById("day-groups");
    const emptyStateEl = document.getElementById("empty-state");
    const lastUpdatedEl = document.getElementById("last-updated");
    const refreshBtn = document.getElementById("refresh-btn");
    const activityFiltersEl = document.getElementById("activity-filters");
    const areaFilterEl = document.getElementById("area-filter");
    const locationFilterEl = document.getElementById("location-filter");
    const keywordFilterEl = document.getElementById("keyword-filter");
    const openOnlyFilterEl = document.getElementById("open-only-filter");
    const favoritesOnlyFilterEl = document.getElementById("favorites-only-filter");

    const preferencesBtn = document.getElementById("preferences-btn");
    const prefOpenOnlyEl = document.getElementById("pref-open-only");
    const prefSaveBtn = document.getElementById("pref-save-btn");
    const prefSkipBtn = document.getElementById("pref-skip-btn");
    const prefEmailAlertsEl = document.getElementById("pref-email-alerts");
    const PREFS_KEY = "activityDashboardPreferences";

    let allEvents = [];
    try {
      allEvents = JSON.parse(document.getElementById("events-data").textContent);
    } catch (err) {
      console.error("Could not parse events data:", err);
    }
    let loggedIn = false;
    try {
      loggedIn = !!JSON.parse(document.getElementById("user-data").textContent).loggedIn;
    } catch (err) {
      console.error("Could not parse user data:", err);
    }
    let activeActivity = "all";

    function formatFetchedAt(epochSeconds) {
      if (!epochSeconds) return "Not yet loaded";
      const d = new Date(epochSeconds * 1000);
      return "Updated " + d.toLocaleString();
    }

    function badgeInfo(ev) {
      const spots = (ev.spots || "").trim();
      const status = (ev.status || "").trim();
      const spotsLower = spots.toLowerCase();
      if (spotsLower.includes("full")) {
        return { cls: "badge-full", text: spots, open: false };
      }
      if (spotsLower.includes("spot")) {
        return { cls: "badge-open", text: spots, open: true };
      }
      if (status === "Register") {
        return { cls: "badge-open", text: "Register", open: true };
      }
      if (status === "Closed") {
        return { cls: "badge-closed", text: "Closed", open: false };
      }
      if (status) {
        return { cls: "badge-info", text: status, open: false };
      }
      return { cls: "badge-info", text: "Details", open: false };
    }

    function formatDateHeading(isoDate, dayOfWeek) {
      if (!isoDate) return "Unknown date";
      const [y, m, d] = isoDate.split("-").map(Number);
      const dt = new Date(y, m - 1, d);
      const monthDay = dt.toLocaleDateString(undefined, { month: "long", day: "numeric" });

      const today = new Date();
      today.setHours(0, 0, 0, 0);
      const daysAway = Math.round((dt - today) / 86400000);
      if (daysAway === 0) return `Today · ${dayOfWeek}, ${monthDay}`;
      if (daysAway === 1) return `Tomorrow · ${dayOfWeek}, ${monthDay}`;
      return `${dayOfWeek}, ${monthDay}`;
    }

    function todayIso() {
      const d = new Date();
      const pad = (n) => String(n).padStart(2, "0");
      return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
    }

    // "09:30 PM" -> minutes since midnight, or null if unparseable.
    function timeToMinutes(text) {
      const m = /^(\d{1,2}):(\d{2})\s*(AM|PM)$/i.exec((text || "").trim());
      if (!m) return null;
      let hours = parseInt(m[1], 10) % 12;
      if (/PM/i.test(m[3])) hours += 12;
      return hours * 60 + parseInt(m[2], 10);
    }

    // A session earlier today is just noise — you can't attend it any more.
    function alreadyFinished(ev) {
      if (ev.date !== todayIso()) return false;
      const end = timeToMinutes(ev.end_time);
      const start = timeToMinutes(ev.start_time);
      const finishesAt = end === null ? start : end;
      if (finishesAt === null) return false;
      const now = new Date();
      return finishesAt < now.getHours() * 60 + now.getMinutes();
    }

    // A star covers the activity — its name at a venue — not the single
    // session clicked, since one activity is split across many recurring
    // course ids.
    function sameActivity(a, b) {
      return (
        a.source_name === b.source_name &&
        a.event_name === b.event_name &&
        (a.location || "") === (b.location || "")
      );
    }

    function countSessions(ev) {
      return allEvents.filter((e) => sameActivity(e, ev)).length;
    }

    function favoriteTitle(ev) {
      if (ev.favorite_scope === "activity") {
        const n = countSessions(ev);
        return `Watching all ${n} “${ev.event_name}” session${n === 1 ? "" : "s"}. Click to stop.`;
      }
      if (ev.favorite_scope === "session") {
        return "Watching just this one session. Click to stop.";
      }
      return "Watch this — you'll be alerted when a spot opens";
    }

    function shortDate(isoDate) {
      if (!isoDate) return "this session";
      const [y, m, d] = isoDate.split("-").map(Number);
      return new Date(y, m - 1, d).toLocaleDateString(undefined, {
        weekday: "short",
        month: "short",
        day: "numeric",
      });
    }

    async function toggleFavorite(ev, scope) {
      const resp = await fetch("/api/favorites", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          source_name: ev.source_name,
          event_name: ev.event_name,
          location: ev.location || "",
          course_id: ev.course_id,
          scope,
          date: ev.date,
        }),
      });
      const data = await resp.json();
      const on = !!data.favorited;

      if (on && scope === "session") {
        // Only this dated occurrence lights up.
        allEvents.forEach((e) => {
          if (sameActivity(e, ev) && e.date === ev.date) {
            e.is_favorited = true;
            e.favorite_scope = "session";
          }
        });
      } else {
        // Starting or stopping an activity-wide watch affects every session
        // of it; stopping also clears any one-off watch on the same activity.
        allEvents.forEach((e) => {
          if (sameActivity(e, ev)) {
            e.is_favorited = on;
            e.favorite_scope = on ? "activity" : null;
          }
        });
      }
      render();
    }

    function closeStarMenus() {
      document.querySelectorAll(".star-menu").forEach((m) => m.remove());
    }

    function openStarMenu(btn, ev) {
      closeStarMenus();
      const menu = document.createElement("div");
      menu.className = "star-menu";

      const n = countSessions(ev);
      const options = [
        {
          scope: "activity",
          label: `Watch every session`,
          sub: n > 1 ? `all ${n}, including future ones` : "including future ones",
        },
        {
          scope: "session",
          label: "Just this one",
          sub: shortDate(ev.date),
        },
      ];

      options.forEach((opt) => {
        const item = document.createElement("button");
        item.type = "button";
        item.className = "star-menu-item";
        item.innerHTML =
          `<span class="star-menu-label"></span><span class="star-menu-sub"></span>`;
        item.querySelector(".star-menu-label").textContent = opt.label;
        item.querySelector(".star-menu-sub").textContent = opt.sub;
        item.addEventListener("click", async (e) => {
          e.stopPropagation();
          closeStarMenus();
          try {
            await toggleFavorite(ev, opt.scope);
          } catch (err) {
            console.error("Failed to start watching:", err);
          }
        });
        menu.appendChild(item);
      });

      btn.parentElement.appendChild(menu);
      // Dismiss on the next outside click.
      setTimeout(() => {
        document.addEventListener("click", closeStarMenus, { once: true });
      }, 0);
    }

    function buildFavoriteButton(ev) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className =
        "favorite-btn" +
        (ev.is_favorited ? " favorited" : "") +
        (ev.favorite_scope === "session" ? " favorited-once" : "");
      btn.textContent = ev.is_favorited ? "★" : "☆";
      btn.title = favoriteTitle(ev);
      btn.addEventListener("click", async (e) => {
        e.stopPropagation();
        if (ev.is_favorited) {
          // Already watching — a click just stops, no need to ask how.
          btn.disabled = true;
          try {
            await toggleFavorite(ev, ev.favorite_scope || "activity");
          } catch (err) {
            console.error("Failed to stop watching:", err);
            btn.disabled = false;
          }
          return;
        }
        openStarMenu(btn, ev);
      });
      return btn;
    }

    function buildCard(ev) {
      const card = document.createElement("article");
      card.className = "event-card";

      const timeCol = document.createElement("div");
      timeCol.className = "event-time";
      timeCol.textContent = ev.start_time && ev.end_time
        ? `${ev.start_time} – ${ev.end_time}`
        : (ev.start_time || "Time TBD");
      card.appendChild(timeCol);

      const mainCol = document.createElement("div");
      mainCol.className = "event-main";

      const titleRow = document.createElement("div");
      titleRow.className = "event-title-row";

      if (loggedIn && ev.source_name && ev.course_id) {
        titleRow.appendChild(buildFavoriteButton(ev));
      }

      const title = document.createElement("h3");
      title.textContent = ev.event_name || "Untitled activity";
      titleRow.appendChild(title);

      const activityTag = document.createElement("span");
      activityTag.className = "activity-tag";
      activityTag.textContent = ev.activity_type;
      titleRow.appendChild(activityTag);

      mainCol.appendChild(titleRow);

      const facility = document.createElement("div");
      facility.className = "event-facility";
      facility.textContent = ev.facility || ev.location || "";
      mainCol.appendChild(facility);

      const metaRow = document.createElement("div");
      metaRow.className = "event-meta";
      if (ev.price) {
        const price = document.createElement("span");
        price.textContent = ev.price;
        metaRow.appendChild(price);
      }
      if (ev.calendar_label) {
        const label = document.createElement("span");
        label.className = "calendar-label";
        label.textContent = ev.calendar_label;
        metaRow.appendChild(label);
      }
      mainCol.appendChild(metaRow);

      // The portal's own description — equipment requirements, age rules,
      // supervision ratios. Collapsed by default so it doesn't bury the list,
      // but it answers "can I actually go to this?" without leaving the app.
      if (ev.details) {
        const details = document.createElement("details");
        details.className = "event-details";

        const summary = document.createElement("summary");
        summary.textContent = "Details";
        details.appendChild(summary);

        const body = document.createElement("p");
        body.className = "event-details-body";
        body.textContent = ev.details;
        details.appendChild(body);

        mainCol.appendChild(details);
      }

      card.appendChild(mainCol);

      const statusCol = document.createElement("div");
      statusCol.className = "event-status";

      // The badge is now purely a status indicator; the call to action is
      // its own clearly-labelled button below it.
      const badge = badgeInfo(ev);
      const badgeEl = document.createElement("span");
      badgeEl.className = "badge " + badge.cls;
      badgeEl.textContent = badge.text;
      statusCol.appendChild(badgeEl);

      if (ev.detail_url) {
        const isWaitlist = !badge.open && ev.has_waitlist;
        const registerEl = document.createElement("a");
        registerEl.className = "register-btn" + (isWaitlist ? " waitlist-btn" : "");
        registerEl.textContent = badge.open
          ? "Register / Pay ↗"
          : isWaitlist
          ? "Join waitlist ↗"
          : "View details ↗";
        registerEl.href = ev.detail_url;
        registerEl.target = "_blank";
        registerEl.rel = "noopener noreferrer";
        registerEl.title = isWaitlist
          ? `This session is full. Opens its official ${ev.source_name} page in a ` +
            "new tab, where the city runs the waitlist."
          : `Opens this session's official ${ev.source_name} page in a new tab, ` +
            "where registration and payment are handled by the city.";
        statusCol.appendChild(registerEl);
      }

      card.appendChild(statusCol);

      return card;
    }

    // --- Map view ---------------------------------------------------------
    //
    // One marker per venue, not per session: eleven "Stick, Ring & Puck"
    // sessions at Poirier are one building, and eleven stacked pins would
    // say nothing a single pin doesn't.
    //
    // Leaflet is loaded with `defer`, so it is not available while this file
    // first runs. The map is therefore built on the first switch to it,
    // which also means people who never open the map never pay for it.

    const viewToggleEl = document.getElementById("view-toggle");
    const mapViewEl = document.getElementById("map-view");
    const mapEl = document.getElementById("facility-map");
    const mapNoteEl = document.getElementById("map-note");

    const mapAreaLegendEl = document.getElementById("map-area-legend");

    // Roughly centres the Tri-Cities, used only until markers exist to fit.
    const MAP_HOME = [49.2695, -122.8175];
    const MAP_HOME_ZOOM = 12;
    // Long popups are unusable on a phone; the rest stay in the list view.
    const MAX_POPUP_SESSIONS = 8;

    // One colour per area, in the order config.py lists them. Areas are
    // named on the server, so this is looked up by name with a fallback
    // rather than by index — adding a city must never silently re-colour
    // every existing area.
    const AREA_COLORS = {
      Coquitlam: "#2563eb",
      "Port Coquitlam": "#c2410c",
      "Port Moody": "#0f766e",
      "New Westminster": "#7c3aed",
    };
    const AREA_FALLBACK_COLOR = "#64748b";

    function areaColor(area) {
      return AREA_COLORS[area] || AREA_FALLBACK_COLOR;
    }

    // A zone should read as "roughly here", not as a claim about a city
    // boundary, so it is drawn from the venues themselves and padded out.
    //
    // It is a hull around the venues rather than a circle. A circle centred
    // on Coquitlam's ten venues has to be about 6.7 km wide to reach
    // Maillardville and Smiling Creek, which is wide enough to swallow both
    // Port Moody and Port Coquitlam whole — so the circles said nothing.
    // Hulls of the same venues do not overlap at all.
    const ZONE_PADDING_METRES = 450;
    // Below three venues there is no polygon to draw, so those fall back to
    // a small circle — kept tight, since it has no shape to justify itself.
    const ZONE_FALLBACK_RADIUS_METRES = 650;
    // A hull thinner than the padding around it is a line, not an area, so
    // it takes the circle instead. Squaring the padding is the natural
    // scale for "too small to be worth outlining".
    const ZONE_MIN_AREA_SQ_METRES = 450 * 450;

    let currentView = "list";
    let map = null;
    let markerLayer = null;
    let zoneLayer = null;
    // Which venues the current framing was chosen for, so the view is only
    // re-fitted when that set changes.
    let lastFitKey = null;

    function ensureMap() {
      if (map) return true;
      if (!window.L) return false;

      map = L.map(mapEl, {
        scrollWheelZoom: true,
        // Eases the wheel zoom instead of jumping a whole level per notch.
        wheelPxPerZoomLevel: 120,
        zoomControl: true,
      }).setView(MAP_HOME, MAP_HOME_ZOOM);

      // OpenStreetMap's own tiles. Carto's Positron basemap was tried here
      // because it is muted and lets the markers dominate, but it now serves
      // an "API KEY REQUIRED" placeholder instead of map data — with an HTTP
      // 200 and a PNG content type, so only looking at the image reveals it.
      // These need no key and no account.
      L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        // Required by the OpenStreetMap tile usage policy.
        attribution:
          '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      }).addTo(map);

      L.control.scale({ imperial: false }).addTo(map);

      // Zones sit under the markers, so a pin is never obscured by the
      // tint of the area it belongs to.
      zoneLayer = L.layerGroup().addTo(map);
      markerLayer = L.layerGroup().addTo(map);
      return true;
    }

    function venueIcon(count, openCount, area) {
      // A numbered circle rather than Leaflet's default teardrop pin: the
      // count is the most useful thing about a venue at a glance, and a pin
      // that carries it saves opening the popup to find out. Green when
      // something is actually bookable there, matching the badges.
      //
      // The area is shown as the ring around the pin rather than as its
      // fill, because open-vs-full is the more important of the two and had
      // the fill first. A pin therefore answers "can I go?" by colour and
      // "whereabouts is this?" by ring, without either overwriting the
      // other.
      const cls = "venue-marker" + (openCount > 0 ? " venue-marker-open" : "");
      // count is an array length and the colour comes from the table above,
      // so neither is scraped text — safe to interpolate. Venue names are
      // not interpolated anywhere here; see buildPopup.
      return L.divIcon({
        className: "",
        html:
          `<div class="${cls}" style="--area-color:${areaColor(area)}">` +
          `<span>${count}</span></div>`,
        iconSize: [36, 36],
        iconAnchor: [18, 18],
        popupAnchor: [0, -20],
        tooltipAnchor: [0, -20],
      });
    }

    // Metres between two lat/lng pairs. The equirectangular approximation is
    // wrong by well under a metre at these distances, and the alternative is
    // a trig-heavy haversine for a number only ever used to size a circle
    // and to rank areas by nearness.
    function distanceMetres(a, b) {
      const toRad = Math.PI / 180;
      const meanLat = ((a[0] + b[0]) / 2) * toRad;
      const x = (b[1] - a[1]) * toRad * Math.cos(meanLat);
      const y = (b[0] - a[0]) * toRad;
      return Math.sqrt(x * x + y * y) * 6371000;
    }

    function centroid(points) {
      const lat = points.reduce((sum, p) => sum + p[0], 0) / points.length;
      const lng = points.reduce((sum, p) => sum + p[1], 0) / points.length;
      return [lat, lng];
    }

    // Where each area is, derived from the venues in the data rather than
    // configured separately — so a new venue moves its area's centre on its
    // own and there is no second list to keep in step.
    function areaCentres(events) {
      const points = new Map();
      for (const ev of events) {
        if (!ev.area || typeof ev.lat !== "number" || typeof ev.lng !== "number") continue;
        if (!points.has(ev.area)) points.set(ev.area, new Map());
        // Keyed by venue so a busy centre doesn't drag the centroid toward
        // itself just by having more sessions than its neighbours.
        points.get(ev.area).set(ev.location, [ev.lat, ev.lng]);
      }
      const result = new Map();
      for (const [area, venues] of points) {
        const coords = Array.from(venues.values());
        result.set(area, { centre: centroid(coords), coords });
      }
      return result;
    }

    // Andrew's monotone chain: sort the points, then sweep the lower and
    // upper edges, dropping any point that turns the wrong way. Returns the
    // outline in order, or fewer than three points if they are collinear.
    function convexHull(points) {
      const sorted = points
        .slice()
        .sort((a, b) => a[0] - b[0] || a[1] - b[1])
        .filter((p, i, all) => i === 0 || p[0] !== all[i - 1][0] || p[1] !== all[i - 1][1]);
      if (sorted.length < 3) return sorted;

      const cross = (o, a, b) =>
        (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);

      const build = (list) => {
        const out = [];
        for (const p of list) {
          while (out.length >= 2 && cross(out[out.length - 2], out[out.length - 1], p) <= 0) {
            out.pop();
          }
          out.push(p);
        }
        out.pop();
        return out;
      };
      return build(sorted).concat(build(sorted.slice().reverse()));
    }

    // Roughly how much ground a hull encloses, in square metres. Used only
    // to reject shapes too thin to mean anything: the collinearity test in
    // convexHull compares a floating-point cross product against zero, and
    // three venues along one road produce a value that is merely nearly
    // zero, so they survive as a hull with no width. Measuring the result
    // catches that where testing the arithmetic cannot.
    function polygonAreaMetres(points) {
      if (points.length < 3) return 0;
      const latMetres = 111320;
      const lngMetres = latMetres * Math.cos((points[0][0] * Math.PI) / 180);
      let sum = 0;
      for (let i = 0; i < points.length; i += 1) {
        const [aLat, aLng] = points[i];
        const [bLat, bLng] = points[(i + 1) % points.length];
        sum += aLng * lngMetres * (bLat * latMetres) - bLng * lngMetres * (aLat * latMetres);
      }
      return Math.abs(sum) / 2;
    }

    // A hull runs exactly through the outermost venues, which would clip
    // those markers in half. Pushing each corner away from the centre gives
    // the outline some breathing room without needing real polygon offset.
    function padOutward(points, centre, metres) {
      const latMetres = 111320;
      const lngMetres = latMetres * Math.cos((centre[0] * Math.PI) / 180);
      return points.map(([lat, lng]) => {
        const dLat = lat - centre[0];
        const dLng = lng - centre[1];
        const length = Math.hypot(dLat * latMetres, dLng * lngMetres);
        if (!length) return [lat, lng];
        const scale = (length + metres) / length;
        return [centre[0] + dLat * scale, centre[1] + dLng * scale];
      });
    }

    function renderZones(visible) {
      zoneLayer.clearLayers();
      const centres = areaCentres(visible);

      // With one area on screen the tint says nothing the map doesn't
      // already show, and it only dulls the tiles underneath.
      if (centres.size > 1) {
        for (const [area, { centre, coords }] of centres) {
          const style = {
            color: areaColor(area),
            weight: 1,
            opacity: 0.5,
            fillColor: areaColor(area),
            fillOpacity: 0.07,
            interactive: false,
          };
          const hull = convexHull(coords);
          if (hull.length >= 3 && polygonAreaMetres(hull) >= ZONE_MIN_AREA_SQ_METRES) {
            L.polygon(padOutward(hull, centre, ZONE_PADDING_METRES), style).addTo(zoneLayer);
          } else {
            // One or two venues, or all of them along one road — there is
            // no area to enclose, so mark the spot rather than draw a
            // sliver that only looks like a mistake.
            L.circle(centre, { ...style, radius: ZONE_FALLBACK_RADIUS_METRES }).addTo(zoneLayer);
          }
        }
      }

      if (!mapAreaLegendEl) return;
      mapAreaLegendEl.textContent = "";
      if (centres.size <= 1) return;
      for (const area of Array.from(centres.keys()).sort()) {
        const item = document.createElement("span");
        const dot = document.createElement("i");
        dot.className = "legend-dot legend-dot-area";
        dot.style.background = areaColor(area);
        item.append(dot, document.createTextNode(area));
        mapAreaLegendEl.appendChild(item);
      }
    }

    function buildPopup(venue, events) {
      // Built as DOM rather than an HTML string: these values come from a
      // scraped third-party page, and innerHTML would make a portal's
      // session name executable in the browser.
      const wrap = document.createElement("div");
      wrap.className = "map-popup";

      const title = document.createElement("h3");
      title.textContent = venue;
      wrap.appendChild(title);

      const sorted = events
        .slice()
        .sort((a, b) =>
          `${a.date} ${a.start_time}`.localeCompare(`${b.date} ${b.start_time}`)
        );
      const shown = sorted.slice(0, MAX_POPUP_SESSIONS);

      const list = document.createElement("ul");
      list.className = "map-popup-list";
      for (const ev of shown) {
        const item = document.createElement("li");

        const name = document.createElement("span");
        name.className = "map-popup-name";
        name.textContent = ev.event_name;

        const when = document.createElement("span");
        when.className = "map-popup-when";
        when.textContent = [
          formatDateHeading(ev.date, ev.day_of_week),
          ev.start_time,
        ]
          .filter(Boolean)
          .join(" · ");

        const badge = badgeInfo(ev);
        const badgeEl = document.createElement("span");
        badgeEl.className = "badge " + badge.cls;
        badgeEl.textContent = badge.text;

        item.append(name, when, badgeEl);
        list.appendChild(item);
      }
      wrap.appendChild(list);

      if (sorted.length > shown.length) {
        const more = document.createElement("p");
        more.className = "map-popup-more";
        const n = sorted.length - shown.length;
        more.textContent = `+${n} more session${n === 1 ? "" : "s"} — see the list view`;
        wrap.appendChild(more);
      }
      return wrap;
    }

    function renderMap(visible) {
      // Nothing to do while the map is hidden; switching to it re-renders.
      if (currentView !== "map") return;
      if (!ensureMap()) {
        mapNoteEl.textContent =
          "The map library could not be loaded. The list view still works.";
        return;
      }

      markerLayer.clearLayers();
      renderZones(visible);

      const byVenue = new Map();
      let unplaced = 0;
      for (const ev of visible) {
        if (typeof ev.lat !== "number" || typeof ev.lng !== "number") {
          unplaced += 1;
          continue;
        }
        const key = ev.location || "";
        if (!byVenue.has(key)) byVenue.set(key, []);
        byVenue.get(key).push(ev);
      }

      const points = [];
      for (const [venue, events] of byVenue) {
        const { lat, lng } = events[0];
        const openCount = events.filter((ev) => badgeInfo(ev).open).length;

        const marker = L.marker([lat, lng], {
          icon: venueIcon(events.length, openCount, events[0].area),
          // Venues with something open sit above the ones without, so an
          // open pin is never hidden under a full one.
          zIndexOffset: openCount > 0 ? 1000 : 0,
          title: venue,
        });
        marker.bindPopup(() => buildPopup(venue, events), { maxWidth: 320 });
        marker.bindTooltip(
          `${venue} — ${events.length} session${events.length === 1 ? "" : "s"}` +
            (openCount > 0 ? `, ${openCount} open` : ""),
          { direction: "top" }
        );
        marker.addTo(markerLayer);
        points.push([lat, lng]);
      }

      // Only re-frame when the set of venues actually changed. Refitting on
      // every render would throw away the zoom someone just chose the
      // moment they ticked a filter.
      const fitKey = Array.from(byVenue.keys()).sort().join("|");
      if (fitKey !== lastFitKey) {
        lastFitKey = fitKey;
        if (points.length > 0) {
          map.fitBounds(points, { padding: [50, 50], maxZoom: 14 });
        } else {
          map.setView(MAP_HOME, MAP_HOME_ZOOM);
        }
      }

      const venues = byVenue.size;
      const sessions = visible.length - unplaced;
      mapNoteEl.textContent =
        venues === 0
          ? "No locations match your filters."
          : `${sessions} session${sessions === 1 ? "" : "s"} at ${venues} location${
              venues === 1 ? "" : "s"
            }.` + (unplaced > 0 ? ` ${unplaced} at venues with no map position.` : "");
    }

    function setView(view) {
      currentView = view;
      const showMap = view === "map";

      mapViewEl.hidden = !showMap;
      dayGroupsEl.hidden = showMap;

      viewToggleEl.querySelectorAll(".view-btn").forEach((btn) => {
        const active = btn.dataset.view === view;
        btn.classList.toggle("active", active);
        btn.setAttribute("aria-pressed", active ? "true" : "false");
      });

      if (showMap) {
        // Order matters. Leaflet caches its container's size, and anything
        // measured while the container was hidden is wrong — grey tiles, and
        // a fitBounds that frames the wrong area. So re-measure first, then
        // draw. The container is already unhidden by this point.
        if (ensureMap()) map.invalidateSize();
        renderMap(visibleEvents());
      }
    }

    if (viewToggleEl) {
      viewToggleEl.addEventListener("click", (e) => {
        const btn = e.target.closest("button[data-view]");
        if (!btn) return;
        setView(btn.dataset.view);
      });
    }

    // The events currently passing every filter. Split out of render() so
    // the list and the map are guaranteed to be showing the same set —
    // "the map is another view of this data", not a second query.
    function visibleEvents() {
      const keyword = keywordFilterEl.value.trim().toLowerCase();
      const area = areaFilterEl ? areaFilterEl.value : "";
      const location = locationFilterEl.value;
      const openOnly = openOnlyFilterEl.checked;

      const favoritesOnly = favoritesOnlyFilterEl ? favoritesOnlyFilterEl.checked : false;

      const upcoming = allEvents.filter((ev) => !alreadyFinished(ev));

      return upcoming.filter((ev) => {
        if (activeActivity !== "all" && ev.activity_type !== activeActivity) return false;
        if (area && ev.area !== area) return false;
        if (location && ev.location !== location) return false;
        if (keyword && !ev.event_name.toLowerCase().includes(keyword)) return false;
        if (favoritesOnly && !ev.is_favorited) return false;
        // Open-only used to be applied after the cards were built, via
        // card._open. Doing it here instead gives the same answer —
        // badgeInfo() is what set that flag — and lets the map reuse it.
        if (openOnly && !badgeInfo(ev).open) return false;
        return true;
      });
    }

    function renderList(visible) {
      dayGroupsEl.innerHTML = "";

      const groups = new Map();
      for (const ev of visible) {
        const key = ev.date || "";
        if (!groups.has(key)) groups.set(key, []);
        groups.get(key).push(ev);
      }

      const sortedKeys = Array.from(groups.keys()).sort();

      for (const key of sortedKeys) {
        const events = groups.get(key);

        const section = document.createElement("section");
        section.className = "day-group";

        const heading = document.createElement("h2");
        heading.textContent = formatDateHeading(key, events[0].day_of_week);
        section.appendChild(heading);

        const list = document.createElement("div");
        list.className = "event-list";
        events.map(buildCard).forEach((c) => list.appendChild(c));
        section.appendChild(list);

        dayGroupsEl.appendChild(section);
      }
    }

    function render() {
      const keyword = keywordFilterEl.value.trim().toLowerCase();
      const area = areaFilterEl ? areaFilterEl.value : "";
      const location = locationFilterEl.value;
      const openOnly = openOnlyFilterEl.checked;
      const favoritesOnly = favoritesOnlyFilterEl ? favoritesOnlyFilterEl.checked : false;

      const upcoming = allEvents.filter((ev) => !alreadyFinished(ev));
      const visible = visibleEvents();

      renderList(visible);
      renderMap(visible);

      const renderedAny = visible.length > 0;
      emptyStateEl.hidden = renderedAny;
      if (!renderedAny) {
        const anyFilterActive =
          activeActivity !== "all" ||
          !!area ||
          !!location ||
          !!keyword ||
          openOnly ||
          favoritesOnly;
        const textEl = document.getElementById("empty-state-text");
        const clearBtn = document.getElementById("clear-filters-btn");
        if (textEl) {
          textEl.textContent = anyFilterActive
            ? "No activities match your filters."
            : upcoming.length === 0
            ? "No upcoming activities found. The schedule may not be published yet."
            : "Nothing to show right now.";
        }
        // Only offer to clear filters when filters are actually the reason.
        if (clearBtn) clearBtn.hidden = !anyFilterActive;
      }
    }

    // Every venue the page was served with, so the location dropdown can be
    // narrowed to one area and then widened again without a round trip.
    const allLocationOptions = Array.from(locationFilterEl.options).map((o) => ({
      value: o.value,
      label: o.textContent,
    }));

    // Which area each venue is in, learned from the events themselves.
    function venueAreas() {
      const map = new Map();
      for (const ev of allEvents) {
        if (ev.location && ev.area && !map.has(ev.location)) map.set(ev.location, ev.area);
      }
      return map;
    }

    // Keep the location list to the chosen area. Without this the two
    // filters can be set to contradict each other — "Coquitlam" plus a Port
    // Moody pool — and the page goes blank with no hint why.
    function syncLocationOptions() {
      if (!areaFilterEl) return;
      const area = areaFilterEl.value;
      const areas = venueAreas();
      const previous = locationFilterEl.value;

      locationFilterEl.textContent = "";
      for (const option of allLocationOptions) {
        if (area && option.value && areas.get(option.value) !== area) continue;
        const el = document.createElement("option");
        el.value = option.value;
        el.textContent = option.label;
        locationFilterEl.appendChild(el);
      }
      // Drop a venue that the new area doesn't contain, rather than leaving
      // a selection the dropdown no longer offers.
      locationFilterEl.value = Array.from(locationFilterEl.options).some(
        (o) => o.value === previous
      )
        ? previous
        : "";
    }

    function clearAllFilters() {
      selectActivityChip("all");
      if (areaFilterEl) areaFilterEl.value = "";
      syncLocationOptions();
      locationFilterEl.value = "";
      keywordFilterEl.value = "";
      openOnlyFilterEl.checked = false;
      if (favoritesOnlyFilterEl) favoritesOnlyFilterEl.checked = false;
      render();
    }

    function selectActivityChip(value) {
      activeActivity = value;
      activityFiltersEl.querySelectorAll(".chip").forEach((c) => {
        c.classList.toggle("active", c.dataset.activity === value);
      });
    }

    activityFiltersEl.addEventListener("click", (e) => {
      const btn = e.target.closest("button[data-activity]");
      if (!btn) return;
      selectActivityChip(btn.dataset.activity);
      render();
    });

    if (areaFilterEl) {
      areaFilterEl.addEventListener("change", () => {
        syncLocationOptions();
        // Picking an area is a request to look somewhere else, so the map
        // reframes on it rather than holding the previous area's view.
        lastFitKey = null;
        render();
      });
    }

    locationFilterEl.addEventListener("change", render);
    keywordFilterEl.addEventListener("input", render);
    openOnlyFilterEl.addEventListener("change", render);
    if (favoritesOnlyFilterEl) favoritesOnlyFilterEl.addEventListener("change", render);

    const clearFiltersBtn = document.getElementById("clear-filters-btn");
    if (clearFiltersBtn) clearFiltersBtn.addEventListener("click", clearAllFilters);

    refreshBtn.addEventListener("click", async () => {
      refreshBtn.disabled = true;
      refreshBtn.textContent = "Refreshing…";
      try {
        const resp = await fetch("/api/events?refresh=1");
        const data = await resp.json();
        allEvents = data.events;
        lastUpdatedEl.textContent = formatFetchedAt(data.fetched_at);
        render();
      } catch (err) {
        lastUpdatedEl.textContent = "Refresh failed — showing last known data";
      } finally {
        refreshBtn.disabled = false;
        refreshBtn.textContent = "Refresh";
      }
    });

    function setRadioGroupValue(name, value) {
      const radios = preferencesModal.querySelectorAll(`input[name="${name}"]`);
      let matched = false;
      radios.forEach((r) => {
        if (r.value === value) {
          r.checked = true;
          matched = true;
        }
      });
      if (!matched && radios.length) radios[0].checked = true;
    }

    function getRadioGroupValue(name) {
      const checked = preferencesModal.querySelector(`input[name="${name}"]:checked`);
      return checked ? checked.value : "";
    }

    function readStoredPreferences() {
      try {
        const raw = localStorage.getItem(PREFS_KEY);
        return raw ? JSON.parse(raw) : null;
      } catch (err) {
        return null;
      }
    }

    function writeStoredPreferences(prefs) {
      // Some browsers (e.g. Safari Private Browsing) throw on writes — don't
      // let that trap the user with a modal that can't be dismissed.
      try {
        localStorage.setItem(PREFS_KEY, JSON.stringify(prefs));
      } catch (err) {
        /* best-effort: preference just won't persist across reloads */
      }
    }

    async function fetchAccountPreferences() {
      try {
        const resp = await fetch("/api/preferences");
        if (!resp.ok) return null;
        return await resp.json();
      } catch (err) {
        console.error("Failed to load account preferences:", err);
        return null;
      }
    }

    async function saveAccountPreferences(prefs) {
      try {
        await fetch("/api/preferences", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(prefs),
        });
      } catch (err) {
        console.error("Failed to save account preferences:", err);
      }
    }

    function applyPreferences(prefs) {
      selectActivityChip(prefs.activity || "all");
      if (areaFilterEl) areaFilterEl.value = prefs.area || "";
      // Narrow the venue list before restoring the saved venue, or the
      // saved value would be dropped as "not in this area" on every load.
      syncLocationOptions();
      locationFilterEl.value = prefs.location || "";
      openOnlyFilterEl.checked = !!prefs.openOnly;
    }

    // Email alerts are an account setting rather than a view filter, so it is
    // kept out of applyPreferences (which only drives the visible filters).
    let emailAlertsEnabled = false;

    // --- Working out which area someone is in --------------------------
    //
    // Asked once, on the first visit only, to preselect the nearest area in
    // the preferences modal. Three rules keep that from becoming a nuisance:
    // the answer is never asked for twice (a refusal is remembered as
    // firmly as a permission), nothing waits on it for more than a few
    // seconds, and every failure path just leaves "All areas" selected.
    // Nothing here is sent anywhere — the coordinates are compared against
    // the venues already on the page and then discarded.
    const GEO_ASKED_KEY = "activityDashboardLocationAsked";
    const GEO_TIMEOUT_MS = 7000;

    function locationAlreadyAsked() {
      try {
        return localStorage.getItem(GEO_ASKED_KEY) === "1";
      } catch (err) {
        // No storage means no memory of asking, and asking on every visit
        // would be worse than never asking.
        return true;
      }
    }

    function rememberLocationAsked() {
      try {
        localStorage.setItem(GEO_ASKED_KEY, "1");
      } catch (err) {
        /* best-effort */
      }
    }

    // The area of the single closest venue — not the closest area centre.
    // Centres mislead badly here: Port Moody's three venues average out to a
    // point 2.8 km west of Coquitlam's centre, so standing at Port Moody
    // city hall, "nearest centre" answers Coquitlam. Nearest venue answers
    // the question people actually mean — where could I go from here.
    function nearestArea(position) {
      const here = [position.coords.latitude, position.coords.longitude];
      let best = null;
      let bestDistance = Infinity;
      for (const ev of allEvents) {
        if (!ev.area || typeof ev.lat !== "number" || typeof ev.lng !== "number") continue;
        const distance = distanceMetres(here, [ev.lat, ev.lng]);
        if (distance < bestDistance) {
          bestDistance = distance;
          best = ev.area;
        }
      }
      return best;
    }

    // Resolves to an area name, or to null for every "we don't know" case:
    // no support, already asked, refused, timed out, or too far away for an
    // area to be a sensible guess.
    function detectNearestArea() {
      if (locationAlreadyAsked() || !navigator.geolocation) return Promise.resolve(null);
      rememberLocationAsked();
      return new Promise((resolve) => {
        let settled = false;
        const finish = (value) => {
          if (!settled) {
            settled = true;
            resolve(value);
          }
        };
        // navigator.geolocation can hang indefinitely on some browsers even
        // with its own timeout set, and the modal must not wait on it.
        setTimeout(() => finish(null), GEO_TIMEOUT_MS);
        navigator.geolocation.getCurrentPosition(
          (position) => finish(nearestArea(position)),
          () => finish(null),
          { timeout: GEO_TIMEOUT_MS, maximumAge: 600000, enableHighAccuracy: false }
        );
      });
    }

    // suggestedArea, when given, preselects an area the filters are not set
    // to yet — the first-visit location guess. It is only ever a suggestion:
    // it reaches the filters if this dialog is saved, and is forgotten if it
    // is skipped or dismissed.
    function openPreferencesModal(suggestedArea) {
      setRadioGroupValue("pref-activity", activeActivity);
      setRadioGroupValue(
        "pref-area",
        suggestedArea || (areaFilterEl ? areaFilterEl.value : "")
      );
      setRadioGroupValue("pref-location", locationFilterEl.value);
      prefOpenOnlyEl.checked = openOnlyFilterEl.checked;
      if (prefEmailAlertsEl) prefEmailAlertsEl.checked = emailAlertsEnabled;
      preferencesModal.hidden = false;
    }

    function urlBase64ToUint8Array(base64String) {
      const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
      const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
      const raw = atob(base64);
      return Uint8Array.from([...raw].map((c) => c.charCodeAt(0)));
    }

    async function showWatchStatus() {
      const el = document.getElementById("watch-status");
      if (!el) return;
      try {
        const resp = await fetch("/api/watch-status");
        const s = await resp.json();

        if (!s.configured) {
          el.textContent = "Alert watcher: not configured.";
          return;
        }
        if (!s.last_run) {
          el.textContent =
            "Alert watcher: never run yet — the scheduled job isn't calling it.";
          el.classList.add("watch-status-bad");
          return;
        }

        const mins = Math.round(s.seconds_ago / 60);
        const ago =
          mins < 1 ? "less than a minute ago" : mins === 1 ? "1 minute ago" : `${mins} minutes ago`;
        el.textContent = s.healthy
          ? `Alert watcher: last checked ${ago} (${s.checked} sessions tracked).`
          : `Alert watcher: last checked ${ago} — that's overdue, the scheduled job may have stopped.`;
        el.classList.toggle("watch-status-bad", !s.healthy);
      } catch (err) {
        console.error("Could not load watch status:", err);
        el.textContent = "";
      }
    }

    function setUpAlertsButton() {
      const alertsBtn = document.getElementById("alerts-btn");
      if (!alertsBtn) return;

      const supported =
        "serviceWorker" in navigator && "PushManager" in window && "Notification" in window;
      if (!supported) {
        alertsBtn.textContent = "🔔 Alerts unavailable";
        alertsBtn.disabled = true;
        alertsBtn.title =
          "This browser can't receive push notifications here. On iPhone, add " +
          "this site to your Home Screen first, then open it from that icon.";
        return;
      }

      const vapidKey = alertsBtn.dataset.vapidKey;

      // navigator.serviceWorker.ready never settles if the worker fails to
      // activate, so cap the wait — otherwise this hangs forever and takes
      // the button's behaviour down with it.
      function swReady(timeoutMs = 8000) {
        return Promise.race([
          navigator.serviceWorker.ready,
          new Promise((_, reject) =>
            setTimeout(() => reject(new Error("service worker not ready")), timeoutMs)
          ),
        ]);
      }

      async function currentSubscription() {
        const reg = await swReady();
        return reg.pushManager.getSubscription();
      }

      // Tracked so the click handler knows synchronously whether it is turning
      // alerts on or off — deciding that with an await would burn the click's
      // user activation before we can request notification permission.
      let isSubscribed = false;

      function paint(subscribed) {
        isSubscribed = subscribed;
        alertsBtn.textContent = subscribed ? "🔔 Alerts on" : "🔔 Alerts off";
        alertsBtn.classList.toggle("alerts-on", subscribed);
        alertsBtn.title = subscribed
          ? "You'll be notified when a spot opens in a starred activity. Click to turn off."
          : "Get notified when a spot opens in one of your starred activities.";
      }

      function withTimeout(promise, ms, label) {
        return Promise.race([
          promise,
          new Promise((_, reject) => setTimeout(() => reject(new Error(label)), ms)),
        ]);
      }

      // Attach the click handler BEFORE any await. Awaiting first would mean a
      // hung service worker prevents this listener from ever being attached,
      // leaving a button that looks fine and does nothing when clicked.
      alertsBtn.addEventListener("click", async () => {
        // Turning alerts OFF needs no permission, so handle it separately.
        if (isSubscribed) {
          alertsBtn.disabled = true;
          try {
            const existing = await currentSubscription();
            if (existing) {
              await fetch("/api/push/unsubscribe", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ endpoint: existing.endpoint }),
              });
              await existing.unsubscribe();
            }
            paint(false);
          } catch (err) {
            console.error("Failed to turn alerts off:", err);
            alertsBtn.textContent = "🔔 Alerts failed";
            alertsBtn.title = "Couldn't turn alerts off: " + (err && err.message);
          } finally {
            alertsBtn.disabled = false;
          }
          return;
        }

        // Turning alerts ON: ask for permission FIRST, synchronously within
        // the click. Browsers only honour a permission request while the
        // click's transient user activation is still valid — awaiting
        // anything first (e.g. the service worker) burns it, and the prompt
        // then silently never appears.
        if (Notification.permission === "denied") {
          alertsBtn.title =
            "Notifications are blocked for this site. Click the icon at the left " +
            "of the address bar, set Notifications to Allow, then reload.";
          alertsBtn.textContent = "🔔 Alerts blocked";
          return;
        }

        let permissionPromise = null;
        if (Notification.permission !== "granted") {
          permissionPromise = Notification.requestPermission();
        }

        alertsBtn.disabled = true;
        try {
          if (permissionPromise) {
            const permission = await withTimeout(
              permissionPromise,
              120000,
              "no response to the notification prompt"
            );
            if (permission !== "granted") {
              alertsBtn.textContent = "🔔 Alerts blocked";
              alertsBtn.title =
                "Notification permission wasn't granted. Allow notifications for " +
                "this site in your browser, then click again.";
              return;
            }
          }

          if (!vapidKey) throw new Error("missing VAPID public key");

          const reg = await swReady();
          const sub = await reg.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: urlBase64ToUint8Array(vapidKey),
          });

          const resp = await fetch("/api/push/subscribe", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(sub.toJSON()),
          });
          if (!resp.ok) throw new Error("server rejected subscription");
          paint(true);
        } catch (err) {
          console.error("Failed to toggle alerts:", err);
          // Surface the failure on the button itself — a silent console error
          // just looks like a dead button to the person clicking it.
          alertsBtn.textContent = "🔔 Alerts failed";
          alertsBtn.title = "Couldn't enable alerts: " + (err && err.message) +
            ". Try reloading the page.";
        } finally {
          alertsBtn.disabled = false;
        }
      });

      // Reflect the existing subscription state. Runs after the listener is
      // attached, so a failure here can never disable the button.
      currentSubscription()
        .then((sub) => paint(!!sub))
        .catch((err) => {
          console.error("Could not read push subscription:", err);
          paint(false);
        });
    }

    // Wrapped, not passed directly: a listener is handed the click event,
    // which would arrive as openPreferencesModal's suggestedArea and reset
    // the area radio to "All areas" every time the dialog was reopened.
    preferencesBtn.addEventListener("click", () => openPreferencesModal());

    prefSkipBtn.addEventListener("click", () => {
      try {
        // Account-side "skip" isn't persisted server-side (no extra schema
        // for it) — logged-in users who skip just get asked again next
        // visit until they save. Anonymous users get the localStorage flag
        // so they aren't nagged every time.
        if (!loggedIn) writeStoredPreferences({ skipped: true });
      } finally {
        closePreferencesModal();
      }
    });

    prefSaveBtn.addEventListener("click", async () => {
      try {
        const prefs = {
          activity: getRadioGroupValue("pref-activity"),
          area: getRadioGroupValue("pref-area"),
          location: getRadioGroupValue("pref-location"),
          openOnly: prefOpenOnlyEl.checked,
        };
        if (prefEmailAlertsEl) {
          emailAlertsEnabled = prefEmailAlertsEl.checked;
          prefs.emailAlerts = emailAlertsEnabled;
        }
        if (loggedIn) {
          await saveAccountPreferences(prefs);
        } else {
          writeStoredPreferences(prefs);
        }
        applyPreferences(prefs);
        render();
      } catch (err) {
        console.error("Failed to save preferences:", err);
      } finally {
        closePreferencesModal();
      }
    });

    setUpAlertsButton();
    showWatchStatus();

    lastUpdatedEl.textContent = formatFetchedAt(Number(lastUpdatedEl.dataset.fetchedAt));

    (async () => {
      try {
        const storedPrefs = loggedIn
          ? await fetchAccountPreferences()
          : readStoredPreferences();
        if (storedPrefs && typeof storedPrefs.emailAlerts === "boolean") {
          emailAlertsEnabled = storedPrefs.emailAlerts;
        }
        // A stored record holding only the email-alert flag means the filter
        // preferences were never set, so still prompt for those.
        const hasFilterPrefs =
          storedPrefs &&
          ("activity" in storedPrefs ||
            "location" in storedPrefs ||
            "area" in storedPrefs);
        if (hasFilterPrefs && !storedPrefs.skipped) {
          applyPreferences(storedPrefs);
        } else if (!storedPrefs || !hasFilterPrefs) {
          if (!(storedPrefs && storedPrefs.skipped)) {
            // First visit. Offer the nearest area as the starting point,
            // but open the dialog either way — a refused or slow location
            // prompt must not hold the page hostage.
            openPreferencesModal(await detectNearestArea());
          }
        }
      } catch (err) {
        console.error("Failed to load preferences:", err);
      } finally {
        render();
      }
    })();
  }
})();
