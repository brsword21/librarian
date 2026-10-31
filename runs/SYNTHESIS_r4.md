# Round 4 synthesis (integrator) -> v3

v3 = v2 + a small set of gated, test-visible defect fixes. Every v2 file is untouched; the new route lenses are
integrator wrappers (`lenses/{ssu,multi,ku}/merged_r4.py`) built on `core/merge.py::first_changed`: build the frozen v2
route pack, then each lens agent's gated post-fix wrapper in priority order; the first one whose Reactor-visible pack
(passage ids + texts, hint) differs from v2 wins, else the v2 pack is returned unchanged.

Config: `configs/best_v3.json` (= `configs/best.json`; `configs/best_v2.json` unchanged; pipeline variant `routed_v3`).
Test packs: `runs/final/v3_test_packs.jsonl` (same answer-format suffix). Changes vs v2: `runs/final/v3_changed.tsv`
(18 of 146 packs, all Reactor-visible; qids in `runs/final/v3_changed_qids.txt`).

## Per-type winners (gold-type sweeps, same split and question set, tag merge4)

| type | winner (route lens) | dev S / PA / CF1 / chars | dev200 S / PA / CF1 / chars | vs v2 |
|---|---|---|---|---|
| ssu | `ssu/merged_r4 r4` = v2 + [ssu/a_r4_route hpd, temporal/b_r4_last last, ssu/b_r4_sent g_res_lv_d] | 93.4 / 1.000 / 0.984 / 3608 | 92.5 / 1.000 / 0.955 / 3842 | tie (chars -11/-17); hops fire 0x on dev/dev200 |
| ssa | `ssa/a_recsent r2_conf2` (unchanged) | 93.6 / 1.000 / 1.000 / ~4.6k (agent run) | 93.7 / 1.000 / 1.000 / ~4.2k | saturated; 0 test defects |
| multi | `multi/merged_r4 r4` = v2 + [multi/a_r4_route vlbhc6, multi/b_r4_inst vc2] | 87.8 / 0.959 / 0.911 / 5842 | 83.3 / 0.909 / 0.868 / 6279 | +0.6 dev (Sall +0.6), dev200 tie |
| ku | `ku/merged_r4 r4` = v2 + [ku/a_r4 r4, ku/b_r4_ku nolate_c] | 93.4 / 1.000 / 0.979 / 3032 | 93.4 / 1.000 / 0.977 / 3040 | tie on S; Sall +0.1 / +0.3 |
| temporal | `temporal/a_r3_gap span_own` (unchanged) | 81.3 / 0.898 / 0.843 / 7520 (agent run) | 83.7 / 0.909 / 0.897 / 7453 | 0 test defects in 36 packs |

None of the round-4 fixes clears the +2 S bar on dev, because dev/dev200 have (almost) no questions of the test shapes
they repair (residence category->instance, by-how-many delta, 'last X I mentioned', one-line own instance asides,
late decoy sessions). They were adopted under the v3 rule instead: (a) repairs a visible defect on a test pack,
(b) changes few packs, (c) no regression on routed dev/dev200 S or Sall. All three hold.

## Routed system (lenses/pipeline.py, runs/merge4/all/pipeline/*)

| system | dev S (Sall) | dev PA / CF1 / CF1all / chars | dev200 S (Sall) | dev200 PA / CF1 / CF1all / chars |
|---|---|---|---|---|
| v2 (routed_v2) | 86.9 (85.3) | 0.942 / 0.915 / 0.860 / 5585 | 87.0 (85.2) | 0.946 / 0.905 / 0.847 / 5489 |
| **v3 (routed_v3 = routed)** | **87.1 (85.4)** | 0.944 / 0.915 / 0.861 / 5581 | **87.0 (85.3)** | 0.946 / 0.905 / 0.848 / 5485 |

Per gold type, routed v3 dev: ssu 87.4, ssa 93.0, multi 85.8 (v2 85.2), ku 91.5, temporal 80.3.
dev200: ssu 87.1, ssa 93.7, multi 83.0, ku 86.8, temporal 84.2.

## Router (no change in v3)

Text router accuracy vs gold type: dev 0.679, dev200 0.648. After the in-lens hand-offs (role -> ssa, ku gate -> ku):
dev 0.783, dev200 0.736. Dev confusion (gold rows, final route columns ssu/ssa/multi/ku/temporal):
ssu [49,0,14,2,5], ssa [7,104,0,0,1], multi [9,0,114,0,10], ku [21,0,32,21,4], temporal [5,0,4,0,124].
Mean S by (gold -> final route): ku->multi 93.3 (n=29) and ku->ssu 85.7 are cheap; the expensive cells are
multi->ssu 61.4 (n=7), temporal->ssu 57.3 (n=5), ssu->ku 51.4 (n=2), ssu->multi 73.0 (n=13, but 11 of 13 have PA 1;
the 2 PA-0 ones are 'largemouth bass caught', 'skeins of yarn found'). No router edit was made: any rule change would
move test packs outside the gated set, and the costly cells are small. Temporal-B's recency questions ('last X I
mentioned VERB') stay on ssu and are handled by the recency guard inside the ssu wrapper.

## Abstention (configs/abstain.json, measured_r4)

Routed v3 abstain_p AUC: dev 0.813, dev200 0.853, pooled 0.821 (45 unanswerable / 606 answerable); pooled
precision at 0.8 = 0.30, recall 0.20. No threshold reaches the enable bar (precision >= 0.7 at recall >= 0.4).
Policy unchanged: no generic abstention hint; abstain_p is logged only; lens-factual absence lines are kept
(temporal own-cut, and now ku a_r4 head-absence for the cats pack). Real Reactor, first 51 test answers: 6
INSUFFICIENT_EVIDENCE; 2 are correct abstentions (dog's name; screen-grid resistor: only Toshi's, a parts-bin and a
'briefly tried ... removed it' statement exist), 4 were pack recall defects (job title, Lisbon, bakery fund, volume
ohms), all repaired in v2/v3. Reactor abstains on its own when the fact is missing; the bottleneck is recall.

## Citations trade-off (not confirmed whether we may post-filter Reactor's citations)

CF1 on cite_plan is our intent; CF1all (every passage cited) is the pessimistic bound: routed v3 0.915 vs 0.861 on
dev (-5.6 S between S and Sall is mostly multi/temporal/ku context sessions). v3 fixes mostly ADD cited own-instance
sessions (multi) or DROP decoy sessions (ku rent, job title, tractors; ssu volume pack rebuilt from its 2 cited
sessions), so the packs move toward the cite set. Remaining risk: multi rescues keep the third-party decoys in the pack
(sister Paola's 30,000-peso fund, Carlos's three books), and real Reactor already cited outside cite_plan in 9 of 51
answers on v2 packs (`python -m harness.reactor_monitor --packs runs/final/v2_test_packs.jsonl`): ssu 5 (cat's name,
younger son, milonga, French tutor, AGC resistor), multi 3 (vegetables, tango shoes, systolic readings), ku 1 (rent). The constant suffix already asks to cite only the passage(s) that state the answer; the next lever is
dropping uncited context passages, not a longer hint.

## What changed in v3 (18 test packs; reasons per qid in runs/final/v3_changed.tsv)

- ssu (8): Lisbon 'I live in Graça' residence hop (v2 answer INSUFFICIENT_EVIDENCE), volume-control delta rebuilt from
  the 500k/250k pot sessions (v2 answer INSUFFICIENT_EVIDENCE), Van Nelle Factory sentence hop, beer 'peach saison' and
  book 'The Civil War' recency guard, 3 hint head-noun fixes (bicycle, café, renovation company).
- multi (5): bakery fund opening deposit (v2 INSUFFICIENT_EVIDENCE), orchids (v2 answer '0'), books since March (3 own
  reads; v2 pack's only number was Carlos's), vegetables (carrot seeds missing; v2 answer 5), book club March '7 people'.
- ku (5): rent decoy-session drop (v2 answer '9,000 shillings' came from the brother decoy session), long-run clause
  attribution (playgroup 9:00 out of the pair), cats absence line, job title and tractors late-session drop.
- Already answered by Reactor with the v2 hash (re-ask needed): Lisbon, vegetables, rent, bakery, volume ohms,
  orchids; job title was only answered on its v1 pack. The rest are not yet asked.

## Rejected / declined

- ku b_r4_ku nolate_c_cnt2 (rooms renovated): 15-session instance pack with noise (earrings, under-cabinet lighting,
  reunion food) and the neighbour's 'finished four rooms' decoy; loose. Kept the v2 pack (no completion line: known
  defect, next round).
- ssu b_r4_ssu sh (loose sentence hop): imported the running partner's half marathon and 'briefly tried' resistors.
- multi a_r4_verb vlw (no category word): injected decoys; b_r4_inst vc3_t11 (CE floor -11): noise.
- temporal so_nor (decoy-free gap packs): +0.0 / +0.1 S, would change 8 packs with no visible defect; revisit only if
  real Reactor cites the runner-up decoy (check with harness.reactor_monitor).
- ssa r4 role module on the ssu route (+0.1 routed dev, 0 test change) and b_r4_quote semq_shape (1 hint change, no
  defect): not worth a pack change now.
- Router edits: none (see above).

## CORE REQUESTs

Done (backward compatible):
- `harness.audit --qids q1,q2|FILE` builds only those test questions (ssu-B).
- `harness.audit --compare` with `--type X` ignores other routes' packs (no false PARTIAL DIFF; multi-A);
  `--diff OLD NEW [route]` takes an optional route filter; changed passage sets now print `+sid@date` / `-sid@date`
  (ku-B, ssu-B).
- `harness.reactor_monitor --results ... --packs ...`: lists INSUFFICIENT_EVIDENCE answers, answers citing outside
  cite_plan, uncited answers, and stale answers (pack hash changed) per route (ssa-B).
- `core/merge.py::first_changed` + `lenses/*/merged_r4.py` route wrappers.
Declined (this round): a_owner._NP unicode fix and b_sweep._FIRST case fix (lens-owned, and they would move many
test packs: do them as lens variants next round), hint-quality metric QA/QX (needs a gold quote annotation; prototype
in lenses/ssa/scratch_b/r4_quote_eval.py), synthetic check sets and rescue-precision mode (too big for a 40-minute
merge; listed in the brief), failures role column (low value now), b_merge deterministic ordering (frozen v1 code).

## Brief for the next round

See `brief_a` / `brief_b` in the round output (same text as below).

### A (structure) agents
- ssu-A: (1) make the question parser's noun phrase unicode-aware and participle-aware for RETRIEVAL, not only the hint
  (café, Graça, 'renovation company working'); ship as a new variant and list test pack changes with
  harness.audit --compare. (2) Generalise the residence hop into category -> instance typing (place / workplace 'I work
  at X' / school / product / person) for 'name of my <category>' questions whose pack has no instance of that type.
  (3) Extend the before/after delta to 'how much more/less', 'by how much did X change', 'how many more X than'.
  (4) Reactor cited outside cite_plan on 5 ssu answers (harness.reactor_monitor): find which context passages it cites
  and drop context sessions that are not needed for the answer.
- ssa-A: (1) export u_first (own vs pasted / role-play text) as a helper the ssu and ku lenses can use to drop pasted
  units. (2) Router cue 'my example of' / role-play -> ssa (1 dev question; verify 0 test change). (3) Keep v3 packs;
  fit nothing on ku/temporal routes.
- multi-A: (1) Drop (not only uncite) third-party value sentences (kin name + told me / opened / has) from count and
  sum packs: bakery 'sister Paola 30,000', books 'Carlos three'. (2) Kin/recipient gate for 'for my sister/daughter'
  (dev200 cousin false positive). (3) Grow the hyponym table from a static WordNet export. (4) Reuse the verb-class gate
  on the ssu route for multi -> ssu misroutes (routed dev S 61.4 on 7 questions).
- ku-A: (1) Old-value back-link: the replaced value quoted inside the new member ('Decaf') points to the older session
  to cite. (2) bge sentence admission for weak old members (job title 'Operations Manager'). (3) Extend the
  conflict-gated decoy-session filter to the extra sessions of the ssu and multi routes. (4) Long-run pack still carries
  the uncited playgroup session: drop uncited sessions whose only valued clause was misattributed.
- temporal-A: (1) 'N days/weeks ago' pin: T = question date - N, pin the top CE user units of sessions dated T +/- tol
  (dev ATR-0 failures). (2) so_nor only if harness.reactor_monitor shows real Reactor citing the runner-up decoy in gap
  packs. (3) Order restatements by dense similarity of the event phrase over pick-session user units.

### B (semantic) agents
- ssu-B: (1) Build the synthetic mixed-unit set (splice gold sentences into distractor units of dev histories) and
  calibrate the sentence-hop margin on gold. (2) Generalise the recency-verb hop to 'what did I end up <verb>ing' with
  an attribute check. (3) Multi-value own slot with no update cue (cat): dated own values hint, newest last, only behind
  a gate that fires 0x on dev answerable questions. (4) Answer-type hop for 'where do I work / which company / which
  school'.
- ssa-B: (1) Move the hint-quality metric (QA = quoted line contains gold, QX = names another item) into a harness
  prototype that runs on sweep output. (2) Synthetic rec-style ssa set (plant 'I recommend X for Y' + different-purpose
  decoy) to measure quote precision. (3) Clean quote join artifacts only when a pack is rebuilt for another reason.
- multi-B: (1) Rank class-matched candidates against a templated statement ('I read a book', 'I bought an orchid')
  instead of the question so short asides ('finished that Pelé biography') clear the floor. (2) Add event classes view /
  lead / use for the dev category -> instance misses. (3) Put every packed session that holds a class-matched own
  quantity sentence into cite_plan (book club June). (4) Rescue-precision harness mode: withhold a gold session and
  score whether the hook recovers it.
- ku-B: (1) Tighten cnt2 for the rooms question: own completion verb + bge category-noun similarity, no neighbour
  lines, cap ~6 sessions, keep the list-then-count hint; target the rooms test pack with < 6 passages and no 'four
  rooms' decoy. (2) Filter non-own statements out of the hint's 'Statements about this' list (Carlos's coffee).
  (3) Synthetic count-of-instances and late-decoy-contradiction ku set.
- temporal-B: (1) Recency as its own route: turn the b_r4_last candidate list into a dated, ordered hint of own
  mentions. (2) Lower the CE floor only with a category check (dev streaming service / Disney+). (3) Make the b_merge
  cross-encoder ordering deterministic (q_cd3c3026183d flips PA between runs).
