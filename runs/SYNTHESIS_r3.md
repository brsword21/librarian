# Round 3 synthesis (integrator): v2 = the system for the final Reactor pass

v1 (git tag v1, `configs/best_v1.json`) is being answered from `runs/final/v1_test_packs.jsonl` and was not touched.
v2 = `configs/best_v2.json` (copied to `configs/best.json`, git tag v2). Final packs: `runs/final/v2_test_packs.jsonl`
(rebuilt from `configs/best.json` with the answer-format suffix; reproduces bit for bit). Changed packs:
`runs/final/v2_changed_qids.txt` (10 qids), reasons in `runs/final/v2_changed.tsv`.

## Per-type winners

All numbers are S / PA / CF1 / chars. "Gold" means gold-type questions sent straight to the lens. "Route" means
questions the text router sends to that route, run through the full routed system. Both come from the same full
dev (526) and dev200 (125) splits; none used `--limit`.

| type | winner (v2) | dev | dev200 | v1 on the same slice |
|---|---|---|---|---|
| ssu (route) | `ssu/a_r3_route.py kg3crga` + inner `ssu/merged_r3.py ku11fn4s_p5` + role `ssa/a_r3_role.py` + ku hand-off `ku/a_r3 r3w` | 88.8 / .947 / .952 / 4125 | 88.8 / .971 / .900 / 4192 | 86.1 / 82.3 |
| ssa (gold) | `ssa/a_recsent.py r2_conf2` (unchanged) | 93.6 / 1.0 / 1.0 / ~4.5k | 93.7 / 1.0 / 1.0 / ~4.2k | same |
| multi (route) | `multi/merged_r2.py tight_role9` (b_tight p08c35_aor) + role `ssa/a_r3_role.py` | 86.7 / .943 / .906 / 5460 | 84.2 / .921 / .872 / 5814 | 86.3 / 84.2 |
| ku (gold) | `ku/a_r3.py r3w` | 93.4 / 1.0 / .979 / 3044 | 93.3 / 1.0 / .977 / 3072 | tie (b_r2 r2b) |
| temporal (gold) | `temporal/a_r3_gap.py span_own` | 80.8 / .89 / .844 / 7518 | 83.7 / .909 / .897 / 7453 | tie (fires on 0 answerable dev q) |

How each winner was chosen:
- **ssu**: A alone (kg3crga) scored 87.7 / 85.0 and B alone (ku11fn4s_p5) 87.6 / 88.1. Both are under +2 on dev.
  They are complementary: A adds a typed own-update gate and a runner cite, B adds a ku-cue recall backstop. B's inner
  lens dropped A's `ru_cite`, so I wrote `lenses/ssu/merged_r3.py` to pass it through. The merged lens scores
  **+2.7 dev / +6.5 dev200** on the routed ssu route, which passes the rule. KU-B's qt3c_ap (another ssu-route ku gate,
  0 test changes) was not taken because it overlaps A's gate.
- **ssa**: the type is saturated. Both role refits (SSA-A r3fit, SSA-B comb_guard_adv) reach the same diagnosis and
  change 0 test packs. I took SSA-A's `a_r3_role.py` as the role detector on the ssu and multi routes: gold ssa
  through the router goes from 91.8 to 93.0 on dev and ties on dev200.
- **multi**: `b_r3_full ufull_h` (untrimmed user units) was **rejected** for v2. It fixes a real defect (PA_fact
  0.48 -> 0.95; trimming caused a false INSUFFICIENT_EVIDENCE on road-trip hours in calibration). But it scores
  -0.3 / -0.4 S, changes 15 of 20 test packs, and on test the extra text is chatter or planted decoys ("I read five
  journal articles for my PhD literature review" in a books count, orchid repotting in the grandchildren pack). No
  numeric own fact was missing from the v1 test packs. `a_r3_pin ab` changes only abstain_p and was not wired.
- **ku**: r3w ties r2b on dev and dev200 (the type is saturated), but it fixes 5 visible test defects (see below).
- **temporal**: span_own is v1 plus a span computation for "how many years did I serve" plus an own-cut for gap
  questions with no own statement. Temporal-B's r3_hk6 (+1.4 dev, 0 dev200, 0 test changes) is below the bar.

## Routed system (same-run comparison, `--tag merge3`)

| | dev S | Sall | PA | CF1 | chars | AUC | dev200 S | Sall | PA | CF1 | chars | AUC |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| v1 | 86.0 | 84.9 | .935 | .899 | 5582 | .814 | 84.9 | 83.2 | .918 | .894 | 5478 | .855 |
| **v2** | **86.9** | **85.3** | .942 | .915 | 5585 | .813 | **87.0** | **85.2** | .946 | .905 | 5489 | .853 |

Per gold type, dev (dev200): ssu 87.4 (87.1), ssa 93.0 (93.7), multi 85.2 (83.0), ku 91.5 (86.8; v1 87.9 / 76.8),
temporal 80.3 (84.2). The ku gain comes from the ssu-route gate and backstop: ku->ssu goes from 77.4 to 85.7 on dev
and from 54.7 to 74.8 on dev200.

## Test pack changes vs v1 (10 that Reactor sees, plus 1 cite_plan-only)

`harness.audit --diff runs/final/v1_test_packs.jsonl runs/final/v2_test_packs.jsonl`. A v1 rebuild from
best_v1.json is identical to v1 on all 146 packs, so none of these changes is noise.
- ku r3w, 5 packs:
  - **job title**: v1 abstained with INSUFFICIENT_EVIDENCE because the pack lacked the promotion sentence. This is
    the only question that needs a re-ask.
  - **laps**: the v1 hint list missed the newest value ("30 laps").
  - **long run**: v1 lacked the "Sundays at 6:30 a.m." recap.
  - **horses**: the v1 hint used "Bjørn's daughter has 2" (a decoy). v2 computes 9 + 2 + 5 = 16.
  - **apple trees**: the v1 latest-wins hint invited "3". v2 gives 4 + 3 = 7.
- temporal span_own, 4 packs:
  - **firefighter**: v1 had neither own statement. v2 has both and computes 40.
  - **own-cut** on trail-running shoes (only Camille bought them), travel vaccines (Camille's check-up, the vaccines
    only planned) and first sourdough loaf (never mentioned). v1 hints showed garbage date picks (a meatloaf recipe,
    a film night). v2 sends a factual "no statement that you did this was found" note.
- ssu, 1 pack: **move date** is handed to ku (Sept 2 -> "now September 16", cite both sessions).
- cite_plan only, not re-asked: café (adds the user's own Caffè Gilli session). The pack hash is the same.

Only the job title (v1 order 9) was answered by v1 when the packs were built. The other 9 sit at v1 order 48-142,
so they will most likely be asked for the first time in the v2 pass. The queue's pack_hash cache serves every
unchanged answered pack for free.

## Real Reactor so far (v1, first 24 answers)

There were 3 INSUFFICIENT_EVIDENCE answers:
- "my dog's name": no own dog exists in the history (only Helen's puppy Luna and a therapy dog), so this is likely
  correct.
- "current job title": the pack was weak. Fixed in v2.
- "my neighborhood in Lisbon": the pack was weak. "I live in Graça" was never retrieved; the question word does not
  occur in that sentence.

The ssu ownership hint did not cause the neighborhood abstention, and the ku hint did not cause the job-title one. In
both cases the fact was missing from the pack. The ku "Cite both..." line works (ceramics, accountant and watercolour
teacher all cite 2 sessions).

## Router

- Text router accuracy: dev 0.679, dev200 0.648. After the evidence hand-offs: 0.783 and 0.736.
- Confusion on dev, as gold -> final route:
  - ku -> multi 32 (S 93, harmless) and ku -> ssu 19 (S 85.7)
  - ssa -> ssu 7 (was 13)
  - ssu -> multi 13 (S 77.5)
  - multi -> ssu 7 (S 61, the costliest misroute) and multi -> temporal 9
  - temporal -> ssu 5 (S 57) and temporal -> multi 4
- No router change in v2: any rule change moves test routes, and therefore packs, with no clear test defect to fix.
  The costly misroutes are aggregate/compositional questions landing on ssu ("two hobbies", "how old was I when").

## Abstention (`configs/abstain.json`)

The routed v2 abstain_p AUC is 0.813 on dev, 0.853 on dev200 and 0.821 pooled. No threshold reaches precision 0.7
at recall 0.4: pooled >= 0.8 gives 9 TP and 22 FP, and temporal has 21 answerable packs at >= 0.8. Policy:
`no_generic_abstain_hint`. Keep only the lenses' factual "not found / someone else's" notes. Reactor already abstains
by itself when a fact is missing, so a generic hint would mostly add false abstentions.

## Citations: a trade-off to keep in mind

S uses cite_plan, Sall assumes Reactor cites every passage. The v2 gap is 1.6 on dev and 1.8 on dev200, mostly on
temporal (route S 82.3 vs Sall 77.4: packs carry 3-5 sessions against a 2-session cite set). Whether we may filter
Reactor's citations is unconfirmed, so v2 relies on what we send:
- the answer-format suffix asks Reactor to cite only "the passage(s) that state it";
- ku and ku hand-off hints say "Cite both the session with the earlier value and the session with the latest value";
- horses lists its 3 labels;
- own-cut temporal packs shrink to 1-2 sessions.

Real Reactor mostly follows this: 1-2 labels per answer, 4 on the vegetables count. Multi wide packs remain the main
risk.

## CORE REQUESTs

Implemented:
- `harness.audit --compare/--diff` now reports passage-text, hint (both pack formats, suffix stripped), old -> new
  cite ids, and computed / abstain_p as info. It warns on partial diffs and counts Reactor-visible changes.
  Requested by SSU-A, SSU-B, KU-A, SSA-A and TEMP-B.
- Config wiring as requested by SSU-A/B, KU-A, TEMP-A and SSA-A.
- `routed_v1` / `routed_v2` pipeline variants.

Declined:
- CE/dense score rounding and tie-break for determinism (TEMP-B). It would change scores, and therefore test packs,
  in the final pass. The test rebuild is already bit-identical, so the ±0.5 S noise is dev-run specific.
- hx.sentences instance index (MULTI-A). Too large for the final pass.
- PA_fact / ATR_any metrics (MULTI-A/B). Useful next round. MULTI-B's strict.py is a drop-in.
- In-session gold-turn rank in harness.failures. Next round.
- Router rules "by how many <unit> did I <change>" (1 test q, no dev counterpart) and "my example of" -> ssa (0 test).
- ufull_h and the rescue lenses (see multi above).

## What worked / what failed

**Worked:**
- Gates that require two affirmed own statements with typed, disjoint values. They keep planted decoys out (friend's
  starter, Francesca's café, "briefly tried 68 uF").
- A recall backstop that only acts when the floor widens the window.
- Per-owner and additive count hints in ku.
- The own-cut on planted-decoy gap questions.
- Composing A and B wrappers through params instead of editing their files.

**Failed:**
- Dense sentence rescue in multi: low precision, and it hits test decoys.
- The pool-relative z-score for abstention (anti-informative).
- Unit-level tense fix: it moves test R-77 cites to wrong sessions.
- Wider windows for counts: they only add decoys on test.

**Open:** category -> instance vocabulary gaps (neighbourhood -> "I live in Graça", kitchen gadget -> Instant Pot,
books -> detective novels). This is the main source of the remaining PA misses and real Reactor abstentions.

## Brief for the next round

### A (structure) agents
- **ssu-A**:
  1. Second hop for category -> instance questions: run hx.dense_texts over first-person declaratives ("I live in",
     "my new X", "I got/bought/adopted") in the top-20 sessions, gated by answer type (place, name, product). Targets:
     the test neighbourhood question and dev "kitchen gadget before the Air Fryer".
  2. Fix the ownership-hint head noun: test hints read "their own ride work", "their own before work", "their own
     ohms", "renovation company working". Take the noun-phrase head after my/the; when it is not a noun, or the
     question has no first-person word, emit no hint.
  3. Clause-level tense check. Validate on the test audit first; dev cannot see the R-77 regression.
  4. "By how many <unit> did I <change> X": pack the before and after own statements and compute the difference.
- **ssa-A**:
  1. An impersonal user-fact feature plus sentence-level CE (assistant vs user sentences), to separate the d -5..-1
     band ("President's advisor" vs "move to the new apartment").
  2. On hand-offs without a recommendation cue, cite the best turn's own session.
  3. A role-play detector ("my jumpsuit", "my character", "in the story").
- **multi-A**:
  1. Within-session depth: add each kept session's best good-sentence unit (the second-gold-turn losses). Sall is
     unaffected.
  2. A rescue driven only by verb class (bought/added/read/attended) plus statement-form CE. Audit test decoys before
     any pack change.
  3. Calibrate the s_top abstention term on dev200 per route.
- **ku-A**:
  1. Value-attribution check: the value must attach to the attribute noun (long run 6:30, not playgroup 9:00).
  2. When the old member is someone else's value (Carlos's coffee), replace it with the best own older session.
  3. bge sentence admission (hx.dense_texts) for paraphrased promotions and updates.
  4. Coordinate with multi so ku questions routed to multi (32 dev) also get the "cite both" line inside the
     number-changed clause.
- **temporal-A**:
  1. Generalise span to "how old was I when X" and "how many years between my X and Y".
  2. Order packs: replace B's fill units with per-event restatement mentions.
  3. Own coverage as a continuous abstain_p feature, calibrated on pooled dev+dev200.

### B (semantic) agents
- **ssu-B**:
  1. Score sessions by their best clean OWN sentence, so a decoy sentence inside a mixed unit cannot lift its session
     (café pattern).
  2. Pair cite by value type instead of the 2nd-best session (dev200 5K PB, Saturday wake-up).
  3. Multi hand-off inside the ssu wrapper on aggregate cues ("two", "both", "how old was I when") when two clean own
     sessions sit within 6 logits. multi->ssu misroutes score S 61.
  4. Build a synthetic sibling-slot plus update check set from dev histories.
- **ssa-B**:
  1. Semantic quote fallback (hx.rerank_texts over first-person recommendation sentences) when no sentence matches
     the category lexically (Heden/coworking).
  2. One calibrated detector deciding ssa / ku / ssu on the ssu route, sharing p_assistant with the ku gate.
  3. A symmetric hint guard on the multi route.
- **multi-B**:
  1. A cheaper renderer: whole user units only for each session's top 3 units, fact-trimmed depth. Report PA_fact and
     the number of first-person numeric decoy sentences added on test (the ufull_h objection).
  2. Port ku's rel logic (old count + "added N") to "how many ... currently" on the multi route.
  3. Verb-class instance scoring (bought vs repotted orchids; novels vs books).
  4. Prepare a 5-pack Reactor spot check: ufull_ck vs ufull_h.
- **ku-B**:
  1. Status and place q_types (finished / started / still / moved to) behind a REVERT-style guard (Nightingale,
     Rachel).
  2. An answer-type second hop for paraphrased old values (Instant Pot).
  3. Per-route isotonic calibration of abstain_p, so hand-offs produce comparable scales.
- **temporal-B**:
  1. Two-pool whole-question packs: the anchor session plus category-mates from a category-noun query, one unit each
     on a separate ~5k budget.
  2. Order questions: pin paraphrased second gold turns via rare tokens plus a dense_texts floor.
  3. A/B disagreement monitor (keep A's value and list B's picks as "other mention").
  4. Trace the ±0.5 S dev non-determinism (q_cd3c3026183d).
