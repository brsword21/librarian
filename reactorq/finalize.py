"""results.jsonl (possibly with retries) -> submission predictions.jsonl, validated.

    python -m reactorq.finalize --results runs/final/v1_results.jsonl --packs runs/final/v2_test_packs.jsonl \
        runs/final/v1_test_packs.jsonl --split test --out submission/predictions.jsonl
Keeps one line per question (the last answered one, else the last one), converts with the kit's predictions.py
(--abstain-on agent,no-answer) and checks the format with score.validate. Answers are never touched.

Evidence attribution (organisers on Discord: "retrieval and evidence attribution are handled by your code ... if [E#]
labels are missing, your code can select supporting sessions from the retrieved evidence: just make sure they actually
support Reactor's answer"):
- fill-missing: an answer without [E#] labels gets the passages of its pack whose text contains the answer, or, for a
  value our code computed and Reactor repeated, the pack's planned citations (the sessions the computation used).
- ku-chain: on the knowledge-update route, when Reactor cites one session of the old/new pair our timeline planned,
  the other session of that pair (the earlier statement of the same attribute, which the update supersedes) is added.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import core.paths  # noqa: F401  (puts the upstream kit on sys.path)
from score import normalize, validate  # upstream kit

from core.data import questions, read_jsonl, session_ids_file
from core.paths import KIT

_LABELS = re.compile(r"\s*\[\s*E\d+(?:\s*[,;]\s*E\d+)*\s*\]")


def _num(s: str) -> str | None:
    m = re.search(r"-?\d+(?:\.\d+)?", normalize(s or "").replace(",", ""))
    return m.group(0) if m else None


def attribute(pred: dict, pack: dict | None, fill_missing: bool, ku_chain: bool) -> tuple[dict, str | None]:
    if pred["abstain"] or pack is None:
        return pred, None
    cites = list(pred["citations"])
    note = None
    if fill_missing and not cites:
        ans = normalize(_LABELS.sub("", pred["answer"]))
        support = [p["id"] for p in pack["passages"] if p.get("id") and ans and len(ans) > 1
                   and f" {ans} " in f" {normalize(p['text'])} "]
        if not support and pack.get("computed") is not None and _num(pred["answer"]) is not None \
                and _num(pred["answer"]) == _num(str(pack["computed"])):
            support = [s for s in pack.get("cite_plan") or []]
        if support:
            cites = list(dict.fromkeys(support))
            note = f"filled {len(cites)} citation(s): answer had no [E#] labels"
    if ku_chain and pack.get("route") == "ku" and cites:
        plan = [s for s in (pack.get("cite_plan") or []) if s]
        if len(plan) == 2 and len(set(cites) & set(plan)) == 1:
            other = (set(plan) - set(cites)).pop()
            cites.append(other)
            note = (note + "; " if note else "") + "ku-chain: added the superseded statement's session"
    return {**pred, "citations": cites}, note


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", nargs="+", required=True, help="results files, later ones win")
    ap.add_argument("--packs", nargs="*", default=[], help="pack files (first file wins per question)")
    ap.add_argument("--split", default="test")
    ap.add_argument("--out", required=True)
    ap.add_argument("--no-fill-missing", action="store_true")
    ap.add_argument("--no-ku-chain", action="store_true")
    a = ap.parse_args(argv)
    best: dict[str, dict] = {}
    for f in a.results:
        for r in read_jsonl(Path(f)):
            qid = r.get("question_id")
            if not qid:
                continue
            if r.get("status") == "answered" or best.get(qid, {}).get("status") != "answered":
                best[qid] = r
    packs_by_hash, packs_by_q = {}, {}
    for f in a.packs:
        for p in read_jsonl(Path(f)):
            packs_by_hash.setdefault(p["pack_hash"], p)
            packs_by_q.setdefault(p["question_id"], p)
    qids = [q.question_id for q in questions(a.split)]
    missing = [q for q in qids if q not in best]
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8") as tmp:
        for qid in qids:
            if qid in best:
                tmp.write(json.dumps(best[qid]) + "\n")
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run([sys.executable, str(KIT / "reactor" / "predictions.py"), tmp.name, "--histories",
                           str(session_ids_file(a.split)), "--out", str(out),
                           "--abstain-on", "agent,no-answer"], capture_output=True, text=True)
    print(proc.stderr.strip()[-1500:])
    preds = list(read_jsonl(out))
    notes = []
    if a.packs:
        fixed = []
        for p in preds:
            r = best.get(p["question_id"], {})
            pack = packs_by_hash.get(r.get("pack_hash")) or packs_by_q.get(p["question_id"])
            p2, note = attribute(p, pack, not a.no_fill_missing, not a.no_ku_chain)
            if note:
                notes.append(f"{p['question_id']}: {note}")
            fixed.append(p2)
        preds = fixed
        out.write_text("".join(json.dumps(p, ensure_ascii=False) + "\n" for p in preds), encoding="utf-8")
    errors = validate(preds, set(qids))
    status = {}
    for r in best.values():
        status[r.get("status")] = status.get(r.get("status"), 0) + 1
    for n in notes:
        print("attribution", n)
    print(f"statuses: {status}; predictions: {len(preds)}/{len(qids)}; missing questions: {len(missing)}; "
          f"abstained: {sum(p['abstain'] for p in preds)}; no citations: "
          f"{sum(1 for p in preds if not p['abstain'] and not p['citations'])}; format errors: {len(errors)}")
    for e in errors[:10]:
        print("  ", e)
    return 0 if not errors and not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
