// Pixel-mosaic background: soft flowing ribbons (violet left, green right) rendered one pixel per cell into a tiny
// canvas, scaled up with image-rendering: pixelated. Each canvas is sized to a whole number of 6px cells so the CSS 1px
// grid overlay lines up. Ordered (Bayer) dithering gives the mosaic texture. ~20 fps, paused off-screen or hidden.
// Usage: <canvas class="mosaic" data-variant="hero|cta"> (also picks up #mosaic for older pages).
// This is the fallback for browsers without WebGL; hero-gl.js renders the same canvases when it can.
(function () {
  const CELL = 6;
  const BG = [13, 16, 18];
  const VIOLET = [78, 58, 214];
  const GREEN = [46, 170, 40];
  const B4 = [0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5].map((v) => (v + 0.5) / 16);
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const clamp = (v) => (v < 0 ? 0 : v > 1 ? 1 : v);

  function ribbon(x, y, cx, slope, amp, freq, phase, width) {
    const center = cx + slope * y + amp * Math.sin(y * freq + phase) + amp * 0.45 * Math.sin(y * freq * 2.3 - phase * 1.4);
    const d = (x - center) / width;
    return Math.exp(-d * d);
  }

  const FIELDS = {
    hero(x, y, t) {
      const fade = clamp((1.02 - y) / 0.55);
      const v = 0.75 * ribbon(x, y, 0.03, 0.30, 0.045, 3.4, t * 0.32, 0.06) * (0.55 + 0.45 * Math.sin(y * 5.5 - t * 0.5))
              + 0.45 * ribbon(x, y, 0.13, 0.22, 0.04, 4.6, t * 0.26 + 1.7, 0.04) * (0.5 + 0.5 * Math.sin(y * 4 + t * 0.4 + 1));
      const g = 0.7 * ribbon(y, x, 0.62, -0.55, 0.045, 4.2, t * 0.3 + 0.6, 0.07) * clamp((x - 0.5) / 0.22)
                    * (0.55 + 0.45 * Math.sin(x * 7 - t * 0.45))
              + 0.35 * ribbon(x, y, 0.97, -0.2, 0.035, 3.6, t * 0.22 + 2.4, 0.045);
      return [v * fade, g * fade];
    },
    cta(x, y, t) {
      // two strands crossing on the right half; the left side stays dark for the text
      const side = clamp((x - 0.35) / 0.3);
      const v = 0.7 * ribbon(x, y, 0.62, 0.25, 0.05, 4.0, t * 0.3, 0.07) * (0.5 + 0.5 * Math.sin(y * 6 - t * 0.5));
      const g = 0.65 * ribbon(x, y, 0.9, -0.3, 0.05, 3.2, t * 0.26 + 1.2, 0.08) * (0.5 + 0.5 * Math.sin(y * 5 + t * 0.4));
      return [v * side, g * side];
    },
  };

  function attach(c) {
    const ctx = c.getContext("2d", { alpha: false });
    const field = FIELDS[c.dataset.variant] || FIELDS.hero;
    const host = c.parentElement;
    let W = 0, H = 0, img, visible = true, raf = 0, last = 0;

    function size() {
      const r = host.getBoundingClientRect();
      W = Math.max(1, Math.ceil(r.width / CELL));
      H = Math.max(1, Math.ceil(r.height / CELL));
      c.width = W; c.height = H;
      c.style.width = W * CELL + "px"; c.style.height = H * CELL + "px";
      c.style.right = "auto"; c.style.bottom = "auto";
      img = ctx.createImageData(W, H);
      draw(performance.now());
    }

    function draw(now) {
      const t = reduced ? 0 : now / 1000;
      const d = img.data;
      for (let j = 0; j < H; j++) {
        const y = j / H;
        for (let i = 0; i < W; i++) {
          const x = i / W;
          let [v, g] = field(x, y, t);
          const shimmer = 0.85 + 0.15 * Math.sin(i * 0.9 + j * 1.3 + t * 1.6);
          v *= shimmer; g *= shimmer;
          const th = B4[(j & 3) * 4 + (i & 3)];
          const vv = Math.min(1, Math.floor(v * 5 + th) / 5) * 0.62;
          const gg = Math.min(1, Math.floor(g * 5 + th) / 5) * 0.6;
          const k = (j * W + i) * 4;
          d[k] = BG[0] + VIOLET[0] * vv + GREEN[0] * gg;
          d[k + 1] = BG[1] + VIOLET[1] * vv + GREEN[1] * gg;
          d[k + 2] = BG[2] + VIOLET[2] * vv + GREEN[2] * gg;
          d[k + 3] = 255;
        }
      }
      ctx.putImageData(img, 0, 0);
    }

    function loop(now) {
      raf = 0;
      if (!visible || document.hidden) return;
      if (now - last > 50) { last = now; draw(now); }
      raf = requestAnimationFrame(loop);
    }
    const start = () => { if (!raf && !reduced && visible && !document.hidden) raf = requestAnimationFrame(loop); };

    new ResizeObserver(size).observe(host);
    new IntersectionObserver((es) => { visible = es[0].isIntersecting; start(); }).observe(host);
    document.addEventListener("visibilitychange", start);
    size();
    start();
  }

  // hero-gl.js (loaded first) marks the canvases it renders with data-gl; this 2D version is the fallback
  document.querySelectorAll("canvas.mosaic:not([data-gl]), canvas#mosaic:not([data-gl])").forEach(attach);
})();
