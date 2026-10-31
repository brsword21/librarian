# SSU lens A "Struktura": round 4 report (final lens round, test-visible defects only)

Code: `lenses/ssu/a_r4_route.py`. It wraps the FROZEN v2 ssu route (`lenses/ssu/a_r3_route.py` kg3crga with the
`configs/best_v2.json` params: inner `merged_r3.py ku11fn4s_p5`, role `ssa/a_r3_role.py`, ku `ku/a_r3.py r3w`). It
imports these files and edits none of them. Every fix is a gated post-process of the v2 pack. Variant `v2` reproduces
v2 exactly (88.8 / 88.8 routed).
Earlier reports: `a_report_r1.md`, `a_report_r2.md`, `a_report_r3.md`. Runs: `runs/r4-ssu-a/` (all variants) and
`runs/r4-ssu-a2/` (final hpd after the hint-rule tightening). Test audit: `lenses/ssu/scratch_a/r4_audit_hpd.txt`;
test packs in `runs/audit/ssu/a_r4_route/hpd/test_packs.jsonl`.

**Best variant: `hpd`.** It ties v2 on every gold metric on dev and dev200 (gold-type and routed). It changes 5 Reactor-visible
ssu test packs, and each one fixes a defect visible on test (listed below).

## Variants (cumulative, one hypothesis each)
- `v2`: the frozen v2 ssu route. Packs are byte-identical to v2.
- `h` (brief item 2): fixes the ownership-hint noun. The hint's anchor comes from `a_owner.parse_question`. Its
  NP regex is ASCII-only, so 'café' fails and the parser falls back to the last two content words ('before work').
  The parser also keeps participles ('renovation company working'), takes leftover words ('ride work') and takes the
  unit in 'by how many ohms'. Only the hint text is rewritten; retrieval still uses the old parse. A unicode NP
  extractor ('name of the X', 'what <attr> is the X', 'by how many <unit> did I <verb> the X') supplies the noun. When
  the head is degenerate (an -ing participle, a function word, work/home/before/after, a unit) and no noun is found,
  the ownership sentence is dropped.
- `hp` (brief item 1): a residence hop for 'name of my neighborhood (in <City>)'. It scans the user's first-person
  residence statements ('I live in / we moved to / my flat is in' + a Capitalised place) and skips places named in the
  question. It does nothing when the pack already holds such a statement, or when a user line in the pack already places
  the home ('lease for a new apartment in Kreuzberg'). Otherwise it takes the bge-cosine best (>= 0.35), runs a persona-
  coherence check (max bge cosine to the user's units that mention the question's city >= 0.62), then adds that
  session to the pack and makes it the cite.
- `hpd` (brief item 4): before/after delta for 'By how many <unit> did I <reduce|increase|...> the X in my Y?'.
  Candidates are affirmed own sentences with exactly one value in <unit>. Each must contain every proper-noun/model
  anchor of the question (R-77) and an X word. Trial and parts-bin sentences are rejected ('briefly tried', 'removed
  it', 'junked', 'parts bin', 'ordered'). The cross-encoder picks the top 2 with different values from different
  sessions, and date order gives before -> after. The direction must match the verb. The pack is rebuilt from those 2
  sessions, cite = both, `computed` = |after - before|, and the hint states the computation.
- Not done: brief item 3 (clause-level tense check). It was out of time, and dev cannot see the R-77 risk (see round 3).

dev and dev200 hold 0 questions that match the hp / hpd gates (scan of every split by question text), so those two
fixes can only move test. `h` changes only hint text on dev (chars).

## Results
Gold ssu = 70 dev q / 23 dev200 q; routed ssu = 140 dev q / 38 dev200 q. All rows are full sweeps.

| lens / variant | split | S | Sall | PA | ATR | SR | CF1 | chars | AUC |
|---|---|---|---|---|---|---|---|---|---|
| generic hybrid_rr (gold) | dev | 76.6 | 76.6 | 1.000 | 1.000 | 1.000 | 0.512 | 11934 | 0.924 |
| generic hybrid_rr (gold) | dev200 | 73.5 | 73.5 | 1.000 | 1.000 | 1.000 | 0.407 | 11933 | 0.955 |
| v2 (gold) | dev | 93.4 | 92.7 | 1.000 | 1.000 | 1.000 | 0.984 | 3619 | 0.906 |
| v2 (gold) | dev200 | 92.5 | 89.7 | 1.000 | 1.000 | 1.000 | 0.955 | 3859 | 0.955 |
| h = hp = hpd, first hint rule (gold) | dev / dev200 | 93.4 / 92.5 | 92.7 / 89.7 | 1 / 1 | 1 / 1 | 1 / 1 | 0.984 / 0.955 | 3566 / 3798 | same |
| v2 (routed) | dev | 88.8 | 89.3 | 0.947 | 0.971 | 0.984 | 0.952 | 4193 | 0.934 |
| v2 (routed) | dev200 | 88.8 | 88.9 | 0.971 | 0.971 | 0.986 | 0.900 | 4271 | 0.914 |
| h = hp = hpd, first hint rule (routed) | dev / dev200 | 88.8 / 88.8 | 89.3 / 88.9 | .947 / .971 | .971 / .971 | .984 / .986 | .952 / .900 | 4147 / 4223 | same |
| **hpd final (gold)** | dev | **93.4** | 92.7 | 1.000 | 1.000 | 1.000 | 0.984 | 3608 | 0.906 |
| **hpd final (gold)** | dev200 | **92.5** | 89.7 | 1.000 | 1.000 | 1.000 | 0.955 | 3842 | 0.955 |
| **hpd final (routed)** | dev | **88.8** | 89.3 | 0.947 | 0.971 | 0.984 | 0.952 | 4184 | 0.934 |
| **hpd final (routed)** | dev200 | **88.8** | 88.9 | 0.971 | 0.971 | 0.986 | 0.900 | 4261 | 0.914 |

The first hint rule treated every fallback anchor as degenerate. It dropped the ownership sentence on 76 dev
ssu-routed questions, most of them ssa questions that the role hand-off sends away. That saved chars, but it would also
have removed the "plans / other people's X" guidance from fine anchors ('ikea bookshelf', 'japan'). The final rule only
rewrites real non-noun heads. The rewrite now touches 9 dev, 2 dev200 and 4 test questions, and all 9 dev ones read
badly: 'get home', 'day of week', 'parents been staying', 'oil use'.

## Test pack changes vs runs/final/v2_test_packs.jsonl (5 Reactor-visible, all ssu route; 40 of 45 identical)
| qid | question | change | reason (visible defect) |
|---|---|---|---|
| q_607d3cf5b4f1 | name of my neighborhood in Lisbon | + s_25010d68d7cc ('I live in Graça, but the 28 tram ...'), cite s_02e229aaa490 -> s_25010d68d7cc, abstain_p .27 -> .10 | v1 Reactor answered INSUFFICIENT_EVIDENCE: the answer sentence was never in the pack (it ranks 58th by hybrid) |
| q_33b11e8a4d44 | by how many ohms did I reduce the volume control resistance in my R-77 | pack rebuilt from s_76c839c5c8cb (500k-ohm volume pot, 03-05) + s_c6ece1712294 (250k-ohm volume pot, 05-19); hint states 500k -> 250k = 250k ohms; computed 250000 | the v2 pack held only cathode / screen-grid resistor sessions (150 -> 180 ohms, so Reactor would say 30); no volume-pot session |
| q_1d7f43897caa | brand of the bicycle I ride to work | hint 'their own ride work' -> 'their own bicycle' | broken hint noun |
| q_b7053d97740b | café where I stop for a cappuccino before work | hint 'their own before work / other people's work' -> 'their own café / other people's café' | broken hint noun. The pack holds the decoy 'Francesca usually stops at Caffè Rivoire' next to the user's 'I usually stop at Caffè Gilli'; the fixed hint names the café ownership contrast |
| q_a77da671eff0 | renovation company working on our bungalow | hint 'renovation company working / other people's working' -> 'renovation company / other people's company' | broken hint noun. The only candidate is a plan ('Ben ... recommended Bridge City Builders ... I'm going to call them'); the fixed hint's "plans ... are not the answer" now attaches to the right noun |
Unchanged on purpose: q_1b638b1afb30 (Berlin neighborhood). The pack already says 'new apartment in Kreuzberg'. Before the
'pack states the place' guard, the hop wrongly added a filler 'I just moved to Austin from NYC' (persona cos 0.58 vs 0.67 for Graça).

## Top failure patterns (test, qualitative; dev ssu is saturated: gold PA = 1)
1. **Category -> instance, answer sentence without the category word.** Lisbon 'neighborhood' vs 'I live in Graça'
   (rank 58). Dev 'kitchen gadget before the Air Fryer' vs 'my new Instant Pot' is the same shape and is not fixed (no
   general place/product typing yet; the hop covers residences only).
2. **Paraphrased attribute -> retrieval misses the object.** 'volume control resistance' vs 'volume pot'. The pack held
   the neighbour attribute (cathode resistor 150 -> 180) with the same unit, the classic same-unit decoy. Fixed only for
   the 'by how many' form.
3. **Several own-sounding values for one slot, no update cue.** Cat's name: Fig (05-28), Bica (06-01, 'my son claims
   she's his cat'), Sombra (07-19), Zé (06-14) are all first-person. v1 Reactor answered 'Fig' while v2 cites
   Sombra. Neither the lens nor Reactor has a principled tie-break. Not changed: no evidence which one is gold.

## CORE REQUESTs
- `a_owner.parse_question`: make `_NP` unicode-aware ('café', 'Graça') and stop the NP at -ing participles. The hint fix
  here is a post-process only; retrieval still uses the broken anchor ('before work').
- A small synonym/paraphrase table in core query expansion for device parts (volume control <-> volume pot / potentiometer),
  or a `hx.dense_texts` second hop over own sentences that carry the question's unit.

## Ideas for next round
- Generalise the hop: answer-type typing (place / product / person) + first-person declarative patterns + persona
  coherence, for every 'name of my <category>' question whose pack has no instance of the type.
- Delta/compute for 'how much more/less', 'by how much did X change' over typed own values (reuse `typed_values`).
- Multi-value slot without an update cue (the cat): emit a hint listing the dated own values and asking for the most recent,
  but only after a Reactor check.
