# Lens B "Semantyka", multi-session: Round 1 report

Lens: `lenses/multi/b_sweep.py`. **Best variant: `deep8_10k`.**
Runs: `runs/r1-multi-b/multi/b_sweep/<variant>/{dev,dev200}`; test audit: `runs/audit/multi/b_sweep/deep8_10k`.
Scratch: `scratch_b/cite_fit.py` (fits cite rules offline on `debug["sess"]` from per_question.jsonl) and `scratch_b/atr_diag.py` (for each gold turn that was missed: its rank, its rank inside its own session, and whether its session made the pack).

## Result

| split | variant | S | PA | ATR | SR | ALL | CF1 | chars | AUC |
|---|---|---|---|---|---|---|---|---|---|
| dev (133 / 121 ans.) | generic `hybrid_rr` (baseline) | 69.1 | 0.744 | 0.873 | 0.961 | 0.893 | 0.817 | 11931 | 0.598 |
| dev | R0 `sweep` | 79.8 | 0.884 | 0.963 | 1.000 | 1.000 | 0.867 | 11915 | 0.644 |
| dev | `sf_rel4` | 85.4 | 0.959 | 0.987 | 1.000 | 1.000 | 0.895 | 11950 | 0.644 |
| dev | `deep8` | 86.5 | 0.975 | 0.990 | 0.994 | 0.984 | 0.895 | 11944 | 0.644 |
| dev | **`deep8_10k`** | **86.6** | 0.967 | 0.989 | 0.994 | 0.984 | 0.896 | **9949** | 0.644 |
| dev200 (28 / 22 ans.) | generic `hybrid_rr` (baseline) | 63.7 | 0.682 | 0.844 | 0.950 | 0.864 | 0.770 | 11947 | 0.689 |
| dev200 | R0 `sweep` | 73.1 | 0.818 | 0.949 | 1.000 | 1.000 | 0.788 | 11928 | 0.833 |
| dev200 | `sf_rel4` | 81.6 | 0.909 | 0.983 | 1.000 | 1.000 | 0.874 | 11951 | 0.833 |
| dev200 | `deep8` | 84.5 | 0.955 | 0.985 | 0.991 | 0.955 | 0.874 | 11949 | 0.833 |
| dev200 | **`deep8_10k`** | **85.2** | 0.955 | 0.985 | 0.991 | 0.955 | 0.874 | **9951** | 0.833 |

For reference, lens A `a_tally` `bm25_12k` scores dev 83.4 and dev200 81.2 on the leaderboard.

## Variants tried (one line each; dev S / dev200 S)
- `sweep` (R0 default): multi-query hybrid (question, core, 2 rule-based statements, facets) → CE on the top 90 → priors (fact, window, agent) → session-first selection (22 sessions, 4 units each) → sentence-trimmed snippets (320 chars) → cite rule "CE within 3 of the top" → **79.8 / 73.1**
- `sweep_wide` (14.5k chars, 30 sessions, CE on 120): 80.7 / 73.0. The extra chars buy no PA on dev200.
- `sweep_tight` (8k chars, 12 sessions, 2 per session): 71.6 / 66.0. Too few units per session (ATR 0.89).
- `sweep_noprior` (no fact or agent prior): 82.1 / 78.3. On dev the priors **hurt**: the fact prior pushes "by the way" sentences from unrelated sessions forward.
- `sweep_user` (no assistant recaps): 79.8 / 73.1, identical to `sweep`.
- `sessagg` (Emergence-style NDCG session score, top 10 sessions, `build_pack`): 71.8 / 68.2. Too few sessions; it loses ALL.
- `decay*` (greedy unit pick where the k-th unit of a session is worth 0.6^k): 72.9 to 74.0 / 70.9 to 74.7. Worse than session-first: depth goes to on-topic chit-chat.
- `sf_topk` (no priors + cite "top-3 by fused score + CE within 2", max 4): 80.2 / 74.7. Chosen on 40 questions, worse on the full split (**CF1 0.81 vs 0.87**). Lesson: fit cite rules on the full split.
- `sf_topk_in` (+ **intra-session CE**: every user unit of the top 15 sessions gets a CE score): 80.2 / 74.7. Useful only together with depth (next line).
- `sf_in6` / `sf_in8` / `sf_in8t` (per-session cap 6 / 8 / 8 with trim 240): 81.8 / 82.3 / 82.9 on dev, 74.7 / 77.6 / 77.6 on dev200. Gold fact turns sit 4th to 6th inside their own session.
- `sf_in6f` (the same with the fact prior): 81.4 / 77.1. The prior is no help.
- `sf_rel3` / `sf_rel4` (cite = sessions whose best CE logit over ALL scored units, intra-session ones included, is within 3 / 4 of the top; 2 to 5 / 2 to 6): 85.2 / 81.4 and **85.4 / 81.6**. CF1 0.81 → 0.895.
- `deep8` (+ depth first: the 8 strongest sessions get up to 8 units before the remaining sessions get their first unit): **86.5 / 84.5**.
- `deep8_16` (max 16 sessions): 86.5 / 84.5, identical.
- **`deep8_10k`** (`deep8` at a 10k budget): **86.6 / 85.2** with about 2k fewer chars.

Also in the best variant: "days apart" questions are now parsed. The kind becomes `dates` (facets are split on "apart were X and Y"), the hint says "date each event, then subtract", and the "only count what I did" and agent prior are dropped, so "my son's school play" is not treated as a decoy. Questions that mention family words count as `others_ok`. Questions that ask for a rate ("each morning", "each week", "these days") get a current-value hint ("the most recent statement wins"). These hint changes leave the dev metrics unchanged and target what the test audit showed.

## Top failure patterns (deep8_10k)
1. **A category word with no lexical or dense link to the instance.** "How many projects have I led…": the gold turns say "participated in a case competition" and "presented a poster". Neither appears in the hybrid pool, and the CE scores them low, so 2 of 4 gold sessions are missing (ALL 0). "health-related devices" → "hearing aids" ranks 77th, 5th inside its own session.
2. **Depth beats breadth for 2 questions.** With `deep_top` the pack holds only about 8 to 12 sessions on dev. "How many magazine subscriptions do I currently have?" loses a 4th gold session (s_52006560a680), which ALL 0.994/0.984 also shows. dev200 loses one question the same way. Breadth-first lost more questions on ATR, so this trade-off was the net win.
3. **The gold turn is an assistant turn.** In "charity cycling", the gold turn is the assistant's "Congratulations on … raising $250". The lens keeps only assistant units that are short recaps ("you mentioned…"), so this one is never a candidate.
4. Abstention is weak on dev (AUC 0.64) and decent on dev200 (0.83). Most unanswerable dev questions have one missing facet ("30-gallon tank"), and the missing-terms check catches only some of them.

Test audit (12 packs, no flags, 8 to 17 sessions each): the window prior engages (spans of about 175 days). Packs still carry topical chit-chat units in the depth slots: the R-77 radio question has grandchildren gift talk next to the "replaced the volume…" sentence. These cost chars but not recall. For the systolic-reading count, the 17 sessions are about the number of in-window mentions, so breadth may become the binding limit on test-style counting.

## CORE REQUESTs
1. **Use `cite_plan` for multi citations** (or `cite_plan ∩ Reactor's [E#]`). The pack holds 8 to 17 sessions for recall, while gold has 2 to 5. Citing every passage drops CF1 from about 0.89 to roughly 0.5.
2. `harness.failures`: also print the gold turn's rank **inside its session** (see `scratch_b/atr_diag.py`). That diagnostic found the per-session-cap problem in a single run.
3. `hx.rerank` over **sentence texts** (a cached `models.rerank` on arbitrary strings is already there; an `hx.rerank_sents(query, uid)` helper would standardise it). Test facts are one sentence inside a unit, and CE on the 700-char unit dilutes them.
4. Shared-server etiquette: two agents ran the identical generic baseline at the same time (r1-multi-a and r1-multi-b), which doubled the server load. Have the integrator run the generic baselines once per type and publish them.

## Ideas for the next round
- **Relevance floor for depth units.** Skip a depth unit whose CE logit is below about top − 8. This saves chars on test, where packs carry chit-chat, and the freed budget can go back into breadth for counting questions with many instances (test "systolic > 130 in August").
- **Adaptive depth versus breadth.** Use `deep_top` when the CE scores are concentrated in a few sessions (dev-style) and breadth when many sessions score well (test-style repeated measurements). The signal is how many sessions sit within 3 logits of the top.
- **Sentence-level CE** on the trimmed snippet (see CORE REQUEST 3). This should help ATR on test and fix the "case competition" miss if the sentence is scored on its own.
- **Abstention:** add A's conjunct and facet absence check (+0.25 for each facet with no stem match). Facets are already parsed here.
- **Computed answers** for `dates` kind questions: extract the event dates (explicit dates or relative words resolved against the session date) and put the difference in `computed`, but only once Reactor spot checks confirm the extraction.
- Merge with A: A's lexical sweep and category LEXICON would cover pattern 1. Combined with this lens's CE cite rule and per-session depth, the merged lens is likely better than either.
