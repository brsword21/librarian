# SSU lens A "Struktura": design (round 0)

Code: `lenses/ssu/a_owner.py`. Self-test: `PYTHONPATH=. .venv/bin/python lenses/ssu/a_owner.py`.
Scratch analysis: `lenses/ssu/scratch_a/s01..s10`.

## What makes ssu hard (data findings)

**Dev (LongMemEval).** The fact sits in one user turn, often as an aside: 42% of gold user turns carry "By the way / Also, / speaking of", against 11% of all user turns (27/64; dev200 6/22 vs 11%). Retrieval is easy at 48 sessions. In the 6 unanswerable questions the entity is swapped (hamster vs cat, uncle vs niece, violin vs guitar, Korea vs Japan, dad vs sister, films vs cameras). In 3 of the 6 the key entity or relation never appears in the history.

**Test (qualitative only).** The near-misses are planted sentences, usually prefixed "By the way, My ..." / "Oh, and My ..." / "Also, ...", sometimes with insertion artifacts like ".,". They fall into four shapes:

1. **Possessor swap** (the dominant shape). Examples: "My friend Ines booked her birthday dinner at ...", "My neighbor's move date is ...", "My sister Amina's favorite color is ...", "My coworker says he calls his skateboard ...", "My brother's neighbor has a dog named ...", "My friend Helen's Tuesday morning watercolour class is taught by ...", "My neighbor has one grandchild". Each of these contains every word of the question, so dense retrieval and the cross-encoder rank them at the top.
2. **Negation, plan or rejected trial.** Examples: "..., but I haven't tried it yet", "..., but we didn't camp overnight", "I'm thinking about kegging ...", "I'm thinking of naming ...", "I briefly tried a 47k resistor ..., but ...", "it did not fit".
3. **Update chains** for "end up / now / last ... I mentioned". Examples: "I returned the Weber ... and bought a Big Green Egg instead", "I've renamed my starter Masa", "My old instructor Miguel still ...", "used to be purple ..., but now".
4. **Slot conflict.** Same object, different slot: "Wednesday evening class" vs "Saturday morning class", "school concert" vs "school play".

Filler sessions also invent inconsistent names for the same pet or child. One test history names its cat 8 different ways. When the question has no recency cue, rules cannot settle these; owner, reply, aside and frequency only narrow the field.

The answer can be a short reply to the assistant ("What's her name?" → "X. She's a tiny black cat"), so `Unit.ctx` matters.

## Variants (ranked by expected value on TEST)

### 1. `owner` (rank 1): owner-aware structural rerank, decoys dropped, short hint
- **Pool:** `hx.hybrid(q, k=60, roles=["user"])`, plus `hx.bm25(q + head synonyms + modifiers, k=40, roles=["user"])`, plus a lexical scan of every user unit that contains the head noun or a synonym (cap 80). Cut at 140, then `hx.rerank(q, pool)`, then `sigmoid(logit)`.
- **Question grammar** (regex, no POS tagger): head noun, modifiers, possessor chain (`my brother's new dog` → chain [brother]), attribute (name / brand / ...), question verbs (stemmed), recency cue (end up / now / current / these days / last ... I mentioned), past cue (previous / used to / before I).
- **Sentence classifier**, run on each unit's best sentence:
  - **Owner** = possessor of the head's noun phrase (walk back over at most 3 modifiers, then read the determiner: my/our, X's, his/their), else the clause subject (I/we vs "My wife ...", "A nurse at work ...", "Toshi used ..."). Owner is `match` when it equals the question's chain and `mismatch` otherwise. Slot conflict, a compound relation ("running partner" vs "partner"), and "saw/heard of a X" also count as `mismatch`.
  - **Polarity:** `neg` (the question verb is negated, e.g. "haven't tried"), `plan` (thinking about / planning / rejected trial), `stale` (used to / old / still says), `new` (renamed / instead / now), or `aff`.
- **Score** = `(rr + 0.15·owner_match + 0.10·head + 0.04·mods + 0.04·verb + 0.04·aside + 0.08·reply + 0.05·name_value) × (0.25 if mismatch) × (0.35 neg | 0.45 plan | 0.6 stale)`.
- **Recency:** when the question has a recency cue, the primary pick is the latest valid candidate whose score is at least 0.55·best. The previous valid candidate goes into the pack as context.
- **Pack:** primary session first, then the rest by score. Units that hit the head but are invalid (decoys) are dropped. `build_pack(budget=7000, window=1, order="chrono", max_sessions=2)`. `cite_plan = [primary]`.
- **Hint** (~230 chars): "Answer from what the user said about their own {anchor}. Mentions of other people's {head} (friends, relatives, neighbors, coworkers), plans, or things the user did not actually do are not the answer." With a recency cue, add "the most recent dated statement wins". Add up to 2 decoy notes ("the 2023-05-04 line '...' is about the user's friend, not the user's own").
- **abstain_p**, in order:
  - head noun (with synonyms) is in no text at all: 0.9
  - head noun is in no user turn: 0.75
  - the question's relation (uncle, dad) is in no user turn: 0.85
  - head plus modifiers never occur together in a user unit: 0.3
  - the top candidate is a decoy: 0.6
  - weak reranker score: 0.35
  - otherwise: 0.05
- **Should move:** SR / CF1@1 and PA on test-like near-misses, plus abstention AUC. Expect neutral to slightly positive on dev.
- **Failure modes:**
  - The proper-name subject rule can misfire on brands and pets (now limited to human-agent verbs).
  - A reply-fragment sentence ("Bica.") inherits no owner.
  - A head noun missing from the gold sentence ("Golden Retriever like Max" for "my dog's breed") makes the structure neutral, so retrieval has to carry it.
  - For inconsistent filler names the result is still a multi-candidate pick.

### 2. `notes` (rank 2): `owner` plus a code-written chain-of-note
Same ranking. The hint adds "Candidate statements (oldest first): DATE: "sentence" [only a plan | about the user's friend | old value] | ...", at most 4, one per session. This gives Reactor the timeline and the labels for "end up / last ... I mentioned" questions, and arithmetic chains ("put in 18k ... increased by 15k"). It costs ~300 more hint characters. If a label is wrong, Reactor may follow it. **Should move:** PA on recency and update questions. On dev it should match `owner`.

### 3. `owner1` (rank 3): one-session precision pack
`max_sessions=1, budget=4500`. CF1 is unchanged in the harness (cite_plan is already 1), but chars drop. In the real pipeline Reactor can only cite one passage, so evidence precision is 1 whenever the pick is right. PA drops when the primary pick is wrong. Prefer it if dev and dev200 PA stay within ~1 point of `owner`.

### 4. `plain` (control)
Same pool and cross-encoder, no structure, no hint. It measures what the rules add.

## Offline evidence so far (no core.index; lexical-overlap stand-in for the reranker)
- Dev ssu (64 answerable): gold session R@1 0.906 → **0.953** with structure, R@3 0.938 → **0.984**. Dev200 (22): R@1 0.727 → 0.727, R@3 0.864 → **0.909**.
- None of the 25 sampled dev gold sentences is demoted (owner `mismatch` or polarity `neg`/`plan`). All 30 synthetic near-miss shapes are classified correctly.
- abstain_p on the 6 dev unanswerable questions: [0.9, 0.05, 0.85, 0.45, 0.45, 0.45]. On the 64 answerable: mean 0.097, none ≥ 0.5.
- Stub smoke test of `build()` on 40 dev questions: cite@1 hit 39 (`owner`) vs 36 (`plain`).
- Test audit (qualitative): decoys are demoted for "Wednesday evening class", "briefly tried 47k AGC resistor", "12-volt lamp too dim", "saw a starter named Herman", "thinking of naming". "Ended up fitting a 6.3-volt lamp", "renamed ... Masa" and "changed ... from 150 to 180 ohms" rise to the top.

## CORE REQUESTs
1. **Harness loader:** register the lens module in `sys.modules` before `exec_module`. Otherwise `@dataclass` plus `from __future__ import annotations` crashes on Python 3.14; I removed the future import as a workaround.
2. **`hx.user_sentences()` cache** (uid, sentence index, sentence, ctx): the lexical scan and the classifier re-split text on every call. Cheap now, but it would help sweeps over 200 sessions.
3. **Answer-aware citation trim** (pipeline level, needs a rules check): after Reactor answers, keep only the cited passages whose text contains the answer string. If none match, keep Reactor's citations. Gold ssu evidence is exactly one session, so this lifts CF1 whenever the pack has 2+ sessions.
4. **`build_pack` contract:** confirm that sessions are taken in the first-appearance order of `ranked_uids` and that `max_sessions` caps that order. The lens relies on this to put the primary session first and to drop decoys.

## Ideas for round 1
- Tune the penalty and bonus weights and `rel_thr` on dev plus dev200 only, via `harness.sweep`.
- Value voting for name questions: count the sessions where each extracted name appears with a SELF owner, and break ties by reply / aside / recency. Pass it to the hint only when one value clearly leads.
- "Last ... I mentioned" should search over all valid sessions, not just the top-scored pool. The lexical scan already supplies them, so lower `rel_thr` for those questions.
- Combine the abstention gate with lens B's reranker threshold.
