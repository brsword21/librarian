# Lens B "Semantyka", multi-session: Round 3 report

New lens: `lenses/multi/b_r3_full.py`. It is the frozen `b_tight.build` (same retrieval, same p(gold) keep/cite rule), copied with a new renderer and a corrected routine hint. It imports from `b_sweep.py` and `b_tight.py` and edits neither.
**Best variant: `ufull_h`.** Probe: `lenses/multi/b_r3_combo.py` (lens A's rescue + my renderer).
Runs: `runs/r3-multi-b/multi/{generic,b_tight,b_r3_full,b_r3_combo}/<variant>/{dev,dev200}`, routed runs in `runs/r3-multi-b/multi-routed/...`.
Test audits: `runs/audit/multi/b_r3_full/{ufull,ufull_w,ufull_h}` and `runs/audit/multi/b_r3_combo/a_r2m_full12`. The v1 reference with all 20 multi-routed test questions is saved as `scratch_b/v1_test_packs.jsonl`.
Scratch scripts:
- `scratch_b/strict.py`: fact-sentence coverage, the new PA_fact metric
- `scratch_b/keep_fit3.py`: p(gold) refit
- `scratch_b/test_recall.py`: test-audit check of lexical instance sessions left out of the pack

## Headline: the v1 multi pack drops the fact sentence in half of the "PA = 1" questions

**What the real Reactor did.** In the e1 calibration, Reactor answered `INSUFFICIENT_EVIDENCE` on q_2605c5385371 ("hours driving to my three road trip destinations"). The pack held all 3 gold sessions, so offline PA was 1. But the round-1/2 renderer (`b_sweep.trim_text`) trims every unit to 240 chars, keeping the sentences that share the most question terms. It kept "I'm planning another road trip …" and cut "it only took me four hours to drive there" and "I drove for six hours to Washington D.C.". Reactor read both sessions as plans and abstained. The frozen v1 (`b_tight p08c35_aor`) uses the same renderer and still produces this pack (checked: "four hours" and "six hours" are absent from it).

**How I measured it.** The harness's ATR counts a turn as included even after trimming. `scratch_b/strict.py` instead checks the passage text. PA_fact = PA and every fact-like sentence of the gold user turns is present verbatim. A sentence is fact-like if it has a number, money, "by the way / I just …", or a first-person event verb.

| | PA | PA_fact dev | PA_fact dev200 | lost fact sentences (dev) |
|---|---|---|---|---|
| v1 `b_tight p08c35_aor` | 0.950 / 0.909 | **0.479** | **0.455** | 95 in 107 q |
| lens A `a_r3_pin pin` (pins the best own sentence) | 0.950 | 0.628 | – | 52 |
| lens A `a_r3_pin r2m` (rescue) | 0.967 | 0.479 | – | 99 |
| `fact360` (fact-aware trim, 360 chars) | 0.950 / 0.909 | 0.909 | 0.818 | 6 |
| `fact480` | 0.950 / 0.909 | 0.950 | 0.909 | 0 |
| **`ufull` / `ufull_h`** (user units untrimmed) | 0.950 / 0.909 | **0.950** | **0.909** | 0 |
| combo `a_r2m_full12` (A rescue + no trim, 12k budget) | 0.967 / 0.909 | 0.967 | 0.909 | 0 |

The dataset plants the fact as a "By the way, I …" aside after a topical opening sentence, and term-hit trimming drops exactly that aside. Examples lost by v1 on dev:
- "I just got back from a 3-day solo camping trip to Big Sur"
- "I also got a new set of bike lights installed, which were $40"
- "I recently finished a Tamiya 1/48 scale Spitfire"
- "my Twitter follower count has jumped from 420 to 540"
- "placed an online order with Thrive Market … spent around $150"
- "Dr. Smith, on March 3rd" (the splitter also broke on "Dr.")

The other routes do not have this problem. With the same check, ssu `merged_r2`, ku `b_r2` and temporal `merged_r2` lose 0 sentences (`scratch_b/strict_other_types.txt`), so the fix only concerns multi.

## Results (gold type multi; dev 133 q / 121 answerable, dev200 28 q / 22 answerable)

| split | lens / variant | S | Sall | PA | ATR | SR | CF1 | CF1all | chars | AUC | pass. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| dev | generic `hybrid_rr` (bar) | 69.1 | 69.1 | 0.744 | 0.873 | 0.961 | 0.817 | 0.817 | 11931 | 0.598 | 3.64 |
| dev | `v1` (= b_tight p08c35_aor, frozen v1) | 87.2 | 85.7 | 0.950 | 0.980 | 0.984 | 0.910 | 0.858 | 5841 | 0.731 | 3.53 |
| dev | `fact360` | 87.1 | 85.5 | 0.950 | 0.980 | 0.984 | 0.910 | 0.858 | 6427 | 0.731 | 3.53 |
| dev | `fact480` | 86.9 | 85.4 | 0.950 | 0.980 | 0.984 | 0.910 | 0.858 | 6853 | 0.731 | 3.53 |
| dev | `ufull` | 86.9 | 85.3 | 0.950 | 0.980 | 0.984 | 0.910 | 0.858 | 7071 | 0.731 | 3.53 |
| dev | `ufull_d4` | 83.6 | 82.0 | 0.893 | 0.966 | 0.984 | 0.910 | 0.858 | 5483 | 0.731 | 3.53 |
| dev | `fact360_d4` | 83.8 | 82.2 | 0.893 | 0.966 | 0.984 | 0.910 | 0.858 | 4876 | 0.731 | 3.53 |
| dev | `ufull_ck` (pack == cite, Sall = S) | 85.3 | 85.3 | 0.950 | 0.980 | 0.984 | 0.858 | 0.858 | 7071 | 0.731 | 3.53 |
| dev | `ufull_w` / `ufull_hr` | 86.9 | 85.3 | 0.950 | 0.980 | 0.984 | 0.910 | 0.858 | 7072 | 0.731 | 3.53 |
| dev | **`ufull_h`** | **86.9** | **85.3** | 0.950 | 0.980 | 0.984 | 0.910 | 0.858 | 7072 | 0.731 | 3.53 |
| dev | `ufull_h12` | 86.8 | 85.2 | 0.950 | 0.980 | 0.984 | 0.910 | 0.858 | 7317 | 0.731 | |
| dev | combo `a_r2m_full` (10k) | 86.8 | 84.5 | 0.950 | 0.983 | 0.991 | 0.910 | 0.833 | 7245 | 0.731 | |
| dev | combo `a_r2m_full12` | 87.8 | 85.5 | 0.967 | 0.986 | 0.991 | 0.910 | 0.833 | 7559 | 0.731 | |
| dev200 | generic `hybrid_rr` (bar) | 63.7 | 63.7 | 0.682 | 0.844 | 0.950 | 0.770 | 0.770 | 11947 | 0.689 | 4.29 |
| dev200 | `v1` | 83.3 | 82.3 | 0.909 | 0.962 | 0.973 | 0.868 | 0.835 | 6279 | 0.795 | 3.86 |
| dev200 | `fact360` | 83.0 | 82.0 | 0.909 | 0.962 | 0.973 | 0.868 | 0.835 | 6991 | 0.795 | 3.86 |
| dev200 | `fact480` | 82.9 | 81.9 | 0.909 | 0.962 | 0.973 | 0.868 | 0.835 | 7437 | 0.795 | 3.86 |
| dev200 | `ufull` | 82.9 | 81.9 | 0.909 | 0.962 | 0.973 | 0.868 | 0.835 | 7665 | 0.795 | 3.86 |
| dev200 | `ufull_ck` | 81.9 | 81.9 | 0.909 | 0.962 | 0.973 | 0.835 | 0.835 | 7665 | 0.795 | 3.86 |
| dev200 | `ufull_w` / `ufull_hr` | 82.9 | 81.9 | 0.909 | 0.962 | 0.973 | 0.868 | 0.835 | 7669 | 0.795 | 3.86 |
| dev200 | **`ufull_h`** | **82.9** | **81.9** | 0.909 | 0.962 | 0.973 | 0.868 | 0.835 | 7669 | 0.795 | 3.86 |
| dev200 | `ufull_h12` | 82.8 | 81.7 | 0.909 | 0.962 | 0.973 | 0.868 | 0.835 | 8036 | 0.795 | |
| dev200 | combo `a_r2m_full` (10k) | 79.8 | 77.9 | 0.864 | 0.961 | 0.982 | 0.868 | 0.804 | 7893 | 0.795 | |
| dev200 | combo `a_r2m_full12` | 82.7 | 80.7 | 0.909 | 0.970 | 0.982 | 0.868 | 0.804 | 8300 | 0.795 | |

**Routed multi** (`--route --type multi`; the role hand-off is not applied, so 6 dev ssa questions sit at S ≈ 15 in every variant):

| split | variant | S | Sall | PA | AC | CF1 | chars | per-gold-type notes |
|---|---|---|---|---|---|---|---|---|
| dev (170 q) | v1 | 83.8 | 82.4 | 0.904 | 0.904 | 0.889 | 5493 | ssu misroutes PA 0.846 |
| dev | **ufull** (= ufull_h) | **83.8** | 82.4 | **0.911** | **0.923** | 0.889 | 6627 | **ssu misroutes PA 0.923** |
| dev | fact480 | 83.9 | 82.5 | 0.911 | 0.923 | 0.889 | 6422 | |
| dev200 (45 q) | v1 | 79.9 | 78.2 | 0.868 | 0.938 | 0.844 | 6137 | |
| dev200 | ufull | 79.5 | 77.8 | 0.868 | 0.938 | 0.844 | 7392 | |

The routed AC gain is direct evidence of the trimming problem. On ssu questions misrouted to multi, the gold answer string was in a gold turn that was in the pack, but the trimming removed it. Untrimmed, the matcher finds it.

**Against the acceptance rule** (+2 S on dev, no loss on dev200): `ufull_h` does **not** pass on S. It costs −0.3 on dev and −0.4 on dev200, and the cost is only the chars term: +1.2k chars × 0.05/16k. PA, CF1 and Sall are unchanged apart from that chars term. Offline S cannot see what the change fixes: the answer-bearing sentence is missing from 47% of v1's "answerable" multi packs, and real Reactor reacts to that with a false INSUFFICIENT_EVIDENCE. I recommend it as an explicit exception, as round 2 did for Sall. `fact480` is the same at −200 chars, but it is more code and still trims assistant/user units over 480 chars, so I prefer `ufull`.

## Test audit (no gold) and full change list against v1

`ufull_h` against v1 (`b_tight p08c35_aor`) over all 20 multi-routed test questions:
- **Passage sets changed: 0 of 20. cite_plan changed: 0 of 20.** Routes unchanged.
- **Hint changed: 1 pack.** q_6dd9e5e4fb97, "How many watercolour classes do I attend each week?" (the routine-hint fix, below). Its pack holds "At the moment I only have one regular watercolour class, on Saturday mornings" (May) and "I signed up for an additional watercolour class on Wednesday evenings" (July), so the answer is the sum, 2. The old hint said "the most recent statement wins".
- **Passage text changed: 15 of 20 packs.** These now carry whole user units instead of 240-char trims. Mean chars 6600 → 6815 (+3%); the largest growth is q_90f7c27a95f2 grandchildren (6.3k → 7.2k) and q_8b4f1ff8ce11 books (4.2k → 5.2k).
- Test user turns are short (synthetic style), so on test the renderer recovers only 8 fact-like user sentences, mostly off-topic. **On test this change is mainly robustness**, at a small cost (+215 chars per pack). The big effect is on LongMemEval-style long turns (dev, dev200 and the e1 calibration failure).
- Flags: 1 of 20 (the same as v1).

Window breadth (`ufull_w`, brief item 1) changes 3 test packs and adds one session to each: q_47e3f2749c07 orchids, q_8b4f1ff8ce11 books since March, q_2f121a243f4b PhD books. All 3 added sessions are decoys:
- orchid-care chat
- "My brother told me he bought five books"
- "read two articles for my PhD"

**Rejected.**

Combo `a_r2m_full12` (A's rescue): 16 of 20 test packs gain 1–2 uncited sessions. I inspected 5: one recovers an instance (books: "I just finished reading a book about the history of São Paulo"); the rest are noise (grandchildren: neem oil, loyalty programs; tango: bakery savings; feijoada: plant watering). The obvious missing instances are still missing; see failure pattern 2. I would not ship the rescue on test evidence. If the integrator takes A's rescue anyway, it should be rendered with `trim=0` and a 12k budget, as `a_r2m_full12` does: at 10k the untrimmed units push gold depth units out (dev200 PA 0.909 → 0.864).

## Variants tried (one line each)
- `v1`: b_tight p08c35_aor copied into the new file; reproduces 87.2 / 83.3 exactly.
- `fact360` / `fact480`: fact-aware trim. Sentences are scored by term hits plus fact cue (number, `_FACT`, first-person event verb), the splitter is abbreviation-safe, and units are cut at 360 / 480 chars. PA_fact 0.909 / 0.950 on dev.
- `ufull`: user units untrimmed, assistant units trimmed as before. PA_fact 0.950 / 0.909 at +1.2k chars.
- `ufull_d4`, `fact360_d4`: at most 4 units per session to pay for the larger units. PA 0.893: gold turns sit 5th–8th inside their session. Rejected.
- `ufull_ck`: cite = every passage (Sall = S exactly), the fallback asked for in brief item 4. 85.3 / 81.9.
- `ufull_fs` + `scratch_b/keep_fit3.py`: p(gold) refit with fact-sentence CE features (best CE of a session's own fact sentences, the gap to the best one, their count), fit on dev with dev200 held out (brief item 2).
  - Offline: dev +0.5 (87.7 at C 0.3, tk 0.08); dev200 ±0.
  - Lost gold sessions have fact-sentence CE of −8 to −11, so the feature does not separate them. Not adopted.
- `ufull_w`: in-window sessions with p ≥ tk/2, up to 12, for count questions (brief item 1). No-op on dev and dev200, where the window is never active. Adds decoys on test. Rejected. `ufull_w25` (tk/4) is defined but was not run.
- `ufull_h`: + **additive routine hint** (see below). **Best.**
- `ufull_hr` / `ufull_hr0`: + lexical instance rescue (brief item 3).
  - It takes sessions outside the pack that hold an own, affirmed, fact-cued user sentence with the question's head noun, ranked by sentence CE, at most 2.
  - It fires once on dev, a correct instance: "I recently participated in the Bike-a-Thon charity event". The S change is ±0.
  - On test it picks "I repotted two orchids last week" over "I bought two Cattleya orchids", because ms-marco CE scores the decoy 2 logits higher. Not adopted.
- `ufull_h12`: ufull_h with a 12k budget. −0.1; the budget is not binding for B.
- combo `a_r2m_full` / `a_g2m_full` / `a_r2m_full12`: lens A's rescue rendered untrimmed (credit: multi-A). See the table and the test audit above.

### The routine hint (in `ufull_h`)
v1's rate hint reads: "This asks for a current routine value (per day/week) … the most recent statement wins, earlier values are outdated."
- It fires on 2 dev and 2 dev200 questions, all of them sums over sessions: "How many health-related devices do I use in a day?" (4 devices in 5 sessions) and "How many days a week do I attend fitness classes?" (Zumba Tue+Thu, yoga Wed, weights Sat). On test it fires once, on the watercolour question, also a sum.
- The new text: "… list every item of it from all sessions with its date and [E#]; different items add up, and only when the same item is restated with a new value does the most recent statement win."
- It changes no pack contents and is invisible to offline S. Among routed questions (any gold type), it fires on no other dev or dev200 question.

## Top failure patterns (ufull_h)
1. **Category to instance, low unit CE** (unchanged from round 2; 5 dev and 2 dev200 PA losses):
   - "How many properties did I view before making an offer on the townhouse in Brookside": the gold sessions say "I viewed a 1-bedroom condo on February 10th" and "that one in Cedar Creek"; they rank 3–6 with p 0.002–0.07.
   - "How many projects have I led": gold is "case competition" and "poster".
   - "How many health-related devices": the hearing-aids session ranks 5th.
2. **Test: obvious instances outside the pack** (`scratch_b/test_recall.py`). The test histories hold 20–30 sessions about the same topic, and CE ranks care chatter above the instance:
   - Orchids: "Oh, and I bought two Cattleya orchids for the balcony this week" (03/18) scores CE −4.98, below "I repotted two orchids" (−2.88) and "I bought fertilizer for three of my older orchids" (−3.41).
   - Books since March: "I read two detective novels during my trip to Ubatuba" (06/12) never shares a stem with "books".
   - Book club attendance: "My book club met last night and 7 people came" (03/09).
   - All three are missing from v1, from ufull_h and from A's rescue.
3. **Trimming hides the fact** (fixed by `ufull`): the road-trip hours, Big Sur 3 days, bike lights $40, Spitfire / Tiger I kits, Thrive Market $150.
4. **Wrong routine hint on additive routines** (fixed by `ufull_h`): health devices, fitness-class days, test watercolour.

## CORE REQUESTs
1. **Route multi to `lenses/multi/b_r3_full.py` `ufull_h`** inside `lenses/multi/merged_r2.py` (`multi_variant`), or in a new wrapper. The test changes are text-only in 15 packs and the hint in 1 pack; passage sets and cite_plan are unchanged in all 20.
2. **Harness: add text-level ATR / PA_fact.** A gold turn should count as included only if its fact sentences are in the passage text, not just its turn_id (`scratch_b/strict.py` is a drop-in). Today v1 shows PA 0.950 / ATR 0.980 on dev, but PA_fact is 0.479. Every lens that trims passes this check blind; I checked ssu, ku and temporal v1 and they are clean.
3. If lens A's rescue is adopted, call it with `trim=0, budget=12000` (`b_r3_combo.py a_r2m_full12` shows it); its own renderer keeps the 240-char trim (PA_fact 0.479).

## Ideas for next round
- **Instance verb classes for count questions:** map the question verb ("added to my collection / bought / got / acquired / read / attended / met") to an event class and require it in the instance sentence. This would fix the orchid and book-club misses; CE scores care chatter higher than acquisitions.
- **Dense on the statement form** ("I bought orchids", "I read a novel") over own fact sentences of the whole history, combined with the verb class; bge handles "novels" ≈ "books", which lexical rules do not.
- **A cheaper renderer:** whole user units only for the session's top-3 units, depth units fact-trimmed at 360. This would recover about 0.2 S of the chars cost with PA_fact unchanged.
- **Ask Reactor for a cite-set check** on 5 tight multi packs: does it cite the uncited context sessions? That decides whether `ufull_ck` (Sall = S) or `ufull_h` should ship.
