# Round 1 synthesis (integrator)

Commit `Round 1 merge` (0df37c5). Routed system: `lenses/pipeline.py` + `configs/best.json`. Every comparison below uses
the full gold-type question set (no `--limit`), the same for both lenses. The only partial run was multi A `ledger` (40 q),
which was not a candidate.

## Winners per type (gold routing)

S / PA / CF1 / chars. `Sall` = S if Reactor cites every passage we send (new pessimistic bound, see Citations).

| type | winner | dev S / PA / CF1 / chars | dev200 S / PA / CF1 / chars | Sall dev / dev200 | AUC dev / dev200 | runner-up (dev / dev200 S, Sall) |
|---|---|---|---|---|---|---|
| ssu | `ssu/a_struct.py` nb3t0 | 93.5 / 1.000 / 0.984 / 3489 | 92.5 / 1.000 / 0.955 / 3589 | 93.2 / 90.7 | 0.91 / 0.91 | b_sem best_rec 93.5 / 92.6, Sall 89.1 / 86.0 |
| ssa | `ssa/a_recsent.py` recqs_cf7 | 93.3 / 1.000 / 1.000 / 5587 | 93.3 / 1.000 / 1.000 / 5376 | 92.6 / 92.9 | n/a (no unanswerable) | b_semantic session10k1_rr 92.5 / 93.1 |
| multi | `multi/b_sweep.py` deep8_10k | 86.6 / 0.967 / 0.896 / 9949 | 85.2 / 0.955 / 0.874 / 9951 | 73.9 / 73.5 | 0.64 / 0.83 | a_tally bm25_tight 83.0 / 82.2, Sall 66.0 / 65.3 |
| ku | `ku/b_semantic.py` pair_r1b | 93.2 / 1.000 / 0.979 / 3669 | 93.1 / 1.000 / 0.977 / 3729 | 83.9 / 83.8 | 0.89 / 0.89 | a_timeline pkd_b2 92.1 / 93.1, Sall 83.3 / 83.8 |
| temporal | `temporal/merged_r1.py` gapA_semB | 76.4 / 0.843 / 0.817 / 9099 | 82.1 / 0.909 / 0.861 / 9074 | 71.7 / 74.2 | 0.77 / 0.97 | b_sem sem_turns9 75.3 / 80.9; a_calendar ftb_bm25 74.0 / 75.3 |

Decisions:
- ssu: A and B tie on S (within 0.1 on both splits). I took A because citations hold up. If Reactor cites everything
  we send, A keeps 93.2 / 90.7 and B drops to 89.1 / 86.0, because B packs about 6 sessions on test against about 3 for A.
  On the test audit A's single cite looked right more often where they disagreed (21 of 45). Examples: younger son
  Daniel, favourite meal pilau, and the grill, where A cites the newest "returned the Weber, bought a Big Green Egg"
  session.
- ssa: A, by +0.7 on dev with a tie on dev200, fewer chars and no model calls. The type is saturated.
- multi: B, by +3.6 dev and +3.0 dev200, and +8 on Sall.
- ku: tie (+1.1 dev, 0.0 dev200). I took B for fewer chars and PA 1.000 on dev against 0.986. A has the better
  abstention AUC (0.90 / 0.94).
- temporal: a new merge, `lenses/temporal/merged_r1.py`. Gap questions ("how many days apart / after / before", 34 of
  36 test temporal questions) go to A ftb_bm25, and everything else goes to B sem_turns9. On the gap subset A beats B by
  +5.0 (dev, 29 q) and +5.3 (dev200, 5 q). On the whole type the merge gains only +1.1 / +1.2 over B, which is below the
  2-point rule. I adopted it anyway because the test temporal mix is 94% gap questions, where the gain is about +5.
  I also checked A-on-event-route vs B-on-question-route on dev200: it loses 1.6 there, so I kept the phrasing split.

## Routed system (router -> winner per route)

| run | S | PA | CF1 | chars | AUC | Sall |
|---|---|---|---|---|---|---|
| dev (526 q) | **80.4** | 0.867 | 0.877 | 7375 | 0.719 | 74.9 |
| dev200 (125 q) | **79.9** | 0.864 | 0.864 | 7173 | 0.808 | 74.2 |
| before the router fix (B ssu, B temporal) | 78.3 / 78.5 | | | | | |
| generic hybrid_rr (80 dev q, r0) | 73.4 | 0.932 | 0.552 | 11935 | 0.883 | |

With gold routing, the per-type winners would give about 87.3 on dev, so routing costs about 7 S on dev. Almost all of
that comes from dev phrasing that test does not use. These are the dev cells that hurt (gold -> route, S):
- ssa -> ssu: 50 dev questions, S 70.1. They are cue-less paraphrases such as "Back in Bandung soon. Which restaurant
  ..." or "In the dinosaur children's book, what colour ...". Every test ssa question says "you recommended" and
  routes correctly.
- ku -> ssu: 25 q, S 69.7 (dev200: 9 q, S 47.6). The one-session ssu pack misses the old/new pair.
- ku -> multi: 29 q, S 91.2. The multi lens degrades gracefully.
- multi -> ssu: 10 q, S 43.3. multi -> temporal: 16 q, S 80.1. ssu -> multi: 13 q, S 71.9.
- The reverse direction is the dangerous one: multi -> ku scored S 16.5. So ambiguous counts stay with multi on purpose.

## Router (core/router.py)

Accuracy on gold type: dev **0.633 -> 0.658**, dev200 **0.584 -> 0.632**. Changes:
- "you" addressed to the assistant (not "I told you"), "remind me" (53 of 53 dev questions with it are ssa), and
  "we talked / last time we" -> ssa.
- "last Saturday / the past weekend", holidays, "first, second ...", and "most recently ... X or Y" -> temporal.
- "these days", "so far", "right now", "my current", "... now?" with how many/much -> ku. On test this moves 5
  questions from multi to ku: laps, cups of coffee, km each evening, GB data plan, rooms renovated so far.
  "currently" counts stay multi ("How many instruments do I currently own" is multi on dev).
- Test routes: ssu 45, temporal 36, ssa 25, multi 20, ku 20.

Remaining confusion on dev: ku without a cue (27 -> ssu, 32 -> multi) and cue-less ssa (50 -> ssu). Text rules cannot
fix these; it would take evidence-based detectors (see the briefs). The dev numbers overstate the problem for test.

## Citations (the trade-off)

The submitted citations are whatever Reactor cites among our passages, and post-filtering by `cite_plan` is not
confirmed. CF1 on `cite_plan` is therefore optimistic. Routed dev: CF1 0.877 on the plan against 0.694 if every passage
is cited (S 80.4 vs Sall 74.9). The loss by route: multi 0.87 -> 0.44 (about 8-12 passages for 2-3 gold sessions),
temporal 0.83 -> 0.65, ku 0.96 -> 0.64 (2 context sessions beside the pair). ssa and ssu barely move. Two directions
for round 2:
(a) Send passages close to the cite set: drop context and decoy sessions once the lens is confident.
(b) Add a short hint asking Reactor to cite only the passages that state the answer or each counted item. Offline
    metrics cannot see whether (b) works, so (a) is preferred.
Every sweep now prints `CF1all` / `Sall`. Report both from now on, and do not accept a variant that wins S but loses
more than 2 on Sall.

## Abstention (configs/abstain.json)

- Policy: no abstention hint to Reactor yet. Packs only; Reactor decides from the passages.
- Data: on the final routed system over dev+dev200 (45 unanswerable, 606 answerable), no threshold gets above about
  0.25 precision; at 0.8 there are 13 true abstentions against 43 false ones. Lens AUCs are fine inside their own
  type (ssu 0.91, ku 0.89, temporal 0.77 / 0.97), but the scales differ. On test, 6 of 45 ssu packs score 0.8 or
  more on probably answerable name questions.
- Re-enable rule: a route may add a soft hint ("If none of the passages states this about me, say that our
  conversations do not contain it."), never a forced abstention, once its abstain_p reaches precision >= 0.7 at
  recall >= 0.4 on dev+dev200 pooled.

## Core requests

Done (backward compatible; routed numbers unchanged by them):
- `build_pack(..., pinned=[uids], max_chars_per_session=N)`. pinned covers KU-B pinned_uids and "best session whole +
  runner-up best turn only". The docstring and CONTRACT now state the priority order and the window=0 +
  explicit-neighbour mode.
- `HistoryIndex.rerank_texts(query, texts)` and `dense_texts(query, texts)`: sentence-level CE and bge on arbitrary
  strings, through the same cache (requests from temporal-B, ku-B, multi-B).
- Harness: `CF1all` / `Sall` in per_question and summary and printed by sweep; `included_turns` saved per question;
  `harness.failures` marks each gold turn IN / MISS; `harness.audit` saves route, cite_plan and debug in
  test_packs.jsonl and prints debug. HA containment for sentence answers was already in metrics.
- CONTRACT.md: message_chars signature, the new API, the citation caveat.
- configs/best.json now routes to the winners (cite_plan for ku, temporal and multi is honoured in the metric only).
  The submission-side choice is still open (see Citations).

Declined:
- Model-server priority or queues: we must not restart the shared server. Load is low now (agents are done and
  caches are warm; the routed dev run takes 40-120 s).
- Abbreviation guard in `core.units`: it changes unit boundaries and ids, which would invalidate every cache and
  every lens's uid assumptions mid-event.
- Redefining temporal PA as ALL and (ATR or HA): it would break comparability across rounds. Lenses can report it
  themselves.
- `--ablate-gold` (needs a re-index per question) and an answer-anchored citation filter (a submission-time rule that
  the organisers have not confirmed).
- Generic baselines per type: the agents' runs already cover them (leaderboard r1-*), so I did not re-run them.

## What worked / what failed

Worked:
- Structure-aware, mostly lexical lenses saturate ssu, ssa and ku on dev (PA 1.0, S about 93), at 3-6k chars, with
  little or no model use (ssa A is BM25 only).
- The depth-first, CE-within-session sweep for multi.
- The CE whole-question route for non-gap temporal questions.
- The calendar event-pair computation for gap questions.
- Asymmetric routing: misroutes into multi are cheap, misroutes out of multi are not.

Failed or open:
- Temporal is still the weakest type (dev PA 0.84). The causes are aggregate "since / last time" questions, missing
  second gold turns in "first" questions, and wrong unit conversions (HA 0.62 on dev gap questions for A).
- Multi decoys on test (friends' purchases, declined buys) are left to Reactor.
- Citation robustness is poor for multi, temporal and ku.
- Abstention is uncalibrated across lenses.
- Test audit: 15 flagged. Six are temporal gap questions with no computed value (trail run, first loaf, hive
  inspection / varroa, wife's birthday / anniversary, Montreal alerts -> lease, Toronto Marathon / Moroccan dinner),
  plus "How many years did I serve as a firefighter?" (probably unanswerable, abstain_p 0.62). The other 8 are ssu
  questions with abstain_p >= 0.5.

## BRIEF for round 2

### Structure agents (A)

- **ssu-A (a_struct nb3t0, routed winner).**
  (1) Latest-value phrasing on test: "I last mentioned", "did I end up naming / using", "now". About 15 test ssu
  questions. Pick the newest affirmed own mention and say so in the hint. Audit sourdough starter, last book, last
  restaurant, last beer kegged and the R-77 "end up" values.
  (2) Graceful degradation for KU misroutes (dev200 ku -> ssu: S 47.6). When the two best sessions state different
  values of the same attribute, pack both, newest first, and cite the newest.
  (3) Calibrate abstain_p on dev+dev200 pooled. Dog name, partner name and favourite colour score 0.8 or more on test.
  (4) Value voting for name drift (cat Fig / Sombra / Bica).
  Report Sall.
- **ssa-A (a_recsent recqs_cf7, routed winner).**
  (1) Cut chars with no PA loss: pack the best turn +-2 turns (or `max_chars_per_session`) once turn@1 is confident.
  Target about 4k chars.
  (2) The INSUFFICIENT_EVIDENCE gate should also need the category word to be missing from the top session (Lisbon /
  Heden).
  (3) Offer a role check usable on cue-less questions: `role_guess(q, hx) -> p_assistant` from your structural scan.
  Measure it on dev ssa vs ssu (50 dev ssa questions without cue route to ssu today).
- **multi-A (a_tally, runner-up).**
  (1) Citation-robust packing: 17 passages give Sall 66. Pack only sessions with an own, in-window instance sentence
  plus at most 2 recall sessions, and report Sall.
  (2) Export your facet / conjunct-absence check as a function that B can import for abstain_p (B's AUC is 0.64 on
  dev).
  (3) Code-side ledger note (date | session | sentence) with decoy filtering: friends' purchases, "decided not to
  buy", "skipped". Measure it as a variant of B via import, not as a separate lens.
- **ku-A (a_timeline pkd_b2, runner-up, ties with B).**
  (1) Drop the 2 context sessions when the pair is confident. Sall is 83.8 against S 93; target Sall within 1-2 of S.
  (2) Audit the 5 test questions newly routed to ku (laps each morning, cups of coffee, km each evening, GB data
  plan, rooms renovated so far) and the paraphrased updates (job title -> promotion, long-run recap).
  (3) Your abstention is the best on ku (AUC 0.94 dev200). Expose `abstain_p(q, hx)` so the routed ku lens can use it.
  (4) Per-owner totals ("Bjørn and I in total right now").
- **temporal-A (a_calendar ftb_bm25, now serves gap questions = 34/36 test temporal).**
  (1) Six test gap questions get no computed value: relative dates such as "today" and "tonight", anniversary and
  birthday, "first trail run". Relax min_score when the two events are clearly picked, and add the holiday /
  anniversary grammar.
  (2) When computed is confident, pack only the two event sessions plus at most one runner-up (now 8.3 passages,
  Sall 65).
  (3) HA is 0.62 on dev gap questions. Withhold computed near rounding boundaries or when one date is vague, and use
  `hx.rerank_texts` on event phrases to pick the event sentence (bus / train, smoker).
  (4) An abstention rule for questions with no event match ("years did I serve as a firefighter").
  Evaluate through `lenses/temporal/merged_r1.py` (gap subset) and as your own lens.

### Semantic agents (B)

- **ssu-B (b_sem best_rec, runner-up on Sall).**
  (1) Your pack has about 6 sessions on test and Sall 89.1 / 86.0, against 93.2 / 90.7 for A. Keep decoys out of the
  passages and name them in the hint instead; keep a decoy session only if it changes the answer.
  (2) You degrade much better on KU misroutes (dev200 ku -> ssu: S 76.7 vs 47.6 for A). Build
  `lenses/ssu/b_merge.py` importing A's owner / polarity / tense features with your recall sweep and recency pair. It
  must beat A on routed ssu-route S (run `--route --type ssu`) without losing Sall.
  (3) Fix the "last mentioned" cite: on the grill question you cited the Weber kettle session instead of the newest
  Big Green Egg one.
- **ssa-B (b_semantic session10k1_rr, runner-up; the type is saturated).**
  (1) Build an evidence-based role detector `role_guess(q, hx)`: best assistant-unit CE logit against best user-unit
  CE logit in the top session. Measure accuracy on dev ssa vs ssu gold. The integrator will wire it into the router
  for questions without cues.
  (2) Sentence-level trimming of non-best turns (`hx.rerank_texts`) to about 4k chars with no PA loss.
- **multi-B (b_sweep deep8_10k, routed winner).**
  (1) Citation robustness: test packs carry 11.7 passages for 3.1 cites (Sall 73.9 vs S 86.6). Add a CE relevance
  floor for depth units, drop sessions with no instance unit, and try a short hint ("cite only the passages that
  contain a counted item"). Accept on S and Sall.
  (2) KU-style counts land in multi (29 dev ku questions, S 91). When the same item is restated with a new number,
  state "latest statement wins" in the hint.
  (3) Category -> instance misses ("projects led" -> poster or case competition; "health devices" -> hearing aids):
  sentence-level CE via `hx.rerank_texts` over the user units of the top sessions.
  (4) Missing-facet abstain_p (import A's check).
- **ku-B (b_semantic pair_r1b, routed winner).**
  (1) Pack only the cited pair when it is confident. Sall is 83.9 against S 93.2; the 2 context sessions cost about
  0.33 CF1 if Reactor cites everything.
  (2) Audit the 5 test questions newly routed to ku ('these days', 'my current', 'so far') and the paraphrased updates
  (current job title -> promotion).
  (3) Phrase-level (bigram) abstention for entity swaps ('Italian restaurants', 'Software Engineer Manager').
  (4) An evidence-based detector `ku_pair_p(q, hx)` for the router: 25 dev ku questions go to ssu and 32 to multi
  today. Report its precision on dev ssu and multi questions, because a false positive into ku is very costly for
  multi (S 16).
- **temporal-B (b_sem sem_turns9, now serves non-gap temporal questions).**
  (1) Improve the whole-question route (dev S 64.6 on its 40 questions): aggregate "since I last / in a row /
  how many X before Y", and adaptive cite count (1-2 for single answers, N for "order of the N").
  (2) Second gold turn in "first" questions (sem_turns direction).
  (3) For gap questions where A has no computed value, offer your CE event picks and computed value as a fallback,
  as a variant of `merged_r1` (copy it to `lenses/temporal/b_merge.py`).
  (4) Pack fewer sessions (Sall 71-75).
