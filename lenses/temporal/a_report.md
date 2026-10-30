# Temporal lens A ("Struktura"), round 1 report

Code: `lenses/temporal/a_calendar.py`. Debug helper: `lenses/temporal/scratch_a/dbg.py` (picks vs gold turns for a question).
Best variant: **`ftb_bm25`**. `ft_bm25` is the conservative fallback: it ties the old best on dev200 but gains only +1.5 on dev.

## What changed since round 0
1. **`dense` switch.** `retrieve()` uses BM25 only when `dense=False`. While 12+ sweeps share the model server, a new query embedding takes about 20 s (measured: `hx.dense()` on a fresh query string, 18-21 s; 0.03 s when cached). The event-phrase queries are never cached, so every dense variant (`cal`, `cal_wide`, `cal_tight`, `cal_nocomp`) would need more than an hour per sweep. All round-1 numbers are BM25-only, with 0 server calls and about 30 s per dev sweep.
2. **Topic mode** (`topic=True`). Questions with no parseable events go here: kind `other`, 33 dev questions ("What kitchen appliance did I buy 10 days ago?"), and order questions without listed events, 10 dev questions ("order of the three trips in the past three months"). Steps:
   - `question_window()` resolves the question's own time phrase against the question date: "N days/weeks/months ago", "the Wednesday two months ago", "last Saturday", "the past weekend", "last week/month", "the past N months", "in January", "in March and April", holidays.
   - Ranking is user-role BM25 over the whole history (time words stripped) plus a second user-role BM25 restricted to the window, fused RRF-style.
   - Pack: `window=0`, `topic_budget` chars, chronological order.
   - The hint states the resolved date or span. For order questions it also says "list each event with its date, then sort".
   - `cite_plan` = the top sessions, as many as the count word in the question ("three trips" -> 3), otherwise 2.
3. **More user mentions per event** (`more=2`). Adds the top-2 user-turn mentions of each event to the ranking, because gold turns can be a different turn of the picked session.
4. **First user turn of each picked session** (`first_turn=True`). Dev gold turns are mostly the session's opening user turn ("By the way, I just ... today"), while the pick is often a later restatement.
5. Order hint: tied dates are shown as `A = B` instead of a misleading `A < B`.

## Variants tried (one line each)
| variant | idea | params |
|---|---|---|
| cal_bm25 | round-0 calendar lens, BM25 only | pool 40, budget 8000, fill_k 6, alts 1 |
| m2_bm25 | + top-2 user mentions per event (ATR) | more=2 |
| tp_bm25 | + topic mode for event-less questions | topic, topic_budget 10000, topic_window 0 |
| nr_bm25 / nr2_bm25 | + "near-date" picks (best/cue user unit of sessions within ±2-3 days of the resolved date), interleaved | near 3 / near 2, near_max 4 |
| ft_bm25 | tp + first user turn of each picked session | first_turn |
| tb14_bm25 | tp + topic budget 14000 | topic_budget 14000 |
| **ftb_bm25** | tp + first_turn + topic budget 14000 | both |
| cal, cal_wide, cal_tight, cal_nocomp | round-0 dense variants: **not swept** (query embedding about 20 s each under server contention) | |

## Results (temporal; dev: 133 q / 127 answerable; dev200: 26 q / 22 answerable)
| variant | split | S | PA | ATR | SR | CF1 | chars | AUC |
|---|---|---|---|---|---|---|---|---|
| generic hybrid_rr (bar) | dev | pending* | | | | | | |
| generic hybrid_rr (bar) | dev200 | pending* | | | | | | |
| cal_bm25 | dev | 62.2 | 0.630 | 0.766 | 0.850 | 0.791 | 7932 | 0.816 |
| m2_bm25 | dev | 63.2 | 0.646 | 0.782 | 0.850 | 0.791 | 7937 | 0.816 |
| tp_bm25 | dev | 70.7 | 0.764 | 0.908 | 0.965 | 0.790 | 8506 | 0.835 |
| nr2_bm25 | dev | 70.3 | 0.764 | 0.927 | 0.964 | 0.777 | 8516 | 0.835 |
| ft_bm25 | dev | 72.2 | 0.787 | 0.919 | 0.965 | 0.790 | 8502 | 0.835 |
| tb14_bm25 | dev | 72.5 | 0.795 | 0.922 | 0.971 | 0.790 | 9258 | 0.835 |
| **ftb_bm25** | dev | **74.0** | **0.819** | 0.934 | 0.971 | 0.790 | 9255 | 0.835 |
| cal_bm25 | dev200 | 67.4 | 0.682 | 0.833 | 0.859 | 0.854 | 7937 | 0.858 |
| tp_bm25 | dev200 | 75.6 | 0.818 | 0.894 | 0.959 | 0.837 | 8620 | 0.926 |
| nr2_bm25 | dev200 | 75.6 | 0.818 | 0.894 | 0.959 | 0.837 | 8622 | 0.926 |
| ft_bm25 | dev200 | 75.6 | 0.818 | 0.894 | 0.959 | 0.837 | 8625 | 0.926 |
| **ftb_bm25** | dev200 | 75.3 | 0.818 | 0.894 | 0.968 | 0.837 | 9699 | 0.926 |

\* The baseline sweeps (`--tag r1-temporal-a`, generic `hybrid_rr`) were started first but had not finished after more than 60 min, because they were blocked on the shared model server (rerank of 100 units plus a query embedding per question). For reference, the kit's 80-question mixed sample gives S≈73, PA≈0.93, CF1≈0.55, chars≈11.9k. On other types the same baseline gives dev S 76.6 (ssu) and 83.8 (ku). The sweeps stop when this agent's session ends. Embeddings and rerank scores are cached in the shared sqlite, so re-running `.venv/bin/python -m harness.sweep --lens lenses/generic.py --variants hybrid_rr --split dev --type temporal --tag r1-temporal-a --workers 2` (and the same with `--split dev200`) will be cheaper.

ftb_bm25 vs tp_bm25: +3.3 S on dev. dev200 PA is identical, and the −0.3 S is only the extra topic-mode characters, on 22 questions.

PA by question kind, dev, ftb_bm25:

| kind | n | PA | ALL | ATR=1 | CF1 |
|---|---|---|---|---|---|
| gap (test style) | 36 | 0.92 | 0.97 | 1.00 | 0.97 |
| ago | 17 | 0.94 | 1.00 | 1.00 | 0.90 |
| order with events | 31 | 0.87 | 0.97 | 0.90 | 0.97 |
| topic:other | 33 | 0.67 | 0.82 | 0.79 | 0.43 |
| topic:order | 10 | 0.60 | 0.80 | 0.60 | 0.55 |

## Test audit (12 questions, ftb_bm25, qualitative)
- On the 10 day-gap questions I read, every pick was the true sentence. Decoys were handled:
  - "My friend Valentina entered her own alfajor recipe ... June 8" lost to "I am entering my alfajor recipe ... on June 2, 2023".
  - "My friend Helen flew to Adelaide ... 11 June" lost to "I flew to Adelaide ... 10 June 2023".
  - "My brother Brian started a Python for Data Analysis course on 2023-04-12" lost to the user's own 2023-05-08.
  - "Camille submitted her working holiday visa application" lost to the user's own submission.
- Two flags:
  - "How many years did I serve as a firefighter?" has no events, so it goes to topic mode, which returns an irrelevant pack and abstain_p 0.1. It is probably an abstain question.
  - "Montreal flat alerts -> lease": the right dates and a 45-day gap are in the hint, but `computed` is withheld. Picks dated by "tonight"/"today" score below `min_score=0.55`.

## Top failure patterns (dev, ftb_bm25)
1. **Lexical gap in topic questions (BM25 only)**: the asked category and the stated event share no word. This is the biggest remaining loss.
   - "What kitchen appliance did I buy 10 days ago?": gold "I just got a smoker today" (03/15, exactly the resolved date). ATR 0.
   - "What gardening-related activity did I do two weeks ago?": gold "I just planted 12 new tomato saplings today". ATR 0.
   - "What was the significant business milestone I mentioned four weeks ago?": gold "I just signed a contract with my first client today". ALL 0.
   - The near-date picks (nr*) recover two of these but push decoy sessions out of the pack, so the net effect is 0. Dense or a cross-encoder should fix these.
2. **Gold sets that include every same-topic decoy session** (ALL=0 while the answer itself is in the pack):
   - "Who did I go with to the music event last Saturday?": 5 gold sessions, all Saturdays.
   - "What is the order of the six museums I visited?": 5 of 6 in the pack.
   - "Which pair of shoes did I clean last month?": 5 gold sessions.
3. **Same-day sessions and restatements** in order questions:
   - "Which trip did I take first, the one to Europe with family or the solo trip to Thailand?": both sessions are dated 05/28. The gold turn is t10, and the pick is a different turn.
   - "coffee maker vs stand mixer": the event dates are only "about three weeks ago" / "last month", in a neighbouring sentence of the picked one.
4. **Unit conversion and vague durations**:
   - "How many months ago did I book the Airbnb in San Francisco?": HA 0.
   - "How many weeks had passed since I recovered from the flu when I went on my 10th jog outdoors?": HA 0.
   - "How many weeks have I been accepted into the exchange program when I started attending the pre-departure orientation?": HA 0.

## CORE REQUESTs
1. **Model-server throughput.** A fresh query embedding takes about 20 s with 12+ concurrent sweeps. Options:
   - precompute and cache query embeddings for every question text and for the lens-parsed event phrases (I can export the phrase list: `parse_question(q).events` over all splits);
   - or add a batched `hx.dense_many(queries)` so a lens pays one round trip per question.
   Without this, dense/CE temporal variants cannot be compared in a time box.
2. **Pipeline**: use `cite_plan` for temporal citations (CF1 0.97 on gap/order questions vs about 0.5 for whole-pack citations).
3. **Router**: "How many days apart/after/before ..." -> temporal with high confidence (34 of 36 test temporal questions).
4. **core.dates**: adopt the holiday grammar ("a week before Black Friday"), "the 22nd of April", M/D only after on/the/since, and future-penalised year inference (see a_design.md). Also add a question-side resolver like `question_window()` here ("the Wednesday two months ago", "in March and April", "the past weekend").
5. Metric note: for order questions, ATR needs the exact gold turn. Restatements in a later turn of the same session count as misses, although Reactor can answer from them.

## Ideas for next round
- Dense or CE in topic mode, once the server is free:
  - use `q.question` itself as the dense/rerank query, which is already cached by the generic baseline;
  - rerank the user units inside the window with a time prior;
  - then re-enable the near-date picks.
- Topic-mode abstention: IDF coverage of the question terms by the best user unit (the firefighter case). Also apply the "only someone else did it" rule there.
- `computed` gating: relax `min_score` for `rel`/`session` picks when the margin is large ("tonight", "today"). Test has histories where every date is relative.
- Order questions: when a pick has no date, borrow the relative date of the next sentence in the same unit ("I bought it about three weeks ago").
- Weeks/months conversion: emit both "N weeks (D days)" in the hint, and withhold `computed` when D/7 is within 0.3 of a rounding boundary.
- Topic CF1 is only 0.43: cite sessions in the window plus the top topic session, instead of the top-2 by fused rank.
