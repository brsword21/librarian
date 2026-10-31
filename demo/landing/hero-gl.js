// WebGL pixel-ribbon background for <canvas class="mosaic" data-variant="hero|cta">.
// Flowing, noise-warped ribbons (violet left, green right) rendered at one fragment per 6px cell and scaled up with
// image-rendering: pixelated; the CSS grid overlay draws the 1px gaps. Ordered (Bayer) dither, an intro sweep, a soft
// glow that follows the pointer, slight drift on scroll. Pauses off-screen / when hidden; one still frame for
// prefers-reduced-motion. Canvases it can't handle (no WebGL, or ?nogl) are left to mosaic.js (2D fallback).
(function () {
  "use strict";
  if (/[?&]nogl\b/.test(location.search)) return;
  const CELL = 6;
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const ease = (t) => (t <= 0 ? 0 : t >= 1 ? 1 : 1 - Math.pow(1 - t, 3));

  const VERT = "attribute vec2 a;void main(){gl_Position=vec4(a,0.,1.);}";
  const FRAG = `
precision highp float;
uniform vec2 uRes; uniform float uTime, uIntro, uScroll, uVariant, uGlow; uniform vec2 uMouse;
float hash(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float noise(vec2 p){ vec2 i = floor(p), f = fract(p), u = f * f * (3. - 2. * f);
  return mix(mix(hash(i), hash(i + vec2(1., 0.)), u.x), mix(hash(i + vec2(0., 1.)), hash(i + vec2(1., 1.)), u.x), u.y); }
float fbm(vec2 p){ float v = 0., a = .5; for (int i = 0; i < 4; i++){ v += a * noise(p); p = p * 2.03 + vec2(1.7, 9.2); a *= .5; } return v; }
float ribbon(float x, float c, float w){ float d = (x - c) / w; return exp(-d * d); }
float bayer2(vec2 a){ a = floor(a); return fract(dot(a, vec2(.5, a.y * .75))); }
float bayer4(vec2 a){ return bayer2(.5 * a) * .25 + bayer2(a); }
void main(){
  vec2 cell = floor(gl_FragCoord.xy);
  vec2 uv = (cell + .5) / uRes;          // y up
  float y = 1. - uv.y;                   // y down, like the page
  float asp = uRes.x / uRes.y, t = uTime;
  vec2 p = vec2(uv.x * asp, y + uScroll);
  vec2 w = vec2(fbm(p * 1.5 + vec2(0., t * .06)), fbm(p * 1.5 + vec2(4.1, -t * .05))) - .5;
  float x = uv.x + w.x * .14, yy = y + w.y * .12 + uScroll;
  float v, g;
  if (uVariant < .5) {
    v = .85 * ribbon(x, .02 + .30 * yy + .06 * sin(yy * 3.1 + t * .32), .07) * (.55 + .45 * sin(yy * 5.5 - t * .55))
      + .50 * ribbon(x, .15 + .22 * yy + .045 * sin(yy * 4.4 + t * .26 + 1.7), .045);
    g = .80 * ribbon(x, .99 - .46 * yy + .06 * sin(yy * 3.6 + t * .30 + .6), .075) * (.55 + .45 * sin(yy * 6. + t * .5))
      + .42 * ribbon(x, .80 - .24 * yy + .045 * sin(yy * 4.8 + t * .24 + 2.4), .05);
    float fade = clamp((1.06 - y) / .55, 0., 1.);
    v *= fade; g *= fade;
  } else {
    float side = smoothstep(.34, .72, uv.x);
    v = .75 * ribbon(x, .60 + .26 * yy + .05 * sin(yy * 4. + t * .3), .07) * (.5 + .5 * sin(yy * 6. - t * .5));
    g = .70 * ribbon(x, .93 - .30 * yy + .05 * sin(yy * 3.2 + t * .26 + 1.2), .08) * (.5 + .5 * sin(yy * 5. + t * .4));
    v *= side; g *= side;
  }
  float stri = .74 + .26 * sin((uv.x * asp + y * 1.35) * 34. - t * 1.3);   // diagonal texture inside the ribbons
  v *= stri; g *= stri;
  float edge = min(uv.x, 1. - uv.x) * 1.4 + y * .35;                       // intro: in from the sides and the top
  float reveal = smoothstep(edge - .02, edge + .2, uIntro * 1.3);
  v *= reveal; g *= reveal;
  vec2 dm = (cell + .5 - uMouse) / uRes.y;                                 // pointer glow, tinted by side
  float glow = exp(-dot(dm, dm) * 16.) * uGlow;
  v += glow * (.55 * (1. - uv.x) + 1.6 * v);
  g += glow * (.50 * uv.x + 1.6 * g);
  float sh = .86 + .14 * sin(hash(cell) * 6.2832 + t * 1.7);
  v *= sh; g *= sh;
  float th = bayer4(cell);
  float vv = min(1., floor(v * 5. + th) / 5.) * .64;
  float gg = min(1., floor(g * 5. + th) / 5.) * .62;
  vec3 col = vec3(13., 16., 18.) / 255. + vec3(78., 58., 214.) / 255. * vv + vec3(46., 170., 40.) / 255. * gg;
  gl_FragColor = vec4(col, 1.);
}`;

  function make(canvas) {
    const gl = canvas.getContext("webgl", { antialias: false, alpha: false, depth: false, stencil: false,
      premultipliedAlpha: false, preserveDrawingBuffer: false, powerPreference: "low-power" });
    if (!gl) return null;
    const sh = (type, src) => {
      const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s);
      if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) { console.warn("hero-gl:", gl.getShaderInfoLog(s)); return null; }
      return s;
    };
    const vs = sh(gl.VERTEX_SHADER, VERT), fs = sh(gl.FRAGMENT_SHADER, FRAG);
    if (!vs || !fs) return null;
    const pr = gl.createProgram();
    gl.attachShader(pr, vs); gl.attachShader(pr, fs); gl.linkProgram(pr);
    if (!gl.getProgramParameter(pr, gl.LINK_STATUS)) return null;
    gl.useProgram(pr);
    gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer());
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
    const loc = gl.getAttribLocation(pr, "a");
    gl.enableVertexAttribArray(loc); gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
    const u = {};
    for (const n of ["uRes", "uTime", "uIntro", "uScroll", "uVariant", "uGlow", "uMouse"]) u[n] = gl.getUniformLocation(pr, n);
    return { gl, u };
  }

  function attach(canvas) {
    const ctx = make(canvas);
    if (!ctx) return false;
    const { gl, u } = ctx;
    const host = canvas.parentElement;
    const variant = canvas.dataset.variant === "cta" ? 1 : 0;
    const speed = variant ? 0.6 : 1;
    let W = 1, H = 1, visible = false, raf = 0, t0 = 0, introT0 = 0, lost = false;
    let mx = -9999, my = -9999, tx = -9999, ty = -9999, glow = 0, glowTarget = 0, lastMove = 0;
    canvas.dataset.gl = "1";
    canvas.closest("section")?.classList.add("gl-on");
    canvas.addEventListener("webglcontextlost", (e) => { e.preventDefault(); lost = true; cancelAnimationFrame(raf); raf = 0; });

    function size() {
      const r = host.getBoundingClientRect();
      W = Math.max(1, Math.ceil(r.width / CELL)); H = Math.max(1, Math.ceil(r.height / CELL));
      canvas.width = W; canvas.height = H;
      canvas.style.width = W * CELL + "px"; canvas.style.height = H * CELL + "px";
      canvas.style.right = "auto"; canvas.style.bottom = "auto";
      gl.viewport(0, 0, W, H);
      draw(performance.now());
    }

    function draw(now) {
      if (lost) return;
      if (!t0) t0 = now;
      const t = reduced ? 8 : 8 + ((now - t0) / 1000) * speed;
      const intro = reduced ? 1 : introT0 ? ease((now - introT0) / 1600) : 0;
      const r = host.getBoundingClientRect();
      const scroll = reduced ? 0 : Math.max(-0.3, Math.min(0.3, (-r.top / Math.max(1, r.height)) * 0.22));
      gl.uniform2f(u.uRes, W, H);
      gl.uniform1f(u.uTime, t % 1000);
      gl.uniform1f(u.uIntro, intro);
      gl.uniform1f(u.uScroll, scroll);
      gl.uniform1f(u.uVariant, variant);
      gl.uniform1f(u.uGlow, glow);
      gl.uniform2f(u.uMouse, mx, my);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
    }

    function loop(now) {
      raf = 0;
      if (!visible || document.hidden || lost) return;
      if (!introT0) introT0 = now;
      if (now - lastMove > 2500) glowTarget = 0;
      mx += (tx - mx) * 0.12; my += (ty - my) * 0.12;
      glow += (glowTarget - glow) * 0.06;
      draw(now);
      raf = requestAnimationFrame(loop);
    }
    const start = () => { if (!raf && !reduced && visible && !document.hidden && !lost) raf = requestAnimationFrame(loop); };

    if (!reduced) {
      addEventListener("pointermove", (e) => {
        const r = canvas.getBoundingClientRect();
        const inside = e.clientX >= r.left && e.clientX <= r.right && e.clientY >= r.top && e.clientY <= r.bottom;
        if (!inside || e.pointerType === "touch") { glowTarget = 0; return; }
        tx = (e.clientX - r.left) / CELL; ty = H - (e.clientY - r.top) / CELL;
        if (glow < 0.02) { mx = tx; my = ty; }
        glowTarget = variant ? 0.7 : 1; lastMove = performance.now();
      }, { passive: true });
      document.documentElement.addEventListener("pointerleave", () => { glowTarget = 0; });
    }
    new ResizeObserver(size).observe(host);
    new IntersectionObserver((es) => { visible = es[0].isIntersecting; start(); }).observe(host);
    document.addEventListener("visibilitychange", start);
    size();
    return true;
  }

  document.querySelectorAll("canvas.mosaic, canvas#mosaic").forEach((c) => { try { attach(c); } catch (e) { console.warn(e); } });
})();
