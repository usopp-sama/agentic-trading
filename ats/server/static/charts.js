/* Thin, theme-aware wrapper around the vendored TradingView Lightweight Charts.
 * Pulls candles from /api/ohlcv and markers from /api/annotations, colored from
 * the active theme tokens so charts match Modern / Minecraft / future themes.
 */
(function () {
  if (!window.LightweightCharts) { console.warn("Lightweight Charts not loaded"); return; }
  const LC = window.LightweightCharts;

  function tok(name, fallback) {
    const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    return v || fallback;
  }

  function baseOptions(mini) {
    return {
      autoSize: true,
      layout: { background: { color: "transparent" }, textColor: tok("--muted", "#93a1b5"),
                fontFamily: tok("--font", "sans-serif") },
      grid: { vertLines: { visible: !mini, color: tok("--border", "#26344a") },
              horzLines: { visible: !mini, color: tok("--border", "#26344a") } },
      rightPriceScale: { visible: !mini, borderColor: tok("--border", "#26344a") },
      timeScale: { visible: !mini, borderColor: tok("--border", "#26344a"),
                   timeVisible: true, secondsVisible: false },
      crosshair: { mode: mini ? 0 : 1 },
      handleScroll: !mini, handleScale: !mini,
    };
  }

  function candleColors() {
    const up = tok("--green", "#34d399"), down = tok("--red", "#fb7185");
    return { upColor: up, downColor: down, borderUpColor: up, borderDownColor: down,
             wickUpColor: up, wickDownColor: down };
  }

  async function fetchJSON(u) { const r = await fetch(u); return r.json(); }

  // Snap an event time to the nearest candle time so markers sit ON a bar.
  function nearest(times, t) {
    if (!times.length) return t;
    let lo = 0, hi = times.length - 1;
    if (t <= times[0]) return times[0];
    if (t >= times[hi]) return times[hi];
    while (lo <= hi) {
      const mid = (lo + hi) >> 1;
      if (times[mid] === t) return t;
      if (times[mid] < t) lo = mid + 1; else hi = mid - 1;
    }
    const a = times[Math.max(0, hi)], b = times[Math.min(times.length - 1, lo)];
    return (t - a) <= (b - t) ? a : b;
  }

  // Floating HTML tooltip for hovered annotations (markers stay as small dots).
  function ensureTooltip(el) {
    let tip = el.querySelector(".chart-tip");
    if (!tip) {
      tip = document.createElement("div");
      tip.className = "chart-tip";
      el.appendChild(tip);
    }
    return tip;
  }

  function attachHover(chart, el, byTime) {
    const tip = ensureTooltip(el);
    chart.subscribeCrosshairMove((param) => {
      const evts = param.time != null ? byTime.get(param.time) : null;
      if (!evts || !evts.length || !param.point) { tip.style.display = "none"; return; }
      tip.innerHTML = evts.slice(0, 8).map((e) =>
        `<div class="row"><span class="dot" style="background:${e.color}"></span>${esc(e.detail || e.label)}</div>`).join("");
      const w = el.clientWidth, x = param.point.x;
      tip.style.display = "block";
      tip.style.left = Math.min(w - 270, Math.max(8, x + 14)) + "px";
      tip.style.top = "12px";
    });
  }

  function esc(s) { const d = document.createElement("div"); d.textContent = s == null ? "" : String(s); return d.innerHTML; }

  // Collapse many same-bar events into one dot per (time, position); the full
  // list shows on hover. Priority picks the dot colour when kinds mix.
  const KIND_PRI = { fill: 5, news: 4, move: 3, volume: 2, signal: 1, sme: 0 };
  function buildMarkers(annotations, candleTimes) {
    const byTime = new Map();        // snappedTime -> [events]
    for (const m of annotations) {
      const t = nearest(candleTimes, m.time);
      const e = { ...m, time: t };
      if (!byTime.has(t)) byTime.set(t, []);
      byTime.get(t).push(e);
    }
    const markers = [];
    for (const [t, evts] of byTime) {
      for (const pos of ["aboveBar", "belowBar"]) {
        const here = evts.filter((e) => e.position === pos);
        if (!here.length) continue;
        const lead = here.slice().sort((a, b) => (KIND_PRI[b.kind] || 0) - (KIND_PRI[a.kind] || 0))[0];
        markers.push({
          time: t, position: pos, color: lead.color, shape: lead.shape || "circle",
          text: here.length > 1 ? String(here.length) : "",
        });
      }
    }
    markers.sort((a, b) => a.time - b.time);
    return { markers, byTime };
  }

  async function render(elId, symbol, interval, mini) {
    const el = document.getElementById(elId);
    if (!el) return null;
    el.innerHTML = "";
    el.style.position = "relative";
    const chart = LC.createChart(el, baseOptions(mini));
    const series = chart.addCandlestickSeries(candleColors());
    const iv = interval || "1d";
    const data = await fetchJSON(`/api/ohlcv?symbol=${encodeURIComponent(symbol)}&interval=${iv}&limit=${mini ? 80 : 400}`);
    const candles = (data.candles || []).filter((c) => c.time);
    series.setData(candles);
    if (!mini) {
      const vol = chart.addHistogramSeries({ priceFormat: { type: "volume" }, priceScaleId: "vol",
        color: tok("--accent", "#2dd4bf") });
      chart.priceScale("vol").applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });
      vol.setData(candles.map((c) => ({ time: c.time, value: c.volume || 0,
        color: (c.close >= c.open) ? tok("--green", "#34d399") : tok("--red", "#fb7185") })));
      const ann = await fetchJSON(`/api/annotations?symbol=${encodeURIComponent(symbol)}&interval=${iv}`);
      const times = candles.map((c) => c.time);
      const { markers, byTime } = buildMarkers(ann.markers || [], times);
      if (markers.length) series.setMarkers(markers);
      attachHover(chart, el, byTime);
    }
    chart.timeScale().fitContent();
    return { chart, series };
  }

  async function equity(elId) {
    const el = document.getElementById(elId);
    if (!el) return null;
    el.innerHTML = "";
    const chart = LC.createChart(el, baseOptions(false));
    const accent = tok("--accent", "#2dd4bf");
    const series = chart.addAreaSeries({
      lineColor: accent, topColor: accent,
      bottomColor: "transparent", lineWidth: 2,
    });
    const data = await fetchJSON("/api/equity_curve?limit=730");
    series.setData((data.points || []).map((p) => ({ time: p.time, value: p.equity })));
    chart.timeScale().fitContent();
    return { chart, series };
  }

  window.ATSChart = {
    full: (elId, symbol, interval) => render(elId, symbol, interval, false),
    mini: (elId, symbol) => render(elId, symbol, "1d", true),
    equity,
  };
})();
