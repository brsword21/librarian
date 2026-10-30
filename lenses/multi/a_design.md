# Lens A "Struktura" for multi-session: design (round 0)

Lens file: `lenses/multi/a_tally.py` (runs now with the BM25-only variant; the hybrid variants need `core.model_server`).
Scratch: `lenses/multi/scratch_a/` (`eval_local.py` approximates the harness metrics until `harness.sweep` lands).

## What makes multi hard (data findings)

**Dev (LongMemEval style), 121 answerable / 12 unanswerable.**
- Gold turns are user turns (322 of 323). 69% are the first user turn of the session. Median length is about 300 chars. Gold sessions usually hold 1 gold turn (288 of 316).
- Session dates are useless for time windows. A dev history spans 0 to 10 days, so "in March" or "past few months" refers to dates written in the text, not session dates. **A session-date filter must only engage when the history spans well beyond the window.** That holds on test (6-month histories) and not on dev.
- Raw-question BM25 over user units already finds the sessions: ALL@10 sessions 0.81, ALL@20 0.90 (dev200: 0.59 and 0.86). The naive 31% comes from packing whole sessions. **Coverage is a packing problem, not a retrieval problem**: pack small pieces of many sessions.
- The second loss is inside the session. The gold session is in, but its long on-topic chit-chat turns outrank the "By the way, I …" turn. In gold sessions, gold turns compared with other user turns show:
  - "by the way / oh, and / also," in 55% vs 15%
  - a first-person fact verb ("I just got / bought / attended …") in 73% vs 23%
  - a number in 69% vs 23%
  - a date word in 38% vs 9%
  - first user turn in 69% vs 6%
  
  Dev200 shows the same.
- Category-to-instance vocabulary gaps cause most of the remaining misses:
  - doctors: dermatologist, ENT, Dr. Patel
  - furniture: coffee table, mattress
  - baked: chocolate cake
  - health devices: hearing aids, Fitbit
  - food delivery: Uber Eats
  - instruments: Korg B1, drum set
  
  This is the dense or reranker channel's job. A small generic LEXICON (category to instance words) helps BM25.
- Unanswerable multi questions usually have one part missing: "Hawaii and **Seattle**", "tomatoes and **chili peppers**", "headphones and **the iPad**", "**30-gallon** tank". Checking whether a salient term or a conjunct is absent catches about 4 of 12 with 0 of 121 false alarms at p ≥ 0.5 (AUC 0.62). It stays a soft signal.

**Test (new data, qualitative only, no tuning on single questions).**
- Each fact is one inserted sentence inside an unrelated user turn: "By the way, I bought a pair of tango shoes from a shop in San Telmo for 1,800 pesos." Test user turns are short (median about 170 chars). There are 200 sessions over about 6 months, so session-date windows carry real information.
- Deliberate near-misses sit next to every true instance:
  - **other person**: "My friend Valentina bought a pair of tango shoes for 1,800 pesos", "Carlos told me he has read three books *since March*" (the question's exact phrase), "My sister has 9 Icelandic horses"
  - **negation or non-event**: "tried on … but decided not to buy", "skipped buying", "test batch, didn't use it for any order"
  - **different account or purpose**: "moved 7,500 pesos into my *travel* fund" vs the bakery fund
  
  Exact phrase presence is therefore NOT evidence. Possessor and negation cues matter.
- Values recur in many sessions (blood pressure shows up in about 40 user turns, about 15 of them in August). Counting needs every in-window instance, so a sentence-level ledger is the only way to fit them all into 16k.
- The deposit that opens a balance can be paraphrased: "opened a separate savings account for the bakery and deposited 25,000 pesos" stands in for "bakery fund". Hence the synonyms fund ↔ savings/account.
- Test "multi-style" questions mix in KU-like ones ("how many laps … these days", "cats … right now") and running balances ("how much is left in my bakery fund"). The hint is chosen by question kind.

## Variants (ranked by expected value on TEST)

### 1. `ledger`: hybrid recall + lexical sweep + window + sentence ledger (TOP)
Algorithm (`build()` in a_tally.py):
1. `analyze(question, qdate)` produces:
   - content terms and their stems
   - noun-phrase runs ("tango shoes")
   - quoted titles and proper nouns
   - category synonyms from LEXICON
   - conjuncts ("X and Y")
   - the question kind: count, sum, diff, current or avg
   - the time window from a rule grammar: in/since/from-to month, this/last month, week or year, past N or few days/weeks/months, this or last season, "January and March"
2. Fused score over **user units only**:
   - RRF of `hx.hybrid(cleaned query + synonyms, k=300, roles="user")`, plus 0.5 × RRF of `hx.hybrid(raw question, k=100)`
   - plus a **lexical sweep** over every user unit: stem hits on head terms, a full phrase match (+1.5), titles and proper nouns (+1), synonyms (+0.6 each, capped at 2), and a small bonus for a number
   - × 0.15 when the unit falls outside the time window, applied only if `window_applies()`: at least 1 session inside, at most 85% of sessions inside, and a history span of at least 21 days. Never on dev; usually on test.
3. Session score = best unit + 0.3 × second best (normalised), plus `w_prior` × the fact-likeness prior (by-the-way, fact verb, number, date word, first user turn). Keep the top `max_sessions=24`.
4. Inside each session, choose `per_session=4` units by fused + 1.0 × prior + 0.4 × lexical.
5. Render each unit as an **excerpt**: the matching sentences ±1 sentence, "…" for gaps, and "(assistant asked: …)" before short replies. Fill the 15k budget with strongly matching sessions first (lexical ≥ 0.75 × best, when the best is ≥ 1.5), then the rest in rank order. Output passages oldest first.
6. `cite_plan` = up to 6 kept sessions with a lexical hit ≥ 1 whose kept sentences carry no other-person or negation cue; fall back to the top 3.

Hint, by kind:
- **count**: "The excerpts are the user's own messages, oldest first … First list every distinct instance with its date and [E#], then count. Count only the user's own (skip what friends, family, neighbours or others did or own), skip things only planned, considered, tried but not bought, or not done, and count an item mentioned in several conversations once. If the question sets a condition (a threshold, a place, a purpose), check it for each instance."
- **sum / diff / current / avg**: analogous wording ("list every amount … then add", "deposits +, withdrawals −", "state as of the latest excerpt").
- With a window: "Only count what falls in August 2023 (use each excerpt's date; 'yesterday'/'last night' refers to the day before the excerpt's date)."

`abstain_p` starts at 0.05, then:
- +0.35 for each quoted title, proper noun or number-unit ("30-gallon") absent from all user text
- +0.25 for each conjunct side with no stem in the user text
- +0.3 when the window is engaged and has no lexical hit
- +0.2 when no kept session has a lexical hit

At ≥ 0.5 the hint adds "'X' never appears in the history".

Measured with the BM25-only ranking (`bm25` variant, identical except `rank=bm25`), local approximation of the harness metrics:

| split | S | PA | ALL | ATR | SR | CF1 | chars | sessions |
|---|---|---|---|---|---|---|---|---|
| dev (121) | 68.6 | 0.893 | 0.942 | 0.957 | 0.977 | 0.509 | 14.9k | 15.4 |
| dev200 (22) | 65.6 | 0.864 | 0.955 | 0.961 | 0.991 | 0.469 | 14.6k | 18.0 |

Ablations on dev (BM25):
- same lens with per_session=2, budget 11k: S 58.1 / PA 0.702
- with no within-session cue selection: S 52.0 / PA 0.603
- whole user turns (`render=turns`, per_session 2, 16 sessions): S 58.8 / PA 0.702 / CF1 0.566

Expected failure modes:
- category → instance gaps that neither BM25 nor bge-small bridge (the reranker variant is aimed at these)
- a fact sentence cut from its excerpt when another sentence of the unit matches better (ATR still counts it, but Reactor does not see it)
- reading noise from single-word topic hits ("tango" everywhere)
- CF1 around 0.5: cite_plan picks 6 sessions where gold has 2 to 3
- a window guessed wrong on ambiguous phrasing ("last month" taken as the calendar month)
- dev questions whose window refers to dates written in the text, where the window is correctly not engaged but nothing else helps

Metrics that should move: PA (via ATR) and ALL; chars rises to about 15k (cost ≈ 4.6 S points, already included in S).

### 2. `ledger_rr`: variant 1 plus a cross-encoder on the top 60 fused units
The rerank score is added to the fused order (0.01 × normalised score). It targets the category → instance gaps and the decoy-heavy test topics, where the ms-marco cross-encoder can tell "I bought tango shoes for 1,800" from "tango class tonight". It costs about 60 rerank calls per question, cached. Metric: ALL on dev200, CF1.

### 3. `turns`: same selection, whole user turns, per_session 2, 16 sessions
More context per instance and fewer "…" cuts, so Reactor reads full statements. Best CF1 so far (0.566) but lower PA. Keep it as the fallback if Reactor spot checks show sentence excerpts confuse it.

### 4. `bm25`: variant 1 with BM25 instead of hybrid
No model-server dependency and about 0.1 s per question. The robustness baseline, and the numbers above.

## Not done yet / next round
- **Code-side ledger (`computed`)** for sum, diff and count on test-style data: extract (date, amount, unit, possessor, negation) from in-window, clean sentences and pass the list. Do not pass a final number until Reactor spot checks show the extraction is right; a wrong computed number misleads the reader.
- cite_plan tuning (CF1): threshold on lexical score and cue cleanliness against gold on dev; make cite_k depend on how many clean strong sessions exist.
- Better decoy cues: a "<Name> and I" ownership exception (the question "Bjørn and I in total"), and "for her/his …" (purpose decoys).
- A KU-style rule for "these days / right now" questions: keep the latest 3 or more dated values and say "latest wins".
- Tune `w_prior`, `w_within`, `strong_frac` and `max_sessions` on dev, then confirm on dev200.

## CORE REQUESTs
1. `core.pack.message_chars(question, hint, passages)` with exactly this signature, or document the actual one. The lens falls back to an estimate of 760 + len(q) + len(hint) + Σ(70 + len(text)).
2. Let `build_pack` accept pre-rendered per-session texts, or expose a sentence-excerpt renderer. Multi needs sentence-level excerpts from many sessions, not ±window units.
3. `included_turns` semantics: confirm that a turn counts as included when an excerpt holds only some of its sentences. My lens counts it.
4. An optional `hx.user_text` (lowercased concatenation of user turns) cached on the index. The lens caches it in `hx.__dict__` for now.
