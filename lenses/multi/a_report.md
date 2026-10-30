# Lens A "Struktura" for multi-session: Round 1 report

Lens: `lenses/multi/a_tally.py`. Best variant: **`bm25_tight`**.
Scratch: `lenses/multi/scratch_a/`:
- `cite_an.py`: offline cite-rule search over `debug["sess"]`
- `miss_an.py`: missed gold turns, and whether their session was packed
- `audit_check.py`: grep a test history and mark which hits made it into the audit pack

## Headline

`bm25_tight` scores **S 83.0 on dev and 82.2 on dev200**, at about 11.9k chars. The kit's naive baseline on multi scores 17.6 and 13.7. My Round-0 draft scored 68.6 and 65.7.

It needs no model server. One question takes about 0.1 s on dev and 0.3 s on dev200.

I could not measure the generic `hybrid_rr` bar on multi this round:
- The shared model server was backlogged for the whole session. Every model-dependent sweep on the machine sat at 0% CPU, including all `generic hybrid_rr` sweeps.
- The reference from the task is S ≈ 73, PA ≈ 0.93 and CF1 ≈ 0.55, on an 80-question sample across all types. `bm25_tight` beats it by about 10 points, almost all of it from CF1.
- The hybrid variants of my lens (`ledger`, `ledger_rr`) are defined but not yet measured. A 40-question `ledger` run is queued under the tag `r1-multi-a-hyb`.

**Late result (model server came back at the end):** `ledger` (the same lens with hybrid BM25 + dense recall) on the first 40 dev multi questions, tag `r1-multi-a-hyb`:
- `ledger`: S 83.2, PA 0.950, ALL 1.000, CF1 0.837, 11.9k chars, 4.5 s per question
- `bm25_tight` on the same 40: S 81.1, PA 0.925, ALL 0.975, CF1 0.825

That is +2.1 S. If the gain holds on the full dev and on dev200, `ledger` becomes the best variant. First job of the next round: full dev and dev200 sweeps of `ledger` and `ledger_rr`.

## Results (harness.sweep, multi; tags r1-multi-a)

| split | lens / variant | S | PA | ATR | SR | ALL | CF1 | chars | AUC |
|---|---|---|---|---|---|---|---|---|---|
| dev (133; 121 answerable) | generic naive | 17.6 | 0.066 | 0.243 | 0.551 | 0.306 | 0.526 | 7885 | 0.50 |
| dev | generic hybrid_rr | not measured (model server backlog); ref ≈73 on all-type sample | | | | | | | |
| dev | a_tally Round-0 draft (`bm25`, 15k) | 68.6 | 0.893 | 0.957 | 0.977 | 0.942 | 0.509 | 14851 | 0.62 |
| dev | **a_tally bm25_tight** | **83.0** | 0.950 | 0.981 | 0.994 | 0.984 | 0.832 | 11937 | 0.737 |
| dev | a_tally bm25 (15k, ±1 ctx) | 82.1 | 0.950 | 0.981 | 0.994 | 0.984 | 0.832 | 14853 | 0.62* |
| dev | a_tally bm25_12k (±1 ctx) | 83.0 | 0.950 | 0.981 | 0.994 | 0.984 | 0.832 | 11871 | 0.62* |
| dev | a_tally bm25_10k (±1 ctx) | 83.1 | 0.942 | 0.981 | 0.992 | 0.975 | 0.832 | 9888 | 0.62* |
| dev | a_tally turns | 70.4 | 0.752 | 0.909 | 0.991 | 0.967 | 0.835 | 11118 | 0.62* |
| dev200 (28; 22 answerable) | generic naive | 13.7 | 0.045 | 0.189 | 0.467 | 0.227 | 0.450 | 9006 | 0.50 |
| dev200 | a_tally Round-0 draft (`bm25`, 15k) | 65.7 | 0.864 | 0.961 | 0.991 | 0.955 | 0.469 | 14588 | 0.58 |
| dev200 | **a_tally bm25_tight** | **82.2** | 0.955 | 0.992 | 0.991 | 0.955 | 0.795 | 11934 | 0.606 |
| dev200 | a_tally bm25 (15k) | 81.3 | 0.955 | 0.992 | 0.991 | 0.955 | 0.795 | 14744 | 0.58* |
| dev200 | a_tally bm25_12k | 82.2 | 0.955 | 0.992 | 0.991 | 0.955 | 0.795 | 11860 | 0.58* |
| dev200 | a_tally bm25_10k | 82.8 | 0.955 | 0.992 | 0.991 | 0.955 | 0.795 | 9921 | 0.58* |
| dev200 | a_tally turns | 67.6 | 0.727 | 0.891 | 0.991 | 0.955 | 0.795 | 11117 | 0.58* |

\* These rows were swept before the last abstention change. Their abstain_p is the same function as `bm25_tight` apart from that change.

## What changed (one hypothesis per sweep; S on dev / dev200)

1. **cite_plan by session-score fraction** (68.6 → 78.0 on dev).
   - The rule: sessions whose score is at least 0.8 × the best score, at most 5.
   - It replaces "up to 6 sessions with a clean lexical hit". Mean cite size falls from 5.1 to about 2.5 (gold is 2.6).
   - I chose the rule offline with `cite_an.py` over 70 candidates. The fraction 0.75–0.8 is a plateau on both splits.
   - Offline CF1: dev 0.51 → 0.82, dev200 0.47 → 0.76.
2. **Every user unit of a kept session competes for the per-session slots** (78.0 → 79.6).
   - Before, only units in the fused list could be picked. "By the way, I'm also getting Architectural Digest" shares no word with "magazine subscriptions", so it never made the list.
   - A unit with no lexical hit is rendered as its fact sentences only (by-the-way, or first-person verb + number), not the whole unit.
3. **Attribute patterns plus a small category lexicon** (79.6 → 83.0).
   - Patterns:
     - age questions ("how old", "years older", "average age") ↔ "I'm 32 / just turned 32 / 32-year-old"
     - "typical week" ↔ "on Mondays / twice a week"
   - Category words: aquarium→tank, fish→tetra/gourami, antique→heirloom, magazine→digest, fitness→class names, graduate→degree.
   - This fixed 6 of 13 failures. These are generic category→instance words, but I picked them from dev failures, so expect less transfer.
4. **Budget 15k → 12k** (`bm25_12k`: dev +0.4, dev200 +0.9). PA did not change. 10k loses on dev200 with ±1 context.
5. **Tight excerpts** (`bm25_tight`: no ±1 context sentence, keep sentences ≥ 0.8 × the unit's best, up to 40 sessions).
   - Dev and dev200 are a tie with `bm25_12k`.
   - On the test audit the pack holds **20–32 sessions instead of 13–17**. On dev the evidence is 2–3 sessions; on test, counting questions have 10–20 instances.
   - per_session 3 was worse (PA 0.884): long dev gold sessions have 2 gold turns.
6. **Strong-first ordering only inside the time window.** Before, off-window "strong" sessions were packed first and pushed out in-window instances (test: August blood-pressure readings). No dev effect, as expected, because the window never engages on dev.
7. **Units with no lexical hit capped at 2 per session**, after the lexical units.
   - On test, orchid chit-chat turns no longer eat the budget: 17 → 24 sessions on the BP question.
   - A cap of 1, or counting only a full hit (≥ 1.0) as lexical, cost 1.1 on dev (bread→bake synonym hits, "visited The Art Cube").
   - Final: any lexical hit counts, cap 2. Dev and dev200 are unchanged.
8. **Event verbs and an amount pattern that count only inside a topic sentence**, plus a BP-reading pattern (`\d{2,3}/\d{2,3}`, "128 over 82").
   - Event verbs: "added / acquired / bought" ↔ "picked up / got / gift / new".
   - Amount pattern: "spent / cost" ↔ "$ / pesos".
   - Dev −0.4, dev200 +1.0 (CF1 0.763 → 0.795). This is noise-level on dev, but it closes the test-audit gaps: "I picked up one Phalaenopsis orchid", and the Aug 7/12/19 BP readings are now in the pack.
9. **Abstention signal: no user unit holds both words of the question's head noun pair** ("egg tarts", "chili peppers"), with scaffolding words filtered out. AUC dev 0.62 → 0.74, dev200 0.58 → 0.61. abstain_p only; the hint is unaffected.
10. **Count hint gains one sentence**: "If the user states the total directly …, use the latest such statement." The test audit shows KU-like count questions ("How many ceramic pieces am I putting in the class show?").

## Best variant: `bm25_tight`

The pipeline:
- **Ranking:** BM25 over user units, plus a lexical sweep. The sweep covers head stems, phrases, category synonyms, attribute patterns and event verbs.
- **Window:** a soft time-window ×0.15 for units outside it. It engages only when the history spans at least 21 days and the window covers ≤ 85% of sessions.
- **Session score:** the best unit plus 0.3 × the second-best unit, plus a fact prior.
- **Packing:** up to 4 units per session, rendered as matching sentences, oldest first, into 12k chars.
- **cite_plan:** sessions with a score ≥ 0.8 × the best score, at most 5.
- **Hint:** chosen by question kind (count / sum / diff / current / avg), with the window sentence when a window applies.

Qualitative test audit (12 questions, `harness.audit`):
- Every first-person "tango shoes" purchase is in the pack. So are the decoys (friend Valentina, "skipped", "tried on … decided not to"), so the hint has to do the filtering.
- 14 of 15 August BP readings are in the pack.
- All orchid acquisitions since March are in the pack.

## Top failure patterns (dev / dev200, bm25_tight)

1. **No shared vocabulary and no attribute pattern** (sessions not packed).
   - "How many projects have I led …" vs "I recently presented a poster on my research …". The gold calls a poster presentation a project.
   - "How many years will I be when my friend Rachel gets married?" vs "I'm 32, so I'm in my 30s." The age pattern fires, but the session ranks below the many "Rachel / married" sessions and falls out of the budget.
   - Dense or rerank recall is meant for these (`ledger`, `ledger_rr`), not measured yet.
2. **Gold turn in a packed session but not among the chosen units.**
   - Museums in February: "… James Parker, whose work I recently saw when I visited The Art Cube on 2/15". The words "museum" and "gallery" are absent.
   - Instruments: "my black Fender Stratocaster electric guitar". The lexical hit is weak, and "guitar" is in the lexicon only under "instrument", not "musical".
   - dev200, health devices: "the gold session #90 MISSING". Devices of different kinds have no shared word.
3. **Unreachable or odd gold turns.** An assistant-turn gold ("Congratulations on raising $250") whose user turn says the same thing. Another gold turn is "No, that's all for now. Thanks for your help!". Together they cap dev ATR at about 0.98.
4. **Abstention stays weak** (AUC 0.61–0.74). Unanswerable multi questions usually have one facet missing ("headphones and the **iPad**", "**30-gallon** tank"). Others are answerable-looking with only a window mismatch ("museums in **December**" on dev, where the window cannot engage).

## CORE REQUESTs

1. **Model server throughput.** All hybrid and rerank sweeps on the machine stalled for 60+ minutes at 0% CPU while `core.precompute dev` ran.
   - Please make the precompute yield to interactive requests, or batch across clients.
   - Alternatively, publish when the dev, dev200 and test embedding caches are complete, so lens agents know when hybrid sweeps are usable.
2. **`message_chars` signature.** The real one is `message_chars(q, passages, hint)`. My Round-0 draft assumed `(question, hint, passages)`; it is fixed in the lens. Please list the exact signature in CONTRACT.md: it is written there without argument names.
3. **`harness.failures`: print the missed gold turn when its session is IN the pack.** It prints all gold turns now. A per-turn "included / missed" mark, using `included_turns` saved in per_question.jsonl, would make within-session failures obvious. My lens stores `debug["inc"]` for this.
4. **Save `cite_plan` in the audit's `test_packs.jsonl`,** so CF1 behaviour on test-style decoys can be reviewed.
5. **Final citations for multi must come from `cite_plan`.** The pack holds 20–30 sessions for recall while gold has 2–5. Agent B asks for the same.

## Ideas for the next round

1. Measure `ledger` and `ledger_rr` (hybrid and rerank recall) once the server is free. Expected gains are on pattern 1 at dev200 and test scale. Keep `bm25_tight` as the fallback that needs no server.
2. **Sentence-level session score for test.** Score each session by its best fact-like topic sentence (topic hit + first-person event verb + number), not by unit RRF, so that chatter-heavy topics (orchids, swimming) rank instance sentences first.
3. **Code-side ledger as a note passage** (`Passage(id=None)`). It would list date | session | sentence for in-window, own, non-negated topic sentences with a number, with `computed` only for clean sums. This needs Reactor spot checks before it is used.
4. **cite_plan for count questions on test.** Cite every in-window, clean (own, done) instance session, not a score fraction. Dev cannot tune this; it needs test-like synthetic checks.
5. **KU-like multi questions** ("these days", "current plan", "putting in the show"): add a "latest value wins" ordering and keep the newest 3 statements. Agent B's `latest` flag does this too.
6. **Facet guarantee** (borrowed from B): for "X and Y" questions, give each facet's best session a guaranteed slot. This should help sums with 2 named items, and the missing-facet abstention signal.
