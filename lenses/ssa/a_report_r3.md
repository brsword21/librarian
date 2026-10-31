# SSA lens A ("Struktura"), round 3 report

The round-2 report has moved to `lenses/ssa/a_report_r2.md` and is summarised in `runs/SYNTHESIS_r2.md`.

Files (all new; no frozen v1 file was edited):
- `lenses/ssa/a_r3_role.py`
  - `role_guess(q, hx)`: a refit role detector. It is a drop-in `role_module` for `lenses/ssu/merged_r2.py` and `lenses/multi/merged_r2.py`.
  - Route-slice variants: `ssu_v1`, `ssu_fit`, `ssu_fit_s55`, `ssu_fit_nh55`, `multi_v1`, `multi_fit`.
- `lenses/ssa/a_r3_routed.py`: a measurement wrapper around `lenses/pipeline.py`.
  - `v1` = configs/best.json.
  - `r3fit` = v1 + the role module on both wrappers.
  - `r3nh` = r3fit + no-hint band.
  - Configs are in `lenses/ssa/scratch_a/r3/routed_r3fit.json` and `routed_r3nh.json`.
- `lenses/ssa/scratch_a/r3/`: role features per split (`role_feats.py`, `role_feats_{dev,dev200,test}.jsonl`), the logistic fits (`fit_role.py`), the test candidate audit (`test_cands.py`) and the sweep logs.
- Runs: tags `r3-ssa-a` (gold type and route slices) and `r3-ssa-a-routed` (full routed system). Audit output is in `runs/audit/all/a_r3_routed/r3fit`.

## TL;DR
1. **The ssa route is saturated and stays as it is** (`a_recsent r2_conf2`: PA = CF1 = 1.0, Sall = S on both splits).
   - Test audit of all 25 ssa-routed packs: every pack holds the right recommendation, and the planted decoys are rejected (details under failure patterns).
   - I changed nothing on this route.
2. **The remaining ssa loss is in the hand-off, and real Reactor confirms it.**
   - In the E1b calibration, Reactor answered INSUFFICIENT_EVIDENCE on q_73a1f68b2421 ("Which company does a great job with environmentally responsible supply chains?", gold Patagonia).
   - The pack contained the answer. The ssu hint "Answer from what the user said about their own supply chains …" sent Reactor to the wrong role.
   - That one abstention is the whole of the ssa citation loss in the calibration: ssa evidence F1 was 0.75 = 3 of 4.
   - v1 still routes that question to ssu (p_b 0.73 < 0.8). Thirteen dev gold-ssa questions get the user-only hint. Proxy PA is 1.0 for 11 of them, so the proxy does not see the problem.
3. **`a_r3_role.role_guess` = max(p_b, p_fit, advice rule).**
   - Routed dev: **86.0 → 86.3** (Sall 84.9 → 85.2). On gold ssa: **91.8 → 93.0**, PA 0.973 → 0.991, and the number of gold-ssa questions on the ssa route goes from 97 to 104.
   - dev200: tie (84.9 / 84.9; ssa 21 → 22 on the ssa route).
   - **FP 0** on dev and dev200: no non-ssa question changes route.
   - **0 of 146 test packs change** (`harness.audit --compare runs/final/v1_test_packs.jsonl`). Route, cite_plan, passages and hint text are all identical; the only character difference is the constant 191-character answer-format suffix in the reactor packs.
   - This is below the +2 bar on S. It is offered as an insurance or Reactor-correctness change with zero test diff.

## Variants tried (one line each)
| variant | idea and params | verdict |
|---|---|---|
| logistic fits (offline, `fit_role.py`) | Fit on dev ssu+multi-routed questions, hold out dev200. Feature sets: [d, nf0], + bm_diff/sess_cov/top5_a, + ours/advice, + route. d = CE(best assistant unit) − CE(best user unit); nf0 = no first-person word. | AUC 0.99 dev / 1.00 dev200 for every set. The extra features do not raise the zero-FP TP count. nf0 carries the model (w 5.7 vs 0.47 per d unit). |
| `ssu_fit` / `multi_fit` (= `r3fit`) | role_guess = max(p_b, p_fit). p_fit = sigmoid(0.469·d + 5.666·nf0 + b), with b set so that p = 0.8 at d = −0.73. That is the midpoint between the nearest dev negative ("…move to the new apartment?", d −1.04) and the lowest positive above it (−0.42). Thresholds stay 0.8 (ssu) and 0.9 (multi). | ssu slice: tie. multi slice: +0.4 dev, tie dev200. **Recommended.** |
| advice rule (inside r3fit) | "should I/my/we" and d ≥ 2 → p ≥ 0.85, which passes ssu (0.8) but not multi (0.9). dev: 3 of 3 such ssu-routed questions are ssa; the multi-route "do I need to" questions are not ssa and are not matched. | Fixes "Which back-end languages should I learn …" (PA 0 → 1). 0 test questions match. |
| `ssu_fit_s55` | Soft band: nf0 and −5.5 ≤ d < −0.73 → ssa lens `recqs_cf7` (session fill). | dev slice +0.4 (President's advisor PA 0 → 1); **dev200 −0.9**: the "new apartment" ssu question cites the wrong session. **Rejected.** |
| `ssu_fit_nh55` (= `r3nh`) | Same band, but keep the ssu pack and drop only the user-only hint. | Tie on both splits, 0 test change. Optional; the motivation is Reactor behaviour only. |
| soft quote (offline) | Quote the best line on rec-style questions when shape ≥ 0.5 but the pick is not confident. | dev: 1 of 1 soft quote wrong; dev200: 1 of 1 right. Not enough evidence, so not built. |
| list position (brief item 2) | Pack the list chunk plus the next chunk. | Not built. The computed n-th item is already right on 6 of 6 dev and 3 of 3 dev200 ordinal questions (PA 1). There are no test ordinal ssa questions, and the chars-only gain is about 0.04 S. |

## Results
Gold-type ssa (gold routing; dev 112 q, dev200 22 q; no unanswerable ssa questions, so AUC is "-"):

| split | lens / variant | S | PA | ATR | SR | CF1 | chars | AUC |
|---|---|---|---|---|---|---|---|---|
| dev | generic `hybrid_rr` (baseline) | 72.3 | 1.000 | 1.000 | 1.000 | 0.368 | 11932 | - |
| dev | `a_recsent r2_conf2` (v1, frozen) | 93.6 | 1.000 | 1.000 | 1.000 | 1.000 | 4542 | - |
| dev200 | generic `hybrid_rr` (baseline) | 71.2 | 1.000 | 1.000 | 1.000 | 0.331 | 11938 | - |
| dev200 | `a_recsent r2_conf2` (v1, frozen) | 93.7 | 1.000 | 1.000 | 1.000 | 1.000 | 4186 | - |

Gold ssa questions through the routed system (`a_r3_routed.py`):

| split | variant | S | Sall | PA | ATR | SR | CF1 | chars |
|---|---|---|---|---|---|---|---|---|
| dev | v1 | 91.8 | 91.4 | 0.973 | 0.973 | 1.000 | 0.997 | 4387 |
| dev | **r3fit** | **93.0** | 92.8 | 0.991 | 0.991 | 1.000 | 1.000 | 4504 |
| dev | r3nh | 93.0 | 92.8 | 0.991 | 0.991 | 1.000 | 1.000 | 4497 |
| dev200 | v1 | 93.7 | 93.7 | 1.000 | 1.000 | 1.000 | 1.000 | 4162 |
| dev200 | r3fit / r3nh | 93.7 | 93.7 | 1.000 | 1.000 | 1.000 | 1.000 | 4186 |

Full routed system (all types; dev 526 q, dev200 125 q):

| split | variant | S | Sall | PA | ATR | SR | CF1 | chars | AUC |
|---|---|---|---|---|---|---|---|---|---|
| dev | v1 | 86.0 | 84.9 | 0.935 | 0.967 | 0.985 | 0.899 | 5582 | 0.813 |
| dev | **r3fit** | **86.3** | 85.2 | 0.940 | 0.971 | 0.985 | 0.900 | 5607 | 0.814 |
| dev | r3nh | 86.3 | 85.2 | 0.940 | 0.971 | 0.985 | 0.900 | 5605 | 0.814 |
| dev200 | v1 | 84.9 | 83.2 | 0.918 | 0.956 | 0.970 | 0.894 | 5478 | 0.855 |
| dev200 | r3fit | 84.9 | 83.2 | 0.918 | 0.956 | 0.970 | 0.894 | 5482 | 0.853 |
| dev200 | r3nh | 84.9 | 83.2 | 0.918 | 0.956 | 0.970 | 0.894 | 5481 | 0.853 |

Route slices (`--route`). ssu_fit was measured before the advice rule was added; the routed rows above include it.

| slice | variant | S | PA | ATR | SR | CF1 | chars | AUC |
|---|---|---|---|---|---|---|---|---|
| ssu-routed dev (140) | ssu_v1 | 86.1 | 0.932 | 0.960 | 0.980 | 0.894 | 4159 | 0.931 |
| | ssu_fit | 86.1 | 0.932 | 0.960 | 0.980 | 0.894 | 4217 | 0.933 |
| | ssu_fit_s55 | 86.5 | 0.939 | 0.967 | 0.980 | 0.894 | 4315 | 0.936 |
| | ssu_fit_nh55 | 86.1 | 0.932 | 0.960 | 0.980 | 0.894 | 4208 | 0.933 |
| ssu-routed dev200 (38) | ssu_v1 | 82.3 | 0.886 | 0.929 | 0.943 | 0.867 | 4234 | 0.905 |
| | ssu_fit | 82.3 | 0.886 | 0.929 | 0.943 | 0.867 | 4248 | 0.905 |
| | ssu_fit_s55 | **81.4** | 0.886 | 0.929 | 0.943 | 0.838 | 4291 | 0.905 |
| | ssu_fit_nh55 | 82.3 | 0.886 | 0.929 | 0.943 | 0.867 | 4243 | 0.905 |
| multi-routed dev (170) | multi_v1 | 86.3 | 0.936 | 0.972 | 0.984 | 0.903 | 5467 | 0.795 |
| | multi_fit | 86.7 | 0.943 | 0.978 | 0.984 | 0.905 | 5481 | 0.800 |
| multi-routed dev200 (45) | multi_v1 / multi_fit | 84.2 | 0.921 | 0.965 | 0.984 | 0.872 | 6061 | 0.789 |

**Best:** `r3fit`. In configs/best.json set `routes.ssu.params` and `routes.multi.params` to `{"role_module": "lenses/ssa/a_r3_role.py"}`. The ssa route stays on `a_recsent r2_conf2`. reactorq/build_packs.py already merges `params`.

## Top failure patterns
1. **The user-only ssu hint on misrouted ssa questions.** Real Reactor abstained on one of them. After r3fit, 7 dev gold-ssa questions still get the hint:
   - "Which romantic Italian restaurant in Rome was it for dinner?"
   - "In Bajimaya v Reward Homes Pty Ltd, what year …"
   - "Which traditional game is often performed by skilled dancers at powwows?"
   - "What is Andy wearing in the comedy movie scene script?"
   - the two "designation on my jumpsuit" questions
   - the President's advisor question

   The hint template also produces broken text: "their own jumpsuit led me. Mentions of other people's me", "their own house begin", "their own cordero ancash". `r3nh` removes the hint on the no-first-person ones (0 test change).
2. **A negative CE margin on true ssa questions (the user turn matches better).**
   - President's Chief Advisor (d −4.99) is the only remaining ssa PA miss on dev (ssu lens, PA 0). Rome (d −3.08) and Andy (d −8.18) also have negative margins.
   - They cannot be separated from "How long did it take to move to the new apartment?" (ssu, d −1.04) and "Where did Rachel move to …" (ku, d −6.19) with d and nf0 alone.
   - Handing that band to the ssa lens (s55) fixes the President question but breaks the apartment question's citation on dev200 (CF1 1 → 0). The ssa lens then ranks a runner-up session first.
3. **Role-play ssa questions with a first-person word.** "What designation on my jumpsuit …" and "Which show was my example of Netflix …" (the latter routed to temporal) are unreachable with role features: nf0 = 0. Proxy PA is already 1 for them.
4. **Test ssa route (audit, no gold): all 25 packs pick the right recommendation.**
   - Rejected decoys: the sister's farrier Magnus Vik (we pick Ola Hansen), the sister's illustrator Maja Lie (Silje Dahl), the Supernormal birthday dinner (Matilda 159 Domain for the sons), Coach Elena for strength work (Coach Miriam for speedwork), the AGC 33k-ohm resistor (0.022 µF coupling capacitor), and the user's own Avila Spaces day pass (Heden in Baixa).
   - 22 of 25 packs quote the line. Three have no quote because the pick is not confident (correct by reading, but low-margin):
     - Lisbon/Heden: structural tie at 1.01 across 3 sessions;
     - RouteXL: shape 0.5;
     - Octane Coffee: shape 0.5.

## CORE REQUESTs
1. **configs/best.json:** `routes.ssu.params = routes.multi.params = {"role_module": "lenses/ssa/a_r3_role.py"}`. It is in `lenses/ssa/scratch_a/r3/routed_r3fit.json`. Effect: dev +0.3 routed (+1.2 on gold ssa), tie on dev200, **0 test packs changed**.
2. **ssu lens owners (ssu-A/B), optional:**
   - Do not emit "Answer from what the user said about their own X" when the question has no first-person word. `lenses/ssa/a_r3_role.py ssu_fit_nh55` does this as a wrapper: tie on proxy, 0 test change.
   - Fix the head-noun templating ("their own jumpsuit led me … other people's me").
3. **harness.audit --compare:** also diff the `hint` text, and normalise the 191-character answer-format suffix that reactor packs add to `chars`. I checked both by hand this time.
4. **Reactor check:** test the quoted-line hint on 3–5 ssa test-style packs, and one no-quote pack (Lisbon).

## Ideas for the next round
- An impersonal-user-fact feature ("the new apartment", "Rachel moved") together with a sentence-level CE (assistant sentences vs user sentences instead of units). This would make the −5..−1 band separable and let the s55-style hand-off fix the President question without the apartment regression.
- When the ssa lens takes a hand-off with no rec cue, cite by the turn's own session rather than the fused top, to avoid the dev200 CF1 miss.
- A soft quote line for shape-0.5 picks ("possibly relevant line …"), only after a Reactor check: the dev evidence is 1 wrong and 1 right.
- A role-play detector ("my jumpsuit", "my character", "in the story") for the remaining first-person ssa questions.
