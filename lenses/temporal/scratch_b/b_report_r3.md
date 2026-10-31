# Temporal lens B ("Semantyka"): round 3 report

Code: `lenses/temporal/b_r3_merge.py`. It wraps the frozen v1 temporal route (`merged_r2.py` evA_mixB: a_gap ct_evgba for
gap and named-event questions, b_merge ev1_mix_g for the rest) and imports the frozen files without editing them.
`base` reproduces evA_mixB exactly: 81.3 / 83.7, the same numbers as `merged_r2` in this run.
Runs: `runs/r3-temporal-b/temporal/b_r3_merge/<variant>/{dev,dev200}`; routed runs are in `runs/r3-temporal-b/temporal-routed/`.
Round-2 report: `scratch_b/b_report_r2.md`.
Diagnostics in `scratch_b/`:
- `sub3.py`: metrics per source route.
- `diag3.py`: gold-session rank, pack and cite membership, and whether the gold turn is included.
- `floor3.py`: score floors for trimming the whole-question route.
- `cite3.py`: grid of cite rules.
- `agree_test.py`: on test, A's computed gap against B's independent computation.

Test audits: `scratch_b/audit_r3_base.txt` and `scratch_b/audit_r3_hk6.txt`.

## Where the loss is (v1 = base, dev, answerable, by source route)
| subset | n | S | Sall | PA | ALL | ATR | CF1 | passages |
|---|---|---|---|---|---|---|---|---|
| A gap | 36 | 90.1 | 89.4 | 0.972 | 0.972 | 0.986 | 0.956 | 2.3 |
| A ago | 17 | 91.3 | 90.0 | 1.000 | 1.000 | 1.000 | 0.922 | 1.6 |
| A order ("which first") | 31 | 82.7 | 80.2 | 0.871 | 0.968 | 0.957 | 0.951 | 2.8 |
| B whole-question (no events) | 39 | 69.7 | 60.7 | 0.821 | 0.897 | 0.915 | 0.651 | 13.8 |
| dev200 B whole-question | 7 | 63.6 | 54.2 | 0.714 | 0.714 | 0.857 | 0.676 | 15.4 |

**Test is different.** The 36 temporal-routed test questions are 35 gap questions plus "how many years did I serve as a
firefighter". A computes 32 of the 35 gaps. B's own routes (whole-question and order) never fire on test, so B can only
add value on test through the gap fallback.

## Variants tried (one line each)
| variant | idea / params |
|---|---|
| `base` | v1 temporal route (merged_r2 evA_mixB), reference. |
| `agree` | Brief item 1. Gap fallback by agreement: A withheld its value on its plain confidence gate, and its raw value equals B's independent event-route value (±1). The first version also fired on A's `rounding` gate (weeks) and emitted a wrong 12, so it is now limited to gate None. Dev: 1 firing (tennis racket = 1, correct). Test: 0 firings, because Montreal = 45 is already emitted by A in v1. |
| `fbg` | b_merge's guarded fallback whenever A has no value. Dev: no change. |
| `head2` / `head3` | Whole-question route: the user units of the cited sessions are CE-scored one by one (+1.5 for "today / just / yesterday" when the question has a relative anchor), and their top 2 (or 3) units enter the pack first. Route ATR 0.915 -> 0.940. |
| `head2_c2` | Brief item 2. The whole-question pack is capped at len(cite) + 2 sessions. **Rejected**: dev PA 0.898 -> 0.835 and Sall goes down too (75.8). |
| `ord` | Brief item 3. Order questions: user units of the packed sessions whose CE against the event phrase is >= -3 are pinned. 0 PA change: CE scores of the missed gold turns are -7 to -11. |
| `ords` | Same, at sentence level (hx.rerank_texts per sentence, the unit takes its best sentence). 0 PA change. |
| `ordf` | Order questions: the opening user unit of every packed session is pinned (dev gold turns are mostly the opening turn). +1 PA ("bus or train"). |
| `r3` | agree + head3 + ordf. |
| `r3_b8` / `r3_b7` | r3 with a whole-question budget of 8k / 7k. **Rejected**: dev S -1.8 / -4.3 (category-mates fall out). |
| `r3_div` / `r3_div2` | + diversity: the best unit of every session before any second unit. **Rejected**: ALL goes up, ATR 0.969 -> 0.932. |
| `h3s` | Plain-CE ranking on the question with its time phrase stripped ("... 5 days ago" removed). **Rejected**: ALL 0.937. |
| **`r3_hk6`** | r3 + heads also for the next sessions of the time-prior ranking, up to 6 sessions. **Best.** |
| `r3_hk8` / `r3_hk8p2` | Heads for 8 sessions. The heads eat the budget and ALL falls (80.7). |
| `r3_hk6d` | r3_hk6 + diversity for 10 sessions. 81.7. |
| `r3_hk6_b12` | r3_hk6 with a 12k whole-question budget. ALL 0.953, but S 82.5 (chars). |

## Results (all temporal questions by gold type; dev 133 q / 127 answerable, dev200 26 q / 22 answerable)
| split | variant | S | PA | ATR | SR | CF1 | chars | AUC | Sall |
|---|---|---|---|---|---|---|---|---|---|
| dev | generic hybrid_rr | 65.1 | 0.748 | 0.860 | 0.908 | 0.673 | 11931 | 0.636 | 65.1 |
| dev | v1 = merged_r2 evA_mixB = `base` | 81.3 | 0.898 | 0.957 | 0.980 | 0.843 | 7562 | 0.839 | 77.6 |
| dev | agree (*) | 80.7 | 0.890 | 0.953 | 0.976 | 0.842 | 7558 | 0.839 | 77.0 |
| dev | head3 | 81.2 | 0.898 | 0.961 | 0.976 | 0.842 | 7557 | 0.839 | 77.7 |
| dev | head2_c2 | 77.4 | 0.835 | 0.938 | 0.943 | 0.840 | 6734 | 0.839 | 75.8 |
| dev | ordf | 81.7 | 0.905 | 0.961 | 0.980 | 0.840 | 7682 | 0.839 | 78.1 |
| dev | r3 | 82.2 (rerun 81.7) | 0.913 | 0.969 | 0.980 | 0.840 | 7681 | 0.839 | 78.8 |
| dev | r3_b8 | 80.4 | 0.882 | 0.962 | 0.970 | 0.842 | 7054 | 0.839 | 77.5 |
| dev | r3_div | 79.2 | 0.866 | 0.932 | 0.983 | 0.842 | 7666 | 0.839 | 74.4 |
| dev | **r3_hk6** | **82.7 (rerun 82.2)** | 0.921 | 0.979 | 0.976 | 0.840 | 7681 | 0.839 | **79.5 (79.0)** |
| dev | r3_hk8 | 80.7 | 0.890 | 0.971 | 0.968 | 0.842 | 7671 | 0.839 | 77.5 |
| dev | r3_hk6_b12 | 82.5 | 0.921 | 0.979 | 0.980 | 0.840 | 8297 | 0.839 | 78.7 |
| dev200 | generic hybrid_rr | 61.2 | 0.727 | 0.849 | 0.910 | 0.589 | 11941 | 0.932 | 61.2 |
| dev200 | v1 = `base` | 83.7 | 0.909 | 0.955 | 0.968 | 0.897 | 7453 | 0.966 | 77.3 |
| dev200 | head3 / ordf / r3 | 83.7 | 0.909 | 0.955 | 0.968 | 0.897 | 7444-7597 | 0.966 | 77.2-77.5 |
| dev200 | r3_b8 / r3_b7 | 83.9 / 84.0 | 0.909 | 0.955 | 0.968 | 0.897 | 6903 / 6555 | 0.966 | 78.6 / 79.4 |
| dev200 | **r3_hk6** | **83.7** | 0.909 | 0.955 | 0.968 | 0.897 | 7594 | 0.966 | **77.7** |

(*) This `agree` row is the noisy run (below). Against base, the gate-None `agree` changes only one dev question
(tennis racket, computed 1, correct).

Routed (`--route --type temporal`), S / Sall:

| split | base | r3 | r3_hk6 |
|---|---|---|---|
| dev (144 q) | 82.3 / 77.4 | 83.2 / 78.4 | 83.2 / 78.7 |
| dev200 | 83.7 / 77.4 | - | 83.6 / 77.6 |

Per subset, r3_hk6 against base (dev):
- Whole-question route: S 69.7 -> 73.1, Sall 60.7 -> 65.3, ATR 0.915 -> 0.974, ALL 0.897 -> 0.872.
- Order route: S 82.7 -> 84.7, PA 0.871 -> 0.903, chars 7.7k -> 8.1k.
- Gap and ago routes: unchanged.

On dev200 nothing moves on S. Its two failures are category-mates outside the pack.

**Run-to-run noise.** The same lens and variant varies by about ±0.5 S on dev between runs (ALL 0.953 / 0.945 / 0.937).
Example: in one full run, "Who became a parent first, Rachel or Alex?" flipped from PA 1 to 0 under `agree`, a variant
that does not touch it; run alone with `--qfilter`, it scores PA 1 in both variants. So differences under about 1 S are
noise (CORE REQUEST 1).

## Best variant and decision
`lenses/temporal/b_r3_merge.py:r3_hk6`. Against v1:
- dev: +0.9 to +1.4 S, +1.4 to +1.9 Sall.
- dev200: tie (83.7), +0.4 Sall.
- routed dev: +0.9 S, +1.3 Sall. Routed dev200: tie.
- `harness.audit --compare`: **0 of 36 test temporal packs change**.

It **does not meet** the +2 S acceptance rule. Because the test packs are identical, swapping it into configs/best.json
would change nothing that Reactor sees. Recommendation: keep v1 for the test pass. Take r3_hk6 (or its two parts,
`oq_head`+`head_k` and `ord_first`) only if a later dev-scored system matters.

Brief items:
1. **Agreement fallback.** Implemented with a gate-None restriction; the rounding gate must stay closed, see above. On
   test it has nothing to do: Montreal = 45 is already emitted by A in v1.
2. **Trimming the whole-question route towards its cite set.** Measured and **rejected**: cap len(cite)+2 gives -3.9 S
   and -1.8 Sall on dev; budget 8k/7k gives -1.8 / -4.3 S. `floor3.py` shows why: on dev, keeping 98/109 gold sessions
   with any score floor also keeps 266/392 non-gold sessions. The gold sets of these questions include same-category
   sessions 6-17 logits below the top (pattern 1). The cite grid (`cite3.py`) is flat at CF1 about 0.64 for every rule
   of top-k by the time-prior ranking plus top-k by plain CE.
3. **Sentence-level CE for the second gold turn of "first" questions.** Implemented (`ords`); no gain. The missed gold
   turns score -7 to -11 against the event phrase ("upgraded my home Wi-Fi router 3 weeks ago" for "the mesh network
   system"). The opening-turn pin (`ordf`) recovers 1.
4. **"ago" with an explicit date.** Already handled in v1: those questions go to A's ago route (dev A:ago PA 1.000).

## Test audit (qualitative, all 36 temporal-routed test questions)
- **0 packs change** between base and r3_hk6 (`audit --compare`). Flags: 4, unchanged from v1 (firefighter years,
  trail-running shoes, vaccines, sourdough loaf).
- **Cross-check of A's computed values** (`scratch_b/agree_test.py`): B's event route recomputes all 35 gap questions
  independently.
  - Of the 32 values A emits, B agrees on 28, disagrees on none and abstains on 4 (below its margin gate). Reading those
    4 packs suggests A's pick is right or the two match:
    - Toronto Marathon -> Moroccan family dinner: A uses the explicit "On 2023-06-28, I cooked a Moroccan lamb tagine
      for our big family dinner" (73). B is torn by a later plan, "I'm hosting a big Moroccan dinner for my family on
      Sunday" (07-05 session).
    - Cake tasting: A takes "the cake tasting appointment for your daughter's wedding is on 2023-09-12" (7). B's
      runner-up is the decoy "for your colleague Jan's daughter on 2023-09-15".
    - Arezzo -> Uffizi (46) and wife's birthday -> anniversary (50): B's picks have the same dates as A's.
  - A withholds 3 gap questions:
    - Trail run: only "Camille bought trail-running shoes". B: none.
    - Vaccines: "I still need to sort out my travel vaccines". B: none.
    - Sourdough loaf: no "loaf" anywhere. **B "agrees" with A's raw 58**, but both come from the same garbage picks
      (r2 audit: a "Sourdough croissants" assistant sentence and a meatloaf recipe). A's gate here is `sign`. This is
      why `agree` fires only on gate None: agreement of two pickers on the same wrong sentences is no evidence.

    All three look unanswerable, which is temporal-A's r3 `own` target.

## Top failure patterns (dev, r3_hk6)
1. **Whole-question route: same-category gold sessions far below the anchor session.** These are the remaining PA
   failures on dev200 and most of them on dev. In each case one gold session is never in the pack:
   - "Who did I go with to the music event last Saturday?" (dev200): 5 gold Saturday sessions. s_88e91b1b31f3
     (03/18) is not in the pack; one more is in the pack but not cited.
   - "I mentioned participating in a sports event two weeks ago": gold s_954e7ec708ab (06/10).
   - "the life event of one of my relatives ... a week ago": the wedding session s_97bb9b349bdc (05/06), six weeks before the anchor.

   A budget or session cap cannot separate these from decoys (`floor3.py`).
2. **Gold turn in a non-cited session that is not the session's best unit.** For "What was the social media activity I
   participated 5 days ago?", the gold turn is "I shared a recipe for vegan chili using #FoodieAdventures yesterday",
   in the 03/10 session, a category-mate. head_k 6 recovers some of these; head_k 8 eats the budget.
3. **Order questions where the second gold turn is a paraphrase in a later turn.** Examples: "upgraded my home Wi-Fi
   router 3 weeks ago" for "the mesh network system", and "visiting the Galapagos ... as a solo traveler" for "the
   solo trip to Thailand". The CE against the event phrase is -7 to -11, and the turn is not the session opener.
   A related case: "Which group did I join first, 'Page Turners' or 'Marketing Professionals'?" has a 3rd gold session
   (another mention) that A's 2-session pack never retrieves (ALL 0).

## CORE REQUESTs
1. **Determinism.** Identical code gives ±0.5 S between full runs: one full dev run flips "Who became a parent first,
   Rachel or Alex?" to PA 0, while the question run alone gives PA 1. A likely cause is CE / dense scores that depend on
   batch composition in the shared model server, combined with tie-sensitive budget packing. Possible fixes: round CE
   scores to 1e-3 before caching, and break ties on uid. Until then, acceptance decisions need either a rerun or a
   margin above 1 S.
2. `harness.audit --n` limits the number of questions, and the default 12 hides most of the pack diff. Make
   `--compare` diff every routed test question regardless of `--n`, or print that the diff is partial. I ran it with
   `--n 200`.
3. No config change requested for v1. The test temporal packs are identical under r3_hk6.

## Ideas for next round
- Two-pool whole-question packs: (a) the anchor session with all its user turns, (b) category-mates found by a
  category query rather than the question. One example: an LLM-free "category noun" extraction ("sports event",
  "social media activity", "life event of a relative") -> hybrid over user units with that phrase, and one best unit per
  session. The gold sets list every session of the category, so (b) needs its own recall budget (about 5k chars), not
  leftovers from (a).
- Order questions: pin every user unit of the event sessions that shares a rare token with the event (df-weighted,
  "Wi-Fi router" ~ "mesh network" needs a synonym step, maybe dense_texts against the event phrase with a floor),
  instead of the CE threshold.
- The test is gap-dominated (35/36), so the remaining test risk is A's 32 computed values. The B cross-check finds 0
  disagreements. A cheap safety net: when A and B disagree by more than 1 day on a test-like question, keep A's value
  and add B's picks to the hint as "other mention". This needs dev data with disagreements to calibrate; on test it
  would fire 0 times today.
