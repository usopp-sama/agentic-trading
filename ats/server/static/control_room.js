/* Control Room (QA-9): data-first monitoring — heatmap + ticker + status +
 * command palette + drill-down drawer. Built entirely on existing read APIs
 * (/api/analytics, /api/opportunities, /api/movers, /api/dashboard, /api/loops).
 * Live status rides the shared snapshot WebSocket; the heatmap/movers poll on a
 * 60s cadence (they derive from the analytics close/poll passes).
 */
(function () {
  const A = window.ATS || {};
  const esc = A.esc || ((s) => String(s == null ? "" : s));
  const fmtMoney = A.fmtMoney || ((v) => "₹" + Number(v || 0).toLocaleString("en-IN"));
  const $ = (id) => document.getElementById(id);
  let ROWS = [];          // analytics table (heatmap source)

  function scoreClass(s) {
    if (s == null) return "n";
    if (s >= 6) return "sb"; if (s >= 3) return "b";
    if (s <= -6) return "ss"; if (s <= -3) return "s"; return "n";
  }

  async function get(url) {
    try {
      if (A.fetchJSON) return await A.fetchJSON(url);
      const r = await fetch(url); return await r.json();
    } catch (e) { return null; }
  }

  // ---- heatmap ----
  function renderHeat(filter) {
    const el = $("crHeat");
    let rows = ROWS.slice().sort((a, b) => (b.tech_score || 0) - (a.tech_score || 0));
    if (filter) rows = rows.filter((r) => r.symbol.toLowerCase().includes(filter));
    $("crHeatMeta").textContent = rows.length + " symbols";
    if (!rows.length) { el.innerHTML = '<div class="empty">No analytics snapshots yet — run the close pass (or synthetic feed).</div>'; return; }
    el.innerHTML = rows.map((r) => {
      const sc = r.tech_score;
      return `<div class="cr-cell ${scoreClass(sc)}" data-sym="${esc(r.symbol)}" title="${esc(r.symbol)} · score ${sc} · ${esc(r.verdict || "")}">
        <div class="sym">${esc(r.symbol.replace(/\.(NS|BO)$/, ""))}</div>
        <div class="sc">${sc > 0 ? "+" : ""}${sc == null ? "–" : sc}</div></div>`;
    }).join("");
    el.querySelectorAll(".cr-cell").forEach((c) => c.onclick = () => openDrawer(c.dataset.sym));
  }

  async function loadHeat() {
    const j = await get("/api/analytics");
    ROWS = (j && j.rows) || [];
    renderHeat(($("crCmd").value || "").trim().toLowerCase());
  }

  // ---- ticker ----
  async function loadTicker() {
    const j = await get("/api/opportunities?limit=20");
    const el = $("crTicker");
    const list = (j && j.opportunities) || [];
    if (!list.length) { el.innerHTML = '<div class="empty">No high-conviction setups right now.</div>'; return; }
    el.innerHTML = list.map((o) => {
      const side = o.side || (o.direction || "").toUpperCase();
      const cls = side === "LONG" ? "up" : side === "SHORT" ? "down" : "muted";
      return `<div class="tk-row" data-sym="${esc(o.symbol)}">
        <span class="sym">${esc(o.symbol.replace(/\.(NS|BO)$/, ""))}</span>
        <span class="pct ${cls}">${esc(side)}</span>
        <span class="drv">${esc(o.driver || o.setup || "")}</span>
        <span class="conv ${esc(o.conviction || "low")}">${esc(o.conviction || "")}</span>
      </div>`;
    }).join("");
    el.querySelectorAll(".tk-row").forEach((r) => r.onclick = () => openDrawer(r.dataset.sym));
  }

  // ---- movers ----
  async function loadMovers() {
    const m = await get("/api/movers");
    const el = $("crMovers");
    const arr = (m && m.volume_confirmed) || [];
    if (!arr.length) { el.innerHTML = '<div class="empty">—</div>'; return; }
    el.innerHTML = arr.slice(0, 6).map((e) =>
      `<div class="cr-stat" style="cursor:pointer" onclick="location.href='/charts?symbol=${encodeURIComponent(e.symbol)}'">
        <span class="k">${esc(e.symbol.replace(/\.(NS|BO)$/, ""))}</span>
        <b class="${e.pct_change >= 0 ? "up" : "down"}">${e.pct_change >= 0 ? "+" : ""}${(e.pct_change).toFixed(2)}%</b></div>`).join("");
  }

  // ---- status ----
  function applySnap(s) {
    if (!s) return;
    const pf = s.portfolio || {};
    if (pf.equity != null) $("crEquity").textContent = fmtMoney(pf.equity);
    const dp = (pf.unrealized_pnl || 0) + (pf.realized_pnl || 0);
    const d = $("crDayPnl"); d.textContent = fmtMoney(dp); d.className = "cr-mono " + (dp >= 0 ? "up" : "down");
    const st = s.state || {};
    if (st.mode) $("crMode").textContent = st.mode;
    if (st.regime) $("crRegime").textContent = st.regime;
    $("crKill").textContent = st.kill_switch ? "ENGAGED" : "clear";
  }
  async function loadStatus() {
    applySnap(await get("/api/dashboard"));
    const lp = await get("/api/loops");
    if (lp) {
      $("crLoopF").classList.toggle("on", !(lp.fast || {}).kill_switch);
      $("crLoopM").classList.toggle("on", Object.keys((lp.medium || {}).summary || {}).length > 0);
      $("crLoopS").classList.toggle("on", ((lp.slow || {}).factory || {}).enabled !== false);
      const reg = (lp.medium || {}).regime; if (reg) $("crRegime").textContent = reg;
    }
    const health = await get("/api/health");
    if (health && health.llm) $("crLlm").textContent = health.llm.real ? "real" : "mock";
  }

  // ---- drawer ----
  async function openDrawer(symbol) {
    const body = $("crDrawerBody");
    body.innerHTML = `<h2>${esc(symbol)}</h2><div class="muted">Loading…</div>`;
    $("crDrawer").classList.add("open");
    const a = await get("/api/analytics/" + encodeURIComponent(symbol));
    if (!a || a.empty) { body.innerHTML = `<h2>${esc(symbol)}</h2><div class="empty">No snapshot yet.</div>`; return; }
    const sm = a.summary || {}; const fv = a.fair_value;
    const comps = (sm.components || []).map((c) => {
      const cls = c.vote > 0 ? "b" : c.vote < 0 ? "s" : "n";
      return `<div class="cr-comp"><span>${esc(c.name)}</span><span class="${cls}">${c.vote > 0 ? "▲" : c.vote < 0 ? "▼" : "•"}</span></div>`;
    }).join("");
    let fvHtml = '<div class="empty">No fair value (thin fundamentals).</div>';
    if (fv) {
      const grid = (fv.sensitivity && fv.sensitivity.grid || []).map((row) =>
        row.map((v) => `<div>${v}</div>`).join("")).join("");
      fvHtml = `<div class="cr-mono">Intrinsic <b>${fv.intrinsic}</b> · Price ${fv.price ?? "–"} ·
        <span class="${fv.verdict === "undervalued" ? "up" : fv.verdict === "overvalued" ? "down" : "muted"}">${esc(fv.verdict)}</span>
        (MoS ${fv.margin_of_safety_pct ?? "–"}%)</div>
        <div class="muted" style="font-size:11px;margin-top:6px">Sensitivity (wacc × growth)</div>
        <div class="cr-grid3">${grid}</div>
        <div class="muted" style="font-size:11px;margin-top:4px">Model estimate · Piotroski F ${fv.quality ? fv.quality.f_score : "–"}/9</div>`;
    }
    body.innerHTML = `
      <h2>${esc(symbol)} <span class="conv ${sm.label && sm.label.indexOf("buy") >= 0 ? "high" : sm.label && sm.label.indexOf("sell") >= 0 ? "low" : "medium"}">${esc(sm.label || "")}</span></h2>
      <div class="muted cr-mono" style="margin-bottom:8px">score ${sm.score ?? "–"} · ${sm.bulls ?? 0}▲ / ${sm.bears ?? 0}▼ · ₹${a.price ?? "–"}</div>
      <a href="/charts?symbol=${encodeURIComponent(symbol)}" class="pill accent">Open chart →</a>
      <h2 style="font-size:13px;margin:14px 0 4px">Fair value</h2>${fvHtml}
      <h2 style="font-size:13px;margin:14px 0 4px">Technical checks</h2>${comps}`;
  }
  function closeDrawer() { $("crDrawer").classList.remove("open"); }

  // ---- command palette ----
  const cmd = $("crCmd");
  cmd.addEventListener("input", () => renderHeat(cmd.value.trim().toLowerCase()));
  cmd.addEventListener("keydown", (e) => {
    if (e.key === "Escape") { cmd.value = ""; renderHeat(""); closeDrawer(); }
    if (e.key === "Enter") {
      const f = cmd.value.trim().toLowerCase();
      const hit = ROWS.find((r) => r.symbol.toLowerCase().includes(f));
      if (hit) openDrawer(hit.symbol);
    }
  });
  $("crDrawerX").onclick = closeDrawer;

  // ---- boot + cadence ----
  if (A.on) A.on("snapshot", applySnap);
  loadHeat(); loadTicker(); loadMovers(); loadStatus();
  setInterval(() => { loadHeat(); loadTicker(); loadMovers(); }, 60000);
})();
