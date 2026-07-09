/* Minecraft theme behaviour: block-break particle puffs on click + a faint
 * floating-voxel backdrop. Registers mount/unmount with the theme engine so it
 * activates only while the Minecraft theme is on, and respects reduce-motion. */
(function () {
  if (!window.ATSTheme) return;

  let onClick = null;
  let layer = null;

  function motionOn() { return document.documentElement.dataset.motion !== "reduced"; }

  function puff(x, y) {
    if (!motionOn()) return;
    const colors = ["#5fa632", "#7e5a33", "#9b6a3c", "#4a4a4a", "#8a8a8a"];
    for (let i = 0; i < 8; i++) {
      const b = document.createElement("div");
      const size = 4 + Math.floor(Math.random() * 5);
      b.style.cssText = `position:fixed;left:${x}px;top:${y}px;width:${size}px;height:${size}px;
        background:${colors[i % colors.length]};z-index:200;pointer-events:none;image-rendering:pixelated;
        box-shadow:inset 1px 1px 0 rgba(255,255,255,.3), inset -1px -1px 0 rgba(0,0,0,.4)`;
      layer.appendChild(b);
      const dx = (Math.random() - 0.5) * 90, dy = -20 - Math.random() * 60;
      const t0 = performance.now(), life = 480 + Math.random() * 220;
      (function fall(now) {
        const p = (now - t0) / life;
        if (p >= 1) { b.remove(); return; }
        b.style.transform = `translate(${dx * p}px, ${dy * p + 140 * p * p}px) rotate(${p * 90}deg)`;
        b.style.opacity = String(1 - p);
        requestAnimationFrame(fall);
      })(t0);
    }
  }

  ATSTheme.define("minecraft", {
    mount(root) {
      layer = document.createElement("div");
      layer.id = "mcLayer";
      layer.style.cssText = "position:fixed;inset:0;pointer-events:none;z-index:200";
      root.appendChild(layer);
      onClick = (e) => puff(e.clientX, e.clientY);
      window.addEventListener("pointerdown", onClick, { passive: true });
    },
    unmount() {
      if (onClick) window.removeEventListener("pointerdown", onClick);
      if (layer) layer.remove();
      layer = null; onClick = null;
    },
  });
})();
