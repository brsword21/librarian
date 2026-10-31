/* The Librarian: pixel wizard-tower demo. Replays recorded answers; live mode via /api/pack and /api/ask. */
(function () {
  "use strict";
  const $ = (s) => document.querySelector(s);
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const fmt = (n) => Math.round(n).toLocaleString("en-US");

  const KINDS = {
    ssu: { name: "Personal facts", trick: "Only YOUR facts: friends' & family's don't count" },
    ssa: { name: "Advice I was given", trick: "Only what the assistant itself recommended" },
    multi: { name: "Counting across time", trick: "List every instance, count once, skip decoys" },
    ku: { name: "Things that changed", trick: "The most recent value wins" },
    temporal: { name: "Dates & durations", trick: "Dates found, day gap computed by code" },
  };
  const KIND_ORDER = ["ssu", "ssa", "multi", "ku", "temporal"];
  const TOUR = [
    { id: "q_62e927862f62", cap: "The instructor changed: the latest value wins" },
    { id: "q_06ae4afa8961", cap: "Two dates found, the gap computed by code" },
    { id: "q_392fdc44c911", cap: "What the assistant itself recommended" },
    { id: "q_31e7201b2c55", cap: "Counting across months, skipping a friend's purchase" },
    { id: "q_499fc53af8ca", cap: "Not in the archive, and it says so (checked against the answer key)" },
  ];
  const CHARS_PER_CONV = 8000; // ~1.6M characters per 200 conversations
  const CHARS_PER_PAGE = 1000;
  const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const BOOKC = [
    ["#8c2f3c", "#5a1a26", "#c25466", "#e0b04a"], ["#2f4f8c", "#1c2f5a", "#5478c2", "#e0b04a"], ["#3f7a3a", "#244a22", "#68a95e", "#f0d070"],
    ["#8c6a2f", "#5a421a", "#c2994f", "#3a2410"], ["#5f2f8c", "#3a1a5a", "#8a54c2", "#e0b04a"], ["#2f7a7a", "#1a4a4a", "#4fb0a8", "#f0d070"],
    ["#9a4a2a", "#5f2a14", "#cf7445", "#2a1408"], ["#4a4a6a", "#2a2a40", "#7676a0", "#d8c070"], ["#6b2a4a", "#40142c", "#a04a74", "#e0b04a"],
  ];

  const S = {
    data: null, recs: {}, split: "test", person: null, current: null, runId: 0, running: false,
    tourIdx: -1, autoplay: false, holdTimer: null, busy: null, shownHistory: null, books: {}, timelines: {},
    persons: [], wizFrames: [], live: false,
  };

  class Cancel extends Error {}
  const sleep = (ms, id) => new Promise((res, rej) => setTimeout(() => (id !== undefined && id !== S.runId ? rej(new Cancel()) : res()), ms));
  const alive = (id) => { if (id !== S.runId) throw new Cancel(); };

  // ---------- boot: textures + sprites ----------
  const root = document.documentElement.style;
  document.body.style.backgroundImage = `url(${PX.stoneTile()})`;
  root.setProperty("--wood-tile", `url(${PX.woodTile("#6b4220", "#4a2a12", "#8a5a2e")})`);
  root.setProperty("--desk-tile", `url(${PX.woodTile("#4a2c16", "#36200e", "#5e3a1e")})`);
  root.setProperty("--moss-tile", `url(${PX.mossTile()})`);
  root.setProperty("--parch-tile", `url(${PX.parchTile()})`);
  root.setProperty("--seal", `url(${PX.sealURL()})`);
  root.setProperty("--flame", `url(${PX.flameSheet(3)})`);
  const SEAL_URL = PX.sealURL();
  S.wizFrames = PX.wizardFrames(1);
  $("#wizImg").src = S.wizFrames[0];
  $("#logo").src = PX.icon("eye", 6);
  document.querySelectorAll("[data-icon]").forEach((im) => {
    im.src = im.dataset.icon === "wizard" ? S.wizFrames[2] : PX.icon(im.dataset.icon, 6);
  });

  const fx = PX.FX($("#fx"));
  const oracle = PX.Oracle($("#oracle"));
  (function loop(t) { fx.tick(); oracle.draw(t); requestAnimationFrame(loop); })(0);

  const center = (el) => { const r = el.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; };

  // ---------- data ----------
  async function boot() {
    try {
      const r = await fetch("/replay.json", { cache: "no-store" });
      if (!r.ok) throw new Error("HTTP " + r.status);
      S.data = await r.json();
    } catch (e) {
      const d = document.createElement("div"); d.className = "fatal";
      d.textContent = "The archive could not be opened (replay.json: " + e.message + "). Start demo.server and reload.";
      document.body.appendChild(d); return;
    }
    S.timelines = S.data.timelines || {};
    for (const sp of ["test", "dev"]) for (const r of S.data[sp] || []) { r.split = r.split || sp; S.recs[r.question_id] = r; }
    S.persons = [...new Set((S.data.test || []).map((r) => r.history_id))];
    S.person = S.persons[0] || null;
    S.tour = TOUR.filter((t) => S.recs[t.id]);
    if (!S.tour.length) S.tour = (S.data.test || []).slice(0, 5).map((r) => ({ id: r.question_id, cap: "" }));
    renderTourbar();
    renderChooser();
    renderRail();
    pollStatus(); setInterval(pollStatus, 20000);
    // first view: the archive of the first tour question, then the title card
    const first = S.recs[S.tour[0].id];
    if (first) { S.split = first.split; if (first.split === "test") S.person = first.history_id; renderChooser(); prepare(first); idleBanner(first); }
    showHow(true);
  }

  // ---------- header: status + tour ----------
  async function pollStatus() {
    const b = $("#status");
    try {
      const r = await fetch("/api/status", { cache: "no-store" });
      const j = await r.json();
      S.busy = !!j.reactor_busy; S.live = true;
      b.className = "badge " + (S.busy ? "busy" : "live");
      b.textContent = S.busy ? "ORACLE BUSY · REPLAYING RECORDED ANSWERS" : "ORACLE AWAKE · LIVE";
    } catch (e) {
      S.busy = null; S.live = false;
      b.className = "badge"; b.textContent = "REPLAY MODE";
    }
  }
  function renderTourbar() {
    const tb = $("#tourbar"); tb.innerHTML = "";
    S.tour.forEach((t, i) => {
      const r = S.recs[t.id];
      const b = document.createElement("button");
      b.className = "tdot" + (i === S.tourIdx ? " on" : i < S.tourIdx ? " done" : "");
      b.title = r.question;
      b.innerHTML = `<img src="${PX.icon(r.route, 3)}" alt=""><span class="tnum">${i + 1}</span>`;
      b.onclick = () => goTour(i);
      tb.appendChild(b);
    });
    $("#bPlay").textContent = S.autoplay ? "❚❚ PAUSE" : "▶ TOUR";
    $("#bPlay").classList.toggle("on", S.autoplay);
  }

  // ---------- chooser ----------
  function roman(n) { return ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"][n] || String(n + 1); }
  function renderChooser() {
    const tabs = $("#splitTabs");
    tabs.innerHTML = `<button data-s="test" class="${S.split === "test" ? "on" : ""}">RECORDED</button><button data-s="dev" class="${S.split === "dev" ? "on" : ""}">WITH ANSWER KEY</button>`;
    tabs.querySelectorAll("button").forEach((b) => (b.onclick = () => { S.split = b.dataset.s; renderChooser(); }));
    const tomes = $("#tomes");
    if (S.split === "test") {
      tomes.style.display = "";
      tomes.innerHTML = S.persons.map((h, i) => `<button data-h="${h}" class="${h === S.person ? "on" : ""}" title="${(S.timelines[h] || []).length} conversations">TOME ${roman(i)}</button>`).join("");
      tomes.querySelectorAll("button").forEach((b) => (b.onclick = () => { S.person = b.dataset.h; renderChooser(); }));
    } else { tomes.style.display = "none"; tomes.innerHTML = ""; }
    const list = (S.data[S.split] || []).filter((r) => S.split !== "test" || r.history_id === S.person);
    const ql = $("#qlist"); ql.innerHTML = "";
    for (const k of KIND_ORDER) {
      const items = list.filter((r) => r.route === k);
      if (!items.length) continue;
      const g = document.createElement("div"); g.className = "kgroup";
      g.innerHTML = `<div class="khead"><img src="${PX.icon(k, 3)}" alt="">${KINDS[k].name.toUpperCase()}<span class="kc">${items.length}</span></div>`;
      for (const r of items) {
        const b = document.createElement("button");
        b.className = "qitem" + (S.current && S.current.question_id === r.question_id ? " on" : "");
        b.dataset.id = r.question_id;
        let mark = "";
        if (r.gold) { const v = judge(r); mark = v === "ok" ? `<span class="qm ok">✓</span>` : v === "bad" ? `<span class="qm bad">✗</span>` : `<span class="qm">≈</span>`; }
        else if (r.abstained) mark = `<span class="qm none">NOT IN ARCHIVE</span>`;
        b.innerHTML = esc(r.question) + mark;
        b.onclick = () => { stopTour(); playRec(r); };
        g.appendChild(b);
      }
      ql.appendChild(g);
    }
    if (!ql.children.length) ql.innerHTML = `<div class="a-idle">No questions here yet.</div>`;
    const who = S.current ? personLabel(S.current.history_id) : "THIS PERSON";
    $("#askWho").textContent = who;
  }
  function personLabel(h) {
    const i = S.persons.indexOf(h);
    return i >= 0 ? "TOME " + roman(i) : "THIS PERSON";
  }
  function markChooser() {
    document.querySelectorAll(".qitem").forEach((b) => b.classList.toggle("on", !!S.current && b.dataset.id === S.current.question_id));
    $("#askWho").textContent = S.current ? personLabel(S.current.history_id) : "THIS PERSON";
    document.querySelectorAll(".ch-rail img").forEach((im) => im.classList.toggle("on", !!S.current && im.dataset.k === S.current.route));
  }
  function renderRail() {
    $("#rail").innerHTML = KIND_ORDER.map((k) => `<img data-k="${k}" src="${PX.icon(k, 3)}" title="${KINDS[k].name}" alt="">`).join("");
  }

  // ---------- answer-key check (dev) ----------
  const NUMW = { zero: 0, one: 1, two: 2, three: 3, four: 4, five: 5, six: 6, seven: 7, eight: 8, nine: 9, ten: 10, eleven: 11, twelve: 12 };
  const STOP = new Set("i my me the a an of to and in on at for was is did do you your with by from that this it its i'm we our".split(" "));
  function norm(s) { return String(s || "").toLowerCase().replace(/[’']/g, "").replace(/\b(zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\b/g, (w) => NUMW[w]).replace(/[^a-z0-9.%\s]/g, " ").replace(/\s+/g, " ").trim(); }
  function judge(r) {
    const g = r.gold; if (!g) return null;
    if (g.abstain) return r.abstained ? "ok" : "bad";
    if (r.abstained) return "bad";
    const a = norm(r.answer), b = norm(g.answer);
    if (!a) return "bad";
    if (a === b || b.includes(a) || a.includes(b)) return "ok";
    const na = a.match(/\d+(\.\d+)?/g) || [], nb = b.match(/\d+(\.\d+)?/g) || [];
    if (na.length && nb.length) {
      if (na[0] === nb[nb.length - 1]) return "ok";
      return nb.includes(na[0]) ? "meh" : "bad";
    }
    const tb = b.split(" ").filter((w) => w.length > 2 && !STOP.has(w));
    const hit = tb.filter((w) => a.includes(w)).length;
    return tb.length && hit / tb.length >= 0.6 ? "ok" : "meh";
  }

  // ---------- shelves ----------
  function sessionsFor(rec) {
    const tl = S.timelines[rec.history_id];
    if (tl && tl.length) return tl;
    return (rec.passages || []).map((p) => ({ id: p.id, date: p.date, title: (p.text || "").slice(0, 90) }));
  }
  function parseDate(s) {
    const m = /^(\d{4})\/(\d{2})\/(\d{2})(?: \((\w+)\))?(?: (\d{2}:\d{2}))?/.exec(s || "");
    if (!m) return null;
    return { y: +m[1], mo: +m[2], d: +m[3], dow: m[4] || "", time: m[5] || "" };
  }
  function prettyDate(s, withTime) {
    const d = parseDate(s); if (!d) return s || "";
    return `${d.dow ? d.dow + " " : ""}${d.d} ${MONTHS[d.mo - 1]} ${d.y}${withTime && d.time ? " · " + d.time : ""}`;
  }
  function shortDate(s) { const d = parseDate(s); return d ? `${MONTHS[d.mo - 1]} ${d.d}` : ""; }

  function buildShelves(rec, animate) {
    const hid = rec.history_id;
    const shelves = $("#shelves");
    const sessions = sessionsFor(rec);
    if (S.shownHistory === hid && Object.keys(S.books).length) return false;
    S.shownHistory = hid; S.books = {};
    shelves.querySelectorAll(".srow, .empty-shelf").forEach((n) => n.remove());
    const n = sessions.length;
    const archiveChars = n * CHARS_PER_CONV;
    $("#libCount").innerHTML = `<b>${fmt(n)}</b> conversations · <b>≈${archiveChars >= 1e6 ? (archiveChars / 1e6).toFixed(1) + "M" : Math.round(archiveChars / 1000) + "K"}</b> characters · ${personLabel(hid)}`;
    const d0 = parseDate(sessions[0] && sessions[0].date), d1 = parseDate(sessions[n - 1] && sessions[n - 1].date);
    $("#libRange").textContent = d0 && d1 ? `${MONTHS[d0.mo - 1]} ${d0.y} → ${MONTHS[d1.mo - 1]} ${d1.y} · oldest to newest` : "";
    if (!n) { const e = document.createElement("div"); e.className = "empty-shelf"; e.textContent = "This archive is empty."; shelves.appendChild(e); return true; }
    const rows = n > 120 ? 4 : n > 60 ? 3 : 2;
    shelves.style.setProperty("--bmax", n <= 60 ? "46px" : n <= 120 ? "34px" : "26px");
    const per = Math.ceil(n / rows);
    let lastMonth = null, row = null;
    sessions.forEach((s, i) => {
      if (i % per === 0) { row = document.createElement("div"); row.className = "srow"; shelves.appendChild(row); }
      const d = parseDate(s.date);
      const mk = d ? d.y * 12 + d.mo : null;
      if (mk !== null && mk !== lastMonth) {
        const be = document.createElement("div"); be.className = "bookend";
        be.innerHTML = `<span class="plaque">${MONTHS[d.mo - 1].toUpperCase()}${lastMonth === null || d.mo === 1 ? " ’" + String(d.y).slice(2) : ""}</span>`;
        row.appendChild(be); lastMonth = mk;
      }
      const h = PX.hash(s.id);
      const c = BOOKC[(h >>> 3) % BOOKC.length];
      const b = document.createElement("div");
      b.className = "book" + (animate ? " drop" : "");
      b.style.cssText = `--c:${c[0]};--d:${c[1]};--l:${c[2]};--g:${c[3]};--h:${62 + (h % 30)}%;--i:${i}`;
      b.title = `${prettyDate(s.date, true)}\n${s.title || ""}`;
      b.dataset.id = s.id;
      row.appendChild(b);
      S.books[s.id] = b;
    });
    return true;
  }
  function bookFor(id) { return S.books[id] || null; }

  // ---------- wizard ----------
  let walkTimer = null;
  function wizardTo(x, y, ms) {
    const w = $("#wizard"), sh = $("#shelves");
    const ww = w.offsetWidth, wh = w.offsetHeight;
    const nx = Math.max(-4, Math.min(sh.clientWidth - ww + 4, x - ww / 2));
    const ny = Math.max(-wh * .35, Math.min(sh.clientHeight - wh, y - wh));
    const cur = parseFloat(w.style.left) || 0;
    if (Math.abs(nx - cur) > 2) w.classList.toggle("flip", nx < cur);
    w.style.transitionDuration = (ms || 700) + "ms";
    w.style.left = nx + "px"; w.style.top = ny + "px";
    clearInterval(walkTimer);
    let f = 0;
    walkTimer = setInterval(() => { f ^= 1; $("#wizImg").src = S.wizFrames[f]; }, 130);
    setTimeout(() => { clearInterval(walkTimer); $("#wizImg").src = S.wizFrames[0]; }, ms || 700);
  }
  function wizardToBook(el, ms) {
    const sh = $("#shelves").getBoundingClientRect(), r = el.getBoundingClientRect();
    wizardTo(r.left - sh.left + r.width / 2 + ($("#wizard").offsetWidth * 0.62), r.bottom - sh.top + 4, ms);
  }
  function wizardHome() {
    const sh = $("#shelves");
    wizardTo(30, sh.clientHeight * 0.55, 10);
  }
  let bubbleT = null;
  function say(text, ms) {
    const b = $("#bubble");
    clearTimeout(bubbleT);
    if (!text) { b.classList.remove("show"); return; }
    b.textContent = text; b.classList.remove("show"); void b.offsetWidth; b.classList.add("show");
    if (ms) bubbleT = setTimeout(() => b.classList.remove("show"), ms);
  }
  function cast() { $("#wizImg").src = S.wizFrames[2]; const [x, y] = center($("#wizImg")); fx.burst(x + 10, y - 20, 14, "cyan", 2.5); setTimeout(() => ($("#wizImg").src = S.wizFrames[0]), 500); }

  // ---------- banner ----------
  function setBannerMeta(rec) {
    const k = KINDS[rec.route] || { name: rec.route || "Question" };
    $("#qSigil").src = PX.icon(rec.route, 4);
    $("#qKind").textContent = k.name.toUpperCase();
    $("#qDate").textContent = rec.question_date ? "asked " + prettyDate(rec.question_date) : "";
    const qt = $("#qText"); qt.classList.toggle("long", (rec.question || "").length > 95);
    const cap = $("#tourCap");
    const t = S.tourIdx >= 0 && S.tour[S.tourIdx] && S.tour[S.tourIdx].id === rec.question_id ? S.tour[S.tourIdx] : null;
    if (t && t.cap) { cap.textContent = `TOUR ${S.tourIdx + 1}/${S.tour.length} · ${t.cap}`; cap.classList.add("show"); }
    else if (rec.live) { cap.textContent = rec.live === "ask" ? "LIVE · asked just now" : "LIVE · pages found just now"; cap.classList.add("show"); }
    else cap.classList.remove("show");
  }
  function idleBanner(rec) {
    setBannerMeta(rec);
    $("#qText").innerHTML = "Press <b>Space</b> to begin the tour, or pick a question.";
  }
  async function typeQuestion(rec, id) {
    const qt = $("#qText"), q = rec.question || "";
    const step = Math.max(1, Math.ceil(q.length / 45));
    for (let i = 0; i <= q.length; i += step) {
      qt.innerHTML = esc(q.slice(0, i)) + '<span class="caret">&nbsp;</span>';
      await sleep(22, id);
    }
    qt.textContent = q;
  }

  // ---------- desk ----------
  function quotesFrom(notes) {
    const out = []; const re = /"([^"]{10,})"/g; let m;
    while ((m = re.exec(notes || ""))) {
      let q = m[1].replace(/[’]/g, "'").replace(/\s*(…|\.\.\.)\s*$/, "").trim();
      const parts = q.split(/…|\.\.\./).map((x) => x.trim()).filter((x) => x.length >= 10);
      out.push(...(parts.length ? parts : [q]));
    }
    return out;
  }
  function answerNeedles(rec) {
    if (!rec || rec.abstained || !rec.answer) return [];
    const a = String(rec.answer).trim();
    if (/^INSUFFICIENT/i.test(a)) return [];
    if (/^[\d.,]+$/.test(a) && a.replace(/\D/g, "").length < 3) return [];
    const words = a.split(/\s+/);
    const out = [];
    for (let k = words.length; k >= 1; k--) {
      const s = words.slice(0, k).join(" ").replace(/[.,;:]+$/, "");
      if (s.length >= 3 && !(k === 1 && /^\d{1,2}$/.test(s))) out.push(s);
    }
    return out;
  }
  function markLine(text, quotes, needles) {
    const low = text.toLowerCase().replace(/[’]/g, "'");
    const lvl = new Uint8Array(text.length);
    for (const q of quotes) {
      const ql = q.toLowerCase(); let i = low.indexOf(ql);
      if (i < 0 && ql.length > 40) { i = low.indexOf(ql.slice(0, 40)); if (i >= 0) { lvl.fill(1, i, Math.min(text.length, i + ql.length)); continue; } }
      if (i >= 0) lvl.fill(1, i, i + ql.length);
    }
    for (const nd of needles) {
      const i = low.indexOf(nd.toLowerCase());
      if (i < 0) continue;
      let s = i, e = i + nd.length;
      while (s > 0 && !/[.!?]/.test(text[s - 1])) s--;
      while (e < text.length && !/[.!?]/.test(text[e])) e++;
      if (e < text.length) e++;
      for (let k = s; k < e; k++) lvl[k] = Math.max(lvl[k], 2);
      lvl.fill(3, i, i + nd.length);
      break;
    }
    let html = "", cur = -1, buf = "";
    const cls = ["", "hq", "ha", "ha hx"];
    const flush = () => { if (!buf) return; html += cur > 0 ? `<span class="${cls[cur]}">${esc(buf)}</span>` : esc(buf); buf = ""; };
    for (let k = 0; k < text.length; k++) { if (lvl[k] !== cur) { flush(); cur = lvl[k]; } buf += text[k]; }
    flush();
    return html;
  }
  function passageHTML(p, quotes, needles) {
    const lines = String(p.text || "").split("\n");
    return lines.map((ln) => {
      const t = ln.trim();
      if (!t) return "";
      if (/^\[(\.\.\.|…)\]$/.test(t)) return `<div class="gap">· · ·</div>`;
      const m = /^(user|assistant):\s?(.*)$/i.exec(t);
      if (m) {
        const u = m[1].toLowerCase() === "user";
        return `<p class="ln ${u ? "user" : "asst"}"><span class="who">${u ? "USER" : "AI"}</span>${markLine(m[2], quotes, needles)}</p>`;
      }
      return `<p class="ln">${markLine(t, quotes, needles)}</p>`;
    }).join("");
  }
  function reasonNeedles(rec) {
    const out = {};
    if (!rec || rec.abstained) return out;
    String(rec.reasoning || "").split("\n").forEach((l) => {
      const es = [...l.matchAll(/\[E(\d+)\]/g)].map((m) => +m[1]);
      if (es.length !== 1 || /exclud/i.test(l)) return;
      const nums = (l.replace(/\[E\d+\]/g, "").replace(/\d{4}-\d{2}-\d{2}/g, "").match(/\d[\d,]*(\.\d+)?/g) || []).filter((x) => x.replace(/\D/g, "").length >= 2);
      if (nums.length) (out[es[0]] = out[es[0]] || []).push(nums[nums.length - 1]);
    });
    return out;
  }
  function buildDesk(rec, closed) {
    const pages = $("#pages"); pages.innerHTML = ""; pages.scrollLeft = 0; pages.classList.toggle("fit", (rec.passages || []).length <= 3);
    const tabs = $("#tabs"); tabs.innerHTML = "";
    const ps = rec.passages || [];
    const quotes = quotesFrom(rec.notes);
    const cited = new Set(rec.cited || []);
    const needles = answerNeedles(rec);
    if (!ps.length) {
      pages.innerHTML = `<div class="no-pages"><img src="${PX.icon("book", 6)}" alt="">No page in the archive matched this question.<br>The Librarian brings nothing rather than something wrong.</div>`;
      return;
    }
    ps.forEach((p, i) => {
      const c = document.createElement("article");
      c.className = "card" + (closed ? " closed" : "");
      c.dataset.id = p.id;
      const rn = reasonNeedles(rec)[i + 1] || [];
      const useNeedles = (!cited.size || cited.has(p.id) ? needles : []).concat(cited.has(p.id) ? rn : []);
      c.innerHTML = `<div class="card-head"><span class="elabel">E${i + 1}</span><span class="cdate">${esc(prettyDate(p.date, true))}</span><span class="seal-slot"></span></div><div class="card-body">${passageHTML(p, quotes, useNeedles)}</div>`;
      pages.appendChild(c);
      const t = document.createElement("button"); t.className = "ptab"; t.textContent = `E${i + 1} ${shortDate(p.date)}`; t.dataset.id = p.id;
      t.onclick = () => c.scrollIntoView({ behavior: "smooth", inline: "nearest", block: "nearest" });
      tabs.appendChild(t);
    });
  }
  function notesHTML(rec) {
    const notes = String(rec.notes || "").trim();
    const k = KINDS[rec.route];
    let h = `<div class="m-head"><img src="${PX.icon("quill", 3)}" alt="">THE LIBRARIAN'S MARGIN NOTES</div>`;
    if (k) h += `<div class="m-trick">${esc(k.trick)}</div>`;
    let body = "";
    if (rec.computed !== null && rec.computed !== undefined && rec.computed !== "") {
      const isNum = /^-?\d+(\.\d+)?$/.test(String(rec.computed));
      body += `<div class="stamp" id="stamp">${rec.route === "temporal" ? "computed by code" : "code's best guess"}<b>${esc(rec.computed)}${isNum && rec.route === "temporal" && !/year|month|week/i.test(rec.question) ? " days" : ""}</b></div>`;
    }
    if (!notes) return h + `<div class="m-body">${body}</div><div class="m-empty">No margin notes this time: the pages speak for themselves.</div>`;
    const lines = notes.split("\n").map((l) => l.trim()).filter(Boolean);
    body += lines.map((l) => {
      let cls = "meta";
      let t = l;
      if (/^- /.test(l)) { cls = "fact"; t = l.slice(2); }
      else if (/^(Difference between|Likely the line|Note:|If the value changed|Cite both)/i.test(l)) cls = "fact";
      if (/Difference between the two dates|MOST RECENT/i.test(l)) cls += " key";
      let x = esc(t).replace(/&quot;([^&]{3,}?)&quot;/g, '<span class="nq">“$1”</span>');
      x = x.replace(/(MOST RECENT value|\bdecoys?\b|not the answer|someone else|not the user's own|about the user's friend|Difference between the two dates: [^.<]+)/g, "<mark>$1</mark>");
      return `<p class="${cls}">${x}</p>`;
    }).join("");
    return h + `<div class="m-body">${body}</div>`;
  }

  // ---------- oracle + answer ----------
  function oracleMsg(html) { $("#oracleMsg").innerHTML = html || ""; }
  function idleAnswer() {
    $("#answer").innerHTML = `<div class="a-idle">The Oracle waits for a dossier.</div>`;
    $("#ribbon").innerHTML = ribbonHTML(null);
  }
  function answerHTML(rec) {
    if (rec.busyState) {
      return `<div class="a-busy"><b>THE ORACLE IS BUSY</b>Reactor is running the benchmark right now, so this live question gets pages and notes but no answer. Nothing is invented: pick a recorded question to see the Oracle's real replies.</div>`;
    }
    if (rec.errorState) return `<div class="a-busy"><b>THE ORACLE DID NOT ANSWER</b>${esc(rec.errorState)}</div>`;
    if (rec.answer === null || rec.answer === undefined) {
      return `<div class="a-busy"><b>PAGES READY</b>The Librarian found the pages and wrote the notes. Ask the Oracle when it is free; we never fake an answer.</div>`;
    }
    const ps = rec.passages || [];
    const idx = (id) => ps.findIndex((p) => p.id === id) + 1;
    let h = "";
    if (rec.abstained) {
      h += `<div class="a-none"><div class="a-label">THE ORACLE SPEAKS</div><div class="a-text mid reveal">Not written in the archive.</div>
        <p>It read ${ps.length} page${ps.length === 1 ? "" : "s"} and found no line that says this, so it says so instead of guessing.</p></div>`;
    } else {
      const a = String(rec.answer);
      const size = a.length > 38 ? "small" : a.length > 18 ? "mid" : a.length <= 6 ? "huge" : "";
      h += `<div class="a-label">THE ORACLE SPEAKS</div><div class="a-text ${size} reveal">${esc(a)}</div>`;
      const cites = (rec.cited || []).map(idx).filter((i) => i > 0);
      if (cites.length) h += `<div class="a-cites"><img src="${SEAL_URL}" alt="">sealed &amp; cited: ${cites.map((i) => "E" + i).join(", ")}</div>`;
      if (rec.route === "temporal" && rec.computed != null && rec.computed !== "") {
        const same = String(a).replace(/[^0-9.]/g, "") === String(rec.computed).replace(/[^0-9.]/g, "");
        h += `<div class="a-agree${same ? "" : " no"}">${same ? "✓ agrees with the code's date arithmetic" : "≠ differs from the code's date arithmetic (" + esc(rec.computed) + ")"}</div>`;
      }
    }
    if (rec.gold) {
      const v = judge(rec);
      const key = rec.gold.abstain ? "not in the archive" : rec.gold.answer;
      const lab = v === "ok" ? "✓ MATCHES THE ANSWER KEY" : v === "bad" ? "✗ THE ANSWER KEY DISAGREES" : "≈ COMPARE WITH THE ANSWER KEY";
      h += `<div class="gold-check ${v}"><b>${lab}</b>${esc(String(key).slice(0, 220))}</div>`;
    }
    const reason = String(rec.reasoning || "").split("\n").filter((l) => l.trim() && !/^#\s*FINAL ANSWER/i.test(l.trim())).join("\n").trim();
    if (reason.length > 20) h += `<details class="reckon"${rec.route === "multi" ? " open" : ""}><summary>THE ORACLE'S RECKONING</summary><pre>${esc(reason.slice(0, 1600))}</pre></details>`;
    h += questLog(rec);
    return h;
  }
  function questLog(rec) {
    const ps = rec.passages || [];
    const n = sessionsFor(rec).length;
    const nNotes = String(rec.notes || "").split("\n").filter((l) => l.trim()).length;
    const cited = (rec.cited || []).length;
    const rows = [
      ["book", `searched <b>${fmt(n)}</b> conversations`],
      ["wizard", `picked <b>${ps.length}</b> page${ps.length === 1 ? "" : "s"}${rec.build_ms ? ` in ${(rec.build_ms / 1000).toFixed(1)} s` : ""}`],
      ["quill", nNotes ? `wrote <b>${nNotes}</b> margin note${nNotes === 1 ? "" : "s"}${rec.computed != null && rec.computed !== "" ? ` · computed <b>${esc(rec.computed)}</b>` : ""}` : "no margin notes needed"],
      ["eye", rec.answer == null ? "Oracle not asked" : rec.abstained ? "Oracle: <b>not in the archive</b>" : `Oracle answered, cited <b>${cited}</b>`],
    ];
    return `<div class="quest"><div class="q-title">QUEST LOG</div>${rows.map(([ic, t]) => `<div class="q-row"><img src="${ic === "wizard" ? S.wizFrames[0] : PX.icon(ic, 3)}" alt=""><span>${t}</span></div>`).join("")}</div>`;
  }
  function ribbonHTML(rec, archiveN) {
    if (!rec) return `<div class="rb-top">HOW MUCH WE READ</div><div class="rb-big">—</div><div class="rb-bar"><div class="rb-fill" style="width:0"></div></div><div class="rb-small">The Oracle only ever sees a few pages.</div>`;
    const ps = rec.passages || [];
    const chars = ps.reduce((s, p) => s + String(p.text || "").length, 0);
    const n = archiveN || sessionsFor(rec).length;
    const archiveChars = n * CHARS_PER_CONV;
    const pct = archiveChars ? (chars / archiveChars) * 100 : 0;
    const lat = rec.latency_s ? `Oracle took ${Number(rec.latency_s).toFixed(1)} s` : rec.build_ms ? `pages found in ${(rec.build_ms / 1000).toFixed(1)} s` : "";
    const big = archiveChars >= 1e6 ? (archiveChars / 1e6).toFixed(1) + "M" : Math.round(archiveChars / 1000) + "K";
    return `<div class="rb-top">HOW MUCH WE READ</div>
      <div class="rb-big"><b>${ps.length}</b> page${ps.length === 1 ? "" : "s"} from <b>${fmt(n)}</b> conversations</div>
      <div class="rb-bar"><div class="rb-fill" data-w="${Math.max(0.4, pct * 8).toFixed(2)}"></div></div>
      <div class="rb-small"><b>${fmt(chars)}</b> of ≈${big} characters (${pct < 0.01 ? "<0.01" : pct.toFixed(2)}%)${lat ? " · " + lat : ""}</div>`;
  }
  function fillRibbon() { const f = document.querySelector(".rb-fill[data-w]"); if (f) requestAnimationFrame(() => (f.style.width = Math.min(100, parseFloat(f.dataset.w)) + "%")); }

  // ---------- run a question ----------
  function prepare(rec) {
    document.querySelectorAll(".fly-book").forEach((n) => n.remove());
    const fresh = buildShelves(rec, true);
    Object.values(S.books).forEach((b) => { b.classList.remove("chosen", "sealed", "cand", "scan", "dim"); });
    if (fresh) wizardHome();
    $("#desk").classList.remove("show-quotes", "show-answer");
    $("#pages").innerHTML = ""; $("#tabs").innerHTML = "";
    $("#margin").innerHTML = `<div class="m-head"><img src="${PX.icon("quill", 3)}" alt="">THE LIBRARIAN'S MARGIN NOTES</div><div class="m-empty">…</div>`;
    oracle.set("idle"); oracleMsg("");
    idleAnswer();
    say("");
    markChooser();
  }
  function finalize(rec) {
    // render the finished state instantly
    S.current = rec;
    prepare(rec);
    setBannerMeta(rec);
    $("#qText").textContent = rec.question || "";
    const ps = rec.passages || [];
    ps.forEach((p) => { const b = bookFor(p.id); if (b) b.classList.add("chosen"); });
    buildDesk(rec, false);
    $("#margin").innerHTML = notesHTML(rec);
    $("#desk").classList.add("show-quotes");
    reveal(rec, false);
    const last = ps.length ? bookFor(ps[ps.length - 1].id) : null;
    if (last) wizardToBook(last, 300);
  }
  function reveal(rec, animate) {
    const st = rec.busyState ? "resting" : rec.errorState ? "resting" : rec.answer == null ? "resting" : rec.abstained ? "abstain" : "answered";
    oracle.set(st);
    oracleMsg(st === "answered" ? "<b>answered</b> from the dossier" : st === "abstain" ? "<b>declined</b>: nothing in the dossier says this" : rec.busyState ? "resting: busy with the benchmark" : "resting");
    $("#answer").innerHTML = answerHTML(rec);
    $("#ribbon").innerHTML = ribbonHTML(rec); fillRibbon();
    if (rec.answer != null && !rec.abstained) $("#desk").classList.add("show-answer");
    const cited = rec.cited || [];
    let firstCited = null;
    cited.forEach((id, i) => {
      const card = document.querySelector(`.card[data-id="${CSS.escape(id)}"]`);
      if (card) {
        card.classList.add("cited");
        const slot = card.querySelector(".seal-slot");
        if (slot && !slot.firstChild) {
          const im = new Image(); im.src = SEAL_URL; im.alt = "wax seal"; if (animate) { im.className = "stamp-in"; im.style.animationDelay = i * 180 + "ms"; }
          slot.appendChild(im);
        }
        if (!firstCited) firstCited = card;
      }
      const tab = document.querySelector(`.ptab[data-id="${CSS.escape(id)}"]`); if (tab) tab.classList.add("cited");
      const b = bookFor(id); if (b) b.classList.add("sealed");
    });
    // bring the page that holds the answer into view (else the first cited page)
    const ansCard = (document.querySelector("#pages .hx") || document.querySelector("#pages .ha") || { closest: () => null }).closest(".card");
    const focus = ansCard || firstCited;
    if (focus) {
      const pages = $("#pages");
      const left = focus.offsetLeft - pages.offsetLeft - 8;
      if (left + focus.offsetWidth > pages.scrollLeft + pages.clientWidth || left < pages.scrollLeft) pages.scrollLeft = left;
    }
    document.querySelectorAll("#pages .card").forEach((c) => {
      const hit = c.querySelector(".hx") || c.querySelector(".ha") || c.querySelector(".hq");
      if (hit) { const body = c.querySelector(".card-body"); body.scrollTop = Math.max(0, hit.offsetTop - body.offsetTop - 50); }
    });
    if (animate) {
      const [ox, oy] = center($("#oracle"));
      fx.burst(ox, oy - 20, st === "answered" ? 60 : 30, st === "answered" ? "gold" : "grey", st === "answered" ? 4.5 : 2.5);
      if (firstCited) { const [cx, cy] = center(firstCited.querySelector(".seal-slot")); fx.burst(cx, cy, 24, "red", 3); }
      cited.forEach((id) => { const b = bookFor(id); if (b) { const [bx, by] = center(b); fx.burst(bx, by - 10, 10, "red", 2); } });
      if (rec.gold && judge(rec) === "ok") { const g = document.querySelector(".gold-check"); if (g) { const [gx, gy] = center(g); fx.burst(gx, gy, 30, "moss", 3.5); } }
    }
  }

  function keywords(q) {
    const stop = new Set("what when where which who whom whose how many much did does do was were is are the a an of to and in on at for my me i you your that this with from about have has had name now currently current day days apart between were time times".split(" "));
    return [...new Set(String(q || "").toLowerCase().replace(/[^a-z\s']/g, " ").split(/\s+/).map((w) => w.replace(/'s$/, "")).filter((w) => w.length > 3 && !stop.has(w)))];
  }

  async function runAnimated(rec, id) {
    S.running = true;
    S.current = rec;
    prepare(rec);
    setBannerMeta(rec);
    renderTourbar();
    await sleep(350, id);
    await typeQuestion(rec, id);
    // 1. scan the shelves
    say("Let me look…", 1500);
    const books = Object.values(S.books);
    books.forEach((b) => { b.classList.remove("drop"); b.classList.remove("scan"); void b.offsetWidth; b.classList.add("scan"); });
    const kw = keywords(rec.question);
    const sessions = sessionsFor(rec);
    const cands = kw.length ? sessions.filter((s) => kw.some((w) => String(s.title || "").toLowerCase().includes(w))).slice(0, 24) : [];
    const sh = $("#shelves");
    wizardTo(sh.clientWidth * 0.5, sh.clientHeight * 0.5, 650);
    await sleep(500, id);
    cands.forEach((s) => { const b = bookFor(s.id); if (b) b.classList.add("cand"); });
    wizardTo(sh.clientWidth * 0.88, sh.clientHeight * 0.75, 650);
    await sleep(700, id);
    books.forEach((b) => b.classList.remove("scan"));
    // 2. fetch the pages
    const ps = rec.passages || [];
    buildDesk(rec, true);
    $("#margin").innerHTML = notesHTML(rec);
    $("#margin").querySelectorAll(".m-body > *, .m-empty, .m-trick").forEach((n) => (n.style.visibility = "hidden"));
    if (!ps.length) { say("Nothing here…", 1800); cands.forEach((s) => { const b = bookFor(s.id); if (b) b.classList.remove("cand"); }); await sleep(900, id); }
    const order = ps.map((p, i) => ({ p, i })).sort((a, b) => String(a.p.date).localeCompare(String(b.p.date)));
    const solo = order.length <= 6 ? order : order.slice(0, 4);
    const rest = order.length <= 6 ? [] : order.slice(4);
    for (const { p, i } of solo) {
      const b = bookFor(p.id);
      if (b) { wizardToBook(b, 520); await sleep(540, id); }
      say(shortDate(p.date) + "!", 700);
      await flyToCard(b, i, id, 560);
    }
    if (rest.length) {
      say(`+${rest.length} more`, 900); cast();
      await Promise.all(rest.map(({ p, i }, k) => sleep(k * 70, id).then(() => flyToCard(bookFor(p.id), i, id, 520))));
    }
    cands.forEach((s) => { const b = bookFor(s.id); if (b && !ps.some((p) => p.id === s.id)) b.classList.remove("cand"); });
    books.forEach((b) => { b.classList.remove("cand"); if (!b.classList.contains("chosen")) b.classList.add("dim"); });
    alive(id);
    // 3. margin notes
    say("Notes…", 1200);
    $("#pages").scrollLeft = 0;
    const parts = [...$("#margin").querySelectorAll(".m-trick, .m-body > p, .m-empty")];
    const stamp = $("#stamp");
    for (const n of parts) {
      n.style.visibility = ""; const len = n.textContent.length;
      const d = Math.min(650, Math.max(160, len * 3.2));
      n.style.setProperty("--d", d + "ms"); n.classList.add("ink-in");
      const m = $("#margin"); if (n.offsetTop + n.offsetHeight > m.scrollTop + m.clientHeight) m.scrollTop = n.offsetTop - 30;
      await sleep(d * 0.8, id);
    }
    $("#margin").scrollTop = 0;
    $("#desk").classList.add("show-quotes");
    if (stamp) { stamp.style.visibility = ""; stamp.classList.add("thud"); const [sx, sy] = center(stamp); fx.burst(sx, sy, 16, "red", 2.4); await sleep(500, id); }
    // 4. the Oracle
    oracle.set("thinking");
    say("To the Oracle!", 1200); cast();
    const [ox, oy] = center($("#oracle"));
    const pagesEl = $("#pages");
    let streaming = true;
    (function stream() {
      if (!streaming || id !== S.runId) return;
      const [px, py] = center(pagesEl); for (let k = 0; k < 3; k++) fx.stream(px + (Math.random() - .5) * pagesEl.clientWidth * .8, py, ox, oy - 10, "cyan");
      setTimeout(stream, 60);
    })();
    try {
      if (rec.askPromise) {
        const t0 = Date.now();
        let done = false, res = null;
        rec.askPromise.then((r) => { done = true; res = r; });
        while (!done) {
          alive(id);
          oracleMsg(`the Oracle reads ${ps.length} page${ps.length === 1 ? "" : "s"}… <b>${Math.round((Date.now() - t0) / 1000)} s</b>`);
          await sleep(250, id);
        }
        Object.assign(rec, res);
      } else if (rec.answer != null || rec.busyState) {
        const lat = Number(rec.latency_s) || 0;
        const steps = 22;
        for (let k = 1; k <= steps; k++) {
          oracleMsg(`the Oracle reads ${ps.length} page${ps.length === 1 ? "" : "s"}…${lat ? ` <b>${(lat * k / steps).toFixed(1)} s</b>` : ""}`);
          await sleep(rec.busyState ? 40 : 95, id);
        }
        if (lat) oracleMsg(`took <b>${lat.toFixed(1)} s</b> live (replayed fast)`);
        await sleep(250, id);
      } else await sleep(600, id);
    } finally { streaming = false; }
    alive(id);
    // 5. reveal
    reveal(rec, true);
    if (rec.abstained) say("Not written here.", 2400); else if (rec.answer != null) say("Sealed!", 1600);
    S.running = false;
    renderTourbar();
    scheduleNext();
  }

  async function flyToCard(book, i, id, ms) {
    alive(id);
    const card = $("#pages").children[i];
    if (!card) return;
    // keep the target card in view while cards arrive
    const pages = $("#pages");
    if (card.offsetLeft + card.offsetWidth > pages.scrollLeft + pages.clientWidth) pages.scrollLeft = card.offsetLeft - pages.offsetLeft - 10;
    let from;
    if (book) { book.classList.add("chosen"); from = book.getBoundingClientRect(); const [bx, by] = center(book); fx.burst(bx, by, 12, "gold", 2.2); }
    else { const r = $("#wizImg").getBoundingClientRect(); from = { left: r.left, top: r.top, width: 14, height: 40 }; }
    const to = card.getBoundingClientRect();
    const fb = document.createElement("div"); fb.className = "fly-book";
    if (book) fb.style.cssText = book.style.cssText;
    fb.style.left = from.left + "px"; fb.style.top = from.top + "px"; fb.style.width = Math.max(8, from.width) + "px"; fb.style.height = from.height + "px";
    document.body.appendChild(fb);
    const dx = to.left + to.width / 2 - (from.left + from.width / 2), dy = to.top + Math.min(to.height, 220) / 2 - (from.top + from.height / 2);
    const anim = fb.animate([
      { transform: "translate(0,0) rotate(0deg) scale(1)" },
      { transform: `translate(${dx * .45}px, ${dy * .45 - 90}px) rotate(200deg) scale(2.2)`, offset: .5 },
      { transform: `translate(${dx}px, ${dy}px) rotate(360deg) scale(3)`, opacity: .2 },
    ], { duration: ms, easing: "cubic-bezier(.4,.1,.3,1)" });
    let flying = true;
    (function trail() { if (!flying) return; const [x, y] = center(fb); fx.sparkle(x, y, "gold", 14); requestAnimationFrame(trail); })();
    try { await anim.finished; } catch (e) { /* cancelled */ }
    flying = false; fb.remove();
    if (id !== S.runId) throw new Cancel();
    card.classList.remove("closed"); card.classList.add("opening");
    const [cx, cy] = center(card); fx.burst(cx, cy - to.height * 0.3, 14, "gold", 2.5);
  }

  function playRec(rec, opts) {
    opts = opts || {};
    clearTimeout(S.holdTimer);
    S.runId++;
    const id = S.runId;
    if (rec.split === "test" && S.persons.includes(rec.history_id) && S.person !== rec.history_id) { S.person = rec.history_id; S.split = "test"; renderChooser(); }
    else if (rec.split === "dev" && S.split !== "dev" && !rec.live) { S.split = "dev"; renderChooser(); }
    if (opts.instant) { S.running = false; finalize(rec); renderTourbar(); scheduleNext(); return; }
    runAnimated(rec, id).catch((e) => { if (!(e instanceof Cancel)) { console.warn(e); S.running = false; } });
  }

  // ---------- tour ----------
  function goTour(i, instant) {
    if (!S.tour.length) return;
    S.tourIdx = (i + S.tour.length) % S.tour.length;
    if (!$("#main").classList.contains("collapsed")) setCollapsed(true);
    renderTourbar();
    const rec = S.recs[S.tour[S.tourIdx].id];
    playRec(rec, { instant });
  }
  function scheduleNext() {
    clearTimeout(S.holdTimer);
    if (!S.autoplay || S.tourIdx < 0) return;
    S.holdTimer = setTimeout(() => { if (S.autoplay && !S.running) goTour(S.tourIdx + 1); }, 9000);
  }
  function stopTour() { S.autoplay = false; S.tourIdx = -1; clearTimeout(S.holdTimer); renderTourbar(); $("#tourCap").classList.remove("show"); }
  function togglePlay() {
    if (S.autoplay) { S.autoplay = false; clearTimeout(S.holdTimer); renderTourbar(); return; }
    S.autoplay = true;
    setCollapsed(true);
    if (S.tourIdx < 0 || !S.running) goTour(S.tourIdx < 0 ? 0 : (S.current && S.tour[S.tourIdx] && S.current.question_id === S.tour[S.tourIdx].id ? S.tourIdx + 1 : S.tourIdx));
    renderTourbar();
  }
  function next() {
    if (S.running && S.current) { S.runId++; S.running = false; finalize(S.current); renderTourbar(); scheduleNext(); return; }
    goTour(S.tourIdx < 0 ? 0 : S.tourIdx + 1);
  }
  function prev() { goTour(S.tourIdx <= 0 ? S.tour.length - 1 : S.tourIdx - 1); }
  function setCollapsed(v) { $("#main").classList.toggle("collapsed", v); setTimeout(() => { if (S.current && !S.running) { const ps = S.current.passages || []; const last = ps.length ? bookFor(ps[ps.length - 1].id) : null; if (last) wizardToBook(last, 200); } }, 450); }

  // ---------- how-it-works overlay ----------
  function showHow(v) { $("#how").hidden = !v; fx.setAmbient(true); }

  // ---------- live mode ----------
  async function postJSON(url, body) {
    const r = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    let j = null; try { j = await r.json(); } catch (e) { j = null; }
    return { status: r.status, ok: r.ok, body: j };
  }
  function askMsg(t, err) { const m = $("#askMsg"); m.textContent = t || ""; m.classList.toggle("err", !!err); }
  async function live(withOracle) {
    const q = $("#askInput").value.trim();
    const base = S.current || (S.tour[0] && S.recs[S.tour[0].id]);
    if (!q) { askMsg("Write a question first."); $("#askInput").focus(); return; }
    if (!base) { askMsg("Pick a recorded question first (it picks the person).", true); return; }
    stopTour();
    $("#bPack").disabled = $("#bAsk").disabled = true;
    askMsg("The Librarian is searching the shelves…");
    try {
      const pk = await postJSON("/api/pack", { question_id: base.question_id, question: q });
      if (!pk.ok || !pk.body || pk.body.error) throw new Error((pk.body && pk.body.error) || "HTTP " + pk.status);
      const rec = Object.assign({}, pk.body, { split: base.split, answer: null, abstained: false, cited: [], latency_s: null, reasoning: "", live: withOracle ? "ask" : "pack" });
      rec.history_id = rec.history_id || base.history_id;
      if (withOracle) {
        await pollStatus();
        if (S.busy) { rec.busyState = true; askMsg("The Oracle is busy with the benchmark: replaying recorded answers. Showing pages and notes only."); }
        else {
          askMsg("Asking the Oracle: this takes 1-2 minutes…");
          rec.askPromise = postJSON("/api/ask", { question_id: base.question_id, question: q }).then((r) => {
            if (r.status === 409) return { busyState: true, answer: null };
            if (!r.ok || !r.body || r.body.error) return { errorState: (r.body && r.body.error) || "HTTP " + r.status, answer: null };
            return { answer: r.body.answer, abstained: !!r.body.abstained, cited: r.body.cited || [], latency_s: r.body.latency_s, reasoning: r.body.reasoning || "", passages: r.body.passages || rec.passages };
          }).catch((e) => ({ errorState: String(e.message || e), answer: null })).finally(() => { askMsg(""); });
        }
      } else askMsg(`Found ${rec.passages.length} page${rec.passages.length === 1 ? "" : "s"}${rec.build_ms ? ` in ${(rec.build_ms / 1000).toFixed(1)} s` : ""}.`);
      playRec(rec);
    } catch (e) {
      askMsg("The Librarian could not open the archive: " + (e.message || e), true);
    } finally {
      $("#bPack").disabled = $("#bAsk").disabled = false;
    }
  }

  // ---------- wiring ----------
  $("#bPlay").onclick = () => { showHow(false); togglePlay(); };
  $("#bNext").onclick = () => { showHow(false); next(); };
  $("#bPrev").onclick = () => { showHow(false); prev(); };
  $("#bHow").onclick = () => showHow($("#how").hidden);
  $("#bFull").onclick = toggleFull;
  $("#bCollapse").onclick = () => setCollapsed(!$("#main").classList.contains("collapsed"));
  $("#howGo").onclick = () => { showHow(false); if (!S.autoplay) togglePlay(); };
  $("#how").addEventListener("click", (e) => { if (e.target.id === "how") showHow(false); });
  $("#askForm").addEventListener("submit", (e) => { e.preventDefault(); live(true); });
  $("#bPack").onclick = () => live(false);
  $("#askInput").addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); live(true); } });
  function toggleFull() {
    try {
      if (document.fullscreenElement) document.exitFullscreen();
      else document.documentElement.requestFullscreen().catch(() => {});
    } catch (e) { /* not allowed */ }
  }
  document.addEventListener("keydown", (e) => {
    const tag = (e.target && e.target.tagName) || "";
    if (tag === "TEXTAREA" || tag === "INPUT") { if (e.key === "Escape") e.target.blur(); return; }
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    const howOpen = !$("#how").hidden;
    if (e.key === " " || e.code === "Space") { e.preventDefault(); if (howOpen) { showHow(false); if (!S.autoplay) togglePlay(); } else togglePlay(); }
    else if (e.key === "ArrowRight") { e.preventDefault(); showHow(false); next(); }
    else if (e.key === "ArrowLeft") { e.preventDefault(); showHow(false); prev(); }
    else if (e.key === "f" || e.key === "F") toggleFull();
    else if (e.key === "q" || e.key === "Q") setCollapsed(!$("#main").classList.contains("collapsed"));
    else if (e.key === "h" || e.key === "H" || e.key === "?") showHow(howOpen ? false : true);
    else if (e.key === "Escape") showHow(false);
    else if ((e.key === "r" || e.key === "R") && S.current) playRec(S.current);
  });
  let rz = null;
  window.addEventListener("resize", () => { clearTimeout(rz); rz = setTimeout(() => { if (S.current && !S.running) { const ps = S.current.passages || []; const last = ps.length ? bookFor(ps[ps.length - 1].id) : null; if (last) wizardToBook(last, 10); } }, 200); });

  boot().catch((e) => {
    console.warn(e);
    const d = document.createElement("div"); d.className = "fatal";
    d.textContent = "The Librarian tripped over a book: " + (e && e.message ? e.message : e) + ". Reload the page.";
    document.body.appendChild(d);
  });
})();
