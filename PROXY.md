# Reactor simulator on a second Mac (experiment, 06:15–07:30)

A local LLM (MLX) answers our evidence packs in Reactor's exact message format. We use it only to compare variants on
training data. **Nothing it produces goes into the submission.** Every line it writes carries `"proxy": true`, it writes
only under `runs/proxy/`, and `reactorq.finalize` refuses both.

## What you get (one archive, <1 MB)
`proxy_kit.tar.gz` holds:
- the code: `librarian/core`, `librarian/reactorq`;
- the organisers' kit, `memory-challenge/` (its `client.py` builds and parses the messages, its `score.py` scores);
- dev and dev200 `questions.jsonl` + `gold.jsonl`;
- the 28 calibration packs that the real Reactor answered (E1/E1b), plus its answers;
- the experiment packs.

No embeddings, no histories and no Reactor key are needed: we built the packs on the team machine, which has the caches.

## Setup on the M5 (start the model download first, it is the slowest step)
```sh
# 0. model, ~8.3 GB (fallback if the network is slow: mlx-community/Qwen2.5-7B-Instruct-4bit, ~4.3 GB)
pip3 install -U "huggingface_hub[cli]" && huggingface-cli download mlx-community/Qwen2.5-14B-Instruct-4bit &

# 1. unpack the kit (AirDrop proxy_kit.tar.gz to ~/Downloads)
mkdir -p ~/proxy && cd ~/proxy && tar -xzf ~/Downloads/proxy_kit.tar.gz
cd ~/proxy/librarian

# 2. Python env (uv if present, else python3 -m venv)
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python mlx-lm
#   or: python3 -m venv .venv && .venv/bin/pip install mlx-lm

# 3. smoke test, 3 packs: FINAL ANSWER lines parsed? seconds per question?
.venv/bin/python -m reactorq.proxy_reader run --packs runs/proxy/packs/cal_packs.jsonl --out runs/proxy/smoke.jsonl --limit 3
```

## Run
```sh
# A. calibration, 28 questions the real Reactor already answered (~5 min)
.venv/bin/python -m reactorq.proxy_reader run --packs runs/proxy/packs/cal_packs.jsonl --out runs/proxy/cal_proxy.jsonl
.venv/bin/python -m reactorq.proxy_reader calib --split dev --proxy runs/proxy/cal_proxy.jsonl \
    --reactor runs/reactor/e1_results.jsonl runs/reactor/e1b_results.jsonl
#   rows marked "unj" (string matcher could not decide): judge by eye, write lines like  P:q_123=correct  R:q_456=wrong
#   into runs/proxy/resolve.txt, then re-run calib with --resolve runs/proxy/resolve.txt

# B. only on GO: experiments, in this order (each 2 x up to 40 questions)
for e in notes multi ssa; do
  .venv/bin/python -m reactorq.proxy_reader run --packs runs/proxy/packs/exp_${e}_A.jsonl --out runs/proxy/exp_${e}_A.jsonl
  .venv/bin/python -m reactorq.proxy_reader run --packs runs/proxy/packs/exp_${e}_B.jsonl --out runs/proxy/exp_${e}_B.jsonl
  .venv/bin/python -m reactorq.proxy_reader ab --a runs/proxy/exp_${e}_A.jsonl --b runs/proxy/exp_${e}_B.jsonl
done
# C. 07:30: AirDrop the whole runs/proxy/ folder back to the team machine
```
| Experiment | A (current v3) | B (alternative) | Question |
|---|---|---|---|
| `notes` | temporal packs with our margin notes (dates, computed day gap) | same packs, notes removed | Do the notes help the reader? |
| `multi` | tight multi packs (fewer sessions) | wider deep8 packs | Does breadth help counting? |
| `ssa` | lens A: top session + quoted recommendation line | lens B: whole top session, no quote | Which helps recommendations? (offline tie) |

## Stop / go
| When | Condition | Action |
|---|---|---|
| 06:50 | the smoke test is not answering yet (download or install stuck) | **STOP**, nothing lost |
| after calibration | all 7 `calib` checks PASS: FINAL ANSWER parsed ≥ 27/28; no unresolved "unjudged"; correct/wrong agreement with Reactor ≥ 83%; catches at least half of Reactor's own errors; abstains on unanswerable (≥ n−1); false abstentions ≤ Reactor's + 2; median ≤ 15 s/question | **GO** to the experiments; else **STOP** |
| any experiment | `ab` prints "prefer B": B ≥ +3 net questions and ≥ 60% of decisive pairs | candidate change; the team machine re-checks offline S/Sall, rebuilds only the affected test packs and re-asks them on the **real** Reactor (at most 40 re-asks, done by 09:00) |
| any experiment | "no reliable difference" or "prefer A" | keep v3 |
| 07:30 | hard stop, whatever is running | send `runs/proxy/` back |

Caveat: 28 calibration questions can reject a bad simulator but cannot prove a good one, so a GO makes the simulator a
tie-breaker, never the final word. Real-Reactor answers stay the only answers in the submission.

## Option B: building packs on the M5 (not needed for this plan)
This needs the embedding cache so nothing is re-embedded:
- `librarian/cache/models.sqlite` (+ `-wal`, ~0.9 GB);
- `data/dev*/histories.jsonl`;
- the full venv: torch, sentence-transformers, bm25s, PyStemmer, dateparser;
- `python -m core.model_server` (downloads the two small models, ~150 MB).

Cached embeddings and reranker scores are keyed by text hash, so only new text is computed.
