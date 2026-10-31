# Librarian: rules for Claude Code sessions in this repo

Hackathon project (Reactive AI Memory Retrieval Challenge). Read ONBOARDING.md first; docs/NIGHT_LOG.md has the full
event context. Team language: Polish.

## Hard rules (breaking them disqualifies the team or leaks a secret)
- Never call Reactor (reactor.sh, reactorq.queue, demo /api/ask) unless the user explicitly says so in this session:
  there is one shared, slow Reactor and one process at a time may talk to it.
- No external model APIs anywhere in the pipeline (Claude, OpenAI, any hosted LLM). Local models only, and only through
  core/model_server.py (bge-small-en-v1.5, ms-marco-MiniLM-L-6-v2). The final answer always comes from Reactor.
- Never edit predictions or Reactor answers by hand. Citations may only be chosen by code, and every added session must
  support Reactor's answer (reactorq/finalize.py documents the allowed rules).
- Never write, print or commit the Reactor key (rxk_...). It lives in the macOS keychain only.
- Simulator (proxy) output never goes into submission/: finalize refuses it; keep it that way.
- Do not copy code from ../memory-challenge (upstream has no LICENSE): import it (core/paths.py puts it on sys.path).

## Working conventions
- Python: .venv/bin/python, run from librarian/ (python -m harness.sweep ..., python -m reactorq.build_packs ...).
- One model_server (:8765) is shared: never stop it, never import torch elsewhere; use core.models / HistoryIndex.
- Measure through the harness only (harness.sweep -> runs/leaderboard.csv), at most 2 worker processes.
- Accept a variant only with >= +2 S on dev and no loss on dev200; on a tie the shorter pack wins.
- Test questions have no gold: use harness.audit for qualitative checks, never tune to a single test question.
- Any change to test packs means re-asking Reactor (~105 s per question): diff packs first (.venv/bin/python -m harness.audit --diff OLD.jsonl NEW.jsonl).
- Edit only files your task owns; core/ and configs/best.json changes need a heads-up to the team.
