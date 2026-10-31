# Lens B "Semantyka", multi-session: Round 2 report

New lens: `lenses/multi/b_tight.py`, which imports the round-1 helpers from `b_sweep.py`. **Best variant: `p08c35_aor`.**
Runs: `runs/r2-multi-b/multi/{generic,b_sweep,b_tight}/<variant>/{dev,dev200}`. Test audit: `runs/audit/multi/b_tight/p08c35_aor`.
Scratch (offline fits from per_question.jsonl):
- `scratch_b/prune_fit.py`: gap-threshold pruning
- `scratch_b/lost.py`: gold sessions far below the top CE score
- `scratch_b/keep_fit.py`: logistic p(gold session) model, and the keep and cite thresholds
- `scratch_b/kind_fit.py`: thresholds per question kind (no gain)

## Headline

The round-1 winner `deep8_10k` sends about 8 sessions on dev and dev200 and about 12 on test, for 2 to 3 gold sessions. If Reactor cites every passage, S drops by 12.7 on dev (86.6 to 73.9) and by 11.7 on dev200 (85.2 to 73.5).

`p08c35_aor` cuts the pack down to the sessions that a small logistic model calls likely gold (3.5 per question on dev, 3.7 on dev200), at about 6k chars instead of 10k:
- dev: S 86.6 → **87.2**; Sall 73.9 → **85.7** (+11.8).
- dev200: S 85.2 → **83.3** (−1.9); Sall 73.5 → **82.3** (+8.8).
- The dev200 S loss is one question out of 22: the "properties viewed before the townhouse offer" question, which has 5 gold sessions.

Against the acceptance rule (S +2 on dev and no loss on dev200), the result is **mixed**: S +0.6 on dev and −1.9 on dev200. On Sall, the robust metric, it wins by +9 to +12. If submission citations are whatever Reactor cites, which the organisers have not confirmed either way, this is the variant to route. If the integrator stays on the strict rule, keep `deep8_10k` for S and take the Sall gain only after the cite-post-filter question is settled. My recommendation is to switch: Sall is +9 to +12, while S is +0.6 on dev and −1.9 on dev200, and the dev200 loss is a single question.

The abstention AUC also improves on dev: 0.644 → **0.731**, by importing multi-A's absence check (credit: `a_tally.abstain_score`). On dev200 it falls from 0.833 to 0.795, but dev200 has only 6 unanswerable questions.

## Results (multi gold type; dev 133 q / 121 answerable, dev200 28 q / 22 answerable)

| split | lens / variant | S | Sall | PA | ATR | SR | CF1 | CF1all | chars | AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| dev | generic `hybrid_rr` (bar) | 69.1 | 69.1 | 0.744 | 0.873 | 0.961 | 0.817 | 0.817 | 11931 | 0.598 |
| dev | b_sweep `deep8_10k` (R1 best) | 86.6 | 73.9 | 0.967 | 0.989 | 0.994 | 0.896 | 0.473 | 9949 | 0.644 |
| dev | b_tight `k8m2` | 80.6 | 80.6 | 0.884 | 0.955 | 0.960 | 0.833 | 0.833 | 5927 | 0.644 |
| dev | b_tight `k10m2` | 82.3 | 82.3 | 0.934 | 0.976 | 0.982 | 0.789 | 0.789 | 6520 | 0.644 |
| dev | b_tight `k7m3` | 81.2 | 81.2 | 0.926 | 0.970 | 0.974 | 0.770 | 0.770 | 6482 | 0.644 |
| dev | b_tight `k8m2_rel` | 82.5 | 80.6 | 0.884 | 0.955 | 0.960 | 0.895 | 0.833 | 5927 | 0.644 |
| dev | b_tight `s8m2` | 80.6 | 80.6 | 0.884 | 0.956 | 0.960 | 0.831 | 0.831 | 5962 | 0.644 |
| dev | b_tight `s10m2` | 81.7 | 81.7 | 0.926 | 0.973 | 0.977 | 0.787 | 0.787 | 6560 | 0.644 |
| dev | b_tight `p06` | 85.2 | 85.2 | 0.950 | 0.983 | 0.985 | 0.843 | 0.843 | 6021 | 0.644 |
| dev | b_tight `p08` | 85.7 | 85.7 | 0.950 | 0.980 | 0.984 | 0.858 | 0.858 | 5841 | 0.644 |
| dev | b_tight `p10` | 85.1 | 85.1 | 0.934 | 0.974 | 0.979 | 0.873 | 0.873 | 5648 | 0.644 |
| dev | b_tight `p15` | 84.0 | 84.0 | 0.909 | 0.968 | 0.971 | 0.887 | 0.887 | 5433 | 0.644 |
| dev | b_tight `p10f` | 84.9 | 84.9 | 0.934 | 0.974 | 0.979 | 0.866 | 0.866 | 5732 | 0.644 |
| dev | b_tight `p10c35` | 86.2 | 85.1 | 0.934 | 0.974 | 0.979 | 0.910 | 0.873 | 5648 | 0.644 |
| dev | b_tight `p08c35` | 87.2 | 85.7 | 0.950 | 0.980 | 0.984 | 0.910 | 0.858 | 5841 | 0.644 |
| dev | b_tight `p08c35_amax` | 87.2 | 85.7 | 0.950 | 0.980 | 0.984 | 0.910 | 0.858 | 5841 | 0.728 |
| dev | **b_tight `p08c35_aor`** | **87.2** | **85.7** | 0.950 | 0.980 | 0.984 | 0.910 | 0.858 | 5841 | **0.731** |
| dev200 | generic `hybrid_rr` (bar) | 63.7 | 63.7 | 0.682 | 0.844 | 0.950 | 0.770 | 0.770 | 11947 | 0.689 |
| dev200 | b_sweep `deep8_10k` (R1 best) | 85.2 | 73.5 | 0.955 | 0.985 | 0.991 | 0.874 | 0.487 | 9951 | 0.833 |
| dev200 | b_tight `k10m2` | 76.3 | 76.3 | 0.864 | 0.947 | 0.959 | 0.745 | 0.745 | 7098 | 0.833 |
| dev200 | b_tight `k7m3` | 79.6 | 79.6 | 0.909 | 0.970 | 0.982 | 0.755 | 0.755 | 6902 | 0.833 |
| dev200 | b_tight `k8m2_rel` | 80.3 | 77.3 | 0.864 | 0.947 | 0.959 | 0.874 | 0.773 | 6681 | 0.833 |
| dev200 | b_tight `s10m2` | 76.4 | 76.4 | 0.864 | 0.947 | 0.959 | 0.746 | 0.746 | 6837 | 0.833 |
| dev200 | b_tight `p06` | 81.8 | 81.8 | 0.909 | 0.962 | 0.973 | 0.820 | 0.820 | 6432 | 0.833 |
| dev200 | b_tight `p08` | 82.3 | 82.3 | 0.909 | 0.962 | 0.973 | 0.835 | 0.835 | 6279 | 0.833 |
| dev200 | b_tight `p10` | 82.4 | 82.4 | 0.909 | 0.962 | 0.973 | 0.841 | 0.841 | 6240 | 0.833 |
| dev200 | b_tight `p10c35` | 83.3 | 82.4 | 0.909 | 0.962 | 0.973 | 0.868 | 0.841 | 6240 | 0.833 |
| dev200 | b_tight `p08c35` | 83.3 | 82.3 | 0.909 | 0.962 | 0.973 | 0.868 | 0.835 | 6279 | 0.833 |
| dev200 | b_tight `p08c35_amax` | 83.3 | 82.3 | 0.909 | 0.962 | 0.973 | 0.868 | 0.835 | 6279 | 0.663 |
| dev200 | **b_tight `p08c35_aor`** | **83.3** | **82.3** | 0.909 | 0.962 | 0.973 | 0.868 | 0.835 | 6279 | **0.795** |

ALL for `p08c35_aor`: dev 0.959 (R1: 0.984), dev200 0.909 (R1: 0.955).

**Routed multi** (dev, questions the router sends to multi, KU misroutes included; tag `r2-multi-b-route`):

| variant | S | Sall | PA | CF1 | CF1all | chars | AUC |
|---|---|---|---|---|---|---|---|
| `deep8_10k` | 82.6 | 69.7 | 0.918 | 0.868 | 0.438 | 9944 | 0.668 |
| **`p08c35_aor`** | **83.1** | **81.8** | 0.897 | 0.882 | 0.839 | 5487 | **0.758** |

## Variants tried (one line each)

All variants share the round-1 `deep8_10k` retrieval: multi-query hybrid → CE on the top 90 → intra-session CE over the user units of the top 15 sessions. Each session gets a score, rmax = its best unit CE logit. The variants differ in which sessions they keep, and so in what gets packed.
- `k8m2` / `k10m2` / `k7m3`: keep the sessions within D = 8 / 10 / 7 logits of the top, at least 2 / 2 / 3 and at most 8. Sall rises to 80–82, but PA drops to 0.88–0.93: gold sessions often rank 2nd to 4th with a 6 to 14 logit gap.
- `k8m2_rel`: the same, with the round-1 "within 4 logits" cite rule applied inside the kept sessions. S 82.5.
- `s8m2` / `s10m2` / `s7m3`: add sentence-level CE (`hx.rerank_texts` over the user sentences of the top 10 sessions), max-fused into the session score. **No gain** (−0.6 on dev, ±0 on dev200). The unit-level CE already sees the fact sentence.
- `p06` / `p08` / `p10` / `p15`: **keep the sessions whose p(gold) ≥ tk**, at least 2 and at most 8, with cite = every kept session (so S = Sall).
  - p(gold) is a 5-feature logistic model fit on dev only, using:
    - gap to the top CE logit
    - rank by CE
    - question-term coverage of the session's user text
    - number of the session's units in the top 40 of the final ranking
    - log of the rank of the session's first unit in the final ranking
  - Rank and fused rank carry the signal, not the CE gap.
  - dev200 served as the holdout. Offline, the model predicted dev200 S 84.0 at tk 0.1, against 79.8 for the best gap rule.
  - Measured: p08 scores 85.7 on dev and 82.3 on dev200.
- `p10f`: also force each facet's top session into the pack. −0.2; dropped.
- `p10c35` / **`p08c35`**: pack = sessions with p ≥ 0.10 / 0.08; cite_plan = packed sessions with p ≥ 0.35 (at least 2). This gives S > Sall when cite post-filtering is allowed and leaves Sall unchanged otherwise.
- `p08c35_amax` / **`p08c35_aor`**: abstain_p combined with multi-A's absence check (titles, capitalised words, conjuncts and noun pairs that never appear in any user turn, plus an empty-window flag) by max / noisy-OR. Noisy-OR wins: AUC 0.731 / 0.795.
- Hint, added in all `b_tight` variants (it cannot be measured offline): for count and sum questions without a "now / currently" cue, the hint adds "If a later session restates the same item with a new number, the latest statement wins." This covers the KU-style counts routed to multi (brief item 2).
- Not done: a "cite only the passages that contain a counted item" hint. The pack is now close to the cite set (3.5 sessions for about 2.8 gold), so the hint matters less, and offline metrics cannot see it.
- Thresholds per question kind (a lower tk for `count`): no gain offline (`kind_fit.py`).

## Failure patterns (p08c35_aor)

1. **Category to instance, many gold sessions.** The question names a category, and the gold sessions name instances with a 7 to 14 logit gap and fused rank 6 to 15.
   - "How many properties did I view before making an offer on the townhouse in Brookside": 5 gold sessions. Two of them have p 0.07 and 0.006, so the pack keeps 3. This is the dev200 loss, and the same question fails on dev.
   - "How many pieces of furniture did I buy, assemble, sell, or fix": the 4th gold session has p 0.03 and term coverage 0.
   - "How many years in total did I spend in formal education from high school to…": the 3rd gold session is rank 6, gap 7.3, p 0.05.
   - The round-1 deep pack kept these at about 8 sessions, so they are the price of pruning.
2. **Gold session missing from the hybrid pool entirely.** "projects I led" → case competition / poster. This miss is carried over from round 1.
3. **Test-style repeated-measurement counts may need more breadth than 8 sessions.** In the test audit, "How many times did my systolic reading exceed 130 in August?" keeps 6 sessions, and "phone calls with my daughter in August" keeps 6. The audit shows several in-window mentions, and the count of in-window sessions could exceed the cap. This cannot be checked on dev, where the window is inactive because the history spans fewer than 45 days.
4. Decoys still sit inside kept sessions; for example, the test tango-shoes pack holds "I skipped buying new tango shoes". The hint covers this, and the session is cited only when its p ≥ 0.35.

Test audit (12 packs, 0 flagged): 4 to 8 sessions per pack, 4.8k to 9.6k chars. R1 sent about 12 sessions.

## CORE REQUESTs
1. **Decide the cite policy for multi with Sall in view.** `p08c35_aor` makes the pack nearly equal to the cite set, so Sall is within 1.5 of S on dev and within 1.0 on dev200. If Reactor's own citations are used, route this variant instead of `deep8_10k`, which scores 12.7 Sall below its S on dev.
2. Optional: store `kind` / `facets` from each lens's analysis in per_question.jsonl, so offline threshold fits per kind need not re-run `analyze`.

## Ideas for next round
- **Adaptive breadth for windowed counts on test:** when the window prior is active and the kind is count, keep every in-window session with p ≥ tk/2, up to 12. This targets failure 3, but it can only be validated by test audit and a Reactor spot check.
- **Instance expansion for category questions:** multi-A's LEXICON plus `hx.dense_texts` against the user sentences of sessions ranked 4 to 15, used as an extra feature in the p(gold) model. This targets failure 1. Refit the model on dev only and validate it on dev200.
- **Refit p(gold) with richer features:** whether the best unit states a first-person fact with a number, and facet-hit flags. Fit on dev, check on dev200.
- A soft "cite only the passages that contain a counted item" hint, once a Reactor spot check is allowed.
