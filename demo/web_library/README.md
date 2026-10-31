# The Librarian — quiet frontend v1

An independent frontend variant. It does not replace the other demo frontends or modify the shared backend, retrieval harness or Reactor queue.

## Run

From any directory:

```sh
/Users/mikolaj/Developer/start-hackathon-2/librarian/demo/web_library/run.sh
```

Open http://127.0.0.1:8804/. Override the port with `PORT=8805 ./run.sh`.

Or from `librarian/`:

```sh
.venv/bin/python -m demo.server --web demo/web_library --port 8804
```

No npm install or build step. Local fonts and assets. Uses the existing server's `/replay.json`, `/api/status`, `/api/pack` and `/api/ask`.

## Experience

- A single still illustration with only subtle indicator-light blinking.
- One question and one primary action. Choose another recorded question through the archive link.
- Recorded questions replay real Reactor answers. Custom questions first run local evidence retrieval; a live answer is available after that only when Reactor is free.
- Sources appear on demand. Cited conversations are shown first, with other selected passages collapsed.
- “How it works” opens the five illustrated chapters. “The ledger” shows dev-only calibration and explains its limits.
- Cancelled operations cannot overwrite a newer state. Live conflicts and unavailable data return usable feedback.
- Keyboard focus, native dialog focus trapping, reduced-motion support and an indicator-light pause control.

## Files

`index.html`: semantic views and dialogs. `style.css`: layout and indicator masks. `app.js`: state, recorded replay, API actions and progressive disclosure. `data.js`: narrative copy and pure calibration metrics. `assets/`: runtime WebP. `fonts/`: local font files. `source-art/`: original new background and exact generation prompt.

This direction supersedes the earlier four-section raster-panel composition for this variant. The other frontend variants retain their own design.

## Validation

```sh
node --test demo/web_library/qa/metrics.test.mjs
uv run --with playwright python demo/web_library/qa/smoke.py
```

Run from `librarian/` with this frontend already serving on port 8804. The smoke checks mock every API write; they do not call Reactor. Browser screenshots and the result are in `qa/`.

Verified at 1440×900, 1920×1080 and 390×844. Three metric tests passed; browser smoke checks passed with no JavaScript errors or missing resources. Includes recorded abstention, evidence dialogs, cancellation, retrieval failures, Reactor conflict, reduced motion and load failure. Real retrieval/answer generation was not exercised, to avoid interfering with the benchmark queue.

## Artwork

The new background was generated using built-in imagegen with `design/raw/B00.png` as style reference. The five comic frames and emblem use the existing project assets. No OpenAI API credits were spent on video or animation generation.
