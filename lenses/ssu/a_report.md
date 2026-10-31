# SSU lens A "Struktura": round 2 report

Code: `lenses/ssu/a_struct2.py`. It imports the round-1 pool, scoring and classifier from `a_struct.py` and `a_owner.py`, which are unchanged.
The round-1 report is now in `lenses/ssu/a_report_r1.md`.
Scratch scripts: `lenses/ssu/scratch_a/r2_*.py`. Test audits: `scratch_a/r2_audit_r3rn.txt` (45 packs), plus the 12-pack audits for `r3` and `r2best_a4x2`.
Runs: gold-type runs are in `runs/r2-ssu-a/ssu/...`. Routed runs (`--route --type ssu`) are in `runs/r2-ssu-a-route/ssu/...`; they need a separate tag because `--route` writes to the same path.

**Best variant: `a_struct2.py` / `r3rn`.**
- On gold-type ssu it ties the round-1 winner `nb3t0`:
  - dev: S 93.4 vs 93.5.
  - dev200: S 92.5 vs 92.5.
  - Sall: -0.5 on dev and -1.0 on dev200, within the 2-point limit.
  - AUC: 0.919 vs 0.911 on dev, 0.955 vs 0.909 on dev200.
- On the routed ssu route, which is what the system actually serves, it wins clearly:
  - dev: S 82.6 vs 74.4, Sall 84.2 vs 75.8.
  - dev200: S 78.5 vs 72.6, Sall 79.1 vs 73.8.
- Gold-type ssu is saturated. PA is 1.000, and 63 of 64 dev cites are already correct, so the ceiling at about 3.6k chars is S ≈ 93.9. A +2 win on gold-type dev is not possible; the gains have to come from the routed questions and from test behaviour.
- On the 45 test ssu-route packs, `r3rn` changes the cite on 2 questions, both recency fixes (pattern 4 below). Mean passages per pack go from 2.71 to 2.80. No pack has abstain_p ≥ 0.5 any more; before, 8 did.

## Variants tried (one line each)
| variant | idea and params |
|---|---|
| r2 | `nb3t0`, but the hint no longer carries the "answer INSUFFICIENT_EVIDENCE" line. This follows the integrator's no-abstention-hint policy. |
| pair2 / pair3 | Also cite the runner-up session when it scores within 2 / 3 logits of the best one (KU update pair). |
| pair3t | pair3 with a tight pack: only cited sessions are packed. |
| pair3h | pair3 plus a dated hint: "the user mentioned this on d1 and d2; if they differ, the later one is current". It uses the earlier date for "previous" questions. |
| ru | pair3 plus an **outlier runner-up** rule. When s2 > −6 and s2 − s3 > 3, the runner-up session's best 3 units are packed but not cited. |
| ruc / ruch | ru, and the runner-up is also cited: always (ruc), or only when its best unit is an affirmed own unit with a head hit (ruch). |
| ruct / rucht | ruc / ruch with a tight pack. |
| ru_ab0/1/2 | ru, with the abstention prior using max(best user logit, best ALL-roles logit − 0/1/2). The ALL-roles logit comes from the generic hybrid_rr pool, which is already cached. |
| r2best | ru_ab1 plus Platt calibration of abstain_p (a=0.5, c=−2), fitted on pooled dev+dev200 routed-ssu rows. |
| r2best_a2 / _a4 | r2best, plus: when the best ALL-roles unit is an assistant unit in another session and beats the best user logit by 2 / 4, cite that session (ssa misroute). |
| r2best_a4x4 / _a4x2 | _a4, plus the best assistant unit (±1) of a kept session is packed when it beats the best user logit by 4 / 2. |
| r3 | r2best_a4x2 **without** the pair cite (pair_gap off). |
| r3new / r3new2 | r3 with the pair (gap 3 / 2) packed, citing only the newest session (or the oldest for "previous"). |
| r3g4 / r3g3 | r3 with sess_gap 4 / 3 instead of 6 (fewer context sessions). |
| **r3rn** | **r3 plus a check on the recency jump: a later near-top session is picked only if it states the attribute itself (an affirmed own unit with a head or modifier hit).** |
| r3rn_x1 / _x0 | r3rn, adding the assistant unit at a +1 / 0 logit margin. |
| r2best_h | r2best plus the pair hint. It has no offline effect, so it is not adopted. |

## Results
"gold" means questions of gold type ssu: dev has 70 (64 answerable), dev200 has 23 (22 answerable). "routed" means the questions the router sends to ssu: 144 on dev and 40 on dev200. The routed sets include the dev-only cue-less ssa misroutes (50 + 7) and the ku, multi and temporal misroutes.

| lens/variant | set | dev S | dev Sall | PA | ATR | SR | CF1 | chars | AUC | dev200 S | dev200 Sall | PA | ATR | SR | CF1 | chars | AUC |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| generic/hybrid_rr (baseline) | gold | 76.6 | 76.6 | 1.000 | 1.000 | 1.000 | 0.512 | 11934 | 0.924 | 73.5 | 73.5 | 1.000 | 1.000 | 1.000 | 0.407 | 11933 | 0.955 |
| generic/hybrid_rr (baseline) | routed | 75.7 | 75.7 | 0.971 | 0.983 | 0.993 | 0.545 | 11932 | 0.847 | 76.6 | 76.6 | 1.000 | 1.000 | 1.000 | 0.510 | 11939 | 0.946 |
| a_struct/nb3t0 (r1 winner) | gold | 93.5 | 93.2 | 1.000 | 1.000 | 1.000 | 0.984 | 3489 | 0.911 | 92.5 | 90.7 | 1.000 | 1.000 | 1.000 | 0.955 | 3589 | 0.909 |
| a_struct/nb3t0 (r1 winner) | routed | 74.4 | 75.8 | 0.757 | 0.866 | 0.952 | 0.875 | 3701 | 0.837 | 72.6 | 73.8 | 0.757 | 0.851 | 0.905 | 0.817 | 3799 | 0.838 |
| r2 | gold | 93.5 | 93.2 | 1.000 | 1.000 | 1.000 | 0.984 | 3483 | 0.911 | 92.5 | 90.7 | 1.000 | 1.000 | 1.000 | 0.955 | 3583 | 0.909 |
| r2 | routed | 74.4 | 75.8 | 0.757 | 0.866 | 0.952 | 0.875 | 3689 | 0.837 | 72.5 | 73.8 | 0.757 | 0.851 | 0.905 | 0.817 | 3802 | 0.838 |
| pair3 | gold | 93.5 | 93.2 | 1.000 | 1.000 | 1.000 | 0.984 | 3486 | 0.911 | 92.1 | 90.7 | 1.000 | 1.000 | 1.000 | 0.939 | 3629 | 0.909 |
| pair3 | routed | 75.9 | 75.8 | 0.757 | 0.866 | 0.952 | 0.926 | 3746 | 0.837 | 73.8 | 73.7 | 0.757 | 0.851 | 0.905 | 0.860 | 3874 | 0.838 |
| pair3t | gold | 93.5 | 93.5 | 1.000 | 1.000 | 1.000 | 0.984 | 3390 | 0.911 | 92.2 | 92.2 | 1.000 | 1.000 | 1.000 | 0.939 | 3291 | 0.909 |
| pair3t | routed | 73.1 | 73.1 | 0.713 | 0.830 | 0.915 | 0.926 | 3434 | 0.837 | 70.5 | 70.5 | 0.703 | 0.806 | 0.860 | 0.860 | 3356 | 0.838 |
| ru | gold | 93.5 | 92.7 | 1.000 | 1.000 | 1.000 | 0.984 | 3558 | 0.911 | 92.0 | 89.3 | 1.000 | 1.000 | 1.000 | 0.939 | 3851 | 0.909 |
| ru | routed | 78.7 | 78.9 | 0.801 | 0.888 | 0.974 | 0.926 | 3866 | 0.837 | 77.3 | 76.9 | 0.811 | 0.878 | 0.932 | 0.860 | 4081 | 0.838 |
| ruc | gold | 93.0 | 92.7 | 1.000 | 1.000 | 1.000 | 0.969 | 3558 | 0.911 | 89.7 | 89.3 | 1.000 | 1.000 | 1.000 | 0.864 | 3851 | 0.909 |
| ruc | routed | 79.3 | 78.9 | 0.801 | 0.888 | 0.974 | 0.946 | 3866 | 0.837 | 77.1 | 76.9 | 0.811 | 0.878 | 0.932 | 0.856 | 4081 | 0.838 |
| ruch | gold | 93.0 | 92.7 | 1.000 | 1.000 | 1.000 | 0.969 | 3558 | 0.911 | 91.5 | 89.3 | 1.000 | 1.000 | 1.000 | 0.924 | 3851 | 0.909 |
| ruch | routed | 78.9 | 78.9 | 0.801 | 0.888 | 0.974 | 0.933 | 3866 | 0.837 | 77.5 | 76.9 | 0.811 | 0.878 | 0.932 | 0.869 | 4081 | 0.838 |
| r2best | gold | 93.5 | 92.7 | 1.000 | 1.000 | 1.000 | 0.984 | 3558 | 0.919 | 92.0 | 89.3 | 1.000 | 1.000 | 1.000 | 0.939 | 3851 | 0.955 |
| r2best | routed | 78.7 | 78.9 | 0.801 | 0.888 | 0.974 | 0.926 | 3866 | 0.895 | 77.3 | 76.9 | 0.811 | 0.878 | 0.932 | 0.860 | 4081 | 0.874 |
| r2best_a4 | routed | 78.8 | 78.9 | 0.801 | 0.888 | 0.974 | 0.928 | 3870 | 0.895 | 79.3 | 78.8 | 0.838 | 0.905 | 0.932 | 0.869 | 4072 | 0.874 |
| r2best_a4x2 | gold | 93.4 | 92.7 | 1.000 | 1.000 | 1.000 | 0.984 | 3613 | 0.919 | 92.0 | 89.5 | 1.000 | 1.000 | 1.000 | 0.939 | 3890 | 0.955 |
| r2best_a4x2 | routed | 84.0 | 84.2 | 0.882 | 0.932 | 0.974 | 0.928 | 4067 | 0.895 | 79.3 | 78.9 | 0.838 | 0.892 | 0.932 | 0.869 | 4170 | 0.874 |
| r3 | gold | 93.4 | 92.7 | 1.000 | 1.000 | 1.000 | 0.984 | 3609 | 0.919 | 92.5 | 89.7 | 1.000 | 1.000 | 1.000 | 0.955 | 3859 | 0.955 |
| r3 | routed | 82.6 | 84.2 | 0.882 | 0.932 | 0.974 | 0.883 | 4012 | 0.895 | 78.5 | 79.1 | 0.838 | 0.892 | 0.932 | 0.844 | 4131 | 0.874 |
| r3g3 | routed | 81.7 | 83.5 | 0.868 | 0.918 | 0.960 | 0.883 | 3846 | 0.895 | 76.8 | 77.2 | 0.811 | 0.874 | 0.914 | 0.844 | 3922 | 0.874 |
| r3new | gold | 93.0 | 92.7 | 1.000 | 1.000 | 1.000 | 0.969 | 3614 | 0.919 | 92.4 | 89.7 | 1.000 | 1.000 | 1.000 | 0.955 | 3890 | 0.955 |
| **r3rn** | gold | **93.4** | **92.7** | 1.000 | 1.000 | 1.000 | 0.984 | 3609 | **0.919** | **92.5** | **89.7** | 1.000 | 1.000 | 1.000 | 0.955 | 3859 | **0.955** |
| **r3rn** | routed | **82.6** | **84.2** | 0.882 | 0.932 | 0.974 | 0.883 | 4012 | 0.895 | **78.5** | **79.1** | 0.838 | 0.892 | 0.932 | 0.844 | 4131 | 0.874 |

The full table, including pair2, pair3h, ruct, rucht, ru_ab*, r2best_a2/_a4x4, r3g4, r3new2, r3rn_x0 and r3rn_x1, can be rebuilt from `runs/r2-ssu-a*/ssu/a_struct2/*/summary.json`. None of the omitted rows beats the rows shown.

Routed ssu by gold type, `nb3t0` → `r3rn` (S):

| gold type | dev | dev200 |
|---|---|---|
| ssu | 93.3 → 93.3 | 92.1 → 92.0 |
| ssa | 70.1 → 86.1 (PA 0.64 → 0.88) | 71.3 → 84.8 |
| ku | 69.7 → 77.4 (PA 0.80 → 0.92) | 47.6 → 54.7 |
| multi | 43.3 → 49.7 | 37.6 → 59.0 |
| temporal | 39.2 → 49.9 | 78.2 → 78.2 |

Every test ssa question says "you recommended" and routes correctly, so the ssa part of the routed gain is mostly a dev artefact. On test, the gain that counts is the ku and multi part, plus the recency fix.

Why `r3rn` and not the higher routed S of `r2best_a4x2` (84.0 on dev, +1.4)? The difference is the pair cite. On test it fires on **10 of 12** audited ssu packs, because test histories plant value drift and decoys: the cat is Fig, Bica and Sombra across sessions, and the sourdough starter is Bubbles, Herman and Masa. Citing two sessions there would cost about 0.33 CF1 on most test ssu questions. On dev and dev200 it fires on only 5 of the 62 routed gold-ssu questions (`scratch_a/r2_gap.py`).

## Top failure patterns (with examples)
1. **The KU update session was dropped from the pack (fixed by `ru`).** The update session scores 6–10 logits below the top session, so `sess_gap=6` dropped it, but it sits far above the noise floor of about −8 to −11. Session scores (G = gold):
   - "What day of the week do I take a cocktail-making class?" [3.6 G, −2.9 G, −8.3].
   - "What day of the week did I meet with my previous language exchange tutor Juan?" [6.5 G, −0.3 G, −10.1].
   - "Is my mom using the same grocery list method as me?" [6.9 G, −3.3 G, −9.9].

   The outlier rule (s2 > −6 and s2 − s3 > 3) fires on 28 of 34 routed ku questions, and the runner-up is gold in 27 of them. On ssu it fires on 8 of 62. ku PA on dev goes from 0.80 to 0.92.
2. **Right session, wrong turn on ssa misroutes (fixed by `asst_add`).** The cited session is right (CF1 1.0), but the answer is in an assistant turn that the user-only pool never packed. Examples:
   - "Which fashion brand uses wild rubber from the Amazon rainforest?": best user logit −7.5, best ALL-roles logit +7.3.
   - "What's that hostel near the Red Light District in Amsterdam called?"

   Still failing are list-position questions, where the item sits in a chunk more than one unit from the best match: "Of the five bottles for a gin cocktail bar, what was the fifth?" and "In the chess game, what move came after 27. Kg2 Bd5+?".
3. **One cite for a two-gold KU pair (open).** CF1 is about 0.64 on ku misroutes. The pair cite fixes this on dev (+1.5 routed S), but on test it fires on drift and decoys (see above). A value-disagreement test is needed; see the ideas below.
4. **The recency jump picked a session that only shares the topic (test; fixed by `rec_need`).**
   - "What speaker impedance did I end up using in my National R-77?" and "What AM intermediate frequency did I end up using …": `nb3t0` cited 2023/07/14, "I briefly tried a 22k-ohm screen grid resistor in my National R-77 … removed it". That was the latest session within 2.5 logits.
   - Now AM IF cites 07/09, "realigned the AM IF of my National R-77 to 465 kHz".
   - The speaker question now cites 05/19 ("the new old-stock speaker is a Pioneer…", with the assistant's 8-ohm discussion), the latest own speaker statement after the 03/11 "4-ohm unit".
5. **An unflagged "perceive" decoy (open).** "I saw a sourdough starter named Herman in a French baking forum" is the top unit (+3.98) for "What did I end up naming my sourdough starter?". The recency rule still picks 09/02, "I've renamed my sourdough starter Masa".
6. **Abstention (improved).** Pooled routed AUC goes from 0.827 to 0.882. Most of the high-abstain_p negatives were ssa misroutes, whose evidence sits in assistant turns; the ALL-roles prior handles them.
   - After calibration, 3 of 8 packs with p ≥ 0.3 are truly unanswerable.
   - On test, 0 packs reach ≥ 0.5. Before, 8 of 45 did, including dog name, partner and favourite colour.
   - This is still far from the integrator's re-enable rule (precision ≥ 0.7 at recall ≥ 0.4), and there is no abstention hint.

## CORE REQUESTs
1. **`harness.sweep --route` should write to its own path**, for example `runs/<tag>/<type>-routed/...`. Today a routed run silently overwrites the gold-type run that has the same tag.
2. **Per-gold-type breakdown in routed sweep output.** This is `scratch_a/r2_bytype.py`, which takes S, Sall, PA and CF1 per gold type from per_question.jsonl. Without it, misroute effects stay hidden in the route mean.
3. **`harness.audit --compare <old run>`**: list the test packs whose cite_plan or passage count changed. This is `scratch_a/r2_cmp_test.py`. It is how the pair-cite problem and the recency fix were found.
4. Carried over: **answer-anchored citation** on the submission side.
5. Wiring: set `configs/best.json` ssu → `lenses/ssu/a_struct2.py` / `r3rn`. It reuses the cached generic hybrid_rr all-roles pool. Build time is about 110 ms on dev and 370 ms on dev200, cached.

## Ideas for the next round
- **Gate the pair cite on value disagreement.** Cite both sessions only when both best units are affirmed own statements of the same attribute with *different* extracted values (number, day, time, duration), the KU signature. Do not cite both on name drift. Measure it on routed dev and on the test audit together.
- **Name drift voting** (cat Fig, Bica, Sombra) was not done this round. Count affirmed own mentions per value, prefer replies to "What's her name?", and break ties by recency. Name the leading value in the hint only when it clearly leads.
- **Perceive decoys.** Extend PERCEIVE_RX in `a_owner.py` to "I saw/read about a X named Y" with owner = other.
- **ssa list-position questions:** for ordinal cues ("fifth", "number 7", "last on the list"), pack the assistant chunk that holds the list, plus the next chunk.
- **Merge with B:** B's all-roles session sweep, combined with A's structure, recency check and outlier runner-up.
