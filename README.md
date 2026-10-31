# Librarian

Memory for AI assistants that knows what it doesn't know. Built in one night for the **Reactive AI Memory Retrieval
Challenge** (START Warsaw x Poland Tech Week Hackathon, Oct 30–31, 2026).

A user talks to an assistant for months (200 sessions, ~1.6M characters). Then a question arrives: *"What is my dog's
name?"*. Librarian finds the few sessions that matter and hands them to Reactor as a compact evidence pack. Reactor is
the organisers' model and the only allowed answerer. Librarian then turns Reactor's reply into a cited prediction, or
into an honest abstention when the history does not contain the answer. Per question, Reactor reads about 0.1–0.4% of
the archive.

```
question ─► router (5 types) ─► type lens ─► evidence pack ─► Reactor ─► finalize ─► predictions.jsonl
            + evidence hand-offs  BM25 + dense      ~3 dated sessions  answer     code-chosen
                                  + rerank, dates,  (1–9) + code notes + [E#]     supporting
                                  timelines, tallies (e.g. day gaps)              citations
```

| Offline score S | dev (526 q) | dev200 (test scale) |
|---|---|---|
| organisers' naive keyword baseline (our reimplementation, no router) | 42.9 | |
| generic hybrid retrieval (80-question dev sample, no router) | 73.4 | |
| routed v1 | 86.0 | 84.9 |
| routed v3 (submitted) | **87.1** | **87.0** |

`S = 100 · mean(0.65·PA + 0.30·CF1 − 0.05·chars/16000)`:
- **PA** means the pack lets a reader answer;
- **CF1** is citation F1;
- **chars** is the pack length.

The harness measures S offline against gold, in minutes and without calling Reactor. Per gold type, routed v3 on dev
scores ssu 87.4, ssa 93.0, multi 85.8, ku 91.5 and temporal 80.3. Each route's lens alone, on questions of its own type,
scores 93.4, 93.6, 87.8, 93.4 and 81.3; the difference is router error.

Test submission (`submission/predictions.jsonl`):
- 146/146 questions answered by Reactor;
- 13 abstentions;
- every answer has at least one citation;
- 0 format errors (`score.validate`).

**Standalone filter, open source (MIT): [brsword21/librarian-recall](https://github.com/brsword21/librarian-recall).**
**How it works and how we got here: [SOLUTION.md](SOLUTION.md).** Team onboarding: [ONBOARDING.md](ONBOARDING.md) (Polish). Lens contract: [CONTRACT.md](CONTRACT.md). Research notes:
[RESEARCH.md](RESEARCH.md). Reports from the agent rounds: `runs/SYNTHESIS_r*.md`.

## Quick demo (no data, no dependencies)
```sh
python3 -m demo.server --web demo/web --port 8800    # then open http://127.0.0.1:8800
```
It replays the recorded Reactor answers from `demo/replay.json`. Keys: Space starts the tour, ←/→ step through it,
F toggles fullscreen.

**Your own archive:** open http://127.0.0.1:8800/live, drop a file (challenge history, ChatGPT `conversations.json`,
WhatsApp `.txt` export, or Markdown notes with date headings; try `demo/samples/founder_notes.md`) and ask. This needs
`core.model_server` running; "Ask Reactor" also needs Reactor access (see Reproduce). API: `POST /api/upload`, then
`POST /api/pack` or `/api/ask` with `{"split": "upload", "history_id", "question"}` (see `demo/server.py`).

**Memory inbox:** http://127.0.0.1:8800/inbox shows the archive as an inbox and runs the whole workflow step by step:
route, search (sessions picked, share of the archive read), code notes, Reactor, output. The sessions Librarian picked
and those Reactor cited are highlighted. Every live answer is logged to `cache/live_outputs.jsonl` and downloadable as
JSON or JSONL.

## Reproduce
Requirements: macOS or Linux, [uv](https://docs.astral.sh/uv/), git, curl.

Workspace layout: `<ws>/librarian` (this repo), `<ws>/memory-challenge` (the organisers' kit, imported at runtime, not
copied) and `<ws>/data`.
```sh
mkdir ws && cd ws && git clone https://github.com/brsword21/librarian.git
sh librarian/tools/setup.sh          # kit @ f0a317d, data-v1 (dev, test), LongMemEval oracle, venv, sharded histories
cd librarian
.venv/bin/python -m core.model_server &    # local bge-small-en-v1.5 + ms-marco-MiniLM-L-6-v2 on 127.0.0.1:8765

# offline evaluation of the full routed system
.venv/bin/python -m harness.sweep --lens lenses/pipeline.py --variants routed --split dev --tag check

# test packs -> Reactor -> predictions
SUFFIX="Write the final answer line as: only the answer itself (a name, number, date or short phrase), followed by the [E#] label(s) of the passage(s) that state it. No explanation, no alternatives."
.venv/bin/python -m reactorq.build_packs --config configs/best.json --split test --suffix "$SUFFIX" \
    --out runs/final/x_packs.jsonl                      # add --qids q_...,q_... for a few questions
# Reactor access: copy tools/reactor.env.example to ../reactor.env and tools/reactor.sh to ../reactor.sh, create
# ../.venv with websockets>=14, and put the access key in the macOS keychain (see tools/reactor.sh). Then:
.venv/bin/python -m reactorq.queue --packs runs/final/x_packs.jsonl --out runs/final/x_results.jsonl --timeout 600
.venv/bin/python -m reactorq.finalize --results runs/final/x_results.jsonl --packs runs/final/x_packs.jsonl \
    --split test --out submission/predictions.jsonl
```
The submitted file is rebuilt byte for byte from the recorded Reactor answers:
```sh
.venv/bin/python -m reactorq.finalize --results runs/final/v1_results.jsonl runs/final/v3_reask_results.jsonl \
    runs/final/v3_err_reask_results.jsonl \
    --packs runs/final/v3_test_packs.jsonl runs/final/v2_test_packs.jsonl runs/final/v1_test_packs.jsonl \
    --split test --out submission/predictions.jsonl
```

## Rules we follow
- Every answer comes from Reactor. No hosted LLM is used anywhere; local models run only through `core/model_server.py`.
- Answers are never edited. `reactorq/finalize.py` adds a citation only when the cited session contains Reactor's
  answer or holds the value our code computed and Reactor repeated. The docstring lists every rule.
- The organisers' kit is imported, not vendored.

## Data and licences
- **Code and docs:** our code and documents are MIT ([LICENSE](LICENSE)).
- **Dev excerpts:** from LongMemEval (Wu et al., 2024, MIT, https://github.com/xiaowu0162/LongMemEval).
- **Test excerpts:** those in `runs/final/*packs*.jsonl` and `demo/replay.json` come from the organisers' public
  `data-v1` release (https://github.com/RxAI-dev/memory-challenge). They are included only to reproduce the submission
  and the demo.
- **Fonts:** the fonts in `demo/*/fonts` are SIL OFL 1.1 (see `OFL.txt` there).
