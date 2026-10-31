# The Librarian — styled presentation demo

The existing full-information demo, now using the illustrated monastery / retro-electronics visual style. Served at http://127.0.0.1:8800/.

From `librarian/`:

```sh
.venv/bin/python -m demo.server --web demo/web --port 8800
```

## What changed

- `library.css` adds the visual treatment after the original `style.css`: walnut/brass colors, local fonts, readable evidence and notes, illustrated books and Reactor, responsive fallback.
- `assets/` contains copies of the existing project WebP assets. `fonts/` contains local font files; Google Fonts is not needed at runtime.
- `index.html` integrates those assets and adds the scrollable method section below the full demo.
- `presentation.js` drives the five illustrated method chapters, keyboard tab navigation, librarian poses, modal focus containment and tour pause when scrolling away.
- `app.js` retains the original evidence selection display, recorded answers, candidate checks, citation mapping, guided tour and live endpoints. Edits cover visual helpers, terminology, method navigation, keyboard accessibility and reduced motion. The decorative particle loop is no longer started.

The separate frontend on port 8804 is unchanged. Before-edit copies of the original port-8800 files are only on Mikołaj's machine (not in git); `demo/web_arcane` is the pre-restyle winner.

## Presentation

The first viewport retains the full workflow: question, history shelves, selected pages, local context/checks and Reactor answer. “How it works” scrolls to the explanation. The illustrated walkthrough has five steps, followed by the five lens types and abstention. Return links lead back to the demo.

Existing shortcuts remain active within the demo. They yield to normal scrolling and chapter controls in the method section. Reduced-motion disables ambient blinking and shortens replay timing.

## Validation

With the demo running on port 8800, from `librarian/`:

```sh
uv run --with playwright python demo/web/qa/smoke.py
```

Passed: all five question types, recorded abstention, rejected computed candidate, evidence view and focus return, chooser and tour controls, scrolling, illustrated chapters and tab keyboard navigation, 1440×900, 1920×1080, mobile overflow fallback and reduced motion. Answer text is compared directly to the recorded data. API writes are intercepted during smoke checks; no real Reactor requests are made.

Evidence type: 18 px on laptop, 22 px on projector; expanded transcripts use 22 px. Screenshots and machine-readable results are in `qa/`.
