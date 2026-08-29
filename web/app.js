// Piyon Log - panel istemcisi.

const POLL_MS = 2500;
const QUERY_DEBOUNCE_MS = 350;
const BADGE_COLORS = [
  "#34d399", "#60a5fa", "#f59e0b", "#f472b6",
  "#a78bfa", "#2dd4bf", "#facc15", "#fb923c",
];

const AY_ADLARI = [
  "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
  "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık",
];

const PAGE_TITLES = { home: "Bugün", analytics: "Analitik", projects: "Projeler", settings: "Ayarlar" };
const FOCUS_RING_CIRCUMFERENCE = 2 * Math.PI * 40;

function todayStr() {
  const d = new Date();
  const tz = d.getTimezoneOffset() * 60000;
  return new Date(d - tz).toISOString().slice(0, 10);
}

const state = {
  currentDate: todayStr(),
  followingToday: true,
  page: "home",
  querying: false,
  projects: [],
  expandedBlocks: new Set(),
  lastRenderKey: "",
};

const el = {
  pageTitle: document.getElementById("page-title"),
  status: document.getElementById("status"),
  statusText: document.getElementById("status-text"),
  refreshBtn: document.getElementById("refresh-btn"),
  themeToggle: document.getElementById("theme-toggle"),
  searchInput: document.getElementById("search-input"),
  searchClear: document.getElementById("search-clear"),
  dateNav: document.getElementById("date-nav"),
  datePrev: document.getElementById("date-prev"),
  dateNext: document.getElementById("date-next"),
  logDate: document.getElementById("log-date"),
  reportActions: document.querySelector(".report-actions"),
  dlMd: document.getElementById("dl-md"),
  dlPdf: document.getElementById("dl-pdf"),

  statTotal: document.getElementById("stat-total"),
  statFocusTime: document.getElementById("stat-focus-time"),
  statDeepWork: document.getElementById("stat-deep-work"),
  statSwitches: document.getElementById("stat-switches"),

  focusRingFill: document.getElementById("focus-ring-fill"),
  focusRingValue: document.getElementById("focus-ring-value"),

  dayRibbon: document.getElementById("day-ribbon"),
  ribbonLegend: document.getElementById("ribbon-legend"),
  ribbonTicks: document.getElementById("ribbon-ticks"),

  log: document.getElementById("log"),
  logEmpty: document.getElementById("log-empty"),
  appChart: document.getElementById("app-chart"),
  projectDonut: document.getElementById("project-donut"),
  projectDonutLegend: document.getElementById("project-donut-legend"),
  nudgeCard: document.getElementById("nudge-card"),
  nudgeAmount: document.getElementById("nudge-amount"),
  nudgeBtn: document.getElementById("nudge-btn"),

  heatmap: document.getElementById("heatmap"),
  appsLog: document.getElementById("apps-log"),
  appsLogEmpty: document.getElementById("apps-log-empty"),

  projectManager: document.getElementById("project-manager"),
  pmKeyword: document.getElementById("pm-keyword"),
  pmProject: document.getElementById("pm-project"),
  pmProjectList: document.getElementById("pm-project-list"),
  pmAddBtn: document.getElementById("pm-add-btn"),
  pmList: document.getElementById("pm-list"),
  projectsLog: document.getElementById("projects-log"),
  projectsLogEmpty: document.getElementById("projects-log-empty"),

  queryLog: document.getElementById("query-log"),
  queryLogEmpty: document.getElementById("query-log-empty"),
  queryTitle: document.getElementById("query-title"),
};

function hashColor(name) {
  let h = 0;
  for (let i = 0; i < name.length; i++) {
    h = (h * 31 + name.charCodeAt(i)) >>> 0;
  }
  return BADGE_COLORS[h % BADGE_COLORS.length];
}

function formatSaat(iso) {
  const d = new Date(iso);
  if (isNaN(d)) return iso;
  return d.toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" });
}

const TITLE_APP_SUFFIX_RE = / - (Microsoft​? ?Edge|Google Chrome|Mozilla Firefox)$/i;
const TITLE_VSCODE_SUFFIX_RE = / - Visual Studio Code( - (Read-only|Modified))?$/i;
const TITLE_TAB_NOISE_RE = / ve diğer \d+ sayfa/i;
const TITLE_PROFILE_SUFFIX_RE = / - (Kişisel|Work|İş)$/i;

/**
 * Ham pencere başlığını "site/uygulama" (primary) ve "sayfa/dosya" (secondary)
 * olarak ayrıştırır. Tanınmayan biçimler olduğu gibi primary'e düşer.
 */
function cleanTitle(raw, app) {
  let s = (raw || "").trim();
  if (!s) return { primary: "", secondary: "" };

  s = s.replace(TITLE_VSCODE_SUFFIX_RE, "");
  s = s.replace(TITLE_APP_SUFFIX_RE, "");
  s = s.replace(TITLE_TAB_NOISE_RE, "");
  s = s.replace(TITLE_PROFILE_SUFFIX_RE, "");
  s = s.trim();

  const isCode = (app || "").toLowerCase() === "code.exe";
  if (isCode) {
    const dashIdx = s.lastIndexOf(" - ");
    if (dashIdx > -1) {
      return { primary: s.slice(dashIdx + 3).trim(), secondary: s.slice(0, dashIdx).trim() };
    }
    return { primary: s, secondary: "" };
  }

  const pipeIdx = s.lastIndexOf("|");
  if (pipeIdx > -1) {
    return { primary: s.slice(pipeIdx + 1).trim(), secondary: s.slice(0, pipeIdx).trim() };
  }
  return { primary: s, secondary: "" };
}

function formatSure(saniye) {
  saniye = Math.max(0, Math.floor(saniye || 0));
  const saat = Math.floor(saniye / 3600);
  const dakika = Math.floor((saniye % 3600) / 60);
  if (saat && dakika) return `${saat}sa ${dakika}dk`;
  if (saat) return `${saat}sa`;
  if (dakika) return `${dakika}dk`;
  return "<1dk";
}

function formatGun(dateStr) {
  const [y, m, d] = dateStr.split("-").map(Number);
  if (dateStr === todayStr()) return "Bugün";
  return `${d} ${AY_ADLARI[m - 1]}`;
}

function maxKey(obj) {
  const entries = Object.entries(obj || {});
  if (entries.length === 0) return null;
  return entries.reduce((a, b) => (b[1] > a[1] ? b : a));
}

function clearContainer(container) {
  container.querySelectorAll(".entry-card").forEach((c) => c.remove());
}

// --- Bugün sayfası ---

function renderStats(data) {
  el.statTotal.textContent = formatSure(data.toplam_sure);
  el.statFocusTime.textContent = formatSure(data.focus_seconds);
  el.statDeepWork.textContent = formatSure(data.deep_work_seconds);
  el.statSwitches.textContent = data.sessions.length;
  el.logDate.textContent = formatGun(data.date);
  el.dateNext.disabled = data.date >= todayStr();
}

function renderFocusRing(data) {
  const hasData = data.sessions.length > 0;
  const ratio = hasData ? data.focus_ratio : 0;
  const offset = FOCUS_RING_CIRCUMFERENCE - (ratio / 100) * FOCUS_RING_CIRCUMFERENCE;
  el.focusRingFill.style.strokeDashoffset = String(offset);
  el.focusRingValue.textContent = hasData ? `%${ratio}` : "—";
}

const UNASSIGNED_COLOR = "#5f666e";

function renderDayRibbon(data) {
  el.dayRibbon.innerHTML = "";
  const legendSeen = new Map();

  const toMin = (iso) => {
    const d = new Date(iso);
    return isNaN(d) ? null : d.getHours() * 60 + d.getMinutes();
  };

  // Boş saatleri kırpmak için gerçek aktivite aralığını bul (ör. gün 00:00
  // yerine ilk kayıttan 30dk önce başlasın), en az 4 saatlik bir pencere kalsın.
  let rangeStart = 1440;
  let rangeEnd = 0;
  for (const s of data.sessions) {
    const a = toMin(s.start_ts);
    const b = toMin(s.end_ts);
    if (a === null || b === null) continue;
    rangeStart = Math.min(rangeStart, a);
    rangeEnd = Math.max(rangeEnd, b);
  }
  if (data.date === todayStr()) {
    const now = new Date();
    rangeEnd = Math.max(rangeEnd, now.getHours() * 60 + now.getMinutes());
  }
  if (rangeStart > rangeEnd) {
    rangeStart = 0;
    rangeEnd = 1440;
  } else {
    rangeStart = Math.max(0, rangeStart - 30);
    rangeEnd = Math.min(1440, rangeEnd + 30);
    if (rangeEnd - rangeStart < 240) {
      const mid = (rangeStart + rangeEnd) / 2;
      rangeStart = Math.max(0, mid - 120);
      rangeEnd = Math.min(1440, mid + 120);
    }
  }
  const span = rangeEnd - rangeStart;

  for (const s of data.sessions) {
    const startMin = toMin(s.start_ts);
    const endMinRaw = toMin(s.end_ts);
    if (startMin === null || endMinRaw === null) continue;
    const endMin = Math.max(startMin + 1, endMinRaw);
    const key = s.project;
    const color = key ? hashColor(key) : UNASSIGNED_COLOR;

    const seg = document.createElement("div");
    seg.className = "ribbon-segment";
    seg.style.left = `${((startMin - rangeStart) / span) * 100}%`;
    seg.style.width = `${((endMin - startMin) / span) * 100}%`;
    seg.style.background = color;
    seg.title = `${key || "Kategorisiz"} · ${formatSaat(s.start_ts)}–${formatSaat(s.end_ts)}`;
    el.dayRibbon.appendChild(seg);

    if (!legendSeen.has(key || "Kategorisiz")) legendSeen.set(key || "Kategorisiz", color);
  }

  if (data.date === todayStr()) {
    const now = new Date();
    const nowMin = now.getHours() * 60 + now.getMinutes();
    if (nowMin >= rangeStart && nowMin <= rangeEnd) {
      const line = document.createElement("div");
      line.className = "ribbon-now";
      line.style.left = `${((nowMin - rangeStart) / span) * 100}%`;
      line.title = "şimdi";
      el.dayRibbon.appendChild(line);
    }
  }

  el.ribbonTicks.innerHTML = "";
  const tickCount = 5;
  for (let i = 0; i < tickCount; i++) {
    const min = Math.round(rangeStart + (span * i) / (tickCount - 1));
    const tick = document.createElement("span");
    tick.textContent = `${String(Math.floor(min / 60)).padStart(2, "0")}:${String(min % 60).padStart(2, "0")}`;
    el.ribbonTicks.appendChild(tick);
  }

  el.ribbonLegend.innerHTML = "";
  let i = 0;
  for (const [name, color] of legendSeen) {
    if (i++ >= 4) break;
    const item = document.createElement("div");
    item.className = "ribbon-legend-item";
    const dot = document.createElement("span");
    dot.className = "ribbon-legend-dot";
    dot.style.background = color;
    item.append(dot, document.createTextNode(name));
    el.ribbonLegend.appendChild(item);
  }
}

function renderChartInto(container, totals, limit) {
  container.innerHTML = "";
  let entries = Object.entries(totals || {}).sort((a, b) => b[1] - a[1]);
  if (limit) entries = entries.slice(0, limit);

  if (entries.length === 0) {
    const empty = document.createElement("div");
    empty.className = "chart-empty";
    empty.textContent = "Veri yok.";
    container.appendChild(empty);
    return;
  }

  const max = entries[0][1];
  for (const [name, seconds] of entries) {
    const row = document.createElement("div");
    row.className = "chart-row";

    const label = document.createElement("span");
    label.className = "chart-label";
    label.textContent = name;

    const track = document.createElement("div");
    track.className = "chart-bar-track";
    const fill = document.createElement("div");
    fill.className = "chart-bar-fill";
    fill.style.background = hashColor(name);
    fill.style.width = `${Math.max(3, (seconds / max) * 100)}%`;
    track.appendChild(fill);

    const value = document.createElement("span");
    value.className = "chart-value";
    value.textContent = formatSure(seconds);

    row.append(label, track, value);
    container.appendChild(row);
  }
}

function renderProjectDonut(data) {
  const entries = Object.entries(data.project_totals || {}).sort((a, b) => b[1] - a[1]);
  const total = entries.reduce((sum, [, v]) => sum + v, 0);

  el.projectDonutLegend.innerHTML = "";

  if (total === 0) {
    el.projectDonut.style.background = "var(--bg)";
    const empty = document.createElement("div");
    empty.className = "donut-empty";
    empty.textContent = "Bu gün için veri yok.";
    el.projectDonutLegend.appendChild(empty);
    return;
  }

  let acc = 0;
  const stops = [];
  for (const [name, seconds] of entries) {
    const startPct = (acc / total) * 100;
    acc += seconds;
    const endPct = (acc / total) * 100;
    const color = hashColor(name);
    stops.push(`${color} ${startPct}% ${endPct}%`);

    const row = document.createElement("div");
    row.className = "donut-legend-row";
    const dot = document.createElement("span");
    dot.className = "donut-legend-dot";
    dot.style.background = color;
    const nameEl = document.createElement("span");
    nameEl.className = "donut-legend-name";
    nameEl.textContent = name;
    const pctEl = document.createElement("span");
    pctEl.className = "donut-legend-pct";
    pctEl.textContent = `${Math.round((seconds / total) * 100)}%`;
    row.append(dot, nameEl, pctEl);
    el.projectDonutLegend.appendChild(row);
  }
  el.projectDonut.style.background = `conic-gradient(${stops.join(", ")})`;
}

function renderUnassignedNudge(data) {
  const total = data.toplam_sure || 0;
  const unassigned = (data.project_totals || {})["Diğer"] || 0;
  if (total < 300 || unassigned / total < 0.15) {
    el.nudgeCard.hidden = true;
    return;
  }
  el.nudgeCard.hidden = false;
  el.nudgeAmount.textContent = formatSure(unassigned);
}

el.nudgeBtn.addEventListener("click", () => {
  document.querySelector('.sidebar-item[data-page="projects"]').click();
});

function makeProjectControl(displayObj, color, targetSessions) {
  const wrap = document.createElement("span");
  const targets = targetSessions || [displayObj];

  function renderView() {
    wrap.innerHTML = "";
    const badge = document.createElement("span");
    badge.className = "entry-project";
    badge.title = "Projeyi değiştirmek için tıkla";
    if (displayObj.project) {
      badge.textContent = displayObj.project;
      badge.style.color = color;
    } else {
      badge.textContent = "+ proje";
      badge.style.color = "var(--text-faint)";
      badge.dataset.empty = "1";
    }
    badge.addEventListener("click", renderEdit);
    wrap.appendChild(badge);
  }

  function renderEdit() {
    wrap.innerHTML = "";
    const select = document.createElement("select");
    select.className = "entry-project-select";

    const noneOpt = document.createElement("option");
    noneOpt.value = "";
    noneOpt.textContent = "Yok";
    select.appendChild(noneOpt);

    for (const p of state.projects) {
      const opt = document.createElement("option");
      opt.value = p;
      opt.textContent = p;
      if (p === displayObj.project) opt.selected = true;
      select.appendChild(opt);
    }

    select.addEventListener("change", async () => {
      const newProject = select.value || null;
      displayObj.project = newProject;
      for (const t of targets) t.project = newProject;
      renderView();
      try {
        await Promise.all(
          targets.map((t) =>
            fetch("/api/session/update", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ id: t.id, project: newProject }),
            })
          )
        );
      } catch (e) {
        // sessizce yut
      }
    });
    select.addEventListener("blur", renderView);

    wrap.appendChild(select);
    select.focus();
  }

  renderView();
  return wrap;
}

function makeEntryCard(session, opts = {}) {
  const card = document.createElement("div");
  card.className = "entry-card";

  const app = session.app || "bilinmeyen";
  const color = hashColor(app);
  card.style.borderLeftColor = color;

  const head = document.createElement("div");
  head.className = "entry-head";

  const time = document.createElement("span");
  time.className = "entry-time";
  time.textContent = formatSaat(session.start_ts);
  head.appendChild(time);

  if (opts.showDate) {
    const dateBadge = document.createElement("span");
    dateBadge.className = "entry-date";
    dateBadge.textContent = (session.start_ts || "").slice(0, 10);
    head.appendChild(dateBadge);
  }

  const badge = document.createElement("span");
  badge.className = "entry-badge";
  badge.textContent = app;
  badge.style.color = color;
  badge.style.background = color + "22";
  head.appendChild(badge);

  head.appendChild(makeProjectControl(session, color));

  const duration = document.createElement("span");
  duration.className = "entry-duration";
  duration.textContent = formatSure(session.duration_s);
  head.appendChild(duration);

  card.appendChild(head);

  const { primary, secondary } = cleanTitle(session.title, session.app);
  if (primary) {
    const title = document.createElement("div");
    title.className = "entry-title";
    title.textContent = primary;
    card.appendChild(title);
  }
  if (secondary) {
    const sub = document.createElement("div");
    sub.className = "entry-subtitle";
    sub.textContent = secondary;
    card.appendChild(sub);
  }

  if (session.text && session.text.trim()) {
    const text = document.createElement("div");
    text.className = "entry-text";
    text.textContent = session.text;
    card.appendChild(text);
  }

  return card;
}

// --- oturum gruplama: aynı uygulama + aynı site/dosya kökü + 2dk'dan az
// boşluk olan ardışık oturumlar tek bir "blok" kartında birleşir. ---

const GROUP_GAP_S = 120;

function groupSessions(sessions) {
  const blocks = [];
  for (const s of sessions) {
    const { primary } = cleanTitle(s.title, s.app);
    const rootKey = `${s.app}::${primary}`;
    const last = blocks[blocks.length - 1];
    if (last && last.rootKey === rootKey) {
      const gap = (new Date(s.start_ts) - new Date(last.end_ts)) / 1000;
      if (gap <= GROUP_GAP_S) {
        last.sessions.push(s);
        last.end_ts = s.end_ts;
        last.duration_s += s.duration_s;
        if (s.text && s.text.trim()) last.texts.push(s.text.trim());
        if (s.project) last.project = s.project;
        continue;
      }
    }
    blocks.push({
      rootKey,
      app: s.app,
      project: s.project,
      start_ts: s.start_ts,
      end_ts: s.end_ts,
      duration_s: s.duration_s,
      title: s.title,
      sessions: [s],
      texts: s.text && s.text.trim() ? [s.text.trim()] : [],
    });
  }
  return blocks;
}

function makeSessionBlock(block, opts = {}) {
  const card = document.createElement("div");
  card.className = "entry-card";

  const app = block.app || "bilinmeyen";
  const appColor = hashColor(app);
  const color = block.project ? hashColor(block.project) : "var(--text-faint)";
  card.style.borderLeftColor = color;

  const head = document.createElement("div");
  head.className = "entry-head";

  const timeEl = document.createElement("span");
  timeEl.className = "entry-time";
  timeEl.textContent = block.sessions.length > 1
    ? `${formatSaat(block.start_ts)}–${formatSaat(block.end_ts)}`
    : formatSaat(block.start_ts);
  head.appendChild(timeEl);

  if (opts.showDate) {
    const dateBadge = document.createElement("span");
    dateBadge.className = "entry-date";
    dateBadge.textContent = (block.start_ts || "").slice(0, 10);
    head.appendChild(dateBadge);
  }

  const badge = document.createElement("span");
  badge.className = "entry-badge";
  badge.textContent = app;
  badge.style.color = appColor;
  badge.style.background = appColor + "22";
  head.appendChild(badge);

  head.appendChild(makeProjectControl(block, color === "var(--text-faint)" ? appColor : color, block.sessions));

  if (block.sessions.length > 1) {
    const countEl = document.createElement("span");
    countEl.className = "entry-count";
    countEl.textContent = `${block.sessions.length} kayıt`;
    head.appendChild(countEl);
  }

  const duration = document.createElement("span");
  duration.className = "entry-duration";
  duration.textContent = formatSure(block.duration_s);
  head.appendChild(duration);

  card.appendChild(head);

  const { primary, secondary } = cleanTitle(block.title, block.app);
  if (primary) {
    const title = document.createElement("div");
    title.className = "entry-title";
    title.textContent = primary;
    card.appendChild(title);
  }
  if (secondary) {
    const sub = document.createElement("div");
    sub.className = "entry-subtitle";
    sub.textContent = secondary;
    card.appendChild(sub);
  }

  if (block.texts.length > 0) {
    const text = document.createElement("div");
    text.className = "entry-text";
    text.textContent = block.texts.join("\n\n");
    card.appendChild(text);
  }

  if (block.sessions.length > 1) {
    const blockKey = block.sessions[0].id;
    const expanded = state.expandedBlocks.has(blockKey);

    const toggle = document.createElement("button");
    toggle.className = "entry-expand-toggle";
    toggle.type = "button";
    toggle.textContent = expanded ? "▾ ham kayıtları gizle" : `▸ ham kayıtları göster (${block.sessions.length})`;

    const rawList = document.createElement("div");
    rawList.className = "entry-raw-list";
    rawList.hidden = !expanded;
    for (const s of block.sessions) {
      const row = document.createElement("div");
      row.className = "entry-raw-row";
      row.textContent = `${formatSaat(s.start_ts)} · ${s.title || ""}`;
      rawList.appendChild(row);
    }

    toggle.addEventListener("click", () => {
      const willExpand = rawList.hidden;
      rawList.hidden = !willExpand;
      toggle.textContent = willExpand ? "▾ ham kayıtları gizle" : `▸ ham kayıtları göster (${block.sessions.length})`;
      if (willExpand) state.expandedBlocks.add(blockKey);
      else state.expandedBlocks.delete(blockKey);
    });

    card.appendChild(toggle);
    card.appendChild(rawList);
  }

  return card;
}

function makeProjectSummaryCard(item) {
  const card = document.createElement("div");
  card.className = "entry-card";
  card.style.cursor = "pointer";
  const color = hashColor(item.project);
  card.style.borderLeftColor = color;

  const head = document.createElement("div");
  head.className = "entry-head";
  const badge = document.createElement("span");
  badge.className = "entry-badge";
  badge.textContent = item.project;
  badge.style.color = color;
  badge.style.background = color + "22";
  head.appendChild(badge);
  const duration = document.createElement("span");
  duration.className = "entry-duration";
  duration.textContent = formatSure(item.total_seconds);
  head.appendChild(duration);
  card.appendChild(head);

  const meta = document.createElement("div");
  meta.className = "entry-title";
  const aralik = item.first_date === item.last_date ? item.first_date : `${item.first_date} – ${item.last_date}`;
  meta.textContent = `${item.session_count} oturum · ${aralik}`;
  card.appendChild(meta);

  card.addEventListener("click", () => {
    runQuery({ project: item.project }, `${item.project} — tüm kayıtlar`);
  });
  return card;
}

function makeAppSummaryCard(item) {
  const card = document.createElement("div");
  card.className = "entry-card";
  card.style.cursor = "pointer";
  const color = hashColor(item.app);
  card.style.borderLeftColor = color;

  const head = document.createElement("div");
  head.className = "entry-head";
  const badge = document.createElement("span");
  badge.className = "entry-badge";
  badge.textContent = item.app;
  badge.style.color = color;
  badge.style.background = color + "22";
  head.appendChild(badge);
  const duration = document.createElement("span");
  duration.className = "entry-duration";
  duration.textContent = formatSure(item.total_seconds);
  head.appendChild(duration);
  card.appendChild(head);

  const meta = document.createElement("div");
  meta.className = "entry-title";
  const aralik = item.first_date === item.last_date ? item.first_date : `${item.first_date} – ${item.last_date}`;
  meta.textContent = `${item.session_count} oturum · ${aralik}`;
  card.appendChild(meta);

  card.addEventListener("click", () => {
    runQuery({ app: item.app }, `${item.app} — tüm kayıtlar`);
  });
  return card;
}

function renderBlocksInto(sessions, container, emptyEl, opts = {}) {
  clearContainer(container);
  if (sessions.length === 0) {
    emptyEl.style.display = "block";
    return;
  }
  emptyEl.style.display = "none";

  const nearBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 40;
  for (const block of groupSessions(sessions)) {
    container.appendChild(makeSessionBlock(block, opts));
  }
  if (nearBottom) container.scrollTop = container.scrollHeight;
}

function goToDate(dateStr) {
  if (dateStr > todayStr()) return;
  state.currentDate = dateStr;
  state.followingToday = dateStr === todayStr();
  state.expandedBlocks = new Set();
  state.lastRenderKey = "";
  clearContainer(el.log);
  poll();
}

function addDays(dateStr, days) {
  const [y, m, d] = dateStr.split("-").map(Number);
  const dt = new Date(Date.UTC(y, m - 1, d));
  dt.setUTCDate(dt.getUTCDate() + days);
  const yy = dt.getUTCFullYear();
  const mm = String(dt.getUTCMonth() + 1).padStart(2, "0");
  const dd = String(dt.getUTCDate()).padStart(2, "0");
  return `${yy}-${mm}-${dd}`;
}

function shiftDate(days) {
  goToDate(addDays(state.currentDate, days));
}

async function poll() {
  if (state.querying || state.page !== "home") return;
  try {
    const res = await fetch(`/api/today?date=${state.currentDate}`, { cache: "no-store" });
    if (!res.ok) throw new Error("sunucu hatası");
    const data = await res.json();

    renderStats(data);
    renderFocusRing(data);
    renderDayRibbon(data);
    renderChartInto(el.appChart, data.app_totals, 5);
    renderProjectDonut(data);
    renderUnassignedNudge(data);

    const last = data.sessions[data.sessions.length - 1];
    const renderKey = `${data.sessions.length}:${last ? last.id : ""}`;
    if (renderKey !== state.lastRenderKey) {
      state.lastRenderKey = renderKey;
      renderBlocksInto(data.sessions, el.log, el.logEmpty);
    }

    const isToday = state.currentDate === todayStr();
    el.status.classList.toggle("live", isToday);
    el.statusText.textContent = isToday ? "canlı" : "arşiv";
  } catch (err) {
    el.status.classList.remove("live");
    el.statusText.textContent = "bağlantı yok";
  }
}

// --- Analitik sayfası ---

async function loadHeatmap() {
  try {
    const res = await fetch("/api/daily-totals?days=30", { cache: "no-store" });
    const data = await res.json();
    renderHeatmap(data.days || []);
  } catch (e) {
    // sessizce geç
  }
}

function renderHeatmap(days) {
  el.heatmap.innerHTML = "";
  const max = Math.max(1, ...days.map((d) => d.total_seconds));
  for (const d of days) {
    const cell = document.createElement("div");
    cell.className = "heatmap-cell";
    if (d.total_seconds > 0) {
      const alpha = 0.15 + 0.85 * (d.total_seconds / max);
      cell.style.background = `rgba(52, 211, 153, ${alpha.toFixed(2)})`;
      cell.style.borderColor = "transparent";
    }
    cell.title = `${d.date} · ${formatSure(d.total_seconds)}`;
    el.heatmap.appendChild(cell);
  }
}

async function loadAppSummary() {
  try {
    const res = await fetch("/api/apps/summary", { cache: "no-store" });
    const data = await res.json();
    clearContainer(el.appsLog);
    if (data.apps.length === 0) {
      el.appsLogEmpty.style.display = "block";
    } else {
      el.appsLogEmpty.style.display = "none";
      for (const item of data.apps) el.appsLog.appendChild(makeAppSummaryCard(item));
    }
  } catch (e) {
    // sessizce geç
  }
}

// --- Projeler sayfası ---

async function loadProjectSummary() {
  try {
    const res = await fetch("/api/projects/summary", { cache: "no-store" });
    const data = await res.json();
    clearContainer(el.projectsLog);
    if (data.projects.length === 0) {
      el.projectsLogEmpty.style.display = "block";
    } else {
      el.projectsLogEmpty.style.display = "none";
      for (const item of data.projects) el.projectsLog.appendChild(makeProjectSummaryCard(item));
    }
  } catch (e) {
    // sessizce geç
  }
}

async function loadProjects() {
  try {
    const res = await fetch("/api/projects");
    const data = await res.json();
    state.projects = data.projects || [];
  } catch (e) {
    state.projects = [];
  }
  el.pmProjectList.innerHTML = "";
  for (const p of state.projects) {
    const opt = document.createElement("option");
    opt.value = p;
    el.pmProjectList.appendChild(opt);
  }
}

async function loadProjectKeywords() {
  try {
    const res = await fetch("/api/project-keywords", { cache: "no-store" });
    const data = await res.json();
    renderProjectKeywords(data.keywords || []);
  } catch (e) {
    // sessizce geç
  }
}

function renderProjectKeywords(keywords) {
  el.pmList.innerHTML = "";
  if (keywords.length === 0) {
    const empty = document.createElement("div");
    empty.className = "pm-empty";
    empty.textContent = "Henüz proje eşleştirme kuralı yok.";
    el.pmList.appendChild(empty);
    return;
  }
  for (const kw of keywords) {
    const row = document.createElement("div");
    row.className = "pm-row";
    const keyword = document.createElement("span");
    keyword.className = "pm-keyword";
    keyword.textContent = kw.keyword;
    const arrow = document.createElement("span");
    arrow.className = "pm-arrow";
    arrow.textContent = "→";
    const project = document.createElement("span");
    project.className = "pm-project";
    project.textContent = kw.project;
    const del = document.createElement("button");
    del.className = "pm-delete";
    del.type = "button";
    del.textContent = "✕";
    del.title = "Kuralı sil";
    del.addEventListener("click", async () => {
      row.remove();
      try {
        await fetch("/api/project-keywords/delete", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ id: kw.id }),
        });
        loadProjects();
      } catch (e) {
        // sessizce yut
      }
    });
    row.append(keyword, arrow, project, del);
    el.pmList.appendChild(row);
  }
}

el.pmAddBtn.addEventListener("click", async () => {
  const keyword = el.pmKeyword.value.trim();
  const project = el.pmProject.value.trim();
  if (!keyword || !project) return;
  try {
    await fetch("/api/project-keywords/add", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ keyword, project }),
    });
    el.pmKeyword.value = "";
    el.pmProject.value = "";
    loadProjectKeywords();
    loadProjects();
  } catch (e) {
    // sessizce yut
  }
});

// --- sayfa gezinme ---

function showPageSection(id) {
  document.querySelectorAll(".page").forEach((sec) => (sec.hidden = true));
  document.getElementById(id).hidden = false;
}

function renderBaseView() {
  if (state.page === "home") poll();
  else if (state.page === "analytics") {
    loadHeatmap();
    loadAppSummary();
  } else if (state.page === "projects") {
    loadProjectKeywords();
    loadProjectSummary();
  }
}

function setPage(page) {
  state.page = page;
  document.querySelectorAll(".sidebar-item").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.page === page);
  });
  showPageSection(`page-${page}`);
  el.pageTitle.textContent = PAGE_TITLES[page] || "";
  const isHome = page === "home";
  el.dateNav.style.visibility = isHome ? "visible" : "hidden";
  el.reportActions.style.visibility = isHome ? "visible" : "hidden";
  renderBaseView();
}

document.querySelectorAll(".sidebar-item").forEach((btn) => {
  btn.addEventListener("click", () => {
    if (state.querying) {
      state.querying = false;
      el.searchInput.value = "";
      el.searchClear.hidden = true;
    }
    setPage(btn.dataset.page);
  });
});

// --- arama / proje-uygulama filtresi ---

let queryDebounceTimer = null;

async function runQuery(params, titleText) {
  state.querying = true;
  showPageSection("page-query");
  el.pageTitle.textContent = "Arama";
  el.queryTitle.textContent = titleText;
  el.dateNav.style.visibility = "hidden";
  el.reportActions.style.visibility = "hidden";
  el.searchClear.hidden = false;

  const qs = new URLSearchParams();
  if (params.q) qs.set("q", params.q);
  if (params.project) qs.set("project", params.project);
  if (params.app) qs.set("app", params.app);

  try {
    const res = await fetch(`/api/search?${qs.toString()}`, { cache: "no-store" });
    const data = await res.json();
    renderBlocksInto(data.sessions, el.queryLog, el.queryLogEmpty, { showDate: true });
  } catch (e) {
    // sessizce geç
  }
}

function exitQuery() {
  if (!state.querying) return;
  state.querying = false;
  showPageSection(`page-${state.page}`);
  el.pageTitle.textContent = PAGE_TITLES[state.page] || "";
  const isHome = state.page === "home";
  el.dateNav.style.visibility = isHome ? "visible" : "hidden";
  el.reportActions.style.visibility = isHome ? "visible" : "hidden";
  renderBaseView();
}

el.searchInput.addEventListener("input", () => {
  clearTimeout(queryDebounceTimer);
  const q = el.searchInput.value.trim();
  el.searchClear.hidden = q.length === 0;
  queryDebounceTimer = setTimeout(() => {
    if (q) runQuery({ q }, `"${q}" için sonuçlar`);
    else exitQuery();
  }, QUERY_DEBOUNCE_MS);
});

el.searchClear.addEventListener("click", () => {
  el.searchInput.value = "";
  el.searchClear.hidden = true;
  exitQuery();
});

el.datePrev.addEventListener("click", () => shiftDate(-1));
el.dateNext.addEventListener("click", () => shiftDate(1));

el.dlMd.addEventListener("click", () => {
  window.location.href = `/api/report.md?date=${state.currentDate}`;
});
el.dlPdf.addEventListener("click", () => {
  window.open(`/report.html?date=${state.currentDate}`, "_blank");
});

el.refreshBtn.addEventListener("click", () => location.reload());
window.addEventListener("keydown", (e) => {
  if (e.key === "F5" || (e.ctrlKey && e.key.toLowerCase() === "r")) {
    e.preventDefault();
    location.reload();
  }
});

// --- tema (açık/koyu) ---

const THEME_KEY = "piyon-log-theme";

function applyTheme(theme) {
  if (theme === "light") {
    document.documentElement.setAttribute("data-theme", "light");
  } else {
    document.documentElement.removeAttribute("data-theme");
  }
}

function initTheme() {
  let saved = null;
  try {
    saved = localStorage.getItem(THEME_KEY);
  } catch (e) {
    // localStorage kapalıysa sessizce varsayılana düş
  }
  applyTheme(saved === "light" ? "light" : "dark");
}

el.themeToggle.addEventListener("click", () => {
  const isLight = document.documentElement.getAttribute("data-theme") === "light";
  const next = isLight ? "dark" : "light";
  applyTheme(next);
  try {
    localStorage.setItem(THEME_KEY, next);
  } catch (e) {
    // sessizce yut
  }
});

initTheme();

// --- başlangıç ---

loadProjects();
setPage("home");
setInterval(() => {
  if (state.querying || state.page !== "home") return;
  const t = todayStr();
  if (state.followingToday && state.currentDate !== t) {
    goToDate(t);
    return;
  }
  if (state.currentDate === t) poll();
}, POLL_MS);
