# SSA lens B ("Semantyka"): round 2 report

Files:
- `lenses/ssa/b_role.py`: new this round. It holds the evidence-based role detector `role_guess(q, hx)` and a routed wrapper lens that measures it end to end.
- `lenses/ssa/b_semantic.py`: the ssa lens, extended this round.
- Scratch: `lenses/ssa/scratch_b/role_probe.py`, `role_eval.py`, `role_test.py`, `role_test_multi.py`, `role_other_routes.py`.
- Runs: `runs/r2-ssa-b/` (ssa type) and `runs/r2-ssa-b-role/` (routed ssu, multi and all).

**Headline: the role detector is the round-2 deliverable.** With it, cue-less dev ssa questions routed to ssu or multi are switched to the ssa lens.
- Routed system: dev S goes from 80.4 to **83.3** (+2.9) and Sall from 74.9 to **78.0**. dev200 S goes from 79.9 to **82.8** (+2.9) and Sall from 74.2 to **77.2**.
- Abstain AUC goes from 0.719 to 0.750 on dev and from 0.808 to 0.825 on dev200.
- No ssu, ku, multi or temporal question is switched by mistake on dev or dev200 (FP 0).
- On test it switches nothing (0 of 45 ssu-routed, 0 of 20 multi-routed questions). Every test ssa question carries the "you recommended" cue.

The ssa type itself is still saturated. My lens ties lens A there (92.5 / 93.1 against A's 93.3 / 93.3), and sentence-level trimming to about 4k chars cannot be done without losing PA on dev.

## Variants tried (one line each)
ssa lens (`b_semantic.py`, gold ssa questions):
- `session10k1_rr` (round-1 best, default): the whole top session in cross-encoder priority order, cut at 10k chars.
- `session10k1_rrp`: as `session10k1_rr`, plus a recommendation-sentence pool. Every assistant unit whose first-person recommendation shares a category or purpose token with the question joins the cross-encoder pool. The idea follows lens A's sentence scan. It is neutral on dev and dev200. On test it adds a hint line and drops abstain_p from 0.73 to 0.06 for the illustrator question, whose recommendation unit sat at hybrid rank 50.
- `trim4k`, `trim5k`, `trim6k`: brief item (2). The best turn and its user request are kept whole; the rest of the top session follows in unit cross-encoder order (raw question). The cut is at 4k, 5k or 6k.
- `trim4k_nohead`: as `trim4k`, without the turn-head unit before each chunk.
- `trim5k_cq`, `trim6k_cq`: as `trim5k` / `trim6k`, but the cross-encoder query is the cleaned question, with meta-cues ("our previous chat about") removed.
- `trim5k_s`, `trim6k_s`: as the `_cq` variants, but a unit's score is the maximum sentence-level cross-encoder logit (`hx.rerank_texts`).
- `trim5k_sb`: as `trim5k_s`; the best turn is also chosen by sentence score.
- `_SELF_REC` now also matches "you might like / you'd love / you'll enjoy". This is general recommendation phrasing; it affects the hint and abstain_p only.
- The INSUFFICIENT_EVIDENCE note in the hint is switched off by default (`abstain_hint` = 9), following the brief's "no abstention hints".

Role detector (`b_role.py`, router plus switch, ssa target = A `recqs_cf7` unless noted):
- `noswitch`: the routed system as in `configs/best.json` (control).
- `switch_a`: ssu route switched at p ≥ 0.7, c = −1.0.
- `switch_b`: as `switch_a`, but the target is my `session10k1_rr` instead of A's lens.
- `switch_a5`: as `switch_a`, threshold 0.5.
- `switch_a_m`: c = −1.2 (margin version), threshold 0.7.
- `switch_m6`, `switch_m8`: margin version at thresholds 0.6 and 0.8 (sensitivity check).
- `switch_nf0`: text feature only, with no cross-encoder margin (ablation).
- `switch_am9`, `switch_am95`: the ssu route at 0.7, plus the multi route at 0.9 or 0.95.
- **`switch_m8m9` (recommended):** the ssu route at 0.8 and the multi route at 0.9.

## role_guess(q, hx) -> p_assistant
Signals:
- `d`: the best cross-encoder logit over assistant units minus the best over user units. It is computed on the cross-encoder-reranked top 40 of `hx.hybrid(question, k=100, pool=300)`, the same query and pool as generic `hybrid_rr`, so the rerank pairs are cached.
- `nf0`: the question has no first-person word (I, my, me, mine, our, us …).

The probability is `p = sigmoid(0.35·clip(d, ±8) + 2.2·nf0 − 1.2)`.

The idea: cue-less ssa questions ask about content the assistant produced ("Which dessert shop in Orlando had the giant milkshakes?"). They match an assistant unit much better than any user unit (d about +2 to +16) and rarely mention the user. ssu questions match the user's own statement.

Results on questions routed to ssu (offline `role_eval.py`; dev has 144 such questions, 50 of them gold ssa):

| | dev | dev200 |
|---|---|---|
| AUC, p_assistant (ssa vs everything routed to ssu) | 0.974 | 1.000 |
| AUC, ssa vs ssu only | 0.978 | 1.000 |
| accuracy at 0.7, ssa vs ssu only | 0.919 | 1.000 |
| TP / FP at 0.7 | 42 / 0 | 7 / 0 |
| TP / FP at 0.8 | 37 / 0 | 6 / 0 |
| highest p of a non-ssa question | 0.654 | 0.654 |

Gain captured: on dev, +1.97 of the +2.25 a perfect oracle switch would give; on dev200, +1.25 of +1.27.

Where the gain comes from: the switch gains about 64 S on each ssa question that the ssu lens gets wrong, and costs about 1 S (chars) on each one it gets right. The cost side is steep. A false switch of an ssu, multi or ku question costs 31 to 86 S, for example "What breed is my dog?" (−65), "What time did I reach the clinic" (−65) and "Where did Rachel move to" (−86). That is why the thresholds are strict.

Wiring (CORE REQUEST 1): after `route(q.question)`:
- if the route is ssu and `role_guess(q, hx) ≥ 0.8`, use ssa;
- if the route is multi and `role_guess(q, hx) ≥ 0.9`, use ssa;
- never apply it to the ku or temporal routes. On temporal-routed dev questions p ≥ 0.7 gives 12 false switches ("Which event happened first, …" has no first-person word).

## Results
### ssa type (gold ssa; dev n = 112, dev200 n = 22; AUC undefined, 0 unanswerable ssa)
| split | variant | S | Sall | PA | ATR | SR | CF1 | chars |
|---|---|---|---|---|---|---|---|---|
| dev | generic `hybrid_rr` (bar) | 72.3 | 72.3 | 1.000 | 1.000 | 1.000 | 0.368 | 11932 |
| dev | A `recqs_cf7` (routed winner, r1) | 93.3 | 92.6 | 1.000 | | | 1.000 | 5587 |
| dev | **session10k1_rr** | **92.5** | **92.5** | 0.991 | 1.000 | 1.000 | 1.000 | 6085 |
| dev | session10k1_rrp | 92.5 | 92.5 | 0.991 | 1.000 | 1.000 | 1.000 | 6085 |
| dev | session8k1 | 92.4 | 92.4 | 0.991 | 0.991 | 0.991 | 0.991 | 5692 |
| dev | trim4k | 88.0 | 88.0 | 0.911 | 0.920 | 1.000 | 1.000 | 3702 |
| dev | trim4k_nohead | 88.0 | 88.0 | 0.911 | 0.920 | 1.000 | 1.000 | 3696 |
| dev | trim5k | 88.4 | 88.4 | 0.920 | 0.920 | 1.000 | 1.000 | 4407 |
| dev | trim6k | 90.5 | 90.5 | 0.955 | 0.964 | 1.000 | 1.000 | 4963 |
| dev | trim5k_cq | 89.6 | 89.6 | 0.938 | 0.938 | 1.000 | 1.000 | 4403 |
| dev | trim6k_cq | 91.1 | 91.1 | 0.964 | 0.973 | 1.000 | 1.000 | 4960 |
| dev | trim5k_s | 90.1 | 90.1 | 0.946 | 0.946 | 1.000 | 1.000 | 4406 |
| dev | trim6k_s | 91.1 | 91.1 | 0.964 | 0.973 | 1.000 | 1.000 | 4967 |
| dev | trim5k_sb | 90.1 | 90.1 | 0.946 | 0.955 | 1.000 | 1.000 | 4401 |
| dev200 | generic `hybrid_rr` (bar) | 71.2 | 71.2 | 1.000 | 1.000 | 1.000 | 0.331 | 11938 |
| dev200 | A `recqs_cf7` (r1) | 93.3 | 92.9 | 1.000 | | | 1.000 | 5376 |
| dev200 | **session10k1_rr** | **93.1** | **93.1** | 1.000 | 1.000 | 1.000 | 1.000 | 5929 |
| dev200 | session10k1_rrp | 93.1 | 93.1 | 1.000 | 1.000 | 1.000 | 1.000 | 5929 |
| dev200 | trim5k_cq | 87.8 | 87.8 | 0.909 | 0.909 | 1.000 | 1.000 | 4279 |
| dev200 | trim6k_cq | 90.6 | 90.6 | 0.955 | 0.955 | 1.000 | 1.000 | 4756 |

### Role switch, questions routed to ssu (dev n = 144, dev200 n = 40)
| variant | dev S / Sall | dev PA / ATR / SR / CF1 / chars / AUC | dev200 S / Sall | dev200 PA / ATR / SR / CF1 / chars / AUC |
|---|---|---|---|---|
| noswitch (= best.json, a_struct nb3t0) | 74.4 / 75.8 | .757 / .866 / .952 / .875 / 3701 / .837 | 72.6 / 73.8 | .757 / .851 / .905 / .817 / 3799 / .838 |
| switch_a (0.7, c −1.0) | 82.0 / 83.8 | .875 / .939 / .952 / .883 / 4431 / .936 | 76.8 / 77.6 | .811 / .905 / .905 / .844 / 4130 / .892 |
| switch_b (target: B lens) | 81.9 / 84.0 | .875 / .939 / .952 / .883 / 4566 / .923 | 76.7 / 77.5 | .811 / .905 / .905 / .844 / 4232 / .883 |
| switch_a5 (0.5) | 81.5 / 83.3 | .868 / .936 / .948 / .883 / 4614 / .912 | 72.4 / 73.6 | .757 / .865 / .892 / .817 / 4427 / .856 |
| switch_a_m (0.7, c −1.2) | 82.0 / 83.8 | .875 / .939 / .952 / .883 / 4409 / .936 | 76.8 / 77.6 | .811 / .905 / .905 / .844 / 4130 / .892 |
| switch_m6 (0.6) | 81.5 / 83.4 | .868 / .932 / .952 / .883 / 4509 / .909 | 74.1 / 75.6 | .784 / .878 / .905 / .817 / 4289 / .928 |
| **switch_m8 (0.8)** | **82.0 / 83.8** | .875 / .939 / .952 / .883 / 4329 / .934 | **76.8 / 77.6** | .811 / .905 / .905 / .844 / 4117 / .892 |
| switch_nf0 (text only) | 81.1 / 83.0 | .868 / .937 / .948 / .871 / 4511 / .922 | 75.9 / 77.3 | .811 / .905 / .905 / .817 / 4218 / .892 |

The plateau runs from 0.7 to 0.8, and 0.6 already lets in "move to the new apartment" (an ssu question; −31 S on dev200). The cross-encoder margin adds about +0.9 S on this route over the text-only rule, on both splits.

### Role switch, questions routed to multi (dev n = 158, dev200 n = 42)
| variant | dev S / Sall | dev200 S / Sall |
|---|---|---|
| no multi switch | 82.6 / 69.7 | 79.5 / 67.2 |
| **multi at 0.9** | **85.3 / 72.8** | **84.2 / 72.5** |
| multi at 0.95 | 84.8 / 72.2 | 84.2 / 72.5 |

At 0.9 the switch catches 5 of the 6 dev ssa questions routed to multi, and 2 of 2 on dev200, with 0 false switches. Examples are "How many eggs go into a classic French omelette again?" and "How many mummies … Lost Temple of the Djinn". On these the multi lens scores S 5 to 17; the ssa lens scores 93.

### Routed system (all questions; dev n = 526, dev200 n = 125)
| variant | dev S / Sall / PA / CF1 / chars / AUC | dev200 S / Sall / PA / CF1 / chars / AUC |
|---|---|---|
| noswitch (current best.json) | 80.4 / 74.9 / .867 / .877 / 7375 / .719 | 79.9 / 74.2 / .864 / .864 / 7173 / .808 |
| switch_a (ssu 0.7) | 82.5 / 77.1 / .899 / .879 / 7575 / .750 | 81.3 / 75.5 / .882 / .873 / 7279 / .820 |
| switch_am9 (ssu 0.7 + multi 0.9) | 83.3 / 78.0 / .909 / .884 / 7525 / .751 | 82.8 / 77.2 / .900 / .882 / 7192 / .823 |
| **switch_m8m9 (ssu 0.8 + multi 0.9)** | **83.3 / 78.0 / .909 / .884 / 7504 / .750** | **82.8 / 77.2 / .900 / .882 / 7188 / .825** |

## Best variants
- **For the router: `lenses/ssa/b_role.py` `switch_m8m9`.** It gains +2.9 S on both dev and dev200 and +3.1 / +3.0 Sall, and passes the acceptance rule. The integrator wires `role_guess` into `pipeline.py`.
- **ssa type:** `b_semantic.py` `session10k1_rr` (equivalently `session10k1_rrp`, which gives better test hints). It ties A within 0.8 on dev and 0.2 on dev200. Keep **A `recqs_cf7`** on the ssa route: it has fewer chars and gets the one test question where we disagree right (see failure pattern 3).

Test audit (`harness.audit`, all 25 test ssa questions, `session10k1_rrp`):
- Every pack is a single session of 2.0 to 3.4k chars (mean 2.66k), so brief item (2)'s target of about 4k is already met on test. Trimming only matters for the long LongMemEval sessions on dev.
- 23 of 25 hints quote exactly one first-person recommendation sentence that matches the purpose (Toggl Track, pandas, VS Code, Riverdale Park East, Silje Dahl, Octane Coffee …).
- The cited session matches A's `r2_solo` on 23 of 25 questions. The two that differ are Lisbon coworking (probably unanswerable: abstain_p 0.70, both lenses cite a session with no recommendation) and homebrew (failure pattern 3).

## Top failure patterns
1. **Trimming the top session loses the gold turn, whatever the trimming signal.** Unit cross-encoder, cleaned-query cross-encoder and sentence-level cross-encoder all fail. At 5k, PA falls from 0.991 to between 0.92 and 0.95; each miss costs 0.58 S and 1k chars saves only 0.31 S. Examples:
   - "Bandung … Nasi Goreng": the gold is assistant turn t7 ("Miss Bee Providore offers …"), at gold_rank 21. Sibling turns name the restaurant too.
   - "Radiation Amplified zombie": the gold is the user turn "Fissionator is a REALLY cool one", at gold_rank 30.
   - "powwows … Hoop Dance": the gold-turn label points to a user turn ("I'll definitely look into those powwows …") that does not contain "Hoop" (q_6fabbe9a09a6, q_4d6447a7f593). This looks like label noise in `core.gold_turns`. A whole-session pack satisfies it; any trimmed pack loses it.
2. **Role-detector misses and near-misses.**
   - Missed: "Who was the President's Chief Advisor … in the article on the Lawrence Livermore fusion breakthrough?" (d = −5.0). The user pasted the article, so the best cross-encoder match is a user unit; the miss costs 64.7 S. "Which back-end languages should I learn …" (nf = 1, d = +4.1, p = 0.56).
   - Near false positives: "What breed is my dog?" (d = +4.65), "Where do I take yoga classes?" (d = +4.68) and "How long did it take to move to the new apartment?" (nf0, d = −1.04). Each would cost 31 to 65 S if switched, hence thresholds of 0.8 and 0.9 rather than 0.5.
3. **A recommendation whose name only partly matches the category (test, qualitative).** "What was the name of the homebrew supply shop you recommended?"
   - B cites the session where the user mentions "the homebrew supply place".
   - A cites the right session, with "You should check out Peachtree Brew Supply in Decatur".
   - The cross-encoder logit of that sentence is −8.4, and it sits at hybrid rank 99. The `rrp` pool brings it into the pool, but the additive speech-act bonus (+0.8) cannot beat the cross-encoder z-score.
   - I did not tune a weight on this single test question. A's structural scan handles it, which is one more reason to keep A on the ssa route.

## CORE REQUESTs
1. **Wire `role_guess` into the routed pipeline.** `from lenses.ssa.b_role import role_guess`:
   - after `route()`: route ssu with p ≥ 0.8 goes to ssa; route multi with p ≥ 0.9 goes to ssa; ku and temporal are untouched.
   - `lenses/ssa/b_role.py` `build()` is a working reference implementation (it reads `configs/best.json`).
   - Cost: one `hybrid` call plus a cross-encoder rerank of the top 40 per ssu- or multi-routed question. These are cache-shared with generic `hybrid_rr`; about 0.2 to 0.8 s cold.
2. Check `core.gold_turns` for "Hoop Dance" (q_6fabbe9a09a6, q_4d6447a7f593): the gold turn has no answer string. It may be a turn-index offset. If it is real, ATR for that question rewards packing the wrong turn.
3. (Optional) A `route_with_evidence(q, hx)` in `core/router.py`, so that every consumer (audit, sweeps with `--route`) sees the same evidence-aware route.

## Ideas for next round
- Reuse the role signal on the ku route. Its own detector (ku-B `ku_pair_p`) could combine with `d`: "Where is the painting … currently hanging?" has p = 0.90, so `role_guess` alone must not touch ku.
- Combine B's role signal with A's structural recommendation-sentence features (A's brief item 3) into one detector. A's sentence scan catches the "Brew Supply" class, and the cross-encoder margin catches content questions.
- For the ssa lens: gate the session choice on a first-person recommendation with an IDF-weighted category match when the question has no purpose phrase, as A does. Validate it on dev questions of the form "the X you recommended" before using it; dev has few such questions.
- Trimming is not worth more effort for ssa: test packs are already about 2.7k chars, and on dev every trimming signal loses more PA than the chars are worth.
