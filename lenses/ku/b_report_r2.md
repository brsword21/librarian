# KU lens B ("Semantyka"): round 2 report

(Saved from `lenses/ku/b_report.md` at the start of round 3, which now holds the round-3 report.)

Lens: `lenses/ku/b_r2.py`. It reuses the pair_r1b retrieval and pair logic from `lenses/ku/b_semantic.py` unchanged and replaces the packing. Round-1 report: `lenses/ku/b_report_r1.md`. Runs: `runs/r2-ku-b/ku/{generic,b_semantic,b_r2}/<variant>/{dev,dev200}`. Test audits: `runs/audit/ku/b_r2/{r2b,r2c}/test_packs.jsonl` and `lenses/ku/scratch_b/r2_audit_r2b.log`. Detector runs: `runs/r2-ku-b-det/{multi,ssu}/b_r2/r2b/dev`.

**Best variant: `b_r2.py` / `r2b`.**
- Dev: S 93.4, Sall 93.6.
- dev200: S 93.3, Sall 92.7.
- Round-1 winner `pair_r1b` (re-run): S 93.2 / 93.1, Sall 83.9 / 83.8.

So r2b gains about +0.2 S and **+9.7 Sall on dev, +8.9 Sall on dev200**, with about 600 fewer chars and a higher abstention AUC (dev 0.887 → 0.926, dev200 0.886 → 0.898).

The "+2 S on dev" rule cannot be met. Dev KU is saturated: the S ceiling at about 3k chars is about 93.9. r2b wins on Sall, which is what round-2 brief item 1 targets, and it loses nothing on S on either split.

## Variants tried (one line each)
- `r1b`: control. pair_r1b re-run through b_r2: the pair plus 2 context sessions, budget 6000.
- `only`: the cited pair only (extra=0, 3 units per pair session, budget 4500). It loses 2 PA on dev and 1 on dev200.
  - The context sessions were rescuing the gym-frequency, kitchen-gadget and one dev200 pair.
- `gate`: pair only if the pair is confident, otherwise pair + 1. The gate needs own ≥ 0, cov_min ≥ 0.5, no newer "threat" session, and distinct values or margin ≥ 2.
  - cov ≥ 0.5 was far too strict: 25 of 72 questions were judged not confident, and it still missed the gym question. Dev S 92.5, Sall 90.9.
- **`m35`**: margin-only gate. The pair goes alone when its weaker member's score is ≥ 3.5 above the best non-pair session; otherwise pair + 1 context session.
  - On dev, all 5 pair misses or PA risks have margin < 3.5: camera lens 0.43, Saturday wake-up 0.58, gym 1.8, United status 2.7, kitchen gadget 3.1. The next correct pair is at 4.95.
  - The hint still quotes dated statements from 2 more sessions (`tl_extra=2`). Reactor can read them but cannot cite them.
- `m35x2`: as m35 with pair + 2 when not confident. Same S, Sall −0.8 on dev200.
- `m5`: gate margin 5.0. Same S, Sall −0.6 on dev200.
- `m35_bg`, `m35_bg1`, `m35_bg15`: m35 plus phrase-level (bigram) abstention, with logit +w per missing question bigram, capped at 2. The `missing_phrases` helper is copied from lens A (`a_timeline.py`, pkl_b1); credit to A.
  - w=1.0 is best: AUC 0.926 dev, 0.898 dev200. Only abstain_p changes.
- **`r2b`**: m35_bg1 without the INSUFFICIENT_EVIDENCE note in the hint, per the round-2 rule of no abstention hints. Metrics are identical.
- `r2c`: r2b plus an ownership rule for quantity questions. A bare-name subject with no I/my counts as someone else's value ("Carlos drinks three cups of coffee every morning.").
  - Neutral on dev and dev200, and no pack changed on test: Carlos drops to own=−1 but still ranks 2nd. Not adopted (simpler wins).
  - The flag `OWN_NAME` in b_semantic.py defaults to off, so pair_r1b is unchanged (selftest passes).

## Results (KU only; dev 78 q / 72 answerable, dev200 26 q / 22 answerable)
| variant | dev S | Sall | PA | ATR | SR | CF1 | CF1all | chars | AUC | dev200 S | Sall | PA | ATR | SR | CF1 | CF1all | chars | AUC |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| generic/hybrid_rr (bar) | 83.8 | 83.8 | 0.972 | 0.979 | 0.986 | 0.812 | 0.812 | 11936 | 0.806 | 83.5 | 83.5 | 1.000 | 1.000 | 1.000 | 0.740 | 0.740 | 11923 | 0.852 |
| r1b (= pair_r1b, R1 winner) | 93.2 | 83.9 | 1.000 | 0.965 | 1.000 | 0.979 | 0.667 | 3669 | 0.887 | 93.1 | 83.8 | 1.000 | 0.977 | 1.000 | 0.977 | 0.667 | 3729 | 0.886 |
| only | 91.6 | 91.6 | 0.972 | 0.972 | 0.979 | 0.979 | 0.979 | 2994 | 0.887 | 90.4 | 90.4 | 0.955 | 0.977 | 0.977 | 0.977 | 0.977 | 2876 | 0.886 |
| gate (cov gate) | 92.5 | 90.9 | 0.986 | 0.986 | 0.993 | 0.979 | 0.926 | 3187 | 0.887 | - | | | | | | | | |
| m35 | 93.4 | 93.6 | 1.000 | 0.993 | 1.000 | 0.979 | 0.986 | 3048 | 0.887 | 93.3 | 92.7 | 1.000 | 1.000 | 1.000 | 0.977 | 0.955 | 3077 | 0.886 |
| m35x2 | 93.4 | 93.4 | 1.000 | 0.993 | 1.000 | 0.979 | 0.979 | 3080 | 0.887 | 93.3 | 91.9 | 1.000 | 1.000 | 1.000 | 0.977 | 0.930 | 3255 | 0.886 |
| m5 | 93.4 | 93.5 | 1.000 | 0.993 | 1.000 | 0.979 | 0.981 | 3063 | 0.887 | 93.3 | 92.1 | 1.000 | 1.000 | 1.000 | 0.977 | 0.936 | 3125 | 0.886 |
| m35_bg (w .6) | 93.4 | 93.6 | 1.000 | 0.993 | 1.000 | 0.979 | 0.986 | 3048 | 0.917 | 93.3 | 92.7 | 1.000 | 1.000 | 1.000 | 0.977 | 0.955 | 3077 | 0.898 |
| m35_bg1 (w 1.0) | 93.4 | 93.6 | 1.000 | 0.993 | 1.000 | 0.979 | 0.986 | 3048 | 0.926 | 93.3 | 92.7 | 1.000 | 1.000 | 1.000 | 0.977 | 0.955 | 3077 | 0.898 |
| m35_bg15 (w 1.5) | 93.4 | 93.6 | 1.000 | 0.993 | 1.000 | 0.979 | 0.986 | 3048 | 0.924 | 93.3 | 92.7 | 1.000 | 1.000 | 1.000 | 0.977 | 0.955 | 3077 | 0.898 |
| **r2b** | **93.4** | **93.6** | 1.000 | 0.993 | 1.000 | 0.979 | 0.986 | 3043 | 0.926 | **93.3** | **92.7** | 1.000 | 1.000 | 1.000 | 0.977 | 0.955 | 3072 | 0.898 |
| r2c | 93.4 | 93.6 | 1.000 | 0.993 | 1.000 | 0.979 | 0.986 | 3043 | 0.926 | 93.3 | 92.7 | 1.000 | 1.000 | 1.000 | 0.977 | 0.955 | 3072 | 0.898 |

On dev, CF1all (0.986) is higher than CF1 on cite_plan (0.979). On two low-margin questions (camera lens, kitchen gadget) the context session is the gold session the pair missed, so citing everything there is correct.

## Test audit (`harness.audit`, 20 KU-routed questions, qualitative)
- **The gate is stricter on test.** 8 of 20 packs are pair-only. 12 of 20 get pair + 1 because test margins are low (planted near-misses). If those pairs are right, the expected test KU CF1all is about 0.88, against 0.667 for pair_r1b.
- **Brief item 2: the newly routed questions.**
  - Correct old → new pairs: km each evening 3 km → 5 km (confident); GB data plan 15 → 25 GB (confident); UX team 6 → 8 (confident); apple trees 4, then +3 (confident); chapters 8 → 12; beehives 3 → 4; tractors 1 → 2; rent 18,000 → 22,000; watercolour Margaret → Priya Nair; accountant Marta → Bruno; ceramics Miguel → Ana Ferreira.
  - Still wrong:
    - **laps**: only "40 laps" restatements and the neighbour's 20 laps are found. The update is not retrieved.
    - **cups of coffee**: the pair holds "Carlos drinks three cups" (another person) next to the correct new "switched to just one cup". The user's own old statement is not retrieved.
    - **rooms renovated so far**: no count statement is retrieved.
    - **job title**: the promotion to Director of Clinical Services is not retrieved. The hint now quotes nothing misleading.
    - **long run**: the recap "shifted to Sundays at 6:30 a.m." is not retrieved; we get "playgroup moved to 9:00".
    - **skateboard**: the old name 'Decaf' is only quoted inside the update sentence.
    - **cats on my farm**: probably unanswerable. The pack shows horses and beehives with abstain_p 0.18.

## Top failure patterns (r2b)
1. **Paraphrased updates without the attribute noun are not retrieved (test).** Examples: job title → "another promotion, so now I am Director of Clinical Services"; long run → assistant recap "Sundays at 6:30 a.m."; laps. Dev cannot measure this: every dev KU gold turn is a user turn with the attribute noun.
2. **Another person's value fills the old slot when the user's own old statement is not in the pool** (test). Example: coffee, "Carlos drinks three cups". The own penalty (−6) is not enough when every other candidate is weak too.
3. **Low-margin dev pairs (CF1 only, PA kept by the gate):** camera lens; kitchen gadget before the Air Fryer; gym frequency.
4. **The bigram abstention signal also fires on answerable test questions** ('job title', 'monthly rent', 'freelance taxes', "skateboard's name", 'completely renovated'). Fine as a ranking score but must not drive a hint.

## Brief item 4: evidence-based KU detector `ku_pair_p(q, hx)` (in `b_r2.py`)
Rule: the pair's best sentences carry two **different** values, the weaker pair member's score is ≥ 6, and min coverage is ≥ 0.5. Measured on dev with 40-question samples for multi and ssu:

| threshold (min score, min cov) | ku hit | multi FP | ssu FP |
|---|---|---|---|
| 0, 0.3 | 55/78 | 10/40 | 0/40 |
| 4, 0.5 | 42/78 | 3/40 | 0/40 |
| **6, 0.5** | 40/78 | 2/40 | 0/40 |

Apply only to ssu-routed questions (a multi → ku misroute costs about 70 S).

## CORE REQUESTs (round 2)
1. Route ku to `lenses/ku/b_r2.py` variant `r2b` (done in v1).
2. Router: wire `ku_pair_p` into the ssu route only, after re-measuring (measured as e5; deferred because of 6 test firings).
3. Submission: if post-filtering by `cite_plan` is ever confirmed, KU loses nothing either way now.

## Ideas for the next round (round 2)
- **Attribute-paraphrase second hop for the test misses.** Run sentence-level CE (`hx.rerank_texts`) over value-bearing own sentences of the top 60 user units, plus assistant recaps, with the declarative attribute ("my job title", "my long run start time"). Admit a session to the pair only if it states a value of the same type (time / count / title / name) as the old member. Targets job title, long run and laps.
- **Own-value constraint in the pair.** When one pair member has own < 0 (Carlos), replace it with the best own same-type-value session even if its score is lower, or drop to a single-session pack plus the hint.
- **Per-owner totals** ("Bjørn and I in total"): one timeline per owner and a summed `computed`.
- **Calibrate abstain_p on dev + dev200 pooled**, using the bigram signal only together with low coverage, so answerable phrase variants ("monthly rent") are not pushed up.
