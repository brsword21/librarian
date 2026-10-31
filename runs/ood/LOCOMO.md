# Out-of-distribution check: LoCoMo

**Question:** does Librarian only work on LongMemEval-style histories, or on a memory dataset we never looked at?
**Answer:** the retrieval core and the citation planning transfer; the type-specific lenses do not add recall there.
On LoCoMo the routed system scores **S 66.4 vs 31.3** for the naive keyword baseline. On dev the same pair is 87.1 vs
42.9. That is roughly 2x the baseline on both datasets, with no tuning on LoCoMo.

## What and how
- **Data:** [LoCoMo](https://github.com/snap-research/locomo) (Maharana et al., 2024, `data/locomo10.json`, CC BY-NC
  4.0; not in this repo).
  - 10 conversations between two people, 19–32 sessions each, about 590 turns and 73k characters per conversation.
  - 1,986 questions: 1 multi-hop (282), 2 temporal (321), 3 open-domain (96), 4 single-hop (841), 5 adversarial
    (unanswerable, 446). We use 1,981: five answerable questions whose evidence ids do not resolve are dropped.
- **Conversion** (`harness/ood_locomo.py`): session = `session_N` with its date; turn = `dia_id`; content is
  `"Name: text"` plus the shared photo's caption. Question date = the day after the last session.
  - Two role mappings: **user** (every turn is a user turn) and **ab** (speaker A = user, speaker B = assistant).
- **Offline only, no Reactor.** For every question we build an evidence pack and check the gold evidence against it.
  The metrics match the dev harness: SR, ALL, ATR, AC (only where the gold answer is verbatim in the evidence turns),
  CF1 of the planned citations, and chars.
  - **S** = `100 · mean(0.65·PA + 0.30·CF1 − 0.05·chars/16000)`.
  - **PA stand-in** (LoCoMo has no code-computable answers, so no HA):
    - single-hop and open-domain: all gold turns in the pack, plus the answer if it is extractive;
    - multi-hop and temporal: all gold sessions and all gold turns in the pack.
- **Systems compared:**
  - **routed**: the submitted system, `lenses/pipeline.py` + `configs/best.json` (v3).
  - **hybrid_3k**: generic BM25 + dense + rerank, no router, at the routed system's pack size (~3.3k chars).
  - **hybrid**: the same at a 12k-char budget.
  - **naive**: the organisers' keyword baseline (our reimplementation, 42.9 S on dev).

## Results (user roles, 1,535 answerable questions + 446 adversarial)
| system | category | n | S | PA | CF1 | SR | ALL | ATR | AC (extractive, n) | chars |
|---|---|---|---|---|---|---|---|---|---|---|
| **routed** | 1 multi-hop | 282 | 26.2 | 0.24 | 0.39 | 0.56 | 0.32 | 0.49 | 0.54 (39) | 3895 |
| | 2 temporal | 320 | 71.5 | 0.78 | 0.73 | 0.85 | 0.83 | 0.81 | 0.65 (26) | 3118 |
| | 3 open-domain | 92 | 35.3 | 0.37 | 0.41 | 0.55 | 0.46 | 0.48 | 0.60 (5) | 3212 |
| | 4 single-hop | 841 | 81.3 | 0.89 | 0.81 | 0.94 | 0.94 | 0.90 | 0.92 (459) | 3093 |
| | **all 1–4** | 1535 | **66.4** | 0.72 | **0.69** | 0.83 | 0.77 | 0.78 | 0.88 (529) | 3253 |
| hybrid_3k | all 1–4 | 1535 | 56.8 | 0.71 | 0.38 | 0.87 | 0.81 | 0.78 | 0.89 (529) | 3233 |
| hybrid (12k) | all 1–4 | 1535 | 54.5 | 0.82 | 0.16 | 0.96 | 0.94 | 0.88 | 0.97 (529) | 11929 |
| naive | all 1–4 | 1535 | 31.3 | 0.34 | 0.32 | 0.60 | 0.55 | 0.37 | 0.45 (529) | 1736 |
| routed, **ab roles** | all 1–4 | 1535 | 59.8 | 0.63 | 0.67 | 0.71 | 0.67 | 0.68 | 0.80 (529) | 3534 |

The dev reference comes from `runs/leaderboard.csv`:
- routed v3: S 87.1, PA 0.94, CF1 0.92, SR 0.99, ALL 0.97, ATR 0.97, AC 0.98, 5.6k chars. dev200: 87.0.
- naive: S 42.9, PA 0.43, CF1 0.58, SR 0.74, ATR 0.50.
- generic hybrid at 12k (80-question sample): S 73.4, CF1 0.55, SR 0.99, ATR 0.97.

Adversarial questions (category 5): the abstention signal does not transfer.
- AUC of `abstain_p`, category 5 vs 1–4: routed 0.56 (user) and 0.54 (ab), hybrid 0.58, naive 0.50. On dev the
  routed system reaches 0.81.
- LoCoMo's adversarial questions swap the person ("What did Caroline realize after *her* charity race?", where it was
  Melanie's race). The words are in the history, so retrieval confidence cannot flag them. Abstaining stays Reactor's
  call, as in the submission.

Per-category tables for all four systems and both role mappings are in `locomo_results_summary.json`. Per-question rows
(packs' session ids, route, metrics) are in `locomo_results.jsonl`.

## What it means
1. **The core transfers.** Hybrid retrieval with reranking lifts session recall from 0.60 to 0.83–0.96 and gold-turn
   recall from 0.37 to 0.78–0.88. The gain comes from the shared core, not from LongMemEval-specific rules.
2. **Citation planning transfers; type-specific recall does not.** At the same pack size, routed and generic hybrid
   find the same evidence (ATR 0.78 vs 0.78), and the hybrid's session recall is slightly higher (0.87 vs 0.83).
   Routed still wins on S, 66.4 vs 56.8, because its planned citations are twice as precise (CF1 0.69 vs 0.38). On dev
   the router and lenses matched the 12k hybrid's recall at half the pack size. LoCoMo's questions are phrased
   differently, so the router sends 1,895 of 1,981 to the single-fact route.
3. **Multi-hop is the weak spot.** S is 26 and only 32% of questions get all gold sessions. LoCoMo multi-hop questions
   carry no "how many / in total" cue: 253 of 282 go to the single-fact route, which keeps at most about 3 sessions.
4. **Role mapping matters for uploads.** Labelling the second human as "assistant" costs 6.6 S (59.8 vs 66.4). The role
   hand-off moves 1,062 questions to the assistant lens, which keeps one session.
   - For any human-to-human chat, import every turn as `user` with a `"Name: "` prefix.

## Failure examples (routed, user roles)
- **Absolute date window.** *"What was Dave doing in the first weekend of October 2023?"* → "attending a car show".
  - The gold session is 2023/10/08 ("Last Friday I went to the car show"). We sent the March, April and August
    sessions instead.
  - The question carries no topic words, and no lens filters sessions by a calendar window named in the question.
    LongMemEval asks for gaps relative to the question date instead.
- **Session date named in the question.** *"What new activity did Maria start recently, as mentioned on 3 June,
  2023?"* → volunteering at a dog shelter.
  - The gold session is dated exactly 2023/06/03. We sent sessions 1, 10 and 21.
  - The date in the question is ignored. A date-to-session filter would solve this whole pattern.
- **Inference across sessions.** *"What is Dave's favorite activity?"* → "Restoring cars".
  - The gold evidence is in sessions 19, 21 and 22, and the word "favorite" never appears in it.
  - Routed to the single-fact lens, which picked sessions where Dave talks about other things he likes. The hybrid gets
    it wrong too.

## Limitations
- **Easier scale than test.** A LoCoMo conversation is about 73k chars, versus about 1.6M in our test histories.
  Recall is easier there: a 12k pack is 16% of the whole conversation.
- **S is not strictly comparable with dev.** PA is a stand-in (no HA, different question taxonomy), and AC covers only
  the 34% of answers that are verbatim in the evidence. Temporal answers are mostly absolute dates computed from
  "yesterday"-style mentions, so they are rarely extractive.
- **Retrieval only.** We measure whether Reactor would get the evidence; Reactor's answers on LoCoMo were not run.

## Reproduce
```sh
mkdir -p ../data/locomo && curl -sSL -o ../data/locomo/locomo10.json \
    https://raw.githubusercontent.com/snap-research/locomo/main/data/locomo10.json
.venv/bin/python -m harness.ood_locomo --per-cat 0 --roles user,ab --systems routed,naive,hybrid,hybrid_3k \
    --workers 2 --out runs/ood/locomo_results.jsonl   # 10-20 min on an M2 with core.model_server running
```
