# Librarian: solution write-up

**Reactive AI Memory Retrieval Challenge**, START Warsaw x Poland Tech Week Hackathon (Oct 30–31, 2026). Team Ptysie.

## TL;DR

- **Approach.** We treat long-term memory as a *librarian's* job: retrieval, ordering, dating and arithmetic are done
  by code; reading and answering is done by Reactor. A question is routed to one of five type-specific "lenses". The
  lens builds a small evidence pack: ~3 dated sessions out of 200 (~3.2k characters out of ~1.6M), plus code-computed
  notes such as day gaps. Reactor answers from that pack and cites it.
- **Harness.** An offline harness scores any retrieval variant against gold in minutes, without calling Reactor. Its
  metrics are pack answerability, citation F1 and cost. We calibrated it against real Reactor answers.
- **Development.** 10 local agents (2 per question type) plus an integrator iterated in 5 rounds under a fixed
  acceptance rule.
- **Score.** Offline S went from 42.9 (naive keyword baseline) to 87.1 on dev and 87.0 on dev200, a test-scale split.
- **Submission.** 146/146 test questions were answered by Reactor, with 13 abstentions, a citation on every answer
  and 0 format errors. No hosted LLM is used anywhere.

## 1. The problem and our constraints

Each test question comes with one user's chat history: 200 sessions spread over months, about 1.6M characters. The
system must:
- find the sessions that answer the question;
- get the answer **from Reactor** (the organisers' model, the only allowed answerer);
- cite the supporting session ids;
- abstain when the history does not contain the answer.

Questions fall into five types:

| Type | Short name | Asks for |
|---|---|---|
| single-session user | ssu | a fact the user stated once |
| single-session assistant | ssa | what the assistant recommended |
| multi-session | multi | a count or sum across sessions |
| knowledge update | ku | the latest value of something that changed |
| temporal reasoning | temporal | dates and gaps |

The test set gives no type label, and it is adversarial:
- decoys differ only by person, year, event or negation, e.g. "My coworker took his test on…" or "not the
  orthodontist appointment";
- knowledge updates are paraphrased;
- dates appear in at least three formats.

Constraints that shaped the design:
- **No external models in the pipeline.** Only local models run: `bge-small-en-v1.5` embeddings and the
  `ms-marco-MiniLM-L-6-v2` cross-encoder. Everything else is rules and code.
- **One Reactor, slow.** A real answer takes ~90 s (median 89 s over 153 test calls). The whole night allowed fewer
  than 200 Reactor calls, so all model selection had to happen offline.
- **Answers are never edited.** Our code chooses citations only from sessions that support Reactor's answer.

## 2. Pipeline

```
question ─► router ─► type lens ─► evidence pack ─► Reactor ─► finalize ─► predictions.jsonl
```

**Router** (`core/router.py`, `lenses/pipeline.py`).
- A text router assigns one of the five routes.
- In-lens hand-offs then correct it from the evidence:
  - a role detector sends "what did *you* say" questions to ssa;
  - a knowledge-update gate fires when the two best own-attribute sessions state different values.
- Route accuracy against gold type on dev is 0.68 from the text alone and 0.78 after hand-offs.
- Misroutes were designed to be cheap: an ambiguous count stays on multi, because multi→ku cost ~70 S per question.

**Shared retrieval core** (`core/`).
- Turns are split into units: a sentence ±1, with the previous turn's last sentence as context, because answers are
  often replies such as "What's her name?" → "Sombra.".
- Units are indexed with BM25 and dense embeddings, fused with RRF and reranked by the cross-encoder.
- Every embedding and rerank score is cached by text hash, so dev, dev200 and test share work.

**Five lenses** (`lenses/<type>/`, chosen per route in `configs/best.json`).

| Route | Lens | What it does |
|---|---|---|
| ssu | `ssu/merged_r4` | precision first: entity-matched sessions, short packs, recency guard for "the last X I mentioned" |
| ssa | `ssa/a_recsent` | assistant turns verbatim, with the recommended sentence quoted |
| multi | `multi/merged_r4` | wide recall over instance sentences, diversified by session; the reader is asked to list instances, then count |
| ku | `ku/merged_r4` | a timeline of every dated mention of the attribute; the pack carries the old/new pair, newest last |
| temporal | `temporal/a_r3_gap` | a regex calendar of dated events (ISO, "June 27, 2023", "23 April 2023", dates relative to the session); the event pair is matched by head noun and owner; **the day gap is computed in Python** and given to Reactor as a note |

**Evidence pack** (`core/pack.py`).
- Passages are ordered chronologically, each with its session date.
- The pack carries the code's margin notes.
- It ends with a fixed answer-format line that asks for the answer followed by its `[E#]` passage labels.
- The pack also stores the sessions our code expects to be cited, `cite_plan`.

**Reactor queue** (`reactorq/queue.py`).
- One question at a time, one Reactor history per dataset history.
- Resumable, with answers cached by pack hash.
- Retries stay in the same Reactor history, with a 600 s timeout and recovery of late replies.

**Finalize** (`reactorq/finalize.py`).
- Converts replies with the organisers' `predictions.py` and validates with their `score.validate`.
- Then adds citations only by rules that keep support. A session is added when:
  - it contains Reactor's whole answer phrase (only for answers with at least 2 content words, because one-word
    answers hit decoys); or
  - it holds the value our code computed and Reactor repeated; or
  - it is the superseded statement of a knowledge update Reactor cited from only one side.
- Reactor's own citations are never removed, and answers are never touched.

## 3. Harness: how we choose without calling Reactor

**Metric.**

`S = 100 · mean(0.65·PA + 0.30·CF1 − 0.05·chars/16000)`

- **PA (pack answerable).**
  - ssu and ssa: the gold answer turn is in the pack *and* the gold answer string occurs in the pack text.
  - ku: additionally, the newest gold session is in the pack.
  - multi: all gold sessions are in the pack.
  - temporal: all gold sessions are in the pack and the code's day count matches gold.
- **CF1** is citation F1 of `cite_plan` against gold sessions. A pessimistic variant, `Sall`, assumes Reactor cites
  every passage we send.
- **chars** is a cost term, so a variant that adds context has to earn it.
- Abstention is tracked separately as AUC of the pack's own absence signal.

**Splits.**
- **dev:** 526 questions from LongMemEval.
- **dev200:** we built it to match test scale: 125 dev-large questions (25 per type, including unanswerable ones), each
  with its gold sessions plus 196 random sessions from its own history, i.e. exactly 200 sessions like test. A variant
  that only wins on the small dev histories does not survive here.
- **Gold answer turns** come from the LongMemEval `has_answer` flags (908 turns, 496/496 answerable dev questions
  matched).

**Tooling** (`harness/`).
- `sweep` runs a lens over a split and appends to `runs/leaderboard.csv`, which holds 1,784 runs with git hash.
- `failures` prints the worst questions with what was missed and what was taken instead.
- `audit` builds test packs, which have no gold, and flags suspicious ones. Examples: no unique event date, a
  person/year/negation decoy, a gap ≤ 0 or > 365 days, a ku pack with fewer than 2 mentions, an ssa pack whose top
  passage is not an assistant turn.
- `audit --diff` lists exactly which test packs a change touches, and so which questions must be re-asked.

**Acceptance rule.** A variant replaces the incumbent only with ≥ +2 S on dev and no loss on dev200. On a tie, the
shorter pack wins. After round 3, a narrower rule applied for test-visible defect fixes:
- they repair a visible defect on a test pack;
- they change few packs;
- they cause no regression on routed dev, dev200 or `Sall`.

**Calibration against the real Reactor** (`runs/reactor/`). We asked Reactor 30 dev questions using our packs.
- 20 answers matched the scorer exactly, including all 5 abstentions; 6 were correct in substance; 4 were wrong
  (2 false abstentions and 2 dropped connections).
- With labelled packs, Reactor's own citation F1 was 0.85 on answered questions.
- The calibration exposed one real bug: an early "answer only" instruction made Reactor drop its `[E#]` labels, so
  citations vanished. The answer-format line was fixed before the test run.

**Agent rounds.** Each question type had two local agents, one per approach:
- **A, "structure":** rules, dates, timelines, entities, computed values.
- **B, "semantics":** fusion weights, granularity, rerank depth, neighbours, diversity, time decay.

Each agent looped: sweep → 20 worst questions → one fix per hypothesis → re-sweep. An integrator merged the winners per
route after every round, ran the routed regression on dev and dev200, audited test packs and wrote the next brief.
Agents had no access to Reactor or any hosted model, and measured only through the harness. The integrator's reports
are in `runs/SYNTHESIS_r1..r4.md`.

## 4. Results

| System | dev S | dev200 S | Note |
|---|---|---|---|
| naive keyword baseline (our reimplementation of the kit's, no router) | 42.9 | | |
| generic hybrid retrieval (BM25 + dense + rerank, no router) | 73.4 | | 80-question dev sample |
| round 1, routed | 80.4 | 79.9 | per-type lenses + router |
| v1 (round 2) | 86.0 | 84.9 | evidence hand-offs, ku timeline, temporal calendar |
| v2 (round 3) | 86.9 | 87.0 | recall fixes found by auditing test packs |
| **v3 (round 4, submitted)** | **87.1** | **87.0** | gated test-defect fixes; `Sall` 85.4 / 85.3 |

v3 per gold type on dev:

| Type | Routed | Lens alone on its own type |
|---|---|---|
| ssu | 87.4 | 93.4 |
| ssa | 93.0 | 93.6 |
| multi | 85.8 | 87.8 |
| ku | 91.5 | 93.4 |
| temporal | 80.3 | 81.3 |

The gap between the columns is router error.

**Test run.** We sent 146 questions to Reactor in one pass per history. The v1 packs were swapped for v2 and then v3
mid-run as the system improved. 7 questions whose pack changed after they were answered were re-asked, and 3 that
failed on a network drop were retried.

Final result:
- 146/146 answered by Reactor;
- 13 abstentions;
- 1.65 citations per answer on average;
- 0 format errors.

`finalize` rebuilds `submission/predictions.jsonl` byte for byte from the recorded replies.

**Out of distribution: LoCoMo** (`runs/ood/LOCOMO.md`). We never looked at this dataset while building: 10 conversations
between two people and 1,535 answerable questions. Measured offline with the same harness and no tuning:

| System | S | CF1 | Session recall | Gold-turn recall |
|---|---|---|---|---|
| naive keyword baseline | 31.3 | 0.32 | 0.60 | 0.37 |
| generic hybrid, same pack size | 56.8 | 0.38 | 0.87 | 0.78 |
| **routed v3** | **66.4** | **0.69** | 0.83 | 0.78 |

On both datasets the routed system scores about 2x the baseline (dev: 87.1 vs 42.9). On LoCoMo the gain comes from
the shared core and the citation planning; the type lenses add no recall there. S is not comparable 1:1 across the
two datasets, because LoCoMo needs its own stand-in for PA.

## 5. Decisions worth knowing

- **Compute, then let Reactor read.** Date arithmetic, latest-value logic and instance lists are done in code and given
  to Reactor as notes. Temporal was the hardest type (65 → 81). The calendar plus code-computed gaps carried it, which
  matches the literature: without a calendar, Chronos loses 34.5 points.
- **Precision over recall where it is safe.** Knowledge-update and single-fact packs are short, about 3k characters.
  Multi packs are wide because counting needs every instance. The `chars` term kept this honest.
- **No generic abstention hint.** Our absence signal reached only AUC 0.82, and no threshold gave precision ≥ 0.7 at
  recall ≥ 0.4. Reactor abstains correctly on its own when the fact is missing: 5/5 on calibration. In early test
  answers, most of its abstentions turned out to be *our* recall defects, which we fixed in v2 and v3. Recall is the
  bottleneck, not abstention.
- **We rejected a learned citation model.** A logistic model over 25 features matched the rules on dev, added nothing
  on real Reactor answers, and confidently cited a decoy on test (the answer was "Masa"; it cited a passage saying "not
  'masa madre'"). An adversarial verifier also found that our old knowledge-update chaining rule added 2 unsupported
  sessions on test. We fixed the rule and kept only rules whose added sessions contain or compute the answer.
- **No simulator answers in the submission.** We built an optional local-LLM simulator to A/B pack formats on training
  data. `finalize` refuses any file or line it produced.

## 6. Limits

- Router errors cost up to 6 S per type (ssu): compare the two columns of the per-type table. The expensive cells are
  multi→ssu and temporal→ssu; they are rare on test because test phrasing is more explicit than dev.
- Temporal remains the weakest type, at 80 routed: event matching against near-identical decoys.
- dev ≠ test. The test set is more adversarial, and dev200 only fixes the scale. Round-4 fixes were judged on visible
  test-pack defects, not on test answers.
- The Reactor server rejected continuing an older history ("history_changed") for re-asks. Those few questions were
  therefore answered in a fresh Reactor history with the same self-contained pack.

- Out of distribution (LoCoMo), multi-hop scores 26 S: questions with no counting cue go to the single-fact route,
  and no lens filters sessions by a calendar window named in the question ("the first weekend of October 2023").
  Our unanswerable-question signal does not transfer either (AUC 0.56, vs 0.81 on dev), so abstaining stays
  Reactor's call.
- Everything is English: BM25 stemmer, embedder, reranker and the notes to Reactor. Archives in other languages are
  untested.

## 7. Application

The demo is `demo/`: run `python3 -m demo.server --web demo/web` and open http://127.0.0.1:8800.

It shows one user's archive as a library of 200 books (sessions). The Librarian pulls the few relevant pages, the
code's margin notes appear next to them, and Reactor answers and seals the pages it cites. A counter shows how little of
the archive was read. The 5-stop tour covers one question per type, ending with an honest "not in the archive" in which
two other people's dogs are rejected as decoys. With Reactor free, a live question goes through the same pipeline.

`/live` (same server) takes any archive: a challenge history, a ChatGPT export, a WhatsApp export or dated notes
(`demo/ingest.py`). It indexes the upload locally (BM25 + embeddings, about a second for a 1.7M-character history whose
embeddings are cached), then asks Reactor through the same pipeline. On `demo/samples/founder_notes.md`, a fictional
startup notebook unrelated to LongMemEval, the code computed "16 days" between the demo day and the first paying
customer, and Reactor answered 16 with both sessions cited, in 47 s.

Business use: any assistant with long-lived memory (support, coaching, health, personal agents) needs to answer from
months of history:
- cheaply: it reads ~0.2% of the archive per question;
- verifiably: every answer carries its source sessions;
- safely: when the fact is not there, it says so instead of guessing.

We have that business use case, but we prefer to share the code with the community. The filter on its own (Python
and HTTP API, no Reactor, no benchmark tooling) is open source under MIT: https://github.com/brsword21/librarian-recall.

## Reproduce

See [README.md](README.md) for setup (`tools/setup.sh`), offline evaluation, pack building, the Reactor queue and
`finalize`.
