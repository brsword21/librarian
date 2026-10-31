# Learned evidence attribution (reactorq/attribution.py)

`attribute(pred, pack, reactor_result) -> (citations, note)`. Answers are never touched. Abstentions keep their empty
citations. The finalize.py integration belongs to the orchestrator.

## Method
- **Data:** packs from the frozen v3 system (`reactorq.build_packs`, configs/best.json) for every answerable question:
  dev has 496 questions and 1651 pack sessions, dev200 has 110 and 323. The label is whether the session is in the gold
  evidence. Real check: e1b, with 16 answerable questions, real Reactor answers and citations, and the older e1b packs.
- **Proxy:** on dev and dev200 the gold answer (its first alias) plays the role of Reactor's answer.
- **Features**, all computable at test time from the answer and the pack:
  - normalized phrase containment (also the answer without parentheticals, or all content words present)
  - number token match and content-token overlap
  - in cite_plan, first in cite_plan, and cite_plan when pack.computed equals the answer
  - cross-encoder max over the session's segments vs the question and vs "question + answer", raw and relative to the
    pack's best (`HistoryIndex.rerank_texts`)
  - answer specificity: 1 / the number of sessions that contain the answer
  - 1 / the pack size
  - route one-hot with route × contains / in_plan interactions
  - whether the answer is a bare number, and bare number × contains
- **Model:** L2 logistic regression (C=0.1, chosen by 5-fold CV grouped by question). The coefficients are constants in
  the module, with no pickle.
- **Support rule:** a session is added only if it contains the answer (normalized or as a number) or is in cite_plan
  with a computed value that equals the answer. When Reactor has already cited something and the answer is a bare
  number on the multi or temporal route, containing that number does not count as support, because "3" in a session
  does not support "3 doctors". Without this gate one real e1b multi answer went from F1 1.0 to 0.75.
- **Decision:** Reactor's citations are always kept, because every Reactor citation in e1b was gold.
  - If Reactor cited something, add supporting sessions with p >= 0.5, at most 2.
  - If Reactor cited nothing, cite supporting sessions with p >= 0.4, at most 5, and always at least the best one.
  - ku-chain from finalize.py is kept as a separate switch (`use_ku_chain`, on by default). It does NOT satisfy the
    support rule, because the old session holds the old value.
- **Policy choice:** the CV optimum was 0.3 / 3. 0.5 / 2 tied it (0.6181 vs 0.6178) and adds fewer sessions, so it was
  taken.

## Results (mean evidence F1 over answerable questions; no answer = 0)

On the dev proxy, "Reactor" citations are simulated three ways: `contains` (the sessions that contain the answer, as the
task specified), `top1` (only the best containing session, which mimics Reactor under-citing) and `none` (fill-missing).

| split / scenario | Reactor only | + finalize rules | cite_plan only | **model** | model without ku-chain |
|---|---|---|---|---|---|
| dev CV / contains | 0.454 | 0.538 | 0.915 | **0.618** | 0.607 |
| dev CV / top1 | 0.441 | 0.525 | 0.915 | **0.618** | 0.607 |
| dev CV / none | 0.000 | 0.538 | 0.915 | **0.619** | 0.607 |
| dev200 / contains, top1 | 0.496 / 0.482 | 0.590 / 0.576 | 0.905 | **0.682** | 0.670 |
| dev200 / none | 0.000 | 0.590 | 0.905 | **0.682** | 0.670 |
| e1b real (16) | 0.693 | 0.693 | 0.666 | **0.714** | 0.714 |
| e1b real, answered only (13) | 0.853 | 0.853 | 0.819 | **0.878** | n/a |

Per type, dev CV / top1, finalize rules -> model:

| type | finalize rules | model |
|---|---|---|
| ku | 0.505 | 0.710 |
| multi | 0.035 | 0.098 |
| ssa | 0.830 | 0.929 |
| ssu | 0.870 | 0.901 |
| temporal | 0.560 | 0.645 |

The only change on e1b is q_7e25312cf880 (temporal): "The Nightingale by Kristin Hannah" gains its second gold
session (p=0.86, contains the answer), so F1 goes 0.667 -> 1.0. Nothing else changes and nothing gets worse.

## The main finding: the support rule is the ceiling, not the model
An oracle that cites exactly the gold sessions allowed by the support rule reaches:

| split | all | ssu/ssa | ku | temporal | multi |
|---|---|---|---|---|---|
| dev | 0.609 | 0.92 | 0.63 | 0.65 | 0.10 |
| dev200 | 0.678 | 1.00 | 0.58 | 0.71 | 0.11 |

The model without ku-chain gets 0.607 on dev and 0.670 on dev200, so it is at that ceiling. cite_plan alone scores
0.915 and 0.905, which shows that the packs already hold the right sessions. The remaining gap is structural:
- **multi:** count and sum answers ("3") do not appear in the instance sessions.
- **ku:** the old-value session does not contain the new value. Only ku-chain recovers it.
- **temporal:** gap answers ("6 days") are supported by the two event sessions only through our computation, which
  counts only when pack.computed equals Reactor's answer.

Further F1 can only come from a broader but still defensible notion of support:
1. **Reactor's own reasoning.** The `reply` field lists instances with [E#] labels before the final line. On e1b a ku
   reply mentioned both gold sessions while citing one. This was not usable for training (dev has no replies) and the
   signal is noisy: one reply mentioned all 8 passages.
2. **Instance support for multi.** A session supports a count when it holds one counted instance. This needs
   per-instance extraction in our multi lens, exposed as computed plus the sessions it used, the same way temporal
   does it.
3. **Computed values for ku and temporal.** Have the ku timeline emit `computed` (the newest value) and its old/new
   sessions. Then ku-chain becomes a computed-match citation under the support rule.

## Caveats
- e1b is small (16 questions) and its packs come from the older v1-era system. The +0.021 there is a single question.
- The proxy uses gold answers. Wrong Reactor answers find fewer containing sessions, so real gains will be smaller.
- The cross-encoder features need the shared model server (port 8765, sqlite cache). If it is down, they fall back to
  0, the scores shift, and the support rule still holds.

## Files
- `reactorq/attribution.py`: features, constants, `attribute()`, `decide()`, `ku_chain()`.
- `runs/citations/train_attr.py feats | fit [--write]`: reproduces everything here. Outputs `fit_result.json` and
  `fit.log`.
- `runs/citations/{dev,dev200}_packs.jsonl`: v3 packs. `feats_{dev,dev200,e1b}.jsonl`: per-session features.
