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
      const n = countSessions(ev);
      const scope = n > 1 ? `all ${n} “${ev.event_name}” sessions` : `“${ev.event_name}”`;
      const where = ev.location ? ` at ${ev.location}` : "";
      return ev.is_favorited
        ? `Stop watching ${scope}${where}`
        : `Watch ${scope}${where} — you'll be alerted whenever a spot opens`;
    }

    function buildFavoriteButton(ev) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "favorite-btn" + (ev.is_favorited ? " favorited" : "");
      btn.textContent = ev.is_favorited ? "★" : "☆";
      btn.title = favoriteTitle(ev);
      btn.addEventListener("click", async () => {
        btn.disabled = true;
        try {
          const resp = await fetch("/api/favorites", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              source_name: ev.source_name,
              event_name: ev.event_name,
              location: ev.location || "",
              course_id: ev.course_id,
            }),
          });
          const data = await resp.json();
          const nowFavorited = !!data.favorited;
          // Apply to every session of this activity, so all their stars
          // update together rather than just the one clicked.
          allEvents.forEach((e) => {
            if (sameActivity(e, ev)) e.is_favorited = nowFavorited;
          });
          render();
        } catch (err) {
          console.error("Failed to toggle favorite:", err);
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

      card._open = badge.open;
      return card;
    }

    function render() {
      const keyword = keywordFilterEl.value.trim().toLowerCase();
      const location = locationFilterEl.value;
      const openOnly = openOnlyFilterEl.checked;

      const favoritesOnly = favoritesOnlyFilterEl ? favoritesOnlyFilterEl.checked : false;

      const upcoming = allEvents.filter((ev) => !alreadyFinished(ev));

      const filtered = upcoming.filter((ev) => {
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
      if (!renderedAny) {
        const anyFilterActive =
          activeActivity !== "all" || !!location || !!keyword || openOnly || favoritesOnly;
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

    function clearAllFilters() {
      selectActivityChip("all");
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
      locationFilterEl.value = prefs.location || "";
      openOnlyFilterEl.checked = !!prefs.openOnly;
    }

    // Email alerts are an account setting rather than a view filter, so it is
    // kept out of applyPreferences (which only drives the visible filters).
    let emailAlertsEnabled = false;

    function openPreferencesModal() {
      setRadioGroupValue("pref-activity", activeActivity);
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
          storedPrefs && ("activity" in storedPrefs || "location" in storedPrefs);
        if (hasFilterPrefs && !storedPrefs.skipped) {
          applyPreferences(storedPrefs);
        } else if (!storedPrefs || !hasFilterPrefs) {
          if (!(storedPrefs && storedPrefs.skipped)) openPreferencesModal();
        }
      } catch (err) {
        console.error("Failed to load preferences:", err);
      } finally {
        render();
      }
    })();
  }
})();
