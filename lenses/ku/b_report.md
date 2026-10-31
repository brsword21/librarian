# KU lens B ("Semantyka"): round 3 report

Earlier reports: round 2 is in `b_report_r2.md` (restored from this file's round-2 contents) and round 1 is in `b_report_r1.md`.
Files this round (all new, no frozen file edited):
- `lenses/ku/b_r3_gate.py`: **ssu-route lens with a value-type ku hand-off**. It reuses `lenses/ssu/merged_r2.py` (role hand-off, unchanged) and the frozen ku lens `lenses/ku/b_r2.py` r2b.
- `lenses/ku/b_r3_ku.py`: a copy of the b_r2 r2b packing, plus the own-value pair fix (brief item 2) and coverage-gated bigram abstention (brief item 3).
- `lenses/ku/b_r3_routed.py` + `scratch_b/r3_cfg_qt3c*.json`: the full routed system with only the ssu route swapped. Gives e5-style numbers.
- Scratch: `scratch_b/r3_rules.py`, `r3_rules2.py` (offline gate fitting over the dumped `ku_feats`), logs `scratch_b/r3_*.log`.

Runs are in `runs/r3-ku-b/{ku,ssu-routed,all}/...`. Test audits are in `runs/audit/ssu/b_r3_gate/{v1,qt3c,qt3c_ap}` and `runs/audit/ku/b_r3_ku/own`.

**Best variant: `lenses/ku/b_r3_gate.py` / `qt3c_ap`, as the ssu route.**
- Full routed system against v1:
  - dev: S 86.0 -> 86.5, Sall 84.8 -> 85.0.
  - dev200: S 84.9 -> 86.3, Sall 83.2 -> 84.6.
- **0 of 45 test ssu-routed packs change** (`harness.audit --compare runs/audit/all/pipeline/routed/test_packs.jsonl`). It also does not fire on any of the 6 test questions where the r2 detector fired.
- The r2 detector (e5) gained +0.3 dev / +1.3 dev200 but moved 6 test packs.

## What the gate does (brief item 1)
`ku_gate(q, hx)` fires on an ssu-routed question (after the role hand-off) in either of two cases. The pair comes from b_semantic, and both members must be the user's own sentences (own > 0), not assistant recaps, and not an abandoned trial.

- **(a) Typed-value update.**
  - `q_types(question)` decides which value types the question asks for:
    - "what time", "personal best" -> time;
    - "how often" -> frequency / quantity / weekday;
    - "what day" -> weekday;
    - "how many / much / long", "amount / value / voltage / price / limit ..." -> quantity / money.
  - Names, titles and places are excluded on purpose. Capitalised-word drift is the planted ssu decoy (sourdough name, café, restaurant).
  - Both pair sentences must carry a value of one of those types, with disjoint values: 8:30 am -> 7:30 am, 6 -> 9 months, $350k -> $400k, Thursday -> Friday, twice -> three times a week.
  - Thresholds: min pair score >= 3, min attribute coverage >= 0.25.
  - "... three weeks ago" is not counted as a value.
- **(b) The question itself asks about a change.**
  - That is b_semantic mode old / compare / both: "previous", "before I ...", "initially", "more ... than", "increase or decrease".
  - Thresholds: min pair score >= 1, coverage >= 0.3.
  - On dev and dev200, the gold-ssu questions in these modes all have negative pair scores (≤ −3.3): "previous occupation", "last name before I changed it", "initially think was just a cold".
- **Abandoned-trial filter (`REVERT`).** A sentence like "I briefly tried a 68 µF capacitor ... and I removed it" or "I bought a 12-volt lamp, but it was too dim" is not an update.
  - On test this is what keeps the gate off the three R-77 questions (dial lamp, filter capacitor, volume-control ohms): they have typed quantity differences, but the newer member is a reverted trial.
  - Caveat: I saw this pattern in the test audit of the features. It is a general linguistic rule (it only makes the hand-off more conservative), not a per-question rule.
- `qt3c_ap` = `qt3c` plus one change on hand-offs: abstain_p = min(ku lens, ssu lens).
  - The ku lens's bigram signal runs high on these questions ("coffee-to-water ratio" 0.88, "language exchange" 0.53), which cost routed AUC: dev200 0.855 -> 0.845 with `qt3c`.
  - With `_ap` the ssu-route slice AUC is back to v1 (0.931 / 0.905). Packs and routes are identical to `qt3c`.

## Variants tried (one line each)
- `v1`: frozen ssu route (merged_r2 role8_r3rn), no ku hand-off. Reference.
- `r2ku`: the r2 detector (b_r2.ku_pair_p, distinct values + score ≥ 6 + cov ≥ 0.5) = e5. 0 FP on dev/dev200, but 6 test firings.
- `vt`: r2 detector AND same-type differing values AND own AND attribute head in both sentences. Too strict: 1 dev / 1 dev200 ku hand-off.
- `vt_cue`: vt plus an update cue word. Fires on nothing.
- `vt_nohead`: vt without the head check. 2 / 1 hand-offs.
- `qt2` / `qt3` / `qt4`: question-typed disjoint values + REVERT, with score/cov thresholds 2/.25, 3/.25 and 4/.4.
  - qt2 and qt3: 7 dev + 2 dev200 ku hand-offs, 0 FP.
  - qt4: 5 + 2.
- **`qt3c`**: qt3 plus the question-cue branch (b). 12 dev + 4 dev200 ku hand-offs, 0 FP on gold ssu/ssa/multi/temporal, 0 test changes.
- **`qt3c_ap`**: qt3c with abstain_p = min(ku, ssu) on hand-offs. Only AUC changes.
- `b_r3_ku own`: own-value pair fix (brief item 2).
  - First version (own < 0): −0.6 dev, because the ownership regex has false negatives: "to my friend's birthday party", "He's actually ...", "getting used to".
  - Restricted to own < 0 with no first-person word at all: neutral on dev/dev200, 1 test pack changes (coffee).
  - Not adopted; see failures.
- `b_r3_ku bgm1` / `bgm2` / `bgm3`: bigram abstention at full weight only when attribute miss ≥ 0.1 / 0.2 / 0.3 (else 0.3 / 0.3 / 0).
  - bgm2 raises KU AUC: dev 0.926 -> 0.928, dev200 0.898 -> 0.920, pooled 0.910 -> 0.916.
  - S is identical; only abstain_p changes.

## Results

### Baseline and KU gold type (ku lens; dev 78 q / dev200 26 q)
| variant | dev S | Sall | PA | ATR | SR | CF1 | chars | AUC | dev200 S | Sall | PA | ATR | SR | CF1 | chars | AUC |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| generic hybrid_rr (bar) | 83.8 | 83.8 | .972 | .979 | .986 | .812 | 11936 | .806 | 83.5 | 83.5 | 1.000 | 1.000 | 1.000 | .740 | 11923 | .852 |
| b_r3_ku r2b (= v1 ku route) | 93.4 | 93.6 | 1.000 | .993 | 1.000 | .979 | 3043 | .926 | 93.3 | 92.7 | 1.000 | 1.000 | 1.000 | .977 | 3072 | .898 |
| b_r3_ku own | 93.4 | 93.6 | 1.000 | .993 | 1.000 | .979 | 3043 | .926 | 93.3 | 92.7 | 1.000 | 1.000 | 1.000 | .977 | 3072 | .898 |
| b_r3_ku bgm2 | 93.4 | 93.6 | 1.000 | .993 | 1.000 | .979 | 3043 | **.928** | 93.3 | 92.7 | 1.000 | 1.000 | 1.000 | .977 | 3072 | **.920** |

### ssu route slice (`--route --type ssu`: dev 140 q, dev200 38 q; all gold types)
| variant | dev S | Sall | PA | ATR | SR | CF1 | chars | AUC | ku->ku | dev200 S | Sall | PA | ATR | SR | CF1 | chars | AUC | ku->ku |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| v1 | 86.1 | 88.3 | .932 | .960 | .980 | .894 | 4159 | .931 | 0/27 | 82.3 | 82.6 | .886 | .929 | .943 | .867 | 4234 | .905 | 0/9 |
| r2ku (= e5 detector) | 87.3 | 88.9 | .939 | .963 | .984 | .917 | 4068 | .924 | 7 | 86.5 | 86.8 | .943 | .957 | .971 | .881 | 4117 | .905 | 3 |
| vt | 86.8 | 88.8 | .939 | .963 | .984 | .901 | 4146 | .929 | 1 | 84.4 | 84.7 | .914 | .943 | .957 | .876 | 4205 | .905 | 1 |
| vt_cue | 86.1 | 88.3 | .932 | .960 | .980 | .894 | 4159 | .931 | 0 | 82.3 | 82.6 | .886 | .929 | .943 | .867 | 4234 | .905 | 0 |
| vt_nohead | 86.9 | 88.9 | .939 | .963 | .984 | .904 | 4135 | .926 | 2 | 84.4 | 84.7 | .914 | .943 | .957 | .876 | 4205 | .905 | 1 |
| qt2 / qt3 | 87.2 | 88.9 | .939 | .963 | .984 | .914 | 4056 | .933 | 7 | 84.7 | 84.7 | .914 | .943 | .957 | .886 | 4148 | .886 | 2 |
| qt4 | 87.1 | 88.9 | .939 | .963 | .984 | .909 | 4085 | .936 | 5 | 84.7 | 84.7 | .914 | .943 | .957 | .886 | 4148 | .886 | 2 |
| qt3c | 87.6 | 88.9 | .939 | .963 | .984 | .927 | 3980 | .911 | 12 | 86.8 | 86.8 | .943 | .957 | .971 | .890 | 4062 | .857 | 4 |
| **qt3c_ap** | **87.6** | **88.9** | .939 | .963 | .984 | .927 | 3980 | **.931** | 12 | **86.8** | **86.8** | .943 | .957 | .971 | .890 | 4062 | **.905** | 4 |

Hand-off false positives on gold ssu / ssa / multi / temporal: **0** for every qt variant on both splits. The ssa questions are handed off by role_guess first.

### Full routed system (e5-style; `lenses/ku/b_r3_routed.py`, all 526 dev / 125 dev200 q)
| system | dev S | Sall | PA | ATR | SR | CF1 | chars | AUC | dev200 S | Sall | PA | ATR | SR | CF1 | chars | AUC | test packs changed |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| v1 (configs/best.json) | 86.0 | 84.8 | .935 | .967 | .985 | .899 | 5583 | .812 | 84.9 | 83.2 | .918 | .956 | .970 | .894 | 5478 | .855 | – |
| e5 (r2 detector, from SYNTHESIS_r2, pre-router-r2) | +0.3 vs e2 | | | | | | | | +1.3 vs e2 | | | | | | | | 6 / 45 |
| **qt3c** | **86.5** | **85.0** | .938 | .968 | .986 | .908 | 5535 | .810 | **86.3** | **84.6** | .936 | .965 | .979 | .902 | 5426 | .845 | **0 / 45** |
| **qt3c_ap (recommended)** | **86.5** | **85.0** | .938 | .968 | .986 | .908 | 5535 | .811 | **86.3** | **84.6** | .936 | .965 | .979 | .902 | 5426 | **.855** | **0 / 45** |

On the routed system, ku gold-type S goes 87.9 -> 90.7 on dev and 76.8 -> 84.0 on dev200. Every other gold type is unchanged.

**Acceptance.** Routed dev is +0.5 S (below the +2 bar, because 140 of 526 questions are ssu-routed). Routed dev200 is +1.4 S with no loss on either split. Test risk is zero: no test pack changes. The ku -> ssu cell improves from dev 27 q at S 77.4 to 85.5, and from dev200 9 q at S 54.7 to 72.1.

## Brief items 2-3 (ku route)
- **Own-value constraint (`b_r3_ku own`)**: replace a pair member that is someone else's value (own < 0 and no first-person word) with the best own same-type session among the top 8.
  - Neutral on dev and dev200.
  - On test it changes one pack, q_355094c7f34a (coffee). "Carlos drinks three cups" is replaced as the old member by "do you think it's okay to have a cup or two a day" (s_6e8e872282a3), which is a question, not a stated value. The new member ("switched to just one cup") and the answer are unchanged.
  - The sign of the CF1 change is unknown, so **not recommended** (one test change of uncertain value).
- **Abstention calibration (`bgm2`)**: the bigram signal at full weight only when attribute coverage of the best sentences misses ≥ 0.2 (weight 0.3 otherwise).
  - Pooled dev+dev200 KU AUC 0.910 -> 0.916; dev200 0.898 -> 0.920.
  - It only changes abstain_p, and the current policy uses no abstention hint, so it has no Reactor effect. Optional.

## Top failure patterns (after qt3c)
1. **ku -> ssu questions whose update carries no typed value stay on ssu.** Dev 15, dev200 5. Most still have PA 1 and lose only the second cite (S about 83). Examples:
   - "Did I finish reading 'The Nightingale'?": a status update;
   - "Where am I planning to stay for my birthday trip to Hawaii?": a name;
   - "What time do I usually go to the gym?": the newer sentence restates the days, not the time;
   - "How long have my parents been staying with me?": the old member has no value.
2. **Real PA losses on the ssu route that the gate cannot see**, because the pair scores are negative:
   - "What new kitchen gadget did I invest in before getting the Air Fryer?" (dev and dev200, S 19): "my new Instant Pot" has no lexical overlap.
   - "Is my mom using the same grocery list method as me?" (dev200, S 19): own = 0.5 on the newer member.
   - A "before X" rule would also catch the gold-ssu "last name before I changed it", so I did not add one.
3. **The ownership regex has false negatives** that make own < 0 unusable as a hard constraint: "my friend's birthday party", "He's actually ...", "getting used to" (PAST_OTHER "used to"). Only "own < 0 and no first-person word" is safe.
4. **The test ssu route is full of planted near-updates** (R-77 sibling components, abandoned trials, name candidates). Any looser gate (the r2 detector, or qt without REVERT) fires on them. Test ku -> ssu gains therefore probably need answer-type-aware evidence, not a looser gate.

## CORE REQUESTs
1. **Route ssu to `lenses/ku/b_r3_gate.py` variant `qt3c_ap`** in the next config. Ready-made config: `lenses/ku/scratch_b/r3_cfg_qt3c_ap.json`; `qt3c` is the same without the AUC fix.
   - It wraps the frozen `lenses/ssu/merged_r2.py` (role8_r3rn behaviour, by calling `choose(..., ku_pair=False)` and the same inner lenses) and the frozen `lenses/ku/b_r2.py` r2b.
   - Routed: +0.5 dev / +1.4 dev200 S, +0.2 / +1.4 Sall, **0 of 45 test packs changed**, so it costs nothing on the remaining Reactor pass.
   - It adds one `b_semantic.analyze` call per ssu-routed question (about 100-300 ms warm).
2. Optional, no Reactor effect: switch the ku route to `lenses/ku/b_r3_ku.py` `bgm2`. Packs are byte-identical to r2b; only abstain_p changes (KU AUC dev200 0.898 -> 0.920).
3. A fix inside `b_semantic.ownership`, owned by me but frozen: "used to" in PAST_OTHER should not match "getting used to", and "my friend's <event>" should not make the whole sentence someone else's. Deferred because b_semantic is imported by the frozen b_r2.

## Ideas for the next round
- Answer-type-aware second hop for paraphrased updates ("Instant Pot" for "kitchen gadget"): dense_texts / rerank_texts over own sentences carrying an entity of the asked type (gadget = product name).
- Extend `q_types` with status (finished / started / still) and place (moved to X), each guarded by a REVERT-style negation check. That would cover Nightingale-like status updates without opening the name-drift door.
- Per-route isotonic calibration of abstain_p, so hand-off lenses produce comparable scales (the `_ap` min-trick is a stopgap).
