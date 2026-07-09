/* Liquid Glass wallpaper engine.
 *
 * Registers a theme hook via ATSTheme.define(). On mount it fetches the
 * wallpaper list from /api/wallpapers (drop any image into static/wallpapers/
 * and it appears — no restart), picks one at random, and cross-fades between
 * two fixed layers behind the frosted-glass panels. A legibility scrim keeps
 * text readable over any photo. On unmount everything is torn down. Rotation
 * and cross-fade are disabled under reduced motion; the CSS gradient in
 * liquidglass.css is the fallback when the folder is empty or JS is off.
 */
(function () {
  const ATS = window.ATSTheme;
  if (!ATS) return;

  const ROTATE_MS = 45000;
  const root = document.documentElement;
  let layers = [];      // two crossfade divs
  let scrim = null;
  let timer = null;
  let list = [];        // wallpaper URLs
  let cur = 0;          // index of the currently-visible layer (0/1)
  let idx = 0;          // index into `list`
  let active = false;   // guards the async fetch against a fast toggle-away

  function reducedMotion() {
    return root.dataset.motion === "reduced";
  }

  async function fetchList() {
    try {
      const r = await fetch("/api/wallpapers", { cache: "no-store" });
      if (!r.ok) return [];
      const j = await r.json();
      return Array.isArray(j.wallpapers) ? j.wallpapers : [];
    } catch (e) {
      return [];
    }
  }

  function ensureDom() {
    if (scrim) return;
    for (let i = 0; i < 2; i++) {
      const d = document.createElement("div");
      d.className = "lg-wallpaper";
      document.body.appendChild(d);
      layers.push(d);
    }
    scrim = document.createElement("div");
    scrim.className = "lg-scrim";
    document.body.appendChild(scrim);
  }

  function show(url) {
    if (!layers.length) return;
    const next = layers[(cur + 1) % 2];
    const curr = layers[cur];
    const img = new Image();       // preload so the fade starts on a ready bitmap
    img.onload = () => {
      if (!active) return;
      next.style.backgroundImage = 'url("' + url + '")';
      next.style.opacity = "1";
      curr.style.opacity = "0";
      cur = (cur + 1) % 2;
    };
    img.onerror = () => {};        // keep the current wallpaper on a bad file
    img.src = url;
  }

  function rotate() {
    if (list.length < 2) return;
    idx = (idx + 1) % list.length;
    show(list[idx]);
  }

  async function mount() {
    active = true;
    ensureDom();
    list = await fetchList();
    if (!active) return;           // toggled away while fetching
    if (list.length) {
      idx = Math.floor(Math.random() * list.length);
      show(list[idx]);
      if (!reducedMotion() && list.length > 1) {
        timer = setInterval(rotate, ROTATE_MS);
      }
    }
    // else: the CSS gradient fallback stays visible.
  }

  function unmount() {
    active = false;
    if (timer) { clearInterval(timer); timer = null; }
    layers.forEach((d) => d.remove());
    layers = [];
    if (scrim) { scrim.remove(); scrim = null; }
  }

  ATS.define("liquidglass", { mount, unmount });
})();
