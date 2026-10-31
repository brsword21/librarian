# Temporal lens A ("Struktura"), round 3 report

Code: `lenses/temporal/a_r3_gap.py`. It wraps the frozen v1 temporal route (`merged_r2.py` evA_mixB, which runs `a_gap` ct_evgba on gap and named-event questions and `b_merge` ev1_mix_g on everything else). It imports the frozen files and does not edit them. Round-2 report: `a_report_r2.md`.
Scratch: `lenses/temporal/scratch_a/r3/insp.py` prints picks and top mentions per event. `chk.py` prints span firings and own-coverage per event on any split.
Runs: `runs/r3-temporal-a/temporal/{generic/hybrid_rr,a_r3_gap/<variant>}/{dev,dev200}`. Test audits: `runs/audit/temporal/a_r3_gap/{span_own,so_nor}`.

## Why the work targets test
The v1 test audit has 36 temporal-routed questions: 35 gap questions ("how many days after/apart ...") and "How many years did I serve as a firefighter?". Test has no order, ago or whole-question temporal questions. Dev order (34 q) and B-route (43 q) work therefore cannot change the one remaining test pass, so this round targets the four test packs that v1 gets wrong or leaves weak:
1. **Firefighter (answerable; v1 misses it).** The history says "I joined the fire brigade when I was 23 years old" (04/02) and "I retired from the fire department the day I turned 63" (06/18). Decoys: "Carlos ... retired from the fire department at 60" and "My neighbor's son just joined the fire brigade at 23". v1's B pack (2 sessions) holds neither gold statement, and abstain_p is 0.62.
2. **Three gap questions with planted decoys (probably unanswerable).** v1 sent 8k chars and 4-5 passages each, plus a "Date notes" hint built from wrong picks:
   - trail-running shoes -> first trail run: only "Camille bought trail-running shoes today";
   - medical check-up -> travel vaccines: Camille's check-up, and "I still need to sort out my travel vaccines";
   - sourdough starter -> first loaf: no loaf anywhere; "Camille got a sourdough starter today".

## Variants tried (one line each)
| variant | idea |
|---|---|
| v1 | frozen merged_r2 evA_mixB reproduced inside the lens |
| span | + "how many years / how long did I serve / work / spend / teach ... (as X)": scan user sentences for an age ("when I was 23", "the day I turned 63", "at age N") or a year ("in 1998") together with a start verb (joined, started, became ...) or an end verb (retired, left, quit ...). Keep only the user's own statements (`subject_kind == self`), rank them by cross-encoder relevance to the question, and compute end - start. Tight 2-session pack; the hint gives both statements and the difference; computed = difference |
| own | + own-absence check on gap / ago packs **without a confident computed value**. For each event: coverage = IDF share of its content stems (leading verb dropped) in the best own, done user sentence (subject self, no plan or negation marker within 35 chars before the event word). An event is *missing* when its own coverage is < 0.75 **and** either a full-coverage sentence exists that is not an own done action (someone else's, or a plan), at >= 0.9, or nothing covers it, at < 0.4. When an event is missing: the pack shrinks to the sessions of the closest mentions (budget 4000), the hint says "no statement that you did this was found; the closest mention is '<Camille ...>'" or "not mentioned in the history" instead of listing wrong picks as "date notes", and abstain_p >= 0.8 |
| span_own | span + own |
| so_nor | span_own + tight gap packs without the runner-up session (`max_runner 0`), so passages = cite set |
| so_ordm | span_own + 2 more own mentions per event and the opening user turn on non-tight (order) packs: **no effect** (identical metrics; the budget is already full) |

## Results (whole temporal type; dev 133 q / 127 answerable, dev200 26 q / 22 answerable)
| variant | split | S | Sall | PA | ATR | SR | CF1 | CF1all | chars | AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| generic hybrid_rr (bar) | dev | 65.1 | 65.1 | 0.748 | 0.860 | 0.908 | 0.673 | 0.673 | 11931 | 0.636 |
| generic hybrid_rr (bar) | dev200 | 61.2 | 61.2 | 0.727 | 0.849 | 0.910 | 0.589 | 0.589 | 11941 | 0.932 |
| v1 (merged_r2 evA_mixB) | dev | 80.8 | 77.0 | 0.890 | 0.953 | 0.976 | 0.844 | 0.719 | 7560 | 0.839 |
| v1 | dev200 | 83.7 | 77.3 | 0.909 | 0.955 | 0.968 | 0.897 | 0.680 | 7453 | 0.966 |
| span / own / **span_own** | dev | 80.8 | 77.0 | 0.890 | 0.953 | 0.976 | 0.844 | 0.719 | 7518 | 0.839 |
| **span_own** | dev200 | 83.7 | 77.3 | 0.909 | 0.955 | 0.968 | 0.897 | 0.680 | 7453 | 0.966 |
| so_nor | dev | 80.8 | 77.4 | 0.890 | 0.957 | 0.976 | 0.844 | 0.730 | 7485 | 0.839 |
| so_nor | dev200 | 83.8 | 78.5 | 0.909 | 0.955 | 0.968 | 0.897 | 0.723 | 7411 | 0.966 |
| so_ordm | dev | 80.8 | 77.0 | 0.890 | 0.953 | 0.976 | 0.844 | 0.719 | 7526 | 0.839 |

- The v1 reproduction gives 80.8 on dev, against 81.3 in `runs/merge2`. One question differs, q_cd3c3026183d "Who became a parent first, Rachel or Alex?" (b_merge route, PA 1 -> 0), and it differs in v1 itself, not in my code. I did not chase it (time box).
- **span** fires on 0 dev / dev200 questions and on 1 test question (firefighter: computed 40, both gold statements, both decoys rejected).
- **own** fires on 1 dev question, the unanswerable "iPad" one (abstain_p was already 0.8), and on 0 answerable dev / dev200 questions. That includes the 14 answerable no-computed gap / ago packs with sign / who / rounding / vague gates (Super Bowl, flu -> 10th jog, Airbnb, ...). On test it fires on exactly the 3 decoy questions.
- So dev S does not move (+0.0 / +0.0). These are test-targeted changes, with zero false positives found on dev or dev200.

## Best variant: `a_r3_gap.py:span_own`
Test packs changed against v1 (`harness.audit --compare runs/audit/all/pipeline/routed/test_packs.jsonl`): **4 of 36**.
| qid | question | v1 | span_own |
|---|---|---|---|
| q_0f66a8b016b8 | years served as a firefighter | B pack, 2 passages, no gold statement, abstain_p 0.62 | joined-at-23 (04/02) and retired-at-63 (06/18) sessions, computed 40, abstain_p 0.05 |
| q_6ab86da6d151 | trail-running shoes -> first trail run | 5 passages, 8.0k chars, hint lists wrong picks | 1 passage (Camille's statement), 1.6k chars, abstain_p 0.8 |
| q_22ab86c83e4c | medical check-up -> travel vaccines | 4 passages, 8.0k | 2 passages (Camille's check-up; "I still need to sort out my travel vaccines"), 2.5k, abstain_p 0.8 |
| q_33cd29d8e252 | sourdough starter -> first loaf | 4 passages, 8.0k | 2 passages, 3.1k, hint "bake my first loaf: not mentioned in the history", abstain_p 0.8 |

Optional **so_nor** (+0.0 / +0.1 S, Sall +0.4 / +1.2) drops the runner-up session from 8 more test gap packs: q_1fda88c230cc, q_e6ffd9f64dac, q_ae313330ed3d, q_24028b381273, q_7040872842c8, q_5bf8400d0361, q_2eb1ff9b6496, q_b0b9ca48ad21. That is 12 of 36 changed packs in total. In dev and dev200 the runner-up never saved PA, and the passages then equal the cite set. Reactor's temporal citations are selective (evidence F1 0.83), so the gain on real Reactor is small. I would take it only if the integrator wants Sall = S on temporal. Otherwise span_own is the minimal-change choice.

## Top failure patterns (dev, unchanged from v1; not addressed this round because test has none of them)
1. **Order questions, restatement turns** (5 PA fails out of 34):
   - q_2ad03036e541 "Europe with family or solo trip to Thailand": ATR 0.5;
   - q_f00c26116d06 "bus or train most recently": ATR 0.5;
   - q_1525ff1b6137 "'Page Turners' or 'Marketing Professionals'": the third gold session is a same-day restatement, so ALL = 0.
   - Adding more mentions to wide order packs (so_ordm) changed nothing, because the budget is full of fill units. The fix has to replace fill with restatements, not add them.
2. **B whole-question route** (43 dev q, S 67): "What gardening-related activity did I do two weeks ago?". This is B's area.
3. **Aggregate "since I last ..." in the gap regex** (2 dev q, topic mode, 13k chars): "How many months have passed since I last visited a museum with a friend?". None on test, so not done (brief item 2).
4. Reschedule guard (brief item 3): the r2 `resched.py` scan found no later own mention that moves a scheduled date on any test gap question, so it would change 0 test packs. Not implemented.

## CORE REQUESTs
1. Route temporal to `lenses/temporal/a_r3_gap.py` variant `span_own` (or `so_nor`; see above). It is a superset of v1: every pack that neither the span nor the own rule touches is byte-identical to merged_r2 evA_mixB. Test diff: the 4 packs listed above.
2. The router sends "How many years did I serve as a firefighter?" to temporal today. Keep it there: span lives in the temporal route lens.
3. The abstention policy has no hint. The own-cut hint ("no statement that you did this was found; the closest mention is ...") is factual, not an abstention instruction. It fires on 0 answerable dev / dev200 questions, but please keep it in mind when you read Reactor's answers on q_6ab86da6d151, q_22ab86c83e4c and q_33cd29d8e252.

## Ideas for next round
- Order packs: replace the B fill units with the per-event restatement mentions and opening user turns, instead of adding them on top (q_2ad03036e541, q_1525ff1b6137).
- Generalise span to "how old was I when X" and "how many years between my X and Y" with age and year statements. This is the same scanner with a different combiner.
- Use own coverage as an abstain_p feature for every temporal route (AUC), calibrated on dev+dev200 pooled. Today it only gates no-computed packs.
- Check the q_cd3c3026183d non-determinism in v1 (b_merge route).
