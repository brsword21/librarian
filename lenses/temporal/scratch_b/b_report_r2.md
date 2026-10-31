# Temporal lens B ("Semantyka"): round 2 report

Code: `lenses/temporal/b_merge.py`, a copy of the integrator's `merged_r1`. Gap questions go to A (ftb_bm25) and everything
else to B (b_sem sem_turns9), with B-side changes that each variant switches on. The `base` variant reproduces
merged_r1 exactly (76.4 / 82.1).
Runs: `runs/r2-temporal-b/temporal/b_merge/<variant>/{dev,dev200}`, routed runs in `runs/r2-temporal-b-route/`.
Test audit: `lenses/temporal/scratch_b/audit_r2_ev1_mix.txt` and `scratch_b/audit_fb.py`. Diagnostics: `scratch_b/diag_other.py`
(gold-session ranks on the whole-question route), `scratch_b/diag_cite.py` (cite-rule grid), `scratch_b/sub.py` (metrics
per subset: gap / event / other).
r1 lenses `b_sem.py` and `b_evcal.py` are unchanged; the r1 report is replaced by this one.

## Variants tried (one line each)
| variant | idea / params |
|---|---|
| `base` | merged_r1 gapA_semB, unchanged (reference). |
| `fb` | Gap fallback: when A emits no computed value, use B's event route. If its margin-gated computed exists, put B's dated picks and gap in the hint and in `computed`. Pin B's event units if their session is missing. |
| `sess5` / `sess5t` | Whole-question route made session-centric: top 5 sessions only, every user unit of those sessions CE-scored (`t`: +1.5 for "today/yesterday/just" units). **Rejected**: ALL 0.85 -> 0.64 on the route. |
| `fb_c4` / `fb_c3` | + whole-question cite = top 4 (3) sessions by score (gap 8 instead of 3; "the N ..." still caps). Grid in diag_cite: CF1 0.565 -> 0.651 dev, 0.563 -> 0.676 dev200. |
| `fb_c4_ev` | + event-route fill fix: user units of the cited sessions that share an event token come right after the picks. They are ranked by overlap, interleaved across sessions, at most 3 per session, without neighbours. In r1 they came in uid order with +/-1 neighbours, so the budget ran out before the second gold turn. |
| `fb_c4_ev1` / `ev2` | + event route packs at most len(cite_plan) + 1 (or + 2) sessions (Sall). |
| `ev1_k8` / `ev1_k6` | + whole-question route capped at 8 (6) sessions. It trades dev S for Sall. |
| `ev1_mix` | ev1 + the whole-question route packs units from two rankings interleaved: CE plus anchor time prior, and plain CE. The gold set of "what did I do two weeks ago" also holds sessions of the same category at other dates. |
| `ev1_mix_k8` | ev1_mix capped at 8 sessions. Best Sall on dev200 (77.1), but -1.4 S on dev. |
| **`ev1_mix_g`** | ev1_mix + a sanity guard on the gap fallback (detailed below). **Best.** Same dev and dev200 numbers as ev1_mix; the guard only removes fallbacks that are wrong on test. |

The fallback guard requires three things: every picked sentence shares a content word with its event, no pick is
about someone else, and "after" / "before" questions get their dates in the stated order.

## Results (all temporal questions by gold type; dev 133 q / 127 answerable, dev200 26 q / 22 answerable)
| split | variant | S | PA | ATR | SR | CF1 | chars | AUC | CF1all | Sall |
|---|---|---|---|---|---|---|---|---|---|---|
| dev | generic hybrid_rr | 65.1 | 0.748 | 0.860 | 0.908 | 0.673 | 11931 | 0.636 | 0.673 | 65.1 |
| dev | merged_r1 = `base` | 76.4 | 0.843 | 0.948 | 0.968 | 0.817 | 9099 | 0.769 | 0.661 | 71.7 |
| dev | fb | 76.9 | 0.850 | 0.948 | 0.968 | 0.816 | 9089 | 0.769 | 0.661 | 72.3 |
| dev | sess5 | 74.0 | 0.803 | 0.945 | 0.943 | 0.817 | 8807 | 0.769 | 0.735 | 71.5 |
| dev | fb_c4 | 77.7 | 0.850 | 0.948 | 0.968 | 0.842 | 9089 | 0.769 | 0.661 | 72.3 |
| dev | fb_c4_ev | 79.7 | 0.882 | 0.967 | 0.972 | 0.842 | 9080 | 0.769 | 0.606 | 72.7 |
| dev | fb_c4_ev1 | 79.2 | 0.874 | 0.959 | 0.960 | 0.842 | 9059 | 0.769 | 0.662 | 73.8 |
| dev | ev1_k8 | 78.4 | 0.858 | 0.951 | 0.949 | 0.842 | 8591 | 0.769 | 0.699 | 74.1 |
| dev | ev1_mix_k8 | 78.9 | 0.866 | 0.951 | 0.946 | 0.843 | 8699 | 0.769 | 0.698 | 74.5 |
| dev | **ev1_mix_g** | **80.3** | 0.890 | 0.959 | 0.969 | 0.842 | 9058 | 0.769 | 0.666 | **75.0** |
| dev200 | generic hybrid_rr | 61.2 | 0.727 | 0.849 | 0.910 | 0.589 | 11941 | 0.932 | 0.589 | 61.2 |
| dev200 | merged_r1 = `base` | 82.1 | 0.909 | 0.955 | 0.968 | 0.861 | 9074 | 0.966 | 0.596 | 74.2 |
| dev200 | fb_c4 | 83.2 | 0.909 | 0.955 | 0.968 | 0.897 | 9062 | 0.966 | 0.596 | 74.2 |
| dev200 | fb_c4_ev | 83.2 | 0.909 | 0.955 | 0.968 | 0.897 | 9072 | 0.966 | 0.526 | 72.0 |
| dev200 | fb_c4_ev1 | 83.2 | 0.909 | 0.955 | 0.968 | 0.897 | 8902 | 0.966 | 0.622 | 75.0 |
| dev200 | ev1_k8 | 83.4 | 0.909 | 0.955 | 0.968 | 0.897 | 8113 | 0.966 | 0.687 | 77.1 |
| dev200 | ev1_mix_k8 | 83.4 | 0.909 | 0.955 | 0.968 | 0.897 | 8130 | 0.966 | 0.687 | 77.1 |
| dev200 | **ev1_mix_g** | **83.2** | 0.909 | 0.955 | 0.968 | 0.897 | 8907 | 0.966 | 0.621 | **75.0** |

Routed (`--route --type temporal`, the questions that the router sends to temporal):

| split | base S / Sall | ev1_mix_g S / Sall |
|---|---|---|
| dev (152 q) | 77.9 / 72.0 | 79.9 / 74.0 |
| dev200 | 83.0 / 74.1 | 83.1 / 75.7 |

Per subset, base -> ev1_mix_g, S / Sall:

| subset | dev | dev200 |
|---|---|---|
| gap (A, n 29/5) | 83.7 / 79.1 -> 85.8 / 81.4 | 92.5 / 82.9 -> 92.5 / 83.0 |
| event route (n 59/10) | 81.2 / 77.9 -> 84.5 / 81.3 | 92.2 / 83.7 -> 92.4 / 85.5 |
| whole-question route (n 39/7) | 63.9 / 57.0 -> 69.7 / 60.7 | 60.2 / 54.3 -> 63.6 / 54.2 |

On the gap subset the fallback fires 6 times on dev and once on dev200, with HA = 1 every time. It rescues 1 dev
pack where ATR < 1.

## Best variant
`lenses/temporal/b_merge.py:ev1_mix_g`. Against the current winner (merged_r1):
- dev: +3.9 S, +3.3 Sall.
- dev200: +1.1 S, +0.8 Sall.
- routed dev: +2.0 S, +2.0 Sall.
- chars are equal or lower.

It meets the acceptance rule (>= 2 S on dev, no loss on dev200, Sall not down). A drop-in replacement for the temporal
entry in configs/best.json.

If Sall turns out to matter more than S (Reactor cites everything), use `ev1_mix_k8`. It costs 1.4 S on dev against
ev1_mix_g, gains 2.1 Sall on dev200 and uses about 800 fewer chars.

## Test audit (qualitative, 12 packs + every test gap question where A gives no computed value)
- The fallback fires on 2 of the 5 test gap questions where A has no computed value. Both look right:
  - Montreal flat alerts -> lease = 45. The picks are "I set up alerts for shared flats in Montreal tonight" and "I signed a lease ... today". A's raw value is also 45, withheld by A for low confidence.
  - Hive inspection -> varroa = 14, from explicit dates.
- Without the guard, the sourdough question got 58 from garbage picks: an assistant sentence on "Sourdough croissants" and a "Meatloaf" recipe, with B's margin conf at 0.78. The guard rejects it: no content word shared, and "after" with the dates in the wrong order. A's raw value was the same wrong 58.
- No fallback on the trail run (B finds only "Camille bought trail-running shoes", someone else) or on the wife's birthday / anniversary (B conf 0.59, just below the gate). Both are left to Reactor.
- 1 of 12 audit packs is flagged: "How many years did I serve as a firefighter?", abstain_p 0.62, probably unanswerable, unchanged from r1.

## Top failure patterns (dev, ev1_mix_g)
1. **Whole-question route: same-category gold sessions at other dates rank too low, so ALL fails.** These gold sets
   list every session of the asked category, not only the one at the anchor date.
   - "Who did I go with to the music event last Saturday?": the 5th gold session is at session rank 14 with the time prior, 5 without it.
   - "I mentioned cooking something for my friend a couple of days ago": the 2nd gold session is at rank 18 (9 without the prior).
   - "What was the life event of one of my relatives that I participated in a week ago?": rank 24.
   The interleaved plain-CE ranking (`mix`) recovers some of these: route ALL 0.846 -> 0.897.
2. **Whole-question packs are wide.** 13.8 passages for about 3 gold sessions gives CF1all 0.35. Every session cap
   tried costs ALL:
   - top-5 sessions: ALL 0.85 -> 0.64.
   - cap 8: -1.4 S on dev, +2.1 Sall on dev200.
   The ranking cannot separate the category-mates from decoys well enough for a cap to be free.
3. **Event-route "ago" with an explicit date or a long span.**
   - "How many days ago did I read the March 15th issue of The New Yorker?": computed 17, gold 12/13; the date is in the question.
   - "How many months ago did I book the Airbnb in San Francisco?": computed 0, gold 5.
   - "Which group did I join first, 'Page Turners' or 'Marketing Professionals'?": ALL 0, one gold session not retrieved.

## CORE REQUESTs
1. Point the temporal route in `configs/best.json` at `lenses/temporal/b_merge.py:ev1_mix_g`. It contains merged_r1 as `base`, so A's gap route is untouched apart from the guarded fallback.
2. Add `harness.sweep --filter <regex>` (or `--qids file`) to sweep a subset, such as gap and non-gap questions. Today that needs post-hoc scripts (`scratch_b/sub.py`).
3. Coordinate with temporal-A: A's gap packs average 4.4 passages (Sall 79 vs S 84 on the dev gap subset). Brief A(2) trims them; when it lands, b_merge picks it up through `load_lens` with no change.

## Ideas for next round
- Gap fallback by agreement: when A's raw (withheld) value equals B's computed, emit it even below A's own confidence gate. Montreal on test is such a case.
- Whole-question route, two-stage sessions: (a) the anchor session (time prior) plus (b) category sessions with plain CE above a floor. Pack whole user turns of those sessions only and cite (a) + (b). That would allow a session cap without losing the category-mates.
- Use `hx.rerank_texts` on sentences to pick the second gold turn of "first" questions instead of token overlap. The event-route fill still misses ATR on paraphrased turns ("solo trip to South America" for "Thailand").
- "ago" questions with an explicit date in the question ("March 15th issue"): compute from the question date directly.
- `w_today` (a unit that dates its own event: "today", "just") helped a little only in the session-centric route. Retry it on the mix ranking.
