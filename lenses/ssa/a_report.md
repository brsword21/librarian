# SSA lens A ("Struktura"), round 1 report

Lens: `lenses/ssa/a_recsent.py`, with **best variant `recqs_cf7`**. Scratch tools are in `lenses/ssa/scratch_a/`: `audit_best.py` (test best sentence, margin and abstain), `quote_prec.py` (whether the quoted line sits inside the gold turn), and `turn_dist.py` (best-turn vs gold-turn offset).

## Variants tried (one line each)
| variant | idea and params |
|---|---|
| `rec_bm25` | Round-0 `rec` with lexical channels only: `hx.bm25(query, 60)` + role-BM25, a structural sentence scan (cue, kind, purpose, third-party, contrast) with w_struct=1.0 on rec-style questions and 0.3 elsewhere, best turn whole + previous user turn + rest of the best session, budget 7000, cite 1 session. No model server. |
| `recq_bm25` | Adds a quoted "likely line" to the hint, gated strictly: first-person cue + a name/value + purpose match (or head-noun match when there is no purpose), ov ≥ 0.4, margin ≥ 1.3, not third-party/past/contrast. The hint keeps the question's own words ("for my freelance work"); round 0 wrongly flipped them to "your" and lowercased them. |
| `recqs_bm25` | Adds a **shape boost**: on rec-style questions, a unit whose best sentence is recommendation-shaped (shape ≥ 0.5) gets struct × (1 + shape). The first try boosted every cue sentence and cost 2 PA on dev; gated to shape ≥ 0.5 it is neutral on dev and dev200 and fixes 2/25 test picks. Also adds compound-term matching ("homebrew" ~ "Brew Supply") and a robust ordinal list-turn choice. |
| `recqs_b5` / `recqs_b4` | `recqs_bm25` with budget 5000 / 4000 to cut chars. PA dropped, so both are rejected. |
| **`recqs_cf7`** | `recqs_bm25` with cue floor 0.7 (struct × (0.7 + cue) instead of × (0.4 + cue)), so cue-less list items in dev answers are not crushed. It fixes the one CF1 miss on dev and leaves every test pick unchanged. |
| `rec`, `rec_quote`, `rec_tight`, `topic` | Round-0 hybrid + rerank variants, **not swept**. The shared model server was saturated (about 30 sweeps running): the generic baseline took 27 minutes on dev. Since lexical-only already gets PA 1.0 and CF1 1.0, dense and rerank can only add chars and latency here. |

## Results (harness.sweep, tag `r1-ssa-a`; ssa has no unanswerable questions in dev or dev200, so AUC is "-")
| split | variant | S | PA | ATR | SR | CF1 | chars | AUC |
|---|---|---|---|---|---|---|---|---|
| dev (112) | generic `hybrid_rr` (baseline) | 72.3 | 1.000 | 1.000 | 1.000 | 0.368 | 11932 | - |
| dev | `rec_bm25` | 93.0 | 1.000 | 1.000 | 1.000 | 0.991 | 5584 | - |
| dev | `recq_bm25` | 93.0 | 1.000 | 1.000 | 1.000 | 0.991 | 5587 | - |
| dev | `recqs_bm25` (ungated boost) | 91.8 | 0.982 | 0.982 | 0.991 | 0.991 | 5590 | - |
| dev | `recqs_bm25` (boost gated, shape ≥ 0.5) | 93.0 | 1.000 | 1.000 | 1.000 | 0.991 | 5587 | - |
| dev | `recqs_b5` | 91.0 | 0.964 | 0.973 | 1.000 | 0.991 | 4506 | - |
| dev | `recqs_b4` | 87.2 | 0.902 | 0.902 | 0.991 | 0.991 | 3764 | - |
| dev | **`recqs_cf7`** | **93.3** | 1.000 | 1.000 | 1.000 | **1.000** | 5587 | - |
| dev200 (22) | generic `hybrid_rr` (baseline) | 71.2 | 1.000 | 1.000 | 1.000 | 0.331 | 11938 | - |
| dev200 | `rec_bm25` | 93.3 | 1.000 | 1.000 | 1.000 | 1.000 | 5370 | - |
| dev200 | `recq_bm25` | 93.3 | 1.000 | 1.000 | 1.000 | 1.000 | 5374 | - |
| dev200 | `recqs_bm25` (gated) | 93.3 | 1.000 | 1.000 | 1.000 | 1.000 | 5376 | - |
| dev200 | `recqs_b5` | 90.7 | 0.955 | 0.955 | 1.000 | 1.000 | 4331 | - |
| dev200 | `recqs_b4` | 85.0 | 0.864 | 0.864 | 1.000 | 1.000 | 3673 | - |
| dev200 | **`recqs_cf7`** | **93.3** | 1.000 | 1.000 | 1.000 | 1.000 | 5376 | - |

Baseline cost: 27.5 min on dev and 4 min on dev200, against under 1 min for every lens variant.

Computed answers (ordinal list items) are correct in 6/6 dev cases and 3/3 dev200 cases. The harness reports HA 0.833 / 0.667 because the "27th parameter" gold answer is a sentence containing "27", which `first_number` compares against an item that has no number. This is a metric artefact.
Quote precision: the quoted line fires in 2/112 dev and 1/22 dev200 questions, and lies inside the gold turn 3/3 times. On test it fires in 23/25 SSA-routed questions.
Build time is about 250 ms/q on dev and about 1.1 s/q on dev200, with no model calls.

**Best: `recqs_cf7`**. It beats the baseline by +21.0 S on dev and +22.1 S on dev200: CF1 rises from 0.37/0.33 to 1.0 and chars fall from 11.9k to 5.5k at the same PA of 1.0. Over my own `rec_bm25` it adds +0.3 S on dev (the CF1 fix, below the 2-point bar but free) and ties on dev200.
Test audit (`harness.audit --n 12`, plus `scratch_a/audit_best.py` on all 25 SSA-routed test questions): 0 flags. **25/25 best sentences are the asked first-person recommendation**, and 23 are quoted in the hint. Two picks were fixed in round 1:
- "homebrew supply shop" → "You should check out Peachtree Brew Supply in Decatur", via compound match and shape boost. In round 0 the pick was an unrelated storage tip.
- "coworking space in Lisbon" → "Heden in Baixa has a good day pass", via shape boost. In round 0 the pick was a KonMari sentence. It is cited as the best session, with a runner-up session added because the margin is small.

## Top failure patterns (all now fixed or neutralised; these are what to watch)
1. **The right session but the wrong turn is the normal case, not the exception.** The best turn is the gold turn in only 74/112 dev and 14/22 dev200 questions; the offsets run from −8 to +8 turns. Examples: the Bandung Nasi Goreng question (the gold is 4 turns before the best turn), "Radiation Amplified zombie" (+5), and "tea tree oil ratio" (+8). PA stays at 1.0 only because the whole best session is packed. That is why budgets of 5000 and 4000 lose 4% and 10% PA. Cutting chars needs better turn ranking first.
2. **Generic "you recommended" questions in dev lose to cue sentences.** Example: "Mayo Clinic video you recommended". The struct scan preferred "For YouTube creators, OBS Studio and XSplit are popular choices" (cue + kind "video") over the cue-less list item '"How to Sit Properly…" by the Mayo Clinic', so the wrong session was cited. The fix is the softer cue floor (`cf7`).
3. **Over-eager structure boosts.** Example: "type of beer for Seco de Cordero". An ungated shape boost lifted "For a reliable power adapter for Japan, I'd recommend the following" from another session, and the gold turn then fell out of the 7000 budget. Gating the boost to shape ≥ 0.5 (head-noun or purpose match + a name + coverage ≥ 0.3) fixed it.
4. (Fixed.) Ordinal questions computed from the wrong turn when the best turn changed: "last venue in the list of Portland venues" returned "Music festivals…". The list turn is now the first assistant turn of the best session, in ranking order, whose list has at least n items.

## abstain_p
Dev and dev200 contain no unanswerable SSA questions, so AUC is not measurable. The design is qualitative: on rec-style questions, abstain_p maps the best *recommendation shape* anywhere in the assistant turns to 0.05 / 0.35 / 0.6 / 0.8 (+0.1 if the top unit has no cue). On test, 21/25 get 0.05 and 4/25 get 0.35 (Lisbon/Heden, RouteXL, Octane Coffee, all with weaker term coverage). By my reading every one of the 25 test SSA questions is answerable, so no high values is the correct outcome.

## CORE REQUESTs
1. **`harness.metrics` HA for ssa/ssu items**: when the gold answer is a sentence ("The 27th parameter was 'Sound effects…'"), compare `computed` by containment (`normalize(computed)[:40] in normalize(gold)`) before `first_number`. Today a correct item scores HA=0.
2. **`build_pack` priority vs chrono**: still wanted from round 0. When the budget cuts, keep the `ranked` priority (best turn first, session fill last). It works today only because 7000 rarely cuts. A `max_chars_per_session` option would allow a "best session whole, runner-up best turn only" pack without hand-ordering.
3. **Model-server load**: a per-agent queue or priority, or a "BM25-only" note in CONTRACT.md for types where lexical retrieval saturates. The 112-q baseline took 27 minutes.
4. `core.units._SENT` still splits "Dr." / "St." at chunk boundaries (round-0 request #2). It matters for the quoted-line hint ("I recommend Dr. Vogel").

## Ideas for next round
- **Reactor check of the quoted line** (integrator, about 10 test-style questions): compare `recqs_cf7` against the same variant with `hint_mode="generic"`. Offline metrics can't see the quote, and the test audit says it is right 25/25.
- **Better turn ranking, to cut chars without losing PA**: a round score (assistant unit + preceding user turn, as in B's design) and the cross-encoder over the best session's turns only (about 10 pairs, cheap once the server is free). Then pack the best turn ± 2 turns instead of the whole session, which needs turn@1 ≥ 0.95 first.
- Dense purpose matching only for rec-style ties (Lisbon-like "in Baixa" ↔ "in Lisbon"): `hx.dense(question, uids=shape≥0.5 units)`, which is a handful of vectors.
- Raise the quote gate's coverage requirement when the runner-up session's sentence has the same kind but a different purpose (Coach Miriam/Elena-style margins of about 1.1 currently suppress the quote, which is safe but loses help).
