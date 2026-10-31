# Citation attribution: rule policies on real Reactor answers

The study was read-only. Nothing in `reactorq/`, `configs/`, `lenses/`, `core/` or `runs/final/` was changed. Reactor was never called, and the model server was not touched.

Files saved:
- `runs/citations/cit_rules.py`: all policies. Run from `librarian/` with `.venv/bin/python runs/citations/cit_rules.py calib|test|sim|calib2|test2|sim2 [results.jsonl]`.
- `runs/citations/finalize_proposed.py`: `finalize.py` with the proposed rules.
- `runs/citations/finalize.diff`: the diff (also in the recommendation field).

Inputs:
- **Test answers:** a snapshot of `runs/final/v1_results.jsonl` at 75 rows: 64 answered, 11 INSUFFICIENT_EVIDENCE. Each answer was joined by `pack_hash` to the pack Reactor actually saw (v3, then v2, v1, …). All 75 joined by hash.
- **Dev simulation packs:** `runs/citations/{dev,dev200}_packs.jsonl`, built by `reactorq.build_packs` with the frozen system and full passage text. They were already being built when I started.
- **e1 size:** e1 has only 12 result rows, not about 19. Of these, 9 are answerable and 8 were answered, all without labels.

## TL;DR

1. **Fix the ku-chain trigger.**
   - It should fire only when Reactor cites exactly one session.
   - On test, Reactor cites 2 sessions on 9/9 ku answers, because the "Cite both …" hint works.
   - The current trigger fires when one of Reactor's cites is in the 2-session plan. It fired on 2/9 test answers, both times adding a third session to a pair Reactor had already chosen.
   - In `q_8e9be6f580d2` (Moroccan spices) the added E1 says nothing about a store, so it does not support the answer. Reactor's own E2 ("shop on Danforth") was the real old value.
   - In `q_e165458f4cff` (rent) it adds the 18,000 rent to Reactor's 22,000 → 9,000 pair. That one is debatable.
2. **Enable computed-chain.**
   - Rule: when Reactor's number equals `pack.computed` (±1 day for how-many-days/weeks/months/years questions), cite all cite_plan sessions.
   - Every session it added in the dev simulation was gold: 23/23 on dev, 5/5 on dev200.
   - It changes 0 of today's test answers: all 18 temporal answers already cite both date sessions, and computed matches on all 18. It is a free safety net for the "Reactor cites one of the two event sessions" failure.
3. **Make fill-missing fuzzy.**
   - It matches plurals and hyphens ("55 inches" vs "55-inch").
   - For a bare count N it matches "N + question noun" ("7 shirts", "four bikes").
   - e1 (no labels) answered F1 goes from 0.625 to 0.875.
   - In the dev simulation with no labels, added sessions are gold 95% of the time, up from 97% before, and F1 rises from 0.457 to 0.494 on dev and from 0.496 to 0.567 on dev200.
   - There are 0 uncited test answers today.
4. **Add guarded containment on ssu/ssa/ku/temporal.**
   - Rule: add every packed session that contains Reactor's whole normalized answer phrase.
   - Guard: only for answers with at least 2 content words or a number of 4 or more digits.
   - Without the guard, a one-word answer hits decoys. On test, "Masa" matched E2 "not 'masa madre'".
   - With the guard it changes 0 test answers.
   - On e1b it fixes "The Nightingale by Kristin Hannah" (0.67 → 1.0).
   - In the dev simulation, containment-only additions were gold 11/11 on dev and 3/3 on dev200.
5. **Add reply-rows on the multi route.**
   - Rule: cite the [E#] that Reactor itself listed as counted instance rows in its working, before its "Excluded" notes and skipping not/decoy/✗ rows.
   - On e1b it fixes "How many bikes do I currently own?" (0.67 → 1.0). Reactor listed E1 = 3 bikes and E2 = 4 bikes but cited only E2.
   - It changes 1 test answer, the watercolour classes. It adds E1 and E2, which both state the Saturday class, one of the 2 classes counted.
   - Only one calibration example exists, so a human should check it.
6. **Reject plan-union (d) and drop-unsupported (f).**
   - **Plan-union (d)** adds sessions that do not support the answer: on test, the cat "Sombra" session against Reactor's "Fig", and zucchini or possum sessions on multi. Its added-session precision is 0.67–0.80 on multi and temporal in the simulation.
   - **Drop-unsupported (f)** removes correct sessions. On test it dropped the old-store session from the Moroccan ku pair. In the dev simulation it lowers F1: ssu 0.924 → 0.904, temporal 0.850 → 0.831, multi (raw) 0.903 → 0.830.

Overall effect of the proposed rule set on real Reactor answers:
- e1b answered F1: **0.853 → 0.904**.
- e1b over all answerable questions: 0.693 → 0.734.
- e1 answered: 0.625 → 0.875.

The rest of the gap does not come from attribution:
- 3/16 answerable e1b questions are abstentions or closed connections, handled elsewhere.
- Graduation: gold has 5 sessions, but our plan has 3 and Reactor excluded the other 2.
- Two ku-type questions were routed to ssu or multi, and no rule can verify their old-value session:
  - "Oahu": our ssu plan has the old session, Reactor cites the new one.
  - "Canon 80D trips": Reactor itself excluded E2 as "states no trip count".

## 1. Real Reactor answers (dev calibration)

Policies compared:
- **a:** Reactor's own citations.
- **b:** the current finalize (exact fill-missing + ku-chain).
- **c:** b + computed-chain; `c_strict` is the same without ±1.
- **d:** own ∪ cite_plan.
- **e:** b + containment union; `_g` means guarded, `_raw` means unguarded.
- **f:** drop own cites without the answer when another own cite has it, then b.
- **rec:** b + c + guarded containment on ssu/ssa/ku.
- **b2:** the proposed finalize with fuzzy fill-missing and single-cite ku-chain.
- **g:** b2 + multi reply-rows.
- **rec2:** the full proposal (b2 + computed-chain + containment with the 2-word guard + reply-rows) = the attached diff.

**e1:** 9 answerable, 8 answered, all without [E#] labels (prompt bug).

| policy | F1 over answerable | F1 over answered | answers changed |
|---|---|---|---|
| a_own | 0.000 | 0.000 | 0 |
| b_finalize (current) | 0.556 | 0.625 | 5 |
| c / c_strict / e_g / e_raw / f / rec | 0.556 | 0.625 | 5 |
| d_plan_union | 0.852 | 0.958 | 8 |
| **b2 / rec2 (proposed)** | **0.778** | **0.875** | 7 |

The proposal fixes "55 inches" (the passage says "55-inch") and "7" shirts (the passage says "I brought 7 shirts"). It still misses "On Valentine's Day in February": the passage says only "Valentine's Day". Plan-union scores 0.958 here, but only because uncited ssu answers fall back to the top-ranked session. The organisers' Discord message warns against exactly that.

**e1b:** 16 answerable, 13 answered.

| policy | F1 over answerable | F1 over answered | answers changed |
|---|---|---|---|
| a_own | 0.693 | 0.853 | 0 |
| b_finalize (current) | 0.693 | 0.853 | 0 |
| c_computed / c_strict | 0.693 | 0.853 | 0 |
| d_plan_union | 0.726 | 0.894 | 6 |
| e_contain_g | 0.714 | 0.878 | 1 |
| e_contain_raw | 0.672 | 0.827 | 4 |
| f_drop_g | 0.693 | 0.853 | 0 |
| f_drop_raw | 0.635 | 0.782 | 2 |
| g_reply_rows | 0.714 | 0.878 | 1 |
| **rec2 (proposed)** | **0.734** | **0.904** | 2 |

Per-question detail for e1b answered questions:

| question | route / gold type | gold sessions | own F1 | best policy |
|---|---|---|---|---|
| doctors (1086b7) | multi / multi | 3 | 1.0 | own (d → 0.67, plan 3/6) |
| graduation (150957) | multi / multi | 5 (plan 3/3) | 0.75 | d 0.89 (retrieval loss) |
| Nightingale (2cf880) | temporal | 2 | 0.67 | containment 1.0 |
| sculpting tools (9fe315) | temporal | 2 (plan 1/3) | 0.67 | none (d → 0.40) |
| bikes (a3c703) | multi / ku | 2 (plan 2/2) | 0.67 | reply-rows 1.0, d 1.0 |
| Oahu (66e337) | ssu / ku | 2 (plan 1/1, other one) | 0.67 | only d (plan = old session, not verifiable) |
| Canon 80D (2b5706) | multi / ku | 2 (plan 2/2) | 0.67 | only d (Reactor excluded E2) |
| 6 others | — | — | 1.0 | unchanged |

## 2. Dev and dev200 simulation (gold answer stands in for Reactor's answer)

Simulated Reactor citation behaviours:
- **none:** no labels.
- **one:** Reactor cites one session, the newest cite_plan session containing the answer, else plan[0]. This is what we saw on ku and temporal.
- **plan:** Reactor cites exactly cite_plan.

Mean F1 over answerable questions:

| split | base | policy | ssu | ssa | multi | ku | temporal | ALL | gold / added |
|---|---|---|---|---|---|---|---|---|---|
| dev | none | b current | .679 | .625 | .154 | .672 | .492 | .457 | 303/311 |
| dev | none | b2 proposed | .679 | .644 | .254 | .703 | .497 | .494 | 331/350 |
| dev | one | a own | .863 | 1 | .606 | .696 | .651 | .748 | – |
| dev | one | b current | .863 | 1 | .606 | .971 | .651 | .761 | 21/23 |
| dev | one | c computed | .863 | 1 | .606 | .971 | .708 | .776 | 44/46 |
| dev | one | d plan-union | .924 | 1 | .903 | .971 | .850 | .915 | 343/447 |
| dev | one | e_raw | .880 | 1 | .609 | .962 | .694 | .776 | 47/62 |
| dev | one | rec2 | .867 | 1 | .606 | .971 | .727 | .782 | 55/57 |
| dev | plan | a own | .924 | 1 | .903 | .971 | .850 | .915 | – |
| dev | plan | f_drop_g | .904 | 1 | .891 | .971 | .831 | .903 | – |
| dev | plan | rec2 | .928 | 1 | .903 | .971 | .853 | .917 | 3/3 |
| dev200 | one | a own | .846 | 1 | .606 | .722 | .687 | .763 | – |
| dev200 | one | c computed | .846 | 1 | .606 | .944 | .770 | .790 | 10/11 |
| dev200 | one | rec2 | .885 | 1 | .606 | .944 | .787 | .802 | 13/14 |
| dev200 | plan | a own | .865 | 1 | .865 | .944 | .911 | .905 | – |
| dev200 | plan | f_drop_g | .865 | 1 | .882 | .944 | .860 | .901 | – |
| dev200 | plan | rec2 | .903 | 1 | .865 | .944 | .911 | .914 | 2/2 |

Precision of added sessions under base "one", per route (gold / added):
- **ku-chain:** dev 21/23, dev200 5/6.
- **computed-chain (temporal):** dev 23/23, dev200 5/5.
- **Plan-union:**
  - dev: ssu 15/15, multi 197/245 (0.80), temporal 110/164 (0.67).
  - dev200: ssu 2/3, multi 46/63 (0.73), temporal 18/25 (0.72).
- **Raw containment:**
  - dev: multi 4/10, temporal 19/25.
  - dev200: ssu 3/5, multi 2/5.
- **Guarded containment:** dev multi 3/3, dev200 multi 2/3.

These are the reasons for excluding multi from containment.

Plan-union looks best on the simulated F1 averages. It is excluded because about 1 in 4 added sessions on multi and temporal is not evidence, and on real test answers its additions are clearly unrelated (examples below). That breaks the organisers' "must support Reactor's answer" rule.

## 3. Test answers (no gold): how many citations each policy changes

The 64 answered test questions break down by route as ku 9, multi 12, ssa 11, ssu 16, temporal 16.

Reactor's citations against our cite_plan:
- **ssa:** 12/12 single cites inside the plan.
- **temporal:** 18/18 cite 2 sessions inside the plan, and computed matches.
- **ku:** 9/9 cite 2 sessions; 2 of them fall outside the plan.
- **multi:** 3 answers cite outside the plan.
- **ssu:** 5 answers cite outside the plan. In 2 of them our `computed` differs from Reactor's answer.
- **Uncited answers:** 0.

| policy | answers changed | sessions added | sessions removed | changed per route |
|---|---|---|---|---|
| b_finalize (current) | 2 | 2 | 0 | ku 2 |
| c_computed / c_strict | 2 | 2 | 0 | ku 2 (only the b changes) |
| d_plan_union | 17 | 28 | 0 | ku 2, multi 12, ssu 3 |
| e_contain_g | 3 | 3 | 0 | ku 2, ssu 1 |
| e_contain_raw | 6 | 7 | 0 | ku 2, multi 3, ssu 1 |
| f_drop_g / f_drop_raw | 2 | 2 | 1 | ku 2 |
| rec | 3 | 3 | 0 | ku 2, ssu 1 |
| b2 (proposed finalize core) | 0 | 0 | 0 | removes the 2 current ku-chain additions |
| g_reply_rows / rec2 (proposed) | 1 | 2 | 0 | multi 1 |

Examples for a human to judge "does this session support the answer". "contains" means Reactor's normalized answer string appears in the session.

**b_finalize (current ku-chain), 2 of 2:**
- `q_e165458f4cff` [ku] "What is my current monthly rent?"
  - Reactor: "9,000 shillings [E2][E3]". Its own working lists E2 = 22,000 (earlier value) and E3 = 9,000 (latest). Plan = E1, E2.
  - ADD E1 (2023-04-14): "my rent is 18,000 shillings a month". This is an older value still; doubtful.
- `q_8e9be6f580d2` [ku] "store where I currently buy Moroccan spices"
  - Reactor: "Marrakech Market in Mississauga [E2][E3]". E2 = "ras el hanout from the shop on Danforth" (old store), E3 = new store. Plan = E1, E3.
  - ADD E1 (2023-05-02): a Moroccan dinner menu that names no store. Not support. Wrong.

**c_computed:** the same 2 as b. Computed-chain itself fires 0 times on test.

**d_plan_union, 10 of 17:**
- `q_40f751819121` [ssu] cat's name: Reactor "Fig [E1]", computed = Sombra.
  - ADD E3: "What's her name? — Sombra." This contradicts Reactor's answer.
- `q_068d0a4b3f7b` [multi] ceramic pieces in the class show: Reactor "5 [E6][E7]".
  - ADD E2: "the new cat keeps knocking over my clay pieces". Not a count.
- `q_6dd9e5e4fb97` [multi] watercolour classes per week: Reactor "2 [E5][E6]".
  - ADD E3: possums in the veggie patch. Unrelated.
  - ADD E2: "only have one regular watercolour class, on Saturday mornings". Supports.
  - ADD E7: "My friend Helen goes to a watercolour class". Decoy.
- `q_eefdc20af97b` [multi] vegetable varieties since April: Reactor "5 [E1][E3][E5][E6]".
  - ADD E4: quick-dinner chat, which Reactor explicitly excluded (herbs).
- `q_91ae9daa0edc` [multi] car savings: Reactor "37,500 [E1][E4]".
  - ADD E2: "saving for a used car… 180,000 KES so far". Reactor excluded it as plans or running totals.
- `q_e165458f4cff` [ku]: same as the b example.
- `q_1969c49ff4e7` [ssu] milonga name: Reactor "La Catrina [E1]".
  - ADD E2: Valentina's festival ticket. Unrelated.
- `q_b5232f0c896b` [ssu] French tutor: Reactor "Camille [E1]".
  - ADD E2: Moulin de Paris flour. Unrelated.
- `q_31e7201b2c55` [multi] tango shoes total: Reactor "6,200 pesos [E1][E3][E5]".
  - ADD E6: cheap dinner ideas. ADD E2: weekly dinner plan. Both unrelated; Reactor excluded them.
- `q_bb61022c7cfc` [multi] dulce de leche total: Reactor "8 [E1][E3]".
  - ADD E4: French and tango practice. Reactor excluded E4 (the test batch).

**e_contain_g, 3:** the two ku-chain cases above, plus:
- `q_2ea50c2672ba` [ssu] sourdough starter name: Reactor "Masa [E3]".
  - ADD E2, which contains the answer: "they use 'levain' for sourdough starter, not 'masa madre'… a starter named Herman". A decoy. This is why the guard now requires 2 or more content words.

**e_contain_raw, 6:** the 3 above, plus:
- `q_068d0a4b3f7b` [multi]: adds E5 because "5" appears in text about the cat yowling at 5 a.m. Wrong.
- `q_43e6976bec02` [multi] systolic readings over 130: adds E1 (orchids, "three hours of sun") and E6. Both wrong.
- `q_90f7c27a95f2` [multi] grandchildren "2": adds E5 (camping, "5-6 people"). Wrong.

**f_drop_g / f_drop_raw, 2:** the two ku-chain cases. On `q_8e9be6f580d2` it also DROPs E2, the "shop on Danforth" old store, which was a correct citation. Wrong.

**rec, 3:** the same as e_contain_g (it includes the Masa decoy).

**g_reply_rows / rec2 (proposed), 1:**
- `q_6dd9e5e4fb97` [multi] watercolour classes per week: Reactor "2 [E5][E6]". Reactor's working lists E1 → 1, E2 → 1, E5 → 2, E6 → 2, and "E7 Helen → ignored".
  - ADD E1 (2023-04-22): "My Saturday morning watercolour class is taught by Margaret".
  - ADD E2 (2023-05-16): "At the moment I only have one regular watercolour class, on Saturday mornings".
  - Both state the Saturday class, which is one of the 2 counted. They support the answer.

## 4. Dry run of the proposed finalize

`finalize_proposed.py` was run on the 75-row test snapshot with the v3, v2 and v1 pack files, writing only to the scratchpad. It produced 75 predictions with 0 format errors and 0 answers without citations. It made 1 attribution change ("q_6dd9e5e4fb97: reply-rows +2"). The 2 current ku-chain additions are gone. Its `attribute()` reproduces the calibration numbers exactly (e1 0.778/0.875, e1b 0.734/0.904).

## Caveats

- The real-answer calibration is small (13 + 8 answered). The rule-precision numbers come from a simulation that uses gold answers and simulated citation behaviour.
- Reply-rows depends on Reactor's free-text format. The current prompt produces "date | [E#] | item | n" rows, and the parser stops at "Excluded…" and skips rows with not/✗/decoy/friend/planned.
- Re-run `cit_rules.py test2 runs/final/v1_results.jsonl` once the queue finishes, and look at any new changes before submitting.

## Summary table

| policy | e1 answered F1 (n=8, no labels) | e1b answered F1 (n=13) | e1b F1 over answerable (n=16) | dev sim F1, one-cite base (ALL) | dev200 sim F1, one-cite base (ALL) | test answers changed (of 64) | verdict |
|---|---|---|---|---|---|---|---|
| a own citations | 0.000 | 0.853 | 0.693 | 0.748 | 0.763 | 0 | baseline |
| b current finalize (fill-missing + ku-chain) | 0.625 | 0.853 | 0.693 | 0.761 | 0.775 | 2 (ku; 1 clearly unsupported) | fix the ku-chain trigger |
| c b + computed-chain | 0.625 | 0.853 | 0.693 | 0.776 | 0.790 | 2 (same as b) | ENABLE (temporal adds 23/23 and 5/5 gold) |
| d own ∪ cite_plan | 0.958 | 0.894 | 0.726 | 0.915 | 0.905 | 17 (ku 2, multi 12, ssu 3; mostly unrelated sessions) | REJECT (does not support the answer) |
| e_g b + containment (not bare small number) | 0.625 | 0.878 | 0.714 | 0.776 | 0.794 | 3 (incl. the Masa decoy) | only with the 2-word guard |
| e_raw b + containment, unguarded | 0.625 | 0.827 | 0.672 | 0.776 | 0.785 | 6 (multi number decoys) | REJECT |
| f_g drop own cites without the answer | 0.625 | 0.853 | 0.693 | 0.761 | 0.775 | 2 (drops a correct ku old-store cite) | REJECT |
| f_raw | 0.625 | 0.782 | 0.635 | 0.761 | 0.775 | 2 | REJECT |
| b2 fuzzy fill-missing + single-cite ku-chain | 0.875 | 0.853 | 0.693 | 0.761 | 0.775 | 0 (removes the 2 bad ku-chain adds) | ENABLE |
| g b2 + multi reply-rows | 0.875 | 0.878 | 0.714 | n/a (needs replies) | n/a | 1 (watercolour; supports) | ENABLE |
| rec2 = proposed finalize (b2 + c + contain2 on ssu/ssa/ku/temporal + reply-rows on multi) | 0.875 | 0.904 | 0.734 | 0.782 | 0.802 | 1 | ENABLE |

## Recommendation (rules agent)

Adopt the full proposed `finalize.py` (rec2). Every rule cites only sessions that contain Reactor's answer, hold the values our code computed, or that Reactor itself listed as counted instances. Per route:
- **ssu / ssa:** fuzzy fill-missing, plus containment for answers with at least 2 content words or a 4+ digit number. No plan-union.
- **multi:** fuzzy fill-missing (including "N + question noun"), plus reply-rows. No containment and no plan-union.
- **ku:** fill-missing, ku-chain only when Reactor cites exactly one session (today's trigger misfires 2/2 on test), plus guarded containment.
- **temporal:** fill-missing, computed-chain (±1 day), plus guarded containment.

Reject plan-union (d) and drop-unsupported (f).

Expected effect:
- e1b answered F1 0.853 → 0.904; e1 answers without labels 0.625 → 0.875.
- On the current test answers, 1 answer changes (watercolour, reply-rows) and 2 doubtful ku-chain additions are removed.

Do not edit `finalize.py` until the queue is done, and re-run `.venv/bin/python runs/citations/cit_rules.py test2 runs/final/v1_results.jsonl` on the final results first. The diff below is also saved as `runs/citations/finalize.diff`, and the full file as `runs/citations/finalize_proposed.py`. A dry run on the 75-row test snapshot gave 0 format errors.

```diff
--- a/reactorq/finalize.py
+++ b/reactorq/finalize.py
@@ -10,8 +10,15 @@
 support Reactor's answer"):
 - fill-missing: an answer without [E#] labels gets the passages of its pack whose text contains the answer, or, for a
   value our code computed and Reactor repeated, the pack's planned citations (the sessions the computation used).
-- ku-chain: on the knowledge-update route, when Reactor cites one session of the old/new pair our timeline planned,
-  the other session of that pair (the earlier statement of the same attribute, which the update supersedes) is added.
+- ku-chain: on the knowledge-update route, when Reactor cites exactly ONE session and it belongs to the old/new pair our
+  timeline planned, the other session of that pair (the earlier statement the update supersedes) is added. When Reactor
+  already cites two or more sessions it has given its own old/new pair, and nothing is added.
+- computed-chain: when Reactor's number equals the value our code computed (days +/-1), the sessions holding the dates /
+  values the computation used (cite_plan) are cited.
+- containment: on ssu / ssa / ku / temporal, every packed session that contains Reactor's whole answer phrase is cited,
+  only for answers of >= 2 content words or a >= 4-digit number (one-word answers hit decoys: 'Masa' in 'masa madre').
+- reply-rows: on the multi route, the sessions Reactor listed as counted instances in its own working
+  ('date | [E#] | item | n' rows, not the excluded ones) are cited.
 """
 from __future__ import annotations
 
@@ -37,28 +44,112 @@
     return m.group(0) if m else None
 
 
-def attribute(pred: dict, pack: dict | None, fill_missing: bool, ku_chain: bool) -> tuple[dict, str | None]:
+_STOP = set("the a an of in on at to for and or my i me with from by is was it this that day days week weeks month "
+            "months year years time times".split())
+_DAYQ = re.compile(r"\bhow many (days|weeks|months|years)\b|\bhow long\b|\bhow old\b", re.I)
+_ROW_E = re.compile(r"\[?E(\d+)\]?")
+_ROW_BAD = re.compile(r"(?i)exclud|\bnot\b|ignor|decoy|reject|✗|drop|outside|skip|plan(?:ned|s)?\b|other person|"
+                      r"friend|no user|never|n't|irrelevant|unrelated")
+_ROW_STOP = re.compile(r"(?i)^(excluded|decoys?|notes? on what|choices|two things|the one|\(excluded)")
+
+
+def _stoks(s: str) -> list[str]:
+    """normalized tokens, plural-insensitive ('55 inches' ~ '55-inch')."""
+    out = []
+    for t in normalize(s or "").split():
+        out.append(t[:-2] if len(t) > 4 and t.endswith("es") else t[:-1] if len(t) > 3 and t.endswith("s") else t)
+    return out
+
+
+def _contains(text: str, ans: str) -> bool:
+    return bool(ans) and f" {ans} " in f" {normalize(text)} "
+
+
+def _supports(text: str, answer: str, question: str) -> bool:
+    """the passage states the answer: exact phrase, plural/hyphen-insensitive phrase, or for a bare number N
+    'N <noun of the question>' ('7 shirts', 'four bikes')."""
+    ans = normalize(_LABELS.sub("", answer))
+    if len(ans) > 1 and _contains(text, ans):
+        return True
+    a, t = _stoks(_LABELS.sub("", answer)), _stoks(text)
+    if not a:
+        return False
+    if (len(a) > 1 or not a[0].isdigit()) and f" {' '.join(a)} " in f" {' '.join(t)} ":
+        return True
+    if len(a) == 1 and a[0].replace(".", "").isdigit():
+        nouns = {x for x in _stoks(question) if len(x) >= 4 and x not in _STOP and not x.isdigit()}
+        return any(x == a[0] and any(y in nouns for y in t[i + 1:i + 4]) for i, x in enumerate(t))
+    return False
+
+
+def _specific(answer: str) -> bool:
+    """distinctive enough that 'the passage contains it' means 'the passage supports it'."""
+    toks = normalize(_LABELS.sub("", answer)).split()
+    content = [t for t in toks if not t.isdigit() and t not in _STOP and len(t) >= 3]
+    return len(content) >= 2 or any(t.replace(".", "").isdigit() and len(t.replace(".", "")) >= 4 for t in toks)
+
+
+def _computed_match(answer: str, pack: dict) -> bool:
+    if pack.get("computed") is None:
+        return False
+    a, b = _num(answer), _num(str(pack["computed"]))
+    if a is None or b is None:
+        return False
+    if a == b:
+        return True
+    try:
+        return bool(_DAYQ.search(pack.get("question", ""))) and abs(float(a) - float(b)) == 1
+    except ValueError:
+        return False
+
+
+def _reply_rows(reply: str) -> list[int]:
+    """E numbers of the instance rows Reactor counted in its own working (before its 'Excluded' notes)."""
+    out = []
+    for line in (reply or "").split("# FINAL ANSWER")[0].splitlines():
+        s = line.strip()
+        if _ROW_STOP.match(s):
+            break
+        if ("|" in s or "→" in s) and not _ROW_BAD.search(s):
+            es = set(_ROW_E.findall(s))
+            if len(es) == 1:
+                out.append(int(es.pop()))
+    return out
+
+
+def attribute(pred: dict, pack: dict | None, fill_missing: bool, ku_chain: bool, reply: str = "",
+              computed_chain: bool = True, contain: bool = True, reply_rows: bool = True) -> tuple[dict, str | None]:
     if pred["abstain"] or pack is None:
         return pred, None
     cites = list(pred["citations"])
-    note = None
+    notes = []
+    ids = [p["id"] for p in pack["passages"] if p.get("id")]
+    route = pack.get("route")
+
+    def add(sids, why):
+        new = [s for s in sids if s and s not in cites]
+        if new:
+            cites.extend(new)
+            notes.append(f"{why}: +{len(new)}")
+
     if fill_missing and not cites:
-        ans = normalize(_LABELS.sub("", pred["answer"]))
-        support = [p["id"] for p in pack["passages"] if p.get("id") and ans and len(ans) > 1
-                   and f" {ans} " in f" {normalize(p['text'])} "]
-        if not support and pack.get("computed") is not None and _num(pred["answer"]) is not None \
-                and _num(pred["answer"]) == _num(str(pack["computed"])):
-            support = [s for s in pack.get("cite_plan") or []]
-        if support:
-            cites = list(dict.fromkeys(support))
-            note = f"filled {len(cites)} citation(s): answer had no [E#] labels"
-    if ku_chain and pack.get("route") == "ku" and cites:
+        support = [p["id"] for p in pack["passages"] if p.get("id")
+                   and _supports(p["text"], pred["answer"], pack.get("question", ""))]
+        if not support and _computed_match(pred["answer"], pack):
+            support = list(pack.get("cite_plan") or [])
+        add(support, "fill-missing (answer had no [E#] labels)")
+    if ku_chain and route == "ku" and len(cites) == 1:
         plan = [s for s in (pack.get("cite_plan") or []) if s]
-        if len(plan) == 2 and len(set(cites) & set(plan)) == 1:
-            other = (set(plan) - set(cites)).pop()
-            cites.append(other)
-            note = (note + "; " if note else "") + "ku-chain: added the superseded statement's session"
-    return {**pred, "citations": cites}, note
+        if len(plan) == 2 and cites[0] in plan:
+            add([s for s in plan if s != cites[0]], "ku-chain (superseded statement)")
+    if computed_chain and cites and _computed_match(pred["answer"], pack):
+        add(pack.get("cite_plan") or [], "computed-chain (sessions the computed value came from)")
+    if reply_rows and cites and route == "multi":
+        add([ids[k - 1] for k in _reply_rows(reply) if 1 <= k <= len(ids)], "reply-rows (instances Reactor counted)")
+    if contain and cites and route in ("ssu", "ssa", "ku", "temporal") and _specific(pred["answer"]):
+        ans = normalize(_LABELS.sub("", pred["answer"]))
+        add([p["id"] for p in pack["passages"] if p.get("id") and _contains(p["text"], ans)], "containment")
+    return {**pred, "citations": cites}, ("; ".join(notes) or None)
 
 
 def main(argv=None) -> int:
@@ -69,6 +160,9 @@
     ap.add_argument("--out", required=True)
     ap.add_argument("--no-fill-missing", action="store_true")
     ap.add_argument("--no-ku-chain", action="store_true")
+    ap.add_argument("--no-computed-chain", action="store_true")
+    ap.add_argument("--no-contain", action="store_true")
+    ap.add_argument("--no-reply-rows", action="store_true")
     a = ap.parse_args(argv)
     best: dict[str, dict] = {}
     for f in a.results:
@@ -106,7 +200,9 @@
         for p in preds:
             r = best.get(p["question_id"], {})
             pack = packs_by_hash.get(r.get("pack_hash")) or packs_by_q.get(p["question_id"])
-            p2, note = attribute(p, pack, not a.no_fill_missing, not a.no_ku_chain)
+            p2, note = attribute(p, pack, not a.no_fill_missing, not a.no_ku_chain, reply=r.get("reply") or "",
+                                 computed_chain=not a.no_computed_chain, contain=not a.no_contain,
+                                 reply_rows=not a.no_reply_rows)
             if note:
                 notes.append(f"{p['question_id']}: {note}")
             fixed.append(p2)
```
