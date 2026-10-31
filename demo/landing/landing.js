// Landing page: scroll-driven "How it works" steps with an archive animation, small card visuals, score chart.
(function () {
  "use strict";
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const C = { bg: "#0d1012", dim: "#2a3034", dot: "#5d656b", lit: "#9aa1a7", cream: "#f9f5ea", green: "#4fc13e",
              violet: "#8c7dff", muted: "#80868c", ink: "#0e1113" };
  const ease = (t) => (t < 0 ? 0 : t > 1 ? 1 : 1 - Math.pow(1 - t, 3));
  const clamp = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v));

  // ---------------------------------------------------------------- archive stage (200 conversations)
  // The cat question from the test set: its three evidence sessions and the one Reactor cited.
  const CAT = { history: "h_d99a2da8f8ee", sent: ["s_af842296e994", "s_38f2e98f38bc", "s_651a8bb6626d"], cited: "s_af842296e994",
                dates: ["28 May", "1 Jun", "19 Jul"] };
  const COLS = 20, N = 200;
  const stageEl = document.querySelector(".stage");
  const cv = document.getElementById("archive");
  const cap = document.querySelector(".stage-cap");
  const CAPS = [
    ["“What is my cat's name?”", "a fact about me"],
    ["searching 200 conversations", "keyword + meaning"],
    [`3 passages · ${CAT.dates.join(" · ")}`, "3 of 200"],
    ["Reactor cites 1 session", "0.1% read"],
    ["“What is my dog's name?”", "<b>Not in memory</b>"],
  ];
  let dots = [], sentIdx = [2, 3, 7], citedIdx = 2, decoys = [], candidates = [];
  let step = -1, stepT0 = performance.now(), stageVisible = false, raf = 0;

  function rng(seed) { return () => ((seed = (seed * 1664525 + 1013904223) >>> 0) / 4294967296); }

  function buildDots(sizes) {
    const r = rng(7);
    let lens = Array.from({ length: N }, () => 4000 + r() * 14000);
    const h = sizes && sizes[CAT.history];
    if (h) {
      const ids = Object.keys(h.sessions);
      if (ids.length) {
        lens = Array.from({ length: N }, (_, i) => h.sessions[ids[i % ids.length]]);
        const pos = CAT.sent.map((id) => ids.indexOf(id));
        if (pos.every((p) => p >= 0 && p < N)) { sentIdx = pos; citedIdx = ids.indexOf(CAT.cited); }
      }
    }
    const max = Math.max(...lens);
    dots = lens.map((l) => ({ w: 0.35 + 0.65 * Math.sqrt(l / max), seed: r() }));
    candidates = [...sentIdx];
    while (candidates.length < 14) { const k = Math.floor(r() * N); if (!candidates.includes(k)) candidates.push(k); }
    decoys = [candidates[5], candidates[9]];
    layout();
  }

  let W = 0, H = 0, dpr = 1, cell = 0, ox = 0, oy = 0, rows = Math.ceil(N / COLS);
  function layout() {
    if (!cv) return;
    const r = cv.getBoundingClientRect();
    dpr = Math.min(2, window.devicePixelRatio || 1);
    W = r.width; H = r.height;
    cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr);
    const padB = 64;
    cell = Math.min((W - 48) / COLS, (H - 40 - padB) / rows);
    ox = (W - cell * COLS) / 2; oy = Math.max(24, (H - padB - cell * rows) / 2);
    draw(performance.now());
  }

  function draw(now) {
    if (!cv || !dots.length) return;
    const ctx = cv.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, W, H);
    const t = reduced ? 1 : ease((now - stepT0) / 1100);
    const loop = reduced ? 0.5 : ((now - stepT0) / 2600) % 1;
    // fine halftone screen under the dots
    ctx.fillStyle = "rgba(255,255,255,0.035)";
    const g = cell / 3;
    for (let y = oy - cell / 2; y < oy + rows * cell; y += g)
      for (let x = ox; x < ox + COLS * cell; x += g) { ctx.beginPath(); ctx.arc(x, y, 0.8, 0, 6.283); ctx.fill(); }
    for (let i = 0; i < N; i++) {
      const cx = ox + (i % COLS + 0.5) * cell, cy = oy + (Math.floor(i / COLS) + 0.5) * cell;
      const d = dots[i];
      let r = (cell * 0.36) * d.w, col = C.dot, alpha = 1, glow = 0, ring = null;
      const isSent = sentIdx.includes(i), isCand = candidates.includes(i);
      if (step === 0) { col = C.dot; alpha = 0.55 + 0.25 * Math.sin(now / 900 + d.seed * 6); }
      else if (step === 1) {
        const front = loop * (COLS + 6) - 3, dx = (i % COLS) - front;
        const near = Math.exp(-dx * dx / 4);
        col = isCand && dx < 0 ? C.green : C.lit;
        alpha = 0.35 + 0.65 * near + (isCand && dx < 0 ? 0.25 : 0);
        if (isCand && dx < 0) glow = 0.25;
      } else if (step === 2 || step === 3) {
        if (isSent) { col = C.green; alpha = 1; glow = t; r *= 1 + 0.25 * t; }
        else { col = C.dot; alpha = 0.3 + 0.2 * (1 - t) * (isCand ? 1 : 0); }
        if (step === 3 && i === citedIdx) ring = { col: C.cream, a: t };
      } else if (step === 4) {
        col = C.dot; alpha = 0.32;
        if (decoys.includes(i)) { ring = { col: C.violet, a: 0.35 + 0.65 * t }; alpha = 0.75; col = C.lit; }
      }
      if (glow > 0) {
        ctx.fillStyle = "rgba(79,193,62," + (0.12 * glow).toFixed(3) + ")";
        for (let k = 0; k < 10; k++) {
          const a = (k / 10) * 6.283, rr = r * 2.1;
          ctx.beginPath(); ctx.arc(cx + Math.cos(a) * rr, cy + Math.sin(a) * rr, r * 0.28, 0, 6.283); ctx.fill();
        }
      }
      ctx.globalAlpha = clamp(alpha);
      ctx.fillStyle = col;
      ctx.beginPath(); ctx.arc(cx, cy, r, 0, 6.283); ctx.fill();
      ctx.globalAlpha = 1;
      if (ring && ring.a > 0) {
        ctx.strokeStyle = ring.col; ctx.globalAlpha = ring.a; ctx.lineWidth = 2;
        ctx.beginPath(); ctx.arc(cx, cy, r + 5, 0, 6.283); ctx.stroke(); ctx.globalAlpha = 1;
      }
    }
  }

  function frame(now) {
    raf = 0;
    if (!stageVisible || document.hidden) return;
    draw(now);
    if (!reduced) raf = requestAnimationFrame(frame);
  }
  const kick = () => { if (!raf && stageVisible) raf = requestAnimationFrame(frame); };

  // ---------------------------------------------------------------- steps (scroll-driven when the section is sticky)
  const hiw = document.getElementById("how");
  const sticky = hiw && hiw.querySelector(".hiw-sticky");
  const steps = hiw ? [...hiw.querySelectorAll(".step")] : [];
  const isSticky = () => sticky && getComputedStyle(sticky).position === "sticky";

  function setStep(i, local) {
    if (i !== step) {
      step = i; stepT0 = performance.now();
      steps.forEach((s, k) => {
        s.classList.toggle("on", k === i);
        s.querySelector("button").setAttribute("aria-expanded", String(k === i));
      });
      if (cap) { const [a, b] = CAPS[i]; cap.innerHTML = `<span>${a}</span><span>${b}</span>`; }
      kick();
      if (reduced) draw(performance.now());
    }
    steps.forEach((s, k) => s.style.setProperty("--p", k === i ? String(local) : "0"));
  }

  function onScroll() {
    if (!hiw || !isSticky()) return;
    const r = hiw.getBoundingClientRect();
    const span = hiw.offsetHeight - innerHeight;
    const p = clamp(-r.top / Math.max(1, span));
    const x = p * steps.length;
    const i = Math.min(steps.length - 1, Math.floor(x));
    setStep(i, clamp(x - i));
  }

  steps.forEach((s, i) => s.querySelector("button").addEventListener("click", () => {
    if (isSticky()) {
      const top = hiw.getBoundingClientRect().top + scrollY;
      const span = hiw.offsetHeight - innerHeight;
      scrollTo({ top: top + ((i + 0.08) / steps.length) * span, behavior: reduced ? "auto" : "smooth" });
    } else setStep(i, 1);
  }));
  // mobile / short screens: no scroll pinning, so advance on a timer while the stage is on screen
  setInterval(() => { if (!isSticky() && stageVisible && !reduced && !document.hidden) setStep((step + 1) % steps.length, 1); }, 3800);

  if (cv) {
    new ResizeObserver(layout).observe(cv);
    new IntersectionObserver((es) => { stageVisible = es[0].isIntersecting; kick(); }, { rootMargin: "100px" }).observe(stageEl);
    document.addEventListener("visibilitychange", kick);
    buildDots(null);
    fetch("sizes.json").then((r) => (r.ok ? r.json() : null)).then(buildDots).catch(() => {});
    if (cap) cap.innerHTML = `<span>${CAPS[0][0]}</span><span>${CAPS[0][1]}</span>`;
  }
  // nav turns dark-on-cream while a light section sits under it
  const nav = document.querySelector(".nav");
  const lights = [...document.querySelectorAll(".light")];
  function navTone() {
    const y = (nav ? nav.offsetHeight : 68) / 2;
    const on = lights.some((s) => { const r = s.getBoundingClientRect(); return r.top <= y && r.bottom >= y; });
    if (nav) nav.classList.toggle("on-light", on);
  }
  addEventListener("scroll", navTone, { passive: true });
  navTone();
  addEventListener("scroll", onScroll, { passive: true });
  addEventListener("resize", onScroll);
  onScroll();
  if (step < 0) setStep(0, isSticky() ? 0 : 1);

  // ---------------------------------------------------------------- card visuals (inline SVG, pixel style)
  const NS = "http://www.w3.org/2000/svg";
  const el = (tag, attrs, text) => {
    const n = document.createElementNS(NS, tag);
    for (const k in attrs) n.setAttribute(k, attrs[k]);
    if (text != null) n.textContent = text;
    return n;
  };
  function screen(svg, w, h, color, step = 12) {
    for (let y = step / 2; y < h; y += step) for (let x = step / 2; x < w; x += step)
      svg.appendChild(el("rect", { x: x - 1, y: y - 1, width: 2, height: 2, fill: color }));
  }
  const VIZ = {
    change(svg) {
      screen(svg, 400, 240, "rgba(255,255,255,0.05)");
      svg.appendChild(el("line", { x1: 40, y1: 150, x2: 360, y2: 150, stroke: "#33393e", "stroke-width": 1 }));
      const months = ["Jun", "Jul", "Aug", "Sep", "Oct"];
      months.forEach((m, i) => {
        const x = 50 + i * 75;
        svg.appendChild(el("rect", { x: x - 2, y: 148, width: 4, height: 4, fill: "#5d656b" }));
        svg.appendChild(el("text", { x, y: 176, "text-anchor": "middle", fill: "#80868c", "font-family": "IBM Plex Mono, monospace", "font-size": 11 }, m));
      });
      svg.appendChild(el("rect", { x: 194, y: 138, width: 12, height: 12, fill: "#5d656b" }));
      svg.appendChild(el("rect", { x: 189, y: 133, width: 22, height: 22, fill: "none", stroke: "#f9f5ea", "stroke-width": 1.2 }));
      svg.appendChild(el("text", { x: 200, y: 118, "text-anchor": "middle", fill: "#80868c", "font-family": "Newsreader, Georgia, serif", "font-size": 30, "font-weight": 300 }, "three"));
      svg.appendChild(el("rect", { x: 269, y: 138, width: 12, height: 12, fill: "#4fc13e" }));
      svg.appendChild(el("rect", { x: 264, y: 133, width: 22, height: 22, fill: "none", stroke: "#f9f5ea", "stroke-width": 1.2 }));
      svg.appendChild(el("text", { x: 275, y: 118, "text-anchor": "middle", fill: "#f9f5ea", "font-family": "Newsreader, Georgia, serif", "font-size": 30, "font-weight": 300 }, "four"));
      svg.appendChild(el("text", { x: 350, y: 118, "text-anchor": "middle", fill: "#80868c", "font-family": "Newsreader, Georgia, serif", "font-size": 30, "font-weight": 300 }, "?"));
      svg.appendChild(el("rect", { x: 344, y: 138, width: 12, height: 12, fill: "none", stroke: "#8c7dff", "stroke-width": 1.2 }));
    },
    needle(svg) {
      screen(svg, 400, 240, "rgba(255,255,255,0.05)");
      const r = rng(11);
      for (let i = 0; i < 11; i++) {
        const y = 26 + i * 18, w = 120 + r() * 200, hit = i === 6;
        svg.appendChild(el("rect", { x: 40, y, width: hit ? 150 : w, height: 7, fill: hit ? "#4fc13e" : "#2a3034" }));
        if (hit) svg.appendChild(el("text", { x: 204, y: y + 8, fill: "#f9f5ea", "font-family": "Newsreader, Georgia, serif", "font-size": 22, "font-weight": 300 }, "Instant Pot"));
      }
    },
    absent(svg) {
      const r = rng(5);
      const cols = 16, rowsN = 7, gx = 22, gy = 22, x0 = 35, y0 = 30;
      const marks = [3 * cols + 4, 1 * cols + 12];
      for (let j = 0; j < rowsN; j++) for (let i = 0; i < cols; i++) {
        const k = j * cols + i, rr = 2.2 + r() * 3.4;
        svg.appendChild(el("circle", { cx: x0 + i * gx, cy: y0 + j * gy, r: rr, fill: "#3a4146", opacity: 0.8 }));
        if (marks.includes(k)) svg.appendChild(el("circle", { cx: x0 + i * gx, cy: y0 + j * gy, r: rr + 6, fill: "none", stroke: "#8c7dff", "stroke-width": 1.2 }));
      }
      svg.appendChild(el("text", { x: x0 + 4 * gx + 14, y: y0 + 3 * gy + 22, fill: "#8c7dff", "font-family": "IBM Plex Mono, monospace", "font-size": 11 }, "a friend's puppy"));
      svg.appendChild(el("text", { x: x0 + 12 * gx - 14, y: y0 + 1 * gy - 12, "text-anchor": "end", fill: "#8c7dff", "font-family": "IBM Plex Mono, monospace", "font-size": 11 }, "a therapy dog"));
      svg.appendChild(el("text", { x: 200, y: 222, "text-anchor": "middle", fill: "#f9f5ea", "font-family": "Newsreader, Georgia, serif", "font-size": 24, "font-weight": 300 }, "Not in memory"));
    },
  };
  document.querySelectorAll(".viz[data-viz]").forEach((box) => {
    const svg = el("svg", { viewBox: "0 0 400 240", preserveAspectRatio: "xMidYMid meet" });
    VIZ[box.dataset.viz](svg);
    box.appendChild(svg);
  });

  // pixel glyphs for the use cases (6x6 grids; G = green accent)
  const GLYPHS = {
    support: ["XXXXXX", "X....X", "X.GG.X", "X....X", "XXXXXX", ".X...."],
    health: ["..XX..", "..XX..", "XXGGXX", "XXGGXX", "..XX..", "..XX.."],
    agent: ["..XX..", "..XX..", "......", ".XXXX.", "X.GG.X", "X....X"],
    team: ["X.XX.X", "X.XX.X", "......", "XXGGXX", "X....X", "X....X"],
  };
  document.querySelectorAll(".glyph[data-glyph]").forEach((box) => {
    const svg = el("svg", { viewBox: "0 0 36 36" });
    GLYPHS[box.dataset.glyph].forEach((row, y) => [...row].forEach((ch, x) => {
      if (ch !== ".") svg.appendChild(el("rect", { x: x * 6, y: y * 6, width: 5, height: 5, fill: ch === "G" ? "#2f8f22" : "#0e1113" }));
    }));
    box.appendChild(svg);
  });

  // ---------------------------------------------------------------- score climb (pixel bars)
  const climb = document.getElementById("climb");
  if (climb) {
    const SCORES = [42.9, 73.4, 80.4, 86.0, 87.1];
    let shown = reduced ? 1 : 0, t0 = 0;
    const paint = (now) => {
      const r = climb.getBoundingClientRect(), d = Math.min(2, devicePixelRatio || 1);
      climb.width = Math.round(r.width * d); climb.height = Math.round(r.height * d);
      const ctx = climb.getContext("2d");
      ctx.setTransform(d, 0, 0, d, 0, 0);
      const p = shown >= 1 ? 1 : ease((now - t0) / 1400);
      const colW = r.width / SCORES.length, px = 8, gap = 2, top = 46, usable = r.height - top;
      SCORES.forEach((s, i) => {
        const cols = Math.max(3, Math.floor((colW * 0.42) / (px + gap)));
        const x0 = i * colW + (colW - cols * (px + gap)) / 2;
        const rowsN = Math.floor((usable * (s / 100) * p) / (px + gap));
        const last = i === SCORES.length - 1;
        for (let rr = 0; rr < rowsN; rr++) for (let c = 0; c < cols; c++) {
          const mix = rr / Math.max(1, usable / (px + gap));
          ctx.fillStyle = last ? (mix > 0.6 ? "#4fc13e" : "#3d8f30") : `rgba(140,125,255,${0.25 + 0.5 * mix})`;
          ctx.fillRect(x0 + c * (px + gap), r.height - (rr + 1) * (px + gap), px, px);
        }
        ctx.fillStyle = last ? "#f9f5ea" : "#b9bdc1";
        ctx.font = `300 ${Math.round(Math.min(26, colW * 0.3))}px Newsreader, Georgia, serif`;
        ctx.textAlign = "center";
        const yTop = r.height - rowsN * (px + gap) - 12;
        ctx.globalAlpha = p;
        ctx.fillText(s.toFixed(1), i * colW + colW / 2, yTop);
        ctx.globalAlpha = 1;
      });
      if (p < 1) requestAnimationFrame(paint); else shown = 1;
    };
    const go = () => document.fonts.ready.then(() => { t0 = performance.now(); requestAnimationFrame(paint); });
    new IntersectionObserver((es, io) => { if (es[0].isIntersecting) { io.disconnect(); go(); } }, { threshold: 0.3 }).observe(climb);
    new ResizeObserver(() => { if (shown >= 1) paint(performance.now()); }).observe(climb);
  }

  // ---------------------------------------------------------------- plugin code card: tabs + copy
  const tabs = [...document.querySelectorAll(".code-tabs [role=tab]")];
  const copyBtn = document.querySelector(".code-card .copy");
  function selectTab(tab, focus) {
    tabs.forEach((t) => {
      const on = t === tab;
      t.setAttribute("aria-selected", String(on)); t.tabIndex = on ? 0 : -1;
      document.getElementById(t.getAttribute("aria-controls")).hidden = !on;
    });
    if (focus) tab.focus();
    if (copyBtn) copyBtn.textContent = "Copy";
  }
  tabs.forEach((t, i) => {
    t.addEventListener("click", () => selectTab(t));
    t.addEventListener("keydown", (e) => {
      if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
        e.preventDefault();
        selectTab(tabs[(i + (e.key === "ArrowRight" ? 1 : tabs.length - 1)) % tabs.length], true);
      }
    });
  });
  if (copyBtn) copyBtn.addEventListener("click", async () => {
    const panel = document.querySelector(".code-card pre:not([hidden]) code");
    try { await navigator.clipboard.writeText(panel.textContent); copyBtn.textContent = "Copied"; }
    catch { const r = document.createRange(); r.selectNodeContents(panel); getSelection().removeAllRanges(); getSelection().addRange(r); copyBtn.textContent = "Selected"; }
    setTimeout(() => { copyBtn.textContent = "Copy"; }, 1800);
  });
})();
