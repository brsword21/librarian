# SSA lens B ("Semantyka"): design, round 0

Type: single-session-assistant, i.e. something the assistant said or recommended. About 17% of test. Lens file: `lenses/ssa/b_semantic.py`. Scratch analysis: `lenses/ssa/scratch_b/`.

## What the data says

### Dev and dev200 (LongMemEval)
Session retrieval is solved. BM25 alone ranks the gold session first for 112/112 dev questions and 22/22 dev200 questions (`scratch_b/qexp.py`). The difficulty is at chunk level:
- Every question has exactly one gold turn. 102/112 are assistant turns and 10/112 are user turns (for example "what show did *I* use as an example").
- Gold turns run 1.2k chars at the median and 2.5k at p90, so they are split into 1 to 9 units. The answer sits in chunk 0 in 48/68 extractive cases, chunk 1 in 14, and chunks 2 to 3 in 6. Packing only the best unit with ±1 neighbour misses about 10%.
- The decoys are sibling turns of the same session that repeat the entity. In the Bandung question, turns t5, t9 and t11 all name "Miss Bee Providore", but the gold turn is t7. The session is right and the turn is wrong, so ATR=0.
- Measured on gold-turn rank@1 with BM25: weighting assistant units ×1 against user units ×0.6 raises it from 0.62 to 0.74 on dev and from 0.45 to 0.68 on dev200. Round aggregation (adding the preceding user turn's match) gives the same gain on dev200. A declarative query does nothing for BM25; it is meant for the dense channel.

### Test (qualitative only: `scratch_b/short_recs.py`, `scratch_b/test_audit.py`)
Test SSA uses a different, injected pattern. Short persona sessions (8 to 10 turns of about 200 chars each, about 2k chars per session) sit among LongMemEval-style filler sessions. The answer is a single short assistant sentence:

> "For your Python data cleaning project, **I recommend** using pandas …"
> "Oh, For the audio coupling capacitor in your Panasonic RF-2200, **I'd use** a 0.022 µF film capacitor."

Its *purpose phrase echoes the question* ("…did you recommend for my data cleaning project?"). The near-misses are systematic:

| Decoy kind | Test example (pattern) |
|---|---|
| Same category, different purpose | "For your data **visualization** project, I recommend matplotlib"; "For **strength and mobility** work, I recommend Coach Elena" |
| Recommended to someone else | "I recommended Café Rosa's … **to a friend**"; "…a saddle fitter … **for your neighbor** Bjørn's horse" |
| Third party recommends | "**The beekeeping association recommended** De Zwarte Bij"; "**Coach Miriam sometimes sends runners to** Centennial Park … I haven't been there myself" |
| Hedged or negative | "I'd **avoid** TD for now"; "I recommended 'The Phoenix Project' … **but that is more about** software delivery" |
| User-mentioned item | "I used a day pass at Avila Spaces"; "I opened a Clockify account"; "Toshi used a 0.01 µF coupling capacitor" |
| Listed options, not a pick | "Clockify is free … Toggl Track is also very smooth … Harvest is another" |
| Probably unanswerable | coworking space in Lisbon: no assistant recommendation exists, only the user's Avila Spaces |

Generic-topic BM25 combined with the speech-act features put the injected first-person recommendation at rank 1 for 13 of 15 test sample questions. On the other two, the dentist and drum-plugin questions, it ranked first among the assistant units and the units above it were user turns. Some recommendation sentences also sit inside a filler sentence ("That reminds me about local appointments. For your next dental check-up, I recommend Dr. Vogel").

## Variants (ranked by expected value on TEST)

### 1. `rec`: speech-act-aware hybrid with rerank (top pick)
**Idea:** retrieve like a good RAG system, then rescore candidates by whether the assistant itself recommended the asked category for the asked purpose. Precompute that judgement as a short note for Reactor.

**Algorithm** (`rank_units`, `session_scores`, `select_units`, `build`):
1. Parse the question with pure-python regex:
   - `clean_question` drops meta-cues ("I'm going back to our previous chat about", "can you remind me") and keeps "recommend".
   - `split_topic` extracts the topic from cues like "conversation about/where X" or "we discussed X".
   - `parse_rec` extracts the category and purpose ("Which **code editor** did you recommend I use **for my Python practice scripts**?").
   - `declarative` builds the statement form ("For your Python practice scripts, I recommend the code editor").
2. Build the candidate pool by RRF:
   - `hx.hybrid(clean, k=120, roles=[assistant])` with weight 1.0
   - `hx.hybrid(clean, k=120, roles=[user])` with weight 0.6
   - `hx.dense(declarative, k=60, roles=[assistant])` with weight 0.5
3. Rerank the top 40 with `hx.rerank(clean, top40)` and z-score the results. Then add:
   - **round bonus** `0.35 × match(prev user turn)` from `hx.bm25(topic or clean, roles=[user])`
   - **topic bonus** `0.25 × match(session's user turns vs topic)`
   - user-unit penalty −0.3
   - on recommendation questions, a **rec bonus** `0.6·rec + 0.6·purpose·[rec>0] + 0.2·cat`. Terms:
     - `rec` = +1 for a first-person "I recommend / I'd use / I suggest", 0.4 for past tense, −1.2 when made for another person, −0.6 for a third party, −0.8 when hedged or negative.
     - `purpose` = IDF-weighted overlap between the question's purpose phrase and the sentence, using history DF so that "data" and "project" count little and "cleaning" counts a lot.
     - `cat` = category substring match (bank ↔ Scotiabank).
4. Session score: NDCG of unit hits (Emergence), with **each session capped at its 2 best units**. Without the cap a long, broadly related session outvoted the gold one: dev SR went from 0.982 to 0.991.
5. Pack (`select_units`, then `build_pack(order="chrono", max_sessions=3, budget=7000)`), filled top-session-heavy:
   - every chunk of the best turn of session 1
   - its best unit with ±1 neighbour (brings in the user turn before it)
   - its other units in fused order
   - then the rest of session 1 if it is small (test gold sessions are about 2k chars, so the whole session goes in), capped at `top_budget=5000`
   - then the best unit of sessions 2 and 3, as near-miss candidates for Reactor to contrast
6. `cite_plan` = top session only, since SSA gold is always 1 session.

**Hint** (recommendation questions only; empty otherwise):
> Answer with the code editor the assistant itself recommended for my Python practice scripts. Recommendations for other purposes or other people, options only listed, and things the user mentioned do not count. Recommendation sentences found: (2023/06/02) "Yes, absolutely. I recommend using Visual Studio Code for your Python practice scripts because …"

When `abstain_p ≥ 0.6`, the hint adds: "Note: no assistant turn found recommending a coworking space in Lisbon; if the passages do not show one, answer INSUFFICIENT_EVIDENCE."

**abstain_p:** for recommendation questions it is `0.05 + 0.65·(1 − match) + 0.25·p_flat`. Here `match` = max over candidate assistant units of `rec × min(1, purpose/0.6) × (1 if cat matches or cat is generic else 0.6)`, and `p_flat` is a sigmoid of the gap between the top-1 fused score and the mean of ranks 2 to 10. Otherwise it is `0.6·p_flat`. On the 15 test samples, the coworking/Lisbon question scores 0.70 and every other question scores ≤ 0.32.

**Expected failure modes:**
- Free paraphrase between the question purpose and the recommendation ("dental check-up" vs "dentist"), which lowers `purpose` and raises abstain_p. Dense and rerank carry the retrieval, but the hint line can be missed.
- A recommendation spread over two sentences ("there's a solid option. For dinner with your sons, I'd recommend …") is fine because the scoring is per sentence and the unit is kept.
- Lists ("Here are some recommendations: 1. X …") get `rec = 0` and fall back to rerank.
- Dev questions that ask about a non-first chunk of a very long turn when the session exceeds `top_budget`.

**Metrics that should move:**
- Test: answer accuracy on near-misses (Reactor gets the contrast note), CF1 (cite 1 session), and abstention recall on SSA-style unanswerables.
- Dev: ATR and PA through the top-turn expansion. Chars should drop to about 6k.

### 2. `rec_wide`: same as `rec` with a wider net
`n_sess=4`, `budget=10000`, `top_budget=7000`, `rerank_n=60`, `pool=150`. Insurance in case the real dense/rerank stack ranks the gold session third or fourth on 200-session test histories. It costs about 2.7k chars (−0.8 S) for a recall gain that dev cannot show, because dev SR is already 1.0. Choose it over `rec` only if dev200 SR@3 < 1.

### 3. `lean`: precision first
`n_sess=2`, `budget=4500`, `top_budget=3500`, `rerank_n=30`. Test sessions are short, so the whole gold session plus one contrast session fits in about 4k chars. It is worth it if Reactor degrades with longer context (RESEARCH: small readers drop beyond about 3k tokens). On the dev dry run it loses about 7 PA points (Bandung-type same-session sibling turns), so it ranks below `rec`.

### 4. `plain`: ablation control
`rec` without the speech-act features or the hint (`w_rec=0`, `hint=False`). It should tie `rec` on dev and dev200, which contain no injected recommendation sentences; the dry run gives S 87.0 for both. Any dev gap would mean the rec features hurt LongMemEval-style list answers. Compare test packs of `plain` and `rec` with `harness.audit` to check that the decoy separation works qualitatively.

## Dry-run numbers
These come from `scratch_b/dryrun.py`, with BM25 standing in for dense, hybrid and rerank and a crude `build_pack`. They are relative numbers only; the real ones come from `harness.sweep` in round 1.

| split | variant | PA | ATR | SR | CF1 | chars | S≈ |
|---|---|---|---|---|---|---|---|
| dev (112) | rec | .955 | .973 | .991 | .991 | 6209 | 89.9 |
| dev (112) | lean | .884 | .902 | .982 | .982 | 3879 | 85.7 |
| dev200 (22) | rec | .955 | .955 | 1.0 | 1.0 | 5971 | 90.2 |
| dev200 (22) | rec_wide | .955 | .955 | 1.0 | 1.0 | 8771 | 89.3 |
| dev200 (22) | lean | .909 | .909 | 1.0 | 1.0 | 3799 | 87.9 |

The remaining dev misses are chunk-level ("what year did construction begin" in a long legal-case turn; a not-quite-extractive list of back-end languages) and one uncued question ("second sad song") whose session BM25 alone misranks. Dense and rerank should fix the last one.

Not used:
- **Time decay:** recency does not separate test SSA decoys; purpose does.
- **MMR across sessions:** replaced by "1 best unit per runner-up session".
- **LLM reformulation:** not allowed.

## CORE REQUESTs
1. **`roles` argument:** document its type. The lens passes `roles=["assistant"]` and falls back to post-filtering on `TypeError`.
2. **Abstention probe for SSA:** dev has 0 unanswerable SSA questions, so the abstain AUC is undefined. Proposal: a harness flag `--ablate-gold` that drops the gold sessions from the history (a `HistoryIndex` over the filtered sessions), which turns every answerable dev question into a near-miss unanswerable one. That would calibrate abstain_p for SSU and SSA without touching test.
3. **Reranker input:** confirm `hx.rerank` scores `Unit.index_text` (ctx + text). The ctx (the user's question before the turn) is what links "for dinner with your sons" to a bare "I'd recommend Matilda 159 Domain".
4. Optional:
   - `hx.idf` per history; the lens computes its own, cached by `id(hx)`.
   - A `build_pack` option to include a whole session when it is under N chars. The lens emulates it today by passing every uid of a small top session.
