(function () {
  "use strict";

  const dayGroupsEl = document.getElementById("day-groups");
  const emptyStateEl = document.getElementById("empty-state");
  const lastUpdatedEl = document.getElementById("last-updated");
  const refreshBtn = document.getElementById("refresh-btn");
  const activityFiltersEl = document.getElementById("activity-filters");
  const locationFilterEl = document.getElementById("location-filter");
  const keywordFilterEl = document.getElementById("keyword-filter");
  const openOnlyFilterEl = document.getElementById("open-only-filter");

  let allEvents = JSON.parse(document.getElementById("events-data").textContent);
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
    const badge = badgeInfo(ev);
    const badgeEl = document.createElement(ev.detail_url ? "a" : "span");
    badgeEl.className = "badge " + badge.cls;
    badgeEl.textContent = badge.text;
    if (ev.detail_url) {
      badgeEl.href = ev.detail_url;
      badgeEl.target = "_blank";
      badgeEl.rel = "noopener noreferrer";
      badgeEl.title = "Opens the official City of Coquitlam registration page in a new tab";
    }
    statusCol.appendChild(badgeEl);
    card.appendChild(statusCol);

    card._open = badge.open;
    return card;
  }

  function render() {
    const keyword = keywordFilterEl.value.trim().toLowerCase();
    const location = locationFilterEl.value;
    const openOnly = openOnlyFilterEl.checked;

    const filtered = allEvents.filter((ev) => {
      if (activeActivity !== "all" && ev.activity_type !== activeActivity) return false;
      if (location && ev.location !== location) return false;
      if (keyword && !ev.event_name.toLowerCase().includes(keyword)) return false;
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

  activityFiltersEl.addEventListener("click", (e) => {
    const btn = e.target.closest("button[data-activity]");
    if (!btn) return;
    activeActivity = btn.dataset.activity;
    activityFiltersEl.querySelectorAll(".chip").forEach((c) => c.classList.remove("active"));
    btn.classList.add("active");
    render();
  });

  locationFilterEl.addEventListener("change", render);
  keywordFilterEl.addEventListener("input", render);
  openOnlyFilterEl.addEventListener("change", render);

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

  lastUpdatedEl.textContent = formatFetchedAt(Number(lastUpdatedEl.dataset.fetchedAt));
  render();
})();
