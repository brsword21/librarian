# SSA lens B ("Semantyka"): round 3 report

Round-2 report: `lenses/ssa/b_report_r2.md`.

Files:
- `lenses/ssa/b_r3_role.py` (new). It holds the combined role detector `role_guess(q, hx)`, the ssu-route hint guard, the "should I" advice hand-off, and a routed wrapper lens that measures all three.
- Scratch: `lenses/ssa/scratch_b/r3_probe.py` (role features for every router-placed question; outputs in `r3_probe_{dev,dev200,test}.jsonl`) and `r3_compare.py` (per-question differences against v1).
- Runs: `runs/r3-ssa-b/` (`ssa/`, `ssu-routed/`, `multi-routed/` and `all/`).
- Test audits: `runs/audit/{ssu,multi,ssa}/b_r3_role/{comb_guard,comb_guard_adv}/`.

No frozen file was edited.

## TL;DR
1. **The ssa type stays saturated.** v1 (`a_recsent r2_conf2`) scores PA = CF1 = 1.0 at 4.5k / 4.2k chars. The test ssa packs are healthy: 25 single sessions of 2.4 to 3.2k chars, and 23 of 25 quote the recommendation line. Following brief item 3, I did not trim them.
2. **The real-Reactor failure on ssa is a hint conflict, not retrieval.** In the calibration run, the one ssa miss was q_73a1f68b2421 ("Which company does a great job with environmentally responsible supply chains?"). The question was routed to ssu, and the pack contained the answer, Patagonia. The ssu lens adds "Answer from what the user said about their own supply chains. Mentions of other people's … are not the answer." Reactor obeyed that hint and answered INSUFFICIENT_EVIDENCE.
   - On dev, every one of the 13 gold-ssa questions left on the ssu route carries this hint (dev200: 1). The proxy PA scores them as fine (S ≈ 94).
   - v1 still routes q_73a1f68b2421 to ssu (p = 0.73).
   - Lens A found the same problem independently this round (`a_r3_role.py`, variant nh55).
3. **Deliverable: `b_r3_role.py comb_guard_adv`.** It adds three things to v1, and no test pack changes (audit --compare: 0 of 90 ssu / multi / ssa packs change route, cite, passages or hint; ku and temporal are untouched by construction):
   - **(a) Combined detector.** B's cross-encoder margin plus A's lexical role scan. TP at FP 0 goes from 37 to 39 of 50 on the dev ssu route and from 5 to 6 of 6 on the dev multi route; dev200 is unchanged at 6 of 7 and 2 of 2. Both thresholds are unchanged.
   - **(b) Hint guard.** On a ssu-routed question with no first-person word and p ≥ 0.6, the ownership / decoy / "user never mentions" sentences are replaced by a role-neutral line. It fires on 6 ssa + 1 ssu question on dev, 1 + 1 on dev200, and 0 on test.
   - **(c) Advice hand-off.** "should I …" on the ssu route goes to the ssa lens at p ≥ 0.5. One dev question moves: S 29 → 93.
4. **Routed S** (all 526 / 125 questions): dev 85.9 → **86.2** (Sall 84.7 → 85.0, AUC 0.810 → 0.811), gold-ssa rows 91.8 → 93.0 (PA 0.973 → 0.991; ssa route 97 → 101 of 112), dev200 tie at 84.9 / Sall 83.2. That is below the +2 acceptance bar. It is a robustness and Reactor-motivated change with **zero test diff**.

## Variants tried (one line each)
`lenses/ssa/b_r3_role.py`. Each variant is the whole routed system: text router, then configs/best.json, with the overrides below.
- `v1`: control. Reproduces v1 exactly (dev200 84.9 / Sall 83.2 / AUC 0.855).
- `comb`: the ssu and multi wrappers (`merged_r2`, through their `role_module` parameter) use the combined `role_guess`: `z = 0.35·clip(d,±8) + 2.2·nf0 − 1.2 + logit(pA) − 0.5`, `p = sigmoid(z)`. Thresholds stay 0.8 (ssu) and 0.9 (multi). `pA` is A's r2 lexical `role_features` (BM25 role diff, top-5 role mix, per-role term coverage, first-person count, advice cue).
- `v1_guard`: v1 plus the hint guard (soft = 0.6, ssu route, no first-person word). Isolates the guard.
- `comb_guard`: `comb` plus the guard.
- **`comb_guard_adv` (recommended)**: `comb_guard`, plus "should I" questions on the ssu route go to `a_recsent recqs_cf7` when p ≥ 0.5 (A's r2 nf50a idea).
- Offline only (`r3_probe` rows), not swept:
  - A 9-feature standardised logistic fit: ssu TP 38 at FP 0, but the multi margin shrinks to 0.17 logit. Rejected as overfit.
  - `B + 0.5·logit(pA)`: 40 / 50 on ssu, but the ssu margin is 0.40 and it gives 1 FP on ku and on temporal.
  - `B + top1_a`, `B + top5_a`, `B + advice` alone: no gain.
- Temporal-route hand-off (brief item 2): **not built.** dev has exactly one gold-ssa question on the temporal route ("Which show was my example of Netflix only having the last season available?"), and dev200 has none. That question is user-role: its answer is the user's own line, so d = −8.9 and no assistant-margin feature can see it. v1's temporal lens already answers it (S 91.9). Meanwhile 7 dev / 2 dev200 temporal questions sit at p ≥ 0.8 under either score ("Which trip did the narrator take first …"). Nothing can be learned from one positive.

## Results
Columns: S / PA / ATR / SR / CF1 / chars / AUC. dev and dev200 have no unanswerable ssa question, so AUC is "-" on ssa rows.

**Gold ssa questions, ssa lens on gold type** (the ssa route itself)

| split | lens / variant | S | PA | ATR | SR | CF1 | chars | AUC |
|---|---|---|---|---|---|---|---|---|
| dev (112) | generic `hybrid_rr` (baseline) | 72.3 | 1.000 | 1.000 | 1.000 | 0.368 | 11932 | - |
| dev | v1 `a_recsent r2_conf2` | 93.6 | 1.000 | 1.000 | 1.000 | 1.000 | 4542 | - |
| dev200 (22) | generic `hybrid_rr` | 71.2 | 1.000 | 1.000 | 1.000 | 0.331 | 11938 | - |
| dev200 | v1 `a_recsent r2_conf2` | 93.7 | 1.000 | 1.000 | 1.000 | 1.000 | 4186 | - |

**Gold ssa questions through the router** (what gets submitted)

| split | variant | S | PA | ATR | SR | CF1 | chars |
|---|---|---|---|---|---|---|---|
| dev (112) | v1 | 91.8 | 0.973 | 0.973 | 1.000 | 0.997 | 4387 |
| dev | comb / comb_guard | 92.5 | 0.982 | 0.982 | 1.000 | 1.000 | 4415 |
| dev | **comb_guard_adv** | **93.0** | 0.991 | - | - | 1.000 | - |
| dev200 (22) | v1 = all variants | 93.7 | 1.000 | 1.000 | 1.000 | 1.000 | 4162 |

**Router-selected slices** (`--route`; all question types on the route)

| slice | variant | S | PA | ATR | SR | CF1 | chars | AUC |
|---|---|---|---|---|---|---|---|---|
| ssu-routed dev (140) | v1 | 86.1 | 0.932 | 0.960 | 0.980 | 0.894 | 4159 | 0.931 |
| | comb / comb_guard / v1_guard | 86.1 | 0.932 | 0.960 | 0.980 | 0.894 | 4161 | 0.932 |
| | **comb_guard_adv** | **86.6** | 0.939 | 0.967 | 0.980 | 0.894 | 4184 | 0.932 |
| ssu-routed dev200 (38) | all variants | 82.3 | 0.886 | 0.929 | 0.943 | 0.867 | 4234 | 0.905 |
| multi-routed dev (170) | v1 / v1_guard | 86.3 | 0.936 | 0.972 | 0.984 | 0.903 | 5467 | 0.795 |
| | **comb / comb_guard** | **86.7** | 0.943 | 0.978 | 0.984 | 0.905 | 5481 | 0.800 |
| multi-routed dev200 (45) | all variants | 84.2 | 0.921 | 0.965 | 0.984 | 0.872 | 6061 | 0.789 |

**Routed system, all types** (`runs/r3-ssa-b/all/b_r3_role/`)

| split | variant | S | Sall | PA | CF1 | chars | AUC |
|---|---|---|---|---|---|---|---|
| dev200 (125) | v1 | 84.9 | 83.2 | 0.918 | 0.894 | 5478 | 0.855 |
| dev200 | comb_guard_adv | 84.9 | 83.2 | 0.918 | 0.894 | 5477 | 0.855 |
| dev (526) | v1 | 85.9 | 84.7 | 0.933 | 0.899 | 5587 | 0.810 |
| dev | **comb_guard_adv** | **86.2** | **85.0** | 0.938 | 0.899 | 5599 | 0.811 |

(v1 re-measured at 85.9 here vs 86.0 in SYNTHESIS_r2; the 0.1 drift is in temporal rows, identical in both variants of this run.)

Per-question changes against v1 (`r3_compare.py`). No question loses S.
- dev ssu route:
  - switched to ssa: "Besides 'sexual compulsions' …" and "phone number of the Speyer tourism board" (S 94.3 → 94.2), plus "Which back-end languages should I learn …" (S 29 → 93).
  - guard only: "27th of the 100 prompt parameters", "Seco de Cordero beer", "powwows traditional game", "environmentally responsible supply chains" (the Reactor failure), and the ssu question "How long did it take to move to the new apartment?". That last one keeps its pack and recency line and only loses the ownership sentence.
- dev multi route: "DHL Wellness Retreats … influencer marketing", S 19 → 93.2.
- dev200: guard only, on "Speyer" and "new apartment".

### Test audit (no gold)
`harness.audit --compare runs/final/v1_test_packs.jsonl`:
- ssu: **0 of 45** packs change for both `comb_guard` and `comb_guard_adv`.
- multi: **0 of 20** change.
- ssa: **0 of 25** change.
- ku and temporal are not touched by construction.

Why nothing moves: the highest `p_assistant` on test is 0.33 on the ssu route and 0.28 on the multi route. Every ssu- and multi-routed test question contains I / my / our, so the guard is gated off, and none says "should I". The one flag is the pre-existing v1 multi flag (feijoada, abstain_p 0.54).

Test packs this change modifies: **none**. I checked the ssa packs qualitatively:
- Lisbon coworking (q_a13386c9d560): the pack holds "Heden in Baixa has a good day pass" without the word coworking, and there is no quote line. It is a plausible answer, and I made no per-question fix.
- Speedwork coach (q_bad53f86da03): no quote line, but the pack holds "I recommend Coach Miriam at the Toronto Lakeshore Running Club".

## Top failure patterns
1. **Role hint contradicts the evidence (Reactor-visible, proxy-invisible).** A ssa question on the ssu route keeps PA = 1, but it gets "answer from what the user said about their own X". Examples:
   - q_73a1f68b2421 supply chains: real Reactor abstained.
   - "Which beer goes in the Seco de Cordero from Ancash?" (p 0.70).
   - "Which traditional game is often performed by skilled dancers at powwows?" (p 0.77).

   The guard fixes all three on dev. It cannot reach ssa questions phrased with "my" ("What designation on my jumpsuit led me to the file number …", p 0.41).
2. **The cross-encoder margin is blind when the answer echoes the user's words, or when the answer is user-role.**
   - "Besides 'sexual compulsions', what were the other four alternative terms?": the user quotes the term, so d = −0.3. A's lexical scan sees the terms in assistant turns (pA 0.87), and the combined score catches it.
   - "Who was the President's Chief Advisor … in the article on the Lawrence Livermore fusion breakthrough?": the user pasted the article, so d = −5.0. No role feature can catch this, and the ssu lens misses the turn (S 28.7).
   - "Which show was my example of Netflix …": user-role, on the temporal route.
3. **Thin margin at the nearest ssu question.** "How long did it take to move to the new apartment?" has no first-person word. It is the closest negative for every detector: combined z 0.85 on dev and 0.65 on dev200, against the switch threshold of 1.39. That is why it gets the guard rather than a switch. A's `a_r3_role` places its nf0 switch at d ≥ −0.73 against this question's d = −1.04, and A's s55 variant, which switched it, lost on dev200.

## Overlap with lens A (round 3)
A's `a_r3_role.py` reaches the same diagnosis, citing the same Reactor question. Its `role_guess = max(p_b, p_fit)` switches more nf0 questions to the ssa lens: routed dev 86.0 → 86.3, gold ssa 91.8 → 93.0, test 0 changes. My version switches fewer at a wider margin and covers the remainder with the hint guard instead of a lens change. A's nh55 variant is the same guard idea.

The two are interchangeable on test, since neither changes any pack, and they tie on routed dev (A 86.3 against v1 86.0 in A's run; mine 86.2 against v1 85.9 in this run). Suggested integration (pick one):
- (i) Mine: `routes.ssu = {"lens": "lenses/ssa/b_r3_role.py", "variant": "comb_guard_adv"}` and `routes.multi.params = {"role_module": "lenses/ssa/b_r3_role.py"}`.
- (ii) A's switch with my guard: the same `routes.ssu`, plus `"params": {"role_module": "lenses/ssa/a_r3_role.py"}` (the guard reads `p_assistant` from the wrapper's debug, so it then uses A's p), and `routes.multi.params.role_module = "lenses/ssa/a_r3_role.py"`. Not swept by me.

`b_r3_role.build` calls the frozen `merged_r2` route lenses directly, so it can sit on the ssu route without recursion.

## CORE REQUESTs
1. **Wire the ssu-route guard.** Route `ssu` → `lenses/ssa/b_r3_role.py comb_guard_adv`, and route `multi` → `merged_r2 tight_role9` with `params.role_module = "lenses/ssa/b_r3_role.py"`. Test diff: 0 packs.
2. **Reactor check of the guard:** re-run q_73a1f68b2421 (dev) with the guarded pack in the next calibration batch. It is the only Reactor-measured case.
3. (Optional, router) "my example of / the example I gave" → ssa. It affects 1 dev question, which v1 already answers via temporal. Low priority.
4. (Harness) A "hint conflict" audit flag: an ssu-route pack whose best cross-encoder unit is an assistant unit while the hint says "what the user said". Proxy PA cannot see this failure.

## Ideas for next round
- A user-role ssa detector (the user pasted an article or gave an example): the question names a document ("in the article", "the script", "my example of") and the best unit is a long user turn. It needs more than the 2 dev positives available.
- A semantic quote fallback for the ssa hint when no sentence has a lexical category match (Lisbon / Heden-style paraphrase). Score first-person recommendation sentences in the chosen session with `hx.rerank_texts` against the question's purpose phrase. dev has no "you recommended" questions, so it can only be validated on a synthetic dev set.
- Calibrate `p_assistant` jointly with the ku detector, so that one detector decides ssa / ku / ssu on the ssu route.
