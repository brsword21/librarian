# Temporal lens B ("Semantyka"): round 4 report (final round, test-visible defects only)

Code: `lenses/temporal/b_r4_last.py`. It is a wrapper around the frozen v2 ssu route spec (`configs/best_v2.json`
routes.ssu). It edits no frozen file.
Runs: `runs/r4-temporal-b/...`. Audits: `runs/audit/ssu/b_r4_last/last/test_packs.jsonl` and
`runs/audit/temporal/a_r3_gap/span_own/test_packs.jsonl`.
Scratch files are in `scratch_b/`:
- `r4_grep.py`: regex search over a test history.
- `r4_last_proto.py`, `r4_last_own.py`, `r4_last_q.py`: candidate and score dumps.
- `r4_audit_*.txt` and `r4_*.txt`: sweep and audit logs.

Round-3 report: `scratch_b/b_report_r3.md`.

## 1. Temporal route on test: no visible defect, so no pack change is proposed

A rebuild of v2 `a_r3_gap span_own` matches `runs/final/v2_test_packs.jsonl` on all 36 temporal-routed packs (0
changes). I checked every pack against its history (`scratch_b/r4_grep.py`):
- **29 of 32 computed gaps** agree with B's independent `b_sem sem_turns9` computation (±1).
- **The other 3**, where B finds no value, I checked by hand: Moroccan dinner 73, fresco/Uffizi 46 and anniversary
  50. For the anniversary, "Our anniversary was June 21, 2022" is last year, and the 2023 date comes from the assistant
  line.
- **Lines from the assistant or in the second person** are correct: Ardèche ("You left for your Ardèche canoe trip on
  2023-07-12"), Juniper vet (the user says the same thing), citizenship workshop and cake tasting.
- **No later reschedule** exists for hive/varroa, tyre/inspection, pottery/glaze or jamboree. The third passage in
  those packs is a dated decoy: neighbour Jan, the wife's car, "the jamboree was on April 22, 2022", "Your sister
  visited Trondheim".
- **Firefighter span**: "joined the fire brigade when I was 23" and "retired ... the day I turned 63" give 40.
- **The 3 own-cut packs really have no own answer**:
  - trail shoes: only Camille bought them;
  - vaccines: Camille had the check-up, and for the user they are still "I still need to sort out";
  - first loaf: no loaf is ever mentioned. "My sourdough starter" appears on 06/29, but only for croissants.
- **Real Reactor so far**: 6 temporal answers (v1: 5, v2: 1, alfajor = 104). Each one equals the computed value and
  cites exactly the 2 planned sessions.

Only one risk is left. **8 packs carry a third (decoy) session**: monstera, Montreal lease, Moroccan dinner, varroa,
tyre, jamboree, anniversary and Bergen. If v2 Reactor cites that session, A's `so_nor` (passages = cite set) would fix
it. Re-asking costs 8 × ~105 s. Check this after the v2 pass, not before.

## 2. A visible test defect next to the temporal route: "the last X I mentioned" recency questions (route ssu)

The 5 test questions "What was the [style of the] last X I mentioned VERB?" all sit in history h_dc718905421e. They
are order/recency questions, but the text router sends them to ssu with confidence 0.4. The v2 ssu route gets 3 of
them right: state park → Cloudland Canyon, grill → Big Green Egg, and restaurant (only the wife and the brother tried
one, so it is likely unanswerable). **2 packs miss the user's latest own statement:**

| qid | v2 pack (cite) | missing latest own statement | fix: cite / passages |
|---|---|---|---|
| q_4b0e37d9cd0c "style of the last beer I mentioned I'd kegged" | 02/10, 03/15, 03/18; cites 03/18 "Maybe I'll just keg the wheat" (a maybe-plan) | 2023/05/21 s_9c4dc842da3d "I finally kegged my peach saison last weekend." | cite s_9c4dc842da3d; 3 → 4 passages, 5.3k chars |
| q_e3fb401aa669 "last book I mentioned I was reading" | 01/13, 02/12, 02/15; cites 02/12 ("The Lost City") | 2023/05/10 s_527519621ef9 "I switched to reading 'The Civil War: A Narrative' by Shelby Foote" | cite s_527519621ef9; 3 → 4 passages, 8.4k chars |

How `b_r4_last.py` works (variant `last`):
1. Parse the category and the action: "beer" / "kegged", "book" / "reading", and so on.
2. Find candidate user sentences in which:
   - the action appears as a done form: a past form, or `been / started / switched to + -ing`;
   - it is followed by a specific object: a quote, a capitalised name, or a determiner + word ("a lot" is
     excluded);
   - the sentence is the user's own (`a_calendar.subject_kind`) and not a plan, a negation or "maybe / I'll"
     (`a_r3_gap._undone`);
   - the cross-encoder score against the question (time word removed) is ≥ -7.
3. Take the latest candidate by session date.
4. If that session is already in the v2 cite_plan, the v2 pack is returned unchanged. Otherwise:
   - the statement's unit is pinned first, and only the v2 sessions are added after it (at most +1 session);
   - one hint line is added: "Most recent own statement found by code: the 2023/05/21 line ...";
   - cite_plan becomes that session.

The test audit (`harness.audit --lens lenses/temporal/b_r4_last.py --variant last --type ssu --n 999 --compare
runs/final/v2_test_packs.jsonl`) changes **exactly 2 of the 45 ssu-routed packs, the 2 above**. The other 3
recency questions are unchanged (park and grill are already cited; for the restaurant there is no own candidate).
If the v2 queue has not reached h_dc718905421e yet, swapping these 2 packs costs no extra Reactor time. Otherwise it
costs 2 re-asks (~3.5 min).

## Variants tried (one line each)
| variant | idea / params | outcome |
|---|---|---|
| (v2) `a_r3_gap span_own` | frozen temporal route, rebuilt as the baseline | 0 test diffs vs v2 packs |
| `last` draft 1 | any verb form; CE of the statement "I kegged beer" ≥ -2; no object check | **rejected**: book picked the 02/12 line "speaking of reading, I've been meaning to ask..."; fired on the restaurant question on "I'm trying to nail down a cookout menu" |
| `last` draft 2 | same, but the whole inner ranking at a 6k budget | beer pack grew to 9 sessions → limited to the v2 sessions + 1 |
| **`last`** | structural done-verb + object filter, own / not-plan, question-form CE ≥ -7, add at most 1 session | **taken**: 4 of 4 answerable test recency questions pick the right latest statement; restaurant does not fire; 0 dev / dev200 firings |
| `last_ce4` / `last_pipe_ce4` | CE ≥ -4 | would lose the beer fix (its CE is -6.1) |
| `last_pipe_lo` | CE ≥ -10 (evaluation only) | fires on the dev "Which streaming service did I start using most recently?": ALL 0.67 → 1, AC 0.67 → 1, PA and CF1 unchanged, S -0.3 on that subset (chars). Not taken: it also admits weaker lines on test |
| `last_pipe` | the same guard behind the full v2 pipeline (acts only when the final route is ssu) | used for the dev and dev200 checks below |

## Results

Temporal gold (dev 133 q, dev200 26 q):

| split | system | S | PA | ATR | SR | CF1 | chars | AUC | Sall |
|---|---|---|---|---|---|---|---|---|---|
| dev | generic hybrid_rr (bar) | 65.1 | 0.748 | 0.860 | 0.908 | 0.673 | 11931 | 0.636 | 65.1 |
| dev | v2 temporal lens a_r3_gap span_own | 81.3 | 0.898 | 0.957 | 0.980 | 0.843 | 7520 | 0.839 | 77.6 |
| dev | routed v2 (pipeline routed_v2) | 80.3 | 0.882 | 0.953 | 0.971 | 0.843 | 7255 | 0.853 | 77.6 |
| dev | routed v2 + b_r4_last (last_pipe) | 80.3 | 0.882 | 0.953 | 0.971 | 0.843 | 7254 | 0.853 | 77.6 |
| dev200 | generic hybrid_rr (bar) | 61.2 | 0.727 | 0.849 | 0.910 | 0.589 | 11941 | 0.932 | 61.2 |
| dev200 | v2 temporal lens a_r3_gap span_own | 83.7 | 0.909 | 0.955 | 0.968 | 0.897 | 7453 | 0.966 | 77.3 |
| dev200 | routed v2 | 84.2 | 0.909 | 0.955 | 0.968 | 0.909 | 7272 | 0.966 | 78.9 |
| dev200 | routed v2 + b_r4_last | 84.2 | 0.909 | 0.955 | 0.968 | 0.909 | 7272 | 0.966 | 78.9 |

Every recency-phrased dev question (`--qfilter "most recently|last [a-z ]+ I (mentioned|told)|I last mentioned"`,
3 q: bus or train, streaming service, camera lens; 0 on dev200):

| variant | S | PA | ATR | SR | ALL | AC | CF1 | chars | Sall |
|---|---|---|---|---|---|---|---|---|---|
| routed v2 | 36.3 | 0.333 | 0.722 | 0.889 | 0.667 | 0.667 | 0.556 | 6559 | 44.3 |
| last_pipe (= `last`) | 36.3 | 0.333 | 0.722 | 0.889 | 0.667 | 0.667 | 0.556 | 6559 | 44.3 |
| last_pipe_lo | 36.0 | 0.333 | 0.722 | 1.000 | 1.000 | 1.000 | 0.556 | 7383 | 45.9 |

The guard returns the v2 pack untouched for every question that does not parse as a recency question, so gold dev
and dev200 S and Sall cannot move for any type. The table confirms this for temporal: same S, Sall, PA and CF1. The
1-char dev difference is the known dev-run noise.

## Best variant
`lenses/temporal/b_r4_last.py` `last`, wired as routes.ssu: lens `lenses/temporal/b_r4_last.py`, variant `last`, no
params. It reads the v2 ssu spec from `configs/best_v2.json`. It changes 2 test packs, both fixing a visible
defect, and moves dev and dev200 by 0. Keep the temporal route as it is in v2.

## Failure patterns
1. **Recency questions phrased as "the last X I mentioned" land on ssu**, and the ssu ranking prefers the
   best-matching sentence over the latest one. Beer: the 03/18 "keg the wheat" line beats the 05/21 "kegged my
   peach saison" line, which never says "beer". Book: the January/February "book" sessions beat "switched to reading
   'The Civil War...'", which never says "book". The category noun is missing from the latest statement, so lexical
   and CE ranking both bury it.
2. **Bare CE is a weak relevance signal for this pattern.** ms-marco MiniLM scores "I'd love to chat more about
   books and reading" (+2.4) far above the planted "I switched to reading 'The Civil War...'" (-3.2). A structural
   done-verb + specific-object filter has to come before any score threshold.
3. **On dev, "most recently" questions score very low under v2** (S 36, PA 0.33 on 3 q). Examples: "Which mode of
   transport did I use most recently, a bus or a train?" (temporal route, PA 0) and "Which streaming service did I
   start using most recently?" (ssu, PA 0: the "started a free trial of Disney+" line has CE -9).

## CORE REQUESTs
1. Wire `lenses/temporal/b_r4_last.py` `last` as routes.ssu for the final pass, or take just its 2 test packs. The
   changed qids are q_4b0e37d9cd0c and q_e3fb401aa669; packs and reasons are in
   `runs/audit/ssu/b_r4_last/last/test_packs.jsonl` and in the table above.
2. After the v2 pass, list the temporal answers whose citations include a third (decoy) passage. If there are any,
   re-ask those packs with A's `so_nor`.
3. (Informational, for SSU owners) The audit shows the ssu pack for "What's the name of the half marathon I'm
   training for?" with `computed: "Decent"`, a garbage value taken from "Decent, but Sunday is tight". The hint does
   not show it, so Reactor does not see it, but it would be scored as HA on dev-like data.

## Ideas for the next round
- Treat recency ("last X I mentioned", "most recently", "ended up") as its own route. The candidate list from
  `b_r4_last.candidates` could give a dated, ordered hint of own mentions, the same way the temporal gap hint works.
  Build a small synthetic check set, because dev has only 3 analogs.
- Lower the CE floor only together with a category check (dense similarity of the object span against the category
  noun). That would fix the dev streaming-service case without admitting weak lines.
- Temporal route: decoy-free gap packs (`so_nor`) once real Reactor citations show the decoy session being cited.
