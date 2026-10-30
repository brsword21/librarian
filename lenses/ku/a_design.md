# KU lens A ("Struktura"), Round 0 design

Code: `lenses/ku/a_timeline.py`. Self-test: `.venv/bin/python -m lenses.ku.a_timeline`. BM25-only pair check, no model server: `... -m lenses.ku.a_timeline --bm25 dev dev200`. Scratch scripts and dumps are in `lenses/ku/scratch_a/`.

## What the data says

### Dev (72 answerable, 6 unanswerable; dev200 22 + 4)
- Gold turns are always **user** turns. Each one is a "by the way" aside that restates the attribute with nearly the question's wording ("charity 5K run", "Korean restaurants", "Fitbit Charge 3").
- BM25 on user units with the cue words removed puts both gold sessions in the top 2 on 60/72 questions and in the top 5 on 67/72. On dev200 the numbers are 18/22 and 20/22. **Retrieval is mostly solved on dev. Points are lost on the citation pair (CF1, weight 0.30) and in reading.**
- The question's direction is not always "latest". 9/72 ask for the earlier value: "previous", "initially", "before I updated", "earlier … before the 7/22 trip", "when I just started". 2 ask for both values. 3 ask for a comparison ("more or less water", "increase or decrease", "more frequently than previously").
- The new value is often a running count or a total ("three → four restaurants", "4 → 5 MCU films", "27 → 32 species"). Some updates are corrections ("Actually, I need 120 stars, not 300") or relative ("I just added a new coin" to 37 gives 38).
- Data quirk: in q_caf8db8008c5 the session with the newer value ("six times") has an earlier timestamp than the one with the older value ("four times"). Pure date order fails there; for counts, the larger value would be right.
- All 6 unanswerable questions are **entity substitutions** of a real KU question: Italian/Korean, Dr. Johnson/Dr. Smith, Shinjuku/Harajuku, football/baseball, table tennis/tennis, "Software Engineer Manager"/"Senior Software Engineer".
  - A capitalised question term (not a month or weekday) that never appears in user turns flags 3/6 of them and 0/72 answerable KU questions. Across all dev types the false positives are almost all month or weekday names, plus SSA questions whose entity appears only in assistant turns.
  - IDF-weighted coverage of the question terms by the best user turn is a continuous signal. Threshold 0.7 catches 4/6 and flags 13/72 answerable on dev; on dev200 it catches 3/4 and flags 2/22.

### Test (qualitative only, 15 KU-style sample questions)
Test KU is built differently from dev: **injected fact pairs plus deliberate near-misses**.
- **Old and new value as short injected sentences**, often after a discourse marker ("Random note from class:", "Unrelated work thing:", "Oh, and", "By the way,"). Example: "My ceramics class instructor is Miguel Silva." (April) → "The studio hired Ana Ferreira to teach my Wednesday ceramics class after Miguel moved to Porto." (August).
- **The new value is paraphrased** and can lack the question's head noun:
  - instructor → "hired … to teach"
  - job title → "I got another promotion, so now I am Director of Clinical Services"
  - store → "I've started buying all my Moroccan spices at Marrakech Market"
  - long run → "my half-marathon long runs on Saturdays at 7:00 a.m."
- **The new value can live only in an ASSISTANT turn**:
  - "You mentioned you increased your evening walk to five kilometers"
  - "Margaret has retired, so your Saturday morning watercolour class is now taught by Priya Nair"
  - "You mentioned your long run has shifted to Sundays at 6:30 a.m."

  A user-only index misses these.
- **Possessor decoys with the same attribute and the same kind of value**:
  - "My friend Clara's UX team has six people"
  - "My sister Amina is still on a 15GB mobile data plan"
  - "My running partner's Saturday long run starts at 7:30"
  - "Your sister's children's book has 12 chapters"
  - "Bjørn's daughter has 2 Icelandic horses"
  - "He / Carlos drinks three cups of coffee"
- **Attribute and location decoys**:
  - "My UX team uses six different research tools"
  - "a 25GB monthly data cap on my home Wi-Fi router"
  - "The UX team in the Munich office has eight people"
  - "a new client named Bruno Almeida" (same name as the new accountant)
- **Haystack noise with the same attribute**: "I swam my usual 40 laps" repeated in organic sessions around the injected 20 → 30 laps pair, and "My current rent is only 9,000, shared." after the injected 18,000 → 22,000. A blind "latest wins" picks the noise. A quoted timeline lets Reactor see both.
- **Relative updates and sums**: "I bought 2 more Icelandic horses" on top of "I currently have 9"; "How many … do my neighbor Bjørn and I have in total" is a KU plus a sum over two owners.
- Possible exploit, not used: injected sentences often end in a stray "., so" or "..", and assistant injections capitalise after a comma ("Oh, and Your daughter…"). This is a generator artifact. I did not use it: it is brittle and close to tuning on test.

## Variants (ranked by expected value on TEST)

All variants share the same core logic in `a_timeline.py`:
- **Question parsing.** `parse_question` sets:
  - the answer type: number / time / day / freq / duration / name / place / yesno / other;
  - the direction: latest / previous / both / compare (regex grammar);
  - the key stems, after removing cue words ("now", "currently", "these days", "so far", …);
  - the rule synonyms: 19 groups such as instructor~teach~taught~tutor, title~role~position~promotion, store~shop~market~buy, name~named~renamed~call, team~people~members~hires, walk~km~kilometers, purchase~buy~bought~got;
  - the capitalised terms;
  - the owners named in the question (`q_owners`: relation words and names, so "my neighbor Bjørn" or "Emma's recipes" is not treated as a decoy).
- **Mention extraction.** `extract_mentions` scores each sentence of the top 80 candidate units:
  - score = IDF-weighted key coverage (synonyms count) + 0.25 if a value of the answer type is present + 0.08 for a change cue + a retrieval rank bonus, minus 0.6 for another owner, minus 0.35 for assistant text that is not a recap;
  - short replies inherit coverage from `Unit.ctx` ("She moved to Chicago.");
  - a sentence without a value is merged with the next sentence when that one carries the value ("…charity 5K run… By the way, … best time of 25:50").
- **Ownership** is judged on the clause that carries the key terms. It checks:
  - `REL's` and `Name's REL` possessives;
  - `my/your REL (Name) <verb>` subjects;
  - `He/She …` at the start of a sentence;
  - a bare `Name <verb>` subject.

  Names and relations that appear in the question are exempt.
- **Timeline.** `build_timeline` keeps the best mention per session (own mentions only) in chronological order:
  - N (newest) is the latest mention whose score is at least max(0.75, 0.7 × top score). The relative threshold stops late noise mentions with partial coverage from becoming N.
  - O is the strongest of the last 3 earlier mentions whose values differ from N's (`older_mode="strongest"`: strongest anywhere).
  - The citation plan is `[O, N]`.
- **Pack.** `build_pack` gets this order: mention units of O and N, then the other own mentions, then all mentions, then the ranking. Order is chrono, window ±1, `max_sessions` 5, budget 6000 (about 1.9 S points cheaper than the 12k default).
- **computed.** Set to the newest value only when the direction is latest, the answer type is number, there is exactly one value and it is not a relative update (diagnostic: HA).

### A1 `tl_rerank` (default)
- **Retrieval:** RRF of `hx.bm25(cleaned q)`, `hx.bm25(cleaned q + synonyms)` and `hx.dense(cleaned q)`, all roles, pool 200. Then `hx.rerank(question, top 40)`, prepended to the rest.
- **Why it ranks first:** the cross-encoder is what finds paraphrased new values that lack the head noun (job title, store, instructor) and assistant recaps. The timeline hint and the ownership filter handle the test's near-misses.
- **Hint** (direction sentence + up to 4 dated quotes + optional notes):
  ```
  This asks for the CURRENT value. It changed over time: the most recent statement (latest session date) about the user's own value wins over older ones.
  Dated mentions found (oldest first):
  - 2023/04/11: "Random note from class: My ceramics class instructor is Miguel Silva."
  - 2023/08/03: "On another note: The studio hired Ana Ferreira to teach my Wednesday ceramics class after Miguel moved to Porto."
  Ignore values that belong to other people (friend, relative, coworker, neighbour) unless the question is about them.
  ```
  - The other directions use: "…asks for the EARLIER value, the one that held before the most recent change; do not answer with the newest value." / "Give both values…" / "Compare the earlier value with the latest one…".
  - The ownership line is added only when other-owner mentions were actually seen.
  - "If a later statement only gives a change (e.g. '2 more'), apply it to the earlier value." is added when N is a relative update.
  - Absent-term notes: `Note: "Shinjuku" never appears in the conversation history.` (absent from all turns), or `Note: the user never mentions "Johnson".` (absent from user turns).
- **abstain_p:** `0.06 + 0.55·max(0, 0.9 − best_user_coverage)/0.9`, plus:
  - +0.40 if a capitalised non-date question term is absent from the history;
  - +0.25 if it is absent from user turns only;
  - +0.08 if any key stem is absent from user turns;
  - +0.20 if only other-owner mentions exist (a "my rent" question with only "my sister's rent");
  - −0.08 if both N and O have values.

  Clipped to [0.02, 0.95]. Dev examples: Dr. Johnson 0.52; normal answerable 0.02–0.08.
- **Expected failure modes:**
  - Location decoys ("The UX team in the Munich office") count as own.
  - O is chosen from organic noise (laps 40 instead of 20). N stays right and Reactor sees the timeline.
  - Multi-owner sums (Bjørn and I) get the right sessions only partly.
  - The date-reversed dev quirk.
  - The `_attr_label`/synonym list is English-only and hand-made.
- **Metrics that should move:** CF1 (pair vs top-k: BM25-only pair-F1 is 0.958 vs 0.910 for user-top-2 on dev and 0.909 vs 0.909 on dev200), PA through the newest gold session being in P (69/72 newest in pair with BM25 only), chars (6k budget), and abstention AUC.

### A2 `tl_hybrid`
A1 without the cross-encoder; the rest is identical. It is cheaper and it isolates the reranker's contribution. Expected to tie A1 on dev (BM25 already finds the gold) and to lose on test-style paraphrases. Use it if rerank latency or the model-server load becomes a problem.

### A3 `rule_top2`
- **What it does:** hybrid retrieval without synonyms, cites the top-2 sessions by fused rank, sends only the direction sentence plus ownership and absent-term notes (no quotes), with `max_sessions` 4.
- **Why it exists:** it is the simple baseline the timeline must beat by ≥2 S. Its hint is short and safe (no quoted sentences that could mislead Reactor).
- **Expected:** CF1 about 0.91 on dev. It loses on dev questions whose second-ranked session is a third mention.

### A4 `tl_wide` (robustness)
- **What it does:** A1 with budget 9000, `max_sessions` 8, pool 300, rerank top 60. A recall safety net at 200-session scale. The 0.05·chars/16000 penalty costs about 0.9 S more than A1.
- **When to pick it:** only if dev200 or audit show the newest gold session missing from P.
- **Also in the file:** `tl_bm25` (no model server, used by the self-test and as a fallback) and `tl_rerank_strong` (A1 with `older_mode="strongest"`: on test-style questions it picks the right old value more often, e.g. ceramics 27 instead of 31, but it cost 1 question on dev200, so it is not the default).

## Notes for the generic path and the router (CORE REQUESTs)
1. **KU detection from evidence, not from cue words.** The router finds 19% of dev KU questions. `a_timeline.analyse(q, hx, p)` is cheap after retrieval (sentence regexes over 80 units). The generic path could call it and switch to KU handling when the timeline has at least 2 own sessions whose values differ and the question has no temporal-difference cue ("how many days"). Please expose a hook: `generic → analyse() → if ku_like: use the KU hint and cite_plan`.
2. **Do not restrict KU or the generic path to user turns.** Test updates live in assistant recaps ("You mentioned…", "…is now taught by…").
3. **`build_pack` pin option.** I would like a way to force the units of the two cited sessions into the pack ahead of the window expansion (`pinned_uids=`), so the budget cannot drop O. Today I rely on ranking order.
4. **`Unit.ctx` is valuable** for short replies ("She moved to Chicago."). Keep it.
5. If the final pipeline post-filters Reactor's citations, use `cite_plan`. KU gold is always 2 sessions, and a third cited session costs about 0.2 F1.

## Ideas for Round 1+
- Multi-owner questions ("my neighbor Bjørn and I"): split them into one attribute query per owner and list both timelines in the hint.
- Location-qualified decoys ("in the Munich office", "at my old job"): treat a prepositional qualifier missing from the question as another owner.
- For monotone counters (times, followers, pages, episodes), when two values conflict with the dates, prefer the larger one (the dev date-reversal quirk) and say so in the hint.
- Sweep `rel` (0.6/0.7/0.8), `cov_min` (0.3/0.34/0.4), `max_sessions` (3/5) and `older_mode` on dev, with dev200 as the gate.
