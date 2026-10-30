# Temporal lens B ("Semantyka"): round 1 report

Code: `lenses/temporal/b_sem.py` (round-1 routes, imports helpers from `b_evcal.py`), `lenses/temporal/b_evcal.py` (round-0 event calendar, unchanged).
Runs: `runs/r1-temporal-b/temporal/{generic,b_evcal,b_sem}/<variant>/{dev,dev200}`. Test audit: `lenses/temporal/scratch_b/audit_sem_user.txt`.

Context: the shared model server was saturated for most of the round (13 sweeps from all agents at once). A cold cross-encoder call took 17–25 s and a cold query embedding up to 22 s, so the first sweeps ran 25–30 minutes each. After the CE cache was warm, a full dev sweep took 8 s. That is why b_evcal was swept on `--limit 40` only.

## Variants tried (one line each)
| variant | idea / params |
|---|---|
| `b_evcal:evcal` | Round-0 event calendar: per event, pool = dated units ∪ hybrid(event, 30) ∪ anchor window; CE(event) plus features (subject self/other, contrast, year, overlap, explicit date); top-2 per event plus hybrid(question) fill; budget 7k; computed gap; cite top-1 session per event. |
| `b_evcal:evcal_gated` | As evcal, but `computed` only when the per-event date margin conf is at least 0.6. |
| `b_evcal:evcal_wide` | k_hyb 50, 3 alternatives per event, budget 12k. |
| `b_evcal:ce_only` | Ablation with every feature weight set to 0 and no time prior (plain CE). |
| `b_sem:sem` | evcal for questions that name events. Questions with no parsed events go to a new whole-question route: hybrid(question, 60) ∪ anchor-window hybrid, CE(question), time prior to the anchor, +1 for user role, budget 10k, cite the sessions within 3 logits of the top (capped by "the three/six …", else 3). |
| `b_sem:sem_gated` | sem plus the 0.6 gating of the computed value. |
| `b_sem:sem_user` | **Best (accepted).** sem_gated, but the whole-question route searches USER turns only and uses window 0, so more sessions fit. Every dev gold turn is a user statement ("… today"). |
| `b_sem:sem_turns` | sem_user, plus the event route packs every user unit of the cited sessions that shares an event token. Fixes ATR 0.5 on "first" questions. Event budget 7k. |
| `b_sem:sem_turns9` | sem_turns with an event-route budget of 9k. **Candidate**: +1.6 dev / +2.5 dev200 over sem_user, so it misses the +2 dev bar. |
| `b_sem:sem_dense` | Bi-encoder cosine instead of the CE (DenseHX wrapper). Written but not swept: a direct timing check showed no speedup while the server queue was the bottleneck. |

## Results
Full dev (133 q, 127 answerable) and dev200 (26 q, 22 answerable):

| split | variant | S | PA | ATR | SR | CF1 | chars | AUC |
|---|---|---|---|---|---|---|---|---|
| dev | generic hybrid_rr (baseline) | 65.1 | 0.748 | 0.860 | 0.908 | 0.673 | 11931 | 0.636 |
| dev | sem_gated | 65.9 | 0.677 | 0.854 | 0.918 | 0.813 | 7880 | 0.807 |
| dev | **sem_user** | **73.7** | 0.795 | 0.919 | 0.961 | 0.815 | 7881 | 0.809 |
| dev | sem_turns | 74.2 | 0.803 | 0.913 | 0.945 | 0.815 | 7880 | 0.809 |
| dev | sem_turns9 | 75.3 | 0.827 | 0.940 | 0.957 | 0.815 | 9247 | 0.809 |
| dev200 | generic hybrid_rr (baseline) | 61.2 | 0.727 | 0.849 | 0.910 | 0.589 | 11941 | 0.932 |
| dev200 | sem_gated | 72.1 | 0.773 | 0.871 | 0.933 | 0.810 | 7958 | 0.966 |
| dev200 | **sem_user** | **78.4** | 0.864 | 0.932 | 0.968 | 0.823 | 7957 | 0.955 |
| dev200 | sem_turns | 75.4 | 0.818 | 0.909 | 0.946 | 0.823 | 7968 | 0.955 |
| dev200 | sem_turns9 | 80.9 | 0.909 | 0.955 | 0.968 | 0.823 | 9265 | 0.955 |

First 40 dev questions (none unanswerable, so no AUC). The baseline row is the full baseline run restricted to the same question ids:

| variant | S | PA | ATR | SR | CF1 | chars |
|---|---|---|---|---|---|---|
| generic hybrid_rr | 63.4 | 0.725 | 0.843 | 0.902 | 0.666 | 11926 |
| evcal | 67.2 | 0.700 | 0.823 | 0.890 | 0.795 | 6936 |
| evcal_gated | 68.8 | 0.725 | 0.823 | 0.890 | 0.795 | 6939 |
| evcal_wide | 66.9 | 0.725 | 0.868 | 0.923 | 0.783 | 11930 |
| ce_only | 65.4 | 0.675 | 0.823 | 0.877 | 0.791 | 6932 |
| sem | 69.9 | 0.725 | 0.858 | 0.916 | 0.837 | 7464 |
| sem_gated | 71.5 | 0.750 | 0.858 | 0.916 | 0.837 | 7467 |
| sem_user | 81.5 | 0.900 | 0.933 | 0.965 | 0.846 | 7464 |

What each step showed:
- The features beat the plain CE: evcal 67.2 vs ce_only 65.4.
- Gating `computed` helps: evcal_gated 68.8 vs evcal 67.2.
- The wide pack does not pay: evcal_wide reaches ATR 0.868, but its chars cost more than it gains.
- The whole-question route only pays when it is restricted to user turns: on full dev, sem_gated 65.9 vs sem_user 73.7.

Per kind, sem_user on dev:

| kind | n | S | PA |
|---|---|---|---|
| between | 17 | 87.5 | 0.94 |
| ago | 19 | 75.3 | 0.79 |
| first | 29 | 68.7 | 0.66 |
| other (whole-question route) | 40 | 64.6 | 0.78 |

On "first", CF1 is 0.94 while PA is only 0.66. On "other", CF1 is 0.58. HA is 0.88–0.93 where `computed` is emitted.

## Best variant
`b_sem.py:sem_user`. It beats the generic baseline by 8.6 S on dev and 17.2 S on dev200, with about 4k fewer chars. It is close to lens A's best (ftb_bm25: 74.0 dev / 75.3 dev200).

`sem_turns9` is better on both splits (75.3 / 80.9) but misses the +2 dev rule. It also changes two things at once (session fill and a 9k budget). The ablation still needed is sem_user at 9k.

## Test audit (qualitative, sem_user, n=6)
On the "How many days apart" questions the picks look right:
- The son's play (2023-06-10) is picked and the daughter's orthodontist appointment (2023-06-24) gives 14 days. The decoy "school concert … separate from the play" and the dentist decoy are both rejected.
- "Run for Health" (23 Apr) and the annual gala (9 Sep) give 139 days. The decoys "My friend Helen ran in a 5K …" and "the children's ward held a mini gala" are both rejected.

No general problem showed up in the 6 audited packs.

## Top failure patterns (dev)
1. **Aggregate "ago/since" questions are parsed as one event but need several sessions.** ALL fails.
   - "How many months have passed since I participated in two charity events in a row, on consecutive days?": 4 gold sessions, 1 in the pack.
   - "How many months have passed since I last visited a museum with a friend?": `computed` = 5 is correct, but 2 of the 3 gold sessions are missing.
2. **"first" questions get the right sessions but miss a second gold turn in the same session.** CF1 is 1.0 and ATR 0.5. sem_turns/sem_turns9 target this one.
   - "Which gift did I buy first, the necklace for my sister or the photo album for my mom?"
   - "Which project did I start first, the Ferrari model or the Japanese Zero fighter plane model?"
3. **Event phrases too short to retrieve.** For "Which mode of transport did I use most recently, a bus or a train?" the events "a bus" / "a train" put the gold at rank 35.
4. **Citation precision on the whole-question route.** CF1 is 0.58. A cite gap of 3 logits is too loose for single-answer questions; for example, "I mentioned cooking something for my friend a couple of days ago" gets CF1 0.4 and ALL 0. The other failure is a wrong relative date: "How many weeks had passed since I recovered from the flu when I went on my 10th jog outdoors?" computes 12 where the gold is 15.

## CORE REQUESTs
1. **Model-server throughput and visibility.** Concurrent agents push a cold CE call to 20 s or more. Options:
   - precompute CE(question, hybrid top-100) for all temporal questions on dev, dev200 and test, which already warms the whole-question route;
   - or a per-client fair queue;
   - and `harness.sweep` progress lines (today it is silent for 30 minutes).
2. **Temporal PA** (carried over from round 0): `ALL and (ATR==1 or HA==1)`, with HA reported separately. As it stands, a correct computed gap cannot save a pack that misses one gold turn, and a wrong one zeroes a perfect pack.
3. **`hx.rerank_texts(query, texts)`** (carried over from round 0): sentence-level CE, cached by text hash.

## Ideas for next round
- Send aggregate questions ("last time I…", "in a row", plurals, "how many X before Y") to the whole-question route. Compute the answer from the newest or oldest cited session there.
- Adaptive citation on the whole-question route:
  - cite 1–2 sessions for single-answer questions ("What was …", "Who did I …");
  - cite N sessions for "order of the N …";
  - use a tighter gap otherwise.
- Ablate the 9k budget on sem_user, then adopt sem_turns9 if the session fill holds up on its own.
- Expand short event phrases ("a bus" becomes the question context plus a verb) before the CE.
- Borrow lens A's holiday / "a week before Black Friday" grammar and their first-turn prior. Lens A offers BM25-only speed; we offer CE-based decoy rejection; the two combine naturally.
- Test-only abstain trap: when the event is done only by someone else, abstain. This is already in the hint, but its AUC can only be checked qualitatively on test.
