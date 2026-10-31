# Librarian

Memory for AI assistants that knows what it doesn't know. Built in one night for the **Reactive AI Memory Retrieval
Challenge** (START Warsaw x Poland Tech Week Hackathon, Oct 30–31, 2026).

A user talks to an assistant for months (200 sessions, ~1.6M characters). A question arrives: *"What is my dog's
name?"*. Librarian finds the few passages that matter, hands them to Reactor (the organisers' model, the only allowed
answerer) as a compact evidence pack, and turns Reactor's reply into a cited prediction, or an honest abstention when
the history does not contain the answer. Reactor reads about 0.1–0.4% of the archive per question.

```
question ─► router (5 types) ─► type lens ─► evidence pack ─► Reactor ─► finalize ─► predictions.jsonl
            + evidence hand-offs  BM25 + dense      5–8 dated         answer     code-chosen
                                  + rerank, dates,  passages + code   + [E#]     supporting
                                  timelines, tallies notes (day gaps)            citations
```

| Offline score S (routed system) | dev | dev200 (test scale) |
|---|---|---|
| organisers' naive baseline | 42.9 | |
| generic hybrid retrieval | 73.4 | |
| v1 | 86.0 | 84.9 |
| v3 (submitted) | **87.1** | **87.0** |

`S = 100 · mean(0.65·PA + 0.30·CF1 − 0.05·chars/16000)`. PA means the pack lets a reader answer; CF1 is citation
F1. The harness measures it offline against gold, in minutes and without Reactor. Per type, v3 on dev scores ssu 93.4,
ssa 93.6, multi 87.8, ku 93.4 and temporal 81.3.

**Team onboarding:** [ONBOARDING.md](ONBOARDING.md) (Polish). Lens contract: [CONTRACT.md](CONTRACT.md).
Research notes: [RESEARCH.md](RESEARCH.md). Agent round reports: `runs/SYNTHESIS_r*.md`.

Quick demo (no data needed): `python3 -m demo.server --web demo/web --port 8800`, then open http://127.0.0.1:8800.
