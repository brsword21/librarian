# SSU lens B "Semantyka": round 2 report

Lens: `lenses/ssu/b_merge.py`. **Best variant: `best`** (same parameters as `k11ru2u3`).
It combines B's all-role retrieval and user sweep with A's owner / polarity / tense classifier, decoy hint and abstention gates. A's code is imported unchanged from `a_owner.py` and `a_struct.py`.
Round-1 report: `b_report_r1.md`. Scratch: `scratch_b/why.py` explains session choices on any split (test included, no gold). Test audits: `scratch_b/audit_{k11p,k11,k11ru,k11s5,k11ru2,k11ru2u2,k11ru2u3,best}.txt`.
Runs: `runs/r2-ssu-b/ssu/...` (gold type) and `runs/r2-ssu-b-route/ssu/...` (`--route --type ssu`, the questions the router sends to ssu).

## Headline (dev / dev200)
| system | gold ssu S | gold ssu Sall | routed ssu S | routed ssu Sall | test passages/q | test chars |
|---|---|---|---|---|---|---|
| generic hybrid_rr | 76.6 / 73.5 | 76.6 / 73.5 | - | - | - | - |
| A a_struct nb3t0 (r1 winner) | 93.5 / 92.5 | 93.2 / 90.7 | 74.4 / 72.6 | 75.8 / 73.8 | 2.71 | 3138 |
| B b_sem best_rec (r1) | 93.5 / 92.6 | 89.1 / 86.0 | 72.4 / 75.3 | 72.9 / 74.4 | 5.92 | 3341 |
| **B b_merge best** | **93.5 / 92.5** | **92.1 / 90.2** | **80.3 / 76.9** | **82.3 / 78.7** | **2.13** | **3031** |

- **Routed ssu route against A:** +5.9 S on dev and +4.3 on dev200; Sall +6.5 and +4.9.
- **Gold ssu:** S ties A. Sall is −1.1 on dev and −0.5 on dev200, inside the 2-point limit. The cost comes from KU-cued ssu questions that keep 2–3 sessions.
- **Test audit:** the test packs carry 2.13 passages per question, against 2.71 for A and 5.92 for my round-1 lens.
- **Agreement with A on test:** the primary cite agrees with A on 44 of 45 test ssu questions. A's cites were judged right in the round-1 audit (younger son Daniel, pilau, Big Green Egg).
- **Where the routed gain comes from** (dev, best vs A):

  | gold type | PA best | PA A | S best | S A |
  |---|---|---|---|---|
  | ssa misroutes (50 q) | 0.82 | 0.64 | 82.4 | 70.1 |
  | ku misroutes (25 q) | 0.92 | 0.80 | 77.5 | 69.7 |
  | temporal (6 q) | 0.50 | 0.33 | – | – |

  Multi misroutes lose: S 36.8 against 43.3 for A (10 q).
- **dev200 ku → ssu:** S 76.4 against 47.6 for A.

## Variants tried (one line each; all in `b_merge.py`)
| variant | idea / params |
|---|---|
| m5 | B pool (all-role hybrid 100, rerank, user sweep of the top 3 sessions) + A structure. Pack the sessions within 5 logits (max 3), cite the primary. Pack the best assistant unit when it beats every user unit. |
| m5_noasst | m5 without assistant units. Shows the ssa-misroute fix: routed dev 69.6 → 77.5. |
| m5_plain | m5 without structure or hint (control). Better on routed (79.5), so the plan penalty demotes KU/multi facts. |
| m3 / m8 / m0 | competitor window of 3 / 8 / 0 logits (m0 = 1 session). m3 and m0 lose the dev200 Japan gold (gap 4.8). |
| m5_pair | m5 + cite clean sessions within 3 logits. |
| m5r | m5 + other sessions' units by raw CE logit, 3 units each. |
| k11 | KU cue (present-tense state or habit, previous / before / most recently / still / now / same) widens the window to 11 logits. Raw-logit units, ou=3. |
| k11p | k11 + cite the KU-cued sessions within 5 logits. +1.3 routed dev, but on test it cites 2–3 R-77 decoy sessions. Rejected. |
| k11pa / k11pa8 | + rerank the assistant units of the top session, pack the best one within 4 / 8 logits of the best user unit. Worse: more chars, budget crowding. |
| k11c2 / k11c0 | cap the assistant echo at 2 / 0 logits above the session's best user unit. Loses on gold dev200 (−1.4 / −4.3). |
| k11v | +1 for name questions whose unit holds an extracted name. Neutral on dev; not enough on test alone. |
| k11s / k11s5 | sentence-level CE (`hx.rerank_texts`) on the top 12 user units, unit score → best sentence (w 1 / 0.5). +1.7 routed dev, but dev200 loses the Japan gold: the "planning a trip to Japan" sentence wins. Rejected. |
| k11ru | recency cue picks the latest session by its best clean **user** unit, not by the session score. Neutral on dev. On test it fixes the R-77 "end up" cites, which pointed at the assistant's own suggestion session. |
| k11ru2 | k11ru + at most 2 sessions (3 under a KU cue). Test passages fall from 2.76 to 2.13. |
| k11ru2p | k11ru2 + cite a KU pair within 2 logits. Small dev gain, same test risk as k11p. |
| k11ru2u2 / **k11ru2u3 = best** | k11ru2 + user-backed primary. When the top session wins on an assistant unit, take the session within 2 / 3 logits whose best clean user statement is strongest. It must match the head noun and not be a question to the assistant. Neutral on dev/dev200. On test it fixes 5 assistant-echo cites. |
| best_k2 / best_k8 | KU mode with 2 sessions / 8-logit window. Better gold Sall (+0.3 / +0.6), but routed dev200 drops by 3.5 / 1.8. |

## Results (gold ssu = 70 dev q (64 answerable), 23 dev200 q (22); routed = 144 dev q, 40 dev200 q)
| variant | split | S | Sall | PA | ATR | SR | CF1 | CF1all | chars | AUC | routed S | routed Sall | routed PA |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| generic hybrid_rr (baseline) | dev | 76.6 | 76.6 | 1.000 | 1.000 | 1.000 | 0.512 | 0.512 | 11934 | 0.924 | - | - | - |
| generic hybrid_rr (baseline) | dev200 | 73.5 | 73.5 | 1.000 | 1.000 | 1.000 | 0.407 | 0.407 | 11933 | 0.955 | - | - | - |
| A a_struct nb3t0 (r1 winner) | dev | 93.5 | 93.2 | 1.000 | 1.000 | 1.000 | 0.984 | 0.974 | 3489 | 0.911 | 74.4 | 75.8 | 0.757 |
| A a_struct nb3t0 (r1 winner) | dev200 | 92.5 | 90.7 | 1.000 | 1.000 | 1.000 | 0.955 | 0.894 | 3589 | 0.909 | 72.6 | 73.8 | 0.757 |
| B b_sem best_rec (r1) | dev | 93.5 | 89.1 | 1.000 | 1.000 | 1.000 | 0.984 | 0.837 | 3302 | 0.901 | 72.4 | 72.9 | 0.721 |
| B b_sem best_rec (r1) | dev200 | 92.6 | 86.0 | 1.000 | 1.000 | 1.000 | 0.955 | 0.734 | 3427 | 0.955 | 75.3 | 74.4 | 0.784 |
| m5 | dev | 93.5 | 93.3 | 1.000 | 1.000 | 1.000 | 0.984 | 0.977 | 3273 | 0.911 | 77.5 | 79.5 | 0.801 |
| m5 | dev200 | 92.6 | 91.5 | 1.000 | 1.000 | 1.000 | 0.955 | 0.917 | 3419 | 0.909 | 71.7 | 72.6 | 0.730 |
| m5_noasst | dev | 93.6 | 93.4 | 1.000 | 1.000 | 1.000 | 0.984 | 0.977 | 3036 | 0.911 | 69.6 | 71.6 | 0.676 |
| m5_plain | dev | 93.6 | 93.3 | 1.000 | 1.000 | 1.000 | 0.984 | 0.977 | 3163 | 0.911 | 79.5 | 81.5 | 0.831 |
| m5_plain | dev200 | 92.6 | 91.0 | 1.000 | 1.000 | 1.000 | 0.955 | 0.901 | 3384 | 0.909 | 73.5 | 74.4 | 0.757 |
| m3 | dev200 | 89.7 | 88.3 | 0.955 | 0.955 | 0.955 | 0.955 | 0.909 | 3234 | 0.909 | - | - | - |
| m8 | dev | 93.5 | 91.7 | 1.000 | 1.000 | 1.000 | 0.984 | 0.924 | 3530 | 0.911 | 80.3 | 81.9 | 0.846 |
| m8 | dev200 | 92.5 | 90.5 | 1.000 | 1.000 | 1.000 | 0.955 | 0.886 | 3607 | 0.909 | 76.9 | 77.9 | 0.811 |
| m0 | dev200 | 89.7 | 89.7 | 0.955 | 0.955 | 0.955 | 0.955 | 0.955 | 3116 | 0.909 | - | - | - |
| m5_pair | dev200 | 91.2 | 91.5 | 1.000 | 1.000 | 1.000 | 0.909 | 0.917 | 3419 | 0.909 | 71.9 | 72.6 | 0.730 |
| k11 | dev | 93.5 | 92.0 | 1.000 | 1.000 | 1.000 | 0.984 | 0.935 | 3582 | 0.911 | 80.8 | 82.8 | 0.853 |
| k11 | dev200 | 92.5 | 90.0 | 1.000 | 1.000 | 1.000 | 0.955 | 0.871 | 3751 | 0.909 | 76.9 | 78.4 | 0.811 |
| k11p | dev | 93.8 | 92.0 | 1.000 | 1.000 | 1.000 | 0.995 | 0.935 | 3578 | 0.911 | 82.6 | 83.3 | 0.860 |
| k11p | dev200 | 92.0 | 90.0 | 1.000 | 1.000 | 1.000 | 0.939 | 0.871 | 3751 | 0.909 | 77.4 | 78.4 | 0.811 |
| k11pa | dev200 | 91.9 | 89.9 | 1.000 | 1.000 | 1.000 | 0.939 | 0.871 | 4021 | 0.909 | 75.3 | 76.3 | 0.784 |
| k11c2 | dev200 | 91.1 | 90.0 | 1.000 | 1.000 | 1.000 | 0.909 | 0.871 | 3684 | 0.909 | 77.8 | 80.0 | 0.838 |
| k11c0 | dev200 | 88.2 | 87.1 | 0.955 | 0.955 | 1.000 | 0.909 | 0.871 | 3637 | 0.909 | 73.5 | 76.0 | 0.784 |
| k11s5 | dev | 93.5 | 92.2 | 1.000 | 1.000 | 1.000 | 0.984 | 0.940 | 3476 | 0.911 | 82.5 | 84.3 | 0.875 |
| k11s5 | dev200 | 89.6 | 86.6 | 0.955 | 0.955 | 0.955 | 0.955 | 0.856 | 3574 | 0.909 | 76.9 | 78.0 | 0.811 |
| k11ru2 | dev | 93.5 | 92.1 | 1.000 | 1.000 | 1.000 | 0.984 | 0.938 | 3501 | 0.911 | 80.3 | 82.3 | 0.846 |
| k11ru2 | dev200 | 92.5 | 90.2 | 1.000 | 1.000 | 1.000 | 0.955 | 0.879 | 3711 | 0.909 | 76.9 | 78.7 | 0.811 |
| **best (= k11ru2u3)** | dev | **93.5** | **92.1** | 1.000 | 1.000 | 1.000 | 0.984 | 0.938 | 3501 | 0.911 | **80.3** | **82.3** | 0.846 |
| **best (= k11ru2u3)** | dev200 | **92.5** | **90.2** | 1.000 | 1.000 | 1.000 | 0.955 | 0.879 | 3711 | 0.909 | **76.9** | **78.7** | 0.811 |
| best_k2 | dev200 | 92.5 | 90.7 | 1.000 | 1.000 | 1.000 | 0.955 | 0.894 | 3661 | 0.909 | 73.4 | 74.8 | 0.757 |
| best_k8 | dev | 93.5 | 92.7 | 1.000 | 1.000 | 1.000 | 0.984 | 0.958 | 3376 | 0.911 | 79.9 | 81.9 | 0.838 |
| best_k8 | dev200 | 92.6 | 91.2 | 1.000 | 1.000 | 1.000 | 0.955 | 0.909 | 3541 | 0.909 | 75.1 | 76.7 | 0.784 |

Routed AUC for best: 0.838 on dev and 0.847 on dev200, against 0.837 and 0.838 for A. Rows without a figure for the second split are in the run directories and in `runs/leaderboard.csv`.

## Brief items
1. **Decoys out of passages.** Decoy-only sessions are dropped and named in the hint, using A's note format. Clean dev questions get 1 passage. On test, packs average 2.13 sessions (best) against 5.92 in round 1.
2. **b_merge beats A on the routed ssu route** on both S and Sall, on both splits. Gold ssu S ties. Sall is −1.1 on dev and −0.5 on dev200, within the 2-point limit.
3. **"Last mentioned" cites.** The grill question now cites the newest session, "returned the Weber kettle grill and bought a Big Green Egg". The recency pick compares sessions by user statements (`rec_user`). Without it, 3 R-77 "end up" questions cited a session where the ASSISTANT suggested a screen-grid resistor.

## Top failure patterns
1. **Plan beats past (dev200).** Example: "How long was I in Japan for?" The top session is "I'm planning a trip to Japan … booked with Sakura Travel last month" (logit 6.8). The gold "when I was in Japan a few months ago … spent two weeks" sits at 3.2. It is in the pack, so PA is 1, but the cite is wrong. A's tense rule gives the plan sentence +0.5 because "last month" counts as a past marker. Sentence-level CE makes this worse (k11s, k11s5).
2. **Assistant echo of a decoy (test).** Before the user-backed rule, B cited assistant-driven sessions:
   - "Rice and beans is a great base…" instead of "My favorite meal is pilau".
   - "That's high praise, coming from a son" instead of "My younger son Daniel is moving to Brisbane".

   One case remains. For "physiotherapist after the Toronto Marathon", the only head match is a decoy ("My sister Nadia saw a physiotherapist after the Ottawa Marathon"). It is probably unanswerable, with abstain_p 0.40.
3. **Same-object drift (test).** Many sessions describe the same object with different slots: R-77 AM IF, screen-grid resistor, AGC resistor, cathode resistor, dial lamp. Unit logits are compressed (all 1–5), so the recency rule can pick a sibling slot. Example: "AM IF … end up using" can still cite the July 14 screen-grid session. The 465 kHz session is in the pack.
4. **Misrouted multi questions** (dev 10, dev200 3). These need every gold session, but the pack takes 2–3 sessions within a logit window. They score S 37 against 43 for A, which packs ±1 neighbours of each unit.
5. **Abstention flags on answerable recency questions (test).** Examples: last beer kegged, last book, grill, last restaurant. The CE logits are low (−2 to −5) for "what was the last X I mentioned", so abstain_p is 0.78 to 0.92. Nothing goes to Reactor, but the abstain_p values are miscalibrated for any policy built on them.

## CORE REQUESTs
1. **Router: role detector for cue-less ssa (still the biggest routed loss).** With b_merge, ssa misroutes still reach only PA 0.82. The gold assistant chunk is often missing from the all-role pool. Re-ranking the top session's assistant units (k11pa) crowds the budget. An evidence-based `role_guess` from ssa-B would serve these questions with the ssa lens instead.
2. **Answer-anchored citation** (repeat from round 1, still declined). For ssu the cite plan is one session. Keeping the passages Reactor cites that contain its answer would make Sall equal S on every ssu question.
3. **A cached sentence-level CE over the top units** (`hx.rerank_texts` is cold on test). k11s was slow on its first run (450 ms/q on dev200). A precompute for the top-12 user units of the ssu route would make sentence-level experiments cheap.

## Ideas for the next round
- **KU pair cite gated by evidence, not by the question cue.** Cite the second session only when its best user unit restates the same slot with a different value. This needs a value extractor beyond names, such as numbers with units or quoted titles. On dev it is worth about +1.3 S on the routed route (k11p), and it must not fire on R-77-style sibling slots.
- **Tense fix for "planning a trip … booked … last month".** A plan clause should outrank a past marker in the same sentence when the question asks "was I / did I". This fixes the one wrong dev200 cite.
- **Slot-specific lexical check for drift questions.** Before the recency pick, require the near session's user unit to contain the question's rarest slot term or its abbreviation (intermediate frequency → IF).
- **Calibrate abstain_p for recency phrasing.** Under a recency cue, use the best user-unit logit relative to the question's own pool (a z-score) instead of the absolute logit.
- **Multi misroutes.** When the question carries count or comparison words, fall back to ±1 neighbours and the depth sweep (multi-B).
