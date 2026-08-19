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
    const locationFilterEl = document.getElementById("location-filter");
    const keywordFilterEl = document.getElementById("keyword-filter");
    const openOnlyFilterEl = document.getElementById("open-only-filter");
    const favoritesOnlyFilterEl = document.getElementById("favorites-only-filter");

    const preferencesBtn = document.getElementById("preferences-btn");
    const prefOpenOnlyEl = document.getElementById("pref-open-only");
    const prefSaveBtn = document.getElementById("pref-save-btn");
    const prefSkipBtn = document.getElementById("pref-skip-btn");
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
      return `${dayOfWeek}, ${monthDay}`;
    }

    function buildFavoriteButton(ev) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "favorite-btn" + (ev.is_favorited ? " favorited" : "");
      btn.textContent = ev.is_favorited ? "★" : "☆";
      btn.title = ev.is_favorited ? "Remove from favorites" : "Add to favorites";
      btn.addEventListener("click", async () => {
        btn.disabled = true;
        try {
          const resp = await fetch("/api/favorites", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              source_name: ev.source_name,
              course_id: ev.course_id,
              event_name: ev.event_name,
            }),
          });
          const data = await resp.json();
          ev.is_favorited = !!data.favorited;
          btn.textContent = ev.is_favorited ? "★" : "☆";
          btn.title = ev.is_favorited ? "Remove from favorites" : "Add to favorites";
          btn.classList.toggle("favorited", ev.is_favorited);
          if (favoritesOnlyFilterEl && favoritesOnlyFilterEl.checked) render();
        } catch (err) {
          console.error("Failed to toggle favorite:", err);
        } finally {
          btn.disabled = false;
        }
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
        const registerEl = document.createElement("a");
        registerEl.className = "register-btn";
        registerEl.textContent = badge.open ? "Register / Pay ↗" : "View details ↗";
        registerEl.href = ev.detail_url;
        registerEl.target = "_blank";
        registerEl.rel = "noopener noreferrer";
        registerEl.title =
          `Opens this session's official ${ev.source_name} page in a new tab, ` +
          "where registration and payment are handled by the city.";
        statusCol.appendChild(registerEl);
      }

      card.appendChild(statusCol);

      card._open = badge.open;
      return card;
    }

    function render() {
      const keyword = keywordFilterEl.value.trim().toLowerCase();
      const location = locationFilterEl.value;
      const openOnly = openOnlyFilterEl.checked;

      const favoritesOnly = favoritesOnlyFilterEl ? favoritesOnlyFilterEl.checked : false;

      const filtered = allEvents.filter((ev) => {
        if (activeActivity !== "all" && ev.activity_type !== activeActivity) return false;
        if (location && ev.location !== location) return false;
        if (keyword && !ev.event_name.toLowerCase().includes(keyword)) return false;
        if (favoritesOnly && !ev.is_favorited) return false;
        return true;
      });

      dayGroupsEl.innerHTML = "";

      const groups = new Map();
      for (const ev of filtered) {
        const key = ev.date || "";
        if (!groups.has(key)) groups.set(key, []);
        groups.get(key).push(ev);
      }

      const sortedKeys = Array.from(groups.keys()).sort();

      let renderedAny = false;
      for (const key of sortedKeys) {
        const events = groups.get(key);
        const cards = events.map(buildCard).filter((card) => !openOnly || card._open);
        if (cards.length === 0) continue;

        renderedAny = true;
        const section = document.createElement("section");
        section.className = "day-group";

        const heading = document.createElement("h2");
        heading.textContent = formatDateHeading(key, events[0].day_of_week);
        section.appendChild(heading);

        const list = document.createElement("div");
        list.className = "event-list";
        cards.forEach((c) => list.appendChild(c));
        section.appendChild(list);

        dayGroupsEl.appendChild(section);
      }

      emptyStateEl.hidden = renderedAny;
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

    locationFilterEl.addEventListener("change", render);
    keywordFilterEl.addEventListener("input", render);
    openOnlyFilterEl.addEventListener("change", render);
    if (favoritesOnlyFilterEl) favoritesOnlyFilterEl.addEventListener("change", render);

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
      locationFilterEl.value = prefs.location || "";
      openOnlyFilterEl.checked = !!prefs.openOnly;
    }

    function openPreferencesModal() {
      setRadioGroupValue("pref-activity", activeActivity);
      setRadioGroupValue("pref-location", locationFilterEl.value);
      prefOpenOnlyEl.checked = openOnlyFilterEl.checked;
      preferencesModal.hidden = false;
    }

    preferencesBtn.addEventListener("click", openPreferencesModal);

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
          location: getRadioGroupValue("pref-location"),
          openOnly: prefOpenOnlyEl.checked,
        };
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

    lastUpdatedEl.textContent = formatFetchedAt(Number(lastUpdatedEl.dataset.fetchedAt));

    (async () => {
      try {
        const storedPrefs = loggedIn
          ? await fetchAccountPreferences()
          : readStoredPreferences();
        if (storedPrefs && !storedPrefs.skipped) {
          applyPreferences(storedPrefs);
        } else if (!storedPrefs) {
          openPreferencesModal();
        }
      } catch (err) {
        console.error("Failed to load preferences:", err);
      } finally {
        render();
      }
    })();
  }
})();
