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

  window.ATS = {
    on: (type, fn) => { (handlers[type] || (handlers[type] = [])).push(fn); },
    connect, setMode, setKill, approve, fetchJSON, postJSON,
    fmt, fmtMoney, esc, ago, TOPIC_STAGE,
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
    // Seed header immediately from REST in case first WS snapshot lags.
    fetchJSON("/api/dashboard").then(updateHeader).catch(() => {});
  });
})();
