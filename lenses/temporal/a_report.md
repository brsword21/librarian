# Temporal lens A ("Struktura"), round 2 report

Code: `lenses/temporal/a_gap.py`, which imports the round-1 helpers from `lenses/temporal/a_calendar.py` (unchanged) and B's `b_sem.py`.
Best variant: **`a_gap.py:ct_evgba`**. It is a drop-in replacement for `merged_r1.py:gapA_semB`, with the same gap regex and the same B fallback (`sem_turns9`) for questions without events.
Variant `r1` reproduces merged_r1 inside the same file, so every comparison below uses the same harness version.
Scratch scripts: `lenses/temporal/scratch_a/r2/`:
- `sub.py`: gap vs. rest subset metrics;
- `kinds.py`: per parse-kind comparison;
- `test_gap.py`: picks on test gap questions, no gold;
- `mentions.py`: top mentions per event;
- `resched.py`: checks whether a scheduled date was later moved;
- `absent.py`: event words that never occur in the history.

Runs: `runs/r2-temporal-a/temporal/{generic,a_gap}/<variant>/{dev,dev200}`, routed runs in `runs/r2-temporal-a-route/`, and the test audit in `runs/audit/temporal/a_gap/ct_evgba`.

## What changed (gap route = a_calendar ftb_bm25 plus)
1. **conf2: confidence of the computed gap.**
   - An alternative mention whose only date is its session date is discounted by 0.15 when the pick has a written or relative date. Examples: "Then he asked me about varroa treatment timing", "I think our anniversary is Wednesday".
   - No `computed` in these cases:
     - a pick is someone else's event or is negated (`who:`);
     - the gap is 0 days (`zero`);
     - a week or month count lies within 0.15 of a .5 rounding boundary (`rounding`); the hint then gives "N days = x.y weeks";
     - an event word never occurs in the history (`absent:`, e.g. "iPad"); abstain_p is set to 0.8.
   - With the `who`, `sign`, `zero` and `absent` gates, the hint drops the "Difference: N days" line, so Reactor does not copy a number built from a decoy pair. The mention list stays in the hint. This is not an abstention hint.
2. **tight packing.** When the gap is confident, the pack holds only:
   - the two event sessions (pick sentence, the session's other user mentions of the event, its first user turn);
   - at most one runner-up session, when an event's margin is below 0.25;
   - budget 6000.
3. **Event route for non-gap questions that name their events** (`a_kinds`):
   - "how many days/weeks/months ago did I X", "which did I do first, X or Y", and "how long had I been X when I Y" go to the same calendar and tight path, instead of B;
   - questions with no parsed events stay with B.
4. **abst_b.** For those extra non-gap questions, abstain_p comes from B's pipeline. A's discrete scale cost 0.06 AUC on dev200.
5. **ago_gate.** An "ago" pick that is an assistant sentence dated only by its session, or a 0 result from a session date, gives no computed value.

## Variants tried (one line each)
| variant | idea |
|---|---|
| r1 | merged_r1 reproduced: gap -> a_calendar ftb_bm25, rest -> b_sem sem_turns9 |
| conf2 | + confidence rules 1 (swept before the `absent` rule was added, so its dev AUC is 0.769) |
| tight | + tight packing 2 only |
| ct | conf2 + tight |
| ctc | ct + cross-encoder tie-break (`hx.rerank_texts` on the event vs. its top-6 mention sentences, when margin < 0.15) |
| ct45 | ct with tight budget 4500 |
| ctn | ct, non-confident gap packs with fill_k 2 / budget 6500 |
| ct_ago / ct_ord / ct_ev | ct + event route for "ago" / "order" / both |
| ct_evg | ct + event route for ago, order and A-parsed gap phrasings outside the gap regex |
| ct_evo | ct_ev + tight packing for order questions when every event has a clear own pick (rejected: dev order PA 0.87 -> 0.81) |
| ct_evgb | ct_evg + abstain_p from B for the extra questions |
| ct_evgbc | ct_evgb + CE tie-break (neutral) |
| **ct_evgba** | ct_evgb + ago_gate |

## Results, whole temporal type (dev: 133 q / 127 answerable; dev200: 26 q / 22 answerable)
| variant | split | S | Sall | PA | ATR | SR | CF1 | CF1all | HA | chars | AUC |
|---|---|---|---|---|---|---|---|---|---|---|---|
| generic hybrid_rr (bar) | dev | 65.1 | 65.1 | 0.748 | 0.860 | 0.908 | 0.673 | 0.673 | - | 11931 | 0.636 |
| generic hybrid_rr (bar) | dev200 | 61.2 | 61.2 | 0.727 | 0.849 | 0.910 | 0.589 | 0.589 | - | 11941 | 0.932 |
| r1 (= merged_r1) | dev | 76.5 | 72.1 | 0.843 | 0.948 | 0.968 | 0.817 | 0.674 | 0.917 | 9039 | 0.769 |
| r1 (= merged_r1) | dev200 | 82.1 | 74.4 | 0.909 | 0.955 | 0.968 | 0.861 | 0.602 | 1.000 | 9036 | 0.966 |
| conf2 | dev | 76.9 | 72.7 | 0.850 | 0.948 | 0.968 | 0.815 | 0.674 | 0.949 | 9037 | 0.769 |
| conf2 | dev200 | 82.1 | 74.4 | 0.909 | 0.955 | 0.968 | 0.861 | 0.602 | 1.000 | 9031 | 0.966 |
| tight | dev | 76.6 | 72.5 | 0.843 | 0.944 | 0.968 | 0.817 | 0.681 | 0.917 | 8664 | 0.769 |
| tight | dev200 | 82.3 | 75.9 | 0.909 | 0.955 | 0.968 | 0.861 | 0.650 | 1.000 | 8685 | 0.966 |
| ct | dev | 77.0 | 73.1 | 0.850 | 0.944 | 0.968 | 0.815 | 0.684 | 0.949 | 8606 | 0.839 |
| ct | dev200 | 82.3 | 75.7 | 0.909 | 0.955 | 0.968 | 0.861 | 0.641 | 1.000 | 8550 | 0.966 |
| ctc | dev | 77.0 | 73.2 | 0.850 | 0.948 | 0.968 | 0.813 | 0.685 | 0.951 | 8576 | 0.839 |
| ctc | dev200 | 82.3 | 75.7 | 0.909 | 0.955 | 0.968 | 0.861 | 0.641 | 1.000 | 8550 | 0.966 |
| ct45 | dev | 77.1 | 73.2 | 0.850 | 0.944 | 0.968 | 0.815 | 0.686 | 0.949 | 8445 | 0.839 |
| ct45 | dev200 | 82.4 | 76.1 | 0.909 | 0.955 | 0.968 | 0.861 | 0.650 | 1.000 | 8335 | 0.966 |
| ctn | dev | 77.1 | 73.2 | 0.850 | 0.944 | 0.968 | 0.815 | 0.687 | 0.949 | 8529 | 0.839 |
| ctn | dev200 | 82.3 | 75.7 | 0.909 | 0.955 | 0.968 | 0.861 | 0.641 | 1.000 | 8550 | 0.966 |
| ct_ago | dev | 77.8 | 74.9 | 0.858 | 0.944 | 0.968 | 0.815 | 0.719 | 0.974 | 7977 | 0.841 |
| ct_ago | dev200 | 82.6 | 78.0 | 0.909 | 0.955 | 0.968 | 0.861 | 0.710 | 1.000 | 7788 | 0.966 |
| ct_ord | dev | 77.7 | 73.5 | 0.858 | 0.949 | 0.968 | 0.816 | 0.677 | 0.949 | 8299 | 0.804 |
| ct_ord | dev200 | 82.4 | 75.2 | 0.909 | 0.955 | 0.968 | 0.861 | 0.624 | 1.000 | 8261 | 0.909 |
| ct_ev | dev | 78.4 | 75.3 | 0.866 | 0.949 | 0.968 | 0.816 | 0.712 | 0.974 | 7670 | 0.807 |
| ct_ev | dev200 | 82.7 | 77.6 | 0.909 | 0.955 | 0.968 | 0.861 | 0.692 | 1.000 | 7500 | 0.909 |
| ct_evg | dev | 79.0 | 76.0 | 0.874 | 0.953 | 0.968 | 0.816 | 0.718 | 0.976 | 7515 | 0.809 |
| ct_evg | dev200 | 82.7 | 77.3 | 0.909 | 0.955 | 0.968 | 0.861 | 0.681 | 1.000 | 7448 | 0.909 |
| ct_evo | dev | 77.5 | 74.7 | 0.850 | 0.937 | 0.964 | 0.816 | 0.720 | 0.974 | 7155 | 0.802 |
| ct_evo | dev200 | 82.8 | 78.8 | 0.909 | 0.955 | 0.968 | 0.861 | 0.728 | 1.000 | 6969 | 0.909 |
| ct_evgb | dev | 79.0 | 76.0 | 0.874 | 0.953 | 0.968 | 0.816 | 0.718 | 0.976 | 7515 | 0.839 |
| ct_evgb | dev200 | 82.7 | 77.3 | 0.909 | 0.955 | 0.968 | 0.861 | 0.681 | 1.000 | 7448 | 0.966 |
| ct_evgbc | dev | 79.0 | 76.1 | 0.874 | 0.957 | 0.968 | 0.816 | 0.720 | 0.977 | 7477 | 0.839 |
| ct_evgbc | dev200 | 82.7 | 77.3 | 0.909 | 0.955 | 0.968 | 0.861 | 0.681 | 1.000 | 7448 | 0.966 |
| **ct_evgba** | dev | **79.5** | **76.4** | 0.882 | 0.957 | 0.972 | 0.816 | 0.715 | 1.000 | 7563 | 0.839 |
| **ct_evgba** | dev200 | **82.7** | **77.3** | 0.909 | 0.955 | 0.968 | 0.861 | 0.681 | 1.000 | 7448 | 0.966 |

ct_evgba vs. r1 (merged_r1):
- dev: **+3.0 S**, **+4.3 Sall**, AUC 0.769 -> 0.839, chars -1.5k;
- dev200: +0.6 S, +2.9 Sall, AUC unchanged at 0.966.
- It passes the rule: at least +2 on dev, no loss on dev200, and Sall does not drop.

Routed (`--route --type temporal`, i.e. the questions the router sends to temporal), r1 -> ct_evgba:
- dev: S 77.9 -> **80.6**, Sall 72.4 -> 76.2;
- dev200: S 83.0 -> 83.6, Sall 74.3 -> 77.4.

### Gap subset (the merged_r1 gap route; 94% of test temporal)
| run | split | n | S | Sall | PA | HA | computed / answerable | passages | chars |
|---|---|---|---|---|---|---|---|---|---|
| r1 | dev | 30 | 83.8 | 80.9 | 0.897 | 0.947 | 19 / 29 | 4.0 | 8033 |
| ct_evgba | dev | 30 | **86.4** | **85.1** | 0.931 | **1.000** | 22 / 29 | 3.7 | 6115 |
| r1 | dev200 | 5 | 92.6 | 83.8 | 1.0 | 1.0 | 3 / 5 | 4.0 | 7733 |
| ct_evgba | dev200 | 5 | **93.4** | **89.8** | 1.0 | 1.0 | 5 / 5 | 2.6 | 5206 |

Dev passages include 2 aggregate "how many months have passed since I last ..." questions. They have no events, go to topic mode, and take 19-26 passages. Without them a gap pack has 2.3 passages.

### Per parse-kind, dev (r1 -> ct_evgba)
| kind | n | S | Sall | PA | passages |
|---|---|---|---|---|---|
| gap regex, events parsed | 27 | 87.1 -> 89.9 | 84.2 -> 88.7 | 0.93 -> 0.96 | 2.7 -> 2.3 |
| "N days ago did I X" (was B) | 17 | 82.2 -> **91.3** | 73.5 -> **90.0** | 0.88 -> 1.00 | 2.4 -> 1.6 |
| "how long had I been X when I Y" (was B) | 9 | 82.8 -> 90.7 | 81.2 -> 91.6 | 0.89 -> 1.00 | 2.7 -> 2.2 |
| "which first, X or Y" (was B) | 31 | 80.1 -> 82.7 | 78.7 -> 80.2 | 0.84 -> 0.87 | 2.6 -> 2.8 |
| no parsed events (B, unchanged) | 43 | | | | |

On dev200, ago goes 92.2 -> 93.8 (Sall 78.5 -> 91.3) and order goes 92.2 -> 92.5 (Sall 87.4 -> 85.3, 5 questions). The one dev200 "how long had I been" question keeps PA 1, but its Sall drops 86 -> 80.

### Test (35 gap questions, no gold)
| | round 1 (ftb_bm25) | round 2 (ct_evgba) |
|---|---|---|
| passages per pack | 8.3-8.5 | **2.4** |
| chars | 7.9k | **3.8k** |
| `computed` emitted | 30 / 35 (one of them wrong: Camille's check-up) | **32 / 35** |

- The 3 without `computed` are the probable abstentions:
  - first trail run: only Camille bought trail-running shoes;
  - travel vaccines: only Camille had the check-up, and "I still need to sort out my travel vaccines";
  - first loaf: no mention of a loaf.
- Their abstain_p is 0.6-0.7, and their hints carry no number any more.
- Round 1 left Montreal alerts -> lease (45), first hive inspection -> varroa (14) and wife's birthday -> anniversary (50) without a computed value. The session-date discount now makes them confident.
- `resched.py` found no later mention that moves a scheduled date on any test gap question. The tight pack therefore drops nothing that changes an answer.
- Audit (36 routed temporal test questions): 4 flagged. They are the 3 above plus "How many years did I serve as a firefighter?", which is not a gap question (B route, abstain_p 0.62).

## Top failure patterns (dev, ct_evgba)
1. **Order questions: restatements and third gold sessions.** PA is 0.87 on 31 questions, and ATR misses are turns that restate the event.
   - "Which mode of transport did I use most recently, a bus or a train?": ATR 0.5.
   - "Which trip did I take first, Europe with family or the solo trip to Thailand?": all sessions are dated 05/28. The gold turn is a different turn of the same session.
   - "Which group did I join first, 'Page Turners' or 'Marketing Professionals'?" and "How many months before my anniversary did Rachel get engaged?": the third gold session is a restatement on the same day, and the 2-session pack misses it (ALL 0, answer correct).
   - Tight packing of order questions (`ct_evo`) made this worse (dev PA 0.87 -> 0.81), so order packs stay wide.
2. **Aggregate "since I last ..." inside the gap regex** go to topic mode with 19-26 passages.
   - "How many months have passed since I last visited a museum with a friend?": PA 0, Sall 2.
   - "... since I participated in two charity events in a row": PA 1, but Sall 37.
   - There are none on test.
3. **Gold that disagrees with the computed calendar.**
   - "How many weeks had passed since I recovered from the flu when I went on my 10th jog outdoors?": 01-19 -> 04-10 is 81 days, or 11.6 weeks; gold is 15. The rounding gate now withholds it.
   - "How many months ago did I book the Airbnb in San Francisco?": the pick is an assistant sentence on the question day. ago_gate withholds it, but the event sentence ("two months ago, for my best friend's wedding") is not found by BM25.
4. **Whole-question (B) route**: 41 dev questions with no parsed events (S 61.6 / 74.5). That is B's area this round. Examples: "What gardening-related activity did I do two weeks ago?" and "What was the significant business milestone I mentioned four weeks ago?".

## CORE REQUESTs
1. **configs/best.json**: set the temporal route to `lenses/temporal/a_gap.py` variant `ct_evgba`, replacing merged_r1 gapA_semB. It imports `b_sem.py` and uses `sem_turns9` by name. If B changes that variant this round, pass a different `b_variant` in the variant params.
2. **harness.sweep**: add `--qfilter <regex>` (or `--subset gap`) so a merged lens can be scored on a question subset without scratch scripts. I used `scratch_a/r2/sub.py`.
3. **Metric note**: for temporal, PA = ALL and (HA if computed else ATR), so the metric never rewards a correct `computed` value but punishes a wrong one. A lens can score more by withholding `computed`, while Reactor benefits from it. Please also report "computed coverage" (computed / answerable) next to HA, as the gap-subset table does.
4. **Abstention scale**: A's abstain_p is discrete (0.05 / 0.25 / 0.6 / 0.75 / 0.8) and loses AUC to ties when mixed with B's continuous scores. A pooled calibration (isotonic on dev+dev200 per route) would make `configs/abstain.json` thresholds meaningful.

## Ideas for next round
- Order questions: add each event's other user mentions across all included sessions (restatements) and the opening user turn of every session that mentions an event, then test a "tight + restatements" pack.
- Parse "how many months have passed since I last X" as `ago` with "last" semantics: the newest own mention of X, with a friend/companion filter. Pack the 2-3 newest candidate sessions instead of topic mode.
- Reschedule guard for tight packs: when a pick is a scheduled future date, add any later own mention of the same event with a different date as the runner-up. None exists on test today, but it is a cheap safety net.
- The CE tie-break (`ce_tb`) is neutral offline. On test it raises the margins of every pick that was already right, and for the trail-run question it moves the pick onto "Camille bought trail-running shoes", which the `who:other` gate then blocks. Worth keeping as an option if Reactor runs show low-margin errors.
