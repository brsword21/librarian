# SSU lens A "Struktura": round 1 report

Code: `lenses/ssu/a_struct.py` (round-1 lens; it imports the question grammar and the sentence classifier from `lenses/ssu/a_owner.py`, which was fixed in this round). Scratch: `lenses/ssu/scratch_a/r1_*.py`, plus the test audit `lenses/ssu/scratch_a/r1_audit_nb3t0.txt`.
Runs: `runs/r1-ssu-a/ssu/{generic,a_owner,a_struct}/<variant>/{dev,dev200}`.

**Best variant: `a_struct.py` / `nb3t0`.** On dev: S 93.5, PA 1.000, CF1 0.984, 3.5k chars. On dev200: S 92.5, PA 1.000, CF1 0.955, 3.6k chars. The generic hybrid_rr baseline scores S 76.6 on dev and 73.5 on dev200.

## Variants tried (one line each)
| lens/variant | idea and params |
|---|---|
| generic/hybrid_rr | Baseline: hybrid (all roles) + rerank top 100, 12k budget, cite every pack session. |
| a_owner/owner | Round-0 draft. Sigmoid(rerank) plus additive structure bonuses, decoy units dropped, max 2 sessions, 7k budget, window 1. |
| a_owner/notes | `owner` plus a code-written chain-of-note in the hint. |
| a_owner/owner1 | `owner` with 1 session and a 4.5k budget. |
| a_owner/plain | Same pool and pack as `owner`, no structure. |
| a_struct/s3 | Scores in rerank-logit space (penalties −2 to −3, bonuses +0.15 to +0.5). Max-pool session score + 0.1·second unit. 3 sessions × (4, 2, 1) units, window 1, 6k budget. |
| a_struct/s2 | `s3` with 2 sessions. |
| a_struct/s4w | 4 sessions × (6, 3, 2, 1) units, 9k budget. |
| a_struct/plain3 | Control: the `s3` pack with no structure. |
| a_struct/nb3 | Explicit neighbours, packed with window=0: ±1 around each session's best unit, the preceding assistant chunk for reply units, nothing else. Up to (8, 3, 2) user units per session. |
| a_struct/nb4 | `nb3` with 4 sessions (8, 4, 2, 2) and a 7k budget. |
| a_struct/nb3t | `nb3` plus tense agreement: for a past-tense question, a future or plan unit with no past marker gets −2 and a past-marker unit gets +0.5. |
| a_struct/nb3q | `nb3` plus −1 for user wh-questions to the assistant ("What else should I get for my dog?"). |
| a_struct/nb3_0 | `nb3` with the second-unit session bonus removed (session score = best unit only). |
| **a_struct/nb3t0** | **`nb3t` with the second-unit bonus removed (best).** Also: when top logit > 0, the lexical abstention gates are capped at 0.3. |
| a_struct/plain_nb3 | Control: the `nb3` pack with no structure and no hint. |

Classifier fix applied in round 1 (in `a_owner.py`): 12 of 64 dev gold user units were demoted. Polarity is now judged per occurrence of the question verb, and one affirmed occurrence wins. "I'm thinking of …" anywhere in the clause no longer marks a plan. A possessor that the question itself names ("my favorite artist's debut album") is no longer treated as someone else. After the fix, 0 of 64 dev and 0 of 22 dev200 gold units are flagged as decoys, and the 30 synthetic near-miss cases still pass. The a_owner rows in the table below predate this fix.

## Results (ssu; dev = 64 answerable + 6 abstain, dev200 = 22 + 1)
| lens/variant | split | S | PA | ATR | SR | CF1 | chars | AUC |
|---|---|---|---|---|---|---|---|---|
| generic/hybrid_rr (baseline) | dev | 76.6 | 1.000 | 1.000 | 1.000 | 0.512 | 11934 | 0.924 |
| generic/hybrid_rr (baseline) | dev200 | 73.5 | 1.000 | 1.000 | 1.000 | 0.407 | 11933 | 0.955 |
| a_owner/owner | dev | 91.9 | 1.000 | 1.000 | 1.000 | 0.969 | 6832 | 0.839 |
| a_owner/owner | dev200 | 87.3 | 0.955 | 0.955 | 0.955 | 0.909 | 6553 | 0.909 |
| a_owner/notes | dev | 91.9 | 1.000 | 1.000 | 1.000 | 0.969 | 6846 | 0.839 |
| a_owner/notes | dev200 | 84.3 | 0.909 | 0.909 | 0.955 | 0.909 | 6587 | 0.909 |
| a_owner/owner1 | dev | 88.7 | 0.938 | 0.938 | 0.969 | 0.969 | 4265 | 0.839 |
| a_owner/owner1 | dev200 | 82.2 | 0.864 | 0.864 | 0.909 | 0.909 | 3756 | 0.909 |
| a_owner/plain | dev | 92.4 | 1.000 | 1.000 | 1.000 | 0.984 | 6796 | 0.779 |
| a_owner/plain | dev200 | 85.9 | 0.955 | 0.955 | 0.955 | 0.864 | 6431 | 0.955 |
| a_struct/s3 | dev | 91.8 | 0.984 | 0.984 | 1.000 | 0.984 | 5349 | 0.911 |
| a_struct/s3 | dev200 | 84.9 | 0.909 | 0.909 | 1.000 | 0.909 | 4807 | 0.909 |
| a_struct/s4w | dev | 92.3 | 1.000 | 1.000 | 1.000 | 0.984 | 7138 | 0.911 |
| a_struct/s4w | dev200 | 90.3 | 1.000 | 1.000 | 1.000 | 0.909 | 6383 | 0.909 |
| a_struct/nb3 | dev | 93.5 | 1.000 | 1.000 | 1.000 | 0.984 | 3538 | 0.911 |
| a_struct/nb3 | dev200 | 91.2 | 1.000 | 1.000 | 1.000 | 0.909 | 3623 | 0.909 |
| a_struct/nb4 | dev | 93.5 | 1.000 | 1.000 | 1.000 | 0.984 | 3636 | 0.911 |
| a_struct/nb4 | dev200 | 91.1 | 1.000 | 1.000 | 1.000 | 0.909 | 3771 | 0.909 |
| a_struct/nb3t | dev | 93.5 | 1.000 | 1.000 | 1.000 | 0.984 | 3489 | 0.911 |
| a_struct/nb3t | dev200 | 91.2 | 1.000 | 1.000 | 1.000 | 0.909 | 3608 | 0.909 |
| a_struct/nb3q | dev | 93.5 | 1.000 | 1.000 | 1.000 | 0.984 | 3538 | 0.911 |
| a_struct/nb3q | dev200 | 91.2 | 1.000 | 1.000 | 1.000 | 0.909 | 3622 | 0.909 |
| a_struct/nb3_0 | dev | 93.5 | 1.000 | 1.000 | 1.000 | 0.984 | 3538 | 0.911 |
| a_struct/nb3_0 | dev200 | 91.2 | 1.000 | 1.000 | 1.000 | 0.909 | 3623 | 0.909 |
| **a_struct/nb3t0** | dev | **93.5** | 1.000 | 1.000 | 1.000 | 0.984 | **3489** | 0.911 |
| **a_struct/nb3t0** | dev200 | **92.5** | 1.000 | 1.000 | 1.000 | **0.955** | 3589 | 0.909 |
| a_struct/plain_nb3 | dev | 93.5 | 1.000 | 1.000 | 1.000 | 0.984 | 3303 | 0.909 |
| a_struct/plain_nb3 | dev200 | 91.2 | 1.000 | 1.000 | 1.000 | 0.909 | 3411 | 0.909 |

How to read the table:
- **Pack shape.** Most of the gain over the baseline comes from the pack: cite one session (CF1 0.51 → 0.98) and send about 3.5k characters instead of 12k.
- **Explicit neighbours (`nb*`).** Placing neighbours explicitly instead of using window=1 cuts chars by about 35% and recovers PA. With `s3`, the gold unit was the 5th unit of its own session and fell out of the 4-unit cut.
- **Structure on dev and dev200.** Structure is neutral on dev and dev200 against `plain_nb3` (+1.3 S on dev200 for `nb3t0`), because LongMemEval has almost no planted decoys. Its value is on test (see the audit below), and it no longer costs anything on dev or dev200.
- **Abstention.** The six dev abstain questions limit AUC (dev200 has only one). The logit prior combined by noisy-OR with the lexical gates gives 0.911 on dev, against 0.839 for the round-0 rules alone.
- **Acceptance rule.** `nb3t0` ties `nb3` on dev (dev is saturated: 63 of 64 citations correct), has fewer chars, is simpler (no second-unit term) and wins on dev200, so it is accepted on the tie rule.

## Top failure patterns (with examples)
1. **The second-unit session bonus favours topical sessions** (fixed in `nb3t0`). For dev200 "How long was I in Japan for?" (gold: "I spent two weeks traveling solo … when I was in Japan"), a session about planning a future Japan trip had two units with logits 4.6 and 3.0. Tense agreement moved the gold unit to rank 1 (3.16 vs 2.6), but max + 0.1·second still cited the planning session. With the second-unit term removed, the citation is correct.
2. **The reranker prefers a related item over the asked one** (open). For dev "What is the name of the music streaming service have I been using lately?", "I've been using Netflix …" (logit −0.7) beats "…listening to their songs a lot on Spotify" (−2.8). The structure has no handle on this: both are first-person and affirmed. A domain cue ("music") in the question could add a modifier-agreement feature.
3. **The gold statement is only a presupposition inside a request** (open). For dev200 "What breed is my dog?", the gold is "…a collar that would suit a Golden Retriever like Max?" (logit −8.6). The cited "What else should I get for my dog?" (−5.4) sits in another session. The `nb3q` penalty (−1) for wh-questions to the assistant is too small to flip it, and the gold sentence never contains "dog".
4. **Round-0 classifier over-firing** (fixed). "I'm thinking of visiting my sister Emily in Denver", "I've been thinking about my conversation with Sarah" and "my favorite artist's debut album" were all tagged as decoys and dropped from the pack. That cost 0.09 PA on dev200 for `owner` and `s3`.
5. **Test audit, abstention gate** (fixed in `nb3t0`). For "What AM intermediate frequency did I end up using …", the head word "intermediate" never appears in the history, because the user writes "AM IF". The gate set abstain_p to 0.9 and added "answer INSUFFICIENT_EVIDENCE" to the hint, although the reranker was confident (top logit 2.1) and the right unit ("realigned the AM IF … to 465 kHz", the latest) was ranked first. The gates are now capped at 0.3 when top logit > 0. This changes nothing on dev or dev200, where every gold abstain case has a top logit below 0.

**Test audit** (12 questions, qualitative, `nb3t0`). The decoy notes fire correctly:
- "My friend Helen just adopted a cavoodle puppy named Luna" is flagged as the friend's.
- "My sister Amina's favorite meal is chapati" is flagged as the sister's.
- "My friend Valentina named her sourdough starter Bubbles too" is flagged as someone else's.
- "I measured a 16-ohm speaker … but it did not fit" is flagged as not done.

Name drift is still unresolved: the cat is Fig, Sombra and Bica across sessions, so `computed` = Sombra is a guess. The questions "my neighborhood in Lisbon" and "French tutor" get abstain_p of about 0.8–0.9, and their packs hold no direct statement.

## CORE REQUESTs
1. **Answer-anchored citation** (also requested by lens B). After Reactor answers, cite the pack sessions whose text contains the answer, falling back to `cite_plan`. ssu gold is always exactly one session.
2. **A rerank cache-hit path or a priority queue in the model server.** My first dev sweep took 646 s and dev200 took 1108 s for the baseline, because uncached cross-encoder pairs queue behind the precompute and about 15 parallel sweeps. Lenses that reuse the same pool construction run in about 10 s once cached.
3. **`build_pack(..., neighbors="explicit")`**, or documenting that `window=0` plus explicit neighbour uids is the supported way to get asymmetric context. `nb*` relies on this.
4. **harness.audit: print `debug` fields** (top logit, qparse, decoys) next to each test pack, so gate and parse failures show without a separate script.
5. Carried over from round 0: register the lens module in `sys.modules` before `exec_module` (Python 3.14 dataclass plus `from __future__ import annotations`).

## Ideas for the next round
- **Value voting for name questions with drift** (the Fig/Sombra/Bica cat). Count the sessions where each extracted value appears as the user's own (owner match, affirmed). Prefer a reply to "What's her name?" and break ties by recency. Pass the result in the hint only when one value clearly leads; otherwise list all values with dates and let Reactor see the drift.
- **Calibrate abstention on dev, dev200 and the other types' abstain questions** (only 7 ssu abstain questions exist). Fit ab_bias, ab_temp and gate weights, and maybe use the generic lens's all-roles logit as a second prior (0.955 on dev200).
- **Modifier agreement** ("music" streaming service vs Netflix): a small bonus when the unit contains a domain word of the question's modifiers or context, and a penalty when it names a sibling category.
- **Cite the second session when the margin is small** (`cite_second_gap`, already implemented, untested). The F1 math pays off when p2 > p1/2. Useful on dev200, where 1–2 of 22 citations miss.
- **Merge with lens B.** B's declarative rewrites and session sweep would add recall, and A's owner/polarity/tense features plus decoy notes would add precision. Both lenses already score in logit space.
