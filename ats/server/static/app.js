// Shared client runtime for all dashboard pages.
// One WebSocket feeds every page; pages register handlers via ATS.on(type, fn).
(function () {
  const handlers = { snapshot: [], recent: [], event: [] };
  const TOPIC_STAGE = {
    "market.tick": "market", "market.bar": "market", "market.volume_spike": "market",
    "news.item": "news", "news.sentiment": "nlp", "strategy.signal": "strategy",
    "agent.opinion": "agents", "agent.proposal": "cio", "exec.decision": "risk",
    "exec.order": "execution", "exec.fill": "execution", "exec.approval_request": "execution",
  };

  let ws = null, reconnectTimer = null;

  function setDot(on) {
    const d = document.getElementById("wsdot");
    if (d) d.classList.toggle("on", !!on);
  }

  function connect() {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    ws = new WebSocket(`${proto}://${location.host}/ws`);
    ws.onopen = () => setDot(true);
    ws.onclose = () => { setDot(false); scheduleReconnect(); };
    ws.onerror = () => { try { ws.close(); } catch (e) {} };
    ws.onmessage = (m) => {
      let msg; try { msg = JSON.parse(m.data); } catch (e) { return; }
      if (msg.type === "snapshot") {
        updateHeader(msg.data);
        handlers.snapshot.forEach((fn) => safe(fn, msg.data));
      } else if (msg.type === "recent") {
        handlers.recent.forEach((fn) => safe(fn, msg));
      } else if (msg.type === "event") {
        maybeToast(msg);
        collectAlert(msg);
        handlers.event.forEach((fn) => safe(fn, msg));
      }
    };
  }
  function scheduleReconnect() {
    clearTimeout(reconnectTimer);
    reconnectTimer = setTimeout(connect, 1500);
  }
  function safe(fn, a) { try { fn(a); } catch (e) { console.error(e); } }

  // ---- Header (shared status + controls) -------------------------------
  function updateHeader(snap) {
    const st = (snap && snap.state) || {};
    setPill("hdrMode", st.mode || "?", st.mode === "AUTO" ? "green" : st.mode === "OFF" ? "gray" : "amber");
    setPill("hdrKill", st.kill_switch ? "KILLED" : "ARMED", st.kill_switch ? "red" : "green");
    setPill("hdrMoney", st.real_money_active ? "REAL MONEY" : "PAPER", st.real_money_active ? "red" : "blue");
    const eq = document.getElementById("hdrEquity");
    if (eq && snap && snap.portfolio) eq.textContent = fmtMoney(snap.portfolio.equity);
    const ds = document.getElementById("hdrData");
    if (ds && snap && snap.data_status) {
      const s = snap.data_status;
      setPill("hdrData", `${s.live || 0}/${s.total || 0} live`, (s.live > 0) ? "green" : "gray");
    }
    const sel = document.getElementById("modeSel");
    if (sel && st.mode && sel.value !== st.mode) sel.value = st.mode;
    const kb = document.getElementById("killBtn");
    if (kb) {
      kb.dataset.killed = st.kill_switch ? "1" : "0";
      kb.textContent = st.kill_switch ? "Release" : "Kill";
      kb.className = st.kill_switch ? "go" : "danger";
    }
  }
  function setPill(id, text, cls) {
    const el = document.getElementById(id);
    if (!el) return;
    el.textContent = text;
    el.className = "pill " + (cls || "gray");
  }

  // ---- Per-loop status pills (fast / medium / slow) ----------------------
  function refreshLoopPills() {
    if (!document.getElementById("hdrLoopF")) return;
    fetchJSON("/api/loops").then((d) => {
      const f = d.fast || {}, m = d.medium || {}, s = d.slow || {};
      const feedBad = (f.feed || {}).degraded;
      const reconBad = ((f.reconciliation || {}).last || {}).ok === false;
      setPill("hdrLoopF", "F", f.kill_switch ? "red" : (feedBad || reconBad) ? "amber" : "green");
      const sum = m.summary || {};
      setPill("hdrLoopM", "M", (sum.total || 0) > 0 ? ((sum.paper || 0) > 0 ? "green" : "amber") : "gray");
      const fac = s.factory || {};
      const budget = fac.budget || {};
      setPill("hdrLoopS", "S", !fac.enabled ? "gray" : budget.exhausted ? "amber" : "green");
      const titles = {
        hdrLoopF: `Fast loop: mode ${f.mode || "?"}, ${f.orders_in_flight || 0} in flight` + (f.kill_switch ? " — KILLED" : ""),
        hdrLoopM: `Medium loop: ${sum.paper || 0}/${sum.total || 0} sleeves trading, ${sum.live_calls || 0} live calls`,
        hdrLoopS: `Slow loop: budget ₹${(budget.used_inr || 0).toFixed(0)}/${(budget.budget_inr || 0).toFixed(0)}` + (budget.exhausted ? " — exhausted" : ""),
      };
      Object.entries(titles).forEach(([id, t]) => { const el = document.getElementById(id); if (el) el.title = t; });
    }).catch(() => {});
  }

  // ---- Toast notifications ---------------------------------------------
  const TOAST_MS = 6000;
  function maybeToast(msg) {
    const p = msg.payload || {}, t = msg.topic;
    if (t === "market.volume_spike")
      toast("info", "Volume spike", `${p.symbol || ""} — z=${fmt(p.zscore)} (${fmt(p.volume)})`);
    else if (t === "exec.approval_request")
      toast("warn", "Approval needed", `${p.action || ""} ${p.symbol || ""} qty ${p.qty || p.target_qty || ""}`);
    else if (t === "exec.fill")
      toast("good", "Order filled", `${p.symbol || ""} ${p.side || ""} ${p.qty || ""} @ ${fmt(p.fill_price)}`);
    else if (t === "exec.decision" && (p.status === "blocked" || p.action === "HOLD"))
      toast("info", "Decision: HOLD", `${p.symbol || ""} — ${(p.applied || []).join(", ") || "no action"}`);
    else if (t === "exec.decision")
      toast("info", "Decision", `${p.action || ""} ${p.symbol || ""} qty ${p.qty || p.target_qty || ""}`);
    else if (t === "system.alert")
      toast("bad", "Alert", p.message || JSON.stringify(p).slice(0, 120));
    else if (t === "rules.change")
      toast("warn", "Rule change", `${p.rule || ""} → ${p.status || ""}`);
  }
  function toast(kind, title, msg) {
    const wrap = document.getElementById("toasts");
    if (!wrap) return;
    const el = document.createElement("div");
    el.className = "toast " + kind;
    el.innerHTML = `<div class="ttl">${esc(title)}</div><div class="msg">${esc(msg)}</div>`;
    wrap.appendChild(el);
    setTimeout(() => { el.style.opacity = "0"; setTimeout(() => el.remove(), 300); }, TOAST_MS);
    while (wrap.children.length > 6) wrap.firstChild.remove();
  }

  // ---- Alerts center + browser notifications ---------------------------
  const alerts = [];
  let alertsUnread = 0;
  let notifyOk = false;
  // events worth surfacing as alerts, with priority (notify on high)
  const ALERT_RULES = {
    "market.volume_spike": (p) => ({ kind: "info", t: "Volume spike", m: `${p.symbol||""} z=${fmt(p.zscore)}`, hi: false }),
    "exec.fill":           (p) => ({ kind: "good", t: "Order filled", m: `${p.symbol||""} ${p.side||""} ${p.qty||""}`, hi: true }),
    "exec.approval_request": (p) => ({ kind: "warn", t: "Approval needed", m: `${p.action||""} ${p.symbol||""}`, hi: true }),
    "system.alert":        (p) => ({ kind: "bad", t: "System alert", m: p.message || "", hi: true }),
    "rules.change":        (p) => ({ kind: "warn", t: "Rule changed", m: `${p.rule||""} → ${p.status||""}`, hi: false }),
    "market.regime":       (p) => ({ kind: "info", t: "Regime shift", m: p.label || JSON.stringify(p).slice(0,60), hi: true }),
  };
  function collectAlert(msg) {
    const rule = ALERT_RULES[msg.topic];
    if (!rule) return;
    const a = rule(msg.payload || {});
    a.ts = msg.ts || new Date().toISOString();
    alerts.unshift(a);
    while (alerts.length > 50) alerts.pop();
    alertsUnread++;
    renderAlerts();
    if (a.hi && notifyOk && document.hidden) {
      try { new Notification(a.t, { body: a.m }); } catch (e) {}
    }
  }
  function renderAlerts() {
    const badge = document.getElementById("alertsBadge");
    if (badge) { badge.textContent = alertsUnread ? String(alertsUnread) : ""; badge.style.display = alertsUnread ? "" : "none"; }
    const list = document.getElementById("alertsList");
    if (!list) return;
    list.innerHTML = alerts.length ? alerts.slice(0, 30).map((a) =>
      `<div class="alert-row ${a.kind}"><b>${esc(a.t)}</b> <span class="muted">${ago(a.ts)}</span><div class="muted">${esc(a.m)}</div></div>`).join("")
      : '<div class="empty">No alerts yet.</div>';
  }

  // ---- "Explain this" popover ------------------------------------------
  async function explain(anchor, context) {
    const pop = document.getElementById("explainPop");
    if (!pop) return;
    const r = anchor.getBoundingClientRect();
    pop.style.left = Math.min(window.innerWidth - 320, r.left) + "px";
    pop.style.top = (r.bottom + 8) + "px";
    pop.innerHTML = '<div class="muted">Thinking…</div>';
    pop.classList.add("open");
    try {
      const d = await postJSON("/api/explain", { context });
      pop.innerHTML = `<div>${esc(d.text)}</div><div class="muted" style="font-size:10px;margin-top:6px">${d.real ? "AI" : "auto"} · click away to close</div>`;
    } catch (e) { pop.innerHTML = '<div class="muted">Could not explain right now.</div>'; }
  }

  // ---- Controls ---------------------------------------------------------
  async function setMode(mode) {
    await postJSON("/api/mode", { mode });
  }
  async function setKill(engage) {
    await postJSON("/api/kill", { engage, reason: "dashboard" });
  }
  async function approve(id, ok) {
    await fetch(`/api/approvals/${id}/${ok ? "approve" : "reject"}`, { method: "POST" });
  }

  // ---- Helpers ----------------------------------------------------------
  async function fetchJSON(url) { const r = await fetch(url); return r.json(); }
  async function postJSON(url, body) {
    const r = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    return r.json();
  }
  function fmt(x) { return (x === null || x === undefined || x === "") ? "–" : (typeof x === "number" ? (Math.round(x * 100) / 100) : x); }
  function fmtMoney(x) {
    if (x === null || x === undefined) return "–";
    return "₹" + Number(x).toLocaleString("en-IN", { maximumFractionDigits: 0 });
  }
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])); }
  function ago(ts) {
    if (!ts) return "";
    const d = (Date.now() - new Date(ts).getTime()) / 1000;
    if (d < 60) return Math.max(0, Math.floor(d)) + "s";
    if (d < 3600) return Math.floor(d / 60) + "m";
    return Math.floor(d / 3600) + "h";
  }

  // ---- Animated number count-up (gated by the reduce-motion toggle) -----
  function motionOn() { return document.documentElement.dataset.motion !== "reduced"; }
  function countUp(el, to, opts) {
    opts = opts || {};
    const fmtFn = opts.money ? fmtMoney : (v) => (opts.fmt ? opts.fmt(v) : fmt(v));
    const target = Number(to);
    if (!el || isNaN(target)) { if (el) el.textContent = fmtFn(to); return; }
    if (!motionOn()) { el.textContent = fmtFn(target); return; }
    const from = Number(el.dataset.val || 0);
    const dur = opts.dur || 600, t0 = performance.now();
    function step(now) {
      const p = Math.min(1, (now - t0) / dur);
      const eased = 1 - Math.pow(1 - p, 3);
      el.textContent = fmtFn(from + (target - from) * eased);
      if (p < 1) requestAnimationFrame(step);
      else el.dataset.val = String(target);
    }
    requestAnimationFrame(step);
  }
  function signClass(x) { return Number(x) > 0 ? "up" : Number(x) < 0 ? "down" : ""; }

  // ---- Lightweight cursor-follow glow (Modern); off when reduce-motion ---
  function initCursorGlow() {
    let glow = document.getElementById("cursorGlow");
    if (!glow) {
      glow = document.createElement("div");
      glow.id = "cursorGlow";
      document.body.appendChild(glow);
    }
    window.addEventListener("pointermove", (e) => {
      if (!motionOn()) { glow.style.opacity = "0"; return; }
      glow.style.opacity = "1";
      glow.style.transform = `translate(${e.clientX}px, ${e.clientY}px)`;
    }, { passive: true });
  }

  // ---- Shared opportunity card markup ----------------------------------
  function oppCard(o) {
    const pct = Math.round((o.score || 0) * 100);
    // Simple by design: ticker, a clear LONG/SHORT call, one plain line of why,
    // and conviction. The full breakdown lives in the detail panel on click.
    const headline = o.headline || `${o.direction || ""} setup`;
    const driver = o.driver ? ` · ${esc(o.driver)}` : "";
    return `<div class="card opp" data-symbol="${esc(o.symbol)}">
      <div class="top">
        <span class="sym">${esc(o.symbol)}</span>
        <span class="side ${esc(o.side)}">${esc(o.side)}</span>
      </div>
      <div class="opp-headline">${esc(headline)}${driver}</div>
      <div class="score-bar" title="conviction ${pct}%"><i style="width:${pct}%"></i></div>
      <div class="meta">
        <span class="conv ${esc(o.conviction)}">${esc(o.conviction)} conviction</span>
        <span class="status ${esc(o.status)}">${esc(o.status)}</span>
        <span class="muted" style="margin-left:auto;font-size:11px">details →</span>
      </div>
    </div>`;
  }

  window.ATS = {
    on: (type, fn) => { (handlers[type] || (handlers[type] = [])).push(fn); },
    connect, setMode, setKill, approve, fetchJSON, postJSON,
    fmt, fmtMoney, esc, ago, TOPIC_STAGE, countUp, signClass, motionOn, oppCard, explain,
  };

  document.addEventListener("DOMContentLoaded", () => {
    // Wire shared header controls if present.
    const modeSel = document.getElementById("modeSel");
    if (modeSel) modeSel.onchange = () => setMode(modeSel.value);
    const killBtn = document.getElementById("killBtn");
    if (killBtn) killBtn.onclick = async () => {
      const killed = killBtn.dataset.killed === "1";
      await setKill(!killed);
    };
    connect();
    initCursorGlow();
    // Seed header immediately from REST in case first WS snapshot lags.
    fetchJSON("/api/dashboard").then(updateHeader).catch(() => {});
    refreshLoopPills();
    setInterval(refreshLoopPills, 30000);

    // Alerts bell + browser notifications
    const aBtn = document.getElementById("alertsBtn");
    const aPop = document.getElementById("alertsPop");
    if (aBtn && aPop) {
      aBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        aPop.classList.toggle("open");
        alertsUnread = 0; renderAlerts();
        if (window.Notification && Notification.permission === "default")
          Notification.requestPermission().then((p) => { notifyOk = p === "granted"; });
      });
      document.addEventListener("click", (e) => { if (!aPop.contains(e.target) && e.target !== aBtn) aPop.classList.remove("open"); });
    }
    if (window.Notification && Notification.permission === "granted") notifyOk = true;
    const aClear = document.getElementById("alertsClear");
    if (aClear) aClear.onclick = () => { alerts.length = 0; alertsUnread = 0; renderAlerts(); };

    // Delegated "explain this": any element with data-explain
    document.addEventListener("click", (e) => {
      const t = e.target.closest("[data-explain]");
      const pop = document.getElementById("explainPop");
      if (t) { e.stopPropagation(); explain(t, t.getAttribute("data-explain")); }
      else if (pop && !pop.contains(e.target)) pop.classList.remove("open");
    });
  });
})();
