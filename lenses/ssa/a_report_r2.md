# SSA lens A ("Struktura"), round 2 report

Files:
- `lenses/ssa/a_recsent.py`. **Best variant: `r2_conf2`.** New functions: `role_features` / `role_guess`.
- `lenses/ssa/a_handoff.py`. New: an evidence-based hand-off for the **ssu route**, variant `nf50a`.
- `lenses/ssa/a_routed.py` is a measurement wrapper around `lenses/pipeline.py` with a proposal config at `lenses/ssa/scratch_a/routed_r2a.json`.
- Scratch: `scratch_a/turn_rank.py` (budget vs gold-turn coverage per within-session ordering), `margin_eval.py`, `agree_eval.py`, `role_eval.py` and `route_sim.py`.
- Runs: tags `r2-ssa-a`, `r2-ssa-a-route` and `r2-ssa-a-routed`.

## TL;DR
1. **The ssa route is saturated.** PA = CF1 = 1.0 on both splits. The only levers left are chars and Sall. `r2_conf2` keeps PA 1.0 and moves dev from 93.3 to 93.6 (Sall 92.6 → 93.6) and dev200 from 93.3 to 93.7 (Sall 92.9 → 93.7), with chars at 5.6k → 4.5k and 5.4k → 4.2k. That is below the 2-point bar, but it wins the tie rule (fewer chars), and it gains about +1 on Sall because the pack is now exactly the cite set.
2. **The bigger win is on the ssu route (brief item 3).** On dev, 50 gold-ssa questions without a cue are routed to ssu, where they score S 70. `a_handoff.py nf50a` sends a question to the ssa lens when `role_guess >= 0.5` and the question has no first-person word ("should I …" advice questions are exempt). Over all ssu-routed questions this gives:
   - dev: 74.4 → **82.4** (Sall 75.8 → 84.2, AUC 0.837 → 0.931);
   - dev200: 72.6 → **75.9** (Sall 73.8 → 77.3, AUC 0.838 → 0.892);
   - **test: 0 of 45 ssu-routed questions change** (all say I/my/our), so the change is test-neutral by construction.
3. **Routed system** (both changes on configs/best.json):
   - dev: 80.4 → **82.6** (Sall 74.9 → 77.3, AUC 0.719 → 0.749);
   - dev200: 79.8 → **81.0** (Sall 74.2 → 75.5, AUC 0.810 → 0.820).

(The round-1 report that was in this file is summarised in runs/SYNTHESIS_r1.md, and its runs are under tag `r1-ssa-a`.)

## Variants tried (one line each)
| variant | idea and params |
|---|---|
| `recqs_cf7` | Round-1 winner, re-run for Sall: BM25 + role-BM25 + structural scan, best turn whole + rest of the session, budget 7000, runner-up session when the score is within 0.85x. |
| `r2_solo` | `tie=1.01`: no runner-up session, so the pack equals the cite set (CF1all = 1). PA is unchanged on both splits. On test only the Lisbon pack changes: the decoy runner-up session is dropped. |
| `r2_b6` | Budget 6000. `turn_rank.py` shows the lens order still covers 100% of gold turns at 6k. Runner-up kept. |
| `r2_solo_b6` | solo + 6000. |
| `r2_conf` | solo + 6000, and budget 3500 when the best turn is clearly ahead inside its session (turn_margin ≥ 1.3). turn_margin = fused score of the best unit / best unit of any other turn of that session. At 1.3 the best turn is the gold turn 16/16 on dev and 4/4 on dev200. |
| **`r2_conf2`** | Tiers: margin ≥ 1.3 → 3000, ≥ 1.2 → 4500, else 6000 (+ solo, + kind gate). **Best.** |
| `r2_conf3` | Tiers: ≥ 1.3 → 2500, ≥ 1.2 → 4000, ≥ 1.1 → 5000. Too tight: long gold turns get cut (AC 0.96), and PA drops to 0.964 / 0.909. Rejected. |
| `r2_s55` | solo + flat 5500. Loses 2 dev questions (PA 0.982). Rejected. A flat cut is worse than a confidence-gated one. |
| `kind_gate` (in all r2_*) | abstain_p on rec-style questions is capped at 0.35 when the asked category (head noun or a synonym) appears in the top session's assistant text (brief item 2). Changes abstain_p only. |
| `a_handoff nf50` | ssu route: hand off to `a_recsent recqs_cf7` when p_assistant ≥ 0.5 and the question has no I/my/me/our. |
| **`a_handoff nf50a`** | nf50, and "should I / do I need to" questions count as advice requests (first person allowed). **Recommended for the ssu route.** |
| `a_handoff nf50a_c2` | nf50a handing off to `r2_conf2` instead. Fewer chars, but less robust when the hand-off is wrong. On dev200 the ssu question "How long did it take to move to the new apartment?" loses its user turn to the tighter budget (PA 1 → 0). Use `recqs_cf7` (or `r2_solo`) as the hand-off target. |

Dropped without a sweep:
- **Cross-encoder turn ordering** (`turn_rank.py`). turn@1 is better (0.75 vs 0.66 on dev), but coverage at a given budget is worse than the lens order: at 6k, 0.95 vs 1.00.
- **CE-agreement as a confidence signal** (`agree_eval.py`). When the CE top turn equals the lens best turn, the best turn is the gold turn only 84% of the time on dev (69/82), against 16/16 for margin ≥ 1.3.

## Results: ssa gold type (harness.sweep, tag `r2-ssa-a`; dev and dev200 contain no unanswerable ssa questions, so AUC is "-")
| split | variant | S | Sall | PA | ATR | SR | CF1 | CF1all | chars | AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| dev (112) | generic `hybrid_rr` (baseline) | 72.3 | 72.3 | 1.000 | 1.000 | 1.000 | 0.368 | 0.368 | 11932 | - |
| dev | `recqs_cf7` (r1 best) | 93.3 | 92.6 | 1.000 | 1.000 | 1.000 | 1.000 | 0.979 | 5587 | - |
| dev | `r2_solo` | 93.3 | 93.3 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 5382 | - |
| dev | `r2_b6` | 93.4 | 92.8 | 1.000 | 1.000 | 1.000 | 1.000 | 0.979 | 5131 | - |
| dev | `r2_solo_b6` | 93.4 | 93.4 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 4979 | - |
| dev | `r2_conf` | 93.5 | 93.5 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 4755 | - |
| dev | **`r2_conf2`** | **93.6** | **93.6** | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | **4542** | - |
| dev | `r2_conf3` | 91.3 | 91.3 | 0.964 | 0.991 | 1.000 | 1.000 | 1.000 | 4275 | - |
| dev | `r2_s55` | 92.4 | 92.4 | 0.982 | 0.982 | 1.000 | 1.000 | 1.000 | 4711 | - |
| dev200 (22) | generic `hybrid_rr` (baseline) | 71.2 | 71.2 | 1.000 | 1.000 | 1.000 | 0.331 | 0.331 | 11938 | - |
| dev200 | `recqs_cf7` (r1 best) | 93.3 | 92.9 | 1.000 | 1.000 | 1.000 | 1.000 | 0.985 | 5376 | - |
| dev200 | `r2_solo` | 93.4 | 93.4 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 5248 | - |
| dev200 | `r2_b6` | 93.5 | 93.0 | 1.000 | 1.000 | 1.000 | 1.000 | 0.985 | 4867 | - |
| dev200 | `r2_solo_b6` | 93.5 | 93.5 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 4786 | - |
| dev200 | `r2_conf` | 93.6 | 93.6 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 4493 | - |
| dev200 | **`r2_conf2`** | **93.7** | **93.7** | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | **4186** | - |
| dev200 | `r2_conf3` | 87.9 | 87.9 | 0.909 | 0.955 | 1.000 | 1.000 | 1.000 | 3836 | - |
| dev200 | `r2_s55` | 93.6 | 93.6 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 4556 | - |

S ceiling at PA = CF1 = 1 is 95 − chars/3200. Going from 5.6k to 4.5k chars is worth +0.35, and dropping the runner-up is worth about +0.7 on Sall. A +2 S gain is impossible on this type.
`r2_conf2` vs `recqs_cf7`: S +0.3 dev / +0.4 dev200, Sall +1.0 / +0.8, chars −19% / −22%, no PA loss.

Test audit (`harness.audit --variant r2_conf2 --n 25`): **0 flags out of 25**. Every pack is a single session of 2.2 to 3.4k chars. Against `r2_solo`, only 5 packs change, each losing 300–400 chars of trailing chit-chat. The recommendation sentence stays in every pack. Against `recqs_cf7`, the only session-level change is Lisbon/Heden, where the runner-up (decoy) session is gone. abstain_p on test: 22 × 0.05 and 3 × 0.35.

## Results: the ssu route (`--route --type ssu`, tag `r2-ssa-a-route`; questions the text router sends to ssu, all gold types)
| split | variant | S | Sall | PA | ATR | SR | CF1 | chars | AUC |
|---|---|---|---|---|---|---|---|---|---|
| dev (144 q, 136 answerable) | ssu winner `a_struct nb3t0` (= `a_handoff ssu_only`) | 74.4 | 75.8 | 0.757 | 0.866 | 0.952 | 0.875 | 3701 | 0.837 |
| dev | `a_recsent recqs_cf7` on everything | 77.9 | 79.2 | 0.831 | 0.892 | 0.918 | 0.863 | 6395 | 0.562 |
| dev | `a_handoff nf50` | 81.3 | 83.2 | 0.868 | 0.932 | 0.952 | 0.875 | 4454 | 0.921 |
| dev | **`a_handoff nf50a`** | **82.4** | **84.2** | 0.882 | 0.947 | 0.952 | 0.883 | 4502 | **0.931** |
| dev | `a_handoff nf50a_c2` | 82.5 | 84.5 | 0.882 | 0.947 | 0.952 | 0.883 | 4195 | 0.931 |
| dev200 (40 q, 37 answerable) | ssu winner `nb3t0` | 72.6 | 73.8 | 0.757 | 0.851 | 0.905 | 0.817 | 3799 | 0.838 |
| dev200 | `a_recsent recqs_cf7` on everything | 74.3 | 76.6 | 0.811 | 0.833 | 0.901 | 0.788 | 6489 | 0.500 |
| dev200 | `a_handoff nf50` | 75.9 | 77.3 | 0.811 | 0.905 | 0.905 | 0.817 | 4221 | 0.892 |
| dev200 | **`a_handoff nf50a`** | **75.9** | **77.3** | 0.811 | 0.905 | 0.905 | 0.817 | 4221 | **0.892** |
| dev200 | `a_handoff nf50a_c2` | 74.2 | 75.0 | 0.784 | 0.878 | 0.878 | 0.817 | 4016 | 0.892 |

Per gold type, dev (ssu lens → nf50a): ssa 70.1 → 88.9 (50 q); ssu 93.3 → 93.3; ku, multi and temporal unchanged. **No loss on any non-ssa question on dev.** On dev200 there is one loss: an ssu question, "How long did it take to move to the new apartment?", which has no first-person word. AUC rises because the ssu lens gave high abstain_p to answerable ssa questions, and those now go to the ssa lens. No unanswerable question is handed off (dev 0/8, dev200 0/3).

`role_guess` quality: AUC for gold ssa vs every other type, over ssu-routed questions:

| feature | dev | dev200 |
|---|---|---|
| `p_assistant` (combined) | 0.925 | 0.909 |
| `q_nofirst` (no I/my/me in the question) | 0.916 | 0.985 |
| BM25 assistant-vs-user top score | 0.826 | 0.779 |
| CE assistant-vs-user (`use_ce=True`) | 0.867 | - |

The CE does not improve the combination (0.922), so the default is lexical only. The no-first-person gate turns the probability into a test-safe rule.

### Routed system, all types (`lenses/ssa/a_routed.py`, tag `r2-ssa-a-routed`)
`best` = configs/best.json. `r2a` = the same config with two changes: ssu route → `a_handoff nf50a`, ssa route → `a_recsent r2_conf2`.

| split | config | S | Sall | PA | ATR | CF1 | CF1all | chars | AUC |
|---|---|---|---|---|---|---|---|---|---|
| dev (526) | best | 80.4 | 74.9 | 0.867 | 0.930 | 0.877 | 0.694 | 7375 | 0.719 |
| dev | **r2a** | **82.6** | **77.3** | 0.901 | 0.952 | 0.879 | 0.702 | 7476 | 0.749 |
| dev200 (125) | best | 79.8 | 74.2 | 0.864 | 0.915 | 0.862 | 0.674 | 7206 | 0.810 |
| dev200 | **r2a** | **81.0** | **75.5** | 0.882 | 0.933 | 0.862 | 0.679 | 7166 | 0.820 |

The change is +2.2 S on dev and +1.2 on dev200, with Sall up 2.4 and 1.3 and AUC up as well. It passes the ≥ 2 dev / no dev200 loss rule. On test, `r2a` changes 0 ssu packs; on the ssa route, 5 packs lose 300–400 chars of chit-chat and Lisbon drops its decoy runner-up session.

## Top failure patterns
1. **The best turn is not the gold turn (about 1/3 of dev).** This is still the limit on chars. With a flat budget, any cut below 6k loses gold turns:
   - `r2_s55` loses 2 dev questions;
   - `r2_conf3` cuts long gold turns mid-way (AC 0.957), as in "What was the 27th of the 100 prompt parameters?", where the list item sits deep in a 5k turn.

   Only the margin-gated tiers are safe. Examples where the best turn is not the gold turn: Bandung Nasi Goreng (gold 4 turns before the best), tea tree oil ratio (+8), Radiation Amplified zombie (+5).
2. **Wrong hand-offs are user facts phrased impersonally.** "How long did it take to move to the new apartment?" (ssu, p_assistant 0.67, no I/my) is the one loss on dev200. With the tighter `r2_conf2` budget the user turn falls out of the pack, which is why the hand-off target should be the session-filling `recqs_cf7`.
3. **ssa questions that keep a first-person word stay with the ssu lens.** "Which show was my example of Netflix …" is a user-role ssa question routed to temporal. "Who was the President's Chief Advisor … fusion breakthrough?" scores p_assistant 0.49, just under the threshold. The ssu lens finds the session but not the turn (PA 0, the only remaining ssa PA miss on the ssu route).

## abstain_p
dev and dev200 have no unanswerable question on the ssa route, so calibration on this route is not measurable. The routed-to-ssa set is 100% answerable on both splits. The kind gate moves 6 answerable dev questions from 0.6–0.7 down to 0.35 (dev distribution: 99 × 0.05, 1 × 0.3, 7 × 0.35, 1 × 0.6, 4 × 0.7). Nothing above 0.7 remains on dev, dev200 or test. Recommended reading for the integrator: on the ssa route, abstain_p ≥ 0.7 means "the recommendation shape and the category are both missing". It has never fired on an unanswerable question, because there are none. Keep the no-hint policy.

## CORE REQUESTs
1. **Put `lenses/ssa/a_handoff.py nf50a` on the ssu route** (configs/best.json, integrator-owned). Its `ssu_lens` / `ssu_variant` parameters default to the current ssu winner, so whatever wins ssu-A/B this round can be plugged in. Test-neutral: 0 of 45 test ssu-routed questions are handed off. A cleaner alternative is a `role_guess` hook in `lenses/pipeline.py`: `if route == "ssu" and handoff(q, hx): route = "ssa"`.
2. **ssa route → `a_recsent r2_conf2`.**
3. `harness.sweep`: print `chars` in summary.json under the same key as the leaderboard (`chars_mean`). summary.json has no `chars` key today.
4. The round-1 request for `core.units` sentence splitting at "Dr." / "St." was declined. Still fine: the lens re-joins sentences itself.

## Ideas for the next round
- Calibrate role_guess with a logistic fit on dev and validate on dev200. It is hand-weighted now. Add an "impersonal user fact" feature (definite article plus a personal-life noun: "the new apartment", "the move") to stop the one wrong hand-off.
- Hand off from temporal and multi too: "Which show was my example …" (ssa → temporal) and "How many mummies …" (ssa → multi). It needs a per-route rule; the cost of a wrong move is high on multi.
- Turn ranking: a round score (user question + assistant answer as one unit) for the margin signal, so more questions qualify for the 3000 tier.
- A Reactor check (integrator) of the quoted-line hint on about 10 test-style questions. It fires on 23 of 25 test ssa questions and has never been checked against Reactor.
