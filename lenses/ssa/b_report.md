# SSA lens B ("Semantyka"): round 1 report

Lens: `lenses/ssa/b_semantic.py` (default and best variant: `session10k1_rr`). Scratch: `lenses/ssa/scratch_b/`. Runs: `runs/r1-ssa-b/ssa/`.

## Variants tried (one line each)
All variants share one ranking stage. The candidate pool is `hx.hybrid(raw question)`, optionally plus BM25 on the cleaned question over assistant units (`w_clean`). Units are scored by the fused-RRF z-score (or the cross-encoder z-score when `rerank_n` > 0), plus:
- a round bonus when the preceding user turn matches;
- a topic bonus from "our conversation about X";
- a user-unit penalty, unless the question asks what *I* said;
- speech-act features: a first-person "I recommend / I'd use" with purpose overlap, and penalties for recommendations made to others, by third parties, or hedged.

Sessions are ranked by Emergence-style NDCG over the top 20 units, capped at 2 units per session. Every variant cites only the top session. The variants differ in granularity, depth and budget:
- `turns`: whole turns of the top session in turn-score order (best turn plus the user turn before it) up to 4k chars, plus the best unit (±1) of the runner-up session. No cross-encoder.
- `turns1`: as `turns`, top session only.
- `turns_tight`: as `turns`, with a 2.5k turn budget.
- `plain`: `turns` without the speech-act features or the hint (ablation).
- `turns_rr`: `turns` with the cross-encoder on the top 40 of `hybrid(raw question)`. The query is the raw question, so the rerank cache is shared with `lenses/generic.py`.
- `session`: the whole top session, budget 12k, no cross-encoder.
- `session8k1`: the whole top session in priority order (best turn, then units in fused order, then chronological), cut at 8k.
- `session8k`, `session6k`: as `session8k1`, plus the runner-up's best unit. It is placed before the session fill so the cut cannot drop it.
- `session8k1_rr`, `session10k1_rr`: the whole top session with cross-encoder ordering, cut at 8k or 10k. **Best: `session10k1_rr`.**

## Results (answerable questions; dev n=112, dev200 n=22; AUC undefined because dev SSA has 0 unanswerables)
| split | variant | S | PA | ATR | SR | CF1 | chars | AUC |
|---|---|---|---|---|---|---|---|---|
| dev | generic `hybrid_rr` (baseline) | 72.3 | 1.000 | 1.000 | 1.000 | 0.368 | 11932 | - |
| dev | turns | 83.7 | 0.857 | 0.857 | 1.000 | 0.991 | 5661 | - |
| dev | turns1 | 83.6 | 0.848 | 0.848 | 0.991 | 0.991 | 4127 | - |
| dev | turns_tight | 78.8 | 0.777 | 0.777 | 1.000 | 0.991 | 4623 | - |
| dev | plain | 83.7 | 0.857 | 0.857 | 1.000 | 0.991 | 5631 | - |
| dev | turns_rr | 86.9 | 0.902 | 0.902 | 1.000 | 1.000 | 5436 | - |
| dev | session | 92.2 | 0.991 | 0.991 | 0.991 | 0.991 | 6325 | - |
| dev | session8k (+runner-up) | 90.9 | 0.973 | 0.991 | 1.000 | 0.991 | 6743 | - |
| dev | session6k (+runner-up) | 88.3 | 0.929 | 0.929 | 1.000 | 0.991 | 5631 | - |
| dev | session8k1 | 92.4 | 0.991 | 0.991 | 0.991 | 0.991 | 5692 | - |
| dev | session8k1_rr | 92.1 | 0.982 | 0.991 | 1.000 | 1.000 | 5662 | - |
| dev | **session10k1_rr** | **92.5** | 0.991 | 1.000 | 1.000 | 1.000 | 6090 | - |
| dev200 | generic `hybrid_rr` (baseline) | 71.2 | 1.000 | 1.000 | 1.000 | 0.331 | 11938 | - |
| dev200 | turns | 87.3 | 0.909 | 0.909 | 1.000 | 1.000 | 5594 | - |
| dev200 | turns1 | 87.8 | 0.909 | 0.909 | 1.000 | 1.000 | 4130 | - |
| dev200 | plain | 87.4 | 0.909 | 0.909 | 1.000 | 1.000 | 5566 | - |
| dev200 | turns_rr | 87.4 | 0.909 | 0.909 | 1.000 | 1.000 | 5461 | - |
| dev200 | session | 93.1 | 1.000 | 1.000 | 1.000 | 1.000 | 6045 | - |
| dev200 | session8k | 93.0 | 1.000 | 1.000 | 1.000 | 1.000 | 6505 | - |
| dev200 | session8k1 | 93.3 | 1.000 | 1.000 | 1.000 | 1.000 | 5557 | - |
| dev200 | session8k1_rr | 93.3 | 1.000 | 1.000 | 1.000 | 1.000 | 5537 | - |
| dev200 | **session10k1_rr** | **93.1** | 1.000 | 1.000 | 1.000 | 1.000 | 5941 | - |

For reference, A's `rec_bm25` scores 93.0 on dev and 93.3 on dev200 (leaderboard). **Dev and dev200 are saturated for SSA:** the ceiling at about 5.5k chars is about 93.3 (S max = 95 − chars/3200). Every whole-session variant is within ±0.5 S of it, so the ≥2-point acceptance rule cannot separate them. I picked `session10k1_rr` because it is the only variant with SR = CF1 = 1.0 on both splits; the cross-encoder fixes the one session-pick miss that no-rerank variants have on dev. The choice between B and A has to be made on test answer quality (Reactor), not on these metrics.

Test audit (`harness.audit --variant session8k1 --n 12`, qualitative only):
- All 12 packs are 2.4 to 3.4k chars, since test gold sessions are short injected sessions.
- In 11 of the 12, the hint quotes exactly one first-person recommendation sentence whose purpose matches the question (Toggl Track, Matilda 159 Domain, pandas, VS Code, Moulin de Versailles, 0.022 µF, Scotiabank, Masters Swim Club, Coach Miriam, Riverdale Park East, BEVA 371).
- The Lisbon coworking question is flagged abstain_p = 0.84 (no cue sentence), as designed.

## Top failure patterns
1. **Turn-granular packing loses the gold turn when the top session has several long turns, even with rerank** (turns_rr PA 0.90). Examples:
   - "Bandung … Nasi Goreng": the gold turn is t7, but sibling turns that repeat "Miss Bee Providore" rank first (gold_rank 6).
   - "Andy wearing in the comedy script": the gold turn is the assistant's script, but the user's long brief ranks above it (gold_rank 20 to 28).
   - "Bajimaya … year construction began": the answer sits deep in a user-pasted case text (gold_rank 12 to 15).

   Whole-session packing at 5.5 to 6k chars is cheaper in S than any of these misses.
2. **A budget cut inside a long top session drops the answer chunk.** "DHL Wellness Retreats … influencer marketing" ($2,000): the gold turn is partly included, so ATR = 1 but AC = 0. "Radiation Amplified zombie … name" (Fissionator) at 8k. Raising the cap from 8k to 10k fixes the first kind at +400 chars on average.
3. **Session pick without the cross-encoder.** "What sealant … newspaper flower vase": an assistant sentence about releasing flowers into the ocean, in another session, won the NDCG session score (19.9 vs 9.8). The cross-encoder fixes it (SR 1.0).
4. **A runner-up contrast unit costs more than it buys on dev.** Inside the same budget it pushes out top-session chunks (session8k vs session8k1: −1.5 S). Keep it only when the top session is small, which is the test case.

## CORE REQUESTs
1. **Model-server throughput.** One rerank request waited 10 to 30 s behind the precompute and the other agents. The baseline dev SSA sweep took 30 min, almost all of it queueing for rerank. Please batch or prioritise small rerank requests, or precompute `rerank(q.question, hybrid(q.question, k=100))` for every dev, dev200 and test question. That is the cache-compatible pool my `_rr` variants use.
2. **A `build_pack` priority mode** that respects the order of `ranked` when the budget cuts, renders chronologically, and has a "whole session if ≤ N chars" option. The lens emulates this today with `window=0` and a hand-ordered uid list.
3. **An abstention probe for SSA:** `--ablate-gold`, which rebuilds the index without the gold sessions. Dev SSA has 0 unanswerables, so abstain_p (designed against the test-style Lisbon case) cannot be calibrated.

## Ideas for next round
- Keep a whole-session pack, but cut chars by trimming the top session at sentence level. Drop paragraphs of non-best turns whose rerank score is below the median: the target is about 4k chars with no PA loss, worth +0.5 S.
- On test, add the runner-up session's best unit **only when the top session is under 3k chars** (test-style injected sessions). This gives near-miss contrast and recall insurance at almost no cost on dev.
- Compare A and B on test answer accuracy with a Reactor sample (integrator-run). Dev cannot separate them.
- Check the hint's INSUFFICIENT_EVIDENCE note against the "Heden … has a good day pass" pattern (a recommendation with no cue verb). Option: only add the note when the top session also lacks the category word.
