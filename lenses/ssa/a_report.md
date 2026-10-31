# SSA lens A ("Struktura"), round 4 report

The round-3 report moved to `lenses/ssa/a_report_r3.md` (round 2: `a_report_r2.md`).

Files (all new; no frozen v2 file was edited):
- `lenses/ssa/a_r4_role.py`: role detector r4, a drop-in `role_module` for `lenses/ssu/a_r3_route.py`. It is `a_r3_role.role_guess` plus two sentence-evidence rules (nf0 rule, role-play rule).
- `lenses/ssa/a_r4_role_nf0.py`: the nf0 rule alone (`rp=False`).
- `lenses/ssa/a_r4_routed.py`: measurement wrapper around `lenses/pipeline.py`. Variants:
  - `v2` = configs/best_v2.json.
  - `r4role` = v2 + `a_r4_role_nf0` on the ssu route.
  - `r4rp` = v2 + `a_r4_role` on the ssu route.
- `lenses/ssa/scratch_a/r4/`:
  - configs `routed_r4role.json` and `routed_r4rp.json`;
  - sentence-feature scans `sent_feats.py` (nf0 questions) and `fp_feats.py` (first-person questions, FP check);
  - test audits `audit_r4*_ssu.out`;
  - full routed sweep logs `sw_routed_{dev,dev200}.log`.
- Runs: tag `r4-ssa-a`.

## TL;DR
1. **No ssa test pack is worth a Reactor re-ask. 0 ssa-route packs changed.**
   - Real Reactor (v1_results) answered all 5 ssa questions asked so far correctly, each citing the one right session: Toggl Track, Heden, Matilda 159 Domain, pandas, Visual Studio Code.
   - I audited all 25 ssa-routed v2 test packs by hand. Every pack is a single session, holds the assistant's recommendation sentence, and has no competing recommendation in the passage.
   - 23 of the 25 packs quote the line. The two without a quote (Lisbon/Heden, speedwork/Coach Miriam) still state it plainly ("Heden in Baixa has a good day pass", "I recommend Coach Miriam at the Toronto Lakeshore Running Club"). Reactor already answered Heden correctly.
   - The quote lines have cosmetic join artifacts ("South Yarra.; it has", "grade papers..", "Oh, For the audio coupling…", "made, You should"). They are not defects: Reactor answered the Matilda pack, which has ".;", correctly. Fixing them would mean re-asking 4+ packs for nothing.
2. **There are no role (ssa vs ssu) defects on test.** Every ssu-, multi- and temporal-routed test question carries a first-person word. The highest assistant margin among them is "favorite color" (d 3.2), and all of them are user-fact questions. No test question is handed off to or from ssa (the only hand-off on test is move date, ssu → ku).
3. **Brief items 1 and 3 are implemented as `a_r4_role.py`. They change dev only (0 of 45 test ssu packs).**
   - Gold ssa through routing, dev: **93.0 → 93.6** (PA 0.991 → 1.000, Sall 92.8 → 93.3).
   - ssu-routed slice, dev: 88.8 → 89.3 (Sall 89.3 → 89.8).
   - dev200: identical.
   - 0 false positives: no non-ssa question changes route.
   - All 50 dev gold-ssa questions on the ssu route now reach the ssa lens (v2: 43). None of them gets the broken user-only hint any more ("their own jumpsuit led me. Mentions of other people's me", "their own house begin").
   - Below the +2 bar and invisible on test. Offered only as insurance for a later system. **Not for the final pass.**
4. Brief item 2 (cite the best turn's own session on cue-less hand-offs) is **not needed**. Its motivating regression was the ssu "new apartment" question handed to the ssa lens. The u_first gate keeps that question on ssu, and every r4 hand-off has CF1 = CF1all = 1.

## Test packs I would change
**None.** `harness.audit --lens lenses/ssa/a_r4_routed.py --variant r4rp --type ssu --compare runs/final/v2_test_packs.jsonl` reports: 0 of 45 packs changed, and 0 change what Reactor sees. The ssa route lens (`a_recsent r2_conf2`) is untouched, so the 25 ssa packs are byte-identical.

## Variants tried (one line each)
| variant | idea and params | verdict |
|---|---|---|
| `generic hybrid_rr` (bar) | kit hybrid + rerank | dev 72.3, dev200 71.2 (PA 1, CF1 0.37 / 0.33, ~11.9k chars) |
| `a_recsent r2_conf2` (frozen v2 ssa route) | single-session recommendation lens, quoted line | dev 93.6, dev200 93.7 (PA = CF1 = 1); unchanged |
| `r4role` (`a_r4_role_nf0`) | nf0 question, p_r3 < 0.8, and (u_first == 0 or d_sent ≥ 3) → p = 0.85 (passes ssu 0.8, never multi 0.9) | dev gold-ssa 93.0 → 93.6, ssu slice 88.8 → 89.3, dev200 tie, 0 FP, 0 test change |
| `r4rp` (`a_r4_role`) | r4role + role-play rule: first-person question, u_first == 0 and d ≥ 2 and d_sent ≥ 3 → 0.85 | same S as r4role (the jumpsuit pair already had PA 1); removes the broken hint from the last 2 dev ssa-on-ssu questions; 0 FP, 0 test change. **Best.** |
| brief item 2 (own-session cite on hand-off) | not built | not needed (see TL;DR 4) |

Features (sentence level, `sent_features` in `a_r4_role.py`):
- **u_first**: number of first-person words in the best user sentence. The best user sentence is chosen by CE over the sentences of the top-5 user units in the CE-reranked hybrid top 40.
- **d_sent**: CE of the best assistant sentence minus CE of the best user sentence.
- **Separation in the d −9..−1 band (dev):**
  - nf0 ssu/ku negatives keep a first-person user statement:
    - "it took me and my friends around 5 hours to move" (uf 2)
    - "I remember Alex t…" (uf 4)
    - "my friend Rachel who recently moved" (uf 2)
  - nf0 ssa positives match pasted or requested text:
    - the user pastes the article "Arati Prabhakar, the President's Chief Advisor …"
    - the case text "The case of Bajimaya v Reward Homes …"
    - the script line "Andy wears an untidy …"
    - the request "Can you recommend some authentic Italian restaurants in Rome?"
    - powwows has uf 1 but d_sent +6.38 against a unit d of −1.00.

## Results
Gold-type ssa sent straight to the lens. There are no unanswerable ssa questions, so AUC is "-".

| split | lens / variant | S | PA | ATR | SR | CF1 | chars | AUC |
|---|---|---|---|---|---|---|---|---|
| dev (112) | generic `hybrid_rr` (bar) | 72.3 | 1.000 | 1.000 | 1.000 | 0.368 | 11932 | - |
| dev | `a_recsent r2_conf2` (v2 ssa route) | 93.6 | 1.000 | 1.000 | 1.000 | 1.000 | 4542 | - |
| dev200 (22) | generic `hybrid_rr` (bar) | 71.2 | 1.000 | 1.000 | 1.000 | 0.331 | 11938 | - |
| dev200 | `a_recsent r2_conf2` (v2 ssa route) | 93.7 | 1.000 | 1.000 | 1.000 | 1.000 | 4186 | - |

Gold ssa through the routed system (`a_r4_routed.py`):

| split | variant | S | Sall | PA | ATR | SR | CF1 | chars |
|---|---|---|---|---|---|---|---|---|
| dev | v2 | 93.0 | 92.8 | 0.991 | 0.991 | 1.000 | 1.000 | 4504 |
| dev | r4role | 93.6 | 93.3 | 1.000 | 1.000 | 1.000 | 1.000 | 4571 |
| dev | **r4rp** | **93.6** | 93.3 | 1.000 | 1.000 | 1.000 | 1.000 | 4605 |
| dev200 | v2 / r4rp | 93.7 | 93.7 | 1.000 | 1.000 | 1.000 | 1.000 | 4186 |

ssu-routed slice (`--route --type ssu`; the only route the r4 module touches):

| split | variant | S | Sall | PA | ATR | SR | CF1 | chars | AUC | gold ssa on ssa route |
|---|---|---|---|---|---|---|---|---|---|---|
| dev (140) | v2 | 88.8 | 89.3 | 0.947 | 0.971 | 0.984 | 0.952 | 4193 | 0.934 | 43 / 50 |
| dev | r4role | 89.3 | 89.8 | 0.955 | 0.979 | 0.984 | 0.952 | 4246 | 0.937 | 48 / 50 |
| dev | **r4rp** | **89.3** | 89.8 | 0.955 | 0.979 | 0.984 | 0.952 | 4273 | 0.938 | 50 / 50 |
| dev200 (38) | v2 = r4role = r4rp | 88.8 | 88.9 | 0.971 | 0.971 | 0.986 | 0.900 | 4271 | 0.914 | 7 / 7 |

On the dev slice the ssu, ku, multi and temporal gold rows are identical between v2 and r4 (S 93.3 / 87.7 / 61.4 / 57.3): **FP 0**.

Full routed system (all types; dev 526 q, dev200 125 q; `scratch_a/r4/sw_routed_*.log`):

| split | variant | S | Sall | PA | ATR | SR | CF1 | chars | AUC |
|---|---|---|---|---|---|---|---|---|---|
| dev | v2 | 86.9 | 85.3 | 0.942 | 0.972 | 0.986 | 0.915 | 5585 | 0.812 |
| dev | **r4rp** | **87.0** | 85.4 | 0.944 | 0.974 | 0.986 | 0.915 | 5607 | 0.812 |
| dev200 | v2 | 87.0 | 85.2 | 0.946 | 0.970 | 0.984 | 0.905 | 5489 | 0.853 |
| dev200 | r4rp | 87.0 | 85.2 | 0.946 | 0.970 | 0.984 | 0.905 | 5489 | 0.853 |

Per gold type on dev, the ssu, multi, ku and temporal rows are identical between v2 and r4rp (87.4 / 85.2 / 91.5 / 80.3). Only ssa moves: 93.0 → 93.6. Route mix on gold ssa: v2 104 ssa, 7 ssu, 1 temporal; r4rp 111 ssa, 1 temporal.

## Top failure patterns
1. **The ssa route has none left on proxy or on real Reactor.**
   - PA = CF1 = 1 on dev and dev200.
   - Real Reactor is 5 of 5 correct with a single right cite.
   - The planted decoys on test stay out of the packs: the sister's farrier Magnus Vik, illustrator Maja Lie, Coach Elena, the AGC resistor, and the user's own Avila Spaces pass. Each of the 25 packs is the one recommendation session.
2. **Misrouted ssa questions get a broken user-only hint (dev only).** v2 leaves 7 on the ssu route:
   - "In Bajimaya v Reward Homes …" gets "their own house begin";
   - the jumpsuit question gets "their own jumpsuit led me. Mentions of other people's me";
   - the President question gets "their own fusion breakthrough" and has PA 0: the gold assistant turn is missing (ATR 0), although the user's pasted article holds the name (AC 1).

   r4rp hands all 7 to the ssa lens.
3. **Router-level ssa misroutes the role module cannot see** (dev only):
   - "Which show was my example of Netflix only having the last season available?" goes to the temporal route. That pack carries extra sessions (CF1all 0.993 on the gold-ssa slice).
   - Test has no such question.

## CORE REQUESTs
1. **Not for the final pass:** leave configs/best.json as v2.
   - If there is a later system, set `routes.ssu.params.role_module = "lenses/ssa/a_r4_role.py"` (= `scratch_a/r4/routed_r4rp.json`): dev +0.5 on the ssu slice, +0.6 on gold ssa, dev200 tie, 0 test change.
   - Keep the multi route on `a_r3_role.py`. r4 returns 0.85 when it fires, which never passes the multi threshold of 0.9, so it would change nothing there anyway.
2. **ssu owners (visible on test, not ssa):**
   - "What's the name of the half marathon I'm training for?" has `computed: "Decent"`. That is the user's answer to "How's training going?", not a name.
   - The ssu hint head-noun templating ("their own half marathon … other people's marathon") is ssu-A's brief item 2.
3. **harness.failures:** print the gold turn's role next to IN/MISS. The President question is AC 1 / ATR 0: the name sits in the user's pasted article, while the gold turn is the assistant's keyword list.

## Ideas for the next round
- Treat u_first, the first-person words in the best-matching user sentence, as a general "own statement vs pasted/requested text" signal. ssu and ku could use it to drop user units that are pasted articles or role-play from the user-fact pool.
- A soft quote line for low-confidence ssa picks, but only after a Reactor check (Heden without a quote was answered correctly).
- Clean the quote-line join artifacts (".;", "..", "Oh, For") only when a pack is rebuilt anyway; on its own it is not worth a re-ask.
