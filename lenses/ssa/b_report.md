# SSA lens B ("Semantyka"): round 4 report

Earlier reports: `lenses/ssa/b_report_r3.md` (round 3) and `lenses/ssa/b_report_r2.md` (round 2).

Files:
- `lenses/ssa/b_r4_quote.py` (new). It wraps the frozen v2 ssa lens `a_recsent r2_conf2` and adds an in-session quote fallback (brief item 1). No frozen file was edited.
- Scratch:
  - `lenses/ssa/scratch_b/r4_decoy_scan.py` (+ `r4_decoy_scan_test.log`): history-wide check of the recommendation sentences against each ssa test pack.
  - `r4_quote_probe.py`: in-session candidates scored by CE(question), CE(kind + purpose) and dense.
  - `r4_quote_eval.py`: quote precision against gold on dev and dev200.
- Runs: `runs/r4-ssa-b/ssa/{generic,a_recsent,b_r4_quote}/`. Audit: `runs/audit/ssa/b_r4_quote/semq_shape/`.

## TL;DR
1. **ssa test packs: no visible defect, so I recommend 0 re-asks.**
   - All 25 test ssa questions say "you recommended…" and land on the ssa route, with no misroute in either direction.
   - Every pack is one session of 1.1 to 1.9k chars, and that session holds the right recommendation.
   - 23 of the 25 hints quote the correct line.
   - Same-category decoys in other sessions stay out of the packs: Coach Elena "for strength" vs Coach Miriam "for speedwork", Supernormal "for your birthday dinner" vs Matilda 159 "for dinner with your sons", matplotlib vs pandas, FlexiHorse vs Ola Hansen.
2. **Real Reactor: 6 of 6 ssa answers so far look right and cite the planned session.** They are Toggl Track, Heden, Matilda 159 Domain in South Yarra, pandas, Visual Studio Code and Moulin de Versailles.
3. **Brief item 1 (semantic quote fallback): the loose version is rejected; the strict version (`semq_shape`) is optional.**
   - The loose fallback quotes the best in-session sentence that has a name and a cue. On dev, 0 of 5 quotes contain the answer (4 are wrong lines such as "Yes, there are many other Jamaican dishes that are worth trying."). It is dangerous on long sessions.
   - The strict version needs v2's full recommendation shape and a unique candidate. It is 1 of 1 correct on dev200 (Roscioli), fires 0 times on dev, and S / Sall tie v2.
   - On test it changes 1 pack (speedwork coach), hint only. That is not a defect fix, so re-ask only if Reactor's v2 answer to q_bad53f86da03 is wrong.
4. **Brief items 2 and 3 (role detector on the ssu route, multi hint guard): not built.**
   - They cannot change any test pack. The highest combined p_assistant on test is 0.20 on the ssu route and 0.28 on the multi route.
   - The ku route has a 0.86 ("How many kilometers do I walk each evening these days?"), so never wire the detector there.
5. **Two visible defects on other routes, found with semantic probes** (details under failure patterns; not my files):
   - **multi, q_bcd6d210710b "bakery fund", INSUFFICIENT_EVIDENCE.** The opening deposit is missing from the pack while the sister's decoy is in. The expected answer is 23,200. Dense ranks the missing unit 3rd.
   - **ssu, q_607d3cf5b4f1 "neighborhood in Lisbon".** It is still unfixed in v2, and no semantic channel can find "Graça".

## Variants tried (one line each)
`lenses/ssa/b_r4_quote.py`, inner lens is always `a_recsent r2_conf2`. Only the hint changes; passages, cite_plan and abstain_p are identical to v2.
- `v2`: control (pass-through).
- `semq`: when v2 gives no quote on a rec-style question, quote the cited session's in-pack assistant sentence with a positive structural score, a name/value and a recommendation cue, with no third-party / past / contrast flag, if it is the only such sentence.
- `semq_ce`: as `semq`, plus a cross-encoder margin of at least 3.0 over the in-pack runner-up when there are several candidates.
- **`semq_shape`**: as `semq`, but each candidate must have `rec_shape == 1` (cue + name + kind/purpose fit + overlap ≥ 0.5).
- Probed offline, not swept: CE against the purpose phrase ("coworking space in Lisbon") as the brief proposed. CE scores the Heden line at −11.4 (it has no category word), so CE cannot rescue that case. Dense scores it 0.45, but it is the only candidate anyway.

## Results
Gold ssa questions, ssa lens on the gold type. dev and dev200 have no unanswerable ssa question, so AUC is "-".

| split | lens / variant | S | Sall | PA | ATR | SR | CF1 | chars | AUC |
|---|---|---|---|---|---|---|---|---|---|
| dev (112) | generic `hybrid_rr` (baseline) | 72.3 | 72.3 | 1.000 | 1.000 | 1.000 | 0.368 | 11932 | - |
| dev | v2 `a_recsent r2_conf2` | 93.6 | 93.6 | 1.000 | 1.000 | 1.000 | 1.000 | 4542 | - |
| dev | b_r4_quote `semq` | 93.6 | 93.6 | 1.000 | 1.000 | 1.000 | 1.000 | 4551 | - |
| dev | b_r4_quote `semq_ce` | 93.6 | 93.6 | 1.000 | 1.000 | 1.000 | 1.000 | 4551 | - |
| dev | **b_r4_quote `semq_shape`** | 93.6 | 93.6 | 1.000 | 1.000 | 1.000 | 1.000 | 4542 | - |
| dev200 (22) | generic `hybrid_rr` (baseline) | 71.2 | 71.2 | 1.000 | 1.000 | 1.000 | 0.331 | 11938 | - |
| dev200 | v2 `a_recsent r2_conf2` | 93.7 | 93.7 | 1.000 | 1.000 | 1.000 | 1.000 | 4186 | - |
| dev200 | b_r4_quote `semq` / `semq_ce` / `semq_shape` | 93.7 | 93.7 | 1.000 | 1.000 | 1.000 | 1.000 | 4192 | - |

Quote precision (`r4_quote_eval.py`: "ans" means the gold answer string is inside the quoted line):

| | dev v2 quotes | dev fallback | dev200 v2 quotes | dev200 fallback | test packs changed |
|---|---|---|---|---|---|
| `semq` / `semq_ce` | 2 / 2 ans | **0 / 5 ans** (1 in a gold turn, 4 wrong lines) | 1 / 1 | 1 / 1 (Roscioli) | not audited (rejected) |
| `semq_shape` | 2 / 2 ans | 0 fired | 1 / 1 | 1 / 1 (Roscioli) | 1 (hint only) |

Why no variant can win on the gold metrics: v2 already has PA = CF1 = 1, so S = 95 − 0.3125 · chars/1000. Even 2k-char packs would add only +0.8 S, which is below the +2 bar, and earlier trims lost PA (round 2). Test ssa packs are already 1.1 to 1.9k chars.

The best variant for the ssa route is to **keep v2 (`a_recsent r2_conf2`)**. `b_r4_quote semq_shape` is a safe, optional successor: it ties on dev and dev200 (S and Sall) and changes 1 test hint.

## Test audit (`harness.audit --lens lenses/ssa/b_r4_quote.py --variant semq_shape --type ssa --n 999 --compare runs/final/v2_test_packs.jsonl`)
1 of 25 packs changed (hint only; passages, cite and abstain_p are the same):
- **q_bad53f86da03** "What was the name of the coach you recommended for my speedwork?". The hint gains: *Likely the line you need (assistant, session of 2023/05/02 (Tue) 14:33): "For structured speedwork now that your legs are feeling better, I recommend Coach Miriam at the Toronto Lakeshore Running Club."*
  - Why v2 had no quote: its cross-session margin test failed against Coach Elena ("For strength and mobility work…", CE 0.05), which sits in another session that is not in the pack.
  - Re-ask? **Only if the v2 Reactor answer is wrong or INSUFFICIENT_EVIDENCE.** The v2 pack already contains the line, so I expect "Coach Miriam".

Unchanged on purpose: q_a13386c9d560 "coworking space in Lisbon". The line "Heden in Baixa has a good day pass" is not a full recommendation shape, and Reactor already answered "Heden [E1]".

## Top failure patterns
1. **The loose in-session quote picks list chatter in long sessions** (dev, LongMemEval style). Session uniqueness does not mean precision. Examples:
   - q_6f709e73f130 (gold "Grilled Snapper with Mango Salsa") was quoted "Yes, there are many other Jamaican dishes that are worth trying."
   - q_da07186a650a (gold "The GR-90 trail.") was quoted "…hiking is a must-try activity in the Natural Park of the Moncayo mountain".
   - q_2a698b22434c "last venue" (gold "Revolution Hall", which v2 already computes as list item #last) was quoted a "Music festivals:" line that contradicts the computed item.

   Fix: require `rec_shape == 1`, i.e. `semq_shape`.
2. **Paraphrased category words make the cross-encoder blind.** The Lisbon "coworking space" answer line reads "Heden in Baixa has a good day pass" (CE −11.4 against both the question and the purpose phrase). Lens A's synonym map (coworking → day pass / quiet place) is what retrieves it. A semantic score cannot certify it, so it should stay unquoted, and Reactor got it right anyway.
3. **Cross-type, Reactor-visible: lexical retrieval misses a paraphrased first-person base fact.**
   - **multi q_bcd6d210710b** "How much is left in my bakery fund after those transactions I told you about?" got INSUFFICIENT_EVIDENCE from Reactor (v2 pass).
     - The pack has +7,500 (s_c39041a80b26) and −9,300 (s_2fdde7b225ff). It also has the decoy "My sister Paola opened a bakery fund with 30,000 pesos" (s_a186fc115639, in cite_plan).
     - It misses "I finally opened a separate savings account for the bakery and deposited 25,000 pesos." (s_af3c748536c9, uid 392).
     - Expected answer: 25,000 + 7,500 − 9,300 = **23,200**.
     - Ranks of the missing unit for the raw question (user role): BM25 233, hybrid 32, **dense 3**, **CE rank 4** in the hybrid top 60. A dense or CE floor for numeric first-person units on "how much is left / balance / remaining" questions would recover it.
     - This is a visible defect for the multi owners: qid + reason above.
   - **ssu q_607d3cf5b4f1** "What's the name of my neighborhood in Lisbon?" is still INSUFFICIENT_EVIDENCE material in v2: "I live in Graça…" is not in the pack.
     - Semantic channels cannot fix it: dense unit rank 33 (user role), sentence CE rank 858 of 3362, statement-form dense rank 127. The models do not know Graça is a Lisbon neighbourhood.
     - Only a lexical residence pattern ("I live in <Name>", "my flat in <Name>") for "where / which neighborhood do I live" questions would catch it. That is an ssu-owner decision.

## Test packs I would change (for the integrator)
| qid | route | change | reason | re-ask? |
|---|---|---|---|---|
| q_bad53f86da03 | ssa | hint gains the Coach Miriam quote (`b_r4_quote semq_shape`) | v2 has no quote because of a cross-session margin against a decoy that is not in the pack | only if the v2 answer is wrong |
| q_bcd6d210710b | multi | add s_af3c748536c9 (opening deposit 25,000) | Reactor answered INSUFFICIENT_EVIDENCE; base amount missing | **yes**, if the multi owner implements a fix (not my file) |
| q_607d3cf5b4f1 | ssu | add s_25010d68d7cc ("I live in Graça") | Reactor answered INSUFFICIENT_EVIDENCE (v1) | yes, if the ssu owner finds a general rule (not my file) |

## CORE REQUESTs
1. **Hint-quality metric.** Store, per question, "quote line contains the gold answer" (QA) and "the hint names a different item than gold" (QX) next to AC/HA in sweep summaries. Today hint-only changes are invisible to S, which is how a 0-of-5 quote fallback scored a tie on dev. `r4_quote_eval.py` is a drop-in prototype.
2. **Reactor-result monitor.** A harness command that joins `runs/final/*_results.jsonl` with the pack file and lists INSUFFICIENT_EVIDENCE answers, plus answers whose first citation is not in cite_plan, by route. This round's two cross-type findings came from doing that by hand.
3. **Dense floor for multi numeric questions** ("how much is left / remaining / balance / in total"): the top-5 dense user units carrying a number join the candidate pool. This is a multi-owner change; the evidence is the bakery fund case above.

## Ideas for the next round
- **ssa is done.** Keep v2. If anything, take `semq_shape`: dev200 1/1, dev 0 fires, 1 test hint.
- Build a synthetic "you recommended" dev set from dev histories: plant one recommendation sentence plus one decoy for another purpose into a long session. This would measure quote precision and cross-session-decoy handling at test style. The dev ssa questions are LongMemEval style (14 of 112 are rec-style), so the test style is under-measured.
- Role detector: the ku route's 0.86 on "How many kilometers do I walk each evening these days?" shows why it must stay off ku and temporal. If item 2 is ever built, train it on ssu-route rows only.
- Cross-type: apply sentence-level dense / CE "statement form" retrieval for first-person base facts that are paraphrased ("savings account for the bakery" for "bakery fund"). Gate it by question type (balance / remaining) so the multi decoy problem does not come back.
