/* Pixel engine: sprites, tiles, the crystal Oracle, and chiptune sparkles. No images: everything is drawn. */
(function () {
  "use strict";
  const PX = {};

  // seeded rng so the tiles look the same on every load
  function rng(seed) {
    let s = seed >>> 0;
    return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
  }
  PX.hash = function (str) {
    let h = 2166136261;
    for (let i = 0; i < str.length; i++) { h ^= str.charCodeAt(i); h = Math.imul(h, 16777619); }
    return h >>> 0;
  };

  PX.sprite = function (map, pal, scale) {
    scale = scale || 1;
    const h = map.length, w = Math.max.apply(null, map.map(r => r.length));
    const c = document.createElement("canvas");
    c.width = w * scale; c.height = h * scale;
    const g = c.getContext("2d");
    map.forEach((row, y) => {
      for (let x = 0; x < row.length; x++) {
        const col = pal[row[x]];
        if (col) { g.fillStyle = col; g.fillRect(x * scale, y * scale, scale, scale); }
      }
    });
    return c;
  };
  PX.url = (map, pal, scale) => PX.sprite(map, pal, scale).toDataURL();

  // ---------- tiles ----------
  PX.stoneTile = function () {
    const c = document.createElement("canvas"); c.width = 32; c.height = 32;
    const g = c.getContext("2d"), r = rng(7);
    g.fillStyle = "#130e22"; g.fillRect(0, 0, 32, 32);
    const bricks = [[0, 0, 15, 7], [16, 0, 16, 7], [-8, 8, 15, 7], [8, 8, 15, 7], [24, 8, 15, 7],
      [0, 16, 15, 7], [16, 16, 16, 7], [-8, 24, 15, 7], [8, 24, 15, 7], [24, 24, 15, 7]];
    const tones = ["#1d1631", "#201936", "#1a142d", "#231b3a"];
    bricks.forEach(([x, y, w, h]) => {
      g.fillStyle = tones[Math.floor(r() * tones.length)];
      g.fillRect(x, y, w, h);
      g.fillStyle = "#29213f"; g.fillRect(x, y, w, 1);
      for (let i = 0; i < 5; i++) { g.fillStyle = r() > .5 ? "#2a2243" : "#161029"; g.fillRect(x + Math.floor(r() * w), y + 1 + Math.floor(r() * (h - 1)), 1, 1); }
    });
    // moss specks in the mortar
    for (let i = 0; i < 6; i++) { g.fillStyle = r() > .5 ? "#2f4a26" : "#253d20"; g.fillRect(Math.floor(r() * 32), [7, 15, 23, 31][Math.floor(r() * 4)], 2, 1); }
    return c.toDataURL();
  };
  PX.woodTile = function (base, dark, light) {
    const c = document.createElement("canvas"); c.width = 48; c.height = 12;
    const g = c.getContext("2d"), r = rng(11);
    g.fillStyle = base; g.fillRect(0, 0, 48, 12);
    for (let y = 0; y < 12; y += 3) {
      g.fillStyle = dark;
      let x = Math.floor(r() * 10);
      while (x < 48) { const len = 6 + Math.floor(r() * 14); g.fillRect(x, y + Math.floor(r() * 2), len, 1); x += len + 4 + Math.floor(r() * 8); }
    }
    for (let i = 0; i < 10; i++) { g.fillStyle = light; g.fillRect(Math.floor(r() * 48), Math.floor(r() * 12), 2, 1); }
    g.fillStyle = dark; g.fillRect(Math.floor(r() * 40), 5, 2, 2);
    return c.toDataURL();
  };
  PX.mossTile = function () {
    const c = document.createElement("canvas"); c.width = 24; c.height = 6;
    const g = c.getContext("2d"), r = rng(3);
    for (let x = 0; x < 24; x++) {
      const h = Math.floor(r() * 4) + (r() > .8 ? 2 : 0);
      for (let y = 0; y < h; y++) { g.fillStyle = y === h - 1 ? "#9cc95a" : (y % 2 ? "#5f8d36" : "#4d7a2c"); g.fillRect(x, 5 - y, 1, 1); }
      if (r() > .9) { g.fillStyle = "#f4d36b"; g.fillRect(x, 5 - h, 1, 1); }
    }
    return c.toDataURL();
  };
  PX.parchTile = function () {
    const c = document.createElement("canvas"); c.width = 16; c.height = 16;
    const g = c.getContext("2d"), r = rng(5);
    g.fillStyle = "#efe0b6"; g.fillRect(0, 0, 16, 16);
    for (let i = 0; i < 22; i++) { g.fillStyle = r() > .5 ? "#e6d3a2" : "#f4e8c6"; g.fillRect(Math.floor(r() * 16), Math.floor(r() * 16), 1, 1); }
    return c.toDataURL();
  };

  // ---------- sprites ----------
  const WIZ_PAL = {
    H: "#4a2a86", h: "#6d44b8", S: "#ffd85e", F: "#f2c49b", E: "#24152e", B: "#eceaf6", b: "#b9b6d2",
    R: "#2f57a8", r: "#203c7a", G: "#e8b443", W: "#8b5a2b", O: "#8ff4ff", o: "#ffffff", K: "#3a2622", P: "#f29bb0",
  };
  const WIZ_BASE = [
    "..........HH.......",
    ".........HhH.......",
    "........HhhH.......",
    "........HhSH....O..",
    ".......HhhhH...OoO.",
    ".......HhhhhH...O..",
    "......HhhShhH...W..",
    "....HHHHHHHHHHH.W..",
    "......FFFFFF....W..",
    "......FEFFEF....W..",
    "......FPFFPF....W..",
    ".....BBFFFFBB...W..",
    "....RBBBBBBBBR.FW..",
    "...RRBBBBBBBBRRRW..",
    "...RRRBBbBBBRRR.W..",
    "..RRRRRBBBBRRRr.W..",
    "..RRRRRRBBRRRRr.W..",
    "..RRRRRRBbRRRRr.W..",
    "..RRRRRRRBRRRRr.W..",
    "..RRGRRRRRRRGRr.W..",
    ".RRRRRRRRRRRRRr.W..",
    ".RRRRRRRRRRRRRr.W..",
    ".GGGGGGGGGGGGGG.W..",
  ];
  const FEET = ["...KK.....KK....W..", "....KK...KK.....W..", "..KK.......KK...W.."];
  PX.wizardFrames = function (scale) {
    return FEET.map((f, i) => {
      const m = WIZ_BASE.slice();
      if (i === 1) { m[20] = "..RRRRRRRRRRRRr.W.."; m[21] = ".RRRRRRRRRRRRRRrW.."; }
      if (i === 2) { m[3] = "........HhSH...oOo."; m[4] = ".......HhhhH...OOO."; m[5] = ".......HhhhhH..oOo."; }
      m.push(f);
      return PX.sprite(m, WIZ_PAL, scale).toDataURL();
    });
  };

  const SEAL = [
    "....rrrrr....",
    "..rrRRRRRrr..",
    ".rRRRRdRRRRr.",
    ".rRRRdddRRRr.",
    "rRdddddddddRr",
    "rRRRdddddRRRr",
    "rRRRRdddRRRRr",
    "rRRRdRRRdRRRr",
    ".rRdRRRRRdRr.",
    ".rRRRRRRRRRr.",
    "..rrRRRRRrr..",
    "....rrrrr....",
  ];
  PX.sealURL = () => PX.url(SEAL, { r: "#6d1016", R: "#b8262f", d: "#ef6b63" }, 4);

  const FLAME = [
    [".....", "..Y..", ".YOY.", ".YOY.", "YOWOY", ".YWY."],
    ["..Y..", "..YY.", ".YOY.", "YOOY.", "YOWOY", ".YWY."],
    [".....", ".Y...", ".YYY.", ".YOOY", "YOWOY", ".YWY."],
  ];
  PX.flameSheet = function (scale) {
    const c = document.createElement("canvas"); c.width = 15 * scale; c.height = 6 * scale;
    const g = c.getContext("2d");
    FLAME.forEach((f, i) => g.drawImage(PX.sprite(f, { Y: "#ffb83a", O: "#ff7a1f", W: "#fff6c8" }, scale), i * 5 * scale, 0));
    return c.toDataURL();
  };

  // icons for the five kinds of questions (and the how-it-works panel)
  PX.ICONS = {
    ssu: { map: [
      "............",
      "..GGG.......",
      ".GgggG......",
      "GgG.GgGGGGGG",
      "GgG.GgggggGg",
      ".GgggG..G.G.",
      "..GGG...G.G.",
    ], pal: { G: "#f5c451", g: "#a8741c" } },
    ssa: { map: [
      ".WWWWWWWWW..",
      "WWWWWSWWWWW.",
      "WWWWSSSWWWW.",
      "WWWWWSWWWWW.",
      ".WWWWWWWWW..",
      "...WW.......",
      "..W.........",
    ], pal: { W: "#7fdcff", S: "#ffffff" } },
    multi: { map: [
      "M.M.M.M.....",
      "M.M.M.M...M.",
      "MMMMMMMMMM..",
      "M.M.M.MMM...",
      "M.M.MMM.M...",
      "M.MMM.M.M...",
      "MM..M.M.M...",
    ], pal: { M: "#9fe07a" } },
    ku: { map: [
      "GGGGGGGG",
      ".W....W.",
      ".WSSSSW.",
      "..WSSW..",
      "...WW...",
      "..W.SW..",
      ".W.SS.W.",
      ".WSSSSW.",
      "GGGGGGGG",
    ], pal: { G: "#d9a441", W: "#e8e2ff", S: "#ffcf6a" } },
    temporal: { map: [
      "...MMM...S",
      "..MM....SSS",
      ".MM......S",
      ".MM.......",
      ".MM...S...",
      "..MM......",
      "...MMM....",
    ], pal: { M: "#f0e2a0", S: "#ffffff" } },
    book: { map: [
      ".RRRRRRR.",
      "RRGGGGGRR",
      "RRRRRRRRR",
      "RRRWWWRRR",
      "RRRRRRRRR",
      "RRGGGGGRR",
      "RRRRRRRRR",
      "PPPPPPPPP",
    ], pal: { R: "#8c2f3c", G: "#f5c451", W: "#f3e3b8", P: "#efe0b6" } },
    quill: { map: [
      "........WW",
      ".......WWW",
      "......WWW.",
      ".....WWW..",
      "....WWW...",
      "...WWW....",
      "..BW......",
      ".B........",
      "B.........",
    ], pal: { W: "#f3f0ff", B: "#3a2a1a" } },
    eye: { map: [
      "...CCCC...",
      ".CC....CC.",
      "C..PPPP..C",
      "C..PWPP..C",
      ".CC....CC.",
      "...CCCC...",
    ], pal: { C: "#8ff4ff", P: "#b27bff", W: "#ffffff" } },
    sleep: { map: ["ZZZ", "..Z", ".Z.", "ZZZ"], pal: { Z: "#b8c2dc" } },
  };
  PX.icon = (k, scale) => { const i = PX.ICONS[k] || PX.ICONS.book; return PX.url(i.map, i.pal, scale || 3); };

  // ---------- the crystal Oracle ----------
  const ORACLE_PALS = {
    idle: ["#120c2c", "#24164f", "#3d2584", "#6a3fc2", "#a07af0", "#d9c6ff"],
    thinking: ["#061a33", "#0b3a6e", "#1269b0", "#22a9e0", "#7ff0ff", "#e8ffff"],
    answered: ["#2a1200", "#6b3608", "#b5651a", "#efa634", "#ffe08a", "#fffbe6"],
    abstain: ["#12151f", "#222838", "#363f57", "#566283", "#8592b4", "#c6cee6"],
    resting: ["#100c22", "#1c1538", "#2b2152", "#3f3172", "#5e4c9a", "#8f7fc4"],
  };
  const BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]];
  PX.Oracle = function (canvas) {
    const g = canvas.getContext("2d");
    const W = canvas.width, H = canvas.height;
    let state = "idle", flash = 0, last = 0;
    const self = {
      set(s) { if (s !== state) { state = s; if (s === "answered" || s === "abstain") flash = 1; } },
      get state() { return state; },
      draw(t) {
        if (t - last < 70) return; // ~14 fps: chunky, chiptune motion
        last = t;
        const pal = ORACLE_PALS[state] || ORACLE_PALS.idle;
        const speed = state === "thinking" ? 3.2 : state === "resting" ? 0.35 : state === "abstain" ? 0.5 : 0.9;
        const tt = t / 1000 * speed;
        g.clearRect(0, 0, W, H);
        const cx = W / 2, cy = 29, R = 22;
        // aura
        for (let y = 0; y < 58; y++) for (let x = 0; x < W; x++) {
          const d = Math.hypot(x - cx + .5, y - cy + .5);
          if (d >= R + 1 && d < R + 7) {
            const th = (1 - (d - R - 1) / 6) * (state === "thinking" ? 0.7 : 0.38) + flash * .4 + 0.08 * Math.sin(tt * 2 + d);
            if (th * 16 > BAYER[y & 3][x & 3] + 2) { g.fillStyle = pal[3]; g.globalAlpha = .55; g.fillRect(x, y, 1, 1); g.globalAlpha = 1; }
          }
        }
        // sphere with plasma
        for (let y = cy - R; y <= cy + R; y++) for (let x = cx - R; x <= cx + R; x++) {
          const dx = x - cx + .5, dy = y - cy + .5, d = Math.hypot(dx, dy);
          if (d > R + 1) continue;
          if (d > R) { g.fillStyle = "#0a0716"; g.fillRect(x, y, 1, 1); continue; }
          let v = Math.sin(x * .28 + tt) + Math.sin(y * .23 - tt * 1.3) + Math.sin((x + y) * .17 + tt * .7) + Math.sin(d * .45 - tt * 2.1);
          v = (v + 4) / 8; // 0..1
          const shade = 1 - Math.pow(d / R, 2) * .65 - (dx + dy) / (R * 6);
          let lv = v * 3.2 * shade + 0.6 + flash * 1.6;
          const dith = (BAYER[y & 3][x & 3] / 16) - .5;
          let li = Math.max(0, Math.min(pal.length - 2, Math.floor(lv + dith)));
          g.fillStyle = pal[li]; g.fillRect(x, y, 1, 1);
        }
        // highlights
        g.fillStyle = pal[5];
        [[cx - 11, cy - 13], [cx - 12, cy - 12], [cx - 10, cy - 14], [cx - 13, cy - 10], [cx - 9, cy - 14], [cx - 13, cy - 9], [cx + 9, cy + 12]].forEach(([x, y]) => g.fillRect(x, y, 1, 1));
        g.fillStyle = "rgba(255,255,255,.75)"; g.fillRect(cx - 12, cy - 12, 2, 2);
        // pedestal: gold claws + stone foot
        const gold = ["#5a3a10", "#a8741c", "#f5c451", "#fff0b0"];
        const py = cy + R - 3;
        for (let i = 0; i < 6; i++) {
          const w = 30 - i * 2 + (i > 3 ? 6 : 0);
          g.fillStyle = gold[i === 0 ? 2 : i < 3 ? 1 : 0];
          g.fillRect(cx - w / 2, py + i, w, 1);
        }
        g.fillStyle = gold[3]; g.fillRect(cx - 14, py, 3, 1); g.fillRect(cx + 11, py, 3, 1);
        const stone = ["#3b3156", "#2a2240", "#1b152c"];
        for (let i = 0; i < 12; i++) {
          const w = 18 + (i > 6 ? (i - 6) * 4 : 0);
          g.fillStyle = i === 0 || i === 7 ? "#56497c" : stone[i % 3 === 0 ? 0 : 1];
          g.fillRect(cx - w / 2, py + 6 + i, w, 1);
        }
        g.fillStyle = "#0e0a1a"; g.fillRect(cx - 21, py + 18, 42, 1);
        // runes on the stone glow with state
        g.fillStyle = state === "thinking" ? "#7ff0ff" : state === "answered" ? "#ffd86b" : "#6a5a9a";
        [[cx - 5, py + 9], [cx - 1, py + 10], [cx + 3, py + 9], [cx - 3, py + 13], [cx + 2, py + 13]].forEach(([x, y]) => g.fillRect(x, y, 1, 2));
        flash = Math.max(0, flash - .07);
      },
    };
    return self;
  };

  // ---------- particles ----------
  PX.FX = function (canvas) {
    const g = canvas.getContext("2d");
    let parts = [], W = 0, H = 0, dpr = 1, ambient = true;
    function resize() {
      dpr = Math.min(2, window.devicePixelRatio || 1);
      W = window.innerWidth; H = window.innerHeight;
      canvas.width = W * dpr; canvas.height = H * dpr;
      canvas.style.width = W + "px"; canvas.style.height = H + "px";
      g.setTransform(dpr, 0, 0, dpr, 0, 0);
      g.imageSmoothingEnabled = false;
    }
    resize(); window.addEventListener("resize", resize);
    const PALS = {
      gold: ["#fff3b0", "#ffd85e", "#f5a83a"], cyan: ["#e8ffff", "#8ff4ff", "#4ab8ff"], pink: ["#ffd1f0", "#f29bdc", "#b27bff"],
      moss: ["#e6ff9c", "#b6e36a", "#7fbf4a"], red: ["#ffb0a8", "#ef6b63", "#b8262f"], grey: ["#e6ebf7", "#b8c2dc", "#7a86a8"],
    };
    const self = {
      add(p) { if (parts.length < 900) parts.push(p); },
      burst(x, y, n, pal, power) {
        const cols = PALS[pal] || PALS.gold; power = power || 3;
        for (let i = 0; i < n; i++) {
          const a = Math.random() * Math.PI * 2, s = (0.4 + Math.random()) * power;
          self.add({ x, y, vx: Math.cos(a) * s, vy: Math.sin(a) * s - 1, g: 0.06, life: 1, decay: 0.012 + Math.random() * 0.02, col: cols[i % cols.length], size: Math.random() > .7 ? 3 : 2, star: Math.random() > .6 });
        }
      },
      sparkle(x, y, pal, spread) {
        const cols = PALS[pal] || PALS.gold; spread = spread || 10;
        self.add({ x: x + (Math.random() - .5) * spread, y: y + (Math.random() - .5) * spread, vx: (Math.random() - .5) * .6, vy: -Math.random() * .8, g: 0, life: 1, decay: 0.03 + Math.random() * .03, col: cols[Math.floor(Math.random() * cols.length)], size: 2, star: Math.random() > .5 });
      },
      stream(x, y, tx, ty, pal) {
        const cols = PALS[pal] || PALS.cyan;
        self.add({ x: x + (Math.random() - .5) * 40, y: y + (Math.random() - .5) * 20, vx: (Math.random() - .5) * 2, vy: -1 - Math.random() * 2, g: 0, tx, ty, life: 1, decay: 0.008, col: cols[Math.floor(Math.random() * cols.length)], size: 2, star: Math.random() > .7 });
      },
      setAmbient(v) { ambient = v; },
      tick() {
        g.clearRect(0, 0, W, H);
        if (ambient && Math.random() < 0.12 && parts.length < 140) {
          const cols = PALS.moss;
          self.add({ x: Math.random() * W, y: H * (0.3 + Math.random() * 0.7), vx: (Math.random() - .5) * .25, vy: -.15 - Math.random() * .25, g: 0, life: 1, decay: 0.002 + Math.random() * 0.003, col: cols[Math.floor(Math.random() * 3)], size: 2, firefly: Math.random() * 6 });
        }
        const next = [];
        for (const p of parts) {
          if (p.tx !== undefined) {
            const dx = p.tx - p.x, dy = p.ty - p.y, d = Math.hypot(dx, dy) || 1;
            p.vx = p.vx * .92 + dx / d * .9; p.vy = p.vy * .92 + dy / d * .9;
            if (d < 14) p.life = 0;
          }
          p.vy += p.g; p.x += p.vx; p.y += p.vy; p.life -= p.decay;
          if (p.life <= 0) continue;
          next.push(p);
          let a = Math.ceil(p.life * 4) / 4; // stepped alpha
          if (p.firefly !== undefined) a *= (Math.sin(performance.now() / 300 + p.firefly) > 0 ? 1 : .35);
          g.globalAlpha = a; g.fillStyle = p.col;
          const x = Math.round(p.x), y = Math.round(p.y), s = p.size;
          g.fillRect(x, y, s, s);
          if (p.star && p.life > .45) { g.fillRect(x - s, y, s, s); g.fillRect(x + s, y, s, s); g.fillRect(x, y - s, s, s); g.fillRect(x, y + s, s, s); }
        }
        g.globalAlpha = 1;
        parts = next;
      },
      clear() { parts = []; },
    };
    return self;
  };

  window.PX = PX;
})();
