# SSU lens B "Semantyka": round 4 report (final round, test-visible defects only)

**Best variant: `lenses/ssu/b_r4_sent.py` `g_res_lv_d`.** It is a route lens (drop-in for the v2 ssu route). It runs
the frozen v2 ssu route unchanged (`a_r3_route.py kg3crga` + `merged_r3.py ku11fn4s_p5`, params read from
`configs/best_v2.json`) and then adds four gated second hops. Each hop adds at most one user unit, except the delta hop, which adds up to three:

1. **Sentence hop `g`** (round-3 brief B item 1: score the evidence by its best clean own sentence, not by its
   unit). The cross-encoder runs over the sentences of the user units in the hybrid top-150 pool plus the frozen
   ranking (`hx.rerank_texts`, cached). The best out-of-pack sentence enters when all of these hold:
   - its CE score is >= 2.0 and >= the best in-pack user sentence + 1.0;
   - `a_owner.classify` says it is valid (owner is not mismatch, polarity is not neg/plan, it has a head or verb hit),
     and it does not match `REJECT_RX`;
   - it has no third-party subject ("(Oh,) my running partner is training ...") unless that relation is in the
     question;
   - for name questions, it carries a capitalised name that is not in the question.

   If it beats the in-pack best by >= 2 logits, it also becomes the cite.
2. **Residence hop `res`** (credit: the round-3 brief, SSU-A item 1, category -> instance). For "which
   neighbourhood / area" questions it adds the best own first-person residence statement ("I live in X", "my flat is
   in X", "new apartment in X") when that statement is absent from the pack. It cites the statement when the pack's
   best sentence is below 0.
3. **Recency-verb hop `lv`**, for "the last X I mentioned I'd <verb>ed" questions. It takes the LATEST own affirmed
   sentence that carries an inflected form (past, or progressive after was/am/been) of the question's verb. Plan,
   negation, `REJECT_RX` and third-party sentences are excluded. A generic verb (one that appears in more than 8 user
   sentences: buy, read, try) also needs the head noun and a named or quoted instance. If the sentence is absent from
   the pack, it is added and cited.
4. **Delta hop `d`**, for "By how many <unit> did I <change> <attribute> (in my <object>)". It takes every own,
   affirmed user sentence that names an attribute word (a non-generic word of more than 3 characters, e.g. "volume",
   "control"), names the object if the question has one, and carries a number in the asked unit ("500k-ohm"). With
   1-3 such sentences, the missing ones are added and the cite becomes their sessions. The difference is left to
   Reactor; no hint is added.

The packs are otherwise byte-identical to v2. Frozen passages are reused verbatim and the added unit's session is
inserted in chronological order. The hint, `computed` and `abstain_p` never change. Hand-offs (route_final ssa / ku)
are returned untouched.

## Results
Every number below comes from a full sweep with no `--limit`. Runs are in `runs/r4-ssu-b/ssu/...` (gold-type ssu:
70 dev q, 23 dev200 q) and `runs/r4-ssu-b/ssu-routed/...` (`--route --type ssu`: 140 dev q, 38 dev200 q).

| variant | split | S | Sall | PA | ATR | SR | CF1 | chars | AUC |
|---|---|---|---|---|---|---|---|---|---|
| generic hybrid_rr (kit baseline, gold ssu) | dev | 76.6 | 76.6 | 1.000 | 1.000 | 1.000 | 0.512 | 11934 | 0.924 |
| generic hybrid_rr (kit baseline, gold ssu) | dev200 | 73.5 | 73.5 | 1.000 | 1.000 | 1.000 | 0.407 | 11933 | 0.955 |
| v2 (frozen, = `b_r4_ssu v2`), gold ssu | dev | 93.4 | 92.7 | 1.000 | 1.000 | 1.000 | 0.984 | 3619 | 0.906 |
| v2, gold ssu | dev200 | 92.5 | 89.7 | 1.000 | 1.000 | 1.000 | 0.955 | 3859 | 0.955 |
| v2, routed ssu | dev | 88.8 | 89.3 | 0.947 | 0.971 | 0.984 | 0.952 | 4193 | 0.934 |
| v2, routed ssu | dev200 | 88.8 | 88.9 | 0.971 | 0.971 | 0.986 | 0.900 | 4271 | 0.914 |
| `b_r4_ssu sh / sh_nc / res / sh_res` (loose hop) | dev, dev200, gold + routed | = v2 | = v2 | = | = | = | = | = | = |
| `b_r4_sent g_res_lv`, gold ssu | dev | 93.4 | 92.7 | 1.000 | 1.000 | 1.000 | 0.984 | 3619 | 0.906 |
| `g_res_lv`, gold ssu | dev200 | 92.5 | 89.7 | 1.000 | 1.000 | 1.000 | 0.955 | 3859 | 0.955 |
| `g_res_lv`, routed ssu | dev | 88.8 | 89.3 | 0.947 | 0.971 | 0.984 | 0.952 | 4193 | 0.934 |
| `g_res_lv`, routed ssu | dev200 | 88.8 | 88.9 | 0.971 | 0.971 | 0.986 | 0.900 | 4271 | 0.914 |
| **`b_r4_sent g_res_lv_d` (best)**, gold ssu | dev / dev200 | 93.4 / 92.5 | 92.7 / 89.7 | 1.000 / 1.000 | 1.000 / 1.000 | 1.000 / 1.000 | 0.984 / 0.955 | 3619 / 3859 | 0.906 / 0.955 |
| **`g_res_lv_d` (best)**, routed ssu | dev / dev200 | 88.8 / 88.8 | 89.3 / 88.9 | 0.947 / 0.971 | 0.971 / 0.971 | 0.984 / 0.986 | 0.952 / 0.900 | 4193 / 4271 | 0.934 / 0.914 |
| `g_res`, routed ssu | dev / dev200 | 88.8 / 88.8 | 89.3 / 88.9 | 0.947 / 0.971 | 0.971 / 0.971 | 0.984 / 0.986 | 0.952 / 0.900 | 4193 / 4271 | 0.934 / 0.914 |

**The dev and dev200 splits cannot see these hops.** Even the loose `sh` never fired on any of the 91 + 29 ssu-final
dev/dev200 questions: there, the pack already holds the best sentence. The dev histories have no planted mixed
units, no "which neighbourhood" questions, and no "last X I mentioned" or "by how many <unit> did I" questions. The
`res` cue matches 5 dev and 2 dev200 questions, but it never fires there because the pack already holds the statement. So dev and dev200 are identical to
v2: no regression in S or Sall, but no gain either. The value of this lens is the test audit below. It is a
test-defect fix with a dev and dev200 no-regression guarantee, not a dev improvement. By the contract's +2 rule it
does not qualify on dev. I recommend it only because it fixes visible test defects at zero gold cost.

## Test audit
Command: `harness.audit --lens lenses/ssu/b_r4_sent.py --variant g_res_lv_d --type ssu --n 999 --compare
runs/final/v2_test_packs.jsonl`. 45 ssu-routed packs; **4 change**. All four changes are Reactor-visible (added units plus
a new cite). `g_res_lv` gives the first three.

| qid | question | v2 defect | r4 change | Reactor status |
|---|---|---|---|---|
| **q_607d3cf5b4f1** | What's the name of my neighborhood in Lisbon? | v1 answered **INSUFFICIENT_EVIDENCE**. "I live in Graça" was never retrieved: CE -11.1, bge rank 454, the sentence has no question word. | + s_25010d68d7cc (06/14) "I live in Graça, but the 28 tram ..."; cite -> that session | already answered by v1 (v2 order 6): **needs a re-ask** |
| **q_6fa4f8620294** | What venue did I book for my daughter's wedding reception? | The pack holds only "trying to figure out wedding venues" (07/14, after the booking) and two seating-chart sessions. The booking sentence sits in a mixed unit (chess drills, bees, then "We finally booked the Van Nelle Factory for my daughter's wedding reception"), so its unit scored low. Its sentence scores 3.51 against an in-pack best of 0.55. | + s_d8b1a3729067 (05/20) unit; cite -> that session | not asked yet (v2 order 108) |
| **q_4b0e37d9cd0c** | What was the style of the last beer I mentioned I'd kegged? | The pack holds Feb/Mar pale-ale and wheat sessions ("Maybe I'll just keg the wheat"). The only own kegging statement, "I finally kegged my peach saison last weekend" (05/21), is missing: CE -4.4 even in statement form. Reactor would answer wheat or pale ale. | + s_9c4dc842da3d (05/21) unit; cite -> that session. The later "thinking about kegging a blonde ale" (06/24) is a plan and is excluded. | not asked yet (v2 order 116) |
| **q_33b11e8a4d44** | By how many ohms did I reduce the volume control resistance in my National R-77? | The pack holds only cathode-resistor (150 -> 180 ohms) and trial-resistor sessions and no volume-control sentence at all. That invites "30" or INSUFFICIENT_EVIDENCE. | + s_76c839c5c8cb (03/05) "replaced the scratchy volume pot with a 500k-ohm log taper unit" + s_c6ece1712294 (05/19) "installed a 250k-ohm log taper volume pot"; cite -> both. Excluded: the Panasonic RF-2200 500k pot (other object), Toshi's pot (assistant turn) and the junked S-38 1M pot (other object). The answer is 250k ohms. | not asked yet (v2 order 46) |

Firings checked and rejected by the gates (no pack change):
- younger son: 3 nameless sentences;
- R-77 speaker / screen-grid / AGC: the "briefly tried ... removed it" trial decoys are invalid;
- volume-control ohms: the AGC "+15k ohms" sentence is only +0.07 over the in-pack best;
- physiotherapist: "My sister Nadia saw a physiotherapist", owner mismatch;
- sailing instructor: Ines's Tomas;
- running group: Stumptown Joggers, not joined;
- half marathon: running partner's Bridge to Brews, third-party subject;
- last book: the "self-help books" line names no title;
- state park, grill: the latest verb sentence is already in the pack.

The looser variants show why the gates exist. `b_r4_ssu sh_res` changed 8 test packs. It added the running-partner
decoy to the half-marathon pack, a dial-lamp sentence to two R-77 packs and the AGC sentence to the ohms pack.
Earlier versions of `lv` added "I've already been reading self-help books" to the last-book pack.

Real Reactor (v1 + v2 so far) on the ssu route: cat Fig, coffee shop, younger son Daniel, favourite meal / colour and
milonga look right. Dog INSUFFICIENT_EVIDENCE is likely correct: no own dog is in the history. Neighbourhood is
fixed here. French tutor "Camille" is doubtful: Camille is a "conversation partner", and the only named teacher is
Hélène of an Alliance Française class. The pack sentence "ask my French tutor" names nobody. This lens does not
touch it: no own sentence names a tutor, so it is likely an abstention question or a gold that accepts Camille.

## Variants tried (one line each)
- `b_r4_ssu v2`: control, the frozen v2 ssu route; reproduces `runs/final/v2_test_packs.jsonl` (0 / 45 changes).
- `b_r4_ssu sh`: loose sentence hop (CE >= 2, >= in-pack best - 1.5, own check): 0 dev/dev200 firings; 7 test packs
  changed, 5 of them for the worse (decoys, wrong attribute, nameless).
- `b_r4_ssu sh_nc`: same without the re-cite. `res`: residence hop only (1 test change). `sh_res`: both (8 test changes).
- `b_r4_sent g`: gated sentence hop (margin +1, valid, third-party, name) -> 1 test change (venue).
- `b_r4_sent g_m0_res`: margin 0 -> adds the wrong-attribute AGC sentence to the ohms pack (rejected).
- `b_r4_sent g_res`: gated hop + residence hop -> 2 test changes (neighbourhood, venue).
- `b_r4_sent g_res_lv` = g_res + recency-verb hop -> 3 test changes (+ last kegged beer).
- **`b_r4_sent g_res_lv_d`** = g_res_lv + delta hop -> 4 test changes (+ volume-control ohms). An earlier version used
  `a_r3_route.typed_values`, which reads '500k-ohm' as 500 k(m): the hop now builds its own number+unit regex from the
  question's unit.
- `b_r4_sent lv` / `res`: single hops, for ablation.

## Round-3 brief items not taken (test-visible-only round)
- Item 2, pair cite by value type: it changes `cite_plan` only (dev200 5K PB, Saturday wake-up). Reactor sees nothing
  different, so it is not worth a re-ask now.
- Item 3, multi hand-off on aggregate cues ("two", "both", "how old was I when"): 0 of the 45 ssu-routed test
  questions carry these cues, so there is no test change to make.
- Item 4, synthetic check set: still open (see CORE REQUESTs). Dev has no question of the families the new hops
  target.
- Scratch: `scratch_b/r4_scan.py` (best in-pack vs out-of-pack user sentence per test pack: this is how the venue,
  beer and ohms defects were found), `r4_show.py` (pack viewer), `r4_diag.py`, `r4_changed.tsv` (changed qids and
  reasons).

## Top failure patterns (what remains)
1. **Category -> instance vocabulary gap.** The answer sentence does not contain the question's noun, and neither
   model knows the instance: "Graça" is a neighbourhood, a "peach saison" is a beer style. Both the CE and bge-small
   fail (Graça: CE -11, bge rank 454). Only answer-type lexical hops catch these. `res` and `lv` cover two families.
   Others remain: "kitchen gadget" -> Instant Pot (dev), and "museum where I work" (test; probably an abstention
   question, since the museum is never named).
2. **Mixed units hide a sentence.** A unit that covers 3-4 topics gets a low unit-level CE (venue). The sentence hop
   fixes this when the sentence clearly beats the pack. Below the +1 margin we cannot tell a missing fact from a
   same-object wrong-attribute sentence (R-77: AGC vs volume control).
3. **Planted third-party and trial decoys score highest at sentence level.** Examples: "My friend Ines's sailing
   instructor is named Tomas" 6.53 vs own Marta 3.84; "briefly tried a 22k-ohm screen grid resistor" 6.54. Any
   sentence-level admission needs an owner, third-party and trial gate, or it imports decoys.

## CORE REQUESTs
- `harness.audit --compare` could print the added and removed unit text per changed pack (the "kept 3" line does
  not say what entered). I used `scratch_b/r4_show.py`.
- A `--qids FILE` option for `harness.sweep`/`audit`, to re-run only the changed packs.
- A synthetic check set (brief B item 4) remains open. Dev has 0 "last X I mentioned" and 0 neighbourhood questions,
  so these hops can only be judged on the test audit.

## Integration
- Swap the ssu route lens to `lenses/ssu/b_r4_sent.py` `g_res_lv_d`; no params are needed, because it reads v2's ssu
  route from `configs/best_v2.json`. Only the 4 packs above change. The re-ask set is q_607d3cf5b4f1 (answered
  INSUFFICIENT_EVIDENCE by v1). q_6fa4f8620294, q_4b0e37d9cd0c and q_33b11e8a4d44 are still unasked in the v2
  queue: if their packs are swapped before Reactor reaches them, there is no extra cost.
- Minimal-risk alternatives: `g_res` (2 changes: neighbourhood, venue) and `g_res_lv` (3). They skip the recency-verb
  and delta heuristics, which no gold split can measure: dev and dev200 have 0 'last X I mentioned' and 0 'by how many
  <unit> did I' questions.

## Ideas for the next round
- Generalise `lv` to "what did I end up <verb>ing": the latest own inflected-verb sentence intersected with the
  attribute check of `a_struct2.rec_need`.
- Add an answer-type hop for "where do I work / which company / which school" ("I work at X", "I'm a nurse at X").
- Use sentence-level CE as a second abstention feature only when the owner gate passes (round 3 showed that the raw
  z-score is anti-informative).
- Build a small synthetic dev set of mixed-unit facts by splicing gold sentences into distractor units, to measure
  the sentence hop's margin on gold.
