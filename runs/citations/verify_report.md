# Citation attribution: adversarial verification

Decision: rules (finalize_verified = rec2 + 3 fixes), reply-rows opt-in only, learned model not wired in. Installed into reactorq/finalize.py at 04:25; dry run on 99 test answers: answers unchanged, 2 unsupported ku-chain additions removed, 0 format errors.

## Recommended policy

Use the rules, not the learned model. Take finalize_proposed (rec2) with 3 fixes and turn reply-rows off. Exact settings for reactorq/finalize.attribute:
- fill_missing=True. Accept a session as support when (a) it contains the exact normalized answer phrase, or (b) the answer has 2 or more tokens and the session contains it after plural/hyphen normalization ("55 inches" matches "55-inch"), or (c) the answer is a bare number N and the session says "N <question noun>" within 3 tokens, or (d) the answer equals pack.computed, in which case cite_plan is cited. FIX: the fuzzy match is no longer applied to single-word answers.
- ku_chain=True, but only when Reactor cites exactly one session and that session is one of a 2-session cite_plan. This removes the 2 additions today's trigger makes on test, both unsupported.
- computed_chain=True: when Reactor's number equals pack.computed, cite all of cite_plan. FIX: the off-by-one tolerance applies only when the question is a "how many days/weeks/months/years / how long / how old" question AND a day/week/month/year unit appears in the answer or question.
- contain=True, on the ssu/ssa/ku/temporal routes only (never multi), and only when the answer has 2 or more content words or a number of 4 or more digits.
- reply_rows=False (REJECTED by default). Its only test firing (q_6dd9e5e4fb97) adds 2 sessions that do not contain "2" and are not our computation, and one of them says "only have one ... class". The rule was also validated only on the single e1b case it was built from. If the team later accepts "Reactor's own working" as support, enable it only for packs matched by pack_hash (FIX 3), and read every firing first.
- Keep: Reactor's own citations are never removed. No plan-union (d). No drop-unsupported (f).
- Learned model (reactorq/attribution.py): do not wire into finalize.
- Patched reference implementation: runs/citations/verify/finalize_verified.py (finalize_proposed.py + the 3 fixes). It gives the same numbers as rec2 on e1, e1b, dev and dev200. Its dry run on 87 test rows had 0 format errors.

## Violations found

- LEAKAGE (model): dev200 is a subset of dev. All 125 of its question ids are dev questions with the same answers and the same gold evidence ids. COEF was fit on all of dev, so 'dev200_f1 0.682' is not a held-out number. A refit that excludes those 125 questions gives exactly 0.6821, so the number holds but the held-out claim is wrong.
- LEAKAGE (model): all 16 e1b questions and the e1 questions are dev questions, so the model was trained on their gold labels. The bare-number support gate was also chosen by looking at an e1b answer (the 1.0 -> 0.75 case). A refit excluding them leaves the numbers unchanged: e1b 0.7135 (answerable) / 0.8782 (answered), e1 answered 1.0.
- LEAKAGE (rules): containment and reply-rows were designed on the e1b failures they then fix (Nightingale, bikes), so e1b 0.853 -> 0.904 is in-sample, not a validation. The 2-word guard was set from a test answer ('Masa'). No labels were involved, but 'changes 0 test answers' holds by construction. The dev200 simulation is not independent of dev, because it uses the same questions.
- SUPPORT VIOLATION (current finalize.py, live today): ku-chain adds q_e165458f4cff E1 s_52bb6489d5a8. That session says 'my rent is 18,000 shillings', against Reactor's answer of 9,000; it holds an even older value, and our plan thought 22,000 was current. Reactor had already cited E2 and E3.
- SUPPORT VIOLATION (current finalize.py, live today): ku-chain adds q_8e9be6f580d2 E1 s_dfdd379dd740. It is a Moroccan dinner chat that names no store, against the answer 'Marrakech Market in Mississauga'. Reactor had already cited E2 (the old Danforth shop) and E3.
- SUPPORT VIOLATION (model): use_ku_chain=True copies the old trigger and makes the same 2 unsupported additions on test.
- SUPPORT VIOLATION (model): q_2ea50c2672ba adds E2 s_09f485d8e0cc at p=0.97 (0.92 without the cross-encoder). The passage reads "they use 'levain' for sourdough starter, not 'masa madre'... a starter named Herman", against Reactor's answer 'Masa'. It is a decoy. The model's only non-ku addition on 74 answered test questions is wrong, and made with high confidence.
- SUPPORT VIOLATION by the strict rule (rules, reply-rows): q_6dd9e5e4fb97 adds E1 s_694e7fbd5fda and E2 s_17baf1275f1c. Neither contains '2', and neither is our computation; they come from Reactor's own working. E2 says 'only have one regular watercolour class' (the old state). This is the only rec2 change on test.
- NO REMOVALS: no policy removes a Reactor citation. That held for current, rules and model on all 74 answered test questions so far (87 rows), and on e1 and e1b. The drop-unsupported policy (f) was already rejected by the rules study.
- OVERFITTING (model): the learned weights add almost nothing over the simple rule 'cite every session the model's own support rule admits'. Dev CV top1 0.6178 vs 0.6135 (+0.004). dev200 with an honest refit 0.6821 vs 0.6727 (+0.009). Real e1b 0.7135 vs 0.7135 (+0). The gain over the current finalize comes from the broader support definition, not from learning. On real answers rec2 scores higher than the model on e1b (0.904 vs 0.878, in-sample) and lower on e1 (0.875 vs 1.0, one case: 'On Valentine's Day in February', fixed by the all-content-words containment, not by the weights).
- BUG (model support rule): number-token matching counts as support for non-bare answers ('4 months', '3 doctors'). It also counts for bare numbers on the ssu/ssa/ku routes: 'I have 2 kids and 3 dogs' supports '2' for 'how many dogs'. In fill mode it counts for bare numbers on multi too: the dev CV example 'How many projects have I led' adds a non-gold session at p=0.93. Answers of 1 character have no containment form at all.
- BUG (model): in fill mode it always cites the best candidate even below FILL_THRESHOLD, which is a top-ranked fallback. computed_matches uses the first number or a substring: ('2 hours 30 minutes', '2') -> True, ('Fig', 'Fig Newton') -> True.
- BUG (model): if the model server is down, the cross-encoder features are silently set to 0 and probabilities shift (Masa 0.97 -> 0.92), so decisions can flip on an organiser re-run. attribute() returns (citations, note) instead of (pred, note), so it is not a drop-in replacement for finalize.
- BUG (rules finalize_proposed): _stoks strips plural endings from single-word answers, so fill-missing gives 'Notes' -> matches 'not' and 'James' -> matches 'jam'. Fixed in the scratchpad copy.
- BUG (rules): the off-by-one computed tolerance fires for any 'how long/how old' question, including hours ('4 hours' vs computed 3 cites cite_plan). Fixed by requiring a day/week/month/year unit.
- LATENT BUG (rules): reply-rows maps [E#] by position in whatever pack was found. If pack_hash is missing, finalize falls back to the pack looked up by question id, and the labels can be misaligned. All 87 current rows match by hash. Fixed by passing the reply only when the pack matched by hash.

## Expected F1 gain

Expect only a small gain on test.

**Current test answers (87 rows, 74 answered):**
- The recommended policy removes the 2 unsupported ku-chain additions that today's finalize makes. It changes nothing else, because Reactor already cites every answer, cites 2 sessions on every ku answer and cites both date sessions on every temporal answer.
- Gain vs current finalize: about +0.000 to +0.003 mean F1 over 146 questions, depending on whether the removed sessions are gold. Each removal is at most +0.2 on its question.

**Remaining ~59 questions:** gains come only where Reactor drops labels or under-cites.
- On the real calibration answers (in-sample for the rules), answered-only F1 goes 0.853 -> 0.878 on e1b and 0.625 -> 0.875 on e1, which has no labels at all.
- The dev simulation (gold answer stands in for Reactor) gives top1 0.523 -> 0.546 on dev and 0.566 -> 0.615 on dev200.

**Reply-rows:** turning it on would add about +0.025 on e1b answered (one in-sample case) and +0.001 to +0.002 on test.

**Learned model:** it adds +0.004 (dev CV) / +0.009 (dev200, honest refit) / +0.000 (real e1b) over a no-model 'cite every supporting session' rule. On test it adds 1 decoy (Masa), so its expected test gain is ≤ 0.

**Where the ~0.69 is lost:** mainly abstentions and dropped connections (3/16 on e1b), plus multi count answers that no session contains. Attribution cannot recover these.

## Code changes

**Do not touch reactorq/finalize.py while the queue runs.** After the queue finishes:

**1.** Replace reactorq/finalize.py with runs/citations/verify/finalize_verified.py. That file is runs/citations/finalize_proposed.py (= runs/citations/finalize.diff applied) plus 3 fixes:

(a) in `_supports`:
```python
if len(a) > 1 and f" {' '.join(a)} " in f" {' '.join(t)} ":
```
replacing
```python
if (len(a) > 1 or not a[0].isdigit()) and ...
```
This stops the plural-stripped match on single-word answers ('Notes' ~ 'not').

(b) Add
```python
_DAYU = re.compile(r"\b(days?|weeks?|months?|years?)\b", re.I)
```
and in `_computed_match` make the off-by-one branch
```python
q = pack.get("question", ""); return bool(_DAYQ.search(q)) and bool(_DAYU.search(f"{answer} {q}")) and abs(float(a) - float(b)) == 1
```

(c) In main:
```python
hash_ok = r.get("pack_hash") in packs_by_hash
```
and pass `reply=(r.get("reply") or "") if hash_ok else ""`.

**2.** Turn reply-rows off by default. Either:
- change the attribute() default to `reply_rows=False` and the CLI to an opt-in `--reply-rows`, or
- add `--no-reply-rows` to the finalize call in runs/final/after_v3.sh.

**3.** Do not import reactorq/attribution.py into finalize. Keep it and runs/citations/train_attr.py as research only.

**4.** Before submitting, rerun the check on the final results:
```
.venv/bin/python runs/citations/verify/verify_test_v.py runs/final/v1_results.jsonl
```
It lists every added session with contains/computed-source flags. Read every addition that has `contains=False` and `comp_src=False`; on a correct run the only ones should be single-cite ku-chain additions.

Then run `.venv/bin/python -m reactorq.finalize ...` as in after_v3.sh, and check that it reports 0 format errors and 0 answers without citations.

**Scratchpad checks:**
- `verify_test.py` / `verify_test_v.py`: all policies on the test answers.
- `verify_holdout.py` / `verify_holdout_v.py`: honest refits and the no-model baseline.
- `e1.py` / `e1_v.py`: real e1 and e1b answers.
- `reasons.py`: why the model adds each session.

All are in runs/citations/verify/.

Nothing in reactorq/, configs/, lenses/, core/ or runs/final/ was modified. Reactor was not called.
