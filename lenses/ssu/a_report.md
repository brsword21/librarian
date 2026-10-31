# SSU lens A "Struktura": round 3 report

Code: `lenses/ssu/a_r3_route.py`. It is a new ssu route wrapper. It imports the frozen `a_struct2.py` (r3rn), `ssa/a_recsent.py`, `ssa/b_role.py` and `ku/b_r2.py`, and it edits none of them.
Earlier reports: `a_report_r1.md` and `a_report_r2.md`.
Scratch scripts are in `lenses/ssu/scratch_a/`:
- `r3_kufeat.py`: KU-B pair features per routed question.
- `r3_gate.py`: typed-gate firings on dev, dev200 and test.
- `r3_rugate.py`: runner-up gate analysis.
- `r3_audit_*.txt`: test audits.

Runs:
- Routed runs are in `runs/r3-ssu-a/ssu-routed/{merged_r2,a_r3_route}/...`.
- Gold-type runs are in `runs/r3-ssu-a/ssu/...`.
- Test packs are in `runs/audit/ssu/a_r3_route/<variant>/test_packs.jsonl`.

**Best variant: `a_r3_route.py` / `kg3crga`.** It is a drop-in replacement for the ssu route (`merged_r2.py` role8_r3rn).

Results on the routed ssu slice:

| split | v1 S | kg3crga S | Sall | AUC |
|---|---|---|---|---|
| dev | 86.1 | **87.7** (+1.6) | 88.3 → 88.9 | 0.931 → 0.932 |
| dev200 | 82.3 | **85.0** (+2.7) | 82.6 → 84.7 | 0.905 → 0.914 |

- Gold-type ssu is unchanged: 93.4 on dev and 92.5 on dev200. The gate has 0 false positives on gold ssu.
- **Test: 1 of 45 ssu-route packs changes** (`harness.audit --diff` against `runs/audit/all/pipeline/routed/test_packs.jsonl`):
  - Pack: `q_f14893711b1a` "What is my move date?". Its route changes from ssu to ku, and its cite goes from 1 session to 2.
  - Old pack (v1): it cited the 03/12 session, where the user says the move date is "April 30".
  - New pack: a ku pair. 03/15: "my move date is September 2". 07/10: "Since your move date is now September 16", which the user confirms: "I keep forgetting the date shifted".
  - The new pack also carries a dated timeline hint: "most recent value wins".
  - I believe this is a fix. The old cite was the oldest of three own values.
- Compared with the deferred KU-B hand-off (`merged_r2` role8_r3rn_ku: dev 87.3, dev200 86.5, **6 test changes**):
  - On dev, kg3crga is +0.4.
  - On dev200, it is −1.5.
  - It changes 1 test pack instead of 6. Five of KU-B's six test firings are planted decoys (see pattern 1).
- Against the acceptance rule (+2 dev and no loss on dev200), kg3crga gets +1.6 on dev and +2.7 on dev200. It is the brief's requested gate, and it changes one test pack.

## Variants tried (one line each)
All variants run on the routed ssu slice: 144 dev and 40 dev200 questions. Each one adds a single change to the row above it.

| variant | idea and params |
|---|---|
| v1 | Reproduces `merged_r2` role8_r3rn (frozen): role_guess ≥ 0.8 → ssa lens; otherwise a_struct2 r3rn. |
| kg6 | **Typed value-disagreement gate → ku lens (b_r2 r2b)**. It keeps KU-B's pair at min_score 6 and cov 0.5. Both pair sentences must pass SSU-A's own/affirmed check (`a_owner.classify`: owner ≠ mismatch, polarity ≠ neg/plan; REJECT_RX makes "briefly tried … removed it" a plan). Both must carry a value of the same type: clock time, h:mm, date, weekday, money, or number+unit. The two value sets of that type must be disjoint. Names never count as a type. |
| kg4 / kg3 | The same gate with relaxed KU-B scores: min_score 4 / 3, cov 0.4. The typed check carries the precision. |
| kg6_any | Ablation without the own check. Not swept; offline it re-admits the test decoys. |
| kg3c | kg3, plus **compositional misroutes** (COMP_RX: "how old was I when", "the two", "X and the Y", "increase"): cite a_struct2's outlier runner-up (ru_cite all). On test, 0 of 45 ssu-route questions match. |
| kg3r / kg4r | kg3 / kg4, plus a **runner gate**: cite a_struct2's runner-up when both its best unit and the primary's are own, affirmed, head-hit statements with a typed disagreement. On test it fires on 0 of 45. |
| kg3cr | kg3c plus the runner gate. |
| kg3crg | kg3cr, plus "considering I like to wake up at 7:30 am" is read as "given that". PLAN_RX in a_owner treats every "considering" as a plan, which blocked a real KU pair. |
| **kg3crga** | kg3crg, plus **abstain_p capped at 0.05 when the gate fires**: two affirmed own typed statements are evidence that the question is answerable. It only fixes the ku lens's abstain_p on handed-off questions, which had dropped AUC from 0.931 to 0.914. |
| kg3crgt | kg3crg, plus the **tense fix** (brief item 3): in "did I / was I" questions, a unit with a plan marker gets the future penalty even when it also has a past marker. **Rejected**: S and PA are unchanged, but it moves 3 test R-77 cites to wrong sessions (see pattern 3). |

## Results
"gold" means questions of gold type ssu: dev has 70 (64 answerable), dev200 has 23 (22 answerable). "routed" means the questions the text router sends to ssu: 144 on dev and 40 on dev200.

| set | lens/variant | dev S | Sall | PA | ATR | SR | CF1 | chars | AUC | dev200 S | Sall | PA | ATR | SR | CF1 | chars | AUC |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gold | generic/hybrid_rr (baseline) | 76.6 | 76.6 | 1.000 | 1.000 | 1.000 | 0.512 | 11934 | 0.924 | 73.5 | 73.5 | 1.000 | 1.000 | 1.000 | 0.407 | 11933 | 0.955 |
| gold | a_r3_route/v1 (= frozen ssu) | 93.4 | 92.7 | 1.000 | 1.000 | 1.000 | 0.984 | 3619 | 0.906 | 92.5 | 89.7 | 1.000 | 1.000 | 1.000 | 0.955 | 3859 | 0.955 |
| gold | a_r3_route/kg3crg(a) | 93.4 | 92.7 | 1.000 | 1.000 | 1.000 | 0.984 | 3619 | 0.906 | 92.5 | 89.7 | 1.000 | 1.000 | 1.000 | 0.955 | 3859 | 0.955 |
| routed | merged_r2/role8_r3rn_ku (KU-B hand-off, deferred) | 87.3 | 88.9 | 0.939 | 0.963 | 0.984 | 0.917 | 4068 | 0.924 | 86.5 | 86.8 | 0.943 | 0.957 | 0.971 | 0.881 | 4117 | 0.905 |
| routed | a_r3_route/v1 (= v1 frozen) | 86.1 | 88.3 | 0.932 | 0.960 | 0.980 | 0.894 | 4159 | 0.931 | 82.3 | 82.6 | 0.886 | 0.929 | 0.943 | 0.867 | 4234 | 0.905 |
| routed | kg6 | 86.2 | 88.3 | 0.932 | 0.960 | 0.980 | 0.896 | 4147 | 0.928 | 82.3 | 82.6 | 0.886 | 0.929 | 0.943 | 0.867 | 4234 | 0.905 |
| routed | kg4 | 86.4 | 88.3 | 0.932 | 0.960 | 0.980 | 0.904 | 4106 | 0.919 | 82.6 | 82.6 | 0.886 | 0.929 | 0.943 | 0.876 | 4177 | 0.886 |
| routed | kg3 | 86.5 | 88.3 | 0.932 | 0.960 | 0.980 | 0.907 | 4095 | 0.916 | 82.6 | 82.6 | 0.886 | 0.929 | 0.943 | 0.876 | 4177 | 0.886 |
| routed | kg3c | 86.9 | 88.3 | 0.932 | 0.960 | 0.980 | 0.919 | 4095 | 0.916 | 82.9 | 82.6 | 0.886 | 0.929 | 0.943 | 0.886 | 4177 | 0.886 |
| routed | kg3r | 86.6 | 88.3 | 0.932 | 0.960 | 0.980 | 0.909 | 4095 | 0.916 | 82.6 | 82.6 | 0.886 | 0.929 | 0.943 | 0.876 | 4177 | 0.886 |
| routed | kg4r | 86.5 | 88.3 | 0.932 | 0.960 | 0.980 | 0.907 | 4106 | 0.919 | 82.6 | 82.6 | 0.886 | 0.929 | 0.943 | 0.876 | 4177 | 0.886 |
| routed | kg3cr | 87.0 | 88.3 | 0.932 | 0.960 | 0.980 | 0.922 | 4095 | 0.916 | 82.9 | 82.6 | 0.886 | 0.929 | 0.943 | 0.886 | 4177 | 0.886 |
| routed | kg3crg | 87.7 | 88.9 | 0.939 | 0.963 | 0.984 | 0.929 | 4082 | 0.914 | 85.0 | 84.7 | 0.914 | 0.943 | 0.957 | 0.895 | 4148 | 0.886 |
| routed | **kg3crga** | **87.7** | **88.9** | 0.939 | 0.963 | 0.984 | 0.929 | 4082 | **0.932** | **85.0** | **84.7** | 0.914 | 0.943 | 0.957 | 0.895 | 4148 | **0.914** |
| routed | kg3crgt (rejected on test) | 87.7 | 88.8 | 0.939 | 0.963 | 0.984 | 0.929 | 4095 | 0.914 | 85.0 | 85.0 | 0.914 | 0.943 | 0.957 | 0.895 | 4115 | 0.886 |

Routed S by gold type, v1 → kg3crga:

| gold type | dev | dev200 |
|---|---|---|
| ssu | 93.3 → 93.3 | 92.0 → 92.0 |
| ssa | 91.1 → 91.1 | 93.8 → 93.8 |
| multi | 55.7 → 61.4 | 83.3 → 88.3 |
| ku | 77.4 → 84.2 (6 hand-offs) | 54.7 → 64.3 (2 hand-offs) |
| temporal | 57.3 → 57.3 | n/a |

Gate firings, the same for kg3crg and kg3crga:

| split | firings | details |
|---|---|---|
| dev | 6 | All gold ku. Mortgage pre-approval ($ money), charity 5K PB (27:12 vs 25:50, h:mm), cocktail class (Thursday vs Fridays), French-press ratio (6 vs 5 oz), cat Luna (6 vs 9 months), Saturday wake-up (8:30 vs 7:30 am). |
| dev200 | 2 | Luna, Saturday wake-up. Both gold ku. |
| test | 1 of 45 | Move date. |

Without the own and typed checks, KU-B's ku_pair_p fires on 6 test questions; five of them are decoys.

## Top failure patterns (with examples)
1. **KU-B pairs on test are mostly planted decoys, and the typed own gate removes them (fixed).** Pair sentences from `scratch_a/r3_kufeat_test.jsonl`:
   - Sourdough starter: "I'm thinking of naming my sourdough starter Bubbles" (plan) and "My friend Valentina named her sourdough starter Bubbles too" (other owner, name only).
   - Café: "I usually stop at Caffè Gilli …" and "Francesca usually stops at Caffè Rivoire …" (other owner, name only).
   - R-77 filter capacitor: "swapped … from 33 µF to 47 µF" and "I briefly tried a 68 µF filter capacitor … removed it" (REJECT, so plan).
   - R-77 dial lamp: "ended up fitting a 6.3-volt dial lamp" and "bought a 12-volt dial lamp … but it was too dim" (REJECT).
   - Birthday restaurant: "My friend Ines booked her birthday dinner at Trattoria Otto" (other owner) and "I booked a table at Osteria Numero".

   The one firing the gate keeps is the move date: September 2, then "now September 16". That is a real update.
2. **ku misroutes still miss the second gold session (open). PA on dev200 ku is 0.667.** These are the remaining PA failures on dev200 (`harness.failures … kg3crga/dev200`):
   - "What was my previous personal best time for the charity 5K run?": the 27:45 session (04/11) sits inside a long training-plan turn and is never retrieved. The pack has 27:12 and 26:30.
   - "What new kitchen gadget did I invest in before getting the Air Fryer?": the Instant Pot session ("thinking of using my new Instant Pot") is phrased as a plan, so the plan penalty and the low score drop it.
   - "Is my mom using the same grocery list method as me?": the old state ("she's still stuck on her old paper list") is not a typed value, so no gate can see it. This is a status update, not a value update.
3. **The tense fix as specified is wrong at unit level (rejected, kg3crgt).** In "did I end up using" questions, a unit-level FUT_RX also hits the correct units, because the same turn holds "I need to / I want to". The test cites moved like this:
   - AM IF: from 07/09 "realigned the AM IF … to 465 kHz" to the dial-lamp session.
   - Speaker impedance: from 05/19 "swapped the speaker … to an 8-ohm unit" to 03/11, the old 4-ohm unit.
   - AGC: from 03/04 "18k-ohm" to the dial-lamp session.

   Dev S does not change, so the regression shows up only in the test audit. A clause-level version would need the plan and the past marker to sit in the same clause as the head hit.
4. **A difference question whose head is a unit (open, test only).** "By how many ohms did I reduce the volume control resistance in my National R-77?" parses with head "ohms", so the pack holds three resistor sessions and no volume statement. The evidence is 03/05 "replaced the scratchy volume pot with a 500k-ohm log taper unit" and 05/19 "installed a 250k-ohm log taper volume pot"; the answer is 250k. It also has decoys: a Panasonic RF-2200 with 500k and a Hallicrafters with 1M. Of the other route lenses, multi tight and ku r2b miss both volume statements; only generic hybrid_rr (12k chars) packs them. No dev or dev200 question starts with "by how many", so nothing could be validated and nothing was shipped.
5. **Compositional multi misroutes (partly fixed, dev only).** "How old was I when Alex was born?" and "At which university did I present a poster on my thesis research?" lose the second session, which never becomes an outlier runner-up (SR 0.5). kg3c cites the runner-up when one exists, which raises CF1 on "the two novels", "the two hobbies" and "Instagram increase" (multi CF1 0.667 → 0.857). On test, 0 questions match COMP_RX.

## CORE REQUESTs
1. **Wire kg3crga as the ssu route**: `configs/best.json` ssu → `lenses/ssu/a_r3_route.py` / `kg3crga`. It changes 1 test pack, `q_f14893711b1a`. Build time: about 0.4 s per question on dev and 1.6 s on dev200, cold cache included.
2. **Router or parse: "by how many/much <unit> did I <change-verb> <object>"** is a difference question. Its anchor is the object, not the unit. Route it to a lens that packs the before and after statements of the object and computes the difference. It is one test question with no dev counterpart, so the integrator has to decide whether to wire it untested.
3. Optional: **`harness.audit --diff` should also print hint changes** (route-preserving hint edits are invisible today) and an abstain_p delta column.

## Ideas for the next round
- A clause-level tense check: penalise a plan only when the plan marker and the head hit are in the same clause (CLAUSE_RX split). Validate it on the test audit before trusting dev.
- A status-update gate for KU: still stuck on X, now using Y. Use the same own/affirmed check with a typed contrast "still / old → now / switched" instead of a value type. This covers the grocery-list and "finished the Nightingale" questions.
- Relative updates: "increased the AGC resistor by 15k ohms" after "put in an 18k-ohm resistor". Compute base ± delta when both statements are own and share the head. This is the ku-A brief item; on test it is one question, the AGC resistor.
- Recall for KU old values buried in long turns, such as the 27:45 5K PB inside a training-plan turn. Use a sentence-level CE over all user turns that mention the head.
