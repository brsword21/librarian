# Temporal lens B ("Semantyka"): design, round 0

Code: `lenses/temporal/b_evcal.py` (VARIANTS + build; pure helpers self-test: `.venv/bin/python -m lenses.temporal.b_evcal`).
Scratch: `lenses/temporal/scratch_b/` (`proxy_eval.py` = model-free proxy of the ranking, `dated_sents.py`, `grep_test.py`,
`dev_analysis.py`, `date_census.py`).

## What the data says

**Test (the target: 35 temporal-style questions, about 24% of test)**
- All 35 are "How many days apart were X and Y?" or "How many days after X did/was Y?". The parser in b_evcal splits 35/35 into two event phrases.
- Explicit dates are rare: about 19 sentences per history (13–40; 1–2 in two histories) carry a full date. So the candidate pool "units with a date" is tiny and can always be scored in full by the cross-encoder.
- The facts follow a fixed template: `{I | My <event> | You (assistant) | Your <event>} <event> on <date>.` The fact is usually stated in the session dated on the event day. Planned events (for example "is on April 19", or "scheduled for 2023-09-05" stated in May) are stated earlier. Some are stated a day or two later ("I flew to Brisbane ... on 20 August" in the 22 Aug session).
- Decoy kinds, all checked against the histories:
  - **Person.** "My friend Camille also repotted her monstera on 2023-03-12", "Your colleague Sam attended the hospital leadership conference on 22 May 2023", "Your roommate bought a Korg Minilogue", "Camille's last day of school ...". These often fall on the same date or the next day. They appear in both user and assistant turns.
  - **Event variant.** "winter exhibition opening" vs "annual", "modular synth workshop" vs "synthesizer workshop", "a rough demo of a different song", "a second set of acoustic panels for my bedroom", "adoption fee on 04-13, the day before we brought her home".
  - **Contrast cue.** "..., not the orthodontist appointment", "but that is separate from the play".
  - **Year.** "Our anniversary was June 21, 2022" vs the assistant's "Your anniversary is June 21, 2023" when the question says "this year". Also "The league jamboree was on April 22, 2022".
  - **Assistant-only truth.** "You left for your Ardèche canoe trip on 2023-07-12". In assistant turns "You/Your" is the user.
- **Abstention traps** (new finding). In h_3c02cbc43fc9, four questions (sourdough starter, pre-departure check-up, travel vaccines, trail-running shoes) only have statements about Camille. The user explicitly did *not* do it ("I can't take on a sourdough starter", "I still need to sort out my travel vaccines"). "Only someone else did X" is therefore a strong abstain signal for test.
- Some facts use relative dates or no year ("I booked my flight to Montreal ... this morning", "starts on April 5"). So the resolver needs explicit date > relative-vs-session > session date.

**Dev (different style)**
- 127 answerable: "which first" 31, "days between/before/after" 22, "N days/weeks/months ago" 21, order 7, durations 11, plus about 36 "what did I do two weeks ago"-type questions.
- All 253 gold turns are user turns. Cues: "today" 126, no cue 37, no-year "January 10th / the 15th of April" 39, "N ago" 30, "last <weekday>" 19, "yesterday" 10.
- The gold number equals the session-date gap for 33/45 numeric questions. The rest have both events in one session with dates in the text ("Ash Wednesday ... on February 1st", "Mary's Church on January 2nd").

## Metric note (affects variant choice)
For temporal, `PA = ALL and (HA if computed else ATR==1)`. A wrong `computed` zeroes PA even when the pack is perfect, while dropping `computed` falls back to ATR. Under this metric, `computed` only pays when we are right more often than ATR fails. Yet the computed gap is the main lever for Reactor, a fast instruct model that is poor at date arithmetic. Hence a gated variant, and CORE REQUEST 1.

## Variants (ranked by expected value on TEST)

### 1. `evcal`: event calendar with semantic re-scoring (main bet)
- **Parse** (`parse_question`): kind ∈ {apart, after, before, between, since_when, ago_when, howlong_when, ago, spent, first, order, other}, plus unit (days/weeks/months/years), event phrases and a `this_year` flag. Quotes are stripped and the text is cut at the first "?".
- **Pool per event**: all units with an explicit date (`dated_units`, cached per history), plus `hx.hybrid(event, k=30)` (RRF k=60, w_bm25=w_dense=1). If the question carries an anchor ("two weeks ago", "last Saturday"; `question_anchor`), it also adds `hx.hybrid(event, k=20, uids=units in [anchor-3·tol, anchor+tol])`. Units dated after the question are dropped.
- **Score** = `hx.rerank(event, pool)` logit, plus:
  - `3.0·overlap`: share of the event's stemmed content tokens found in the best sentence of the unit.
  - `+1.0` if that sentence has an explicit date, `+0.3` if it has a relative date.
  - Subject: `+1.0` for self ("I/We/My <thing>" in user turns, "You/Your" in assistant turns, after stripping prefixes such as "Oh, and", "By the way,", "...: ", "Speaking of X,"); `−4.0` for another person (`my/your <friend|coworker|roommate|colleague|son|...> [Name]` or a bare capitalised name subject that is not in the question).
  - `−5.0` for a contrast cue negating the event's tokens; `−1.5` for "a different / another / a second".
  - `−3.0` for a year mismatch when the question says "this year"; `−1.5` for a stale explicit year (more than 200 days before the session).
  - `+2·exp(−|Δ|/tol)` time prior toward the question anchor.
- **Date** (`resolve_date`): the explicit date whose preceding clause shares the most event tokens. Otherwise a relative expression resolved against the session date (via `core.dates.extract_dates`). Otherwise the session date.
- **Compute** (`compute_answer`): |d2−d1| for apart/between/since_when/ago_when/after/before, and q.date−d for ago. The result is converted to the question's unit (weeks = round(d/7), months = round(d/30.44)).
- **Pack**: `build_pack(ranked = top-2 per event interleaved, then hybrid(question, k=40) fill; budget 7000, window 1, chrono)`. `cite_plan` = the top-1 session per event.
- **Hint** (example): `Script-extracted event dates (ignore events of other people, other years or different events): (1) "my son's school play" -> 2023-06-10 (Sat) [date written in the text; session 2023/05/28]; (2) "my daughter's orthodontist appointment" -> 2023-06-24 (Sat) [...]. Computed difference: 14 days.` For first/order questions it adds "Chronological order: A < B". For only-other events it adds: "the history only shows someone else (not the user) doing it; if the user never did it, answer INSUFFICIENT_EVIDENCE."
- **abstain_p** = 1 − (1−p_lex)(1−0.7·p_ce)(1−p_other), where:
  - p_lex = 0.6 if a capitalised or quoted question word never occurs in the history;
  - p_ce = σ(−(best CE + 2)/2) over the weakest event;
  - p_other = 0.75 if, among an event's top-10 candidates, the best "other person" CE score beats the best own one by more than 3.
- **Expected failure modes**:
  - Paraphrased events with no shared tokens; the CE has to carry these.
  - Dates that are part of a name ("the March 15th issue of The New Yorker" read "today").
  - Unsupported formats: "on the 3/8" (M/D, no year) and "a week before Black Friday".
  - A plan statement ("planning to test ... next month") outranking the actual event ("tomorrow").
  - Both events in one 700-char chunk with two dates (handled by clause proximity, but fragile).
- **Should move**: HA and PA on test-style questions, CF1 (top-1 citation per event), and abstention AUC (only-other signal). chars about 7k (−2.2 S).
- **Model-free proxy** (overlap instead of CE and no dense; `scratch_b/proxy_eval.py`):
  - dev: 87/127 answerable questions parsed into events, 47 got a number, HA 37/47 = 79%, top-1 event session in gold 148/155 = 95%;
  - dev200: HA 6/9, session hit 25/27;
  - test (qualitative): about 27/35 picks look right by eye; the misses are the four only-other traps and one plan-vs-done case.

### 2. `evcal_gated`: same, but `computed` only when confident
- `conf` = min over events of σ(margin/2), where margin = top score − best candidate with a *different* date. `computed` (and the "Computed difference" sentence) is set only when conf ≥ 0.6. The dated list stays in the hint.
- The point is to protect PA from the HA trap on low-margin questions. On test this matters less (most margins are large), so it ranks second unless round 1 shows that HA < ATR on uncertain questions.
- **Should move**: PA on dev where the parse is shaky (since_when/ago_when/before).

### 3. `evcal_wide`: recall for multi-event and order questions
- k_hyb 50, 3 alternatives per event, budget 12000. Dev order/duration questions have 3–6 gold sessions, and the "other" questions have no decomposition (whole-question hybrid with the anchor time prior).
- Costs about 1.5 S in chars; expected to win on dev ALL/ATR and to lose on test precision (Reactor sees more decoys).
- **Should move**: ALL and ATR on dev and dev200.

### 4. `ce_only`: ablation
- Same pool and pack, with every feature weight at 0 and no time prior. It measures what the subject, contrast and year features add over the plain cross-encoder. Not meant for submission.

## Ideas not yet in code (round 1+)
- Declarative query templates for dense/CE ("I {verb-past} {object} on"), and masking date tokens before the CE so that dates do not drive similarity.
- Sentence-level CE: score the fact sentence instead of the 700-char chunk, so the injected one-liner is not diluted by its host turn (see CORE REQUEST 2).
- Tune weights on dev with the gold-turn rank diagnostic (`debug.ranking`). Expected order of importance: w_other > w_neg > w_lex.
- Learn the abstain threshold from dev's six unanswerable questions plus the CE distribution; the only-other rule is test-motivated and cannot be tuned on dev (no such traps there).

## CORE REQUESTs
1. **Temporal PA**: replace `ALL and (HA if computed else ATR==1)` with `ALL and (ATR==1 or HA==1)`, and report HA separately. Otherwise lenses are rewarded for withholding the computed gap that Reactor needs most.
2. **Arbitrary-text rerank**: `hx.rerank_texts(query, texts) -> list[float]` (CE on arbitrary strings, cached by text hash), to score single sentences.
3. **`core.dates`**:
   - M/D without a year ("on the 3/8"; ambiguous, so maybe only when the day is ≤ 12 and the session is in the US);
   - a `named` flag for dates followed by "issue/edition/episode";
   - keeping "this morning / tonight / last night" as offset 0/−1 (present already, good).
