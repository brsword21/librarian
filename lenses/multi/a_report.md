# Lens A "Struktura" for multi-session: Round 3 report

Lens: `lenses/multi/a_r3_pin.py`. It copies the frozen `b_tight.build` (`p08c35_aor`, the v1 multi lens behind
`merged_r2.py tight_role9`) and adds three optional layers on top. Variant `ref` reproduces v1 exactly
(dev 87.25 / dev200 83.3).
1. **Sentence-level rescue** (brief item 1): sessions that b_tight did not keep, but whose best own declarative
   sentence ranks near the top by bge cosine.
2. **Pinned trimming**: a unit keeps its best sentence when it is trimmed.
3. **A sentence-evidence abstention term** (brief item 3).

Runs: `runs/r3-multi-a/multi/{generic,a_r3_pin}/<variant>/{dev,dev200}` and `runs/r3-multi-a/multi-routed/...`.
Test audits: `runs/audit/multi/a_r3_pin/{r2m,lf,ab}`.
Scratch files are in `lenses/multi/scratch_a/`:
- `r3_sentrank.py`: where gold instance sentences rank under sentence CE and dense scoring.
- `r3_resc_an.py` / `r3_resc_ce.py`: precision of the rescue.
- `r3_like.py`: the multi_like detector check.
- `r3_audit_*.txt`: the test audits.

The round-2 report is archived below and in `scratch_a/a_report_r2.md`.

## Headline

- **Recommendation for the single remaining test pass: no pack change for multi from lens A.** v1 (`b_tight
  p08c35_aor`) stays.
- **Rescue** (`r2m` / `g2m`): +1.0 S on dev (2 PA questions: furniture, years of formal education) and ±0 on dev200.
  Sall is −0.3 to −1.5 on dev200, and the test audit shows it mostly injects decoys and junk.
  - `r2m` changes 16 of 20 test multi packs.
  - Even the strict lexical + fact gate (`lf`) changes 5, and on inspection 4 of those 5 rescues are planted decoys
    or noise (details in Failure patterns).
  - It fails the +2 S acceptance rule and would cost citation precision on test.
- **Abstention** (`ab`): leaves 0 of 20 test packs changed, so passages, cite_plan and hints are identical to v1.
  - Gold-type AUC: dev 0.731 → **0.787**, dev200 0.795 → **0.955**.
  - Routed multi AUC: dev 0.774 → 0.754, dev200 0.763 → 0.850, pooled 0.769 → 0.778.
  - Precision is still below the policy bar: pooled routed, threshold 0.6 gives 10/23 at recall 0.50.
  - It is safe to log, but it is not good enough to drive an abstention hint.
- **multi_like hand-off** (brief item 2): no usable evidence signal. Sentence-level features do not separate the 9 dev
  multi→ssu questions from the 49 gold-ssu ones (table below), so I built no hand-off and there are no test firings.
- **Hint wording**: the e1 Reactor false abstention (road-trip hours, q_2605c5385371) looked like the "ignore things I
  only planned" clause, but B found the real cause: trimming had cut the "it only took me four hours" sentence
  (`b_r3_full.py`).
  - My `hint_pass` flag (variant `g2mb_h`) adds "(a past event I mention in passing while planning something new still
    counts)".
  - It is unmeasurable offline and would change 17 of 20 test multi packs.
  - Not recommended unless a Reactor check is run.

## Results (gold type multi; dev 133 q / 121 answerable, dev200 28 q / 22 answerable)

| variant | dev S | Sall | PA | ATR | SR | CF1 | chars | AUC | dev200 S | Sall | PA | ATR | SR | CF1 | chars | AUC |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| generic/hybrid_rr (bar) | 69.1 | 69.1 | 0.744 | 0.873 | 0.961 | 0.817 | 11931 | 0.598 | 63.7 | 63.7 | 0.682 | 0.844 | 0.950 | 0.770 | 11947 | 0.689 |
| **ref = v1 b_tight p08c35_aor** | **87.2** | 85.7 | 0.950 | 0.980 | 0.984 | 0.910 | 5841 | 0.731 | **83.3** | 82.3 | 0.909 | 0.962 | 0.973 | 0.868 | 6279 | 0.795 |
| pin | 87.2 | 85.7 | 0.950 | 0.980 | 0.984 | 0.910 | 5874 | 0.731 | - | - | - | - | - | - | - | - |
| r1 | 87.8 | 85.2 | 0.959 | 0.985 | 0.988 | 0.910 | 5918 | 0.731 | 83.2 | 81.0 | 0.909 | 0.970 | 0.982 | 0.868 | 6392 | 0.795 |
| r2 | 88.3 | 85.0 | 0.967 | 0.986 | 0.991 | 0.910 | 5992 | 0.731 | 83.2 | 79.9 | 0.909 | 0.970 | 0.982 | 0.868 | 6501 | 0.795 |
| r2c (rescued cited) | 86.1 | 85.0 | 0.967 | 0.986 | 0.991 | 0.839 | 5992 | 0.731 | 80.4 | 79.9 | 0.909 | 0.970 | 0.982 | 0.777 | 6501 | 0.795 |
| r2p | 88.3 | 84.9 | 0.967 | 0.986 | 0.991 | 0.910 | 6029 | 0.731 | 83.2 | 79.9 | 0.909 | 0.970 | 0.982 | 0.868 | 6530 | 0.795 |
| **r2m** (best on S) | **88.3** | 86.0 | 0.967 | 0.986 | 0.991 | 0.910 | 5912 | 0.731 | 83.2 | 81.3 | 0.909 | 0.970 | 0.982 | 0.868 | 6391 | 0.795 |
| r2f | 87.8 | 85.7 | 0.959 | 0.981 | 0.986 | 0.910 | 5888 | 0.731 | 83.2 | 81.2 | 0.909 | 0.970 | 0.982 | 0.868 | 6371 | 0.795 |
| r2mf | 87.8 | 86.0 | 0.959 | 0.981 | 0.986 | 0.910 | 5863 | 0.731 | 83.2 | 81.9 | 0.909 | 0.970 | 0.982 | 0.868 | 6330 | 0.795 |
| g2 | 88.2 | 84.2 | 0.967 | 0.988 | 0.992 | 0.910 | 6237 | 0.731 | 83.1 | 79.1 | 0.909 | 0.977 | 0.991 | 0.868 | 6875 | 0.795 |
| g2m | 88.3 | 85.4 | 0.967 | 0.988 | 0.992 | 0.910 | 6057 | 0.731 | 83.2 | 80.9 | 0.909 | 0.977 | 0.991 | 0.868 | 6637 | 0.795 |
| g2mf | 87.8 | 85.6 | 0.959 | 0.981 | 0.986 | 0.910 | 5920 | 0.731 | 83.2 | 81.5 | 0.909 | 0.970 | 0.982 | 0.868 | 6425 | 0.795 |
| g2mb | 88.3 | 85.2 | 0.967 | 0.984 | 0.988 | 0.910 | 6074 | 0.731 | 83.2 | 80.9 | 0.909 | 0.970 | 0.982 | 0.868 | 6635 | 0.795 |
| lf (strict) | 87.2 | 85.6 | 0.950 | 0.980 | 0.984 | 0.910 | 5855 | 0.731 | 83.2 | 81.6 | 0.909 | 0.962 | 0.973 | 0.868 | 6336 | 0.795 |
| lfm | 87.2 | 85.7 | 0.950 | 0.980 | 0.984 | 0.910 | 5841 | 0.731 | 83.2 | 82.1 | 0.909 | 0.962 | 0.973 | 0.868 | 6297 | 0.795 |
| lf1 | 87.2 | 85.6 | 0.950 | 0.980 | 0.984 | 0.910 | 5849 | 0.731 | 83.2 | 81.7 | 0.909 | 0.962 | 0.973 | 0.868 | 6303 | 0.795 |
| **ab** (abstain only) | 87.2 | 85.7 | 0.950 | 0.980 | 0.984 | 0.910 | 5841 | **0.787** | 83.3 | 82.3 | 0.909 | 0.962 | 0.973 | 0.868 | 6279 | **0.955** |
| g2m_ab | 88.3 | 85.4 | 0.967 | 0.988 | 0.992 | 0.910 | 6057 | 0.787 | 83.2 | 80.9 | 0.909 | 0.977 | 0.991 | 0.868 | 6637 | 0.955 |

Routed (`--route --type multi`; dev 170 q, dev200 45 q; no ssa role hand-off inside this lens, so the ssa misroutes
stay):

| variant | dev S | Sall | PA | CF1 | chars | AUC | dev200 S | Sall | PA | CF1 | chars | AUC |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ref | 83.8 | 82.4 | 0.904 | 0.889 | 5493 | 0.774 | 79.9 | 78.2 | 0.868 | 0.844 | 6137 | 0.763 |
| ab | 83.8 | 82.4 | 0.904 | 0.889 | 5493 | 0.754 | 79.9 | 78.2 | 0.868 | 0.844 | 6137 | 0.850 |
| g2m_ab | 84.5 | 82.0 | 0.917 | 0.889 | 5678 | 0.754 | 79.8 | 76.9 | 0.868 | 0.844 | 6447 | 0.850 |

Abstention, pooled routed dev+dev200 (20 unanswerable questions), TP/flagged at each threshold:

| variant | thr 0.4 | thr 0.5 | thr 0.6 | thr 0.7 |
|---|---|---|---|---|
| ref | 9/15 (rec 0.45) | 5/11 | 2/8 | 1/7 |
| ab | 15/63 (rec 0.75) | 14/41 (0.70) | 10/23 (0.50) | 7/17 |

## Variants tried (one line each)

- `ref`: b_tight p08c35_aor copied into this file (sanity check). Reproduces v1.
- `pin`: every packed unit keeps its best own sentence (bge) through the 240-char trim. Dev-neutral; B's
  `b_r3_full` fact trimming covers the same failure more directly.
- `r2` / `r1`: rescue up to 2 / 1 sessions. A session qualifies when its best own declarative sentence ranks in the top
  len(keep)+2 sessions by bge cosine and lies within 0.15 of the top, and the sentence is not declined or someone
  else's fact. The pinned unit enters right after the first pass; the session is not cited.
  - r2: +1.0 dev, −0.1 dev200; Sall −0.7 / −2.4.
  - Rescue precision: 3 of 94 rescued sessions on dev and 1 of 30 on dev200 are gold.
- `r2c`: as r2, but the rescued sessions are cited. CF1 drops to 0.839 / 0.777, which confirms the low precision.
- `r2m` / `r2mf` / `r2f`: precision gates: the sentence must beat the weakest kept session's best sentence (m) and/or
  carry a fact cue (f). r2m: +1.0 dev, Sall +0.3 dev, −1.0 dev200.
- `g2` / `g2m` / `g2mf` / `g2mb`: the session strength comes from good sentences only (a "considering condos" opener no
  longer vetoes "I viewed a 1-bedroom condo"), plus the best 2 units of each rescued session.
  - The dev200 health-devices question gets its hearing-aid session (SR 1.0, ATR 0.83). PA stays 0 because the
    first gold turn is still missing.
  - The properties question gets the condo session, but the wrong unit (the dense model prefers "I'm looking at
    options for condo" over "I viewed a 1-bedroom condo on February 10th").
  - A +0.05 fact bonus (`g2mb`) did not change this.
- `lf` / `lfm` / `lf1`: strict rescue. The sentence must name a question term AND state an event or quantity. Neutral
  on dev and dev200 S (fires rarely). On test it changes 5 packs, mostly with decoys.
- `ab` / `g2m_ab`: abstain_p = noisy-OR(b_tight abstain_p, sigmoid(20·(0.63 − s_top))).
  - s_top is the best good own sentence's cosine to the question.
  - The parameters were fit on dev, where unanswerable questions have a median of 0.635 against 0.708 for answerable
    ones. dev200 is the holdout.
- `g2mb_h`: g2mb plus the `hint_pass` wording (not measurable offline).
- Not built: the multi_like hand-off. `r3_like.py` on the 98 dev ssu-routed questions gives the gap between the top-1
  and top-3 sessions by best own sentence (min / median / max):
  - gold ssu 0.007 / 0.164 / 0.366
  - gold multi 0.019 / 0.126 / 0.237
  - gold ku 0.001 / 0.179 / 0.330

  The top cosine overlaps just as much (median 0.725 vs 0.695). There is no threshold with 0 FP on gold ssu that
  catches any of the 3 failing multi→ssu questions (poster university, two hobbies, Alex's birth age).

## Top failure patterns

1. **bge-small sentence similarity is topical, not instance-aware.** On dev, the rescued sentences are mostly generic
   first-person chatter that scores as high as gold instance sentences:
   - "I'm looking for some advice on how to organize my closet" (kitchen items)
   - "I've been reading a lot lately" (weddings)

   A sentence-level CE gate does not help either. Gold rescues score CE −8.8 to −10.7, inside the junk range (−6 to
   −11.3; `r3_resc_ce.py`).
2. **Test histories plant decoys right where a rescue looks.** Even the strict `lf` rescue adds:
   - "I attended a one-off watercolour workshop" and the exhibition opening (q_6dd9e5e4fb97, weekly classes)
   - "I bought a 12-volt dial lamp for the National R-77" (q_6834eb0349a2, tubes replaced)
   - "I repotted two orchids last week" (q_47e3f2749c07, orchids added)
   - the watercolour class and a hike, as noise for vegetable varieties (q_eefdc20af97b)

   Only the bakery deposit "opened a separate savings account for the bakery and deposited 25,000 pesos"
   (q_bcd6d210710b) looks like a real missed instance. The round-2 target "I just finished reading a book about the
   history of São Paulo" (q_8b4f1ff8ce11) is rescued by `r2m`, but `lf` misses it, because the prefix-5 stems do not
   match ("books" vs "book").
3. **The remaining dev/dev200 PA losses are within-session unit choice, not session recall.** Once the session is in
   (g2m), the missing piece is a second gold turn of the same session:
   - the first "replacement batteries for my hearing aids" turn
   - the "I viewed a 1-bedroom condo on February 10th" turn

   For Reactor these packs are probably answerable already; PA (ATR == 1) is stricter than the answer needs.
4. **The abstention signal shifts on test.** Test histories have shorter, chattier user sentences, so s_top_good is
   lower. `ab` lifts 5 of 20 test packs to abstain_p ≥ 0.5:
   - feijoada 0.87 (likely truly unanswerable)
   - systolic 0.67, books since March 0.66, field trips 0.59, book club 0.52 (likely answerable)

   Do not use it as an abstention trigger.

## CORE REQUESTs

1. **Sentence-keyed instance index** (`hx.sentences` with own / declarative / negation / reported-speech flags and
   cached CE): every round-3 idea here recomputes this per question. More importantly, a better sentence scorer than
   bge-small (for example CE on question vs statement pairs, batched) is the only way the rescue gets precise.
2. **`harness.failures`: print the rank of each missing gold turn inside its own session**, not only the session. The
   remaining multi losses are now within-session (pattern 3).
3. **An `ATR_any` / "one gold turn per gold session" metric** next to PA for multi. PA requires every gold turn, which
   undercounts packs that Reactor can answer: health devices, properties with g2m.

## Ideas for next round

- Rescue only with an instance-aware scorer: CE on (question rewritten as a statement, sentence) pairs, or a learned
  p(gold) refit with the sentence features B logs (`ufull_fs`). Validate on dev200 and audit for decoys before any
  test change.
- The within-session second unit for kept sessions: take the session's best good sentence unit in addition to the CE
  depth units (targets pattern 3, no new sessions, so Sall-neutral).
- Calibrate `ab` per route on test-like style (dev200 only) before using abstain_p for anything. Keep the term logged.
- Hint: test `hint_pass` in the next Reactor calibration batch, together with B's fact trimming, on the e1 road-trip
  question and on 3 decoy-heavy test-style questions.

---

# (archived) Round 2 report

Lens: `lenses/multi/a_prune.py`. **Best variant: `r2best`**, which is `p8x1_ddl1` plus a calibrated abstain_p (the metrics are identical).
Exported helper: `lenses/multi/a_abstain.py`, with `facet_absence(question, qdate, hx)` and `combine(p, pf)` (brief item 2).
Runs: `runs/r2-multi-a/multi/a_prune/<variant>/{dev,dev200}`, routed runs under `runs/r2-multi-a-route/...`, and the test audit at `runs/audit/multi/a_prune/r2best` (all 20 multi-routed test questions).
Scratch files are in `lenses/multi/scratch_a/`:
- `prune_sim.py` / `prune_miss.py` simulate pruning rules offline on B's r1 packs.
- `outside_core.py` / `extra_rules.py` compute features of gold sessions that fall outside the CE core.
- `gap_sim.py` refits the core rule offline.
- `test_inst.py` lists the instance sentences of a test question with their strength and whether they made the pack.
- `show_dropped.py` prints the decoy sessions the lens dropped on test.

The lens is built on B by import, as the brief asked. B's retrieval, CE scoring, unit selection, rendering, hint and cite rule are reused unchanged, so the caches are shared. `b_ref` is B `deep8_10k` run through my file and reproduces B exactly.

## Headline

The pack shrinks to the sessions near the cite set, as brief item 1 asked:
- Passages per question fall from 8.1 to 4.4 on dev, from 8.2 to 4.9 on dev200, and from 11.7 to 7.3 on test.
- Chars fall from 9.9k to 6.5k on dev and 7.6k on test.
- If Reactor cites every passage, **Sall rises by +10.1 on dev and +5.4 on dev200**.
- S (cite_plan) is +0.6 on dev and **−2.0 on dev200**. The dev200 loss is one question out of 22; see failure 1.

On the routed system (questions routed to multi, mixed gold types), S is +0.4 / −0.7 and Sall +10.2 / +8.4.

## Results (gold type = multi; dev 133 q / 121 answerable, dev200 28 q / 22 answerable)

| split | lens / variant | S | Sall | PA | ATR | SR | ALL | CF1 | CF1all | chars | AUC |
|---|---|---|---|---|---|---|---|---|---|---|---|
| dev | generic hybrid_rr (r2-multi-b run, reused) | 69.1 | 69.1 | 0.744 | 0.873 | 0.961 | 0.893 | 0.817 | 0.817 | 11931 | 0.598 |
| dev | B deep8_10k (`b_ref`) | 86.6 | 73.9 | 0.967 | 0.989 | 0.994 | 0.984 | 0.896 | 0.473 | 9949 | 0.644 |
| dev | `p8x1` (prune only) | 87.1 | 82.4 | 0.959 | 0.986 | 0.990 | 0.975 | 0.896 | 0.739 | 6840 | 0.644 |
| dev | `p8x1_dd` (+ decoy drop + facet abstain) | 87.1 | 82.4 | 0.959 | 0.986 | 0.990 | 0.975 | 0.896 | 0.739 | 6850 | 0.731 |
| dev | **`r2best` = `p8x1_ddl1`** | **87.2** | **84.0** | 0.959 | 0.986 | 0.990 | 0.975 | 0.896 | 0.790 | 6495 | 0.731 |
| dev | `p8x1_ddl15` (Sall-leaning) | 86.8 | 84.7 | 0.950 | 0.980 | 0.986 | 0.967 | 0.896 | 0.826 | 6131 | 0.731 |
| dev200 | generic hybrid_rr (r2-multi-b run, reused) | 63.7 | 63.7 | 0.682 | 0.844 | 0.950 | 0.864 | 0.770 | 0.770 | 11947 | 0.689 |
| dev200 | B deep8_10k (`b_ref`) | 85.2 | 73.5 | 0.955 | 0.985 | 0.991 | 0.955 | 0.874 | 0.487 | 9951 | 0.833 |
| dev200 | `p8x1` | 83.1 | 78.2 | 0.909 | 0.962 | 0.973 | 0.909 | 0.874 | 0.713 | 7409 | 0.833 |
| dev200 | `p8x1_dd` | 83.1 | 78.2 | 0.909 | 0.962 | 0.973 | 0.909 | 0.874 | 0.713 | 7409 | 0.795 |
| dev200 | **`r2best` = `p8x1_ddl1`** | **83.2** | **78.9** | 0.909 | 0.962 | 0.973 | 0.909 | 0.874 | 0.734 | 7204 | 0.795 |
| dev200 | `p8x1_ddl15` | 83.2 | 80.1 | 0.909 | 0.962 | 0.973 | 0.909 | 0.874 | 0.768 | 6892 | 0.795 |

Routed (`--route --type multi`: dev 158 q, dev200 42 q):

| split | variant | S | Sall | PA | CF1 | CF1all | chars | AUC |
|---|---|---|---|---|---|---|---|---|
| dev | `b_ref` | 82.6 | 69.7 | 0.918 | 0.868 | 0.438 | 9944 | 0.668 |
| dev | **`r2best`** | **83.0** | **79.9** | 0.904 | 0.871 | 0.769 | 6061 | 0.758 |
| dev200 | `b_ref` | 79.5 | 67.2 | 0.886 | 0.835 | 0.425 | 9954 | 0.767 |
| dev200 | **`r2best`** | **78.8** | **75.6** | 0.857 | 0.835 | 0.727 | 6518 | 0.763 |

The last change (named-subject decoys) left every dev and dev200 number unchanged; the tables are from the final code.

Effect on the whole routed system, scaled by the share of questions routed to multi:
- dev: S +0.1, Sall +3.1
- dev200: S −0.2, Sall +2.8

I did not re-run the generic baseline. Agent B had already run it under tag r2-multi-b, and running it twice would double the load on the shared server (a round-1 lesson).

**Against the acceptance rule** (S ≥ +2 on dev, no loss on dev200, at most −2 on Sall):
- `r2best` does not pass on S. It gains +0.6 on dev and loses 2.0 on dev200, which is one question.
- It is a large Sall win: +10.1 on dev and +5.4 on dev200.
- If citations are not post-filtered, `r2best` is the clear choice. If they are, it is a tie with fewer chars (−3.4k) and a better AUC on dev.

## Variants tried (one line each; dev S / Sall, dev200 S / Sall)

1. `b_ref`: B deep8_10k through this file, the sanity check. 86.6 / 73.9, 85.2 / 73.5.
2. `p8x1`: core = sessions within 8 CE logits of the best (2 to 20) + the next session. 87.1 / 82.4, 83.1 / 78.2.
3. `p6x1`, `p7x1`, `p9x1`, `p10x0m3`, `p8x2`, `p8x1m3`: other bands, mins and extras. 85.1–87.3 / 79.9–82.4 on dev; D=8 with one extra is the sweet spot. `p8x2` keeps PA 0.967 on dev but Sall is 79.9.
4. `p8x1_f`: + facet-absence abstention (noisy-OR). AUC 0.644 → 0.731 on dev, 0.833 → 0.795 on dev200, **0.689 → 0.739 pooled**.
5. `p8x1L3`, `p6x1L3`: extra recall sessions by lexical hit (match_score ≥ 3, up to 3). No PA gain; Sall −0.4 / −1.6.
6. `p8x1_do`: + **drop decoy sessions** (strongest units all report another person's fact). Dev-neutral by construction (dev gold has no such decoys). On test it drops 5 correct decoys (Valentina's tango shoes, sister Paola's bakery fund, Carlos's and the brother's grandchildren, Carlos's systolic 145).
7. `p8g4x1`, `p8g5x1`, `p12g4x0`, `p10x0`: also cut the core at a big drop in strength. Dev PA falls (0.90–0.94). Rejected.
8. `p8x1c4`, `p8x1c5`: the recall slot only when the core has fewer than 4 or 5 sessions. On gold type +0.2 / +0.8 Sall, but routed dev200 S is −1.8. Rejected.
9. `p8x1c4s` (sentence-level CE strength, 40 q): −1.6 S and −2.6 Sall. Question-like chatty sentences inflate the core. Rejected.
10. `p8x1_dd`: + **drop declined sessions**. The unit's main topical sentence is "decided not to / skipped buying / did not use it", and no other topical sentence affirms an instance. Dev-neutral. On test it drops 4 more correct decoys: 2 declined tango-shoe buys, a dulce de leche "test batch, didn't use it for any order", and an R-77 tube "did not use it".
11. **`p8x1_ddl1`**: the recall slot only goes to a session sharing the question's topic words (match_score ≥ 1). Offline this kept 15 of 15 gold recall sessions and removed 35% of non-gold ones. 87.2 / 84.0, 83.2 / 78.9. **Best.**
12. `p8x1_ddl15` (threshold 1.5): 86.8 / 84.7, 83.2 / 80.1. Trades 0.4 S for about 1 Sall. This is the alternative if Sall decides.
13. `p8x1_ddl1s2` (scan the next 2 sessions for the slot): 87.1 / 83.4. No gain.
14. `p8x1_led`: **code-side ledger note** in the hint (brief item 3), one "[E#] date: best own sentence" line per passage (CE + fact-cue bonus). 86.5 / 81.8: the 1.5k chars reserved for the ledger cost one question.
    - On dev the ledger often picks the wrong sentence: "great list of questions to ask my doctor", and only 2 of 4 health devices.
    - It would anchor Reactor on an incomplete list. **Not recommended** without a Reactor spot check.
    - Decoy filtering went into the pack instead (items 6 and 10).
15. `p8x1_se2`: sentence-CE recall of buried instance sentences (lexical hit ≥ 2.5, own, declarative). 87.2 / 83.9, 83.2 / 78.9, so dev-neutral. On test it mostly added noise (Python chat for "used car savings"), and the target case was still squeezed out by the budget. Not adopted.
16. `r2best`: `p8x1_ddl1` plus a monotone calibration of abstain_p to P(unanswerable). It is fit on routed dev+dev200 multi questions pooled, as isotonic bins: <0.2: 6/155, 0.2–0.3: 3/25, 0.3–0.4: 2/6, ≥0.4: 8/14. The ranking, and so the AUC, is unchanged.

## Test audit (all 20 multi-routed test questions, `runs/audit/multi/a_prune/r2best`)

| | passages | chars | cite_plan | decoys dropped |
|---|---|---|---|---|
| B deep8_10k (b_ref) | 11.7 | 9947 | 3.1 | 0 |
| `r2best` | 7.3 (2–14) | 7624 | 3.0 | 12 sessions in 8 questions; all were inspected with `show_dropped.py` and all are real decoys |

- **Tango shoes:** all 3 own purchases are in the pack (1,800 / 2,400 / 2,000 pesos). Dropped: friend Valentina's purchase, "tried on … decided not to buy", "skipped buying".
- **Dulce de leche:** the 5 kg birthday and 3 kg anniversary orders are kept. Dropped: the "test batch, didn't use it for any order" and "Valentina made 7 kilos" (a named-subject pattern I added last; dev-neutral).
- **Systolic > 130 in August:** 7 passages. They hold the "My systolic reading was 132 / 135 / 128" sessions plus a recap of 131. "Carlos told me his systolic reading was 145" is dropped.
- **Feijoada last month** (flagged, abstain_p 0.58): the user never eats it; only Carlos and the brother do. The pack is 2 sessions, and the brother's session is dropped. "Carlos told me he ate feijoada twice" stays in, because another unit of that session scores within 2 logits. The likely right answer is 0 or insufficient.

## Top failure patterns

1. **An instance session with weak CE falls outside the core.** This is the only dev200 loss and the one extra dev loss against B.
   - "How many properties did I view before making an offer on the townhouse in the Brookside neighborhood?" has 5 gold sessions with CE 4.1, 1.5, −3.2, −9.5 and −10.3. "I've seen some properties … like that one in Cedar Creek on February 1st" sits 14 logits below the top. No non-CE feature separates it: its fused rank, number of units in the top 40, and lexical score all look like those of non-gold sessions.
   - I also tried the statement-form CE ("I view … properties"): the gold sessions still score −9.6 and −10.8.
2. **Category → instance gaps** (inherited from B; B also misses them):
   - "How many projects have I led": the gold says "participated in a case competition" and "presented a poster".
   - "How many health-related devices": the hearing-aids unit is not picked; it ranks 5th inside its own session.
3. **Test: an instance sentence buried in a chatty unit gets unit-level CE ≈ −11.** In "How many books have I read since March?", "I'll check the roots today. I just finished reading a book about the history of São Paulo" is in neither B's pack nor mine. The core is 14 chatty book sessions (top strength −6.5), and the budget is spent on them. `sent_extra` finds such sentences, but it needs a pinned slot (see the next round).
4. **Test CE is flat on 200-session histories.** Several questions fill the cap of 14 core sessions: ceramic pieces (11 passages), watercolour classes (10–11), orchids (13), phone calls with my daughter (14). The Sall gain on test will be smaller than on dev.
5. **Abstention:**
   - Gold type pooled: at abstain_p ≥ 0.4, precision 7/7 at recall 0.39.
   - Routed pooled: 8/14 (0.57) at recall 0.42. That is below the re-enable rule (precision ≥ 0.7 at recall ≥ 0.4), so no abstention hint is added.
   - The hint is B's unchanged; I added no new abstention text.
   - Misses: "museums in December" (dev windows never engage), "Sapiens" pages left, "Rachel's age at my wedding" (role swap).

## CORE REQUESTs

1. **Decide the citation policy** (cite_plan post-filter or Reactor's own [E#]). For multi it decides between `r2best`, a tie on S and +10 on Sall, and B deep8_10k. If the organisers' FAQ shows whether Reactor cites only the passages it uses, CF1all could be replaced by a better proxy.
2. `build_pack` / `_select` priority for **pinned sentence-level instances**: a pinned unit rendered as just its instance sentence (about 150 chars). This would let a buried fact ("I just finished reading a book about …") enter a budget-bound pack ahead of chatty depth units. B's `_pack_trimmed` renders whole trimmed units.
3. `harness.failures`: print the session-strength rank of each MISSING gold session (my lens saves `debug.strength`, `debug.core` and `debug.extra`). This is the diagnostic that explained failure 1.
4. Summary: add `passages_mean` to summary.json and leaderboard.csv. It drives Sall directly and is now a primary knob.

## Ideas for the next round

- **Pinned instance sentences** (needs CORE REQUEST 2, or a local renderer). Use `sent_extra` (lexical ≥ 2.5, own, declarative, not declined), scored with sentence-level CE against a sentence-level top, not the unit-level top, so the scales match. Pin the sentence ahead of the core's depth units. This targets failure 3, which is test-specific.
- **Test-adaptive core.** When more than 8 sessions sit within 4 logits of the top (flat CE, typical on test), require a lexical instance hit for core membership. This shrinks the 11–14 passage test packs. Dev never triggers it, so it can only be audited.
- **B + A abstention.** Add the conjunct and pair checks for the words B's `missing_terms` ignores. "pair-absent" fires on scaffolding pairs ("read exceed", "up replac", "veget varieti"); a scaffolding stop list for verbs (exceed, end up, varieties) would remove that noise on test.
- **Ledger:** only after a Reactor spot check. The decoy filtering it was meant to provide is now done by dropping sessions, which costs no chars and needs no extra reading from Reactor.
