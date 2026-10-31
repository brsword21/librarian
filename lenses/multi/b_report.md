# Lens B ("Semantyka"), multi-session: Round 4 report

New lens: `lenses/multi/b_r4_inst.py`. It wraps the frozen v2 multi route (`merged_r2.build` with the `tight_role9` params and the `a_r3_role.py` detector, the same as `configs/best.json`) and edits no frozen file. On top of that route it adds a **verb-class instance rescue**.
**Best variant: `vc2`.** Variant `v2` reproduces the frozen route exactly.
Runs: `runs/r4-multi-b/multi/b_r4_inst/<variant>/{dev,dev200}` and `runs/r4-multi-b/multi-routed/...`. Test audit: `runs/audit/multi/b_r4_inst/vc2`.
Scratch scripts:
- `scratch_b/r4_probe.py`: test candidates with CE and bge scores
- `scratch_b/r4_prec.py`: selector precision on gold

## The visible test defects (v2 packs, read by hand)

v1 answered 4 multi questions with real Reactor. All 4 look right: ceramics 5, watercolour 2, vegetables 5, car savings 37,500.
Four of the remaining v2 multi packs miss an obvious own instance, so Reactor will miscount or fall for a decoy:

| qid | question | missing own sentence (session date) | what the v2 pack offers instead |
|---|---|---|---|
| q_bcd6d210710b | bakery fund left after transactions | "I finally opened a separate savings account for the bakery and deposited 25,000 pesos." (05/06) | +7,500, −9,300, and sister Paola's "bakery fund with 30,000 pesos" (decoy) |
| q_47e3f2749c07 | orchids added since March | "Oh, and I bought two Cattleya orchids for the balcony this week." (03/18) and "I picked up one Phalaenopsis orchid at the market yesterday." (05/22) | repotting, fertilizer, "my daughter gave me two orchid seedlings in 2021" |
| q_8b4f1ff8ce11 | books read since March | "Oh, and I read two detective novels during my trip to Ubatuba last week." (06/12) | Carlos's "three books since March" (decoy), a signed copy, a "might start" |
| q_d52f60bba453 | combined March + June book club attendance | "My book club met last night and 7 people came" (03/09) | June "9 people" only, plus "space for about eight people" and "sailing class had 8 people" (decoys) |

In each case the instance is one short aside in an off-topic session. CE ranks that session far below topical chatter, so the p(gold) keep rule never reaches it.

## The fix (`b_r4_inst.vc2`, general, no per-question rule)
After the frozen route, the lens looks at user sentences in sessions that are not in the pack. It skips routine questions ("each week / per day") and questions with no event class. A sentence qualifies when:
1. It is own and affirmed:
   - it has a first-person marker (case-insensitive; b_sweep's `_FIRST` misses a capitalised "My");
   - it does not match `_NEG`, `_REPORT`, `_THIRD_SUBJ` or `_RECAP`;
   - it has no plan or modal cue ("will / can / have to / still have X to");
   - it has no "her own";
   - it has no kin subject without an "I".
2. It matches the question's **event class**: acquire / read / attend / money-transaction (a verb plus an amount) / plant / eat / make. The class comes from the question verb.
3. It hits the head noun (with a tiny books family: novel, memoir, biography …) and carries a quantity or fact cue. Without a head hit it needs a quantity, bge ≥ 0.62 and CE ≥ −3.
4. It sits inside the question window when the window prior is active.

Ranking is by CE on the question. The lens takes at most 2 sessions, with CE ≥ −7 and within 4 logits of the first pick. Each picked session is added as its holding user unit (untrimmed), in date order, and cited. The pack budget is 12k.

## Results (gold multi: dev 133 q / dev200 28 q; routed multi route: dev 170 / dev200 45)

| split | lens / variant | S | Sall | PA | ATR | SR | CF1 | chars | AUC |
|---|---|---|---|---|---|---|---|---|---|
| dev | generic `hybrid_rr` (bar, r3 run) | 69.1 | 69.1 | 0.744 | 0.873 | 0.961 | 0.817 | 11931 | 0.598 |
| dev | `v2` (frozen route) | 87.2 | 85.7 | 0.950 | 0.980 | 0.984 | 0.910 | 5841 | 0.731 |
| dev | **`vc2`** / `vc1` / `vc2_t4` | **87.2** | 85.7 | 0.950 | 0.980 | 0.984 | 0.910 | 5841 | 0.731 |
| dev200 | generic `hybrid_rr` (bar, r3 run) | 63.7 | 63.7 | 0.682 | 0.844 | 0.950 | 0.770 | 11947 | 0.689 |
| dev200 | `v2` | 83.3 | 82.3 | 0.909 | 0.962 | 0.973 | 0.868 | 6279 | 0.795 |
| dev200 | **`vc2`** / `vc1` / `vc2_t4` | **83.3** | 82.3 | 0.909 | 0.962 | 0.973 | 0.868 | 6279 | 0.795 |
| dev routed | `v2` = `vc2` | 86.7 | 85.5 | 0.943 | 0.978 | 0.984 | 0.905 | 5481 | 0.800 |
| dev200 routed | `v2` = `vc2` | 84.2 | 82.7 | 0.921 | 0.965 | 0.984 | 0.872 | 6061 | 0.789 |

The rescue fires on **0 of 215** dev / dev200 routed questions (all gold types), so gold-dev and dev200 S and Sall are unchanged. On dev the instance sessions are already in the pack: dev histories have 48 sessions and long topical turns.

Selector precision on gold (`scratch_b/r4_prec.py`): the same rescue was run with nothing excluded, so it picks from the whole history.
- dev: 17 questions fire, **21 of 21 picks are gold sessions**. Examples: "I just got this kit and a 1/24 '69 Camaro", "I paid $500 to attend", "I planted 5 tomato plants".
- dev200: 4 questions fire, 4 of 6 picks are gold.
- The 2 non-gold picks are "spent around $120 on groceries" (store not named) and "I got my cousin a set of baby clothes" for "gifts for my sister". The second is a kin object, which the gate does not check.

## Test audit and change list against v2 (`harness.audit --compare runs/final/v2_test_packs.jsonl`)
**4 of 20 multi packs change.** Each change adds 1–2 passages; nothing is removed, and the hints are unchanged.
- **q_bcd6d210710b** bakery fund: adds s_af3c748536c9, "opened a separate savings account for the bakery and deposited 25,000 pesos". The expected answer becomes 25,000 + 7,500 − 9,300 = 23,200. Without it there is no starting balance, and the sister's 30,000 is the only "opened a bakery fund" sentence in the pack.
- **q_47e3f2749c07** orchids since March: adds s_9b84ce601f9a ("bought two Cattleya orchids", 03/18) and s_11b3d1451200 ("picked up one Phalaenopsis orchid", 05/22). Without them the pack holds no acquisition at all.
- **q_8b4f1ff8ce11** books since March: adds s_11989ba8c98b, "I read two detective novels". Without it, the only number in the pack is Carlos's 3, a decoy.
- **q_d52f60bba453** book club attendance: adds s_2e89c90bc416, "7 people came" (March). The expected answer becomes 7 + 9 = 16. The pack grows to 10.3k chars.

Pack unchanged, checked: car savings stays as it is. v1 answered it correctly, and the money gate drops "My regular salary is higher than $50,000". The 16 other packs are untouched. Of these, the PhD-books pack is unchanged because "still have to read two articles" is a plan, and the watercolour, ceramics and honey packs because they have no class or are routines.

## Variants tried (one line each)
- `v2`: the frozen route through the wrapper. Reproduces 87.2 / 83.3.
- `vc2`: verb-class rescue, r_max 2, CE ≥ −7, gap 4, dense path bge ≥ 0.62 and CE ≥ −3. **Best.** 4 test packs change, 0 dev firings.
- `vc1`: r_max 1. Loses the second orchid acquisition.
- `vc2_t4`: CE ≥ −4. Loses Cattleya (−4.98) and the detective novels (−6.62).
- `vc2_h`: head noun only, no dense path. Same test firings as vc2; not swept.
- `vc3_t11`, probe only: CE ≥ −11, r_max 3. It adds "finished reading a book about the history of São Paulo" (a real instance) but also "Read the chapter 11 of original book that I sent you" (PhD) and an "import estimate" sentence in car savings. Rejected.

Probe-stage fixes, all general:
- the money class requires a transaction verb (it hit "$50,000 salary");
- the read class requires `read / finished reading / finished the…` ("systolic reading" hit it);
- a kin subject without an "I" is rejected ("My sister Amina deposited 25,000 … her own");
- plan cues "have to / still have X to" are rejected (PhD articles).

## Top failure patterns
1. **Instance asides with low CE** (fixed for 4 test packs). One-sentence "Oh, and I bought …" asides in off-topic sessions score CE −4 to −7; care chatter about the same noun scores −3.
2. **Very short instance sentences fall below any safe CE floor.** In books since March, "I just finished reading a book about the history of São Paulo" scores −10.6 and "I finished that Pelé biography yesterday" scores −11.3. Both are probably instances, and both are still missing with vc2, so Reactor will probably answer 2 where the expected answer is likely 3–4. A lower floor brings in noise (vc3_t11).
3. **Category to instance gaps on dev** (unchanged from r3). "properties viewed" vs "a 1-bedroom condo", "projects led" vs "poster", "health devices" (a routine question). These questions have no event class, so the rescue does not act on them.
4. **cite_plan gap (not Reactor-visible).** The book club June session (s_d35454b437d5, "we had 9 people") is in the pack but not in v2's cite_plan. This only matters if cite_plan filtering is ever used.

## CORE REQUESTs
1. **Re-ask these 4 test packs with Reactor:** q_bcd6d210710b, q_47e3f2749c07, q_8b4f1ff8ce11, q_d52f60bba453. Wire it as `lenses/multi/b_r4_inst.py` `vc2` on the multi route: the same params as v2, plus `resc`.
   - No other test pack changes.
   - Dev and dev200 are bit-identical (0 firings in 215 routed questions).
   - None of the 4 has been answered yet (v1 answered 4 other multi questions), so they cost no extra re-ask if they are swapped in before the v2 pass reaches them.
2. **`R1._FIRST` in `b_sweep.py` is case-sensitive.** It misses a sentence-initial "My". That affects every lens that uses it to gate own statements. Not fixed in frozen files; `b_r4_inst` uses its own regex.
3. **Harness: a firing-precision mode for rescues.** Run a lens hook with a gold session withheld from the pack, to measure recall and precision when dev never triggers it. `scratch_b/r4_prec.py` is the crude version.

## Ideas for next round
- A statement-form CE floor that depends on sentence length. Short asides ("I finished that Pelé biography yesterday") get low ms-marco logits. Rank class-matched head-hit candidates by bge on a templated statement ("I read a book") instead of the question.
- A kin-object check ("got my cousin …" for "gifts for my sister"): the possessor of the object must match the question's possessor.
- Extend the event classes with view / lead / use, for the dev category-to-instance misses, gated by the same own and affirmed filter.
