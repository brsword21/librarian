# SSU lens B "Semantyka": round 3 report

**Best variant: `lenses/ssu/b_r3_route.py` `ku11fn4s_p5`.** It is the route lens: the v1 wrapper `merged_r2` (role hand-off unchanged) with the inner lens `lenses/ssu/b_r3_ssu.py` `ku11fn4s_p5`.
**Fallback: `ku11fn4s`.** Its test packs are identical to v1: 0 of 45 changed, cites included.
Earlier reports: round 2 in `b_report_r2.md`, round 1 in `b_report_r1.md`.
Runs: `runs/r3-ssu-b/ssu/...` (gold type) and `runs/r3-ssu-b/ssu-routed/...` (`--route --type ssu`).
Test audits: `scratch_b/r3_audit_<variant>.txt`. Scratch tools: `scratch_b/r3_diag.py` (rank of the gold session), `r3_cmp.py` (per-question diff of two runs), `r3_abst.py` (abstention AUC per feature).

## What the lens does
The lens runs `a_struct2` `r3rn` (lens A, v1, imported unchanged). It adds one thing: a **KU recall backstop** that acts only on evidence.
- **When it fires.** All four conditions must hold:
  - the question has a knowledge-update cue (`b_merge.KU_CUE`: previous, before, still, now, same, do I, have I been, how often, ...);
  - the question is not recency or drift phrasing ("end up", "the last X I mentioned"), which r3rn's attribute-checked recency handles;
  - the top session is confident: score at least 0, i.e. the window `top - floor(-6)` is wider than r3rn's 6-logit window;
  - every session it adds stays above the absolute floor of -6.
- **What changes.** The competitor window widens from 6 to 11 logits, at most 4 sessions are kept, and the budget rises from 6000 to 8000 chars. The old value of an update sits 4 to 11 logits under the new one. Without the backstop it was cut by the window or by the 6000-char budget.
- **`_p5`.** Under the same gate, the cite also includes the best other packed session within 5 logits of the top: the old/new pair of a KU misroute.
- **Otherwise** the pack is byte-identical to r3rn. The hint and abstain_p never change.

## Results
Gold ssu = 70 dev q, 23 dev200 q. Routed ssu = 140 dev q, 38 dev200 q (the questions the router sends to ssu; the role hand-off sends 37 dev and 6 dev200 of them to ssa, as in v1). Every number comes from a full sweep with no `--limit`.

| variant (gold ssu) | split | S | Sall | PA | ATR | SR | CF1 | chars | AUC |
|---|---|---|---|---|---|---|---|---|---|
| generic hybrid_rr (kit baseline) | dev | 76.6 | 76.6 | 1.000 | 1.000 | 1.000 | 0.512 | 11934 | 0.924 |
| generic hybrid_rr (kit baseline) | dev200 | 73.5 | 73.5 | 1.000 | 1.000 | 1.000 | 0.407 | 11933 | 0.955 |
| v1 (merged_r2 role8_r3rn) | dev | 93.4 | 92.7 | 1.000 | 1.000 | 1.000 | 0.984 | 3619 | 0.906 |
| v1 | dev200 | 92.5 | 89.7 | 1.000 | 1.000 | 1.000 | 0.955 | 3859 | 0.955 |
| ku11fn4 | dev / dev200 | 93.4 / 92.4 | 92.7 / 89.3 | 1 / 1 | 1 / 1 | 1 / 1 | 0.984 / 0.955 | 3619 / 3943 | = |
| ku11f10n4 | dev / dev200 | 93.4 / 92.4 | 91.8 / 88.9 | 1 / 1 | 1 / 1 | 1 / 1 | 0.984 / 0.955 | 3802 / 4039 | = |
| ku11fn4s (fallback) | dev / dev200 | **93.4 / 92.5** | 92.7 / 89.7 | 1 / 1 | 1 / 1 | 1 / 1 | 0.984 / 0.955 | 3619 / 3859 | 0.906 / 0.955 |
| ku11f10n4s | dev / dev200 | 93.4 / 92.4 | 91.8 / 89.3 | 1 / 1 | 1 / 1 | 1 / 1 | 0.984 / 0.955 | 3802 / 3955 | = |
| **ku11fn4s_p5 (best)** | dev / dev200 | **93.4 / 92.5** | 92.7 / 89.7 | 1 / 1 | 1 / 1 | 1 / 1 | 0.984 / 0.955 | 3619 / 3859 | 0.906 / 0.955 |
| ku11fn4s_p11 | dev / dev200 | 93.3 / 92.0 | 92.7 / 89.7 | 1 / 1 | 1 / 1 | 1 / 1 | 0.979 / 0.939 | 3619 / 3859 | = |

| variant (routed ssu) | split | S | Sall | PA | ATR | SR | CF1 | chars | AUC | ku→ssu S / PA / CF1 |
|---|---|---|---|---|---|---|---|---|---|---|
| v1 (merged_r2 role8_r3rn) | dev | 86.1 | 88.3 | 0.932 | 0.960 | 0.980 | 0.894 | 4159 | 0.931 | 77.4 / 0.920 / 0.640 |
| v1 (= b_r3_ssu base) | dev200 | 82.3 | 82.6 | 0.886 | 0.929 | 0.943 | 0.867 | 4234 | 0.905 | 54.7 / 0.556 / 0.667 |
| ku11 | dev | 87.0 | 88.9 | 0.947 | 0.967 | 0.986 | 0.894 | 4319 | 0.931 | 79.9 / 0.960 / 0.640 |
| ku11 | dev200 | 85.9 | 86.1 | 0.943 | 0.971 | 0.971 | 0.867 | 4573 | 0.905 | 68.7 / 0.778 / 0.667 |
| ku11s (= ku11) / ku11b9 | dev200 | 85.9 | 86.1 | 0.943 | 0.971 | 0.971 | 0.867 | 4573 / 4592 | 0.905 | same |
| ku8 | dev | 86.6 | 88.4 | 0.939 | 0.963 | 0.982 | 0.894 | 4289 | 0.931 | 77.3 / 0.920 |
| ku8 | dev200 | 84.1 | 84.1 | 0.914 | 0.957 | 0.957 | 0.867 | 4469 | 0.905 | 61.7 / 0.667 |
| ku11f = ku11fn | dev | 86.6 | 88.7 | 0.939 | 0.967 | 0.984 | 0.894 | 4223 | 0.931 | 79.9 / 0.960 |
| ku11f = ku11fn | dev200 | 85.9 | 86.5 | 0.943 | 0.971 | 0.971 | 0.867 | 4449 | 0.905 | 68.9 / 0.778 |
| ku11fn4 | dev / dev200 | 86.6 / 87.8 | 88.7 / 88.5 | 0.939 / 0.971 | 0.967 / 0.986 | 0.984 / 0.986 | 0.894 / 0.867 | 4223 / 4484 | = | dev200 76.1 / 0.889 |
| ku11f10n4 | dev / dev200 | 87.0 / 87.7 | 89.0 / 88.3 | 0.947 / 0.971 | 0.967 / 0.986 | 0.986 / 0.986 | 0.894 / 0.867 | 4296 / 4516 | = | |
| ku11fn4s (fallback) | dev | 86.6 | 88.7 | 0.939 | 0.963 | 0.984 | 0.894 | 4205 | 0.931 | 80.0 / 0.960 / 0.640 |
| ku11fn4s (fallback) | dev200 | 87.8 | 88.8 | 0.971 | 0.971 | 0.986 | 0.867 | 4417 | 0.905 | 76.1 / 0.889 / 0.667 |
| ku11f10n4s | dev / dev200 | 87.0 / 87.8 | 89.0 / 88.6 | 0.947 / 0.971 | 0.967 / 0.986 | 0.986 / 0.986 | 0.894 / 0.867 | 4296 / 4466 | = | |
| **ku11fn4s_p5 (best)** | dev | **87.6** | 88.7 | 0.939 | 0.963 | 0.984 | **0.928** | 4205 | 0.931 | **85.4** / 0.960 / **0.820** |
| **ku11fn4s_p5 (best)** | dev200 | **88.1** | 88.8 | 0.971 | 0.971 | 0.986 | **0.876** | 4417 | 0.905 | **77.2** / 0.889 / 0.704 |
| ku11fn4s_p11 | dev | 87.9 | 88.7 | 0.939 | 0.963 | 0.984 | 0.938 | 4205 | 0.931 | 86.6 / 0.960 / 0.860 |
| ku11fn4s_p11 | dev200 | 88.6 | 88.8 | 0.971 | 0.971 | 0.986 | 0.895 | 4417 | 0.905 | 79.5 / 0.889 / 0.778 |
| abz (sentence-CE z-score abstention) | dev / dev200 | 86.1 / 82.3 | = v1 | = v1 | | | | | **0.384 / 0.705** | |

**Best against v1 on the routed ssu route:**
- **S:** +1.5 on dev, **+5.8 on dev200**.
- **Sall:** +0.4 on dev, **+6.2 on dev200**.
- **Gold ssu:** identical on both splits.
- **Hand-off routes:** the ssa share is unchanged (91.1 / 93.8). The multi and temporal misroutes are unchanged under the strict gate.

By the contract rule (+2 S on dev), the dev gain is +1.5 (p11: +1.8). The dev200 gain is large, and nothing loses on any split or type, which is why I recommend it.

## Test audit (`harness.audit --compare runs/audit/all/pipeline/routed/test_packs.jsonl`, all 45 ssu-routed test packs)
| variant | packs changed | what changes |
|---|---|---|
| ku11fn4 | 1 | q_962a82f81f3a (physiotherapist after the Toronto Marathon): passages 3→4. The added 4th session is the sister's Ottawa Marathon decoy. This motivated the strict gate. |
| ku11f10n4 | 1 | same pack |
| **ku11fn4s / ku11f10n4s** | **0** | none: hint, passages and cite are identical to v1 |
| **ku11fn4s_p5** / ku11fn4s_p11 | **1** | **q_b7053d97740b** ("café where I usually stop for a cappuccino before work"): cite 1→2, passages unchanged. See below. |

On the café pack, v1 cites `s_fb78000877ae` (06/08) alone. That session scores 7.32 on the unit "**Francesca** usually stops at Caffè Rivoire for a cappuccino before work … I usually just grab a quick espresso". It is a decoy: someone else's café. `_p5` adds `s_da52acbb5b7c` (06/05, score 7.23): "I usually stop at **Caffè Gilli** for a cappuccino before work". That is the user's own statement. The pair cite therefore adds the right session to a cite that held only the decoy. It matters only if `cite_plan` is used to filter Reactor's citations. Reactor sees the same passages as in v1.

The KU cue fires on 10 of the 45 test ssu-routed questions:
- 8 have "end up" phrasing (7 R-77 slots and the sourdough starter), so `ku_norec` excludes them;
- the physiotherapist question's top session is at -7.3, below the confidence gate;
- the café question passes the gate, but the widened window adds nothing to its pack.

## Variants tried (one line each; `lenses/ssu/b_r3_ssu.py`, route twins in `b_r3_route.py`)
- `base`: r3rn exactly (control). Reproduces v1, 82.27 on dev200 routed.
- `ku11`: KU cue → window 11 logits, budget 8000. Routed +0.9 / +3.6, but a weak top adds -10 junk sessions (Air Fryer +3.4k chars).
- `ku11s`: re-pack with every kept session's lead unit first. Identical to ku11: the budget was not the binding limit once it rose to 8000.
- `ku11b9` / `ku11_6k`: budget 9000 changes nothing; `ku11_6k` was not run because budget 8000 is what fixed the 5K question.
- `ku8`: window 8. Loses the mom grocery list (gap 10.2): dev200 84.1.
- `ku11f`: absolute floor -6 on the widened window. Same S as ku11, fewer chars, Sall +0.4 on dev200.
- `ku11fn`: + no backstop under recency phrasing. Same dev/dev200 numbers; removes 8 test firings.
- `ku11fn4`: + up to 4 sessions. dev200 87.8: Saturday wake-up time, where the gold sits in the 4th session.
- `ku11f10n4`: floor -10. +0.4 on routed dev (temporal "first issue after the first service": the gold is at -9.1), Sall −0.9 on gold dev.
- `ku11fn4s` / `ku11f10n4s`: strict gate, act only when the floor widens the window. Same scores, 0 test changes.
- **`ku11fn4s_p5`** / `ku11fn4s_p11`: + cite the best other packed session within 5 / 11 logits under the strict gate. p11 costs gold dev200 −0.5 (shampoo brand: second cite is wrong).
- `abz`: brief item 2. abstain_p from a pool-relative z-score of the best sentence-level CE logit over the top-12 user units. Rejected (AUC below).

## Brief items
1. **Recall backstop merged into r3rn without changing test packs:** done.
   - `ku11fn4s`: 0 of 45 test packs change.
   - `ku11fn4s_p5`: 1 cite change, the café pack above. No pack size changes.
   - Routed dev200 ku→ssu goes from S 54.7 / PA 0.556 to S 77.2 / PA 0.889.
2. **Sentence-level CE z-score abstention: negative result.** Offline on pooled routed rows (135 ssu-final rows, 11 unanswerable; `scratch_b/r3_abst.py`), AUC by feature:

   | feature | AUC |
   |---|---|
   | r3rn abstain_p | **0.892** |
   | absolute best user logit | 0.872 |
   | absolute best sentence logit | 0.850 |
   | z_user | 0.471 |
   | z_sent | 0.543 |
   | any mix with z_sent | ≤ 0.867 |

   Sweep `abz`: AUC 0.384 on dev and 0.705 on dev200. The z-score fails because unanswerable ssu questions still have a near-miss unit far above a pool of unrelated junk (z 3–9), exactly like answerable ones. The absolute logit level is what carries the signal. abstain_p stays as in r3rn.
3. **Slot-specific lexical check before the recency pick: not implemented.** It cannot be measured: r3rn makes **0** recency jumps on dev or dev200 (1 assistant-driven jump on dev), against 7 on test. Qualitative look at the 7 test jumps:
   - 5 look right: power-supply cap 33→47 µF, Cloudland Canyon, Big Green Egg, keg, speaker.
   - Screen-grid resistor jumps to the dial-lamp session. The top session is also a sibling slot (AGC), so the check would not fix it.
   - Sourdough jumps to a "bakery shop name" session. The check would revert it to the "levain" session; there is no gold to say which is right.

   Changing test cites without any dev evidence is not worth the one remaining test pass.

## Top failure patterns (after the best variant)
1. **Category → instance gap.** "What new kitchen gadget did I invest in before getting the Air Fryer?" (dev and dev200). The gold "I'm actually thinking of using my new **Instant Pot**" has CE −11.5 and session rank 13. No window or floor reaches it, so PA stays 0.
2. **The pair cite takes the 2nd-best session when the old value sits 3rd** (dev200, `_p5`):
   - "previous personal best time for the charity 5K": it cites #77 (a 27:12 run) next to #136. The gold old value 27:45 is in #22, which is packed but not cited.
   - "What time do I wake up on Saturday mornings?": the same pattern.

   CF1 drops 0.67 → 0.50 on these 2 questions. On dev, 13 pair cites are all correct.
3. **Multi misroutes without a KU cue** (dev 9 q, PA 0.571, unchanged). Examples: "What are the two hobbies that led me to join online communities?", "How old was I when Alex was born?", "At which university did I present a poster on my thesis research?". Each needs 2 sessions, and the 6-logit window keeps 1–2.
4. **A decoy sentence lifts its session through a mixed unit** (test café, above). Sessions are scored at unit level, so "Francesca usually stops at X … I usually just grab …" outranks the user's own "I usually stop at Caffè Gilli".

## CORE REQUESTs
1. **Adopt** `routes.ssu = lenses/ssu/b_r3_route.py ku11fn4s_p5`. It differs from v1 on test only in the café cite and needs no Reactor re-run for passages. If no cite may change at all, use `ku11fn4s`: test packs identical to v1, dev200 routed +5.5.
   - It imports the frozen files (`merged_r2`, `a_struct2`, `b_merge.KU_CUE`) and edits none of them.
   - Cost: one extra r3rn build on the ~10% of ssu-routed questions with a KU cue (rerank cached).
2. **`harness.audit --compare`:** also report hint, abstain_p and computed changes, and print the old/new cite ids. I checked these by hand.
3. **A drift check set.** Test plants recency/drift ("end up", "the last X I mentioned"; 11 of 45 ssu-routed test questions), but dev and dev200 contain almost none (0 recency jumps). Without a gold-free proxy, the recency logic cannot be tuned or validated. A small synthetic set would do: same-object sibling slots plus an update, built from dev histories.

## Ideas for the next round
- **Pair cite by value type, not by score rank.** Cite the packed session whose own unit states a value of the same type as the primary's (KU-B's value gate). This fixes pattern 2 and keeps the strict gate, so test exposure stays at 0–1 packs.
- **Sentence-level owner scoring of sessions.** Score a session by its best clean OWN sentence, not by its unit, so a decoy sentence cannot lift a mixed unit (pattern 4, test café).
- **Instance expansion for category questions.** Run hx.dense_texts over the user sentences with "my new X / I got / I bought" in the top-20 sessions, to bridge "kitchen gadget" → "Instant Pot" (pattern 1).
- **Multi hand-off inside the ssu wrapper.** Hand off on an aggregate/relational cue ("two …", "how old was I when …", "both") plus two clean own sessions within 6 logits. Needs a check on test firings first.
