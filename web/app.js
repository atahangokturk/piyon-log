// Piyon Log - panel istemcisi. Sunucudan seçili günün verisini periyodik
// olarak çeker ve sunucu logu tarzında akan bir listeye işler.

const POLL_MS = 2500;
const QUERY_DEBOUNCE_MS = 350;
const BADGE_COLORS = [
  "#5b8cff", "#35d488", "#f5a742", "#e35b8c",
  "#8c6bff", "#2fc3d8", "#e0c341", "#ff7a5b",
];

const AY_ADLARI = [
  "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
  "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık",
];

function todayStr() {
  const d = new Date();
  const tz = d.getTimezoneOffset() * 60000;
  return new Date(d - tz).toISOString().slice(0, 10);
}

const state = {
  renderedIds: new Set(),
  currentDate: todayStr(),
  followingToday: true,
  mode: "flow", // 'flow' | 'projects' — hangi sekme aktif
  querying: false, // arama / proje filtresiyle geçici bir liste mi gösteriliyor
  projects: [],
};

const el = {
  status: document.getElementById("status"),
  statusText: document.getElementById("status-text"),
  refreshBtn: document.getElementById("refresh-btn"),
  statTotal: document.getElementById("stat-total"),
  statCount: document.getElementById("stat-count"),
  statFocus: document.getElementById("stat-focus"),
  statProject: document.getElementById("stat-project"),
  statApp: document.getElementById("stat-app"),
  logDate: document.getElementById("log-date"),
  logPanelTitle: document.getElementById("log-panel-title"),
  log: document.getElementById("log"),
  logEmpty: document.getElementById("log-empty"),
  headerControls: document.getElementById("header-controls"),
  dateNav: document.getElementById("date-nav"),
  datePrev: document.getElementById("date-prev"),
  dateNext: document.getElementById("date-next"),
  chart: document.getElementById("chart"),
  heatmap: document.getElementById("heatmap"),
  dlMd: document.getElementById("dl-md"),
  dlPdf: document.getElementById("dl-pdf"),
  searchInput: document.getElementById("search-input"),
  searchClear: document.getElementById("search-clear"),
  tabFlow: document.getElementById("tab-flow"),
  tabProjects: document.getElementById("tab-projects"),
  tabApps: document.getElementById("tab-apps"),
  projectManager: document.getElementById("project-manager"),
  pmKeyword: document.getElementById("pm-keyword"),
  pmProject: document.getElementById("pm-project"),
  pmAddBtn: document.getElementById("pm-add-btn"),
  pmList: document.getElementById("pm-list"),
};

const EMPTY_DEFAULT_TEXT = el.logEmpty.textContent;

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
  return d.toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
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

function renderStats(data) {
  el.statTotal.textContent = formatSure(data.toplam_sure);
  el.statCount.textContent = data.sessions.length;
  el.statFocus.textContent = data.sessions.length ? `%${data.focus_ratio}` : "—";

  const topProject = maxKey(data.project_totals);
  el.statProject.textContent = topProject ? `${topProject[0]} (${formatSure(topProject[1])})` : "—";

  const topApp = maxKey(data.app_totals);
  el.statApp.textContent = topApp ? `${topApp[0]} (${formatSure(topApp[1])})` : "—";

  el.logDate.textContent = formatGun(data.date);
  el.dateNext.disabled = data.date >= todayStr();
}

function renderChart(data) {
  const entries = Object.entries(data.project_totals || {}).sort((a, b) => b[1] - a[1]);
  el.chart.innerHTML = "";

  if (entries.length === 0) {
    const empty = document.createElement("div");
    empty.className = "chart-empty";
    empty.textContent = "Bu gün için veri yok.";
    el.chart.appendChild(empty);
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
    el.chart.appendChild(row);
  }
}

async function loadHeatmap() {
  try {
    const res = await fetch("/api/daily-totals?days=30", { cache: "no-store" });
    const data = await res.json();
    renderHeatmap(data.days || []);
  } catch (e) {
    // bağlantı hatası: sessizce geç
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
      cell.style.background = `rgba(91, 140, 255, ${alpha.toFixed(2)})`;
      cell.style.borderColor = "transparent";
    }
    cell.title = `${d.date} · ${formatSure(d.total_seconds)}`;
    el.heatmap.appendChild(cell);
  }
}

function makeProjectControl(session, color) {
  const wrap = document.createElement("span");

  function renderView() {
    wrap.innerHTML = "";
    const badge = document.createElement("span");
    badge.className = "entry-project";
    badge.title = "Projeyi değiştirmek için tıkla";
    if (session.project) {
      badge.textContent = session.project;
      badge.style.color = color;
    } else {
      badge.textContent = "+ proje";
      badge.style.color = "var(--text-faint)";
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
      if (p === session.project) opt.selected = true;
      select.appendChild(opt);
    }

    select.addEventListener("change", async () => {
      const newProject = select.value || null;
      session.project = newProject;
      renderView();
      try {
        await fetch("/api/session/update", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ id: session.id, project: newProject }),
        });
      } catch (e) {
        // sessizce yut; bir sonraki yenilemede sunucudaki gerçek durum görünür
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

  if (session.title) {
    const title = document.createElement("div");
    title.className = "entry-title";
    title.textContent = session.title;
    card.appendChild(title);
  }

  if (session.text && session.text.trim()) {
    const text = document.createElement("div");
    text.className = "entry-text";
    text.textContent = session.text;
    card.appendChild(text);
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
  const aralik = item.first_date === item.last_date
    ? item.first_date
    : `${item.first_date} – ${item.last_date}`;
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
  const aralik = item.first_date === item.last_date
    ? item.first_date
    : `${item.first_date} – ${item.last_date}`;
  meta.textContent = `${item.session_count} oturum · ${aralik}`;
  card.appendChild(meta);

  card.addEventListener("click", () => {
    runQuery({ app: item.app }, `${item.app} — tüm kayıtlar`);
  });

  return card;
}

function renderSessions(sessions) {
  if (sessions.length === 0) {
    el.logEmpty.style.display = "block";
    return;
  }
  el.logEmpty.style.display = "none";

  const nearBottom = el.log.scrollHeight - el.log.scrollTop - el.log.clientHeight < 40;

  for (const s of sessions) {
    if (state.renderedIds.has(s.id)) continue;
    state.renderedIds.add(s.id);
    el.log.appendChild(makeEntryCard(s));
  }

  if (nearBottom) {
    el.log.scrollTop = el.log.scrollHeight;
  }
}

function clearLog() {
  el.log.querySelectorAll(".entry-card").forEach((card) => card.remove());
  state.renderedIds = new Set();
}

function goToDate(dateStr) {
  if (dateStr > todayStr()) return;
  state.currentDate = dateStr;
  state.followingToday = dateStr === todayStr();
  clearLog();
  poll();
}

function addDays(dateStr, days) {
  // Saat dilimi kaymasından etkilenmemek için tarihi UTC uzayında,
  // saatten bağımsız salt bir takvim günü olarak işler.
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

async function loadProjects() {
  try {
    const res = await fetch("/api/projects");
    const data = await res.json();
    state.projects = data.projects || [];
  } catch (e) {
    state.projects = [];
  }
}

async function poll() {
  if (state.querying || state.mode !== "flow") return;
  try {
    const res = await fetch(`/api/today?date=${state.currentDate}`, { cache: "no-store" });
    if (!res.ok) throw new Error("sunucu hatası");
    const data = await res.json();

    renderStats(data);
    renderChart(data);
    renderSessions(data.sessions);

    const isToday = state.currentDate === todayStr();
    el.status.classList.toggle("live", isToday);
    el.statusText.textContent = isToday ? "canlı" : "arşiv";
  } catch (err) {
    el.status.classList.remove("live");
    el.statusText.textContent = "bağlantı yok";
  }
}

async function loadProjectSummary() {
  if (state.querying || state.mode !== "projects") return;
  el.logEmpty.textContent = EMPTY_DEFAULT_TEXT;
  try {
    const res = await fetch("/api/projects/summary", { cache: "no-store" });
    const data = await res.json();

    clearLog();
    if (data.projects.length === 0) {
      el.logEmpty.textContent = "Henüz proje verisi yok.";
      el.logEmpty.style.display = "block";
    } else {
      el.logEmpty.style.display = "none";
      for (const item of data.projects) {
        el.log.appendChild(makeProjectSummaryCard(item));
      }
    }
  } catch (e) {
    // bağlantı hatası: sessizce geç
  }
}

async function loadAppSummary() {
  if (state.querying || state.mode !== "apps") return;
  el.logEmpty.textContent = EMPTY_DEFAULT_TEXT;
  try {
    const res = await fetch("/api/apps/summary", { cache: "no-store" });
    const data = await res.json();

    clearLog();
    if (data.apps.length === 0) {
      el.logEmpty.textContent = "Henüz uygulama verisi yok.";
      el.logEmpty.style.display = "block";
    } else {
      el.logEmpty.style.display = "none";
      for (const item of data.apps) {
        el.log.appendChild(makeAppSummaryCard(item));
      }
    }
  } catch (e) {
    // bağlantı hatası: sessizce geç
  }
}

function renderBaseView() {
  if (state.mode === "projects") {
    loadProjectSummary();
  } else if (state.mode === "apps") {
    loadAppSummary();
  } else {
    poll();
  }
}

// --- sekmeler (Akış / Projeler / Uygulamalar) ---

function setMode(mode) {
  state.mode = mode;
  el.tabFlow.classList.toggle("active", mode === "flow");
  el.tabProjects.classList.toggle("active", mode === "projects");
  el.tabApps.classList.toggle("active", mode === "apps");
  el.headerControls.style.visibility = mode === "flow" ? "visible" : "hidden";
  el.projectManager.hidden = mode !== "projects";
  if (mode === "projects") loadProjectKeywords();
  if (state.querying) {
    exitQuery();
  } else {
    clearLog();
    renderBaseView();
  }
}

el.tabFlow.addEventListener("click", () => setMode("flow"));
el.tabProjects.addEventListener("click", () => setMode("projects"));
el.tabApps.addEventListener("click", () => setMode("apps"));

// --- arama / proje filtresi (ikisi de aynı "sorgu" görünümünü kullanır) ---

let queryDebounceTimer = null;

async function runQuery(params, titleText) {
  state.querying = true;
  el.dateNav.style.visibility = "hidden";
  el.logPanelTitle.hidden = false;
  el.logPanelTitle.textContent = titleText;
  el.searchClear.hidden = false;

  const qs = new URLSearchParams();
  if (params.q) qs.set("q", params.q);
  if (params.project) qs.set("project", params.project);

  try {
    const res = await fetch(`/api/search?${qs.toString()}`, { cache: "no-store" });
    const data = await res.json();

    clearLog();
    if (data.sessions.length === 0) {
      el.logEmpty.textContent = "Sonuç bulunamadı.";
      el.logEmpty.style.display = "block";
    } else {
      el.logEmpty.style.display = "none";
      for (const s of data.sessions) {
        state.renderedIds.add(s.id);
        el.log.appendChild(makeEntryCard(s, { showDate: true }));
      }
    }
  } catch (e) {
    // bağlantı hatası: sessizce geç
  }
}

function exitQuery() {
  if (!state.querying) return;
  state.querying = false;
  el.dateNav.style.visibility = state.mode === "flow" ? "visible" : "hidden";
  el.logPanelTitle.hidden = true;
  el.searchClear.hidden = el.searchInput.value.trim().length === 0;
  el.logEmpty.textContent = EMPTY_DEFAULT_TEXT;
  clearLog();
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

el.refreshBtn.addEventListener("click", () => location.reload());

// Adres çubuğu/menü olmayan native pencerede F5 varsayılan olarak çalışmayabilir.
window.addEventListener("keydown", (e) => {
  if (e.key === "F5" || (e.ctrlKey && e.key.toLowerCase() === "r")) {
    e.preventDefault();
    location.reload();
  }
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

// --- proje yönetimi (anahtar kelime -> proje kuralları) ---

async function loadProjectKeywords() {
  try {
    const res = await fetch("/api/project-keywords", { cache: "no-store" });
    const data = await res.json();
    renderProjectKeywords(data.keywords || []);
  } catch (e) {
    // bağlantı hatası: sessizce geç
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

loadProjects();
loadHeatmap();
poll();
setInterval(() => {
  if (state.querying || state.mode !== "flow") return;
  const t = todayStr();
  if (state.followingToday && state.currentDate !== t) {
    // gece yarisini gectik: "bugun"u takip ediyorsak otomatik olarak yeni gune gec
    goToDate(t);
    return;
  }
  if (state.currentDate === t) poll();
}, POLL_MS);
