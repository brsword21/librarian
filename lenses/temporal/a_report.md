# Temporal lens A ("Struktura"), round 4 report (final lens round)

**Verdict: no temporal test pack should change.** I checked all 36 temporal-routed v2 test packs by hand. None has a visible defect. Real Reactor has now answered 8 of them, and every answer equals our computed value and cites exactly the cite_plan sessions. I wrote no new lens: by the brief, a lens change is only worth making if it fixes a visible test defect, and there is none. The route stays on frozen v2, `lenses/temporal/a_r3_gap.py:span_own`.

Round-3 report moved to `a_report_r3.md`. Scratch tools are in `lenses/temporal/scratch_a/r4/`: `show.py` prints a test pack's hint and its user/dated lines, and `probe.py` runs a dense + bm25 probe on a test history. Runs are in `runs/r4-temporal-a/temporal/...`.

## 1. Test audit (the work that matters this round)

### Real Reactor answers so far (`runs/final/v1_results.jsonl`, packs identical in v2: same pack_hash)
| qid | question (short) | Reactor | computed | cites = cite_plan |
|---|---|---|---|---|
| q_06ae4afa8961 | son's play / daughter's orthodontist | 14 | 14 | yes (2) |
| q_7c7caecdcce6 | Run for Health 5K / charity gala | 139 | 139 | yes (2) |
| q_b81292033d1e | watercolour exhibition / leadership conf. | 83 | 83 | yes (2) |
| q_9a91a69855b3 | Adelaide trip / Brisbane trip | 71 | 71 | yes (2) |
| q_0d23d90f39ba | Python course start / first cleaning project | 43 | 43 | yes (2) |
| q_95c115fca37d | choir retreat / first test drive | 14 | 14 | yes (2) |
| q_1ac0e01c9100 | alfajor contest entry / winners announced | 104 | 104 | yes (2) |
| q_06b2f5975ae5 | tango ticket / closing night | 10 | 10 | yes (2) |

I read all 8 against the passage text. The dates are stated in the cited user sentences, and the day arithmetic is right.

### The 28 packs Reactor has not reached yet
`harness.audit --lens lenses/temporal/a_r3_gap.py --variant span_own --type temporal --n 999 --compare runs/final/v2_test_packs.jsonl` reports **0 of 36 changed**, so the rebuild is deterministic. I then read every pack (`scratch_a/r4/show.py`):
- **24 gap packs with a computed value.** In each one I checked the hint's two dates against the cited sentences and recomputed the day difference: 69, 72, 45, 43, 5, 73, 100, 21, 77, 108, 46, 14, 51, 134, 99, 101, 28, 7, 14, 14, 35, 50, 7, 73. All are correct. The planted decoys are all rejected by the picks and named as decoys by the hint:
  - Valentina's contest entry (06-08);
  - the neighbour's dress fitting (09-07);
  - Jan's daughter's cake tasting (09-15);
  - neighbour Jan's first hive inspection (05-03);
  - the wife's car tire change (07-06);
  - the previous car's inspection (06-30);
  - "jamboree April 22, 2022";
  - "anniversary June 21, 2022";
  - the sister's Trondheim visit (05-21);
  - the Toronto flat alerts;
  - the coworker's pottery workshop;
  - the high-school Opening Day.
- **Reschedules.** The r2 scan (`scratch_a/r2/resched.py test`) looked for later own mentions that move a scheduled date (dress fitting, cake tasting, tire change, inspection, hive inspection, varroa, Opening Day, jamboree, pottery, anniversary). It found none. Every later mention is someone else's event, a different year or a question.
- **Firefighter** (q_0f66a8b016b8): the pack holds "joined the fire brigade when I was 23" and "retired from the fire department the day I turned 63", so computed = 40. Both statements are present.
- **3 own-cut packs**, sent with abstain_p 0.8 and a factual "no statement that you did this was found" note. I re-probed each history with dense + bm25 queries (`scratch_a/r4/probe.py`) to rule out a paraphrased own statement. The only matches were decoys, so all three are unanswerable and the packs are right:
  - **trail run** (q_6ab86da6d151): only "Camille bought trail-running shoes today". The user's own purchases are hiking boots and sandals, and there is no trail-run statement.
  - **vaccines** (q_22ab86c83e4c): the only own check-up is a *dental* check-up (05-16). "Camille got her travel vaccines today" is someone else's, and "I still need to sort out my travel vaccines" is a plan.
  - **sourdough** (q_33cd29d8e252): Camille's starter, "I bought a bread tin ... when I eventually try sourdough" and croissant plans. No loaf is ever baked.
- **Misroutes.** Test has no temporal-style questions on other routes. A regex over the 110 non-temporal packs (how old / how long / ago / first / since ...) finds only 5 multi "since <month>" counts, which belong to multi.

### Runner-up sessions (optional, not recommended)
8 unanswered test packs carry a third, decoy runner-up session:
- q_1fda88c230cc, q_e6ffd9f64dac, q_ae313330ed3d, q_24028b381273
- q_7040872842c8, q_5bf8400d0361, q_2eb1ff9b6496, q_b0b9ca48ad21

`so_nor` drops it and changes 0 answers on dev and dev200 (S +0.0 / +0.1, Sall +0.4 / +1.2). It is still not a visible defect:
- the hint already names the decoy's date as a decoy;
- real Reactor has cited exactly the cite_plan on 8 of 8 temporal answers, and is selective on wider ku and multi packs.

Swap them only if they can go in before Reactor reaches those questions, so that no re-ask is needed.

## 2. Variants and scores
Variants run this round (no new lens file):
- **generic hybrid_rr**: the bar.
- **span_own**: the frozen v2 lens, rerun.
- **so_nor**: span_own plus tight gap packs without the runner-up session (round-3 variant, rerun for the optional item above).

| variant | split | S | Sall | PA | ATR | SR | CF1 | chars | AUC |
|---|---|---|---|---|---|---|---|---|---|
| generic hybrid_rr (bar) | dev (133 q) | 65.1 | 65.1 | .748 | .860 | .908 | .673 | 11931 | .636 |
| generic hybrid_rr (bar) | dev200 (26 q) | 61.2 | 61.2 | .727 | .849 | .910 | .589 | 11941 | .932 |
| **span_own (v2, frozen)** | dev | **81.3** | 77.6 | .898 | .957 | .980 | .843 | 7520 | .839 |
| **span_own (v2, frozen)** | dev200 | **83.7** | 77.3 | .909 | .955 | .968 | .897 | 7453 | .966 |
| so_nor | dev | 81.3 | 78.0 | .898 | .961 | .980 | .843 | 7486 | .839 |
| so_nor | dev200 | 83.8 | 78.5 | .909 | .955 | .968 | .897 | 7411 | .966 |

span_own scores 81.3 on dev here against 80.8 in r3. The whole difference is q_cd3c3026183d ("Who became a parent first, Rachel or Alex?", b_merge route, PA 0 -> 1). It is known non-determinism in frozen v1 code and has no test counterpart: the test rebuild is identical.

Brief items I checked and did not build, because each has 0 test questions:
1. **Span for "how old was I when X" / "years between X and Y".** Dev has 9 such questions, but only one is gold temporal (q_7eb367e868ef, already PA 1). Dev200 has none on the temporal gold type, and test has none on any route.
2. **Order-pack restatements.** Test has 0 order questions.
3. **Own coverage as a continuous abstain_p feature.** abstain_p is logged only (policy `no_generic_abstain_hint`), so Reactor would never see it.

## 3. Top failure patterns (dev / dev200, all absent from test)
Dev has 13 PA failures out of 127 answerable questions; dev200 has 2 out of 22.
1. **"What did I do N days/weeks ago" whole-question packs** (b_merge sess / other_k). There are 7 failures:
   - **ATR 0**: the right session is in the pack, but its "today / yesterday" turn is not. Examples: q_643c729c83da #PlankChallenge (5 days ago), and q_f1a895ed2f4e "planted 12 new tomato saplings today" (two weeks ago).
   - **ALL 0**: a second gold session at another date is missing. Examples: q_7bdc4143c6b1 first-client contract, q_02eff28e554f ukulele with Rachel, q_e27bb7b3e7b6 cousin's wedding, dev200 q_511a2e5387c0.
2. **Order questions with a paraphrased restatement** (5 failures; ATR 0.5-0.67):
   - q_4cfd0e98cac7 "upgraded my home Wi-Fi router 3 weeks ago" never names the "mesh network system";
   - q_2ad03036e541 Europe / Thailand;
   - q_f00c26116d06 bus / train;
   - q_b7049267f6d0 Disney+;
   - q_1525ff1b6137 has a same-day third gold session.

   Lexical mention lists miss these, which is why so_ordm (more mentions) changed nothing.
3. **Aggregates.** q_2403af78a507 ("months since I last visited a museum with a friend", 13k chars, topic mode) and q_32dba15e4898 (months-before-anniversary: computed 2 is correct, but the third gold session is missing).

## CORE REQUESTs
1. **None for the final pass.** Keep temporal on `a_r3_gap.py:span_own` and re-ask no temporal question.
2. When reading the remaining Reactor answers, expect INSUFFICIENT_EVIDENCE (or a non-number) on q_6ab86da6d151, q_22ab86c83e4c and q_33cd29d8e252, and these numbers on the others:
   - 40 for q_0f66a8b016b8;
   - the computed values listed in section 1 for the 24 gap packs.

   Any other answer would be a Reactor reading error, not a pack defect.
3. (Post-hackathon.) Make the b_merge cross-encoder ordering deterministic (q_cd3c3026183d flips PA between runs).

## Ideas if there were another round
- **"N ago" pin.** Compute T = question date - N, and pin the top-1 or top-2 CE user units of the sessions dated T ± tolerance (days ±1, weeks ±3, months ±10). This targets the ATR-0 cases in failure pattern 1. Estimate: +1 S on dev, 0 on dev200 and test.
- **Order restatements by dense similarity** (hx.dense_texts of the event phrase over the user units of the pick sessions) instead of lexical mentions. Replace fill units rather than adding to them.
- **Age span** ("how old was I when X"): the same scanner as span with an age + event-date combiner. This only matters on a test set that contains such questions.
