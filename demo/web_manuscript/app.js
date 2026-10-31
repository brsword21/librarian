/* The Librarian · illuminated-manuscript demo frontend (vanilla JS, Web Animations API, no build step). */
(() => {
  'use strict';

  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));

  const ROUTES = {
    ssu: { name: 'Personal facts', sub: 'what I told the assistant about myself' },
    ssa: { name: 'Advice I was given', sub: 'what the assistant itself recommended' },
    multi: { name: 'Counting across time', sub: 'facts scattered over many chats' },
    ku: { name: 'Things that changed', sub: 'the most recent value wins' },
    temporal: { name: 'Dates & durations', sub: 'day gaps reckoned by code' },
  };
  const ORDER = ['ssu', 'ssa', 'multi', 'ku', 'temporal'];
  const TOUR = [
    { id: 'q_62e927862f62', cap: 'The instructor changed in August. The Librarian lists every mention, oldest first; the latest value wins.' },
    { id: 'q_06ae4afa8961', cap: 'Code finds both dates and reckons the gap itself; other people’s events are decoys.' },
    { id: 'q_392fdc44c911', cap: 'Only what the assistant itself recommended counts, not tools merely listed or mentioned.' },
    { id: 'q_068d0a4b3f7b', cap: 'Facts scattered over months: three mugs in August plus two vases in September.' },
    { id: 'q_aa27ddd3b7c5', cap: 'A hospital therapy dog and a friend’s puppy are not “my dog”, so the Oracle says it is not written.' },
  ];
  const NAMES = { h_d99a2da8f8ee: 'Carla' };
  const HOLD_MS = 9000;
  const EST_CHARS = 8200; // per conversation, when a history's sizes are unknown
  const REDUCED = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const STOP = new Set('a an the of to in on at for and or is am are was were be been did do does i me my mine you your that this what which who whom whose how many much name names when where why with from about it its have has had there their they them we our us than then so as by any each every since now these those after before apart days day weeks months years ever told mentioned recommended recommend get got go use used using current currently still end ended up'.split(' '));
  const NUMW = { zero: 0, one: 1, two: 2, three: 3, four: 4, five: 5, six: 6, seven: 7, eight: 8, nine: 9, ten: 10, eleven: 11, twelve: 12, thirteen: 13, fourteen: 14, fifteen: 15, twenty: 20 };

  const S = {
    data: null, sizes: {}, split: 'test', persons: {}, rec: null, hid: null,
    runId: 0, tourTok: 0, tourIdx: -1, playing: false, touring: false, busy: null, owl: { x: 0, y: 0 }, holdTimer: null,
  };

  /* ---------------- utilities ---------------- */
  const esc = (s) => String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  const sleep = (ms) => new Promise((r) => setTimeout(r, REDUCED ? Math.min(ms, 120) : ms));
  const fmt = (n) => Number(n).toLocaleString('en-US');
  function roman(n) {
    const t = [[1000, 'M'], [900, 'CM'], [500, 'D'], [400, 'CD'], [100, 'C'], [90, 'XC'], [50, 'L'], [40, 'XL'], [10, 'X'], [9, 'IX'], [5, 'V'], [4, 'IV'], [1, 'I']];
    let s = ''; for (const [v, r] of t) while (n >= v) { s += r; n -= v; } return s;
  }
  function parseDate(s) {
    const m = /^(\d{4})\/(\d{2})\/(\d{2})\s*(?:\((\w+)\))?\s*(\d{2}:\d{2})?/.exec(s || '');
    if (!m) return null;
    return { y: +m[1], mo: +m[2] - 1, d: +m[3], dow: m[4] || '', time: m[5] || '' };
  }
  function prettyDate(s, withTime = true) {
    const p = parseDate(s); if (!p) return esc(s || '');
    return `${p.dow ? p.dow + ' ' : ''}${p.d} ${MONTHS[p.mo]} ${p.y}${withTime && p.time ? ' · ' + p.time : ''}`;
  }
  function shortDate(s) { const p = parseDate(s); return p ? `${p.d} ${MONTHS[p.mo]} ${p.y}` : esc(s || ''); }
  function hash(str) { let h = 2166136261; for (let i = 0; i < str.length; i++) { h ^= str.charCodeAt(i); h = Math.imul(h, 16777619); } return (h >>> 0) / 4294967295; }
  function norm(s) {
    return String(s || '').toLowerCase().replace(/[‘’`']/g, '').replace(/[“”"]/g, '')
      .replace(/\b(zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|twenty)\b/g, (w) => String(NUMW[w]))
      .replace(/[^a-z0-9µ.%]+/g, ' ').replace(/\s+/g, ' ').trim();
  }
  const nums = (s) => (norm(s).match(/\d+(?:\.\d+)?/g) || []).map(Number);
  function animate(el, frames, opts) {
    if (!el || !el.animate) return Promise.resolve();
    const a = el.animate(frames, { fill: 'forwards', ...opts, duration: REDUCED ? 1 : opts.duration });
    return a.finished.then(() => { try { a.commitStyles(); } catch (e) { /* detached */ } a.cancel(); }).catch(() => {});
  }
  function toast(msg, ms = 4200) {
    const t = $('#toast'); t.textContent = msg; t.hidden = false;
    clearTimeout(toast._t); toast._t = setTimeout(() => { t.hidden = true; }, ms);
  }
  async function postJSON(url, body) {
    const r = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    let j = null; try { j = await r.json(); } catch (e) { /* not json */ }
    if (!r.ok) { const err = new Error((j && j.error) || `HTTP ${r.status}`); err.status = r.status; throw err; }
    return j;
  }
  const isAbstain = (rec) => !!rec.abstained || /^INSUFFICIENT_EVIDENCE$/i.test((rec.answer || '').trim());

  /* ---------------- boot ---------------- */
  async function boot() {
    initMotes();
    bindUI();
    try {
      const [data, sizes] = await Promise.all([
        fetch('/replay.json').then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); }),
        fetch('sizes.json').then((r) => (r.ok ? r.json() : {})).catch(() => ({})),
      ]);
      S.data = { test: data.test || [], dev: data.dev || [], timelines: data.timelines || {} };
      S.sizes = sizes || {};
    } catch (e) {
      $('#qtext').textContent = 'The archive could not be opened (replay.json did not load).';
      toast('Could not load /replay.json; is demo.server running?', 8000);
      return;
    }
    let i = 0;
    for (const r of [...S.data.test, ...S.data.dev]) if (!(r.history_id in S.persons)) S.persons[r.history_id] = ++i;
    renderChooser();
    renderDots();
    const first = findRec(TOUR[0].id) || S.data.test[0] || S.data.dev[0];
    if (first) { renderArchive(first.history_id); setLivePerson(first.history_id); S.base = first; }
    setPhase('archive');
    pollStatus();
    setInterval(pollStatus, 20000);
    window.addEventListener('resize', () => { if (!S.moving) parkOwl(true); });
    requestAnimationFrame(() => parkOwl(true));
  }

  function findRec(id) { return [...S.data.test, ...S.data.dev].find((r) => r.question_id === id); }
  function personLabel(hid) { const n = S.persons[hid]; return n ? `Person ${roman(n)}` : 'This person'; }
  function archiveName(hid) { return NAMES[hid] ? `${NAMES[hid]}’s Archive` : `The Archive of ${personLabel(hid)}`; }
  function setLivePerson(hid) { $('#livePerson').textContent = NAMES[hid] ? `${NAMES[hid]} (${personLabel(hid)})` : personLabel(hid); }

  /* ---------------- status ---------------- */
  async function pollStatus() {
    const el = $('#status');
    try {
      const r = await fetch('/api/status', { cache: 'no-store' });
      const j = await r.json();
      S.busy = !!j.reactor_busy;
      el.className = 'status ' + (S.busy ? 'busy' : 'idle');
      el.querySelector('span').textContent = S.busy ? 'Oracle busy with the benchmark · replaying recorded answers' : 'Oracle awake · live questions open';
    } catch (e) {
      S.busy = null;
      el.className = 'status';
      el.querySelector('span').textContent = 'Oracle unreachable · replay mode';
    }
  }

  /* ---------------- chooser ---------------- */
  function goldVerdict(rec) {
    const g = rec.gold; if (!g) return null;
    if (g.abstain) return isAbstain(rec);
    if (isAbstain(rec)) return false;
    const a = norm(rec.answer), b = norm(g.answer);
    if (!a || !b) return false;
    if (b.includes(a) || a.includes(b)) return true;
    const na = nums(rec.answer), nb = nums(g.answer);
    if (na.length && nb.length) return na[0] === nb[0];
    const words = (s) => s.split(' ').filter((w) => w.length > 2 && !STOP.has(w));
    const ta = words(a), tb = words(b);
    const ov = (x, y) => (x.length ? x.filter((w) => y.includes(w)).length / x.length : 0);
    return Math.max(ov(ta, tb), ov(tb, ta)) >= 0.6;
  }

  function renderChooser() {
    const recs = S.data[S.split] || [];
    const groups = {};
    for (const r of recs) (groups[ROUTES[r.route] ? r.route : 'other'] ||= []).push(r);
    const keys = [...ORDER.filter((k) => groups[k]), ...(groups.other ? ['other'] : [])];
    const box = $('#kinds'); box.innerHTML = '';
    for (const k of keys) {
      const meta = ROUTES[k] || { name: 'Other questions', sub: '' };
      const sec = document.createElement('section'); sec.className = 'kind open';
      sec.innerHTML = `<button type="button"><span class="sigwrap"><svg class="sig"><use href="#sig-${ROUTES[k] ? k : 'ssu'}"/></svg></span>
        <span class="kind-name">${esc(meta.name)}<small>${esc(meta.sub)}</small></span><span class="kind-count">${groups[k].length}</span></button><ul></ul>`;
      sec.querySelector('button').addEventListener('click', () => sec.classList.toggle('open'));
      const ul = sec.querySelector('ul');
      for (const r of groups[k]) {
        const li = document.createElement('li'); li.dataset.qid = r.question_id;
        let mark = `<span>${roman(S.persons[r.history_id] || 0)}</span>`;
        const v = goldVerdict(r);
        if (v === true) mark += ' <span class="ok" title="matches the gold answer">✓</span>';
        else if (v === false) mark += ' <span class="no" title="differs from the gold answer">✗</span>';
        else if (isAbstain(r)) mark += ' <span class="ab" title="the Oracle said: not in the archive">∅</span>';
        li.innerHTML = `<span>${esc(r.question)}</span><span class="mark">${mark}</span>`;
        li.addEventListener('click', () => { exitTour(); play(r); });
        ul.appendChild(li);
      }
      box.appendChild(sec);
    }
    markSelected();
  }
  function markSelected() { $$('.kind li').forEach((li) => li.classList.toggle('sel', !!S.rec && li.dataset.qid === S.rec.question_id && !S.rec.live)); }

  /* ---------------- archive ---------------- */
  function renderArchive(hid) {
    if (S.hid === hid) return;
    S.hid = hid;
    const tl = (S.data.timelines[hid] || []).slice();
    const sz = S.sizes[hid] || null;
    const chars = tl.map((s) => (sz && sz[s.id]) || EST_CHARS);
    const total = chars.reduce((a, b) => a + b, 0);
    S.archiveChars = total; S.archiveExact = !!sz;
    S.timeline = tl;
    const ph = $('#phases li[data-phase="archive"] small'); if (ph) ph.textContent = `${tl.length} conversations`;
    $('#who').innerHTML = NAMES[hid] ? esc(archiveName(hid)) : `The Archive of Person <span class="rn">${roman(S.persons[hid] || 0)}</span>`;
    const first = parseDate(tl[0]?.date), last = parseDate(tl[tl.length - 1]?.date);
    const range = first && last ? ` · ${MONTHS[first.mo]} ${first.y} – ${MONTHS[last.mo]} ${last.y}` : '';
    $('#count').innerHTML = tl.length
      ? `<b>${fmt(tl.length)}</b> conversations · <b>${sz ? '' : '~'}${(total / 1e6).toFixed(2)}M</b> characters${range}`
      : 'no conversations recorded for this person';

    const wrap = $('#shelves'); wrap.innerHTML = '';
    S.books = new Map();
    const n = tl.length; if (!n) return;
    const wide = wrap.clientWidth > 1250;
    const nShelves = n <= 60 ? Math.max(1, Math.ceil(n / 30)) : (wide ? 3 : 4);
    const per = Math.ceil(n / nShelves);
    const maxC = Math.max(...chars);
    let shelf = null, lastMonth = -1, monthIdx = -1;
    const hues = [[8, 48], [96, 30], [218, 42], [36, 52], [292, 22], [22, 44], [160, 30], [348, 40]];
    tl.forEach((s, i) => {
      if (i % per === 0) { shelf = document.createElement('div'); shelf.className = 'shelf'; wrap.appendChild(shelf); }
      const p = parseDate(s.date);
      const mkey = p ? p.y * 12 + p.mo : -1;
      const b = document.createElement('div'); b.className = 'book'; b.dataset.id = s.id; b.dataset.i = i;
      if (mkey !== lastMonth) { monthIdx++; lastMonth = mkey; if (p) b.innerHTML = `<span class="mtag">${MONTHS[p.mo].toUpperCase()}${p.mo === 0 || i === 0 ? ` ’${String(p.y).slice(2)}` : ''}</span>`; }
      const r = hash(s.id); const [hh, ss] = hues[monthIdx % hues.length];
      const grow = 0.55 + 1.6 * Math.sqrt(chars[i] / maxC);
      b.style.flex = `${grow.toFixed(3)} 1 0px`;
      b.style.setProperty('--h', `${(72 + 26 * r).toFixed(1)}%`);
      b.style.setProperty('--c', `hsl(${hh + (r - 0.5) * 16} ${ss}% ${(17 + r * 12).toFixed(1)}%)`);
      shelf.appendChild(b);
      S.books.set(s.id, b);
    });
  }

  function bindBookTips() {
    const arch = $('#archive'), tip = $('#booktip');
    arch.addEventListener('mouseover', (e) => {
      const b = e.target.closest('.book'); if (!b) return;
      const s = S.timeline?.[+b.dataset.i]; if (!s) return;
      const sz = S.sizes[S.hid]?.[s.id];
      tip.innerHTML = `<time>${prettyDate(s.date)}${sz ? ` · ${fmt(sz)} chars` : ''}</time>${esc(s.title)}${s.title && s.title.length >= 88 ? '…' : ''}`;
      tip.hidden = false;
      const ar = arch.getBoundingClientRect(), br = b.getBoundingClientRect();
      const x = Math.min(Math.max(8, br.left - ar.left - 40), ar.width - 350);
      tip.style.left = x + 'px'; tip.style.top = (br.bottom - ar.top + 14) + 'px';
      if (br.bottom - ar.top > ar.height * 0.6) tip.style.top = (br.top - ar.top - tip.offsetHeight - 10) + 'px';
    });
    arch.addEventListener('mouseout', (e) => { if (e.target.closest('.book')) tip.hidden = true; });
  }

  /* ---------------- owl ---------------- */
  function owlEl() { return $('#owl'); }
  function homePos() {
    const a = $('#archive').getBoundingClientRect(), o = owlEl().getBoundingClientRect();
    return { x: a.width - o.width - 14, y: -o.height * 0.36 };
  }
  function parkOwl(instant) {
    const h = homePos();
    if (instant) { owlEl().style.transform = `translate(${h.x}px, ${h.y}px)`; S.owl = h; return Promise.resolve(); }
    return owlTo(h.x, h.y, 900);
  }
  function owlTo(x, y, dur) {
    const el = owlEl(); const from = S.owl;
    S.owl = { x, y };
    const mx = (from.x + x) / 2, my = Math.min(from.y, y) - 26;
    return animate(el, [
      { transform: `translate(${from.x}px, ${from.y}px)` },
      { transform: `translate(${mx}px, ${my}px)`, offset: 0.5 },
      { transform: `translate(${x}px, ${y}px)` },
    ], { duration: dur, easing: 'ease-in-out' });
  }
  function owlOver(book, dur) {
    const a = $('#archive').getBoundingClientRect(), b = book.getBoundingClientRect(), o = owlEl().getBoundingClientRect();
    const x = b.left - a.left + b.width / 2 - o.width / 2;
    const y = Math.max(-o.height * 0.3, b.top - a.top - o.height * 0.62);
    return owlTo(x, y, dur);
  }

  /* ---------------- phases ---------------- */
  const PH = ['archive', 'search', 'notes', 'oracle'];
  function setPhase(p) {
    const k = PH.indexOf(p);
    $$('#phases li').forEach((li, i) => { li.classList.toggle('active', i === k); li.classList.toggle('done', i < k); });
  }

  /* ---------------- question bar ---------------- */
  function setQuestion(rec, caption, tourLabel) {
    const q = (rec.question || '').trim();
    const firstCh = q.charAt(0) || '?';
    const meta = ROUTES[rec.route] || { name: rec.live ? 'Live question' : 'Question', sub: '' };
    const sig = ROUTES[rec.route] ? rec.route : 'live';
    $('#qmeta').innerHTML = `<span><svg class="sig"><use href="#sig-${sig}"/></svg>${esc(meta.name)}</span>`
      + `<span class="dim">${esc(personLabel(rec.history_id))}${NAMES[rec.history_id] ? ' · ' + NAMES[rec.history_id] : ''}</span>`
      + (rec.question_date ? `<span class="dim">asked ${shortDate(rec.question_date)}</span>` : '')
      + (rec.live ? '<span>· live</span>' : '')
      + (rec.split === 'dev' && !rec.live ? '<span class="dim">calibration · gold known</span>' : '')
      + (tourLabel ? `<span>${esc(tourLabel)}</span>` : '');
    const cap = $('#qcap'); cap.innerHTML = `<span>${esc(/[A-Za-z]/.test(firstCh) ? firstCh.toUpperCase() : '?')}</span>`;
    animate(cap, [{ opacity: 0, transform: 'scale(.6) rotate(-8deg)', filter: 'blur(6px)' }, { opacity: 1, transform: 'none', filter: 'blur(0)' }], { duration: 700, easing: 'cubic-bezier(.3,1.5,.5,1)' });
    const rest = /[A-Za-z]/.test(firstCh) ? q.slice(1) : q;
    const words = rest.split(/(\s+)/);
    $('#qtext').innerHTML = words.map((w, i) => (/^\s+$/.test(w) ? w : `<span class="w" style="animation:inkin .7s ${(0.25 + i * 0.035).toFixed(2)}s ease-out both">${esc(w)}</span>`)).join('');
    const c = $('#qcaption'); c.textContent = caption || '';
    if (caption) animate(c, [{ opacity: 0 }, { opacity: 1 }], { duration: 900, delay: 900 });
  }

  /* ---------------- desk ---------------- */
  const NUMRE = /\b(\d+(?:[.,]\d+)?|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|twenty|dozen|half)\b/i;
  function keyStems(q) { return norm(q).split(' ').filter((w) => w.length > 2 && !STOP.has(w)).map((w) => w.slice(0, 5)); }
  function needlesFor(rec) {
    const quotes = [];
    const re = /["“]([^"”]{12,})["”]/g; let m;
    while ((m = re.exec(rec.notes || ''))) quotes.push(norm(m[1]));
    let ans = null;
    const a = (rec.answer || '').trim();
    if (!isAbstain(rec) && a.length >= 3 && !/^[\d\s.,%]+$/.test(a)) ans = a;
    const count = rec.route === 'multi' ? keyStems(rec.question) : null;
    return { quotes, ans, count };
  }
  function sentenceHTML(raw, nd) {
    const parts = raw.match(/[^.!?…]+(?:[.!?…]+["”’)]*\s*|$)|[.!?…]+\s*/g) || [raw];
    return parts.map((part) => {
      const n = norm(part);
      let hit = false;
      if (n.length >= 12) hit = nd.quotes.some((q) => q.includes(n) || (q.length >= 12 && n.includes(q)));
      if (!hit && nd.count && nd.count.length && NUMRE.test(part)) {
        const ws = n.split(' ');
        hit = nd.count.filter((k) => ws.some((w) => w.startsWith(k))).length >= Math.min(2, nd.count.length);
      }
      let html = esc(part);
      if (nd.ans) {
        const idx = part.toLowerCase().indexOf(nd.ans.toLowerCase());
        if (idx >= 0) {
          hit = true;
          html = esc(part.slice(0, idx)) + `<span class="ans">${esc(part.slice(idx, idx + nd.ans.length))}</span>` + esc(part.slice(idx + nd.ans.length));
        }
      }
      return hit ? `<span class="hl">${html}</span>` : html;
    }).join('');
  }
  function passageHTML(text, nd) {
    const out = [];
    for (const line of String(text || '').split('\n')) {
      const t = line.trim(); if (!t) continue;
      if (/^\[\s*(\.\.\.|…)\s*\]$/.test(t)) { out.push('<div class="gap">⁂</div>'); continue; }
      const m = /^(user|assistant)\s*:\s?(.*)$/i.exec(t);
      if (m) {
        const u = m[1].toLowerCase() === 'user';
        out.push(`<p class="${u ? 'usr' : 'asst'}"><span class="who ${u ? 'u' : 'a'}">${u ? 'User' : 'Assistant'}</span>${sentenceHTML(m[2], nd)}</p>`);
      } else out.push(`<p>${sentenceHTML(t, nd)}</p>`);
    }
    return out.join('') || '<p class="muted">(an empty page)</p>';
  }
  function buildPages(rec) {
    const box = $('#pages'); box.innerHTML = ''; box.scrollLeft = 0;
    const ps = rec.passages || [];
    box.classList.toggle('few', ps.length > 0 && ps.length <= 2);
    if (!ps.length) {
      box.innerHTML = '<div class="desk-empty">No page in the archive matched.<br>The Librarian brings an empty dossier.</div>';
      return [];
    }
    const nd = needlesFor(rec);
    return ps.map((p, i) => {
      const el = document.createElement('article');
      el.className = 'page parchment'; el.dataset.id = p.id;
      el.style.transform = `rotate(${((hash(p.id + i) - 0.5) * 1.6).toFixed(2)}deg)`;
      const pd = parseDate(p.date);
      el.innerHTML = `<header><span class="folio">${roman(i + 1)}</span><time>${pd ? `${pd.d} ${MONTHS[pd.mo]} ${pd.y}${pd.time ? ' · ' + pd.time : ''}` : esc(p.date || '')}</time></header>
        <svg class="seal" viewBox="0 0 60 60"><use href="#seal"/></svg>
        <div class="page-body" style="position:relative">${passageHTML(p.text, nd)}</div>`;
      box.appendChild(el);
      return el;
    });
  }
  function flyBook(book, page, delay) {
    const br = book.getBoundingClientRect();
    const box = $('#pages').getBoundingClientRect();
    let pr = page.getBoundingClientRect();
    const tx = Math.min(pr.left, box.right - 80), ty = pr.top;
    const tw = Math.min(pr.width, box.right - tx), th = Math.min(pr.height, 160);
    const f = document.createElement('div'); f.className = 'flybook';
    f.style.cssText = `left:${br.left}px;top:${br.top}px;width:${br.width}px;height:${br.height}px;background:${getComputedStyle(book).background}`;
    document.body.appendChild(f);
    const dx = tx - br.left, dy = ty - br.top;
    const sx = Math.max(0.2, tw / Math.max(1, br.width)), sy = Math.max(0.2, th / Math.max(1, br.height));
    f.style.transformOrigin = '0 0';
    return animate(f, [
      { transform: 'translate(0,0) scale(1,1) rotate(0deg)', opacity: 1 },
      { transform: `translate(${dx * 0.45}px, ${dy * 0.25 - 90}px) scale(${1 + (sx - 1) * 0.3}, ${1 + (sy - 1) * 0.3}) rotate(-12deg)`, opacity: 1, offset: 0.5 },
      { transform: `translate(${dx}px, ${dy}px) scale(${sx}, ${sy}) rotate(0deg)`, opacity: 0.0 },
    ], { duration: 1050, delay, easing: 'cubic-bezier(.5,0,.3,1)' }).then(() => f.remove());
  }
  function ensureVisible(page) {
    const box = $('#pages'); if (!page || !box) return;
    const l = page.offsetLeft, r = l + page.offsetWidth, vl = box.scrollLeft, vr = vl + box.clientWidth;
    if (r > vr - 4) box.scrollTo({ left: Math.max(0, r - box.clientWidth + 12), behavior: 'smooth' });
    else if (l < vl) box.scrollTo({ left: Math.max(0, l - 12), behavior: 'smooth' });
  }
  function revealPage(page, delay) {
    return animate(page, [
      { opacity: 0, filter: 'blur(8px) sepia(.6)', clipPath: 'circle(0% at 50% 18%)' },
      { opacity: 1, filter: 'blur(0px) sepia(0)', clipPath: 'circle(150% at 50% 18%)' },
    ], { duration: 900, delay, easing: 'ease-out' }).then(() => { page.style.clipPath = 'none'; page.style.filter = 'none'; });
  }

  function notesHTML(rec) {
    const raw = String(rec.notes || '').trim();
    const blocks = [];
    if (rec.route === 'temporal' && rec.computed != null && rec.computed !== '') {
      const u = /how many\s+(days|weeks|months|years)/i.exec(rec.question || '');
      blocks.push(`<div class="ink"><span class="reckon">code reckons <b>${esc(rec.computed)}${u ? ' ' + esc(u[1].toLowerCase()) : ''}</b></span></div>`);
    }
    if (!raw) {
      blocks.push('<p class="ink muted">No notes this time: the pages speak for themselves.</p>');
      return blocks.join('');
    }
    const inline = (s) => esc(s)
      .replace(/"([^"]{2,})"/g, '<q>$1</q>')
      .replace(/\b(\d{4}[-/]\d{2}[-/]\d{2})\b/g, '<span class="num">$1</span>')
      .replace(/\b(\d+ (?:days?|weeks?|months?|years?))\b/g, '<span class="num">$1</span>')
      .replace(/\b(MOST RECENT|NOT|ignore)\b/g, '<u>$1</u>');
    let list = null;
    for (const line of raw.split('\n')) {
      const t = line.trim(); if (!t) continue;
      if (/^[-•*]\s+/.test(t)) {
        if (!list) { list = []; blocks.push(list); }
        list.push(`<li class="ink">${inline(t.replace(/^[-•*]\s+/, ''))}</li>`);
      } else { list = null; blocks.push(`<p class="ink">${inline(t)}</p>`); }
    }
    return blocks.map((b) => (Array.isArray(b) ? `<ul>${b.join('')}</ul>` : b)).join('');
  }
  async function writeNotes(rec, alive) {
    const body = $('#marginBody');
    body.innerHTML = notesHTML(rec); body.scrollTop = 0;
    const inks = $$('.ink', body);
    inks.forEach((e) => { e.style.opacity = '0'; });
    const totalLen = inks.reduce((a, e) => a + e.textContent.length, 0) || 1;
    const budget = Math.min(4200, 900 + totalLen * 6);
    for (const e of inks) {
      if (!alive()) return;
      const d = Math.max(260, Math.min(1500, budget * (e.textContent.length / totalLen)));
      if (e.offsetTop + e.offsetHeight > body.scrollTop + body.clientHeight) body.scrollTo({ top: e.offsetTop - 30, behavior: 'smooth' });
      await animate(e, [
        { opacity: 1, clipPath: 'inset(0 100% 0 0)', filter: 'blur(2px)' },
        { opacity: 1, clipPath: 'inset(0 0% 0 0)', filter: 'blur(0)' },
      ], { duration: d, easing: 'linear' });
      e.style.clipPath = 'none'; e.style.filter = 'none';
    }
    await sleep(700);
    if (alive() && body.scrollTop > 0) body.scrollTo({ top: 0, behavior: 'smooth' });
  }

  /* ---------------- oracle ---------------- */
  function resetOracle() {
    const eye = $('#eye'); eye.setAttribute('class', 'eye');
    $('#answerText').className = 'answer-text';
    $('#answerText').innerHTML = '<span class="muted">sleeps until the dossier arrives</span>';
    $('#answerSub').innerHTML = ''; $('#cites').innerHTML = '';
    $('#goldCheck').hidden = true; $('#liveAct').hidden = true; $('#liveAct').innerHTML = '';
    $('#pct').textContent = '—'; $('#pctBar').style.width = '0';
    $('#ribbonSmall').innerHTML = 'The Oracle reads a few pages, never the whole library.';
  }
  function setEye(state) { $('#eye').setAttribute('class', 'eye' + (state ? ' ' + state : '')); }
  function letters(el, text, cls) {
    el.className = 'answer-text ' + cls;
    let i = 0;
    el.innerHTML = text.split(/(\s+)/).map((w) => (/^\s+$/.test(w) ? ' '
      : `<span class="wd">${[...w].map((c) => `<span class="ch" style="animation:inkin .6s ${(i++ * 0.04).toFixed(2)}s ease-out both">${esc(c)}</span>`).join('')}</span>`)).join('');
  }
  function ribbon(rec) {
    const ps = rec.passages || [];
    const read = ps.reduce((a, p) => a + (p.text || '').length, 0);
    const total = S.archiveChars || 1;
    const pct = (read / total) * 100;
    const target = $('#pct');
    const t0 = performance.now(), dur = REDUCED ? 1 : 1100;
    const step = (t) => {
      const k = Math.min(1, (t - t0) / dur);
      const v = pct * (1 - Math.pow(1 - k, 3));
      target.textContent = (pct < 1 ? v.toFixed(2) : v.toFixed(1)) + '%';
      if (k < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
    $('#pctBar').style.width = Math.max(0.6, Math.min(100, pct)) + '%';
    const lat = rec.latency_s != null ? ` · <span class="nw">Oracle replied in <b>${Number(rec.latency_s).toFixed(1)} s</b></span>` : '';
    $('#ribbonSmall').innerHTML = `<span class="nw"><b>${ps.length}</b> page${ps.length === 1 ? '' : 's'}</span> · <span class="nw"><b>${fmt(read)}</b> of <b>${S.archiveExact ? '' : '~'}${fmt(total)}</b> characters</span>${lat}`;
  }
  async function revealAnswer(rec, alive) {
    const abst = isAbstain(rec);
    const at = $('#answerText'), sub = $('#answerSub');
    if (abst) {
      setEye('half');
      letters(at, 'Not written in the archive', 'none');
      const n = (rec.passages || []).length;
      sub.textContent = n
        ? `It read ${n} page${n === 1 ? '' : 's'} and found no statement of it, so it says so instead of guessing.`
        : 'No page holds it, so it says so instead of guessing.';
    } else {
      setEye('open');
      const ans = (rec.answer || '').trim();
      letters(at, ans || '(silence)', 'gilt');
      sub.textContent = '';
      if (rec.route === 'temporal' && rec.computed != null && nums(ans)[0] === nums(String(rec.computed))[0]) {
        sub.textContent = 'agrees with the code’s own date reckoning';
      }
    }
    await sleep(700);
    if (!alive()) return;
    const cited = (rec.cited || []).filter(Boolean);
    const pageIds = (rec.passages || []).map((p) => p.id);
    const cites = $('#cites'); cites.innerHTML = '';
    const ordered = [...cited].sort((a, b) => pageIds.indexOf(a) - pageIds.indexOf(b));
    for (const id of ordered) {
      if (!alive()) return;
      const k = pageIds.indexOf(id);
      const p = (rec.passages || [])[k];
      const c = document.createElement('div'); c.className = 'cite';
      c.innerHTML = `<svg viewBox="0 0 60 60"><use href="#seal"/></svg><span>${k >= 0 ? 'page ' + roman(k + 1) + ' · ' : ''}${p ? shortDate(p.date) : esc(id)}</span>`;
      cites.appendChild(c);
      animate(c, [{ opacity: 0, transform: 'scale(1.6)' }, { opacity: 1, transform: 'scale(1)' }], { duration: 420, easing: 'cubic-bezier(.3,1.6,.5,1)' });
      const page = $(`.page[data-id="${CSS.escape(id)}"]`);
      if (page) {
        page.classList.add('cited');
        const seal = $('.seal', page);
        animate(seal, [{ opacity: 0, transform: 'scale(2.4) rotate(-40deg)' }, { opacity: 1, transform: 'scale(1) rotate(-8deg)' }], { duration: 520, easing: 'cubic-bezier(.4,1.8,.5,1)' });
        ensureVisible(page);
      }
      const book = S.books?.get(id);
      if (book && !$('.wax', book)) {
        book.insertAdjacentHTML('beforeend', '<svg class="wax" viewBox="0 0 60 60"><use href="#seal"/></svg>');
        animate($('.wax', book), [{ opacity: 0, transform: 'translate(-50%,-50%) scale(3)' }, { opacity: 1, transform: 'translate(-50%,-50%) scale(1)' }], { duration: 480, easing: 'cubic-bezier(.4,1.8,.5,1)' });
      }
      await sleep(330);
    }
    if (!cited.length && !abst && !rec.live && rec.split === 'dev') {
      cites.innerHTML = '<div class="cite" style="opacity:1"><span>calibration run · page labels not recorded</span></div>';
    }
    await strikeDecoy(rec, alive);
    if (!alive()) return;
    const v = goldVerdict(rec);
    if (v !== null && v !== undefined && rec.gold) {
      const g = $('#goldCheck');
      const gold = rec.gold.abstain ? 'not in the archive' : String(rec.gold.answer || '');
      g.className = 'gold-check ' + (v ? 'ok' : 'no');
      g.innerHTML = `<b>${v ? '✓ Matches the gold key' : '✗ Differs from the gold key'}</b><br>gold: ${esc(gold.length > 110 ? gold.slice(0, 110) + '…' : gold)}`;
      g.hidden = false;
      animate(g, [{ opacity: 0, transform: 'translateY(6px)' }, { opacity: 1, transform: 'none' }], { duration: 500 });
    }
    ribbon(rec);
  }

  async function strikeDecoy(rec, alive) {
    const c = rec.computed;
    if (c == null || typeof c !== 'string' || c.trim().length < 2 || /^[\d\s.,%-]+$/.test(c)) return;
    if (!isAbstain(rec) && norm(rec.answer).includes(norm(c))) return;
    const needle = c.trim().toLowerCase();
    let hitEl = null;
    for (const body of $$('.page .page-body')) {
      for (const p of $$('p', body)) {
        if (!p.textContent.toLowerCase().includes(needle)) continue;
        const walker = document.createTreeWalker(p, NodeFilter.SHOW_TEXT);
        let node;
        while ((node = walker.nextNode())) {
          const idx = node.data.toLowerCase().indexOf(needle);
          if (idx < 0) continue;
          const r = document.createRange(); r.setStart(node, idx); r.setEnd(node, idx + needle.length);
          const span = document.createElement('span'); span.className = 'decoy'; span.title = 'found by code, not accepted by the Oracle';
          r.surroundContents(span); hitEl = hitEl || span; break;
        }
      }
    }
    if (!hitEl) return;
    const page = hitEl.closest('.page'), body = hitEl.closest('.page-body');
    ensureVisible(page);
    if (body) body.scrollTo({ top: Math.max(0, hitEl.offsetTop - body.clientHeight * 0.35), behavior: 'smooth' });
    await sleep(500); if (!alive()) return;
    $$('.decoy').forEach((d) => d.classList.add('struck'));
    const mb = $('#marginBody');
    mb.insertAdjacentHTML('beforeend', `<p class="ink decoy-note">☒ <q>${esc(c)}</q> was a candidate the code found; the Oracle did not accept it.</p>`);
    const n = mb.lastElementChild;
    animate(n, [{ opacity: 0, clipPath: 'inset(0 100% 0 0)' }, { opacity: 1, clipPath: 'inset(0 0 0 0)' }], { duration: 900 });
    mb.scrollTo({ top: mb.scrollHeight, behavior: 'smooth' });
    await sleep(600);
  }

  /* ---------------- live ask ---------------- */
  function liveOracle(rec, alive) {
    const act = $('#liveAct'); act.hidden = false;
    const sub = $('#answerSub');
    $('#answerText').className = 'answer-text';
    $('#answerText').innerHTML = '<span class="muted">the dossier is ready</span>';
    ribbon({ ...rec, latency_s: null });
    if (S.busy !== false) {
      setEye('half');
      sub.textContent = S.busy
        ? 'The Oracle is busy with the benchmark run, so only recorded answers are replayed. Nothing is invented.'
        : 'The Oracle cannot be reached right now. Nothing is invented.';
      act.innerHTML = '<button type="button" id="retryAsk">Knock on the Oracle’s door</button>';
    } else {
      setEye('');
      sub.textContent = 'The Librarian packed these pages live. The Oracle takes one to two minutes to read them.';
      act.innerHTML = '<button type="button" id="retryAsk">Consult the Oracle</button>';
    }
    $('#retryAsk').addEventListener('click', () => askLive(rec, alive));
  }
  async function askLive(rec, alive) {
    const act = $('#liveAct'), sub = $('#answerSub');
    const t0 = Date.now();
    act.innerHTML = '<span class="hourglass">⧗</span><span id="askClock">The Oracle is reading… 0 s</span>';
    setEye('open reading');
    const clock = setInterval(() => { const c = $('#askClock'); if (c) c.textContent = `The Oracle is reading… ${Math.round((Date.now() - t0) / 1000)} s`; }, 1000);
    try {
      const body = rec.base_qid ? { question_id: rec.base_qid, question: rec.question } : { question_id: rec.question_id };
      const res = await postJSON('/api/ask', body);
      clearInterval(clock);
      if (!alive()) return;
      act.hidden = true;
      const full = { ...rec, ...res, passages: rec.passages, live: true };
      S.rec = full;
      await revealAnswer(full, alive);
    } catch (e) {
      clearInterval(clock);
      if (!alive()) return;
      setEye('half');
      if (e.status === 409) {
        S.busy = true; pollStatus();
        sub.textContent = 'The Oracle is busy with the benchmark run: replaying recorded answers only. No answer was invented.';
      } else {
        sub.textContent = `The Oracle did not answer (${e.message}). No answer was invented.`;
      }
      act.innerHTML = '<button type="button" id="retryAsk">Try again</button>';
      $('#retryAsk').addEventListener('click', () => askLive(rec, alive));
    }
  }

  /* ---------------- the performance ---------------- */
  function candidatesFor(rec) {
    const tl = S.timeline || [];
    const chosen = new Set((rec.passages || []).map((p) => p.id));
    const kw = norm(rec.question).split(' ').filter((w) => w.length > 2 && !STOP.has(w)).map((w) => w.slice(0, 5));
    if (!kw.length) return [];
    const scored = [];
    tl.forEach((s) => {
      if (chosen.has(s.id)) return;
      const t = norm(s.title).split(' ');
      let sc = 0; for (const k of kw) if (t.some((w) => w.startsWith(k))) sc++;
      if (sc) scored.push([sc + hash(s.id) * 0.5, s.id]);
    });
    scored.sort((a, b) => b[0] - a[0]);
    return scored.slice(0, 7).map((x) => x[1]);
  }

  function clearMarks() {
    $$('.book.cand, .book.chosen, .book.seen').forEach((b) => b.classList.remove('cand', 'chosen', 'seen'));
    $$('.book .wax').forEach((w) => w.remove());
    $('#archive').classList.remove('dim');
  }

  async function play(rec, opts = {}) {
    const id = ++S.runId;
    const alive = () => id === S.runId;
    clearTimeout(S.holdTimer);
    $$('.flybook').forEach((f) => f.remove());
    S.rec = rec; S.base = rec.live ? S.base : rec;
    markSelected();
    renderArchive(rec.history_id);
    setLivePerson(rec.history_id);
    clearMarks(); resetOracle();
    $('#desk').classList.remove('idle');
    $('#booktip').hidden = true;
    $('#marginBody').innerHTML = '<p class="muted">The Librarian is searching the shelves…</p>';
    $('#pages').innerHTML = ''; $('#pages').classList.remove('few');
    setPhase('archive');
    setQuestion(rec, opts.caption, opts.tourLabel);
    await sleep(1300); if (!alive()) return;

    /* II · search */
    setPhase('search');
    const arch = $('#archive'); arch.classList.add('dim');
    const owl = owlEl(); owl.classList.add('searching');
    const chosenIds = (rec.passages || []).map((p) => p.id).filter((x) => S.books?.has(x));
    const cand = candidatesFor(rec);
    const visit = [...new Set([...cand, ...chosenIds])].map((x) => S.books.get(x)).filter(Boolean)
      .sort((a, b) => a.dataset.i - b.dataset.i);
    const per = Math.max(170, Math.min(420, 4200 / Math.max(1, visit.length)));
    S.moving = true;
    for (const b of visit) {
      if (!alive()) { S.moving = false; return; }
      await owlOver(b, per);
      b.classList.add('cand');
    }
    S.moving = false;
    await sleep(250); if (!alive()) return;
    for (const x of chosenIds) { const b = S.books.get(x); b.classList.remove('cand'); b.classList.add('chosen'); }
    $$('.book.cand').forEach((b) => { b.classList.remove('cand'); b.classList.add('seen'); });
    await sleep(650); if (!alive()) return;

    /* books fly to the desk */
    const pages = buildPages(rec);
    const flights = [];
    (rec.passages || []).forEach((p, i) => {
      const book = S.books?.get(p.id), page = pages[i];
      if (book && page && i < 8) flights.push(flyBook(book, page, i * 160));
    });
    parkOwl(false);
    owl.classList.remove('searching');
    await Promise.all([Promise.all(flights), sleep(300)]);
    if (!alive()) return;

    /* III · pages + margin notes */
    setPhase('notes');
    await Promise.all(pages.map((pg, i) => revealPage(pg, Math.min(i, 6) * 120)));
    if (!alive()) return;
    const hls = $$('.page .hl');
    hls.forEach((h, i) => setTimeout(() => { if (alive()) h.classList.add('lit'); }, 150 + i * 220));
    pages.forEach((pg) => {
      const h = $('.hl', pg); const body = $('.page-body', pg);
      if (h && body) body.scrollTo({ top: Math.max(0, h.offsetTop - body.clientHeight * 0.25), behavior: 'smooth' });
    });
    const hlPages = pages.filter((pg) => $('.hl', pg));
    if (hlPages.length) ensureVisible(hlPages[hlPages.length - 1]);
    await writeNotes(rec, alive);
    if (!alive()) return;
    await sleep(500); if (!alive()) return;

    /* IV · oracle */
    setPhase('oracle');
    if (rec.live && rec.answer == null) { liveOracle(rec, alive); return; }
    setEye('open reading');
    $('#answerText').innerHTML = '<span class="muted">reading the dossier…</span>';
    await sleep(1500); if (!alive()) return;
    $('#eye').classList.remove('reading');
    await revealAnswer(rec, alive);
    if (!alive()) return;
    if (opts.onDone) opts.onDone(id);
  }

  /* ---------------- tour ---------------- */
  function tourRecs() { return TOUR.map((t) => ({ ...t, rec: findRec(t.id) })).filter((t) => t.rec); }
  function renderDots() {
    const d = $('#tourDots'); d.innerHTML = '';
    tourRecs().forEach((t, i) => {
      const dot = document.createElement('i'); dot.title = `${i + 1}. ${t.rec.question}`;
      dot.addEventListener('click', () => goTour(i, S.playing));
      d.appendChild(dot);
    });
  }
  function updateTourUI() {
    $$('#tourDots i').forEach((d, i) => d.classList.toggle('on', i === S.tourIdx));
    const b = $('#tourPlay'); b.textContent = S.playing ? '❚❚' : '▶'; b.setAttribute('aria-label', S.playing ? 'Pause tour' : 'Play tour');
    document.body.classList.toggle('touring', S.touring);
  }
  function goTour(i, autoplay) {
    const stops = tourRecs(); if (!stops.length) { toast('The tour questions are not in this replay.'); return; }
    S.tourIdx = (i + stops.length) % stops.length;
    S.playing = !!autoplay;
    const wasTouring = S.touring;
    S.touring = true; updateTourUI();
    const t = stops[S.tourIdx];
    const start = () => play(t.rec, {
      caption: t.cap, tourLabel: `tour ${S.tourIdx + 1} / ${stops.length}`,
      onDone: (runId) => {
        if (!S.playing) return;
        S.holdTimer = setTimeout(() => {
          if (runId !== S.runId || !S.playing) return;
          if (S.tourIdx + 1 < stops.length) goTour(S.tourIdx + 1, true);
          else { S.playing = false; updateTourUI(); }
        }, HOLD_MS);
      },
    });
    const tok = ++S.tourTok;
    if (!wasTouring) { S.runId++; setTimeout(() => { if (tok !== S.tourTok) return; parkOwl(true); start(); }, 750); } else start();
  }
  function togglePlay() {
    if (!S.touring || S.tourIdx < 0) { goTour(0, true); return; }
    S.playing = !S.playing; updateTourUI();
    if (S.playing) {
      // resume: advance if the current stop already finished
      const done = $('#phases li:last-child').classList.contains('active') && !$('#eye').classList.contains('reading');
      if (done) goTour(S.tourIdx + 1 < tourRecs().length ? S.tourIdx + 1 : 0, true);
    } else clearTimeout(S.holdTimer);
  }
  function exitTour() {
    S.tourTok++;
    if (!S.touring) return;
    S.touring = false; S.playing = false; clearTimeout(S.holdTimer); updateTourUI();
    setTimeout(() => { if (!S.moving) parkOwl(true); }, 760);
  }
  function toggleFullscreen() {
    if (!document.fullscreenElement) document.documentElement.requestFullscreen?.().catch(() => {});
    else document.exitFullscreen?.().catch(() => {});
  }

  /* ---------------- UI bindings ---------------- */
  function bindUI() {
    bindBookTips();
    document.addEventListener('click', (e) => { const b = e.target.closest('button'); if (b && !b.closest('form')) b.blur(); });
    $('#tourPlay').addEventListener('click', togglePlay);
    $('#tourNext').addEventListener('click', () => goTour(S.tourIdx + 1, S.playing));
    $('#tourPrev').addEventListener('click', () => goTour(Math.max(0, S.tourIdx - 1), S.playing));
    $('#fsBtn').addEventListener('click', toggleFullscreen);
    $$('.split-toggle button').forEach((b) => b.addEventListener('click', () => {
      S.split = b.dataset.split;
      $$('.split-toggle button').forEach((x) => x.classList.toggle('on', x === b));
      if (S.data) renderChooser();
    }));
    document.addEventListener('keydown', (e) => {
      if (e.target.closest('input, textarea')) { if (e.key === 'Escape') e.target.blur(); return; }
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      if (e.key === ' ') { e.preventDefault(); togglePlay(); }
      else if (e.key === 'ArrowRight') { e.preventDefault(); goTour(S.touring ? S.tourIdx + 1 : 0, S.playing); }
      else if (e.key === 'ArrowLeft') { e.preventDefault(); goTour(S.touring ? Math.max(0, S.tourIdx - 1) : 0, S.playing); }
      else if (e.key === 'f' || e.key === 'F') { e.preventDefault(); toggleFullscreen(); }
      else if (e.key === 'Escape') exitTour();
    });
    $('#liveForm').addEventListener('submit', async (e) => {
      e.preventDefault();
      const q = $('#liveQ').value.trim();
      const base = S.base || S.rec;
      if (!q) { $('#liveQ').focus(); return; }
      if (!base) { toast('Pick a recorded question first, so the Librarian knows whose archive to open.'); return; }
      const btn = $('#liveGo'), hint = $('#liveHint');
      btn.disabled = true; hint.textContent = 'The Librarian is pulling books from the shelves…';
      exitTour();
      try {
        const pack = await postJSON('/api/pack', { question_id: base.question_id, question: q });
        await pollStatus();
        const rec = { ...pack, history_id: pack.history_id || base.history_id, question: pack.question || q, split: base.split, live: true, base_qid: base.question_id, answer: null };
        hint.textContent = `Packed ${(pack.passages || []).length} pages in ${pack.build_ms != null ? pack.build_ms + ' ms' : 'a moment'}.`;
        play(rec);
      } catch (err) {
        hint.textContent = 'The Librarian packs pages live; the Oracle answers only when it is not busy.';
        toast(`The stacks are closed: the pack server did not answer (${err.message}).`, 6500);
      } finally { btn.disabled = false; }
    });
  }

  /* ---------------- motes (candle dust & fireflies) ---------------- */
  function initMotes() {
    const c = $('#motes'); const ctx = c.getContext && c.getContext('2d'); if (!ctx) return;
    let w = 0, h = 0, dpr = 1;
    const resize = () => { dpr = Math.min(2, window.devicePixelRatio || 1); w = innerWidth; h = innerHeight; c.width = w * dpr; c.height = h * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0); };
    resize(); addEventListener('resize', resize);
    const N = REDUCED ? 0 : 46;
    const P = Array.from({ length: N }, () => ({
      x: Math.random() * w, y: Math.random() * h, r: 0.6 + Math.random() * 1.9, vy: -(0.08 + Math.random() * 0.25),
      ph: Math.random() * 6.28, sp: 0.4 + Math.random() * 1.2, green: Math.random() < 0.35,
    }));
    const tick = (t) => {
      ctx.clearRect(0, 0, w, h);
      for (const p of P) {
        p.y += p.vy; p.x += Math.sin(t / 1700 * p.sp + p.ph) * 0.25;
        if (p.y < -10) { p.y = h + 10; p.x = Math.random() * w; }
        const a = 0.25 + 0.45 * (0.5 + 0.5 * Math.sin(t / 600 * p.sp + p.ph));
        const g = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.r * 5);
        g.addColorStop(0, p.green ? `rgba(200,240,150,${a})` : `rgba(255,220,140,${a})`);
        g.addColorStop(1, 'rgba(255,200,120,0)');
        ctx.fillStyle = g; ctx.beginPath(); ctx.arc(p.x, p.y, p.r * 5, 0, 6.283); ctx.fill();
      }
      requestAnimationFrame(tick);
    };
    if (N) requestAnimationFrame(tick);
  }

  boot();
})();
