# Round 2 synthesis (integrator), v1 freeze

Commit `Round 2 merge`. Routed system: `lenses/pipeline.py` + `configs/best.json`. Round-1 system: `configs/best_r1.json`
(`--variants routed_r1`). All comparisons use the full gold-type question sets (no `--limit`); every candidate below ran on
the same 526 dev / 125 dev200 questions.

## Winners per type (gold routing)

S / PA / CF1 / chars. `Sall` = S if Reactor cites every passage we send (pessimistic citation bound).

| type | winner (route lens) | dev S / PA / CF1 / chars | dev200 S / PA / CF1 / chars | Sall dev / dev200 | incumbent (r1) dev / dev200 S, Sall |
|---|---|---|---|---|---|
| ssu | `ssu/a_struct2.py` r3rn, wrapped by `ssu/merged_r2.py` role8_r3rn | 93.4 / 1.000 / 0.984 / 3609 | 92.5 / 1.000 / 0.955 / 3859 | 92.7 / 89.7 | a_struct nb3t0 93.5 / 92.5, Sall 93.2 / 90.7 |
| ssa | `ssa/a_recsent.py` r2_conf2 | 93.6 / 1.000 / 1.000 / 4542 | 93.7 / 1.000 / 1.000 / 4186 | 93.6 / 93.7 | recqs_cf7 93.3 / 93.3 (5587 / 5376 chars) |
| multi | `multi/b_tight.py` p08c35_aor, wrapped by `multi/merged_r2.py` tight_role9 | 87.2 / 0.950 / 0.910 / 5841 | 83.3 / 0.909 / 0.868 / 6279 | 85.7 / 82.3 | b_sweep deep8_10k 86.6 / 85.2, Sall 73.9 / 73.5 (9949 chars) |
| ku | `ku/b_r2.py` r2b | 93.4 / 1.000 / 0.979 / 3043 | 93.3 / 1.000 / 0.977 / 3072 | 93.6 / 92.7 | b_semantic pair_r1b 93.2 / 93.1, Sall 83.9 / 83.8 |
| temporal | `temporal/merged_r2.py` evA_mixB (new merge) | 81.3 / 0.898 / 0.843 / 7562 | 83.7 / 0.909 / 0.897 / 7453 | 77.6 / 77.3 | merged_r1 76.4 / 82.1, Sall 71.8 / 74.2 |

Decisions (rule: +2 S on dev and no loss on dev200; on a tie, fewer chars or simpler):
- **ssu**: gold-type S is saturated, so every candidate ties (r3rn -0.04 / -0.09, b_merge best -0.01 / -0.04). I took
  r3rn on the **routed** system, which is what gets submitted. Same config otherwise: routed dev 84.3 -> 85.0 and
  dev200 82.9 -> 84.1 (e1 vs e2 below). r3rn is more robust on misrouted questions, and on test it changes only 2
  cites, both recency fixes (see the test changes below).
- **ssa**: r2_conf2 ties (+0.3 / +0.4) with about 1k fewer chars and Sall = S. Accepted on the tie-break.
- **multi**: an explicit exception, because of citations. On gold-type S, b_tight is +0.6 on dev and -1.9 on dev200
  (one question loses PA), so the S rule alone keeps deep8_10k. But Sall goes 73.9 -> 85.7 on dev and 73.5 -> 82.3 on
  dev200, and the pack shrinks from 9.9k to 5.8k chars. On the routed system the two tie on S (e1 84.3 vs e4 84.2 dev;
  82.9 vs 83.0 dev200), and b_tight is +3.5 / +3.2 on Sall. Since we cannot post-filter Reactor's citations, b_tight
  is the safer choice. Fallback if a Reactor check shows over-abstention on tight multi packs:
  `lenses/multi/merged_r2.py` deep8_role9.
- **ku**: b_r2 r2b ties on S (+0.2 / +0.2), uses 600 fewer chars and gains +9.7 / +8.9 Sall (pair only, no context
  sessions). a_r2 cenq5_dp has Sall = S, but loses 1.1 S on dev (PA 0.986).
- **temporal**: new merge `lenses/temporal/merged_r2.py` evA_mixB. Questions lens A claims (`_GAP`, plus named-event
  ago / order / gap kinds) go to a_gap ct_evgba; everything else goes to b_merge ev1_mix_g. The two round-2 gains sit on
  different subsets. Against merged_r1: +4.9 dev, +1.6 dev200. Against the better single challenger (b_merge): +1.0 /
  +0.5 S, +2.7 / +2.3 Sall, and 1.5k fewer chars. The pure-gap split (gapA_mixB) scores 80.4 / 83.4.

## Routed system

| run | S | PA | CF1 | chars | AUC | Sall |
|---|---|---|---|---|---|---|
| **v1 dev (526 q)** | **86.0** | 0.935 | 0.899 | 5582 | 0.814 | **84.9** |
| **v1 dev200 (125 q)** | **84.9** | 0.918 | 0.894 | 5478 | 0.855 | **83.2** |
| r1 dev / dev200 | 80.4 / 79.9 | 0.867 / 0.864 | 0.877 / 0.864 | 7375 / 7173 | 0.719 / 0.808 | 74.9 / 74.2 |

Config ablation on the routed system, before the r2 router rules (S / Sall, dev | dev200; runs `runs/merge2x`):

| config | dev | dev200 |
|---|---|---|
| e1: ssu nb3t0 + role hand-off + ssa r2_conf2 + multi b_tight + ku b_r2 + temporal merged_r2 | 84.3 / 83.3 | 82.9 / 81.6 |
| e2: e1 with ssu r3rn (= v1 without the router rules) | 85.0 / 84.0 | 84.1 / 82.7 |
| e3: e1 + ku_pair hand-off on the ssu route | 84.7 / 83.4 | 84.2 / 82.9 |
| e4: e1 with multi deep8_10k | 84.2 / 79.8 | 83.0 / 78.4 |
| e5: e2 + ku_pair hand-off | 85.3 / 84.2 | 85.4 / 84.1 |
| **v1 = e2 + router r2** | **86.0 / 84.9** | **84.9 / 83.2** |

Routed vs gold routing per gold type, S dev (dev200): ssu 87.4 vs 93.4 (87.1 vs 92.5); ssa 91.8 vs 93.6 (93.7 vs 93.7);
multi 84.9 vs 87.2 (82.6 vs 83.3); ku 87.9 vs 93.4 (**76.8 vs 93.3**); temporal 80.3 vs 81.3 (84.2 vs 83.7).
The cells that still hurt (gold -> route, n, S):
- ku -> ssu: dev 25 q at S 77, **dev200 9 q at S 55 (PA 0.56)**. This is the biggest remaining loss. The ssu pack
  finds one value and misses the newest one.
- multi -> ssu: dev 9 q at S about 50. temporal -> ssu: dev 5 q at S about 50. ssu -> multi: 13 q at S 73.
- ku -> multi: 29 q at S 93. The multi lens degrades gracefully.
- ssa -> ssu: 13 q left at S 84, after the role hand-off took 37 dev ssa questions to the ssa lens.

### Evidence-based hand-offs (wired)
- `reactorq.build_packs` routes by text only and calls `cfg["routes"][route]`, and reactorq is frozen. So the hand-offs
  live inside the route lenses: `lenses/ssu/merged_r2.py` and `lenses/multi/merged_r2.py`. That way the Reactor packs
  and `lenses/pipeline.py` behave identically: the wrapper-based run reproduces the pipeline-hand-off run exactly
  (84.1 / 85.0).
- **role_guess** (SSA-B, `lenses/ssa/b_role.py`): p = sigmoid(0.35·clip(CE_asst − CE_user, ±8) + 2.2·[no first-person
  word] − 1.2). A question goes to ssa at p ≥ 0.8 on the ssu route and p ≥ 0.9 on the multi route. It is never applied
  to ku or temporal. FP 0 on dev and dev200. **0 of 65 test ssu/multi-routed questions switch.**
- **ku_pair_p** (KU-B): measured but **not enabled**. It adds +0.3 dev and +1.3 dev200 routed (e5 vs e2), but on test
  it moves 6 of 45 ssu-routed questions into 2-session KU pairs: q_2ea50c2672ba sourdough starter name,
  q_6e893bcca955 and q_ca7af42dbd6c R-77 capacitor / dial lamp (sibling slots), q_6d1f42a4c0a8 birthday restaurant,
  q_f14893711b1a move date, q_b7053d97740b café. These are the planted drift / decoy patterns that SSU-A flagged as
  costing about 0.33 CF1 each. Too much test change for a +0.3 dev gain, so it is deferred to round 3, which needs a
  value-type gate.
- `lenses/pipeline.py` also takes an optional `"handoff"` block in a config, used for the experiments in
  `configs/exp/`. `configs/best.json` does not use it.

## Router (core/router.py)

Text router accuracy: dev **0.658 -> 0.679**, dev200 **0.632 -> 0.648**. Final route accuracy, including the role
hand-off: dev **0.759**, dev200 **0.712**. New rules, applied only when the base rules say ssu or temporal:
- "how many days / weeks / hours did I spend / take ..." with an aggregate cue (in total, all, and, trips, activities,
  breaks, a comma) and no gap word -> multi. On dev+dev200 it fixes 8 multi questions and breaks 0 (the singular
  "solo camping trip to Yosemite" and "finish 'The Nightingale'" stay temporal).
- "the most / the least / compared to" -> multi. It fixes 5 multi questions. 2 temporal questions that were already
  misrouted to ssu move to multi.
- **0 test questions change route** (checked against the HEAD router and with `harness.audit --compare`). Routed:
  dev 85.0 -> 86.0, dev200 84.1 -> 84.9.

Rejected: "how long have I been" -> ku. It would fix 6 ku questions but move 3 correct temporal ones, and the ku lens
on temporal questions is unmeasured.

Confusion on dev, final routes (rows = gold; columns ssu / ssa / multi / ku / temporal):
ssu 49/0/14/2/5 · ssa 13/97/1/0/1 · multi 9/0/114/0/10 · ku 27/0/32/15/4 · temporal 5/0/4/0/124.

## Test audit (no gold): every change against round 1

`runs/audit/all/pipeline/routed/test_packs.jsonl` against `runs/audit/r1_routed_test_packs.jsonl`:
- **Route changes: 0 of 146.** Hints are unchanged on all 146 packs. Passage sets changed on 81 packs. Mean passages
  per pack: multi 11.65 -> 5.35, temporal 8.28 -> 2.42, ku 4.00 -> 2.65, ssu 2.71 -> 2.80, ssa 1.04 -> 1.00.
- **cite_plan changes: 18 packs.**
  - multi, 14 packs, from b_tight replacing deep8_10k. In 11 of them the cite set grows to the whole tight pack and
    keeps every round-1 cite: q_068d0a4b3f7b ceramic pieces, q_6dd9e5e4fb97 watercolour classes, q_eefdc20af97b
    vegetable varieties, q_91ae9daa0edc car savings, q_bcd6d210710b bakery fund, q_47e3f2749c07 orchids,
    q_4d36a6e5d796 phone calls with daughter, q_90f7c27a95f2 grandchildren, q_d52f60bba453 book club attendance,
    q_cd53d3a105e4 honey, q_0920dea94636 backyard trees. Three drop one weak session from a 5-cite set:
    q_31e7201b2c55 tango shoes, q_6834eb0349a2 R-77 tubes, q_43e6976bec02 systolic > 130.
    Justification: the passages now approximately equal the cite set, so the result no longer depends on whether
    Reactor cites selectively.
  - ssu, 2 packs: q_1fae05d78e0c (R-77 AM intermediate frequency) and q_1a8be2824d48 (R-77 speaker impedance). r3rn's
    `rec_need` stops the recency jump to the 07/14 screen-grid-resistor session, which only shares the topic, and cites
    the latest own statement of the attribute (SSU-A report, pattern 4).
  - temporal, 2 packs: q_e6ffd9f64dac (Montreal flat alerts -> lease) and q_24028b381273 (hive inspection -> varroa).
    a_gap's tight pack cites only the two event sessions and drops the runner-up from the cite.
- Flags (5): 4 temporal packs without a computed value, at abstain_p 0.60-0.70 (firefighter years, trail-running shoes
  -> first trail run, medical check-up -> vaccines, sourdough starter -> first loaf), and 1 multi pack at abstain_p
  0.54 (feijoada last month). No empty packs. Every cite_plan session is in its pack. Max chars per pack: ssu 5.9k, ssa
  3.0k, multi 9.9k, ku 3.6k, temporal 8.0k.
- One concern for the Reactor check: the multi hint (unchanged since round 1) asks Reactor to "first list every
  matching instance as 'date | [E#] | item | number'". This may conflict with the orchestrator's answer-format suffix.
  It was already in the E1 calibration packs.

## Citations: the trade-off

We submit whatever Reactor cites among the passages we send, so CF1 on cite_plan is optimistic whenever a pack carries
decoy or context sessions. v1 closes most of that gap by sending fewer sessions rather than relying on a filter:
routed Sall went 74.9 -> 84.9 on dev and 74.2 -> 83.2 on dev200, against S 86.0 / 84.9. The cost is a small PA risk on
multi (dev200 PA 0.955 -> 0.909 on gold type) and fewer context sessions for Reactor to cross-check. Temporal still has
a gap (S 81.3, Sall 77.6): the whole-question route sends about 1 session more than it cites. No "cite only ..." hint is
sent yet. If the organisers' per-[E#] measurement shows Reactor cites everything it is given, trim temporal next; if it
cites selectively, deep8-style recall packs become affordable again.

## Abstention (configs/abstain.json)

Policy: **no abstention hint, no threshold**. abstain_p is logged and used only inside lenses. Pooled AUC on dev+dev200
is 0.82 (dev 0.814, dev200 0.855; r1: 0.719 / 0.808), but over 45 unanswerable vs 606 answerable questions precision
peaks at about 0.29 (thr 0.5: 16 TP / 40 FP; thr 0.8: 9 / 22). Temporal packs reach abstain_p ≥ 0.8 on 21 answerable
questions. Real Reactor abstained correctly on 3/3 unanswerable questions with no hint, and over-abstained on 1 multi
question, so a hint would push the wrong way. A route's soft hint gets re-enabled only at precision ≥ 0.7 with recall
≥ 0.4 on pooled dev+dev200, after per-route isotonic calibration.

## CORE REQUESTs

Done (backward compatible):
- `harness.sweep --qfilter REGEX` (temporal A and B).
- `--route` runs write to `<type>-routed` (ssu-A).
- Per-gold-type breakdown printed for routed and all-type sweeps (ssu-A).
- `passages_mean` in summary.json (multi-A); the leaderboard columns are unchanged.
- `harness.audit --compare OLD` and `python -m harness.audit --diff OLD NEW` (ssu-A).
- role_guess wiring (ssa-A, ssa-B), via the route wrappers.
- Route ssu / ssa / multi / ku / temporal to this round's winners.

Declined:
- ku_pair wiring: see above.
- `route_with_evidence` in core: core must not import lenses. The final route is in `pack.route` /
  `debug.route_final`, and `pipeline.final_route()` exists for experiments.
- `hx.sentences` with a sentence-keyed CE cache (ku-A) and pinned sentence-level instances in `build_pack` (multi-A):
  index / pack API changes this close to the freeze. They are first in line for round 3.
- Session-strength rank of missing gold in `harness.failures` (multi-A): the lens can already save it in `debug`, which
  per_question.jsonl keeps.
- Computed coverage in metrics (temporal-A).
- Isotonic calibration (temporal-A): proposed in abstain.json, not implemented.
- Answer-anchored citation (ssu-B): needs the organisers' ruling.
- Hoop Dance gold_turns check (ssa-B): not looked at.

## What worked / what failed

Worked:
- Sall-aware packing: tight multi, pair-only ku and tight temporal gap packs, together +10 routed Sall at equal or
  better S.
- The evidence role detector (+2.9 routed dev on its own, 0 FP, 0 test change).
- Merging A and B on disjoint subsets (temporal).
- Small router rules checked against test phrasing.

Failed or deferred:
- KU pair detection on the ssu route: real gain on dev, but it fires on test drift and decoys.
- Abstention thresholds: still below 0.3 precision.
- ssu gold-type work: saturated at about 93.5, so all the gains were on misroutes.
- ku -> ssu misroutes remain the biggest loss (dev200 9 q at S 55).

## BRIEF for round 3 (per type and role)

See the structured output (`brief_a`, `brief_b`). The same text is below.

### A (structure)
- **ssu-A**:
  1. Build a value-disagreement gate for KU pairs, together with ku-B. Fire only when two affirmed own statements of
     the same attribute head carry different values of the same type (number, time, name, model). Never fire on sibling
     slots (R-77 capacitor vs dial lamp) or name drift. Report routed ssu dev/dev200 and list the firings on test with
     `harness.audit --compare` (today 6 of 45: q_2ea50c2672ba, q_6e893bcca955, q_ca7af42dbd6c, q_6d1f42a4c0a8,
     q_f14893711b1a, q_b7053d97740b).
  2. Degrade gracefully on misrouted aggregates (multi->ssu and temporal->ssu at S about 50 on 14 dev q): when the
     question has a count or comparison word or a time window, widen to ±1 neighbours and up to 4 sessions.
  3. Tense fix: a plan clause outranks a past marker in "did I / was I" questions.
- **ssa-A**:
  1. Fit role_guess as a logistic model on dev and hold out dev200. Add A's recommendation-sentence scan ("Brew Supply"
     for "homebrew supply shop") and an impersonal-user-fact feature. Keep FP 0.
  2. List-position questions (fifth / number 7 / last on the list): pack the assistant chunk with the list plus the
     next chunk.
  3. 13 dev ssa questions remain on ssu at S 84: find what the role detector misses there.
- **multi-A**:
  1. Pinned instance sentences (sentence-level CE, own, declarative) ahead of depth units, so buried facts get in
     without widening packs.
  2. A `multi_like(q, hx)` evidence detector (two or more sessions with own instance sentences of the same category)
     for an ssu->multi hand-off, measured on the 9 dev multi->ssu questions, with 0 FP on gold ssu and the test list
     printed.
  3. Port facet_absence to b_tight's abstain_p and calibrate it on dev+dev200 pooled.
- **ku-A**:
  1. CE admission of paraphrased newest values (F-150, long-run recap) into the timeline.
  2. Prefer habitual or change statements over one-off events for "each morning / these days" questions.
  3. Per-owner totals ("Bjørn and I in total") with relative updates ("2 more").
- **temporal-A**:
  1. Cut the no-computed gap packs. On test, 4 flagged questions (trail-run, vaccines, sourdough loaf, firefighter
     years) get no value: parse "how many years did I serve" and future-planned events.
  2. Parse "how many months since I last X" as ago-last.
  3. A reschedule guard for tight packs.
  4. Order questions: restatement mentions plus the opening user turn, in a tight pack.

### B (semantic)
- **ssu-B**:
  1. Merge B's all-role recall sweep into a_struct2 r3rn as a recall backstop only, with no change to the cite set.
  2. Precompute sentence-level CE for the top-12 user units, and turn abstain_p into a pool-relative z-score.
  3. Slot-specific lexical check (rarest slot term or abbreviation, IF for intermediate frequency) before the recency
     pick.
- **ssa-B**:
  1. One combined role detector (B's CE margin plus A's structural scan) behind the same `role_guess(q, hx)` signature,
     so the wrappers can swap it in.
  2. A temporal-route hand-off with its own features (12 FP at 0.7 today), measured on 'my example of Netflix'-style
     questions.
  3. Leave ssa packs as they are (about 2.7k chars on test); trimming loses PA.
- **multi-B**:
  1. Adaptive breadth for windowed counts (kind == count with an active window prior: keep in-window sessions with
     p ≥ tk/2, up to 12), checked with the test audit.
  2. Refit p(gold) with richer features (first-person numeric fact, facet hits, window flag) on dev, holding out dev200.
  3. Instance expansion for category questions via `hx.dense_texts` over the user sentences of sessions ranked 4-15.
  4. A variant whose passages equal the cite set exactly (Sall = S), as the fallback if Reactor cites everything.
- **ku-B**:
  1. The value-type gate for `ku_pair_p` (shared with ssu-A). Target the 25 dev / 9 dev200 ku->ssu questions with 0 FP
     on gold ssu and no firing on test sibling slots or name drift.
  2. Own-value constraint in the pair: replace someone else's value with the best own sentence of the same value type.
  3. Calibrate abstain_p on dev+dev200 pooled; count the bigram signal only together with low coverage.
- **temporal-B**:
  1. Gap fallback by agreement: when A withholds a value that equals B's computed one, emit it.
  2. Trim the whole-question route towards its cite set (S 81.3 vs Sall 77.6).
  3. Use sentence-level `rerank_texts` to find the second gold turn in "first" questions.
  4. For explicit-date "ago" questions, compute from the question date.
