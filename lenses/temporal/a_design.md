# Temporal lens A ("Struktura"): design, round 0

Code: `lenses/temporal/a_calendar.py` (VARIANTS `cal`, `cal_tight`, `cal_wide`, `cal_nocomp`).
Self-test, no Reactor and no model server: `.venv/bin/python -m lenses.temporal.a_calendar dev|test`.
Scratch analysis: `lenses/temporal/scratch_a/` (explore_test.py, dev_gaps.py, abstain_terms.py, order_check.py).

## What the data says

**Test (34 of 36 temporal-style questions are "How many days apart / after").** Each event is one inserted sentence
("Oh, one more thing: My son's school play is on 2023-06-10, so...") in a session about something else. Every event
has 1-3 decoy sentences that share most of its words:

| decoy kind | examples (test, read qualitatively) |
|---|---|
| other person | "My friend Valentina entered her own alfajor recipe...", "Your friend Helen attended...", "My brother Brian started...", "Camille submitted her visa application today", "I heard Francesca attended..." |
| contrast / negation | "...on 2023-07-01, not the orthodontist appointment", "school concert ... separate from the play", "...in Toronto, not the one in Ottawa" |
| other year | "The league jamboree was on April 22, 2022" vs "...is on April 22, 2023"; "Our anniversary was June 21, 2022" + question says "this year" |
| sibling event | "second set of acoustic panels", "my previous car's annual inspection", "modular synth workshop", "Jazz Festival" vs "Tango Festival", "opening night" vs "closing night", "road test" vs "written test" |
| other possessor | "My wife's car had a tire change appointment" vs "my car's"; "colleague Jan's daughter" vs "your daughter's wedding" |

- Date formats: ISO, "June 27, 2023", "23 April 2023", "April 19" (no year), and in one history only "today" / "this
  morning" / "tonight" (the event date is the session date).
- The true fact is sometimes only in an assistant turn ("You left for your Ardèche canoe trip on 2023-07-12").
- **Abstention traps:** in h_3c02cbc4, 3-4 questions ask about events only the friend did ("Camille bought trail-running
  shoes today", "Camille had her pre-departure medical check-up today", "Camille got a sourdough starter today"); the
  user only says "I still need to sort out my travel vaccines".

**Dev is different** (133 temporal questions): 42 order questions, 30 "what did I do last Saturday / two weeks ago",
24 day gaps, 19 "how many days/weeks/months ago", 8 "how long had I been X when Y". The events usually carry no
written date: "I just got back from a guided tour at MoMA" means the session date. Gold day counts equal the gap
between the two evidence sessions in 23/35 cases; the rest are "two weeks ago", "last weekend, on June 18th", "on
2/15", "the 22nd of April", "a week before Black Friday" (both events in one session, the date only in the text).

**Exact-term abstention signal (dev):** a capitalised question word missing from the history catches 3/6 temporal
abstains with 0 false positives on answerable questions, once weekdays, months and holidays are excluded. It weakens
at 200 sessions: "Peter" turns up in another session in dev200.

## Variants, ranked by expected value on TEST

All four share one algorithm and differ only in pack size and in whether `computed` is emitted.

### 1. `cal`: event calendar + computed gap (pool=40, budget=8000, fill_k=6, alts=1)
Algorithm:
1. `parse_question`: templates → kind (`gap`, `ago`, `order`, `other`), unit, event phrases. It handles "apart were A
   and B" (split at an " and " followed by a determiner or gerund), "passed between", "after A did I / was / is B",
   "before A did I B" (swapped), "since A when B", "did it take to A after B", "ago did I A (when I B)", "how long had I
   been A when B" (`vague=True` because the expected unit is unknown).
2. Per event: candidates = `hx.hybrid(event, k=pool)` units plus a full scan of every unit that has a written date and
   shares a term with the event (cached per history). Split into sentences; abbreviations such as "St." are protected.
3. Sentence score = IDF-weighted stem coverage (half weight for rule synonyms; terms absent from the whole history and
   parenthetical aliases are dropped)
   - 0.4 if the subject is another person (`subject_kind`: "my/your + relation (+Name)" before a verb, "Name + verb",
     "I heard Name ..."; a relation is OK when the question uses it: "my son's school play")
   - 0.2 if event words fall inside a negation scope (not / separate from / rather than / instead of ... up to the next
     comma)
   - 0.15 for a contrastive modifier before a matched word that the question lacks (previous, second, regular, winter...)
   - 0.15 possessor missing ("my son's" in the event, absent from the sentence); 0.2 for a foreign relation possessor
   - 0.12 for a written year other than the question's year (0.3 if the question says "this year")
   - 0.15 for an assistant sentence that has no date
   - +0.25 for a named phrase or quoted title present verbatim
   - +0.08 for a written date, +0.04 for a relative one
   - +0.08 × retrieval rank bonus
4. Sentence date (`choose_date`): drop dates that are part of the event name ("the March 15th issue"), prefer a written
   year over an inferred year over a relative date, then the date nearest the matched words. If there is none, use the
   session date. Year inference picks the closest year, with future distance counted ×3. Holidays are resolved,
   including "a week before Black Friday".
5. Best sentence per event (the second event cannot reuse the first's sentence). Margin = best minus the best sentence
   with a different date.
6. `computed` = |dB − dA| in the asked unit (week = days/7, month = days/30.44). For `ago` it is the question date
   minus dA. It is emitted only if both scores are at least 0.55, both margins at least 0.08, the sign agrees with
   "after", and the unit is not vague.
7. Pack: chosen units first, then 1 alternate per event, then 6 hybrid(question) units. `build_pack(window=1,
   order="chrono", budget=8000)`. `cite_plan` = sessions of the chosen sentences, plus alternate sessions when the
   margin is small.

Hint sent to Reactor (example):
```
Date notes computed by code from the passages:
- "my son's school play" = 2023-06-10 (date written; session 2023/05/28: "Oh, one more thing: My son's school play is on 2023-06-10, so I need to shift…")
- "my daughter's orthodontist appointment" = 2023-06-24 (date written; session 2023/06/01: "Also, My daughter's orthodontist appointment is on 2023-06-24, right in…")
Difference between the two dates: 14 days.
Mentions of other people's events, other years, or events the text calls different/separate are decoys. Answer with just the number.
```
For order questions the hint lists each event's date, gives the chronological chain, and flags ties. A missing
proper noun adds "these words of the question never appear in the history: X".

`abstain_p`:
- 0.75 if a capitalised question word is absent from the history
- 0.7 if a third-person sentence covers the event at least 0.85 while the best own or impersonal sentence covers it
  below 0.75
- 0.6 if no sentence covers it at least 0.5
- 0.55 if the pick itself is third-person
- 0.25 if coverage is below 0.7
- 0.05 otherwise

Should move: HA and PA on day-count questions, CF1 (narrow `cite_plan`), abstention AUC.

Self-test, run with a crude lexical stand-in for `hybrid`:

| set | result |
|---|---|
| dev, count questions | `computed` produced for 53, within ±1 of gold for 43; 38 flagged confident, 35 of those correct (92%) |
| dev, 2-way order | 21/29 correct; most misses are ties where both events share one session date |
| test (qualitative) | on reading, about 31/34 picks are the true sentences; the three "only Camille did it" traps get abstain_p 0.6-0.7 |

Real-index smoke test, first 6 dev questions: ALL=1 on the 4 parseable ones; build takes 0.17 s per question.

Expected failure modes:
- the event is phrased with no shared words, e.g. "my trip to Bergen" vs "a veterinary conference in Bergen", which
  works only through the place name
- "before A did I B" where B's pronoun refers to A ("order her gift")
- "most recently" questions need the reverse order
- dev "how long" questions with durations ("for six weeks")
- assistant restatements with wrong dates
- `computed` wrong while the pack is right, so PA=0; this is why `cal_nocomp` exists

### 2. `cal_tight`: same, budget=4500, fill_k=0
Test events are single sentences, and the two chosen units ±1 turn already contain the answer. This saves about 1.5 S
points of the chars term. Risk: ALL drops whenever a pick is wrong, because there is no hybrid safety net. Expected to
win on test style and lose on dev order and "other" questions.

### 3. `cal_wide`: budget=12000, fill_k=14, alts=2, min_score=0.5, min_margin=0.05
Recall safety for dev-style questions (multi-event order, implicit session dates). It costs chars and puts more
decoys in front of Reactor. The narrow `cite_plan` keeps CF1 up.

### 4. `cal_nocomp`: `cal` without `computed`
Same pack and hint; PA falls back to ALL ∧ ATR. Run it to see how often HA gating, rather than retrieval, costs PA.
Reactor still gets the gap in the hint either way.

## Not built yet (next round)
- **Question-side time window** for dev "what did I do last Saturday / two weeks ago / in January": resolve the
  expression against the question date with the same grammar, restrict candidates to sessions within ±2 days (±4 for
  weeks, ±10 for months), and state the resolved date in the hint. This follows the LongMemEval time-aware expansion
  (+11% round recall). It targets 30 dev questions and about 0 test questions, so it is ranked low.
- Same-date order tie-break from in-text cues ("a month ago", "before", turn order).
- Duration grammar ("for six weeks", "about 3 months ago when I started").

## CORE REQUESTs
1. `core.dates`: consider adopting this grammar: holidays and "a week before <holiday>", "the 22nd of April", M/D
   only after on/the/since (so "1/2 teaspoon" is ignored), future-penalised year inference, `choose_date` dropping
   dates inside the event name.
2. A cached sentence split per unit (`hx.sentences(uid)` → [(offset, text)]) so lenses don't re-split.
3. In the final pipeline, use `cite_plan` for temporal citations. Gold evidence is the 2 event sessions, and the
   hybrid fill would otherwise add 2-4 wrong citations.
4. Router: "How many days apart/after/before" → temporal with high confidence (34 test questions).
