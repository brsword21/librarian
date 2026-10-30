# SSU lens B "Semantyka": round 1 report

Lens: `lenses/ssu/b_sem.py`. **Best variant: `best_rec`.** On metrics it ties `sem_cu5r`. It adds the own-statement hint, light decoy tags and a recency cite, which are meant to help on test.
Round-0 draft (`b_mentions.py`) was swept for reference only. Scratch: `scratch_b/dump.py` (dumps features), `exp.py` (offline ranking grid), `abst.py` (abstention features), `audit_best_rec.txt`.

## Key findings
1. **The assistant echo is the strongest session signal.** Rerank over ALL roles and max-pool per session: top-1 session P@1 is 0.984 on dev and 0.955 on dev200. A user-only pool gives only 0.969 and 0.864 (offline, `exp.py`). Penalising assistant units by 1 logit costs 4 S on dev200 (`sem_asst1`).
2. **The gold USER unit often ranks below its own session's assistant echo.** Examples: yoga is at rank 13, the dog breed at 11-15. So the pack must take the best *user* units of the cited session, and those must be reranked. The session sweep reranks every user unit of the top 3 sessions, and up to 5 user units of the cited session are packed. This took PA from 0.969 to 1.0.
3. **CF1 is the big lever.** Cite only the top session (`cite_plan=[top]`), not every passage: CF1 rises from 0.51/0.41 to 0.98/0.96, worth about +15 S. Citing the runner-up when the margin is under 1 logit loses on dev200.
4. **The preceding assistant chunk is needed only for short replies.** Adding it for every unit costs about 1.7k chars. With the conditional (`before="reply"`: chunk 0, under 200 chars, ctx ends with "?") the pack is about 3.2k chars and PA does not drop.
5. **Pool depth and fusion are flat on dev and dev200.** The cached generic pool (hybrid all-roles top-100, rerank) is enough, so sweeps are about 100% cache hits. Adding z-scored dense or BM25 to the logit moves P@1 by at most 1 question either way (`exp.py`), so it was not adopted.

## Variants (one line each)
| variant | idea / params |
|---|---|
| sem_nosweep | all-role hybrid top-100 → rerank → max-pool sessions; cite top-1; pack the best user unit of 6 sessions, budget 6000 |
| sem | + session sweep: rerank every user unit of the top 3 sessions |
| sem_cu5 / sem_cu8 | + 5 / 8 user units of the cited session, no logit cut |
| sem_cu5r | sem_cu5 + preceding assistant chunk only for short replies |
| sem_cu5r0 | sem_cu5r without the cited unit's next chunk (the gold is sometimes the assistant restatement) |
| sem_tags | sem_cu5r + b_mentions decoy tags (other / negated / tentative) as logit penalties |
| sem_abp / sem_abp2 | + abstention from prefix-df: rarest question term absent from user turns → +0.6; absent from the top-3 user units → +0.3 (abp2: other temperature) |
| best | sem_abp + own-statement hint (~150 chars) |
| **best_rec** | best + recency ("end up / now / last … I mentioned"): cite the latest session within 2 logits of the top, hint "most recent wins" |
| sem_m1 | sem_cu5r + cite the runner-up when the margin is under 1 logit |
| sem_asst1 | sem_cu5r + assistant units −1 logit in session scoring |
| (draft) b_mentions mention / plain / … | user-only pool + tags; dev S 92.8 / 92.9, PA 0.984 |

## Results (dev: 70 q / 64 answerable; dev200: 23 q / 22 answerable)
| variant | split | S | PA | ATR | SR | CF1 | chars | AUC |
|---|---|---|---|---|---|---|---|---|
| generic hybrid_rr (baseline) | dev | 76.6 | 1.000 | 1.000 | 1.000 | 0.512 | 11934 | 0.924 |
| generic hybrid_rr (baseline) | dev200 | 73.5 | 1.000 | 1.000 | 1.000 | 0.407 | 11933 | 0.955 |
| sem_nosweep | dev | 91.6 | 0.969 | 0.969 | 1.000 | 0.984 | 3041 | 0.885 |
| sem_nosweep | dev200 | 89.7 | 0.955 | 0.955 | 1.000 | 0.955 | 3352 | 0.955 |
| sem | dev | 91.6 | 0.969 | 0.969 | 1.000 | 0.984 | 3036 | 0.883 |
| sem_cu5 | dev | 93.1 | 1.000 | 1.000 | 1.000 | 0.984 | 4783 | 0.888 |
| sem_cu5 | dev200 | 92.1 | 1.000 | 1.000 | 1.000 | 0.955 | 5015 | 0.955 |
| sem_cu8 | dev | 92.9 | 1.000 | 1.000 | 1.000 | 0.984 | 5162 | 0.888 |
| sem_cu5r | dev | 93.6 | 1.000 | 1.000 | 1.000 | 0.984 | 3155 | 0.885 |
| sem_cu5r | dev200 | 92.6 | 1.000 | 1.000 | 1.000 | 0.955 | 3279 | 0.955 |
| sem_cu5r0 | dev | 91.7 | 0.969 | 0.984 | 1.000 | 0.984 | 2522 | 0.885 |
| sem_tags | dev | 93.6 | 1.000 | 1.000 | 1.000 | 0.984 | 3152 | 0.888 |
| sem_tags | dev200 | 92.6 | 1.000 | 1.000 | 1.000 | 0.955 | 3277 | 0.955 |
| sem_abp | dev | 93.6 | 1.000 | 1.000 | 1.000 | 0.984 | 3152 | 0.901 |
| sem_abp | dev200 | 92.6 | 1.000 | 1.000 | 1.000 | 0.955 | 3277 | 0.955 |
| sem_m1 | dev | 93.6 | 1.000 | 1.000 | 1.000 | 0.984 | 3165 | 0.888 |
| sem_m1 | dev200 | 92.2 | 1.000 | 1.000 | 1.000 | 0.939 | 3328 | 0.955 |
| sem_asst1 | dev | 93.6 | 1.000 | 1.000 | 1.000 | 0.984 | 3161 | 0.888 |
| sem_asst1 | dev200 | 88.4 | 0.955 | 0.955 | 1.000 | 0.909 | 3126 | 0.955 |
| best | dev | 93.5 | 1.000 | 1.000 | 1.000 | 0.984 | 3298 | 0.901 |
| best | dev200 | 92.6 | 1.000 | 1.000 | 1.000 | 0.955 | 3423 | 0.955 |
| **best_rec** | dev | **93.5** | 1.000 | 1.000 | 1.000 | 0.984 | 3302 | 0.901 |
| **best_rec** | dev200 | **92.6** | 1.000 | 1.000 | 1.000 | 0.955 | 3427 | 0.955 |

Dev and dev200 are close to the ceiling. With PA=1 and CF1=1 at about 3k chars, S is about 94. The remaining gap is one wrong top-1 cite per split. AUC on dev200 rests on a single unanswerable question, so it carries little information.

## Top failure patterns
1. **Plan beats past (tense).** dev200 "How long was I in Japan for?": the top session is "I'm planning a trip to Japan … booked with Sakura Travel" (logit 6.8). The gold "when I was in Japan a few months ago … spent two weeks" scores 2.1. It is in the pack (PA=1), but the cite is wrong. The draft tagger catches "planning to" but not "planning a trip to".
2. **Wrong service, same slot.** dev "music streaming service I've been using lately": Netflix sessions ("I've been using Netflix … lately", −0.7) outrank the Spotify mention (−3.4). Media type is a semantic slot the cross-encoder ignores.
3. **Entity swap with the entity present.** dev "collecting vintage films": "film" appears in the vintage-camera session, so the coverage check passes and the logit is 3.4, giving abstain_p 0.15. dev/dev200 "Korea": Korea is mentioned but the user never says they were there, giving 0.6 to 0.9. Answerable questions with low logits get a high abstain_p, e.g. "painting of a sunset worth" (−5.8) and "What breed is my dog?" (−4.0, the answer is "a Golden Retriever like Max").
4. **Test (audit, qualitative).** Packs carry all the drifting values: cat Sombra, Fig, Bica; starter Bubbles (thinking), Bubbles, Herman (saw), Masa (renamed, latest). They also carry possessor decoys ("My sister Amina's favorite color is teal", "My brother Brian's favorite color is blue"). The hint plus "most recent wins" covers the update questions. Possessor and slot decoys rely on Reactor reading the hint. Lens A's owner classifier is the right tool for those.

## CORE REQUESTs
1. **Answer-anchored citation** (pipeline): after Reactor answers, keep the cited passages whose text contains the answer, falling back to cite_plan. ssu gold is always one session and the pack holds decoys on purpose.
2. **Default pool = all-role hybrid top-100 for every lens.** It is fully cached on dev, dev200 and test. Lenses that add user-only pools or new rerank queries pay about 40 s per question while the server is contended. A shared, precomputed "rerank every user unit of the top-3 sessions" cache would make the session sweep free.
3. **`build_pack(before_if_reply=True)`**: render the previous assistant chunk only when a unit is a short reply to a question. The lens does this by hand now. It saved about 1.7k chars per question with no PA loss.
4. **Model-server contention**: `/rerank` waits behind long `/embed` batches under one LOCK. A separate lock per model, or a priority for small rerank batches, would speed every agent's sweeps.

## Ideas for the next round
- Merge with lens A: B's retrieval and pack (all-role max-pool, user sweep, cu5r pack, top-1 cite) plus A's owner/polarity classifier on the user units as the tagger. A's classifier is more complete than the b_mentions tags. Tags are neutral on dev/dev200, so they must be judged on the test audit.
- Tense feature: the question is past ("was I / did I") and the unit is a plan ("planning a trip", "going to", "next month"), so apply a soft penalty. This fixes the Japan cite.
- Abstention: when the question's key noun appears in the top units only in a different slot ("vintage film cameras" vs "vintage films"), compare noun phrases, not prefixes. Calibrate on dev + dev200 together, since there are only 7 positives.
- Recency on test: when the cue is present, also force the latest head-term session into the pack (`n_sess` +2) so the newest value can never be cut by the budget.
- Chars: drop `other_units` from sessions more than 8 logits below the top (about −0.3k chars). This is only worth doing if test audits show those sessions never matter.
