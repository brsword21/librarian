# SSU lens B ("Semantyka"): design, round 0

Type: single-session-user (ssu), a fact the user stated about themself. It is about 32% of TEST. Lens file: `lenses/ssu/b_mentions.py`.
Scratch scripts: `lenses/ssu/scratch_b/analyze.py` (where the gold turns sit) and `grep_hist.py` (decoy survey on test, qualitative only).

## What the data says

**Dev / dev200 (gold)**
- The gold is always **one user turn** (64/64 answerable dev questions, 22/22 on dev200). In 2/66 dev cases the gold also includes the assistant's next turn, which restates the fact. Those turns are short: median 285 chars, max 503, so each is one unit. The answer sits in the first 500 chars.
- The fact is usually a **side remark** inside a session about something else ("By the way, I've got three bikes", "...for a Golden Retriever like Max"). Topical session aggregation (sum or NDCG) therefore hurts. **Max-pool** unit scores per session instead.
- 12/64 gold turns follow an assistant turn that ends with "?". The answer can be a short reply, which is why the lens needs `Unit.ctx` plus the preceding assistant chunk in the pack.
- Lexical overlap can be zero ("What breed is my dog?" → "a Golden Retriever like Max"; "What is the name of my cat?"). Dense and the reranker carry these cases.
- Dev abstention swaps the entity: hamster vs cat, violin vs guitar, Korea vs Japan, uncle vs niece, dad vs sister, films vs cameras. The rarest question term is missing from the top hits, or appears only away from the asked slot.
- dev200: several sessions now share a topic (e.g. "sister's" appears in 6 sessions; "Godiva box for my sister" is a near-miss to "sister's birthday: yellow dress").
- dev200 ATR caveat: the LongMemEval `has_answer` flag sometimes marks a sibling turn of the gold session. In the bedside-lamp case two turns of the same session contain the answer and only one is flagged.

**Test (qualitative, no gold, nothing tuned per question)**
Every user-fact question I looked at has **planted decoys** of five kinds, often several per question:

| decoy kind | test examples (paraphrased) |
|---|---|
| other person | "My friend Helen just adopted a puppy named Luna", "a therapy dog named Archie", "My wife tried a new pizza restaurant", "A nurse at work ran the Hippie Chick Half Marathon", "My friend Valentina named her starter Bubbles" |
| negated / not done | "Fox Bros. ... but I haven't tried it yet", "picnic at Red Top Mountain SP, but we didn't camp", "invited me to Stumptown Joggers, but I didn't join", "espresso at Dramática was fine, but I still haven't..." |
| tentative | "I'm thinking of naming my starter Bubbles", "I considered calling my podcast 'The Gain Stage'" |
| superseded | "paperwork still says Luna", "renamed my starter Masa", "my old instructor Miguel" |
| filler drift | the same cat is Miso, Sombra, Bica and Fig in different sessions; the greyhound is Juniper, Juno and Luna |

- "end up", "the last X I mentioned" and "now" mean the latest **clean** own statement wins (starter: Bubbles → Masa; podcast: considered → "finally settled on 'Sidechain Diaries'"; state park: Fort Yargo → Cloudland Canyon).
- Some test questions are probably unanswerable and built only from decoys. "What is my dog's name?" finds only a friend's puppy and a hospital therapy dog. "Last restaurant I mentioned trying" finds only "my wife tried" and "haven't tried it yet".
- Generator artefacts (not used, overfitting risk): planted sentences often carry odd capitals or punctuation (", My friend", "Oh, and A nurse", "goes—My younger son", "counters., so").

## Variants (ranked by expected value on TEST)

All variants share one core pipeline, written against `core.index` and `core.pack` exactly as they are now:

1. **Parse** (regex): head entity and its synonyms (cat ↔ kitten, dog ↔ puppy, partner ↔ husband/wife), owner ("my" vs "my brother's"), recency cue (`end up`, `the last X I mentioned`, `now/current/these days/finally/settled on`), past cue (`previous/used to/before I/originally`), and 1–2 **declarative rewrites** ("Where did I buy my new tennis racket from?" → "I bought my new tennis racket from"; "What did I end up naming my sourdough starter?" → "I named my sourdough starter").
2. **Pool**: `hx.hybrid(query, k=100, roles=["user"], rrf_k=60, pool=300)` for the question and each rewrite (weight 0.7), fused by RRF. Then the **anchor channel**: up to 40 user units that literally contain the head noun.
3. **Rerank**: `hx.rerank(question, pool)` on about 100 pairs. Then a **session sweep** reranks every user unit of the top 3 sessions; this finds short replies that sit next to a high-ranked sibling.
4. **Mention-act features**: each unit is scored as rerank logit − 3·other − 3·negated − 2·tentative − 1..2·old, + 1·reply (the assistant asked "What's her name?"), + 1·update (when the recency cue is on). A named reply cancels "other", so "Bica. ... My son claims she's his cat" stays clean.
5. **Session score**: best unit + 0.15·second unit (max-pooling). Keep sessions within 6 logits of the top, at most `n_sess`.
6. **cite_plan**: the top session. With a recency cue: the **latest** session whose best unit is clean (no decoy tag) and within 3 logits of the top. Without a cue: also cite the runner-up when the margin is under 0.5 (F1 math: citing two sessions pays off when p2 > p1/2).
7. **Pack**: `build_pack(window=0, order="chrono", max_sessions=n_sess)` over the hit units only, plus the assistant chunk before a reply unit (`neighbors(uid,1,0)`), plus the assistant's restatement after the cited unit (`neighbors(uid,0,1)`), plus up to 3 units of the cited session. A pack is about 1–2.5k chars.
8. **Hint** (always on in B1–B3):
   > Answer from the user's own first-person statements about themself. Statements about other people (friend, partner, coworker), plans or options not taken, and things the user did not do do not count.
   - plus, when the recency cue is on: "If the user gave different values at different times, the most recent dated statement wins."
   - plus, when the past cue is on: "The question asks for the earlier value, not the current one."
   - plus, when abstain_p ≥ 0.7: "If no excerpt states it for the user themself, reply INSUFFICIENT_EVIDENCE."
9. **abstain_p** = 1 − σ((best_clean_logit + 1)/2) · (1 − pen). `pen` += 0.35 when the rarest question term (by user-unit df) is absent from the top-3 units, and += 0.4 when every near-top unit that contains the head noun is decoy-tagged. The bias and temperature are uncalibrated; fit them in round 1 on dev + dev200 by AUC.

| # | variant | params that differ | idea | expected metric movement |
|---|---|---|---|---|
| B1 | `mention` | n_sess 4, budget 5000, window 0, recency on cue | precise, tag-aware, recency only when the question asks for it | CF1 ↑ (top-1 citation), chars ↓ (about 2k vs 7.5k for the generic baseline), PA ≈ |
| B3 | `mention_latest` | recency also for any name/brand/what/which question | test filler drift (Miso/Sombra/Bica) plus planted updates mean the latest clean value is the safest guess | test answer accuracy ↑ where names drift. Dev is neutral because there is usually one mention; dev200 is the check |
| B2 | `mention_wide` | n_sess 6, budget 8000, window 1 | recall insurance in case tags or the reranker drop the gold | PA/ATR ↑ slightly, chars ↑, Reactor sees more decoys |
| — | `plain` | no tags, no hint, no rewrites, no anchor | control: is the mention logic worth it? | baseline for the ablation |

Why B1 ranks above B3: B3's "always latest" can cite a later, unflagged decoy (e.g. Fábrica, the true value, comes before Dramática, a negated decoy). B1 picks recency only on an explicit cue. If B3 does not lose on dev200, promote it, because test questions without a cue still have drifting names.

## Expected failure modes
- **Tagger false positives on gold**: 1/25 dev gold turns get a decoy tag. "I realized I want to create a playlist" is tagged tentative and costs −2 logits. Possessive heuristics ("his/her X") can also fire on the user's own sentence about a family member. The penalties are soft and the unit stays in the pool.
- **Unresolvable drift**: if the gold value is not the latest clean one (e.g. the cat question), we answer wrong with a confident cite. Nothing local fixes this; B2 at least lets Reactor see all values.
- **Head extraction misses** on odd phrasings ("What was my last name before I changed it?" → head "changed"). These only affect tags and the anchor channel, not the hybrid/rerank core.
- **Reply units**: the answer is a bare noun ("Bica.") and the reranker may score it low. The sweep, the reply bonus and `prev_for_reply` cover this.
- **Abstention**: ms-marco logits for "my cat Luna" against "What is the name of my hamster?" can still be moderately high. The coverage penalty catches the swapped entity unless "hamster" appears elsewhere in the history (it does in dev: df = 1).

## Smoke results (6 questions each, `--tag r0smoke_b`; not an evaluation)
- dev: S 83.8, PA 0.83, CF1 1.0, chars 1188. The one miss had a gold assistant turn, now covered by `next_for_cited`.
- dev200: S 94.3, PA 1.0, CF1 1.0, chars 2545, after adding the session sweep and up to 3 units of the cited session.

## CORE REQUESTs
1. **Answer-anchored citation** (largest expected gain for ssu, ssa and ku): after Reactor answers, cite the pack sessions whose text contains the answer (normalised or fuzzy), falling back to `cite_plan`. ssu gold is always exactly one session, and the pack legitimately holds decoy sessions.
2. **ATR on dev200/dev**: `has_answer` sometimes flags a sibling turn. Report PA also as "AC within a gold session" so lenses that include the other answer-bearing turn are not punished (bedside-lamp case).
3. Optional `render_ctx=True` in `build_pack`, which prints `Unit.ctx` as "assistant: …" before a reply unit, so lenses do not need the extra neighbour chunk. Not blocking; I add `neighbors(uid,1,0)` myself.

## Next round
- Run all 4 variants on dev (70 ssu) and dev200 (23). Fit `ab_bias`, `ab_temp`, `ab_cov` and `ab_decoy` by AUC. Grid `pen_*` ∈ {0, 1.5, 3} and `drop` ∈ {3, 6, 9}.
- Audit test packs (`harness.audit`) for the five decoy kinds: check that tags fire and that `cite_plan` lands on a clean statement.
- Try the reranker on the declarative rewrite as a second rerank query (max of the two logits).
