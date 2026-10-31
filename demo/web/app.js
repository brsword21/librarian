/* The Librarian - arcane night library demo (vanilla JS, no build step) */
(() => {
"use strict";

/* ------------------------------------------------------------------ constants */
const KINDS = {
  ssu:      { name: "Personal facts",       hint: "what you told it about yourself", sigil: "eye" },
  ssa:      { name: "Advice I was given",   hint: "what the assistant recommended", sigil: "scroll" },
  multi:    { name: "Counting across time", hint: "facts spread over many chats", sigil: "tally" },
  ku:       { name: "Things that changed",  hint: "the newest value wins", sigil: "cycle" },
  temporal: { name: "Dates & durations",    hint: "date arithmetic done by code", sigil: "hourglass" },
};
const KIND_ORDER = ["ku", "temporal", "ssa", "multi", "ssu"];
const SIGILS = {
  eye: '<path d="M3 16 Q16 5 29 16 Q16 27 3 16Z"/><circle cx="16" cy="16" r="4.6"/><circle cx="16" cy="16" r="1.4" fill="currentColor"/><path d="M16 3v3M8 5.5l1.6 2.4M24 5.5l-1.6 2.4"/>',
  scroll: '<path d="M10 6h13a3 3 0 0 1 3 3v15a3 3 0 0 1-3 3H9"/><path d="M10 6a3 3 0 0 0-3 3v1h3M9 27a3 3 0 0 1-3-3v-1h3V9"/><path d="M13 12h9M13 16h9M13 20h6"/>',
  tally: '<path d="M8 7v18M12.5 7v18M17 7v18M21.5 7v18M5 21L26 10"/>',
  cycle: '<path d="M7 15a9 9 0 0 1 15.5-6.2"/><path d="M23 3.5v5.6h-5.6"/><path d="M25 17a9 9 0 0 1-15.5 6.2"/><path d="M9 28.5v-5.6h5.6"/>',
  hourglass: '<path d="M9 4h14M9 28h14M10.5 4c0 7 5.5 9 5.5 12s-5.5 5-5.5 12M21.5 4c0 7-5.5 9-5.5 12s5.5 5 5.5 12"/><path d="M13 25.5h6l-3-3.5z" fill="currentColor"/>',
  none: '<circle cx="16" cy="16" r="11"/><path d="M8 24L24 8"/>',
};
const RUNES = [
  "M3 1V15M3 4L8 1M3 8L8 5", "M5 1V15M5 7L1 2M5 7L9 2", "M5 1L8.5 5L5 9L1.5 5ZM3 7L.5 15M7 7L9.5 15", "M8 2L2 8L8 14",
  "M5 1V15M5 1L1 6M5 1L9 6", "M5 1L9 8L5 15L1 8Z", "M1 2V14L9 2V14L1 2", "M7 1L2 6L8 10L3 15", "M2 1V15M2 2L8 6L2 9M2 9L8 15",
  "M2 1V15M8 1V15M2 4L8 8M8 4L2 8",
];
const PEOPLE = {
  h_d99a2da8f8ee: { name: "Carla", desc: "Lisbon · ceramics classes, freelance design, two teenagers, a new cat" },
  h_961be7a385ce: { name: "Grace", desc: "Melbourne · watercolours, hospital work, two grown sons" },
  h_ba495aa00d0c: { name: "Aisha", desc: "A Python data course, freelance data work, a used-car fund" },
  h_4fa7f122fcdb: { name: "Lucia", desc: "Buenos Aires · tango, baking, a sourdough starter" },
  h_8224cd1fdcd0: { name: "Hiroshi", desc: "Restoring a vintage National R-77 radio, valve by valve" },
  h_5e62f4533db4: { name: "Rafael", desc: "Retired firefighter · orchids, morning swims, grandchildren" },
};
const TOUR = [
  { id: "q_62e927862f62", caption: "Things change. Miguel taught the class until August; the Librarian lines up every mention, oldest first, and the newest one wins." },
  { id: "q_06ae4afa8961", caption: "Two dates in two different chats, plus decoys. The code does the date arithmetic; Reactor only has to check it." },
  { id: "q_392fdc44c911", caption: "One sentence of advice, buried in a chat about cat paw prints in the clay, two months earlier." },
  { id: "q_068d0a4b3f7b", caption: "Counting across time: three mugs in August, two vases in September. Two books, one sum." },
  { id: "q_aa27ddd3b7c5", caption: "Two dogs in Grace's archive, and neither is hers: Archie is the hospital's therapy dog, Luna is a friend's puppy. So Reactor won't guess." },
];
/* one hue family per month (hue, saturation), alternating warm and cool so month blocks read on a projector */
const MONTH_HUES = [[266, 34], [104, 28], [352, 38], [190, 36], [36, 46], [226, 36], [318, 28], [150, 28], [18, 40], [60, 30]];
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const MONTHS_LONG = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
const STOP = new Set("what which when where with that this have about your from into were they them then than there their been being does did done much many more most some name named first last time times days apart after before since total ever made make using used just also year years month months week weeks recommend recommended told tell mention mentioned remind previous conversation chat back going".split(" "));
const ABSTAIN_RE = /^\s*(INSUFFICIENT[_ ]EVIDENCE|NOT[_ ]IN[_ ]ARCHIVE)\s*$/i;

/* ------------------------------------------------------------------ state */
const S = {
  data: null, sizes: {}, byId: new Map(), hid: null, rec: null, run: 0, fast: false, stage: false,
  tour: { idx: -1, playing: false, timer: null }, busy: null, statusOk: false, liveSeq: 0, askTimer: null,
};
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => Array.from(el.querySelectorAll(s));
const CANCEL = Symbol("cancel");

/* ------------------------------------------------------------------ helpers */
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmt = (n) => Number(n || 0).toLocaleString("en-US");
const hash = (s) => { let h = 2166136261; for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); } return h >>> 0; };
function parseDate(s) {
  const m = /(\d{4})\/(\d{2})\/(\d{2})(?:\s*\(\w+\))?\s*(\d{1,2})?:?(\d{2})?/.exec(s || "");
  return m ? new Date(+m[1], +m[2] - 1, +m[3], +(m[4] || 0), +(m[5] || 0)) : null;
}
function niceDate(s, withTime = true) {
  const d = parseDate(s); if (!d) return s || "";
  const wd = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"][d.getDay()];
  const t = withTime ? ` · ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}` : "";
  return `${wd} ${d.getDate()} ${MONTHS[d.getMonth()]} ${d.getFullYear()}${t}`;
}
function sigil(name, cls = "") { const art = {eye:"icon_lens_ssu",scroll:"icon_lens_ssa",tally:"icon_lens_multi",cycle:"icon_lens_ku",hourglass:"icon_lens_temporal",none:"icon_abstain"}; return `<img class="sigil-art ${cls}" src="assets/${art[name] || art.eye}.webp" alt="">`; }
function rune(i) { return `<svg viewBox="0 0 10 16" aria-hidden="true"><path d="${RUNES[i % RUNES.length]}"/></svg>`; }
const norm = (s) => String(s || "").toLowerCase().replace(/[’‘`]/g, "'").replace(/[“”]/g, '"').replace(/\s+/g, " ").trim();
function sleep(ms, tok) {
  return new Promise((res, rej) => {
    const t = S.fast ? 0 : ms;
    setTimeout(() => (tok === S.run ? res() : rej(CANCEL)), t);
  });
}
const isAbstain = (r) => !!(r && (r.abstained || ABSTAIN_RE.test(r.answer || "")));
const person = (hid) => PEOPLE[hid] || null;
function personName(hid) {
  const p = person(hid); if (p) return p.name;
  const devIds = Object.keys(S.data?.timelines || {}).filter((h) => !PEOPLE[h]);
  const i = devIds.indexOf(hid);
  return i >= 0 ? `Reader ${i + 1}` : "This person";
}

/* ------------------------------------------------------------------ background: fireflies & runes */
function startMotes() {
  const cv = $("#motes"); const ctx = cv.getContext("2d");
  let W = 0, H = 0, dpr = 1; const motes = [];
  const sprite = (rgb) => {
    const c = document.createElement("canvas"); c.width = c.height = 64; const g = c.getContext("2d");
    const gr = g.createRadialGradient(32, 32, 0, 32, 32, 32);
    gr.addColorStop(0, `rgba(${rgb},1)`); gr.addColorStop(.18, `rgba(${rgb},.75)`); gr.addColorStop(.45, `rgba(${rgb},.18)`); gr.addColorStop(1, `rgba(${rgb},0)`);
    g.fillStyle = gr; g.fillRect(0, 0, 64, 64); return c;
  };
  const sprites = [sprite("255,213,138"), sprite("169,208,122"), sprite("185,167,255"), sprite("143,240,208")];
  function resize() { dpr = Math.min(2, window.devicePixelRatio || 1); W = innerWidth; H = innerHeight; cv.width = W * dpr; cv.height = H * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0); }
  resize(); addEventListener("resize", resize);
  const N = 70;
  for (let i = 0; i < N; i++) motes.push({ x: Math.random() * W, y: Math.random() * H, vx: (Math.random() - .5) * .25, vy: -.05 - Math.random() * .22, r: 4 + Math.random() * 12, s: sprites[i % 7 === 0 ? 3 : i % 3 === 0 ? 1 : i % 5 === 0 ? 2 : 0], ph: Math.random() * 6.28, sp: .6 + Math.random() * 1.6 });
  let last = performance.now();
  function frame(now) {
    const dt = Math.min(50, now - last) / 16.7; last = now;
    ctx.clearRect(0, 0, W, H);
    for (const m of motes) {
      m.ph += .02 * m.sp * dt; m.x += (m.vx + Math.sin(m.ph * .7) * .18) * dt; m.y += m.vy * dt;
      if (m.y < -20) { m.y = H + 20; m.x = Math.random() * W; } if (m.x < -20) m.x = W + 20; if (m.x > W + 20) m.x = -20;
      const a = .25 + .75 * Math.pow((Math.sin(m.ph * 1.7) + 1) / 2, 2);
      ctx.globalAlpha = a * .8; ctx.drawImage(m.s, m.x - m.r, m.y - m.r, m.r * 2, m.r * 2);
    }
    ctx.globalAlpha = 1;
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);

  const bg = $("#runesBg"); let html = "";
  for (let i = 0; i < 14; i++) {
    const x = (hash("x" + i) % 96) + 1, y = (hash("y" + i) % 92) + 2;
    html += `<svg viewBox="0 0 10 16" style="left:${x}vw;top:${y}vh;animation-delay:${-(i * 1.7)}s;transform:rotate(${(hash("r" + i) % 30) - 15}deg)"><path d="${RUNES[i % RUNES.length]}"/></svg>`;
  }
  bg.innerHTML = html;
}

function decorate() {
  $("#beamRunes").innerHTML = '<span class="legend"><span><i class="lg-c"></i>candidate</span><span><i class="lg-t"></i>selected</span><span><i class="lg-s"></i>cited</span></span>';
}

/* ------------------------------------------------------------------ shelves */
function archiveStats(hid) {
  const tl = S.data.timelines[hid] || [];
  const sz = S.sizes[hid];
  const total = sz?.total || tl.length * 8250;
  return { n: tl.length, total, estimated: !sz };
}

function renderShelves(hid) {
  S.hid = hid;
  const tl = (S.data.timelines[hid] || []).slice().sort((a, b) => (parseDate(a.date) || 0) - (parseDate(b.date) || 0));
  const sz = S.sizes[hid]?.sessions || {};
  const nShelves = 3; const per = Math.ceil(tl.length / nShelves) || 1;
  const shelves = []; let prevMonth = null; let monthIdx = -1;
  for (let s = 0; s < nShelves; s++) {
    const slice = tl.slice(s * per, (s + 1) * per); let html = "";
    slice.forEach((t, j) => {
      const d = parseDate(t.date); const mk = d ? `${d.getFullYear()}-${d.getMonth()}` : "";
      if (d && mk !== prevMonth) monthIdx++;
      if (d && (mk !== prevMonth || j === 0)) {
        html += `<span class="month" title="${MONTHS_LONG[d.getMonth()]} ${d.getFullYear()}">${MONTHS[d.getMonth()]}<small>${d.getFullYear()}</small></span>`;
        prevMonth = mk;
      }
      const chars = sz[t.id] || 8000; const h = hash(t.id);
      const w = Math.max(.55, Math.min(1.7, Math.sqrt(chars / 8000)));
      const height = 58 + (h % 34);
      const [hh, ss] = MONTH_HUES[Math.max(0, monthIdx) % MONTH_HUES.length];
      const r = (h % 1000) / 1000, r2 = ((h >>> 10) % 1000) / 1000;
      const c = `hsl(${(hh + (r - .5) * 22).toFixed(0)} ${(ss + (r2 - .5) * 14).toFixed(0)}% ${(20 + r2 * 14).toFixed(1)}%)`;
      const lean = h % 23 === 0 ? " lean" : "";
      html += `<div class="book${lean}" data-id="${esc(t.id)}" style="--w:${w.toFixed(2)};--h:${height}%;--c:${c}" title="${esc(niceDate(t.date))} · ${esc((t.title || "").trim())}…"></div>`;
    });
    shelves.push(`<div class="shelf">${html}</div>`);
  }
  $("#shelves").innerHTML = shelves.join("");
  $("#shelves").style.setProperty("--bmax", tl.length < 90 ? "3.8rem" : "2.2rem");
  const st = archiveStats(hid); const nm = personName(hid);
  $("#archiveOwner").textContent = `${nm}'s archive`;
  const first = parseDate(tl[0]?.date), last = parseDate(tl[tl.length - 1]?.date);
  const span = !first || !last ? "" : first.getMonth() === last.getMonth() && first.getFullYear() === last.getFullYear() ? ` · ${MONTHS_LONG[first.getMonth()]} ${first.getFullYear()}` : ` · ${MONTHS[first.getMonth()]} – ${MONTHS[last.getMonth()]} ${last.getFullYear()}`;
  $("#archiveCount").textContent = `${fmt(st.n)} conversations · ${(st.total / 1e6).toFixed(2)}M characters${span}`;
  $("#liveWho").textContent = nm;
  parkLibrarian();
}

function bookEl(id) { return $(`#shelves .book[data-id="${CSS.escape(id)}"]`); }
function relRect(el) {
  const a = $("#archive").getBoundingClientRect(), r = el.getBoundingClientRect();
  return { x: r.left - a.left, y: r.top - a.top, w: r.width, h: r.height };
}
function moveLibrarian(x, y, mode) {
  const L = $("#librarian");
  L.classList.toggle("fast", mode === "fast"); L.classList.toggle("sweep", mode === "sweep");
  const lw = L.offsetWidth, lh = L.offsetHeight;
  L.style.transform = `translate(${Math.round(x - lw * .5)}px, ${Math.round(y - lh * .62)}px)`;
}
/* Park the Librarian where it hides nothing that matters: never on a sealed or cited book,
   preferably not on a book that went to the desk or on a month marker. Prefers the right end
   of the middle shelf and walks left / to the other shelves only when that spot is busy. */
function parkLibrarian() {
  const a = $("#archive"), L = $("#librarian");
  const aw = a.clientWidth, ah = a.clientHeight, lw = L.offsetWidth || 90, lh = L.offsetHeight || 120;
  const rec = S.rec && S.rec.history_id === S.hid ? S.rec : null;
  const cited = new Set(rec?.answer != null ? rec.cited || [] : []);
  const obstacles = [];
  $$("#shelves .book").forEach((b) => {
    const k = b.classList.contains("sealed") || cited.has(b.dataset.id) ? 100
      : b.classList.contains("taken") || b.classList.contains("chosen") ? 14
        : b.classList.contains("candidate") ? .5 : 0;
    if (!k) return;
    const r = relRect(b), pad = k >= 100 ? 12 : 0; // the wax dot is wider than a thin book
    obstacles.push({ x: r.x - pad, y: r.y, w: r.w + pad * 2, h: r.h, k });
  });
  $$("#shelves .month").forEach((m) => obstacles.push({ ...relRect(m), k: 4 }));
  const rows = $$("#shelves .shelf").map((s) => { const r = relRect(s); return r.y + r.h - lh * .36; });
  const mid = Math.floor(rows.length / 2);
  const ys = rows.length ? rows : [ah * .52];
  const home = aw * .94;
  let best = null;
  ys.forEach((y, ri) => {
    for (let x = aw * .965; x >= aw * .05; x -= lw * .3) {
      // the robed body of the SVG (staff and lamp included), not its aura
      const bx0 = x - lw * .5 + lw * .12, bx1 = x - lw * .5 + lw * .88, by0 = y - lh * .62, by1 = y - lh * .62 + lh * .93;
      let cost = 0;
      for (const o of obstacles) {
        const ox = Math.max(0, Math.min(bx1, o.x + o.w) - Math.max(bx0, o.x)), oy = Math.max(0, Math.min(by1, o.y + o.h) - Math.max(by0, o.y));
        if (ox > 0 && oy > 0) cost += o.k * (ox * oy) / Math.max(1, o.w * o.h);
        else if (o.k >= 100 && oy > 0) {
          // keep clear air around a sealed book so its glow and wax read on their own
          const gap = Math.max(o.x - bx1, bx0 - (o.x + o.w));
          cost += 1.5 * Math.max(0, 1 - gap / (lw * .8));
        }
      }
      // stay near the right end of the middle shelf; the top shelf sits under the beam legend
      cost += Math.abs(home - x) / aw * 3 + (ri === mid ? 0 : ri === 0 ? .9 : .5);
      if (!best || cost < best.cost) best = { x, y, cost };
    }
  });
  moveLibrarian(best ? best.x : home, best ? best.y : ah * .52, "fast");
}

/* ------------------------------------------------------------------ text marking */
function splitSentences(s) {
  try { return s.split(/(?<=[.!?…])\s+(?=[A-Z0-9"'“‘(\[])/); } catch { return [s]; }
}
function noteQuotes(notes) {
  const out = []; const re = /["“]([^"”]{14,})["”]/g; let m;
  while ((m = re.exec(notes || ""))) out.push(norm(m[1]).replace(/(…|\.\.\.)$/, "").trim());
  return out.filter((q) => q.length >= 12);
}
function answerNeedles(rec) {
  if (!rec || isAbstain(rec) || !rec.answer) return [];
  let a = String(rec.answer).trim().replace(/[.。]$/, "");
  const out = new Set();
  if (/^\d{1,2}$/.test(a)) return [];               // tiny numbers would match everywhere
  out.add(a);
  const paren = a.split("(")[0].trim(); if (paren.length >= 3) out.add(paren);
  const inSplit = a.split(/\s+in\s+|,\s*/)[0].trim(); if (inSplit.length >= 4) out.add(inSplit);
  out.add(a.replace(/^(the|a|an)\s+/i, ""));
  const num = a.match(/^[\d.,]+/); if (num && num[0].length >= 3) out.add(num[0]);
  return [...out].filter((x) => x.length >= 2).sort((x, y) => y.length - x.length);
}
const NUM_RE = /\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|dozen|couple)\b/i;
function keyStems(q) {
  return [...new Set(norm(q).replace(/[^a-z0-9' ]/g, " ").split(" ").map((w) => w.replace(/'s$/, "")).filter((w) => w.length >= 4 && !STOP.has(w)).map((w) => w.slice(0, 5)))];
}
function keyHit(sent, key) {
  if (!key || !key.stems.length) return false;
  const sn = norm(sent); const hits = key.stems.filter((s) => sn.includes(s)).length;
  if (key.counting) return hits >= 2 && NUM_RE.test(sent);
  return hits >= Math.min(3, Math.max(2, key.stems.length - 1));
}
/* a counted quantity inside a sentence: "three mugs", "2 vases", "1,800" */
const COUNT_RE = /\b(\d+(?:[.,]\d+)*|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|dozen)\b(?:\s+(?:more|new|small|big|large|little|extra|different|separate|additional)\b)?(?:\s+([a-z][a-z-]+))?/i;
const NUM_WORDS = { one: 1, two: 2, three: 3, four: 4, five: 5, six: 6, seven: 7, eight: 8, nine: 9, ten: 10, eleven: 11, twelve: 12, dozen: 12 };
function toNum(s) {
  const t = String(s ?? "").toLowerCase().trim();
  if (NUM_WORDS[t] != null) return NUM_WORDS[t];
  const m = /[+-]?\d[\d,]*(\.\d+)?/.exec(t);
  return m ? parseFloat(m[0].replace(/,/g, "")) : NaN;
}

/* ------------------------------------------------------------------ the code's candidate vs Reactor */
function candidateVerdict(rec) {
  if (!rec || rec.computed == null || String(rec.computed).trim() === "" || rec.answer == null) return null;
  if (isAbstain(rec)) return { rejected: true, why: "abstained" };
  const c = String(rec.computed).trim(), a = String(rec.answer).trim();
  const nc = c.match(/-?\d+(\.\d+)?/), na = a.match(/-?\d+(\.\d+)?/);
  let same;
  if (nc && na) same = +nc[0] === +na[0];
  else { const sa = simp(a), sc = simp(c); same = !!sc && !!sa && (sa === sc || sa.includes(sc) || (sc.includes(sa) && sa.length >= 3)); }
  return same ? { rejected: false } : { rejected: true, why: "differs" };
}
/* a named candidate (not a day count) whose source sentence is worth marking on the desk */
function candidateWord(rec) {
  const c = String(rec?.computed ?? "").trim();
  return c.length >= 2 && rec.route !== "temporal" && !/^[\d.,\s]+$/.test(c) ? c : null;
}
/* the archive sentence the candidate came from (first mention on the desk) */
function candidateSource(rec) {
  const c = String(rec?.computed ?? "").trim(); if (!c) return null;
  const ps = rec.passages || [];
  for (let i = 0; i < ps.length; i++) {
    for (const line of String(ps[i].text || "").split("\n")) {
      const body = line.replace(/^\s*(user|assistant)\s*:\s?/i, "").replace(/\*\*/g, "");
      for (const s of splitSentences(body)) if (findWord(s, c)) return { e: i + 1, sent: s.trim() };
    }
  }
  return null;
}
function quoteAround(sent, word, max = 96) {
  if (sent.length <= max) return sent;
  const i = Math.max(0, sent.toLowerCase().indexOf(String(word).toLowerCase()));
  let a = Math.max(0, i - Math.round(max * .55)), b = Math.min(sent.length, a + max);
  if (a > 0) a = sent.indexOf(" ", a) + 1 || a;
  if (b < sent.length) b = sent.lastIndexOf(" ", b) > i ? sent.lastIndexOf(" ", b) : b;
  return (a > 0 ? "…" : "") + sent.slice(a, b).trim() + (b < sent.length ? "…" : "");
}

/* ------------------------------------------------------------------ counting: one-line tally */
function oracleTally(rec) {
  if (!rec || rec.route !== "multi" || rec.answer == null || isAbstain(rec)) return null;
  const target = toNum(rec.answer); if (isNaN(target)) return null;
  const close = (x) => Math.abs(x - target) < 1e-6;
  // 1) Reactor's own list: "date | [E#] | item | number"
  const terms = [];
  for (const raw of String(rec.reasoning || "").split("\n")) {
    const m = /\|\s*\[?E(\d+)\]?\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*$/.exec(raw);
    if (!m) continue;
    let v = m[3].trim();
    if (/duplicate|same event|excluded|ignored|not counted/i.test(v)) continue;
    const arrow = /→\s*([+-]?\d[\d,.]*)/.exec(v); if (arrow) v = arrow[1];
    if (!/^[+-]?\d[\d,.]*(\s+[a-z]+)?\.?$/i.test(v)) continue;
    const n = toNum(v); if (isNaN(n)) continue;
    const item = m[2].replace(/\([^)]*\)/g, "").replace(/["“”]/g, "").trim();
    terms.push({ e: +m[1], num: v.replace(/\s+[a-z]+\.?$/i, ""), n, item: /^[a-z-]{2,12}$/i.test(item) ? item : "" });
  }
  const sum = (ts) => ts.reduce((a, t) => a + t.n, 0);
  if (terms.length >= 2 && terms.length <= 6 && close(sum(terms))) return { terms, label: "Reactor's reckoning" };
  // 2) Reactor wrote its sum out: "Sum: 1,800 + 2,400 = 4,200" / "Total = ..."
  const sl = /^[\s\-•*]*(?:sum|total|computed total|computation)\b[^:=\n]{0,30}[:=]\s*(.*\d.*)$/im.exec(String(rec.reasoning || ""));
  if (sl) return { line: sl[1].replace(/\.\s*$/, "").trim(), label: "Reactor's reckoning" };
  // 3) read the counted sentences straight off the cited pages; shown only if they add up
  const cited = new Set(rec.cited || []); const key = { stems: keyStems(rec.question), counting: true };
  const found = [];
  (rec.passages || []).forEach((p, i) => {
    if (!cited.has(p.id)) return;
    String(p.text || "").split("\n").forEach((line) => {
      const m = /^\s*user\s*:\s?(.*)$/i.exec(line); if (!m) return;
      splitSentences(m[1]).forEach((s) => {
        if (!keyHit(s, key)) return;
        const c = COUNT_RE.exec(s); if (!c) return;
        const n = toNum(c[1]); if (isNaN(n)) return;
        found.push({ e: i + 1, num: fmt(n), n, item: c[2] || "" });
      });
    });
  });
  if (found.length >= 2 && found.length <= 6 && close(sum(found))) return { terms: found, label: "tally of the cited pages" };
  return null;
}
function tallyHtml(t, answer) {
  if (!t) return "";
  if (t.line) return `<div class="tally"><small>${esc(t.label)}</small><span class="tl">${esc(t.line)}</span></div>`;
  const items = new Set(t.terms.map((x) => x.item.toLowerCase()));
  const useItems = items.size === t.terms.length && t.terms.every((x) => x.item);
  const body = t.terms.map((x) => `<span class="tt">${esc(x.num)}${useItems ? " " + esc(x.item) : ""}<i>E${x.e}</i></span>`).join('<span class="op">+</span>');
  return `<div class="tally"><small>${esc(t.label)}</small><span class="tl">${body}<span class="op">=</span><b>${esc(String(answer).trim())}</b></span></div>`;
}
/* find `needle` in `sent` on word boundaries; returns [before, hit, after] or null */
function findWord(sent, needle) {
  if (!needle) return null;
  const low = sent.toLowerCase(), n = needle.toLowerCase();
  for (let i = low.indexOf(n); i >= 0; i = low.indexOf(n, i + 1)) {
    const before = sent.slice(0, i), hit = sent.slice(i, i + n.length), after = sent.slice(i + n.length);
    const okL = !/[\w]$/.test(before) || !/^\w/.test(hit), okR = !/^\w/.test(after) || !/\w$/.test(hit);
    if (okL && okR) return [before, hit, after];
  }
  return null;
}
function markSentence(sent, needles, quotes, key, decoy) {
  const sn = norm(sent); let cls = "";
  for (const q of quotes) {
    if (sn.length >= 18 && (q.includes(sn) || sn.includes(q.slice(0, Math.min(q.length, 46))))) { cls = "hl-note"; break; }
  }
  let html = esc(sent);
  for (const n of needles) {
    const f = findWord(sent, n);
    if (f) { html = `${esc(f[0])}<mark>${esc(f[1])}</mark>${esc(f[2])}`; cls = "hl-ans"; break; }
  }
  if (cls !== "hl-ans" && decoy) {
    // where the code's candidate came from; struck through once Reactor rejects it
    const f = findWord(sent, decoy);
    if (f) { html = `${esc(f[0])}<mark>${esc(f[1])}</mark>${esc(f[2])}`; cls = "hl-cand"; }
  }
  if (!cls && key && keyHit(sent, key)) {
    if (key.tally) {
      // counting question: the counted sentence gets the amber answer highlight, its number inked
      const m = COUNT_RE.exec(sent);
      html = m ? `${esc(sent.slice(0, m.index))}<mark>${esc(m[0])}</mark>${esc(sent.slice(m.index + m[0].length))}` : html;
      cls = "hl-ans";
    } else cls = "hl-key";
  }
  return cls ? `<span class="${cls}">${html}</span>` : html;
}
function renderPassage(text, rec, who, pid) {
  const needles = answerNeedles(rec), quotes = noteQuotes(rec?.notes);
  let hits = 0;
  const citedHere = pid && (rec?.cited || []).includes(pid);
  const key = citedHere ? { stems: keyStems(rec.question), counting: rec.route === "multi" || /^how (many|much)/i.test(rec.question || ""), tally: rec.route === "multi" && !isAbstain(rec) } : null;
  const decoy = candidateWord(rec);
  const lines = String(text || "").split("\n").map((line) => {
    const t = line.trim(); if (!t) return "";
    if (/^\[\s*(\.\.\.|…)\s*\]$/.test(t)) return '<div class="gapline">· · ·</div>';
    const m = /^(user|assistant)\s*:\s?([\s\S]*)$/i.exec(t);
    const sp = m ? m[1].toLowerCase() : ""; const body = (m ? m[2] : t).replace(/\*\*/g, "").replace(/\\\*/g, "•").replace(/^#{1,4}\s+/, "");
    const html = splitSentences(body).map((s) => markSentence(s, needles, quotes, sp === "user" || sp === "" ? key : key && !key.tally ? key : null, decoy)).join(" ");
    if (html.includes('class="hl-')) hits++;
    const label = sp === "user" ? who : sp === "assistant" ? "Assistant" : "";
    return `<p class="ln ${sp}">${label ? `<span class="who">${esc(label)}</span>` : ""}${html}</p>`;
  }).join("");
  return { html: lines || '<p class="ln"><i>(empty page)</i></p>', hits };
}

/* ------------------------------------------------------------------ marginalia */
/* the margin shows only what the code found (timelines, dates, the likely line, decoys); its instructions to Reactor are one click away */
const NOTE_RULE = { ssu: "Only the user's own facts", ssa: "The assistant's own advice", multi: "Count each thing once", ku: "The newest value wins", temporal: "Code does the date math" };
const NOTE_EMPTY = { multi: "Reactor lists every mention with its page, then adds them up." };
const dayOf = (s) => { const m = /(\d{4})[/-](\d{2})[/-](\d{2})/.exec(s || ""); return m ? `${+m[3]} ${MONTHS[+m[2] - 1]} ${m[1]}` : ""; };
const unfill = (q) => { const m = /^(?:[^:"]{3,40}:|On an? [a-z ]{3,20} note,|Also,|Oh,)\s+(.{20,})$/i.exec(q); const s = m ? m[1] : q; return s.length > 84 ? s.slice(0, 82).replace(/\s+\S*$/, "") + "…" : s; };
function noteFacts(rec) {
  const text = String(rec.notes || ""), facts = [];
  const bullets = text.split("\n").map((l) => /^\s*[-•*]\s+(.*)$/.exec(l)?.[1]).filter(Boolean);
  bullets.forEach((b, i) => {
    let m;
    if ((m = /^"(.+?)"\s*=\s*(\d{4}-\d{2}-\d{2})/.exec(b))) facts.push(`<span class="dt">${dayOf(m[2])}</span> ${esc(m[1])}`);
    else if ((m = /^(\d{4}\/\d{2}\/\d{2}):\s*"(.*)"\s*$/.exec(b))) facts.push(`<span class="dt">${dayOf(m[1])}</span> “${esc(unfill(m[2]))}”${rec.route === "ku" && i === bullets.length - 1 ? ' <span class="em">newest</span>' : ""}`);
    else facts.push(esc(b.length > 170 ? b.slice(0, 168) + "…" : b));
  });
  let m;
  if ((m = /Likely the line you need \((\w+), session of (\d{4}\/\d{2}\/\d{2}).*?\):\s*"(.*)"/.exec(text))) facts.push(`<span class="dt">${dayOf(m[2])}</span> ${esc(m[1])}: “${esc(m[3])}”`);
  for (const d of text.matchAll(/Note: the (\d{4}\/\d{2}\/\d{2}) line "(.*?)" is about ([^,.]+?), not the user's own/g)) {
    facts.push(`<span class="em">decoy</span> <span class="dt">${dayOf(d[1])}</span> “${esc(unfill(d[2]))}” is about ${esc(d[3])}`);
  }
  return facts;
}
function openNotes(rec) {
  $("#glassHead").innerHTML = `<b>Margin notes sent to Reactor</b> · ${esc(rec.question)}`;
  $("#glassBody").innerHTML = `<pre>${esc(rec.notes || "")}</pre>`; $("#glassBody").classList.remove("rejected");
  openOverlay("#glass");
}

/* ------------------------------------------------------------------ verdict vs answer key */
const NUMW = { zero: 0, one: 1, two: 2, three: 3, four: 4, five: 5, six: 6, seven: 7, eight: 8, nine: 9, ten: 10, eleven: 11, twelve: 12, thirteen: 13, fourteen: 14, fifteen: 15, twenty: 20 };
const simp = (s) => norm(s).replace(/\b(zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|twenty)\b/g, (w) => String(NUMW[w])).replace(/[^\w\s.%]/g, " ").replace(/\.(?!\d)/g, " ").replace(/\b(the|a|an)\b/g, " ").replace(/\s+/g, " ").trim();
function goldVerdict(rec) {
  const g = rec.gold; if (!g) return null;
  if (g.abstain) return isAbstain(rec) ? "ok" : "bad";
  if (isAbstain(rec)) return "bad";
  const a = simp(rec.answer), b = simp(g.answer);
  if (!a) return "bad";
  if (b.includes(a) || a.includes(b)) return "ok";
  const na = a.match(/\d+(\.\d+)?/g), nb = b.match(/\d+(\.\d+)?/g);
  if (na && nb && na[0] === nb[0]) return "ok";
  const ta = a.split(" ").filter((w) => w.length >= 3), tb = b.split(" ").filter((w) => w.length >= 3);
  if (ta.length && tb.length) {
    const ov1 = ta.filter((w) => tb.includes(w)).length / ta.length, ov2 = tb.filter((w) => ta.includes(w)).length / tb.length;
    if (Math.max(ov1, ov2) >= .6) return "ok";
  }
  return "unsure";
}

/* ------------------------------------------------------------------ steps / banner */
function setStep(i) {
  $$("#steps li").forEach((li) => {
    const k = +li.dataset.step;
    li.classList.toggle("on", k === i); li.classList.toggle("done", k < i);
  });
}
function showQuestion(rec, caption) {
  const kind = KINDS[rec.route] || { name: "A question", sigil: "eye" };
  $("#bannerSigil").innerHTML = sigil(kind.sigil);
  $("#bannerKind").textContent = `${kind.name}${rec.live ? " · live question" : rec.split === "dev" ? " · has answer key" : ""}`;
  $("#bannerDate").textContent = rec.question_date ? `asked ${niceDate(rec.question_date, false)}` : "";
  const q = $("#question"); q.classList.remove("reveal"); void q.offsetWidth;
  const ql = (rec.question || "").length;
  q.classList.toggle("mid", ql > 72 && ql <= 110); q.classList.toggle("long", ql > 110);
  q.innerHTML = esc(rec.question || "").replace(/\?$/, '<span class="qmark">?</span>');
  q.classList.add("reveal");
  $("#caption").textContent = caption || "";
}

/* ------------------------------------------------------------------ reset */
function resetStage() {
  S.run++; S.fast = false;
  clearTimeout(S.tour.timer); clearInterval(S.askTimer);
  $("#fx").innerHTML = "";
  $$("#shelves .book").forEach((b) => { b.classList.remove("scan", "candidate", "chosen", "taken", "sealed"); b.style.removeProperty("--d"); b.querySelector(".bseal")?.remove(); });
  $("#librarian").classList.remove("searching");
  $("#pages").innerHTML = ""; $("#pages").classList.remove("rejected"); $("#pages").appendChild(deskEmpty());
  $("#pile").innerHTML = ""; $("#pile").classList.remove("has");
  $("#deskSub").textContent = "pages the Librarian brings";
  $("#notes").innerHTML = ""; $("#notes").className = "notes";
  $("#computed").hidden = true; $("#computed").className = "computed";
  setOracle("idle"); $("#orbText").innerHTML = "";
  $("#verdictLabel").textContent = "listening…"; $("#answer").className = "answer"; $("#answer").innerHTML = "";
  $("#cites").innerHTML = ""; $("#gold").hidden = true; $("#oracleActions").innerHTML = ""; $("#oracle").classList.remove("compact");
  $("#readFill").style.width = "0"; setStep(-1);
}
function deskEmpty() {
  const d = document.createElement("div"); d.className = "desk-empty";
  d.innerHTML = '<svg viewBox="0 0 120 80" aria-hidden="true"><path d="M60 18 C46 8 22 8 8 14 V70 C22 64 46 64 60 74 C74 64 98 64 112 70 V14 C98 8 74 8 60 18Z M60 18 V74"/></svg><p>The Librarian is searching…</p>';
  return d;
}
function setOracle(state) { $("#oracle").dataset.state = state; }

/* ------------------------------------------------------------------ the show */
function featuredPassages(rec) {
  const ps = (rec.passages || []).map((p, i) => ({ ...p, e: i + 1 }));
  const cited = new Set(rec.cited || []);
  const scored = ps.map((p) => ({ p, s: (cited.has(p.id) ? 100 : 0) + renderPassage(p.text, rec, "").hits * 10 - p.e * .01 }));
  scored.sort((a, b) => b.s - a.s);
  const feat = scored.slice(0, 3).map((x) => x.p).sort((a, b) => (parseDate(a.date) || 0) - (parseDate(b.date) || 0) || a.e - b.e);
  const featIds = new Set(feat.map((p) => p.e));
  return { feat, pile: ps.filter((p) => !featIds.has(p.e)), all: ps };
}

function candidateBooks(rec, exclude) {
  const words = norm(rec.question).replace(/[^a-z0-9' ]/g, " ").split(" ").map((w) => w.replace(/'s$/, "")).filter((w) => w.length >= 4 && !STOP.has(w));
  if (!words.length) return [];
  const stems = words.map((w) => w.slice(0, 5));
  const tl = S.data.timelines[rec.history_id] || [];
  const scored = [];
  for (const t of tl) {
    if (exclude.has(t.id)) continue;
    const tt = norm(t.title);
    const s = stems.reduce((acc, st) => acc + (tt.includes(st) ? 1 : 0), 0);
    if (s) scored.push([s, t.id]);
  }
  scored.sort((a, b) => b[0] - a[0]);
  return scored.slice(0, 9).map((x) => x[1]);
}

function pageEl(p, rec, i) {
  const who = personName(rec.history_id);
  const { html } = renderPassage(p.text, rec, who, p.id);
  const tl = S.data.timelines[rec.history_id] || [];
  const idx = tl.findIndex((t) => t.id === p.id);
  const el = document.createElement("article");
  el.className = "page hidden"; el.dataset.id = p.id; el.dataset.e = p.e;
  el.tabIndex = 0; el.setAttribute("role", "button"); el.setAttribute("aria-label", `Read evidence E${p.e}, ${niceDate(p.date, false)}`);
  el.style.setProperty("--rot", `${[-0.8, 0.5, -0.35][i % 3]}deg`);
  const dd = parseDate(p.date);
  const dShort = dd ? `${dd.getDate()} ${MONTHS[dd.getMonth()]} ${dd.getFullYear()}` : esc(p.date || "");
  const tShort = dd ? `${["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"][dd.getDay()]} ${String(dd.getHours()).padStart(2, "0")}:${String(dd.getMinutes()).padStart(2, "0")}` : "";
  el.innerHTML = `<div class="page-head"><span class="elabel">E${p.e}</span><span class="pdate">${dShort}</span><span class="ptime">${tShort}</span><span class="pnum" title="book ${idx + 1} of ${tl.length} on the shelves">${idx >= 0 ? `№${idx + 1}` : ""}</span></div><div class="page-body">${html}</div>`;
  el.addEventListener("click", () => openGlass(p, rec));
  el.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); e.stopPropagation(); openGlass(p, rec); } });
  return el;
}
function scrollToHighlight(page) {
  const body = page.querySelector(".page-body"); const hl = body?.querySelector(".hl-ans") || body?.querySelector(".hl-cand") || body?.querySelector(".hl-note, .hl-key");
  if (body && hl) body.scrollTop = Math.max(0, hl.offsetTop - body.clientHeight * .28);
}

function flyBook(fromEl, toEl, color, tok, dur = 900) {
  if (!toEl) return Promise.resolve();
  const to = toEl.getBoundingClientRect();
  let from = fromEl ? fromEl.getBoundingClientRect() : $("#librarian").getBoundingClientRect();
  if (!from.width) from = { left: innerWidth / 2, top: innerHeight / 3, width: 12, height: 50 };
  const f = document.createElement("div"); f.className = "flyer"; f.style.setProperty("--c", color || "#4b2f73");
  const w0 = Math.max(10, from.width), h0 = Math.max(30, from.height);
  f.style.width = w0 + "px"; f.style.height = h0 + "px";
  $("#fx").appendChild(f);
  const dx = to.left + to.width / 2 - (from.left + w0 / 2), dy = to.top + to.height / 2 - (from.top + h0 / 2);
  const sx = Math.min(8, (to.width * .32) / w0), sy = Math.min(3, (to.height * .55) / h0);
  const x0 = from.left, y0 = from.top;
  const d = S.fast ? 1 : dur;
  const anim = f.animate([
    { transform: `translate(${x0}px, ${y0}px) rotate(0deg) scale(1,1)`, opacity: 1 },
    { transform: `translate(${x0 + dx * .45}px, ${y0 + dy * .45 - 120}px) rotate(-18deg) scale(${1 + (sx - 1) * .5}, ${1 + (sy - 1) * .5})`, opacity: 1, offset: .5 },
    { transform: `translate(${x0 + dx}px, ${y0 + dy}px) rotate(0deg) scale(${sx}, ${sy})`, opacity: .0 },
  ], { duration: d, easing: "cubic-bezier(.45,.05,.35,1)", fill: "forwards" });
  if (!S.fast) sparks(from.left + w0 / 2, from.top + h0 / 2);
  return anim.finished.then(() => { f.remove(); if (tok !== S.run) throw CANCEL; }, () => { f.remove(); throw CANCEL; });
}
function sparks(x, y) {
  for (let i = 0; i < 10; i++) {
    const s = document.createElement("i"); s.className = "spark"; $("#fx").appendChild(s);
    const a = Math.random() * 6.28, r = 20 + Math.random() * 50;
    s.animate([{ transform: `translate(${x}px,${y}px) scale(1)`, opacity: 1 }, { transform: `translate(${x + Math.cos(a) * r}px,${y + Math.sin(a) * r - 20}px) scale(.2)`, opacity: 0 }], { duration: 700 + Math.random() * 400, easing: "ease-out", fill: "forwards" }).finished.then(() => s.remove(), () => s.remove());
  }
}

const sealSvg = (label) => `<span class="seal-art"><img src="assets/icon_citation.webp" alt=""><span>E${esc(label)}</span></span>`;

async function play(rec, opts = {}) {
  resetStage();
  if (S.instant) S.fast = true;
  const tok = S.run; S.rec = rec;
  if (rec.history_id !== S.hid) renderShelves(rec.history_id);
  highlightChooser();
  try {
    /* I. question */
    setStep(0);
    showQuestion(rec, opts.caption);
    $("#verdictLabel").textContent = "listening…";
    updateRibbon(rec, false);
    await sleep(1100, tok);

    /* II. search */
    setStep(1);
    const L = $("#librarian"); L.classList.add("searching");
    const arch = $("#archive"); const aw = arch.clientWidth, ah = arch.clientHeight;
    const { feat, pile, all } = featuredPassages(rec);
    moveLibrarian(aw * .04, ah * .55, "fast");
    await sleep(500, tok);
    const books = $$("#shelves .book");
    books.forEach((b) => { const r = relRect(b); b.style.setProperty("--d", `${((r.x / aw) * 1.7).toFixed(2)}s`); b.classList.add("scan"); });
    moveLibrarian(aw * .95, ah * .55, "sweep");
    await sleep(1500, tok);
    const chosenIds = new Set(all.map((p) => p.id));
    candidateBooks(rec, chosenIds).forEach((id) => bookEl(id)?.classList.add("candidate"));
    await sleep(700, tok);
    books.forEach((b) => b.classList.remove("scan"));

    // build the desk (hidden pages so we can fly to them)
    const pages = $("#pages"); pages.innerHTML = "";
    if (!all.length) {
      pages.appendChild(deskEmpty()); pages.querySelector("p").textContent = "The Librarian found no page worth bringing.";
    }
    const pageEls = feat.map((p, i) => { const el = pageEl(p, rec, i); pages.appendChild(el); return el; });
    const pileEl = $("#pile");
    const tabEls = pile.map((p) => {
      const t = document.createElement("button"); t.className = "ptab"; t.style.visibility = "hidden";
      const b = bookEl(p.id); t.style.setProperty("--c", b ? getComputedStyle(b).getPropertyValue("--c") : "#4b2f73");
      t.dataset.id = p.id; t.innerHTML = `<b>E${p.e}</b>${esc(niceDate(p.date, false))}`;
      t.addEventListener("click", () => openGlass(p, rec));
      return t;
    });
    if (tabEls.length) {
      pileEl.classList.add("has");
      pileEl.innerHTML = `<div class="pile-title">${tabEls.length} more page${tabEls.length > 1 ? "s" : ""}</div>`;
      tabEls.forEach((t) => pileEl.appendChild(t));
    }
    $("#deskSub").textContent = all.length ? `${all.length} page${all.length > 1 ? "s" : ""} brought to Reactor · E# = the label it cites` : "nothing worth bringing";
    await sleep(60, tok);

    // fly: featured (chronological) then pile
    for (let i = 0; i < pageEls.length; i++) {
      const p = feat[i], el = pageEls[i], b = bookEl(p.id);
      if (b) { const r = relRect(b); moveLibrarian(r.x + r.w / 2, r.y - 6, "fast"); }
      await sleep(520, tok);
      b?.classList.remove("candidate"); b?.classList.add("chosen");
      await sleep(260, tok);
      const color = b ? getComputedStyle(b).getPropertyValue("--c") : "#4b2f73";
      const fl = flyBook(b, el, color, tok, 950);
      await sleep(520, tok);
      b?.classList.remove("chosen"); b?.classList.add("taken");
      await fl;
      el.classList.remove("hidden"); el.classList.add("opening"); scrollToHighlight(el);
    }
    for (let i = 0; i < tabEls.length; i++) {
      const p = pile[i], b = bookEl(p.id), t = tabEls[i];
      if (i < 5 && !S.fast) {
        if (b) { const r = relRect(b); moveLibrarian(r.x + r.w / 2, r.y - 6, "fast"); }
        await sleep(240, tok);
        const color = b ? getComputedStyle(b).getPropertyValue("--c") : "#4b2f73";
        b?.classList.add("taken");
        await flyBook(b, t, color, tok, 600);
      } else b?.classList.add("taken");
      t.style.visibility = "visible";
    }
    L.classList.remove("searching"); parkLibrarian();
    updateRibbon(rec, true);
    await sleep(400, tok);

    /* III. margin notes */
    setStep(2);
    await writeNotes(rec, tok);
    await sleep(500, tok);

    /* IV. oracle */
    setStep(3);
    if (rec.live && rec.answer == null) { await oracleLive(rec, tok, opts); return; }
    await revealOracle(rec, tok);
    if (S.tour.playing && opts.fromTour && !S.stage) {
      S.tour.timer = setTimeout(() => { if (tok === S.run && S.tour.playing) tourStep(1); }, 9000);
    }
  } catch (e) {
    if (e !== CANCEL) { console.warn(e); }
  }
}

async function writeNotes(rec, tok) {
  const facts = noteFacts(rec);
  const box = $("#notes"); box.innerHTML = ""; box.className = "notes";
  const comp = $("#computed");
  if (rec.computed != null && String(rec.computed).trim() !== "") {
    if (rec.route === "temporal") {
      const unit = /years?/i.test(rec.question) ? "years" : /months?/i.test(rec.question) ? "months" : /weeks?/i.test(rec.question) ? "weeks" : "days";
      comp.innerHTML = `<small>computed by code, not by Reactor</small><span class="cval">${esc(rec.computed)} ${unit}</span>`;
    } else {
      comp.innerHTML = `<small>code's candidate</small><span class="cval">${esc(rec.computed)}</span>`;
    }
    comp.hidden = false; comp.classList.add("write");
    await sleep(700, tok);
  }
  const rule = comp.hidden && NOTE_RULE[rec.route]; // a computed value already says what the code did
  if (rule) {
    box.insertAdjacentHTML("beforeend", `<div class="note-rule write" data-r="${esc(rec.route)}"><span>${esc(rule)}</span></div>`);
    await sleep(450, tok);
  }
  if (!facts.length) box.insertAdjacentHTML("beforeend", `<p class="note-empty">${esc(NOTE_EMPTY[rec.route] || "The pages speak for themselves.")}</p>`);
  for (const f of facts) {
    const p = document.createElement("p");
    p.className = "fact write"; p.innerHTML = f;
    box.appendChild(p);
    box.scrollTop = box.scrollHeight;
    await sleep(Math.min(900, 300 + f.length * 2), tok);
  }
  if (String(rec.notes || "").trim()) {
    box.insertAdjacentHTML("beforeend", '<button class="notes-link">What the code told Reactor</button>');
    box.querySelector(".notes-link").addEventListener("click", () => openNotes(rec));
  }
  await sleep(300, tok);
  box.scrollTop = 0;
}

/* after Reactor speaks, the margin's candidate is either confirmed or struck through with the reason */
function judgeCandidate(rec) {
  const comp = $("#computed"); if (comp.hidden) return;
  comp.querySelector(".cverdict")?.remove(); comp.classList.remove("rejected", "agreed");
  const v = candidateVerdict(rec); if (!v) return;
  if (!v.rejected) {
    comp.classList.add("agreed");
    comp.insertAdjacentHTML("beforeend", '<span class="cverdict">✓ Reactor agrees</span>');
    return;
  }
  comp.classList.add("rejected"); $("#pages").classList.add("rejected");
  const c = String(rec.computed).trim();
  let why;
  if (v.why === "differs") why = `Reactor chose <b>${esc(String(rec.answer).trim())}</b> instead`;
  else {
    const src = candidateSource(rec);
    if (src) {
      const q = esc(quoteAround(src.sent, c)); const f = findWord(q, esc(c));
      why = `E${src.e} says: “${f ? `${f[0]}<u>${f[1]}</u>${f[2]}` : q}”`;
    } else why = "the pages never say it is the user's own";
  }
  comp.insertAdjacentHTML("beforeend", `<span class="cverdict"><b class="rej">${esc(c)}: rejected</b> · ${why}</span>`);
}

async function revealOracle(rec, tok) {
  setOracle("thinking");
  $("#verdictLabel").textContent = "Reactor reads the pages…";
  await sleep(1900, tok);
  showAnswer(rec);
}

function showAnswer(rec) {
  const abst = isAbstain(rec);
  const ans = $("#answer"); const orb = $("#orbText");
  const n = (rec.passages || []).length;
  if (abst) {
    setOracle("abstained");
    $("#verdictLabel").textContent = "Reactor answers";
    ans.className = "answer none reveal";
    ans.innerHTML = `Not written in the archive<span class="sub">So it doesn't guess.</span>`;
    orb.className = "orb-text"; orb.innerHTML = sigil("none");
  } else {
    setOracle("answered");
    $("#verdictLabel").textContent = "Reactor answers";
    const a = String(rec.answer || "").trim();
    ans.className = "answer reveal" + (a.length > 26 ? " long" : a.length > 6 ? " mid" : "");
    ans.innerHTML = `<span class="aval">${esc(a)}</span>`; // the brass answer window sizes itself to this
    ans.insertAdjacentHTML("beforeend", tallyHtml(oracleTally(rec), a));
    orb.className = "orb-text" + (a.length > 4 ? " med" : "");
    orb.innerHTML = a.length <= 14 ? esc(a) : sigil((KINDS[rec.route] || KINDS.ssu).sigil);
  }
  judgeCandidate(rec);
  // seals
  const cited = rec.cited || [];
  const idxOf = new Map((rec.passages || []).map((p, i) => [p.id, i + 1]));
  const cites = cited.map((id) => idxOf.get(id)).filter(Boolean);
  $("#cites").innerHTML = cites.length
    ? `<span>cites</span>${cites.map((e) => `<span class="c"><i></i>E${e}</span>`).join("")}`
    : (abst ? "<span>no page cited</span>" : "");
  $$("#pages .page").forEach((pg) => {
    if (cited.includes(pg.dataset.id)) { pg.insertAdjacentHTML("beforeend", sealSvg(pg.dataset.e)); }
    else if (cited.length) pg.classList.add("dim");
  });
  $$("#pile .ptab").forEach((t) => t.classList.toggle("cited", cited.includes(t.dataset.id)));
  cited.forEach((id) => { const b = bookEl(id); if (b) { b.classList.add("sealed"); b.insertAdjacentHTML("beforeend", '<i class="bseal"></i>'); } });
  if (cited.length) parkLibrarian();
  // answer key (dev)
  const g = $("#gold"); const v = goldVerdict(rec);
  if (v) {
    const goldText = rec.gold.abstain ? "not in the archive" : rec.gold.answer;
    g.className = "gold " + v; g.hidden = false;
    const gt = goldText.length > 70 ? goldText.slice(0, 68) + "…" : goldText;
    g.innerHTML = `${v === "ok" ? '<span class="gmark">✓</span><b>answer key agrees</b>' : v === "bad" ? '<span class="gmark">✗</span><b>answer key says</b>' : "<b>answer key says</b>"}<span class="gt">${esc(gt)}</span>`;
    g.title = goldText;
    $("#oracle").classList.add("compact");
  }
  // actions
  const lat = rec.latency_s != null ? ` in ${Number(rec.latency_s).toFixed(0)} s` : "";
  $("#oracleActions").innerHTML = `<p>${rec.live ? "live answer" : "recorded answer"}${lat}${rec.reasoning ? ' · <button class="reply-link" id="replyLink">full reply</button>' : ""}</p>`;
  $("#replyLink")?.addEventListener("click", () => openReply(rec));
  updateRibbon(rec, true);
  setStep(4);
  markSeen();
  // a long verdict (answer key, tally, many cites) shrinks the orb instead of being cut off
  requestAnimationFrame(() => { const v = $("#verdict"); if (v.scrollHeight > v.clientHeight + 2) $("#oracle").classList.add("compact"); });
}

/* ------------------------------------------------------------------ live mode */
async function oracleLive(rec, tok, opts) {
  const acts = $("#oracleActions");
  $("#verdictLabel").textContent = "the dossier is ready";
  $("#answer").className = "answer"; $("#answer").innerHTML = "";
  if (S.busy) { oracleBusy(); return; }
  if (opts.ask) { await askOracle(rec, tok); return; }
  setOracle("sleeping");
  if (S.stage) { /* on stage a live answer (1-2 min) is never started; the dossier is the live part */
    acts.innerHTML = `<p>The Librarian built this dossier${rec.build_ms != null ? ` in ${fmt(rec.build_ms)} ms` : ""}, live. Reactor's own answer takes 1–2 minutes, so the recorded questions show that step.</p>`;
    return;
  }
  acts.innerHTML = `<p>The Librarian built this dossier${rec.build_ms != null ? ` in ${fmt(rec.build_ms)} ms` : ""}.</p><button class="btn btn-gold" id="consultBtn"><svg viewBox="0 0 24 24"><path d="M8 5l11 7-11 7z"/></svg>Consult Reactor</button><p>about 1–2 minutes</p>`;
  $("#consultBtn").addEventListener("click", () => askOracle(rec, S.run));
}
function oracleBusy() {
  setOracle("busy");
  $("#verdictLabel").textContent = "Reactor is busy";
  $("#answer").className = "answer none"; $("#answer").innerHTML = `Busy with the benchmark run<span class="sub">Replaying recorded answers only. No answer is ever faked.</span>`;
  $("#oracleActions").innerHTML = "";
}
async function askOracle(rec, tok) {
  if (tok !== S.run) return;
  setOracle("thinking");
  $("#verdictLabel").textContent = "Reactor is reading…";
  const t0 = Date.now();
  $("#oracleActions").innerHTML = `<p class="timer" id="askTimer">0 s</p><p>Live answers take about 1–2 minutes.</p>`;
  clearInterval(S.askTimer);
  S.askTimer = setInterval(() => { const el = $("#askTimer"); if (el) el.textContent = `${Math.round((Date.now() - t0) / 1000)} s`; }, 1000);
  const body = rec.history_question_id ? { question_id: rec.history_question_id, question: rec.question } : { question_id: rec.question_id };
  try {
    const r = await fetch("/api/ask", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    clearInterval(S.askTimer);
    if (tok !== S.run) return;
    if (r.status === 409) { S.busy = true; renderStatus(); oracleBusy(); return; }
    const j = await r.json().catch(() => ({}));
    if (!r.ok || j.error) throw new Error(j.error || `HTTP ${r.status}`);
    const merged = { ...rec, ...j, live: true, split: rec.split, history_id: rec.history_id };
    S.rec = merged;
    showAnswer(merged);
  } catch (e) {
    clearInterval(S.askTimer);
    if (tok !== S.run) return;
    setOracle("sleeping");
    $("#verdictLabel").textContent = "Reactor could not be reached";
    $("#answer").className = "answer none"; $("#answer").innerHTML = `No answer<span class="sub">${esc(String(e.message || e)).slice(0, 160)}</span>`;
    $("#oracleActions").innerHTML = "";
  }
}
async function livePack(ask) {
  const q = $("#liveQ").value.trim(); if (!q) { $("#liveQ").focus(); return; }
  const ref = [...S.data.test, ...S.data.dev].find((r) => r.history_id === S.hid);
  if (!ref) return;
  stopTour();
  if (ask && S.busy) { /* still build the pack, then show busy */ }
  closeDrawer();
  resetStage();
  const tok = S.run;
  showQuestion({ question: q, route: null, live: true, question_date: ref.question_date }, "Live: the Librarian is searching the archive right now…");
  setStep(1);
  $("#librarian").classList.add("searching");
  const arch = $("#archive"); moveLibrarian(arch.clientWidth * .5, arch.clientHeight * .5, "sweep");
  try {
    const r = await fetch("/api/pack", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question_id: ref.question_id, question: q }) });
    const j = await r.json().catch(() => ({}));
    if (tok !== S.run) return;
    if (!r.ok || j.error) throw new Error(j.error || `HTTP ${r.status}`);
    const rec = { ...j, split: ref.split, history_id: ref.history_id, question: q, live: true, answer: null, abstained: false, cited: [], latency_s: null, reasoning: "", history_question_id: ref.question_id };
    play(rec, { caption: `Live question about ${personName(ref.history_id)}${rec.build_ms != null ? ` · dossier built in ${fmt(rec.build_ms)} ms` : ""}`, ask });
  } catch (e) {
    if (tok !== S.run) return;
    $("#librarian").classList.remove("searching"); parkLibrarian();
    $("#caption").textContent = "The Librarian's search engine did not answer (" + String(e.message || e).slice(0, 120) + "). Recorded questions still work.";
    setStep(-1);
  }
}

/* ------------------------------------------------------------------ ribbon */
function updateRibbon(rec, done) {
  const st = archiveStats(rec.history_id);
  const sent = (rec.passages || []).reduce((a, p) => a + (p.text || "").length, 0);
  const convs = `<em>${fmt(st.n)}</em> conversation${st.n === 1 ? "" : "s"}`;
  if (!done) {
    $("#readBig").innerHTML = `The archive holds ${convs}`;
    $("#readSmall").textContent = `${fmt(st.total)} characters${st.estimated ? " (est.)" : ""} · Reactor may read only a few pages`;
    $("#readFill").style.width = "0";
    return;
  }
  const n = (rec.passages || []).length;
  const pct = st.total ? (sent / st.total) * 100 : 0;
  const pctTxt = pct > 0 && pct < .01 ? "<0.01" : pct.toFixed(2);
  $("#readBig").innerHTML = n ? `Reactor read <em>${n} page${n === 1 ? "" : "s"}</em> out of ${convs} · <em>${pctTxt}%</em> of the archive` : `Reactor read <em>nothing</em> from the archive`;
  $("#readFill").style.width = `${Math.max(pct ? 1.2 : 0, Math.min(100, pct * 8))}%`;
  const lat = rec.latency_s == null && rec.build_ms != null ? ` · pages found in ${(rec.build_ms / 1000).toFixed(1)} s` : "";
  $("#readSmall").textContent = `${fmt(sent)} of ${fmt(st.total)} characters${st.estimated ? " (est.)" : ""}${lat}`;
}

/* ------------------------------------------------------------------ tour */
function tourRecords() { return TOUR.map((t) => ({ ...t, rec: S.byId.get(t.id) })).filter((t) => t.rec); }
function renderTourDots() {
  const tr = tourRecords();
  $("#tourDots").innerHTML = tr.map((t, i) => {
    const k = KINDS[t.rec.route] || KINDS.ssu; const abst = isAbstain(t.rec);
    const short = { ssu: "Fact", ssa: "Advice", multi: "Counting", ku: "Changed", temporal: "Dates" }[t.rec.route] || "Question";
    return `<button class="tdot" data-i="${i}" title="${esc(t.rec.question)}">${sigil(abst ? "none" : k.sigil)}${abst ? "Not written" : short}</button>`;
  }).join("");
  $$("#tourDots .tdot").forEach((b) => b.addEventListener("click", () => tourGo(+b.dataset.i, S.tour.playing)));
}
function tourGo(i, playing) {
  const tr = tourRecords(); if (!tr.length) return;
  S.tour.idx = ((i % tr.length) + tr.length) % tr.length;
  S.tour.playing = !!playing; syncTourBtn();
  $$("#tourDots .tdot").forEach((b, k) => b.classList.toggle("on", k === S.tour.idx));
  const t = tr[S.tour.idx];
  play(t.rec, { fromTour: true });
}
function tourStep(d) { tourGo(S.tour.idx < 0 ? (d > 0 ? 0 : tourRecords().length - 1) : S.tour.idx + d, S.tour.playing); }
function stopTour() { S.tour.playing = false; clearTimeout(S.tour.timer); syncTourBtn(); $$("#tourDots .tdot").forEach((b) => b.classList.remove("on")); S.tour.idx = -1; }
function togglePlay() {
  if (S.stage) { tourStep(1); return; } /* presenter mode: every press plays the next question, nothing advances on its own */
  if (S.tour.playing) { S.tour.playing = false; clearTimeout(S.tour.timer); syncTourBtn(); return; }
  S.tour.playing = true; syncTourBtn();
  const cur = S.rec && $("#oracle").dataset.state;
  if (S.tour.idx >= 0 && (cur === "answered" || cur === "abstained")) tourStep(1);
  else if (S.tour.idx >= 0) { /* animation running: it will advance when done */ const tok = S.run; S.tour.timer = setTimeout(function chk() { if (tok !== S.run || !S.tour.playing) return; const st = $("#oracle").dataset.state; if (st === "answered" || st === "abstained") tourStep(1); else S.tour.timer = setTimeout(chk, 1500); }, 1500); }
  else tourGo(0, true);
}
function syncTourBtn() {
  const b = $("#btnTour");
  b.querySelector("span").textContent = S.stage ? (S.tour.idx >= 0 ? "Next question" : "Begin the tour") : S.tour.playing ? "Pause the tour" : S.tour.idx >= 0 ? "Resume the tour" : "Begin the tour";
  b.querySelector("svg").innerHTML = S.tour.playing && !S.stage ? '<path d="M7 5h4v14H7zM13 5h4v14h-4z"/>' : '<path d="M8 5l11 7-11 7z"/>';
}
function markSeen() { if (S.tour.idx >= 0) $$("#tourDots .tdot")[S.tour.idx]?.classList.add("seen"); }

/* ------------------------------------------------------------------ chooser */
function renderPeople() {
  const sel = $("#personSel");
  const testH = [...new Set(S.data.test.map((r) => r.history_id))];
  let html = '<optgroup label="Test archives (~200 conversations each)">';
  testH.forEach((h) => { const c = S.data.test.filter((r) => r.history_id === h).length; html += `<option value="${h}">${esc(personName(h))} · ${c} questions</option>`; });
  html += "</optgroup>";
  if (S.data.dev.length) html += `<optgroup label="Calibration set"><option value="__dev">Answer-key set · ${S.data.dev.length} questions, one per reader</option></optgroup>`;
  sel.innerHTML = html;
  sel.addEventListener("change", () => renderQuestions(sel.value));
}
function renderQuestions(key) {
  const recs = key === "__dev" ? S.data.dev : S.data.test.filter((r) => r.history_id === key);
  $("#personSel").value = key;
  $("#personDesc").textContent = key === "__dev" ? "Each question comes from a different ~50-conversation archive, with the official answer key." : (person(key)?.desc || "");
  const tourIds = new Set(TOUR.map((t) => t.id));
  let html = "";
  for (const k of KIND_ORDER) {
    const list = recs.filter((r) => r.route === k); if (!list.length) continue;
    html += `<div class="qgroup"><h3>${sigil(KINDS[k].sigil)}${KINDS[k].name}<small>${KINDS[k].hint}</small></h3>`;
    list.forEach((r) => {
      const tag = tourIds.has(r.question_id) ? '<span class="tag">tour</span>' : r.gold ? '<span class="tag key">key</span>' : isAbstain(r) ? '<span class="tag no">not written</span>' : "";
      html += `<button class="qbtn" data-id="${r.question_id}">${esc(r.question)}${tag}</button>`;
    });
    html += "</div>";
  }
  const other = recs.filter((r) => !KINDS[r.route]);
  if (other.length) html += `<div class="qgroup"><h3>${sigil("eye")}Other</h3>${other.map((r) => `<button class="qbtn" data-id="${r.question_id}">${esc(r.question)}</button>`).join("")}</div>`;
  $("#qGroups").innerHTML = html || '<p class="person-desc">No recorded questions here.</p>';
  $$("#qGroups .qbtn").forEach((b) => b.addEventListener("click", () => {
    const rec = S.byId.get(b.dataset.id); if (!rec) return;
    stopTour(); closeDrawer(); play(rec);
  }));
  if (key !== "__dev" && key !== S.hid && S.data.timelines[key]) { /* preview that archive */ resetStage(); renderShelves(key); idleBanner(); }
  highlightChooser();
}
function highlightChooser() { $$("#qGroups .qbtn").forEach((b) => b.classList.toggle("cur", S.rec && b.dataset.id === S.rec.question_id)); }
function openDrawer() {
  const key = S.rec ? (S.rec.split === "dev" ? "__dev" : S.rec.history_id) : (S.hid || $("#personSel").value);
  if ($("#personSel").value !== key) renderQuestions(key);
  $("#drawer").classList.add("open"); $("#drawer").setAttribute("aria-hidden", "false");
}
function closeDrawer() { $("#drawer").classList.remove("open"); $("#drawer").setAttribute("aria-hidden", "true"); }
function idleBanner() {
  $("#bannerSigil").innerHTML = sigil("eye");
  $("#bannerKind").textContent = "The archive awaits a question"; $("#bannerDate").textContent = "";
  $("#question").className = "question"; $("#question").textContent = `${personName(S.hid)} talked with an AI assistant for months. Ask what they once said.`;
  $("#caption").textContent = "Press Space for the tour, or Q to choose a question.";
  $("#verdictLabel").textContent = "waiting for a question";
  const st = archiveStats(S.hid);
  $("#readBig").innerHTML = `The archive holds <em>${fmt(st.n)}</em> conversations`;
  $("#readSmall").textContent = `${fmt(st.total)} characters · Reactor may read only a few pages`;
}

/* ------------------------------------------------------------------ overlays */
function openGlass(p, rec) {
  const { html } = renderPassage(p.text, rec, personName(rec.history_id), p.id);
  const cited = (rec.cited || []).includes(p.id) && rec.answer != null;
  $("#glassHead").innerHTML = `<b>E${p.e}</b> · ${esc(niceDate(p.date))}${cited ? " · cited by Reactor" : ""}`;
  $("#glassBody").innerHTML = html;
  $("#glassBody").classList.toggle("rejected", !!(candidateVerdict(rec)?.rejected));
  openOverlay("#glass");
}
function openReply(rec) {
  $("#glassHead").innerHTML = `<b>Reactor's full reply</b> · ${esc(rec.question)}`;
  $("#glassBody").innerHTML = `<pre>${esc(rec.reasoning || "")}</pre>`; $("#glassBody").classList.remove("rejected");
  openOverlay("#glass");
}
let overlayReturnFocus = null;
function openOverlay(sel) { overlayReturnFocus = document.activeElement; $(sel).classList.add("open"); $(sel).setAttribute("aria-hidden", "false"); $(sel).querySelector("button")?.focus(); }
function closeOverlays() { $$(".overlay").forEach((o) => { o.classList.remove("open"); o.setAttribute("aria-hidden", "true"); }); closeDrawer(); overlayReturnFocus?.focus({preventScroll:true}); overlayReturnFocus = null; }

/* ------------------------------------------------------------------ status */
async function pollStatus() {
  try {
    const ctl = new AbortController(); const t = setTimeout(() => ctl.abort(), 4000);
    const r = await fetch("/api/status", { signal: ctl.signal, cache: "no-store" }); clearTimeout(t);
    const j = await r.json(); S.busy = !!j.reactor_busy; S.statusOk = true;
  } catch { S.statusOk = false; S.busy = null; }
  renderStatus();
}
function renderStatus() {
  const p = $("#statusPill");
  p.classList.toggle("busy", S.busy === true); p.classList.toggle("live", S.busy === false);
  p.querySelector("span").textContent = S.busy === true ? "Reactor busy · replay ready" : S.busy === false ? "Reactor available · live ready" : "Replay mode";
  $("#btnAsk").disabled = S.busy === true || !S.statusOk;
  $("#btnPack").disabled = !S.statusOk;
  $("#liveNote").textContent = !S.statusOk
    ? "Live search needs the demo server's API; recorded questions work without it."
    : S.busy ? "Reactor is busy with the benchmark run: the Librarian can still search live (Find the pages), but answers are replay only. Nothing is faked."
      : "Reactor is free: live answers take about 1–2 minutes.";
}

/* ------------------------------------------------------------------ keys & wiring */
function toggleFull() {
  if (!document.fullscreenElement) document.documentElement.requestFullscreen?.().catch(() => {});
  else document.exitFullscreen?.().catch(() => {});
}
function wire() {
  $("#btnTour").addEventListener("click", togglePlay);
  $("#btnFull").addEventListener("click", toggleFull);
  $("#btnQuestions").addEventListener("click", openDrawer);
  $("#drawerClose").addEventListener("click", closeDrawer);
  $("#drawer").addEventListener("click", (e) => { if (e.target.id === "drawer") closeDrawer(); });
  $("#btnHow").addEventListener("click", () => document.querySelector("#method").scrollIntoView({behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth"}));
  $("#howClose").addEventListener("click", closeOverlays);
  $("#glassClose").addEventListener("click", closeOverlays);
  $$(".overlay").forEach((o) => o.addEventListener("click", (e) => { if (e.target === o) closeOverlays(); }));
  $("#btnPack").addEventListener("click", () => livePack(false));
  $("#btnAsk").addEventListener("click", () => livePack(true));
  $("#liveQ").addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); livePack(false); } });
  addEventListener("keydown", (e) => {
    const tag = (e.target.tagName || "").toLowerCase();
    if (tag === "textarea" || tag === "input" || tag === "select") { if (e.key === "Escape") e.target.blur(); return; }
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    if (e.target.closest("#method") || (scrollY > $("#app").offsetHeight * .65 && !$(".overlay.open") && !$("#drawer.open"))) return;
    switch (e.key) {
      case "ArrowRight": case "PageDown": e.preventDefault(); closeOverlays(); tourStep(1); break;
      case "ArrowLeft": case "PageUp": e.preventDefault(); closeOverlays(); tourStep(-1); break;
      case " ": e.preventDefault(); closeOverlays(); togglePlay(); break;
      case "f": case "F": toggleFull(); break;
      case "q": case "Q": $("#drawer").classList.contains("open") ? closeDrawer() : openDrawer(); break;
      case "h": case "H": closeOverlays(); document.querySelector("#method").scrollIntoView({behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth"}); break;
      case "s": case "S": S.fast = true; break;
      case "Escape": closeOverlays(); break;
      default:
        if (/^[1-9]$/.test(e.key) && +e.key <= tourRecords().length) { e.preventDefault(); closeOverlays(); tourGo(+e.key - 1, S.tour.playing); }
    }
  });
  let rt; addEventListener("resize", () => { clearTimeout(rt); rt = setTimeout(() => { if ($("#oracle").dataset.state === "idle" || $("#oracle").dataset.state === "answered" || $("#oracle").dataset.state === "abstained") parkLibrarian(); }, 150); });
}

/* ------------------------------------------------------------------ boot */
async function boot() {
  S.stage = new URLSearchParams(location.search).get("stage") === "1";
  document.body.classList.toggle("stage", S.stage);
  decorate(); wire();
  try {
    const r = await fetch("/replay.json", { cache: "no-store" });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    S.data = await r.json();
  } catch (e) {
    $("#loading p").textContent = "The archive could not be opened (replay.json: " + (e.message || e) + ").";
    return;
  }
  S.data.test = S.data.test || []; S.data.dev = S.data.dev || []; S.data.timelines = S.data.timelines || {};
  try { const r = await fetch("sizes.json"); if (r.ok) S.sizes = await r.json(); } catch { S.sizes = {}; }
  for (const r of [...S.data.test, ...S.data.dev]) S.byId.set(r.question_id, r);
  renderPeople(); renderTourDots();
  const first = tourRecords()[0]?.rec?.history_id || S.data.test[0]?.history_id || Object.keys(S.data.timelines)[0];
  if (first) { renderShelves(first); renderQuestions(S.data.test.some((r) => r.history_id === first) ? first : "__dev"); }
  idleBanner(); syncTourBtn();
  setTimeout(() => $("#loading").classList.add("gone"), 250);
  pollStatus(); setInterval(pollStatus, 10000);
  const qs = new URLSearchParams(location.search);
  S.instant = qs.get("instant") === "1" || matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (qs.get("q") && S.byId.get(qs.get("q"))) play(S.byId.get(qs.get("q")), {});
  else if (qs.has("tour")) tourGo(+(qs.get("tour") || 0), qs.get("play") === "1");
}
window.__librarian = { play, S, tourGo };
boot();
})();
