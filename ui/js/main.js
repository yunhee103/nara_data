/* 나라장터 입찰정보 시스템 — 화면 로직 */

const $ = (sel) => document.querySelector(sel);
const fmt = (n) => (n == null ? "-" : Number(n).toLocaleString("ko-KR"));

async function api(path, options) {
  const res = await fetch(path, options);
  if (!res.ok) throw new Error(`${path} 요청 실패 (${res.status})`);
  return res.json();
}

/* ── 시작(스플래시) 흐름 ─────────────────────────
   exe 실행 → API 키가 있으면 수집을 돌리며 진행률 표시 → 메인 화면
             → 키가 없으면 안내 후 설정 탭으로 이동 */
async function boot() {
  const status = await api("/api/status");

  if (!status.has_api_key) {
    $("#splash-msg").textContent = "API 인증키가 아직 설정되지 않았습니다.";
    $("#splash-detail").textContent = "공공데이터포털에서 키를 발급받아 입력하면 수집이 시작됩니다.";
    $("#splash-goto-settings").classList.remove("hidden");
    $("#splash-goto-settings").onclick = () => { enterMain(); switchTab("settings"); };
    return;
  }

  $("#splash-msg").textContent = "최신 공고를 수집하고 있습니다...";
  $("#splash-skip").classList.remove("hidden");
  $("#splash-skip").onclick = enterMain;
  await api("/api/collect", { method: "POST" });
  pollSplash();
}

async function pollSplash() {
  const { progress } = await api("/api/status");
  const pct = progress.total ? Math.round((progress.done / progress.total) * 100) : 0;
  $("#splash-bar").style.width = pct + "%";
  $("#splash-detail").textContent = progress.running
    ? `${progress.current}  (${progress.done}/${progress.total})`
    : progress.last_result || "";

  if (progress.running) {
    setTimeout(pollSplash, 500);
  } else {
    $("#splash-bar").style.width = "100%";
    setTimeout(enterMain, 600);
  }
}

function enterMain() {
  $("#splash").classList.add("hidden");
  $("#main").classList.remove("hidden");
  refreshStatus();
  loadKeywordTags();
  loadAnnouncements();
  loadSettings();
}

/* 수집된 데이터에 있는 분야(키워드) 목록으로 드롭다운 채우기 */
async function loadKeywordTags() {
  const tags = await api("/api/keywords");
  $("#f-kwtag").innerHTML =
    `<option value="">전체 분야</option>` +
    tags.map((t) => `<option>${t}</option>`).join("");
}

/* ── 상단 요약/즉시 수집 ────────────────────── */
async function refreshStatus() {
  const s = await api("/api/status");
  $("#stat-bids").textContent = s.today.new_bids;
  $("#stat-awards").textContent = s.today.new_awards;
  $("#stat-next").textContent = s.next_run || "예약 없음";
  $("#btn-refresh").textContent = s.progress.running
    ? `수집 중... ${s.progress.done}/${s.progress.total}`
    : "즉시 수집";
  if (s.progress.running) setTimeout(refreshStatus, 1000);
}

$("#btn-refresh").onclick = async () => {
  await api("/api/collect", { method: "POST" });
  refreshStatus();
};

/* ── 탭 전환 ────────────────────────────────── */
function switchTab(name) {
  document.querySelectorAll(".tab").forEach((t) =>
    t.classList.toggle("active", t.dataset.tab === name));
  ["search", "awards", "alerts", "settings"].forEach((id) =>
    $("#tab-" + id).classList.toggle("hidden", id !== name));
}
document.querySelectorAll(".tab").forEach((t) => {
  t.onclick = () => switchTab(t.dataset.tab);
});

/* ── 탭1: 공고 검색 ─────────────────────────── */
function searchParams() {
  const p = new URLSearchParams();
  if ($("#f-category").value) p.set("category", $("#f-category").value);
  if ($("#f-kwtag").value) p.set("keyword_tag", $("#f-kwtag").value);
  if ($("#f-keyword").value) p.set("keyword", $("#f-keyword").value);
  if ($("#f-from").value) p.set("date_from", $("#f-from").value);
  if ($("#f-to").value) p.set("date_to", $("#f-to").value);
  if ($("#f-bmin").value) p.set("budget_min", $("#f-bmin").value);
  if ($("#f-bmax").value) p.set("budget_max", $("#f-bmax").value);
  return p;
}

/* 마감일까지 남은 날짜 배지 (3일 이내면 빨간색) */
function ddayBadge(deadline) {
  if (!deadline) return "";
  const days = Math.ceil((new Date(deadline) - new Date()) / 86400000);
  if (days < 0) return "";
  const cls = days <= 3 ? "dday urgent" : "dday";
  return ` <span class="${cls}">D-${days === 0 ? "DAY" : days}</span>`;
}

async function loadAnnouncements() {
  const rows = await api("/api/announcements?" + searchParams());
  const tbody = $("#tbl-search tbody");
  $("#search-count").textContent =
    rows.length >= 500 ? "500건+ (상위 500건만 표시, 필터로 좁혀 보세요)" : `${rows.length}건`;
  if (!rows.length) {
    tbody.innerHTML = `<tr class="empty-row"><td colspan="9">데이터가 없습니다. API 키 설정 후 [즉시 수집]을 눌러 주세요.</td></tr>`;
    return;
  }
  tbody.innerHTML = rows.map((r) => `
    <tr>
      <td>${r.category}</td><td>${r.bid_type}</td>
      <td class="title-cell">${r.url ? `<a href="${r.url}" target="_blank" style="color:inherit">${r.title}</a>` : r.title}</td>
      <td>${r.org_name ?? "-"}</td><td>${r.demand_org ?? "-"}</td>
      <td class="num amount">${fmt(r.budget)}</td>
      <td>${r.posted_at ?? "-"}</td><td>${r.deadline ? r.deadline + ddayBadge(r.deadline) : "-"}</td>
      <td>${r.matched_keyword ?? "-"}</td>
    </tr>`).join("");
}
$("#btn-search").onclick = loadAnnouncements;

$("#btn-export").onclick = async () => {
  const body = {
    category: $("#f-category").value || null,
    keyword_tag: $("#f-kwtag").value || null,
    keyword: $("#f-keyword").value || null,
    date_from: $("#f-from").value || null,
    date_to: $("#f-to").value || null,
    budget_min: Number($("#f-bmin").value) || null,
    budget_max: Number($("#f-bmax").value) || null,
  };
  const r = await api("/api/export", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  alert(`엑셀 저장 완료 (${r.count}건)\n${r.path}`);
};

/* ── 탭2: 낙찰 현황 ─────────────────────────── */
/* 이름·금액·건수 배열을 가로 막대로 그리는 공용 렌더러 */
function renderBars(el, rows, nameKey) {
  if (!rows.length) {
    el.innerHTML = `<p class="muted">데이터가 아직 없습니다.</p>`;
    return;
  }
  const max = Math.max(...rows.map((r) => r.total_amount)) || 1;
  el.innerHTML = rows.map((r) => `
    <div class="bar-row">
      <span class="bar-name" title="${r[nameKey]}">${r[nameKey]}</span>
      <div class="bar-track"><div class="bar-fill" style="width:${(r.total_amount / max) * 100}%"></div></div>
      <span class="bar-value">${fmt(r.total_amount)}원 · ${r.award_count}건</span>
    </div>`).join("");
}

async function loadAwards() {
  const kw = $("#a-keyword").value;
  const q = kw ? `?keyword=${encodeURIComponent(kw)}` : "";
  renderBars($("#awards-chart"), await api("/api/awards/summary" + q), "winner");
  renderBars($("#awards-monthly"), await api("/api/awards/monthly" + q), "month");
  renderBars($("#awards-orgs"), await api("/api/awards/orgs" + q), "demand_org");

  const p = new URLSearchParams({ category: "낙찰결과" });
  if (kw) p.set("keyword", kw);
  const rows = await api("/api/announcements?" + p);
  const tbody = $("#tbl-awards tbody");
  if (!rows.length) {
    tbody.innerHTML = `<tr class="empty-row"><td colspan="6">낙찰 데이터가 없습니다.</td></tr>`;
    return;
  }
  tbody.innerHTML = rows.map((r) => {
    const rate = r.award_rate != null ? r.award_rate.toFixed(1) + "%" : "-";
    return `<tr>
      <td class="title-cell">${r.title}</td>
      <td>${r.winner ?? "-"}</td>
      <td class="num amount">${fmt(r.award_amount)}</td>
      <td class="num">${fmt(r.budget)}</td>
      <td class="num">${rate}</td>
      <td>${r.posted_at ?? "-"}</td>
    </tr>`;
  }).join("");
}
$("#btn-awards").onclick = loadAwards;
document.querySelector('[data-tab="awards"]').addEventListener("click", loadAwards);

/* ── 탭3: 알림 내역 ─────────────────────────── */
async function loadAlerts() {
  const p = new URLSearchParams();
  if ($("#n-keyword").value) p.set("keyword", $("#n-keyword").value);
  if ($("#n-from").value) p.set("date_from", $("#n-from").value);
  if ($("#n-to").value) p.set("date_to", $("#n-to").value);
  const rows = await api("/api/notifications?" + p);
  const tbody = $("#tbl-alerts tbody");
  tbody.innerHTML = rows.length
    ? rows.map((r) => `<tr><td>${r.created_at}</td><td>${r.keyword ?? "-"}</td><td>${r.message}</td></tr>`).join("")
    : `<tr class="empty-row"><td colspan="3">알림 내역이 없습니다.</td></tr>`;
}
$("#btn-alerts").onclick = loadAlerts;
document.querySelector('[data-tab="alerts"]').addEventListener("click", loadAlerts);

/* ── 탭4: 설정 ──────────────────────────────── */
async function loadSettings() {
  const s = await api("/api/settings");
  $("#s-apikey").value = s.api_key;
  $("#s-keywords").value = s.keywords.join(", ");
  $("#s-exclude").value = (s.exclude_keywords || []).join(", ");
  $("#s-days").value = s.search_date_range_days;
  $("#s-times").value = s.search_times.join(", ");
  loadSuggestions();
}

/* 수집된 공고 제목의 빈출 단어를 클릭 한 번으로 키워드에 추가 */
async function loadSuggestions() {
  const words = await api("/api/keywords/suggest");
  $("#s-suggest").innerHTML = words.length
    ? `<span class="muted">추천:</span> ` +
      words.map((w) => `<button class="chip" data-word="${w}">+ ${w}</button>`).join("")
    : "";
  document.querySelectorAll(".chip").forEach((c) => {
    c.onclick = () => {
      const cur = $("#s-keywords").value.trim();
      $("#s-keywords").value = cur ? `${cur}, ${c.dataset.word}` : c.dataset.word;
    };
  });
}

$("#btn-save-settings").onclick = async () => {
  const body = {
    api_key: $("#s-apikey").value.trim(),
    keywords: $("#s-keywords").value.split(",").map((s) => s.trim()).filter(Boolean),
    exclude_keywords: $("#s-exclude").value.split(",").map((s) => s.trim()).filter(Boolean),
    search_date_range_days: Number($("#s-days").value) || 7,
    search_times: $("#s-times").value.split(",").map((s) => s.trim()).filter(Boolean),
  };
  await api("/api/settings", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  $("#settings-msg").textContent = "저장되었습니다.";
  setTimeout(() => ($("#settings-msg").textContent = ""), 2000);
  refreshStatus();
};

/* ── 사용성(UX) ─────────────────────────────── */

/* 입력창에서 Enter = 그 탭의 조회 실행 */
function bindEnter(ids, action) {
  ids.forEach((id) =>
    $(id).addEventListener("keydown", (e) => { if (e.key === "Enter") action(); }));
}
bindEnter(["#f-keyword", "#f-from", "#f-to", "#f-bmin", "#f-bmax"], loadAnnouncements);
bindEnter(["#a-keyword"], loadAwards);
bindEnter(["#n-keyword", "#n-from", "#n-to"], loadAlerts);

/* 드롭다운은 고르는 즉시 조회 */
$("#f-category").onchange = loadAnnouncements;
$("#f-kwtag").onchange = loadAnnouncements;

/* 필터 초기화 */
$("#btn-reset").onclick = () => {
  ["#f-keyword", "#f-from", "#f-to", "#f-bmin", "#f-bmax"].forEach((s) => ($(s).value = ""));
  $("#f-category").value = "";
  $("#f-kwtag").value = "";
  loadAnnouncements();
};

/* 표 제목줄 클릭 정렬 (숫자/문자 자동 판별, 재클릭 시 역순) */
function makeSortable(tableSel) {
  const table = document.querySelector(tableSel);
  table.querySelectorAll("thead th").forEach((th, idx) => {
    th.onclick = () => {
      const tbody = table.querySelector("tbody");
      const rows = [...tbody.querySelectorAll("tr")].filter((r) => !r.classList.contains("empty-row"));
      const dir = th.dataset.dir === "asc" ? -1 : 1;
      table.querySelectorAll("thead th").forEach((h) => delete h.dataset.dir);
      th.dataset.dir = dir === 1 ? "asc" : "desc";
      rows.sort((a, b) => {
        const x = a.cells[idx].innerText.trim();
        const y = b.cells[idx].innerText.trim();
        const nx = parseFloat(x.replace(/[,%]/g, ""));
        const ny = parseFloat(y.replace(/[,%]/g, ""));
        const cmp = !isNaN(nx) && !isNaN(ny) ? nx - ny : x.localeCompare(y, "ko");
        return cmp * dir;
      });
      rows.forEach((r) => tbody.appendChild(r));
    };
  });
}
makeSortable("#tbl-search");
makeSortable("#tbl-awards");
makeSortable("#tbl-alerts");

boot();
