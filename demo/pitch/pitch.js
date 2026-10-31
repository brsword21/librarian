// Pitch deck: scale the 1920x1080 stage to fit, ←/→/Space/click to move, N notes, F fullscreen, #n deep link,
// ?print stacks every slide for PDF.
(function () {
  "use strict";
  const stage = document.getElementById("stage");
  const slides = [...document.querySelectorAll(".slide")];
  const count = document.getElementById("count");
  const panel = document.getElementById("notesPanel");
  const print = /[?&]print\b/.test(location.search);
  let i = 0;

  if (print) {
    document.body.classList.add("print");
    return;
  }

  function fit() {
    const s = Math.min(innerWidth / 1920, innerHeight / 1080);
    stage.style.transform = `translate(-50%, -50%) scale(${s})`;
  }

  function show(n) {
    i = Math.max(0, Math.min(slides.length - 1, n));
    slides.forEach((el, k) => el.classList.toggle("on", k === i));
    count.textContent = `${i + 1} / ${slides.length}`;
    const note = slides[i].querySelector(".notes");
    panel.textContent = note ? note.textContent.trim() : "";
    if (location.hash !== `#${i + 1}`) history.replaceState(null, "", `#${i + 1}`);
  }

  addEventListener("keydown", (e) => {
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    const k = e.key;
    if (k === "ArrowRight" || k === "PageDown" || k === " ") { e.preventDefault(); show(i + 1); }
    else if (k === "ArrowLeft" || k === "PageUp") { e.preventDefault(); show(i - 1); }
    else if (k === "Home") show(0);
    else if (k === "End") show(slides.length - 1);
    else if (k === "n" || k === "N") panel.hidden = !panel.hidden;
    else if (k === "f" || k === "F") {
      if (document.fullscreenElement) document.exitFullscreen();
      else document.documentElement.requestFullscreen?.().catch(() => {});
    }
  });
  document.getElementById("viewport").addEventListener("click", (e) => {
    if (e.target.closest("a, button, pre") || getSelection().toString()) return;
    show(e.clientX < innerWidth * 0.25 ? i - 1 : i + 1);
  });
  addEventListener("resize", fit);
  addEventListener("hashchange", () => show((parseInt(location.hash.slice(1), 10) || 1) - 1));

  fit();
  show((parseInt(location.hash.slice(1), 10) || 1) - 1);
})();
