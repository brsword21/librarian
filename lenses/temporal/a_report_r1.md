# Temporal lens A, round 1 report (archived copy; the current report is a_report.md)

Code: `lenses/temporal/a_calendar.py`. Best variant: `ftb_bm25`. All round-1 numbers are BM25-only (model server saturated).

## Variants tried
| variant | idea | params |
|---|---|---|
| cal_bm25 | round-0 calendar lens, BM25 only | pool 40, budget 8000, fill_k 6, alts 1 |
| m2_bm25 | + top-2 user mentions per event (ATR) | more=2 |
| tp_bm25 | + topic mode for event-less questions | topic, topic_budget 10000, topic_window 0 |
| nr_bm25 / nr2_bm25 | + near-date picks around the resolved date, interleaved | near 3 / near 2, near_max 4 |
| ft_bm25 | tp + first user turn of each picked session | first_turn |
| tb14_bm25 | tp + topic budget 14000 | topic_budget 14000 |
| **ftb_bm25** | tp + first_turn + topic budget 14000 | both |

## Results (temporal; dev 133 q / 127 answerable; dev200 26 q / 22 answerable)
| variant | split | S | PA | ATR | SR | CF1 | chars | AUC |
|---|---|---|---|---|---|---|---|---|
| cal_bm25 | dev | 62.2 | 0.630 | 0.766 | 0.850 | 0.791 | 7932 | 0.816 |
| m2_bm25 | dev | 63.2 | 0.646 | 0.782 | 0.850 | 0.791 | 7937 | 0.816 |
| tp_bm25 | dev | 70.7 | 0.764 | 0.908 | 0.965 | 0.790 | 8506 | 0.835 |
| nr2_bm25 | dev | 70.3 | 0.764 | 0.927 | 0.964 | 0.777 | 8516 | 0.835 |
| ft_bm25 | dev | 72.2 | 0.787 | 0.919 | 0.965 | 0.790 | 8502 | 0.835 |
| tb14_bm25 | dev | 72.5 | 0.795 | 0.922 | 0.971 | 0.790 | 9258 | 0.835 |
| **ftb_bm25** | dev | **74.0** | **0.819** | 0.934 | 0.971 | 0.790 | 9255 | 0.835 |
| cal_bm25 | dev200 | 67.4 | 0.682 | 0.833 | 0.859 | 0.854 | 7937 | 0.858 |
| tp_bm25 | dev200 | 75.6 | 0.818 | 0.894 | 0.959 | 0.837 | 8620 | 0.926 |
| ft_bm25 | dev200 | 75.6 | 0.818 | 0.894 | 0.959 | 0.837 | 8625 | 0.926 |
| **ftb_bm25** | dev200 | 75.3 | 0.818 | 0.894 | 0.968 | 0.837 | 9699 | 0.926 |

PA by kind (dev, ftb_bm25): gap 0.92 (36 q), ago 0.94 (17), order with events 0.87 (31), topic:other 0.67 (33),
topic:order 0.60 (10).

## Top failure patterns (round 1)
1. Lexical gap in topic questions (BM25 only): kitchen appliance -> "smoker", gardening activity -> "planted 12 new
   tomato saplings", business milestone -> "signed a contract with my first client".
2. Gold sets that include every same-topic decoy session (music event last Saturday: 5 gold sessions).
3. Same-day sessions and restatements in order questions (Europe vs Thailand trip, coffee maker vs stand mixer).
4. Unit conversion and vague durations (Airbnb months ago, flu -> 10th jog weeks, exchange program weeks).
