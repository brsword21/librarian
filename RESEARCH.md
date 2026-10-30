# Research digest (LongMemEval and long-term-memory QA), for lens agents

[V] = verified in the source, [I] = inference.

## LongMemEval paper (arXiv 2410.10813)
- Dense beats BM25 [V]. Session R@5/R@10: BM25 .634/.710, Contriever .723/.823, Stella-1.5B .720/.794. Round (single user+assistant exchange) R@5/R@10: BM25 .472/.538, Contriever .589/.747, Stella .660/.784.
- Granularity [V]: the best QA used round-level values, top-10, with fact-augmented keys (.720 GPT-4o on M). Facts as values hurt, except on multi-session.
- Key expansion with LLM-extracted user facts [V]: +9.4% recall. We cannot use an external LLM; regex/heuristic key expansion is allowed.
- Time-aware query expansion [V] (question → date range → filter): temporal recall +6.8% (session) / +11.3% (round); round R@10 .550 → .722. A weak LLM invented ranges and hurt. Rule-based ranges are safer [I].
- Reading [V]: retrieved items sorted by timestamp; Chain-of-Note ("extract notes, then answer") + JSON format gives up to +10 points. Small readers degrade beyond ~3k retrieved tokens, so precision first [I].

## Systems with published LongMemEval scores (gpt-4o reader unless noted)
- **Emergence simple RAG, 82.4%** [V]: turn matching → cross-encoder rerank → session score = NDCG of its turn hits → read sessions with chain of thought. SSA 100, TR 81.2, MS 73.7, KU 79.5. Local-feasible.
- **Redis, 83.4%** [V]: topic-shift chunks, score 0.7·cosine + 0.3·BM25, expand with neighbouring chunks, no reranker. LLM facts → 86.5% and assistant recall 72% → 100%.
- **Chronos (PwC), 92.6%** [V]: "event calendar" of ISO start/end spans + raw-turn index; dense top-100 → rerank top-15 → ±1 neighbour turn. KU: retrieve every timestamped mention, take the latest. Ablation: no calendar −34.5 pts, no date filter −14.7. Abstention failures = model assuming facts.
- **Hindsight, 83.6–91.4%** [V]: semantic + BM25 + graph + temporal channels fused with RRF (k=60) → cross-encoder ms-marco-MiniLM-L-6-v2. Rule-based date parsers turn the question into a range; facts scored by distance to the range midpoint.
- **LiCoMemory, 73.8%** [V]: BGE-M3, k=15, score = semantic × exp(−(Δt / median Δt)^0.1). Without the time decay, KU dropped 80.8 → 51.9.
- **UltraMem (120-q slice)** [V]: resolve the event's own date, not the session date; do date arithmetic and counting in code; code-computed "latest value" took KU 60% → 80%. More context made the model abstain on questions it had answered before.
- **Zep, Mastra, Supermemory, Mem0**: LLM-extracted facts and observations, not local. Ideas that carry over: valid-from/valid-to on facts, observation date vs referenced date, "say I don't know when context is insufficient".

## Per-type playbook [I]
- **Knowledge update**: retrieve every mention of the attribute, order chronologically with dates, tell the reader the latest dated value wins; cite old and new (gold evidence for KU is always exactly 2 sessions).
- **Temporal**: regex calendar of dated events (ISO, "June 27, 2023", "23 April 2023", relative expressions vs the session date); match by head noun + possessor; compute day gaps in Python and pass them as a hint.
- **Multi-session counting**: top 10–15 rounds ±1 neighbour, dedupe and diversify by session; Chain-of-Note-style instruction "list each instance with its session, then count".
- **Single-session-assistant**: index assistant turns verbatim, chunked; keep the user turn before as context.
- **Abstention**: "not mentioned" when no exact entity match clears a reranker threshold. In dev, a question word absent from the whole history catches 13/30 unanswerable questions but also 14.5% of answerable ones, so treat it as a soft signal (hint to Reactor), not a hard decision.

## Test-set observations (no gold; from reading the 146 test questions and histories)
- Style mix (heuristic): user facts ~47, "how many days apart/after" ~35, "what X did you recommend" ~25, counting/sums ~24, "now / current / right now" updates ~15.
- Temporal: explicit dates in text: ISO 110, "June 27, 2023" 148, "23 April 2023" 42; some histories have no ISO date at all. Decoys differ by person ("My coworker took his driver's written test on June 29, 2023"), year ("Our anniversary was June 21, 2022"), event (school concert vs school play) or a contrast cue ("not the orthodontist appointment"). Sometimes the true date is only in an assistant turn.
- Answers can be short replies to the assistant's question ("What's her name?" → "Sombra. She's a tiny black cat…") — hence `Unit.ctx`.
- KU in test is often paraphrased: "My ceramics class instructor is Miguel Silva" (April) → "My old instructor Miguel still comments…" (July); the new value may use different words ("teacher").
- Several near-identical questions per history (e.g. 8 "What X did I end up using in my National R-77?"): many sessions about the same object act as near-misses; "end up" = the final decision.
- Dev type-routing by simple rules is only 61% accurate (KU 19%: dev KU questions rarely say "now"); lenses should also react to what the evidence shows (several dated values for one attribute → latest-wins logic).
