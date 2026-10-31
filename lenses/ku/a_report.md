# KU lens A ("Struktura"): Round 3 report

Lens: `lenses/ku/a_r3.py`. It wraps the frozen v1 ku route, `lenses/ku/b_r2.py` r2b. Retrieval and pair logic are lens B's, imported and never edited. Every change is a variant flag. `a_r3` `r2b` reproduces frozen `b_r2` r2b exactly: 0 packs differ on dev and on dev200.

**Best variant: `r3w`.** A more conservative alternative is `r3a`, which is `r3w` without the weak-pair rescue.

Other files:
- Round-2 report: `a_report_r2.md`.
- Runs: `runs/r3-ku-a/ku/{generic,b_r2,a_r3}/<variant>/{dev,dev200}` and the routed slice in `runs/r3-ku-a/ku-routed/`.
- Test audits: `runs/audit/ku/a_r3/<variant>/test_packs.jsonl`.
- Diffs against v1: `scratch_a/r3_audit_r3w.txt` (passages / cite) and `scratch_a/r3_hintdiff_r3w.txt` (hint / computed, from `scratch_a/r3_hintdiff.py`).
- v1 ku packs: `scratch_a/v1_ku_test_packs.jsonl`.

## Headline
- **Dev and dev200 cannot separate these changes.** Gold-type ku is saturated (PA 1.000 on both splits), and every dev/dev200 ku gold turn is a user sentence that contains the attribute word.
  - `r3w` against frozen r2b: 1 dev pack differs (q_bda6debf4b81 pre-1920 coins: hint `37 + 1 = 38`, computed 38 = gold, HA 1.0). 0 dev200 packs differ. S, Sall, PA, CF1 and AUC are identical. chars are 3044 vs 3043 on dev and 3072 vs 3072 on dev200.
- **Test: 5 of 20 ku-routed packs change.** All five are failures that the round-2 audit, or the real Reactor, showed. Each is fixed by a general rule.
- **Real-Reactor finding (v1, running now).** On ku-routed packs, B's line "Cite both the session with the earlier value and the session with the latest value" works.
  - Ceramics was answered `Ana Ferreira [E1][E3]` (it skipped the context passage E2). Accountant was answered `Bruno Almeida [E1][E2]`.
  - So the ku evidence F1 of 0.5 in the calibration comes from **ku questions routed to multi or ssu**. Those packs carry no such line, and there Reactor cited only the newest on 3 of 3 (bikes, Canon trips, Hawaii).
  - I therefore **dropped my label-explicit citation line (`lab`)** from the recommendation: it would have changed all 20 test hints to fix something that already works. See CORE REQUEST 2.
  - Job title in v1 was answered `INSUFFICIENT_EVIDENCE` (pack without the promotion). `r3w` fixes that pack.

## Variants tried (one line each)
1. `r2b`: control. b_r2 r2b through this file's `build()`; 0 pack diffs against the frozen lens.
2. `tl` (`tl_pair`): the hint timeline keeps both pair statements when it has more than 4 lines. r2b keeps the oldest 4 (`tl[:4]`), so on test laps the "30 laps" update was cut from the hint while four "40 laps" lines were quoted.
3. `lab`: the citation line names the pair's labels: "cite both [E1] (the earlier value) and [E2] (the latest value)". Labels match cite_plan on 72/72 dev and 17/17 dev200 labelled packs. Not recommended, because B's line already works (see Headline).
4. `rel`: relative update. In "how many" questions, "added / bought / planted N (new|more)" after an older single count gives computed = old + N, plus a hint line. It is blocked by cumulative markers (so far, since, already, total, I have ...), by a second count in the newest sentence, and by question numbers.
   - The older count may sit in another sentence of the old session.
   - The first draft fired wrongly on 4 dev questions (postcards, H&M tops, to-watch list, coins as 1920). After tightening: dev 1 firing, correct (coins 38); test 1 firing (apple trees 4 + 3 = 7).
5. `adm` / `adm4`: CE admission of a newer own change statement over the pair's new member (gap 2 / 4). **0 firings** on dev, dev200 and test: ms-marco CE scores paraphrases low.
6. `hab`: habitual questions ("each morning / these days"). An episodic new member ("40 laps today") yields to an own change statement. **0 firings** on all three splits: on current caches B's pair for test laps is already right (04/15 "40 laps" → 08/21 "increased my morning swim to 30 laps"); only the hint was wrong (fixed by `tl`).
7. `wa` / `wa2`: wider assistant-recap pool (`asst_k` 30→80 / 120, `asst_depth` 20→40 / 60). 0 dev/dev200 changes. On test, the recap "You mentioned your long run has shifted to Sundays at 6:30 a.m." now enters the pack and the hint (v1 had no 6:30 passage at all).
8. `wag`: `wa` plus `lab` gated on B's confidence gate (generic "cite two passages" line otherwise).
9. `wago`: `wag` plus **per-owner totals** ("my neighbor Bjørn and I in total"). There is one count timeline per owner: absolute statements set the value and "bought 2 more" adds to it. "X's daughter" and "my sister" are excluded. The hint gives the arithmetic, computed is the sum, and all owner sessions are cited. 0 dev/dev200 firings; 1 on test.
10. `wagoa`: `wago` with labels only when abstain_p < 0.5, worded "If you answer, ...". In `wago`, 5 of 6 dev ku unanswerables got labels.
11. `r3a`: `tl_pair` + `rel` + `wa` + `owner`, keeping B's citation line. 4 test packs change.
12. **`r3w`**: `r3a` plus a **weak-pair rescue**.
    - When both pair members score < 0 (an off-attribute pair; mode "new"), candidates are own first-person change statements with a value, not questions, from the dense + BM25 top 60 user units, newer than the old member and outside the pair.
    - The best candidate by sentence CE replaces the new member if its CE is higher than the new member's. It is quoted in the hint.
    - On dev/dev200 the rule is checked 4 times (1 answerable volleyball question, 3 unanswerable) and admits nothing.
    - On test it fires once: job title, admitting "I got another promotion, so now I am Director of Clinical Services" (CE −7.09 vs −7.90 for the "Marketing Director" request).

Variants 2–7 were swept before a hint-filter bug was fixed (pair statements briefly bypassed B's `tl_min_cov` hygiene). That bug changed hints only, not S. `r2b`, `wag`, `wago`, `wagoa`, `r3a` and `r3w` were run after the fix.

## Results (gold type ku: dev 78 q / 72 answerable, dev200 26 q / 22 answerable)

| variant | dev S | Sall | PA | ATR | SR | CF1 | chars | AUC | dev200 S | Sall | PA | ATR | SR | CF1 | chars | AUC |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| generic hybrid_rr (bar) | 83.8 | 83.8 | .972 | .979 | .986 | .812 | 11936 | .806 | 83.5 | 83.5 | 1.000 | 1.000 | 1.000 | .740 | 11923 | .852 |
| frozen b_r2 r2b (v1) | 93.4 | 93.6 | 1.000 | .993 | 1.000 | .979 | 3043 | .926 | 93.3 | 92.7 | 1.000 | 1.000 | 1.000 | .977 | 3072 | .898 |
| a_r3 r2b (control) | 93.4 | 93.6 | 1.000 | .993 | 1.000 | .979 | 3043 | .926 | 93.3 | 92.7 | 1.000 | 1.000 | 1.000 | .977 | 3072 | .898 |
| tl | 93.4 | 93.6 | 1.000 | .993 | 1.000 | .979 | 3058 | .926 | 93.3 | 92.7 | 1.000 | 1.000 | 1.000 | .977 | 3110 | .898 |
| lab | 93.4 | 93.6 | 1.000 | .993 | 1.000 | .979 | 3091 | .926 | 93.3 | 92.7 | 1.000 | 1.000 | 1.000 | .977 | 3143 | .898 |
| rel | 93.4 | 93.6 | 1.000 | .993 | 1.000 | .979 | 3092 | .926 | 93.3 | 92.7 | 1.000 | 1.000 | 1.000 | .977 | 3143 | .898 |
| adm / adm4 / hab / wa / wa2 | 93.4 | 93.6 | 1.000 | .993 | 1.000 | .979 | 3092 | .926 | 93.3 | 92.7 | 1.000 | 1.000 | 1.000 | .977 | 3143 | .898 |
| wag / wago | 93.4 | 93.6 | 1.000 | .993 | 1.000 | .979 | 3080 | .926 | 93.3 | 92.7 | 1.000 | 1.000 | 1.000 | .977 | 3116 | .898 |
| wagoa | 93.4 | 93.6 | 1.000 | .993 | 1.000 | .979 | 3094 | .926 | 93.3 | 92.7 | 1.000 | 1.000 | 1.000 | .977 | 3126 | .898 |
| r3a | 93.4 | 93.6 | 1.000 | .993 | 1.000 | .979 | 3044 | .926 | 93.3 | 92.7 | 1.000 | 1.000 | 1.000 | .977 | 3072 | .898 |
| **r3w (best)** | **93.4** | **93.6** | 1.000 | .993 | 1.000 | .979 | 3044 | .926 | **93.3** | **92.7** | 1.000 | 1.000 | 1.000 | .977 | 3072 | .898 |

HA (dev, `rel` and later variants): 1.000 on the 1 computed question. The routed ku slice (`--route --type ku`) is identical for r2b, wag, wago, r3a and r3w: dev 89.0 (17 q: 15 ku at 94.1, 2 ssu at 51.3), dev200 91.6 (4 q). Build time on dev200 is about 1.2 s per question with cold caches, against about 0.5 s for r2b.

**Acceptance.** The "+2 S on dev" bar cannot be met, because ku is saturated. `r3w` is a tie on dev and dev200 with the same chars, and it fixes 5 test packs that are wrong or misleading in v1 (listed below). Choose `r3a` if the weak-pair rescue (its only firing is on test) is too much test-driven change.

## Test packs this change modifies (`r3w` vs v1 `runs/final/v1_test_packs.jsonl`, ku route, 20 packs)
Route changes: 0. Passage / cite changes: 3. Hint / computed changes: 5. The other 15 packs are byte-identical in hint, passages, cite_plan and computed.
1. **q_b3e5afe916c8 "What is my current job title?"**
   - Before: v1 sent a junk pair (a press-release request plus a "Marketing Director" career request), and real Reactor answered INSUFFICIENT_EVIDENCE.
   - After: the pair is [06/27, **08/24 "I got another promotion, so now I am Director of Clinical Services."**], and that sentence is quoted in the hint. Cite 2→2 (kept 1); passages 3→3 (kept 2).
2. **q_eb3a2b633378 "What time does my long run start these days?"**
   - Before: v1 had no passage stating the current time.
   - After: the assistant recap 06/24 "my long run has shifted to Sundays at 6:30 a.m." enters the pair and the hint. Cite 2→2 (kept 1); passages 3→3 (kept 2: 03/12 "Saturdays at 7:00 a.m." and 07/08 playgroup).
   - The pair is [06/24, 07/08 playgroup]. The playgroup line is a near-miss: the 03/12 → 06/24 pair would be better (see failures).
3. **q_a90a3ef2db02 "How many Icelandic horses do my neighbor Bjørn and I have in total right now?"**
   - Before: v1 quoted my 9 and the decoy "Bjørn's daughter has 2".
   - After: the per-owner hint reads "me 9 + 2 = 11 (bought 2 more, 05/02); Bjørn 5 (assistant, 03/14); total 16", with computed 16. Cite 2→3; passages 3→3 (kept 1).
4. **q_be4ffb1f8c06 apple trees:** the hint gains "The later statement adds 3 to the earlier 4: 4 + 3 = 7." and computed is 7. The pack is unchanged.
5. **q_074ae81650db laps:** the hint now quotes the newest "After my check-up I increased my morning swim to 30 laps." in place of the oldest "40 laps" line. The pack is unchanged.

## Top failure patterns (remaining)
1. **ku questions routed to ssu or multi lose the old session in the citation** (calibration, real Reactor).
   - bikes (multi pack): it listed E1 = 3 and E2 = 4, then cited only [E2].
   - Canon trips (multi): it cited only [E7].
   - Hawaii (ssu): it cited only [E2].
   - Every ku gold has exactly 2 sessions, so each such answer gets CF1 ≤ 0.667. This is 59 of 78 dev ku questions (27 → ssu, 32 → multi). It is the biggest ku citation loss and lies outside the ku lens (CORE REQUEST 2).
2. **The new member is a near-miss newer than the true update** (test long run): "playgroup moved to 9:00, keep my long-run start early" (07/08) outranks the 06/24 recap. The time value "9:00" belongs to the playgroup, not the run. A value-attribution check (does the time attach to the attribute noun?) is needed.
3. **Another person's value fills the old slot when the user's own old statement is missing** (test coffee: "Carlos drinks three cups"). The pack still contains the right newest ("switched to just one cup"), so PA is fine and CF1 is about 0.5.
4. **Aggregate-in-ku questions** (test "How many rooms have we completely renovated in the bungalow so far?"). No count is ever stated ("We just refinished the dining room", ...), so the question is really a multi-style count. The ku pair holds two unrelated renovation remarks.
5. **CE admission is blind to paraphrase.** ms-marco CE scores "I got another promotion, so now I am Director of Clinical Services" at −7.1 for "What is my job title?". The weak-pair rescue works only because everything else scores even lower. bge sentence cosine ranks it first (0.60), so it is the better signal for a future admission rule.

## CORE REQUESTs
1. **Routing config:** route ku to `lenses/ku/a_r3.py` variant **`r3w`** (or `r3a`).
   - It imports `lenses/ku/b_r2.py` and `lenses/ku/b_semantic.py` unchanged, so all three files must ship.
   - Test diff: the 5 packs above. The pack file is `runs/audit/ku/a_r3/r3w/test_packs.jsonl`; regenerate it with `python -m harness.audit --lens lenses/ku/a_r3.py --variant r3w --type ku --compare <v1 ku packs>`.
2. **ssu and multi lens owners (biggest ku citation lever):**
   - When a "now / currently / these days / so far / anymore / still" question ends up on the ssu or multi route, add B's line "Cite both the session with the earlier value and the session with the latest value."
   - Real Reactor follows it on ku-routed packs (2 of 2) and ignores the implicit version on multi/ssu packs (cited only the newest on 3 of 3).
   - On multi, add it only to the "If the number changed over time, use the most recent statement" clause.
3. **`harness.audit --compare` should also diff `hint` and `computed`.** Today hint-only changes, like 2 of my 5, are invisible to the "list every test pack you change" check. `lenses/ku/scratch_a/r3_hintdiff.py OLD NEW` does this in 25 lines and reads both the audit format and the v1 `question_text` format.

## Ideas for the next round
- **Admission by bge sentence cosine** (`hx.dense_texts`) instead of CE for weak or ambiguous pairs, gated on a value of the same type as the old member.
- **Value attribution:** the value must attach to the attribute noun ("long run ... at 6:30", not "playgroup ... at 9:00") before a sentence can be the new member.
- **Own old member:** when the old member has own ≤ 0 (Carlos), replace it with the best own older session that has a value, or cite the newest alone.
- **ku → ssu hand-off** with ssu-A / ku-B's value-disagreement gate (dev200 9 q at S 55). The `owner` and `rel` rules would also help there, because the ssu pack never computes old + added.
- **`rel` on the multi route** for "how many ... currently" questions (bikes: 3 → "got a new one" → 4).
