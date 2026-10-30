# Librarian: contract for lens agents

Goal: for each question type, find the evidence-selection approach ("lens") that best lets Reactor (the organisers' LLM) answer correctly, cite the right sessions and abstain when the history lacks the answer. Read `../CONTEXT.md` (challenge, rules, data stats) and `RESEARCH.md` (what published systems do) first.

## Hard rules (breaking any of these can disqualify the team or kill the machine)
1. Never call Reactor (`reactor.sh`, `client.py`) and never call any external LLM / embedding / search API from code. Local only. (Web research with your own tools is fine.)
2. Edit only your own files: `lenses/<type>/<a|b>_*.py` and `lenses/<type>/<a|b>_*.md`. Need a core change? Write it in your report ("CORE REQUEST"); the integrator owns `core/` and `harness/`. You may copy a core helper into your lens file and modify it there.
3. Run evaluations only through `harness.sweep` with `--workers 2` or fewer. Models (embedder, reranker) are served by one shared process (`core.model_server`, already running) — never load torch / sentence-transformers yourself.
4. Test split = qualitative audit only (`harness.audit`); never tune on individual test questions, never hand-write answers.
5. Python: `.venv/bin/python` inside `librarian/`. Run commands from `librarian/`.

## Data
- Splits: `dev` (526 q, ~48 sessions/history, gold), `dev200` (125 q from dev-large cut to 200 sessions/history = test scale, gold), `test` (146 q, 200 sessions/history, no gold). Gold types: single-session-user (ssu), single-session-assistant (ssa), multi-session (multi), knowledge-update (ku), temporal-reasoning (temporal); `abstain: true` = unanswerable.
- `runs/samples/<type>.jsonl`: ~25 dev questions per type with gold answer, evidence sessions and the gold turns' text, plus ~15 test questions of that style. Start there.
- Turn-level gold: `core.gold_turns.gold_turns()[question_id]` -> list of turn_ids that contain the answer (dev/dev200).

## API (`core/`)
```python
from core.types import Question, Unit, Passage, EvidencePack, SHORT, LONG
from core.index import HistoryIndex
hx = HistoryIndex.load(split, history_id)        # cached per process
hx.units            # list[Unit], chronological; Unit = sentence-aligned chunk (<= ~700 chars) of one turn
                    # fields: uid, session_id, sess_idx, date (datetime), date_str, turn_id, turn_idx, role, chunk_idx, text, ctx
hx.sessions         # list[dict]: session_id, date (datetime), date_str, sess_idx, turns [{turn_id, role, content}]
hx.sess_by_id[sid]  # same dict
hx.turn_units(turn_id) -> list[int]
hx.neighbors(uid, before=1, after=1) -> list[int]          # same session only
hx.bm25(query, k=200, roles=None) -> list[(uid, score)]    # bm25s, English stemming + stopwords
hx.dense(query, k=200, roles=None, uids=None) -> list[(uid, score)]   # bge-small cosine; uids restricts the pool
hx.hybrid(query, k=100, roles=None, w_bm25=1.0, w_dense=1.0, rrf_k=60, pool=300) -> list[(uid, score)]  # RRF
hx.rerank(query, uids) -> list[(uid, score)]               # cross-encoder ms-marco-MiniLM-L-6-v2, cached

from core.pack import build_pack, message_chars
passages, included_turns, chars = build_pack(q, hx, ranked_uids, budget=12000, window=1, order="chrono",
                                             hint="", max_sessions=None, whole_turns=False)
# groups units by session, adds +/-window neighbours, renders "user: ..."/"assistant: ...", one Passage per
# session (id=session_id, date=session date string), stops at `budget` characters of the FULL Reactor message.

from core.dates import extract_dates, days_between       # basic: ISO, "June 27, 2023", "23 April 2023", relative weekdays
from core.router import route                            # route(question_text) -> (short_type, confidence)

# added after round 1 (backward compatible)
message_chars(q, passages, hint="") -> int                 # exact length of the Reactor message (question + hint + passages)
build_pack(..., pinned=[uid, ...], max_chars_per_session=N) # pinned units enter first (no neighbours); per-session cap
# build_pack walks `ranked` in priority order: a unit that does not fit is skipped, later ones may still enter.
# window=0 plus explicit neighbour uids in `ranked` is the supported way to hand-pick context.
HistoryIndex.rerank_texts(query, texts) -> list[float]     # cross-encoder on arbitrary strings (sentences), same cache
HistoryIndex.dense_texts(query, texts) -> list[float]      # bge cosine on arbitrary strings, cached embeddings
```

### Citations (read this)
The submitted citations are whatever Reactor cites among the passages we send ([E#] -> session id). Whether our code may
post-filter Reactor's citations with `cite_plan` is NOT confirmed by the organisers. CF1 is measured on `cite_plan` (our
intent) and is optimistic when the pack carries decoy or context sessions. Every sweep now also prints
`CF1all` / `Sall`: the same metrics if Reactor cites every passage we send (pessimistic bound, saved in summary.json and
per_question.jsonl). Prefer packs whose sessions are close to the cite set; extra context sessions must earn their place.
After round 1, routed dev: CF1 0.879 on cite_plan against 0.687 if every passage is cited (-5.8 S). Most of the loss
is in multi (0.87 -> 0.44), temporal (0.83 -> 0.65) and ku (0.96 -> 0.64).

### Harness additions after round 1
- per_question.jsonl rows carry `included_turns`; `harness.failures` marks each gold turn IN / MISS.
- `harness.audit` saves `route`, `cite_plan` and `debug` per test pack in test_packs.jsonl.
- `configs/best.json` holds the current winner per route (the routed system is `lenses/pipeline.py`);
  `configs/abstain.json` holds the abstention policy (no abstention hint to Reactor yet).

## Lens file contract
```python
# lenses/<type>/<a|b>_<name>.py
from core.types import EvidencePack
VARIANTS = {"base": {"k": 8}, "wide": {"k": 15}}        # name -> kwargs for build()
def build(q, hx, **params) -> EvidencePack:
    ...
    return EvidencePack(question_id=q.question_id, variant=params.get("_variant", ""), route="<type>",
                        passages=passages, hint=hint, cite_plan=None, abstain_p=p,
                        included_turns=included_turns, computed=None, debug={"ranking": [uid, ...]})
```
- `hint`: text appended to the question sent to Reactor (computed day differences, "the most recent value wins", "term X never appears in the history", "list every instance with its session, then count"). Keep it short and factual.
- `computed`: the answer your code computed, if any (days, a count, a value) — scored as hint accuracy.
- `abstain_p`: your probability that the history does not contain the answer (0..1).
- `debug["ranking"]`: your full ranked uid list (enables "where did the gold turn rank" diagnostics).

## Evaluate
```sh
.venv/bin/python -m harness.sweep --lens lenses/temporal/a_calendar.py --variants all --split dev --type temporal --tag r1 --workers 2
.venv/bin/python -m harness.sweep ... --split dev200          # robustness at test scale
.venv/bin/python -m harness.failures runs/r1/temporal/a_calendar/<variant>/dev --n 20
.venv/bin/python -m harness.audit --lens lenses/temporal/a_calendar.py --variant <v> --type temporal   # test packs + flags, no gold
```
Outputs: `runs/<tag>/<type>/<lens>/<variant>/<split>/{per_question.jsonl, summary.json}`, one row per run appended to `runs/leaderboard.csv`.

## Metrics (answerable questions; G = gold sessions, P = sessions in pack, A = gold turns)
- SR = |P∩G|/|G|; ALL = 1 if G ⊆ P; ATR = |A ∩ included_turns|/|A|; AC = gold answer string found in pack text (score.py matcher); HA = computed == gold number (or gold+1 for day counts); CF1 = evidence F1 of cite_plan vs G; chars = full message length; ms = build time.
- PA (pack can answer): ssu/ssa: ATR==1 and AC (AC only where the gold answer is extractive; otherwise ATR); ku: AC/ATR and the newest gold session in P; multi: ALL and ATR==1; temporal: ALL and (HA if computed else ATR==1).
- **S = 100 * mean(0.65*PA + 0.30*CF1 - 0.05*chars/16000)**. Abstention: AUC of abstain_p (reported separately).
- Accept a new variant only if it beats your best by >= 2 points of S on dev AND does not lose on dev200; on a tie prefer fewer chars / simpler code.

## Report (your final message, also saved as `lenses/<type>/<a|b>_report.md`)
Variants tried (one line each: idea + params), table of S / PA / ATR / SR / CF1 / chars on dev and dev200, best variant, top failure patterns with 2-3 concrete examples, CORE REQUESTs, ideas for next round.
