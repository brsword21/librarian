# KU lens A ("Struktura"): Round 1 report

Lens: `lenses/ku/a_timeline.py`. Best variant: **`pkd_b2`**. Fallback with no model server: **`pkl_b1`**.
Scratch scripts: `lenses/ku/scratch_a/` (`dbg_q.py`, `dbg_test.py`, `nsent_acc.py`, `bigram_abst.py`, `ku_all200.py`). Snapshot lens copies used for the slow background sweeps are `a_timeline_snapshot_pkh.py`, `a_timeline_snap2.py` and `a_timeline_snap3.py`. All runs are under `runs/r1-ku-a/ku/`.

## Results (KU only: dev 78 q / 72 answerable, dev200 26 q / 22 answerable)

| variant | dev S | PA | ATR | SR | CF1 | chars | AUC | dev200 S | PA | ATR | SR | CF1 | chars | AUC |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| generic `hybrid_rr` (bar) | 83.8 | .972 | .979 | .986 | .812 | 11936 | .806 | 83.5 | 1.000 | 1.000 | 1.000 | .740 | 11923 | .852 |
| `tl_bm25` (R0 draft) | 89.0 | .958 | .898 | .951 | .951 | 5946 | .847 | 81.8 | .864 | .909 | .932 | .917 | 5935 | .955 |
| `pk_base` (R1 packing only) | 89.7 | .958 | .919 | .986 | .951 | 3759 | .847 | 82.2 | .864 | .909 | .955 | .909 | 3783 | .955 |
| **`pkl_b1`** (BM25 only) | 91.0 | .972 | .919 | .986 | .965 | 3774 | .906 | 90.2 | .955 | .932 | .977 | .977 | 3812 | .943 |
| `pkl_rerank` | 91.0 | .972 | .940 | .993 | .965 | 3788 | .906 | 88.8 | .955 | .932 | .977 | .932 | 3804 | .943 |
| `pkd_noadmit` | 90.8 | .972 | .933 | .993 | .958 | 3791 | .906 | 89.5 | .955 | .932 | .977 | .955 | 3820 | .943 |
| `pkd` (admit 3, +0.4) | 92.1 | .986 | .954 | 1.000 | .972 | 3787 | .904 | 93.1 | 1.000 | .955 | 1.000 | .977 | 3786 | .920 |
| `pkd5` (admit 5) | 92.8 | 1.000 | .954 | 1.000 | .965 | 3801 | .904 | 88.8 | .955 | .932 | 1.000 | .932 | 3778 | .920 |
| **`pkd_b2`** (admit 3, +0.2) **BEST** | **92.1** | .986 | .954 | 1.000 | .972 | 3785 | .904 | **93.1** | 1.000 | .955 | 1.000 | .977 | 3787 | .943 |
| `pkv` (value-typed list) | 91.0 | .972 | .919 | .986 | .965 | 3783 | .906 | 88.8 | .955 | .909 | .977 | .932 | 3803 | .943 |
| `pk2_hop` (unit second hop) | 91.0 | .972 | .919 | .986 | .965 | 3773 | .906 | 89.5 | .955 | .932 | .977 | .955 | 3810 | .943 |
| ref: B `pair_prf` | 93.2 | 1.000 | .961 | 1.000 | .979 | 3678 | .875 | 91.8 | 1.000 | .977 | – | .932 | 3752 | .864 |

`pkr`, `pkl_nolink`, `pkd2` and `pkd_old` have the same S as the row they derive from (`pkl_b1` or `pkd_b2`). `pkl_nolink` has AUC .852 on dev and .955 on dev200. `pkd2` has AUC .909 on dev and .943 on dev200. `pkd_ch2` scores 92.1 on dev and 92.4 on dev200 (CF1 .955). The ceiling for dev S at about 3.8k chars is 93.8 (PA = CF1 = 1).

**Choice.** `pkd_b2` beats `pkl_b1` by +1.1 on dev and +2.9 on dev200 (both PA misses on dev200 are fixed: PA 1.000, SR 1.000). It does not reach the formal +2 bar on dev. On dev that bar is nearly out of reach, because `pkl_b1` is already 2.8 below the ceiling, and dev200 is the split that separates lenses. If the integrator applies the rule strictly, `pkl_b1` is the winner. It needs no model server and builds in about 10 ms.

Compared with B: A has higher S on dev200 (93.1 vs 91.8), higher CF1 on dev200 (.977 vs .932) and higher AUC (.904/.943 vs .875/.864). B is ahead on dev (93.2 vs 92.1).

## Variants tried (one line each, in order)
1. `tl_bm25` / `tl_*` (R0): `build_pack` with ±1 windows and a 6000 budget. A single chatty session could fill the whole budget, so a cited session dropped out of the pack and the citation plan had only one session.
2. `pk_bm25`: own `assemble()`, pair-first packing (best mention unit of O and N, then 2 backup sessions with 1 unit each, then neighbours of the pair while the 4000-char budget lasts). Chars went from 5.9k to 3.8k, but ATR fell because the best mention was not always the gold turn.
3. `pkq3`: up to 3 mention units per pair session from distinct turns, plus a 0.3 penalty for user question sentences. PA recovered (dev 90.1).
4. Answer-frame words dropped from the key ("type of", "name of", "increase or decrease", comparatives in compare questions). Sentence-side stems keep stopwords so rule synonyms (got, new) can match. "H&M" kept as one token, contractions treated as stopwords.
5. `pkc` / `pkv3`: numeric continuity. A later restatement of the anchor's quantity counts as "newest" even with partial word coverage. Conditions: number within ×5, compatible unit (the word after the number), some question proper noun in the unit, cov ≥ 0.3. Also need_val: for quantity questions the newest mention must state a value. dev200 went from 84.9 to 89.2 (Instagram 1250→1300, Converse 4→6, Emma 2→3).
6. Budget grid (3000 / 3500 / 4000 / 4500, extra 1–2, pair units 2–3): 4000/2/3 is best. 3500 loses PA on dev200, and 4500 only adds chars.
7. `pkh`: head-noun penalty for "how many X" (−0.4 when X or its synonyms are absent). Neutral on dev; removes beehive lines from the test "cats" timeline.
8. `pkq_v`: values that the question itself names are dropped ("5K", matched as a whole token so "7" in "7/22" survives). +1 correct newest sentence on dev.
9. `pkl`: name link. An update that names the old value plus a new one ("Marta … referred me to Bruno", "hired Ana … after Miguel moved") qualifies as newest, and O is the mention whose name it repeats. This is the same idea as B's step 5b. Neutral on dev; fixes the accountant, ceramics and watercolour pairs on test.
10. `pkl_b1`: abstention gets +0.1 per question content bigram that never occurs as a phrase in user turns ("italian restaurants", "table tennis", "engineer manager"). AUC .852→.906 on dev and .955→.943 on dev200. With the unit fix, dev200 is 90.2.
11. `pks` (synonym hit = 0.5 credit): −0.7 on dev200, rejected. `pk2_hop` (BM25 second hop on question + unit word): one wrong pick on dev200, rejected. `pkv` (BM25 list restricted to units with a value of the asked type): finds the test long-run recap but loses one citation on dev200, kept as an option. `pkr` (raw-form synonyms, no double counting inside a synonym group, request penalty): neutral.
12. `pkl_rerank` (cross-encoder over the top 30): 91.0 / 88.8. The unit-level cross-encoder does not help this structure.
13. `pkd*`: user-only dense list in the RRF, and the dense model's top-k user units admitted as mentions with a coverage floor of 0 and a bonus. k=3 is best: k=5 adds noise on dev200 and k=0 is no better than BM25. Bonus 0.2 keeps S and gives better AUC than 0.4. `pkd_old` (admitted mentions can never be the newest) has no effect. `pkd_ch2` (continuations must contain 2 question words): −0.7 on dev200, rejected.

## Failure patterns (best variant `pkd_b2`, plus the test audit)
1. **A paraphrase with no question words is the newest value** (dev, PA miss): "What type of vehicle model am I currently working on?" Gold: "I have just wrapped up a model and switched to a Ford F-150 pickup truck". The dense user-only rank is 6–7 and BM25 ranks it 87, so the admission cut at top 3 misses it. On test, "What time does my long run start these days?" fails the same way: the update is the assistant recap "your long run has shifted to Sundays at 6:30 a.m." at BM25 rank 142. `pkv` finds it; `pkd_b2` picks "playgroup got moved to 9:00 a.m." instead.
2. **A late low-coverage sentence is promoted to newest.** Continuity or admission picks a filler line with a value of the same kind. Test UX team: the planted "My UX team now has eight people…" is followed by "Six people is solid for summer.", which becomes the newest. Dev200 tidying: "dedicating 15 minutes every morning to tidying" competed with "4 weeks"; the unit check fixed it in `pkl_b1`, but it is still a citation miss in `pkd_b2`. Test job title: "it's the lecturer's job…" and "the role of a Marketing Director" come after "I got another promotion, so now I am Director of Clinical Services".
3. **Wrong older session when the old value is repeated.** Dev "most recent family trip": Hawaii appears in two sessions, and O picks the one that is not gold (CF1 .5). Dev "camera lens": the old 50mm sentence says "got a new 50mm prime lens", and O picks another session. Dev "Saturday wake-up": 8:30 is stated twice. All of these keep PA=1 and lose citation precision only.
4. **Test generator contradictions and multi-owner totals (not fixable lexically).** For rent, the planted "moved … now pay 22,000" is followed by "My current rent is only 9,000, shared." For "Bjørn and I in total", the lens builds one timeline, not one per owner.

## CORE REQUESTs
1. **Model server throughput.** With about 15 concurrent sweeps, one generic `hybrid_rr` KU sweep took 23 min (dev), a cold dense query took about 49 s and rerank40 about 11 s. I saw sweep workers whose parent had died (ppid 1, from killed sweeps) that may still be sending requests. Please clean those up and consider a request queue per agent. Once caches are warm, `pkd_b2` runs in 6–7 s per split.
2. **Move `assemble()` into `core.pack`.** It is a pair-first packer: priority groups of session → units, try the full group then shorter prefixes, then neighbour fill. Every lens that cites a fixed set of sessions needs it, and `build_pack` lets one chatty session eat the budget.
3. **Router / generic path:** use `a_timeline.analyse()` as an evidence-based KU detector (unchanged from R0). Honour `cite_plan` in the submission: KU gold is always exactly 2 sessions.
4. **Optional: `HistoryIndex.value_units(regex)`,** a cached list of units containing a value type, for the `vlist` idea.

## Ideas for the next round
- **Gate admission and continuity on the attribute's modifiers**, not just the head noun. "Six people is solid" lacks "UX team"; "15 minutes … tidying up my bedroom" lacks "routine". Every key word that distinguishes the attribute from its siblings should be required. Combine with `pkv` and accept only if dev200 holds.
- **Self-statement detector for the newest value.** Prefer "I am / my X is / now I / I switched / I moved" over requests and interest ("I'd like to know more about the role of…") when picking the newest mention. Rate it by the share of newest sentences that contain the answer (`scratch_a/nsent_acc.py`: currently 48/72 dev and 13/22 dev200, with yes/no questions never matching).
- **Sentence-level cross-encoder only for the newest/older choice** among the 3–4 strongest own mentions (B's CORE REQUEST `rerank_texts`), keeping my structure for packing and the hint.
- **One timeline per owner** for "X and I in total", with a summed `computed` value; relative updates ("2 more") applied to the previous value in `computed`.
- **Abstention:** add B's coverage-miss signal to the missing-phrase signal and calibrate on dev + dev200 together (10 unanswerable in total, so AUC is noisy).
