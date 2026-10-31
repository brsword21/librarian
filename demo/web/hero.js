/* Cold open for the pitch (?stage=1 or #hero): the key art with a few living details, then smoke into the demo.
   Every moving part is a crop of the key art itself (or a moth sprite), so nothing on top can drift out of style. */
(() => {
 const hero = document.getElementById('hero'); if (!hero) return;
 const W = 1672, H = 941; // key art pixels; zones below are in these units
 // [x, y, w, h, kind, seconds, delay, pivot] — pivot is a key-art point (px) the crop turns or flickers around
 const ZONES = [
  [1027, 62, 196, 108, 'glow', 2.6, 0],          // tubes in the Reactor dome
  [1062, 222, 162, 102, 'glow', 3.1, -1.2],      // tubes under the first ring
  [392, 14, 86, 74, 'glow', 3.6, -0.7],          // shelf tubes, top
  [210, 158, 104, 82, 'glow', 4.2, -2.1],        // shelf tubes, left
  [424, 330, 64, 60, 'glow', 3.3, -1.6],
  [538, 452, 66, 50, 'glow', 2.9, -0.4],
  [428, 484, 94, 100, 'glow', 1.7, -0.9],        // phosphor screen
  [1030, 183, 18, 18, 'lamp', 5.3, -1],          // ring indicator lamps
  [1142, 177, 19, 19, 'lamp', 7.1, -3.3],
  [1192, 187, 19, 19, 'lamp', 4.4, -2.2],
  [1227, 203, 18, 18, 'lamp', 6.2, -4.8],
  [1037, 334, 19, 19, 'lamp', 5.8, -0.6],
  [1146, 333, 19, 19, 'lamp', 6.7, -2.9],
  [1194, 345, 18, 18, 'lamp', 4.9, -3.9],
  [1203.5, 606.5, 64, 74, 'reel', 5, 0, [1235.5, 643.5]],   // tape reels
  [1279.75, 607.25, 58, 68, 'reel', 5, 0, [1308.75, 641.25]],
  [1556, 618, 28, 46, 'flame', 1.3, 0, [1570, 657]],      // candles
  [1277, 448, 22, 30, 'flame', 1.6, -0.5, [1288, 473]],
  [1292, 232, 22, 28, 'flame', 1.4, -0.9, [1303, 256]],
  [846, 34, 22, 28, 'flame', 1.7, -0.3, [857, 58]],
 ];
 const canvas = document.getElementById('heroCanvas');
 const pct = (v, of) => `${(v / of * 100).toFixed(4)}%`;
 for (const [x, y, w, h, kind, dur, delay, pivot] of ZONES) {
  const z = document.createElement('div'); z.className = `hz ${kind}`; z.setAttribute('aria-hidden', 'true');
  z.style.cssText = `left:${pct(x, W)};top:${pct(y, H)};width:${pct(w, W)};height:${pct(h, H)};--dur:${dur}s;--delay:${delay}s`;
  const img = new Image(); img.src = 'assets/keyart.webp'; img.alt = '';
  img.style.cssText = `width:${pct(W, w)};left:${pct(-x, w)};top:${pct(-y, h)}`;
  if (pivot) img.style.transformOrigin = `${pct(pivot[0], W)} ${pct(pivot[1], H)}`;
  z.appendChild(img); canvas.appendChild(z);
 }

 const stage = document.body.classList.contains('stage');
 const qs = new URLSearchParams(location.search);
 function show() {
  hero.hidden = false; hero.classList.remove('leaving'); document.body.classList.add('hero-on');
  scrollTo(0, 0); document.getElementById('heroEnter').focus({ preventScroll: true });
 }
 function enter() {
  if (hero.hidden || hero.classList.contains('leaving')) return;
  hero.classList.add('leaving');
  setTimeout(() => {
   hero.hidden = true; hero.classList.remove('leaving'); document.body.classList.remove('hero-on');
   window.__librarian?.tourGo(0, false);
  }, matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 1150);
 }
 document.getElementById('heroEnter').addEventListener('click', enter);
 // The logo in the header returns to the cover (the landing); /#hero opens it from other pages such as /inbox.
 document.querySelector('#top .brand')?.addEventListener('click', (e) => { e.preventDefault(); show(); });
 addEventListener('hashchange', () => { if (location.hash === '#hero') show(); });
 // Capture phase: while the cover is up, the demo's own shortcuts must not fire behind it.
 addEventListener('keydown', (e) => {
  if (e.metaKey || e.ctrlKey || e.altKey) return;
  if (hero.hidden) {
   if (stage && e.key === 'Home' && !e.target.closest?.('#method, input, textarea, select')) { e.preventDefault(); e.stopImmediatePropagation(); show(); }
   return;
  }
  if ([' ', 'Enter', 'ArrowRight', 'PageDown'].includes(e.key)) { e.preventDefault(); e.stopImmediatePropagation(); enter(); }
  else if (e.key !== 'f' && e.key !== 'F') e.stopImmediatePropagation();
 }, true);
 if ((stage && !qs.has('tour') && !qs.has('q')) || location.hash === '#hero') show();
})();
