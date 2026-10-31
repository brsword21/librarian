# KU lens B ("Semantyka"): round 1 report

Lens: `lenses/ku/b_semantic.py`. Runs: `runs/r1-ku-b/ku/{generic,b_semantic}/<variant>/{dev,dev200}`. Logs and audits are in `lenses/ku/scratch_b/` (`r1_*.log`, `r1_audit_pair_r1*.log`). The new CF1 miss reader is `scratch_b/cf1_miss.py`; `harness.failures` lists only PA<1, and every KU loss here is a CF1 loss.

**Best variant: `pair_r1b`.** Dev S 93.2 / dev200 S 93.1. The generic hybrid_rr baseline gets 83.8 / 83.5, and round-0 `pair_prf` gets 93.2 / 91.8.

Dev is saturated. The highest S possible at 3.7k chars is about 93.85 (PA 1, CF1 1). So the "+2 S on dev" acceptance rule cannot be met by any variant. `pair_r1b` ties on dev and gains +1.3 on dev200, which is test scale. It also adds the test-motivated assistant-recap path with no measured cost.

## Variants tried (one line each)
- `pair` (R0): hybrid user pool → unit and sentence cross-encoder → ownership, value and coverage features → session pair. Cites the pair plus 2 extra sessions, budget 6000, with a timeline hint.
- `pair_prf` (R0): `pair` plus a value-anchored second hop and a forward value link (`link_w=5`).
- `pair_decay` (R0): `pair_prf` plus a linear recency prior (`decay=1.5`). No change.
- `tight` (R0): `pair_prf` with only the pair in the pack (`extra=0`, budget 4000). Loses PA.
- `wide` (control): unit rerank top-2, ±1 window, 12k budget.
- `pair_asst` (R1): `pair_prf` plus assistant recap sentences rewritten to first person, scored like user sentences, `asst_pen=1`. The idea that test updates live in assistant turns comes from lens A's design.
  - v1 let assistant units take the user unit slots and lost one PA on dev200 (S 88.8).
  - v2 gives them their own slot. Now neutral.
- `pair_stem` (R1): `pair_prf` with the Snowball stemmer for coverage and candidate sentences, so "waking" matches "wake". +0.7 on dev200.
- `pair_before` (R1): `pair_prf` plus "before X" chronology. In old-mode questions, the session that best covers the before-clause terms must be the newer pair member (`before_pen=5`). +0.7 on dev200.
- `pair_r1` (R1): `pair_prf` + snowball + asst + before_chrono. Dev 93.2 / dev200 93.1.
- **`pair_r1b`** (R1): `pair_r1` plus two changes. Fewer chars, same pairs.
  - A reverse value link (`rev_link=3`): an earlier own sentence that shares a name with an update naming both the old and the new value.
  - Timeline hygiene (`tl_min_cov=0.2`): the hint no longer quotes off-attribute sentences or bare questions.
- `pair_r1c` (R1, rejected): `pair_r1b` plus a sentence window of −1 when the attribute sentence has no value. It loses one dev200 pair (Lake Michigan bass), −0.7.

## Results (KU only; dev 78 q / 72 answerable, dev200 26 q / 22 answerable)
| variant | dev S | PA | ATR | SR | CF1 | chars | AUC | dev200 S | PA | ATR | SR | CF1 | chars | AUC |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| generic/hybrid_rr (bar) | 83.8 | 0.972 | 0.979 | 0.986 | 0.812 | 11936 | 0.806 | 83.5 | 1.000 | 1.000 | 1.000 | 0.740 | 11923 | 0.852 |
| pair | 93.0 | 1.000 | 0.961 | 1.000 | 0.972 | 3662 | 0.875 | - | | | | | | |
| pair_prf (R0 best) | 93.2 | 1.000 | 0.961 | 1.000 | 0.979 | 3678 | 0.875 | 91.8 | 1.000 | 0.977 | 1.000 | 0.932 | 3752 | 0.864 |
| pair_decay | 93.2 | 1.000 | 0.961 | 1.000 | 0.979 | 3678 | 0.875 | - | | | | | | |
| tight | 91.8 | 0.972 | 0.940 | 0.979 | 0.979 | 2524 | 0.875 | - | | | | | | |
| wide | 90.5 | 1.000 | 0.982 | 1.000 | 0.972 | 11792 | 0.873 | 91.3 | 1.000 | 1.000 | 1.000 | 1.000 | 11700 | 0.886 |
| pair_asst (v2) | 93.2 | 1.000 | 0.961 | 1.000 | 0.979 | 3696 | 0.875 | 91.8 | 1.000 | 0.977 | 1.000 | 0.932 | 3782 | 0.864 |
| pair_stem | 93.2 | 1.000 | 0.965 | 1.000 | 0.979 | 3665 | 0.887 | 92.5 | 1.000 | 0.977 | 1.000 | 0.955 | 3742 | 0.886 |
| pair_before | 93.2 | 1.000 | 0.961 | 1.000 | 0.979 | 3678 | 0.875 | 92.5 | 1.000 | 0.977 | 1.000 | 0.955 | 3747 | 0.864 |
| pair_r1 | 93.2 | 1.000 | 0.965 | 1.000 | 0.979 | 3684 | 0.887 | 93.1 | 1.000 | 0.977 | 1.000 | 0.977 | 3767 | 0.886 |
| **pair_r1b** | **93.2** | 1.000 | 0.965 | 1.000 | 0.979 | 3669 | 0.887 | **93.1** | 1.000 | 0.977 | 1.000 | 0.977 | 3729 | 0.886 |
| pair_r1c (rejected) | 93.2 | 1.000 | 0.965 | 1.000 | 0.979 | 3677 | 0.887 | 92.4 | 1.000 | 0.977 | 1.000 | 0.955 | 3759 | 0.886 |

Against the baseline: +9.4 S on dev and +9.6 on dev200. CF1 goes from 0.81 to 0.98 and from 0.74 to 0.98, at about a third of the chars. Abstention AUC goes from 0.81 to 0.89 and from 0.85 to 0.89.

Lens A's best dev200 run at the time of writing (`pkv3w0_bm25`, BM25 only) was S 89.7.

`wide` has CF1 1.000 on dev200, so plain unit-rerank top-2 got every dev200 pair. That shows the pair features cost dev200 pairs before the R1 fixes. At 11.7k chars, though, it scores less.

## Top failure patterns (pair_r1b)
1. **Old-value questions with several earlier candidates.** The "previous" value is ambiguous.
   - "What was my previous personal best time for the charity 5K run?" (dev200). The gold old value is 27:45 (session 22). We cite session 77, "finished with a time of 27 minutes and 12 seconds", which is a charity 5K time but not a PB.
     The hint still lists all three statements in date order, so Reactor can answer. Only CF1 is lost.
   - "What new kitchen gadget did I invest in before getting the Air Fryer?" (dev). The Instant Pot session ("my new Instant Pot") has almost no lexical overlap with "kitchen gadget / invest".
     The before-clause rule fixed the dev200 copy, where the wrong partner was later than the anchor. On dev the wrong partner is earlier.
2. **Comparison questions.** "Do I go to the gym more frequently than I did previously?" The new value ("four times a week") sits in a sentence about a smoothie. The cross-encoder prefers an assistant-style question that contains "more frequently".
3. **Two mentions of the same item.** "What type of camera lens did I purchase most recently?" Two 70-200mm sentences compete, and we cite the more explicit one, which is the wrong session.
4. **Test (audit, qualitative).**
   - Retrieval misses paraphrased updates without the attribute noun. For "current job title", "promotion … Director of Clinical Services" is not in the top 40. The hint now quotes nothing misleading there (hygiene fix), but the pair is wrong.
   - Skateboard: the old name 'Decaf' sits one sentence before the "skateboard" sentence. The −1 window would fix it, but it cost a dev200 pair, so it is rejected.
   - Fixed on test by R1:
     - watercolour: the assistant recap "Margaret has retired, so your … class is now taught by Priya Nair" is now the top session;
     - rent: the pair is 18,000 → 22,000, with the brother decoy only as extra context;
     - ceramics, accountant, UX team (all decoys out of the pair), beehives and chapters all hold old + new.
5. **Abstention.** "Italian restaurants" (Korean in the history) and "Software Engineer Manager" (Senior Software Engineer) score 0.13 and 0.09. Every question word exists in the history, and the swap is only visible at the phrase level.

## CORE REQUESTs
1. **Sentence-level cross-encoder through `HistoryIndex`.** Add `hx.rerank_texts(query, texts)`. The lens calls `core.models.rerank` directly today, and that path is unstable under load: the sentence rerank was most of the 17-minute dev200 run while the server was shared by 16 sweeps.
2. **Honour `cite_plan` in submission for KU.** Gold KU is always exactly 2 sessions, and the pack shows 2 extra sessions for robustness. Citing them would cost about 0.33 F1 per question.
3. **Expose `analyze()` to the generic path.** The router finds about 19% of dev KU. When the best two sessions hold different own values with coverage ≥ 0.6, the generic path should add the timeline hint and cite the pair. Lens A asks for the same.
4. **`build_pack(pinned_uids=...)`.** The pair's units should always enter first; today this depends on ranking order.
5. **Server queueing or priority.** Sweeps from 16 agents at once made a 26-question run take 17 minutes. Cached reruns take 5 seconds.

## Ideas for the next round
- **Phrase-level abstention:** check bigrams like "Italian restaurant(s)" and "Engineer Manager" against the history, not single terms. That targets the entity swaps the current signal misses.
- **Old mode:** pick the old member as the value immediately preceding the newest one among own same-attribute statements, not the strongest.
- **Attribute paraphrase expansion** for the PRF hop (title → promoted / role / position; instructor → teach), probably borrowing lens A's 19 synonym groups. Gate the −1 sentence window on a quoted or capitalised name only, so it fixes the skateboard case without the bass regression.
- **`computed`** for numeric "new"-mode questions (the newest pair value). This only pays off if Reactor sample runs show the hint is followed.
