# Lens B ("Semantyka") for multi-session: design (Round 0)

Code: `lenses/multi/b_sweep.py` (6 variants; run `.venv/bin/python -m lenses.multi.b_sweep` for the pure-python self-test).
Scratch: `lenses/multi/scratch_b/` (`analyze.py` = dev stats, `grep_hist.py` = qualitative grep, `smoke.py` = build() on a few dev questions).

## 1. What makes multi hard (data findings)

**Dev (LongMemEval) — `scratch_b/analyze.py`**
- 133 q, 12 unanswerable. Gold sessions: 2 → 75, 3 → 24, 4 → 16, 5 → 6.
- Gold turns are **user turns** in 322/323 cases; **turn_idx 0 in 68%** (the opening request with a "By the way, I …" fact sentence).
- One gold turn per gold session in 91% (288/315); 17 sessions have 2–3 gold turns (ATR needs all of them); 11 gold sessions have none flagged (only ALL/SR count them).
- Lexical difficulty: TF-IDF over user turns, gold-turn recall@10 = 72% (dev, ~48 sessions) → 56% (dev200, 200 sessions); @50 = 90% / 89%. So the facts are findable, but at 200 sessions they sit in ranks 10–50. You need a wide candidate pool plus a reranker and per-session diversity.
- **Dev session dates span a median of 10 days** (LongMemEval puts evidence near the question date). Windows like "in February" or "past two weeks" therefore cannot be filtered by session date on dev. Event dates are in the text ("on 2/15").
- Failure seen in the smoke run: later user turns of the same session talk about the topic at more length and outrank the turn-0 fact sentence. A per-session cap then drops the gold turn (ATR 0/2 with SR 3/3). This is fixed by the **fact prior** (§2).
- 32/133 (24%) dev multi questions are "named-facet" sums ("total cost of the car cover and detailing spray", "MCU movies and the main Star Wars films"). Each facet sits in a different session, so the lens issues one query per facet and guarantees each facet's top hit a place in the pack.
- Repeated mentions are common (bike lights $40 stated in 3 sessions, gold $185 = 25 + 40 + 120). The hint must say "count once".

**Test (qualitative, `grep_hist.py`; no tuning on single questions)**
- Test session dates span 174–179 days, so **time windows ("since March", "in August", "last month", "this summer") are real filters on test.**
- Facts are **one short sentence mid-session** (user turns t2–t6), typically after "By the way / Also / On another note". The same topic recurs in 20–60 turns of a history.
- Near-miss decoys are built in:
  - other people's facts ("My friend X bought …", "Y told me he …", "My sister opened a … fund with …")
  - declined or hypothetical actions ("tried on … but decided not to buy", "skipped buying")
  - assistant-injected third-party facts ("By the way: your neighbour told me he added four …")
  - date edges: "yesterday's reading" in a Sept 2 session is Sept 1, outside "in August"
- Real facts sometimes appear only as an **assistant recap** ("You mentioned that the three … you ordered arrived safely").
- Ordinal cues ("another pair", "a third pair") mark distinct instances.
- At least one count-style test question appears to have only other-person mentions, so it is likely unanswerable. The "all hits are other-person" abstention signal exists for this case.
- Many test "multi-style" questions are really KU-like ("these days", "right now", "current"), so the hint adds "the most recent statement wins".

Parser coverage on dev multi: windows found in 28/133, facets in 32/133; kind = count 64, sum 36, other 17, diff 13, avg 3.

## 2. Variants (ranked by expected value on TEST)

All variants share **question analysis** (`analyze()`, pure python):
- `window`: a rule-based date range from the question date. It covers: since <Month> / since the start of <Month|year>, in <Month> / the month of <Month> (most recent past occurrence), this|last <season>, last month, this month, last week (Mon–Sun), past N|few days/weeks/months, this year, last year. 8 assertions in the self-test.
- `core`: the question minus scaffolding, the window phrase and filler ("in total", "each morning", "these days").
- `statements`: LLM-free declarative rewrites in the user's voice ("How many orchids have I added …" → "I added … orchids").
- `facets`: coordinated noun phrases. Verb-only conjuncts ("worked on or bought") are rejected.
- `kind` (count/sum/diff/avg/other), `latest` (now/currently/these days), `others_ok` (the question itself is about friends, family or people).

### V1 `sweep` (default; expected best on test)
1. **Candidates:** RRF over `hx.hybrid(query, k=150, w_bm25=1, w_dense=1, rrf_k=60, pool=300)` for the question (w=1.0), the core (0.8) and 2 statements (0.6). Each facet adds `hx.hybrid(facet, k=40, roles="user")` (0.7).
2. **Role filter:** user units; assistant units only if they are short recaps (`you mentioned|you said|you told me|as you noted…`), ×0.7.
3. **Rerank:** `hx.rerank(question, top 90 + each facet's top 6)`. Final = 1/(60+rank_CE) + 0.5/(60+rank_fused), multiplied by these priors:
   - **fact prior ×1.3** (user unit stating a first-person past event, a quantity, a date or "by the way")
   - **window prior**, only when the history spans ≥ 45 days (so off on dev): in window 1.0, ≤ 10 days after the window 0.8, later 0.5, before the start 0.3
   - **agent prior**, only when not `others_ok`: other-person ×0.6, declined/planned ×0.85
4. **Selection:** session-first diversity. Pass 1 takes each facet's top 2 units, then the best unit of every session (max 22 sessions). Pass 2 adds depth up to 4 units per session.
5. **Rendering (own renderer):** each unit is **sentence-trimmed to ≤ 320 chars** around its question-term sentences, plus one sentence of context. Short user replies get the previous assistant question (`Unit.ctx`). Passages are chronological, one per session, with the date. The budget is measured with `core.pack.message_chars`; `budget=12000`.
6. **cite_plan:** sessions whose best unit's CE logit ≥ top − 3.0 (relative, because CE logits for count questions are about −3 to −8 even on gold), excluding other-person hits. Each facet's confident top session is always cited. Range 2 to 6 sessions.
7. **abstain_p** = 0.03 + 0.55·(fraction of rare question terms absent from the whole history) + 0.30·σ(−(top_CE + 7)/1.5) + 0.35·[top term-bearing hits are all other-person].
8. **Hint**, assembled per question. The tango-shoes example below shows the first three sentences; the window and latest sentences are added only when they apply:

   > These facts are spread over several sessions. First list every matching instance as 'date | [E#] | item | number', then compute the answer from that list. Count a thing once even if it is mentioned again in a later session (same item, same event). Only count what I (the user) did or have; ignore what friends, family or others did, and ignore things I only planned, considered, tried or decided against. Time window 'since March': 2023-03-01 to 2023-09-04 (today is 2023-09-04). Resolve 'yesterday'/'last week' against each excerpt's date; drop instances outside the window. If the number changed over time, use the most recent statement.

   - The "only count what I did" sentence is dropped when the question is about others (babies born to friends).
   - The window sentence appears only with a window; the latest sentence only for now/currently/these days.
   - "Answer INSUFFICIENT_EVIDENCE if no excerpt states a matching instance" is added only when abstain_p ≥ 0.6.
- **Should move:** ALL and ATR (many sessions per char: ~22 sessions and ~40 snippets in 12k), CF1 (relative cite_plan), test accuracy (decoy-aware hint, window).
- **Failure modes:** sentence trimming cuts a needed pronoun antecedent; pass 2 depth goes to topical chatter instead of the fact; the fact prior misses facts phrased without a cue ("Just thirty laps."), which the `ctx` prefix partly covers; facet extraction is wrong on odd syntax; the window prior hurts when the session date ≠ the event date by more than 10 days; the relative cite threshold over-cites on flat score distributions.

### V2 `sweep_wide` (recall first)
Same, with budget 14500, 30 sessions, rerank 120, pool 200. Expected **+ALL on dev200 and test (200 sessions)** at about −0.8 S from chars. Pick it over `sweep` only if dev200 ALL gains ≥ 3 points.

### V3 `sweep_tight` (precision / chars)
Budget 8000, 12 sessions, 2 per session, trim 260, cite_delta 2.0, cite_max 5. Fallback if Reactor accuracy drops with long packs (RESEARCH: small readers degrade with context). Should win on chars and CF1 and lose on ALL.

### V4 `sessagg` (Emergence-style baseline)
Same candidates, rerank and agent filter, then **session score = Σ_{j<3} σ(CE_j)/log2(j+2)** (NDCG of its unit hits). Top 10 sessions, top 2 units each, rendered by `core.pack.build_pack(window=1, order="chrono")`, cite = sessions ≥ 0.35·best (min 2, max 5). Fewer, richer sessions. It loses ALL when gold is 4–5 sessions (smoke: PA 2/6 vs 5/6 for `sweep`), so it is kept as the reference point.

### Ablations (in VARIANTS)
- `sweep_noprior`: no fact, window or agent prior. Measures how much the priors are worth on dev; the window prior is off on dev anyway.
- `sweep_user`: no assistant recaps. On dev this should be ≥ `sweep`, since gold is 99.7% user. Keep recaps for test unless dev200 shows a loss.

### Not implemented yet (Round 2 candidates)
- **V5 enumeration note:** a code-side candidate table as a `Passage(id=None)` note ("date | session | first-person sentence with a number"), filtered by window, agent and negation, plus `computed` when every candidate is the same unit and currency and the question is a plain total. The risk is anchoring Reactor on a wrong list. Only after V1 is measured with Reactor.
- **Sentence-level rerank:** rerank the trimmed sentence instead of the 700-char unit (`core.models.rerank(query, texts)`), which is cleaner for test-style one-sentence facts.
- **Ordinal and dedupe hints:** detect "another/a second/a third <item>" and repeated identical amounts across sessions, then add "the $40 lights are mentioned in 3 sessions = 1 purchase".

## 3. Smoke run (not an eval; 7 dev questions, ms after the embedding cache warms)

| q | sweep ALL/ATR/CF1 | sessagg ALL/ATR/CF1 |
|---|---|---|
| bike total $185 (4 sess) | 1 / 4/4 / 1.00 | 1 / 3/4 / 0.86 |
| museums Feb (3) | 1 / 2/2 / 1.00 | 1 / 0/2 / 0.80 |
| doctors (3) | 1 / 5/5 / 0.75 | 1 / 4/5 / 0.40 |
| babies (4) | 1 / 4/4 / 0.67 | 1 / 4/4 / 0.67 |
| furniture (4) | 1 / 5/5 / 0.67 | 0 / 4/5 / 0.67 |
| baking (4) | 1 / 3/4 / 0.80 | 0 / 1/4 / 0.67 |
| egg tarts (unanswerable) | abstain_p 0.28 vs 0.06–0.21 answerable | same |

Chars about 11.9k. Build time is about 100 ms per question once a history's embeddings are cached; the first build on a history takes 15–22 s.

## 4. CORE REQUESTs
1. **Final citations for multi should come from `cite_plan`** (or cite_plan ∩ Reactor's [E#]). The pack deliberately holds ~22 sessions for recall while gold has 2–5. If the submission uses every passage or whatever Reactor cites, CF1 collapses.
2. Optional: `hx.rerank_texts(query, texts)` or sentence-level units for multi/ssu, to rerank and render single sentences.
3. Optional: `harness.failures` should print the rank of every gold turn and the session it lost to, using `debug["ranking"]`.
