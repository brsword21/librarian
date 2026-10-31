# KU lens B ("Semantyka"): round 4 report (final lens round, test-visible defects only)

Earlier reports: `b_report_r3.md`, `b_report_r2.md`, `b_report_r1.md`.

New files (no frozen file edited):
- `lenses/ku/b_r4_ku.py`: post-processing wrapper over the frozen ku lens `lenses/ku/a_r3.py` r3w (KU-A's lens, credited). It imports r3w and changes the pack only in the two cases below.
- `lenses/ku/b_r4_ssuroute.py`: evaluation-only wrapper. It is the frozen v2 ssu route with its ku hand-off lens swapped to b_r4_ku. Result: 0 change on dev, dev200 and test, so it is **not** proposed.
- Supporting files in `lenses/ku/scratch_b/`:
  - ready configs `r4_cfg_nolate_c.json` and `r4_cfg_nolate_c_cnt2.json` (configs/best.json with only routes.ku swapped);
  - `r4_changed.tsv` (changed test qids with reasons);
  - logs `r4_*.log`, probes `r4_probe_cnt*.py`, and the v2 ku test pack dump `r4_ku_test_v2.txt`.

**Best variant: `lenses/ku/b_r4_ku.py` `nolate_c`** as the ku route.

**Optional add-on: `nolate_c_cnt2`.** It changes the same packs as `nolate_c` plus one more, and fixes a real PA defect on test (rooms renovated). On dev and dev200 it fires only on unanswerable questions, so its gold effect cannot be measured there.

## Test defects found (v1 Reactor answers + v2 ku packs, 20 ku-routed test questions)
1. **Rent (q_e165458f4cff), answered wrong by v1 Reactor: "9,000 shillings [E2][E3]".**
   - The storyline is 18,000 (04/14, Kilimani) → 22,000 (08/11, "moved to a new bedsitter in South B").
   - The pack also carried an uncited session dated 08/20 (s_8729a1a905d8). It is a brother decoy ("My brother Brian pays 22,000 shillings"), and it also says "My current rent is only 9,000, shared. I'll stay." Reactor followed the "MOST RECENT value" instruction and took 9,000.
   - r3w had already flagged this session as `gate.threat`, and r3w's cite_plan and hint statements both say 22,000.
2. **Rooms renovated (q_982391af62c7): PA defect.**
   - The pack has no completion statement; its hint lists "ripping up the carpet" and "living room is a dust zone".
   - The history has: kitchen finished (03/10), dining room refinished (04/18), bathroom done (05/02), toddler's room painted (06/07), main bedroom finished (07/19), and hallway done "but I don't count it as a room" (07/25). It also has two non-instances: the guest room barely started (06/05) and the neighbour's contractor finishing 4 rooms (a decoy).
   - This is a count of events, not a value that was updated.
3. **Late uncited noise sessions on two more packs.**
   - Job title (q_b3e5afe916c8): a 09/11 "role of a Marketing Director" session follows the 08/24 "now I am Director of Clinical Services".
   - Tractors: a beehives session.
4. **Wrong old-member cites; answers are fine.** CF1 only, not fixed: the integrator asked for visible defects only, and these change cite_plan only.
   - Skateboard: the old 'Decaf' naming session is in the pack, but the cited one is "skateboard rolling by as texture".
   - Spices: the "Spice Souk on Danforth" (05/10) session is not in the pack.
   - Coffee: Carlos's "three cups" is listed and cited as the earlier value.
5. **Cats (q_1a034c66813d): no change made.** Only other people's cats have counts (sister 2, Bjørn 3), so the question is most likely unanswerable. Its pack holds horses and beehives, which should lead to INSUFFICIENT_EVIDENCE.

## What the lens does
- **`nolate`**: drop uncited context sessions dated AFTER the newest cite_plan session.
  - The newest cited session is the lens's claim for the latest value. A later session the lens did not cite is a decoy or noise, and it can only contradict that claim. Earlier context sessions are kept.
- **`_c` guard**: skip `nolate` on count-of-instances questions. These match `how many <x> have/has/did I/we <verb>` and have no number in the statement list (digits, number words, once/twice, second..tenth). They make no latest-value claim, so there is nothing to protect. Without this guard `nolate` also dropped the dining-room line from the rooms pack.
- **`cnt2`** (on those same questions): the pack is rebuilt from the user's own units that contain the question's verb stem or a completion verb (finished / done / wrapped up / completed / finally).
  - Units are ranked by bge similarity to the question's statement form ("we renovated in the bungalow the rooms") and pinned by rank under a 6000-char budget. build_pack renders them chronologically.
  - The hint becomes "list every instance as 'date | [E#] | item', then count; only what I actually did; ignore others', planned, not-finished or 'does not count' items".
  - abstain_p stays on the ku lens's scale.

## Variants tried (one line each)
- `r3w`: control, the frozen v2 ku route (a_r3 r3w through the wrapper). Reproduces v2 exactly.
- `nolate`: drop uncited sessions after the newest cite. Fires on 1 of 78 dev and 2 of 26 dev200. 4 test packs change, including rooms, where it does harm by dropping the dining-room line.
- `cnt`: hand count-of-instances questions to the frozen multi route lens (merged_r2 tight_role9). **Rejected.**
  - The rooms multi pack was 9.7k chars of renovation chatter with none of the completion lines.
  - With min(abstain_p) it also cost AUC (dev .926 → .919, dev200 .898 → .864).
- `nolate_cnt`: both of the above. Rejected for the same reasons.
- `nolate_v`: nolate only when the newest cited hint statement carries a value. Too blunt: it also blocked the dev200 "old"-mode question, which has no statement list.
- **`nolate_c`**: nolate except on count-of-instances questions. **Recommended.**
- **`nolate_c_cnt2`**: plus the instance pack.
  - The first version (k=14, cite_plan = all pack sessions) fired on the answerable dev question "How many times have I met up with Alex from Germany?" and cut its CF1 from 1.0 to 0.5 (dev S −0.2). The fix was to add once/twice/thrice and second..tenth to the count words: the Alex statement says "met up twice before".
  - A second fix pins units by rank instead of chronologically, so the budget trims the least similar units, not the newest ones.

## Results

### KU gold type (dev 78 q, dev200 26 q)
| variant | dev S | Sall | PA | ATR | SR | CF1 | CF1all | chars | AUC | dev200 S | Sall | PA | ATR | SR | CF1 | CF1all | chars | AUC |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| generic hybrid_rr (bar) | 83.8 | 83.8 | .972 | .979 | .986 | .812 | .812 | 11936 | .806 | 83.5 | 83.5 | 1.000 | 1.000 | 1.000 | .740 | .740 | 11923 | .852 |
| r3w (= v2 ku route) | 93.4 | 93.6 | 1.000 | .993 | 1.000 | .979 | .986 | 3044 | .926 | 93.3 | 92.7 | 1.000 | 1.000 | 1.000 | .977 | .955 | 3072 | .898 |
| nolate | 93.4 | 93.7 | 1.000 | .993 | 1.000 | .979 | .989 | 3032 | .926 | 93.4 | 93.0 | 1.000 | 1.000 | 1.000 | .977 | .964 | 3021 | .898 |
| cnt (min ap) | 93.4 | 93.6 | 1.000 | .993 | 1.000 | .979 | .986 | 3102 | .919 | 93.3 | 92.7 | 1.000 | 1.000 | 1.000 | .977 | .955 | 3353 | .864 |
| nolate_cnt (min ap) | 93.4 | 93.7 | 1.000 | .993 | 1.000 | .979 | .989 | 3090 | .919 | 93.4 | 93.0 | 1.000 | 1.000 | 1.000 | .977 | .964 | 3321 | .864 |
| nolate_v | 93.4 | 93.7 | 1.000 | .993 | 1.000 | .979 | .989 | 3032 | .926 | 93.3 | 92.7 | 1.000 | 1.000 | 1.000 | .977 | .955 | 3072 | .898 |
| **nolate_c** | **93.4** | **93.7** | 1.000 | .993 | 1.000 | .979 | .989 | 3032 | .926 | **93.4** | **93.0** | 1.000 | 1.000 | 1.000 | .977 | .964 | 3040 | .898 |
| nolate_c_cnt2 (k=14 v1) | 93.2 | 93.5 | 1.000 | .993 | 1.000 | .972 | .982 | 3087 | .926 | 93.4 | 93.0 | 1.000 | 1.000 | 1.000 | .977 | .964 | 3167 | .898 |
| **nolate_c_cnt2** (final) | 93.4 | 93.7 | 1.000 | .993 | 1.000 | .979 | .989 | 3073 | .926 | 93.4 | 93.0 | 1.000 | 1.000 | 1.000 | .977 | .964 | 3169 | .898 |

### ku route slice (`--route --type ku`, all gold types the text router sends to ku: dev 17 q, dev200 4 q)
| variant | dev S | Sall | CF1all | chars | dev200 S | Sall | CF1all | chars |
|---|---|---|---|---|---|---|---|---|
| r3w (v2) | 89.0 | 88.1 | .929 | 3065 | 91.6 | 88.8 | .825 | 2939 |
| nolate_c | 89.1 | 88.8 | .951 | 2989 | 91.6 | 90.1 | .867 | 2890 |
| nolate_c_cnt2 | 89.1 | 88.8 | .951 | 2989 | 91.6 | 90.1 | .867 | 2890 |

### ssu route with the ku hand-off swapped (`b_r4_ssuroute.py`, dev 140 q / dev200 38 q)
All three variants tie v2 exactly: 88.8 / Sall 89.3 on dev and 88.8 / Sall 88.9 on dev200. **0 of 45 test ssu packs change**, so this is not proposed.

**Acceptance.**
- The +2 S bar is not reachable: the type is saturated at PA 1.0 and CF1 .98 on gold.
- The round-4 rule is test defects only, with no dev/dev200 regression. `nolate_c` meets it:
  - S +0.0 / +0.1 and Sall +0.1 / +0.3 on gold ku (dev / dev200);
  - Sall +0.7 / +1.3 on the ku route;
  - 0 losses anywhere.

## Test packs changed vs `runs/final/v2_test_packs.jsonl`
`harness.audit --compare ... --n 999`, ku route, 20 packs. Details are in `scratch_b/r4_changed.tsv`.

| qid | what | variant | re-ask? |
|---|---|---|---|
| q_e165458f4cff | **rent**: drop the 08/20 brother-decoy session with "current rent is only 9,000" (r3w's own `threat`). v1 answered 9,000; the pack now holds only 18,000 → 22,000. | nolate_c | **yes**: v1 answer cached under the old pack_hash |
| q_b3e5afe916c8 | **job title**: drop the 09/11 "role of a Marketing Director" session (late title decoy) | nolate_c | already re-asked in v2 (in v2_changed); not yet answered |
| q_07a3d3d857f4 | **tractors**: drop the irrelevant 06/01 beehives session. Cosmetic. | nolate_c | not yet asked (v2 file order 144); free if swapped in before then |
| q_982391af62c7 | **rooms renovated**: the instance pack replaces a pack with no completion line (15 own lines, 5.9k chars, list-then-count hint) | nolate_c_cnt2 only | not yet asked (order 130) |

Reactor cost: one real re-ask (rent, about 105 s). The other three are either already queued or not yet asked.

Caveats:
- **Rent.** Gold is unknown. The 9,000 line is literally the user's latest own statement. But it sits in a decoy session, says "I'll stay" eleven days after the user moved, and says "shared" about a bedsitter. On dev and dev200, no session dropped by `nolate` was ever gold (PA unchanged; 3 firings).
- **Rooms.** The instance pack lacks the 04/18 "we just refinished the dining room" line (it ranks 15th, past the budget). Reactor will probably count kitchen, bathroom and main bedroom (maybe the toddler's room). I did not tune further on that one question.

## Top failure patterns (remaining)
1. **Count-of-instances questions phrased as updates** ("how many rooms have we renovated so far").
   - The latest-value machinery has nothing to say, and lexical/CE retrieval ranks the completion lines at 44-117 (CE −9 to −11), because the instance sentences name the item (kitchen, bathroom) and not the category (room).
   - The statement-form query + bge over own completion/event units puts all of them in the top 15. Validation is thin: dev and dev200 have no answerable example of this shape.
2. **Off-attribute or someone else's old member.** These cost CF1, not answers:
   - skateboard: cites a "skateboard rolling by" session instead of the "named it 'Decaf'" session;
   - coffee: Carlos's "three cups" is listed as the earlier value;
   - spices: "Spice Souk on Danforth" was never retrieved.
3. **Late contradicting self-statements inside decoy sessions** (rent). This is now handled by `nolate`. The same signal already exists as r3w's `gate.threat`, but r3w uses it only for the gate.

## CORE REQUESTs
1. **Route ku to `lenses/ku/b_r4_ku.py` `nolate_c`.** The ready config is `lenses/ku/scratch_b/r4_cfg_nolate_c.json`. It imports the frozen a_r3 r3w unchanged and changes 3 ku test packs; re-ask rent.
2. Optional: `nolate_c_cnt2` (`r4_cfg_nolate_c_cnt2.json`). It adds the rooms fix (1 more pack, not yet asked). It is dev/dev200-neutral; on dev/dev200 it fires only on 2 unanswerable questions, adding ~2.5-3.3k chars each with the same abstain_p.
3. Do not wire `b_r4_ku` into the ssu route's ku hand-off: there are 0 changes anywhere.
4. Harness: a `--diff` flag that prints the dropped and added session dates per changed pack would make reviewing changes like these faster (I used custom scripts).

## Ideas for next round
- **Old-member backlink** (cite_plan only, no Reactor cost): when the newest statement names the value it replaced ("renamed ... 'Flat White'; 'Decaf' just made me think of work", "after Miguel moved to Porto"), cite the earliest own session that mentions that old value. Fixes the skateboard cite; leaves the ceramics, accountant and watercolour cites unchanged.
- Drop non-own statements from the hint's statement list (Carlos's coffee, the neighbour's laps) and leave the earlier slot empty when the user never stated an old value.
- **Category second hop for instance counts**: dense_texts("<category> such as X") between the question noun ("rooms") and the candidate items (kitchen, bathroom, bedroom), to lift recall of instance lines beyond completion verbs.
- Expose `gate.threat` as a general signal: a later own-sounding statement that contradicts the pair should be shown to Reactor with an ownership note, or dropped as `nolate` does.
