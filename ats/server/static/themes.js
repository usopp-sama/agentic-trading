/* Theme engine: a small registry + switcher.
 *
 * A theme = a set of CSS tokens (and optionally a JS module that mounts an
 * animated background / cursor effects). Switching applies data-theme on
 * <html>, lazy-loads the theme's CSS/JS, runs the previous theme's unmount()
 * and the new theme's mount(), and remembers the choice per device.
 *
 * To add a theme later (anime, three.js, ...):
 *   1) drop /static/themes/<id>.css (override the tokens in app.css)
 *   2) optional /static/themes/<id>.js that calls
 *        ATSTheme.define('<id>', { mount(root){...}, unmount(){...} })
 *   3) register it in REGISTRY below (id, name, css?, js?, variants?)
 */
(function () {
  const REGISTRY = {
    modern:    { name: "Modern",    variants: true },                                            // tokens live in app.css
    nightdesk: { name: "Nightdesk", css: "/static/themes/nightdesk.css", variants: true },       // trading desk at 2 AM
    minecraft: { name: "Minecraft", css: "/static/themes/minecraft.css", js: "/static/themes/minecraft.js", variants: false },
  };
  const KEY = { theme: "ats-theme", variant: "ats-variant", motion: "ats-motion" };
  const hooks = {};          // id -> { mount, unmount }
  const mounted = {};        // id -> bool
  const cssLoaded = {};
  const jsLoaded = {};
  const root = document.documentElement;

  function get(k, d) { try { return localStorage.getItem(k) || d; } catch (e) { return d; } }
  function set(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }

  function ensureCss(id) {
    const t = REGISTRY[id];
    if (!t || !t.css || cssLoaded[id]) return;
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = t.css;
    link.dataset.theme = id;
    document.head.appendChild(link);
    cssLoaded[id] = true;
  }

  function ensureJs(id) {
    return new Promise((resolve) => {
      const t = REGISTRY[id];
      if (!t || !t.js || jsLoaded[id]) return resolve();
      const s = document.createElement("script");
      s.src = t.js;
      s.onload = () => { jsLoaded[id] = true; resolve(); };
      s.onerror = () => resolve();
      document.head.appendChild(s);
    });
  }

  // --- synchronous head pass: apply stored prefs + inject active CSS early ---
  const prefersReduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  let theme = get(KEY.theme, "modern");
  if (!REGISTRY[theme]) theme = "modern";
  const variant = get(KEY.variant, "dark");
  const motion = get(KEY.motion, prefersReduced ? "reduced" : "full");
  root.dataset.theme = theme;
  root.dataset.variant = variant;
  root.dataset.motion = motion;
  ensureCss(theme);

  async function applyTheme(id) {
    if (!REGISTRY[id]) return;
    const prev = root.dataset.theme;
    if (prev && prev !== id && hooks[prev] && mounted[prev] && hooks[prev].unmount) {
      try { hooks[prev].unmount(); } catch (e) {}
      mounted[prev] = false;
    }
    root.dataset.theme = id;
    set(KEY.theme, id);
    ensureCss(id);
    await ensureJs(id);
    if (hooks[id] && !mounted[id] && hooks[id].mount) {
      try { hooks[id].mount(document.body); mounted[id] = true; } catch (e) {}
    }
    reflectControls();
  }
  function setVariant(v) { root.dataset.variant = v; set(KEY.variant, v); reflectControls(); }
  function setMotion(m)  { root.dataset.motion  = m; set(KEY.motion, m);  reflectControls(); }

  function reflectControls() {
    const t = root.dataset.theme, v = root.dataset.variant, m = root.dataset.motion;
    document.querySelectorAll("#segTheme button").forEach((b) => b.classList.toggle("sel", b.dataset.theme === t));
    document.querySelectorAll("#segVariant button").forEach((b) => b.classList.toggle("sel", b.dataset.variant === v));
    document.querySelectorAll("#segMotion button").forEach((b) => b.classList.toggle("sel", b.dataset.motion === m));
    const gv = document.getElementById("grpVariant");
    if (gv) gv.style.display = (REGISTRY[t] && REGISTRY[t].variants) ? "" : "none";
  }

  function wire() {
    const btn = document.getElementById("paletteBtn");
    const pop = document.getElementById("palettePop");
    if (btn && pop) {
      btn.addEventListener("click", (e) => { e.stopPropagation(); pop.classList.toggle("open"); });
      document.addEventListener("click", (e) => { if (!pop.contains(e.target) && e.target !== btn) pop.classList.remove("open"); });
    }
    document.querySelectorAll("#segTheme button").forEach((b) => b.onclick = () => applyTheme(b.dataset.theme));
    document.querySelectorAll("#segVariant button").forEach((b) => b.onclick = () => setVariant(b.dataset.variant));
    document.querySelectorAll("#segMotion button").forEach((b) => b.onclick = () => setMotion(b.dataset.motion));
    reflectControls();
    // mount the active theme's JS hook (animated bg / cursor effects), if any
    ensureJs(theme).then(() => {
      if (hooks[theme] && !mounted[theme] && hooks[theme].mount) {
        try { hooks[theme].mount(document.body); mounted[theme] = true; } catch (e) {}
      }
    });
  }

  window.ATSTheme = {
    define: (id, hook) => {
      hooks[id] = hook;
      // if this theme is already active and DOM is ready, mount now
      if (root.dataset.theme === id && document.body && !mounted[id] && hook.mount) {
        try { hook.mount(document.body); mounted[id] = true; } catch (e) {}
      }
    },
    apply: applyTheme, setVariant, setMotion, registry: REGISTRY,
  };

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", wire);
  else wire();
})();
