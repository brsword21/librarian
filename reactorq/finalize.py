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
- ku-chain: on the knowledge-update route, when Reactor cites exactly ONE session and it belongs to the old/new pair our
  timeline planned, the other session of that pair (the earlier statement the update supersedes) is added. When Reactor
  already cites two or more sessions it has given its own old/new pair, and nothing is added.
- computed-chain: when Reactor's number equals the value our code computed (+/-1 only for day/week/month/year gaps), the sessions holding the dates /
  values the computation used (cite_plan) are cited.
- containment: on ssu / ssa / ku / temporal, every packed session that contains Reactor's whole answer phrase is cited,
  only for answers of >= 2 content words or a >= 4-digit number (one-word answers hit decoys: 'Masa' in 'masa madre').
- reply-rows (opt-in, --reply-rows): on the multi route, the sessions Reactor listed as counted instances in its own
  working ('date | [E#] | item | n' rows, not the excluded ones) are cited. Off: on test it added sessions that do not
  contain the answer.
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

from predictions import _LABELS  # noqa: E402  upstream kit (reactor/predictions.py)


def _num(s: str) -> str | None:
    m = re.search(r"-?\d+(?:\.\d+)?", normalize(s or "").replace(",", ""))
    return m.group(0) if m else None


_STOP = set("the a an of in on at to for and or my i me with from by is was it this that day days week weeks month "
            "months year years time times".split())
_DAYQ = re.compile(r"\bhow many (days|weeks|months|years)\b|\bhow long\b|\bhow old\b", re.I)
_DAYU = re.compile(r"\b(days?|weeks?|months?|years?)\b", re.I)
_ROW_E = re.compile(r"\[?E(\d+)\]?")
_ROW_BAD = re.compile(r"(?i)exclud|\bnot\b|ignor|decoy|reject|✗|drop|outside|skip|plan(?:ned|s)?\b|other person|"
                      r"friend|no user|never|n't|irrelevant|unrelated")
_ROW_STOP = re.compile(r"(?i)^(excluded|decoys?|notes? on what|choices|two things|the one|\(excluded)")


def _stoks(s: str) -> list[str]:
    """normalized tokens, plural-insensitive ('55 inches' ~ '55-inch')."""
    out = []
    for t in normalize(s or "").split():
        out.append(t[:-2] if len(t) > 4 and t.endswith("es") else t[:-1] if len(t) > 3 and t.endswith("s") else t)
    return out


def _contains(text: str, ans: str) -> bool:
    return bool(ans) and f" {ans} " in f" {normalize(text)} "


def _supports(text: str, answer: str, question: str) -> bool:
    """the passage states the answer: exact phrase, plural/hyphen-insensitive phrase, or for a bare number N
    'N <noun of the question>' ('7 shirts', 'four bikes')."""
    ans = normalize(_LABELS.sub("", answer))
    if len(ans) > 1 and _contains(text, ans):
        return True
    a, t = _stoks(_LABELS.sub("", answer)), _stoks(text)
    if not a:
        return False
    if len(a) > 1 and f" {' '.join(a)} " in f" {' '.join(t)} ":   # fuzzy only for multi-token answers ('Notes' !~ 'not')
        return True
    if len(a) == 1 and a[0].replace(".", "").isdigit():
        nouns = {x for x in _stoks(question) if len(x) >= 4 and x not in _STOP and not x.isdigit()}
        return any(x == a[0] and any(y in nouns for y in t[i + 1:i + 4]) for i, x in enumerate(t))
    return False


def _specific(answer: str) -> bool:
    """distinctive enough that 'the passage contains it' means 'the passage supports it'."""
    toks = normalize(_LABELS.sub("", answer)).split()
    content = [t for t in toks if not t.isdigit() and t not in _STOP and len(t) >= 3]
    return len(content) >= 2 or any(t.replace(".", "").isdigit() and len(t.replace(".", "")) >= 4 for t in toks)


def _computed_match(answer: str, pack: dict) -> bool:
    if pack.get("computed") is None:
        return False
    a, b = _num(answer), _num(str(pack["computed"]))
    if a is None or b is None:
        return False
    if a == b:
        return True
    try:
        q = pack.get("question", "")
        return bool(_DAYQ.search(q)) and bool(_DAYU.search(f"{answer} {q}")) and abs(float(a) - float(b)) == 1
    except ValueError:
        return False


def _reply_rows(reply: str) -> list[int]:
    """E numbers of the instance rows Reactor counted in its own working (before its 'Excluded' notes)."""
    out = []
    for line in (reply or "").split("# FINAL ANSWER")[0].splitlines():
        s = line.strip()
        if _ROW_STOP.match(s):
            break
        if ("|" in s or "→" in s) and not _ROW_BAD.search(s):
            es = set(_ROW_E.findall(s))
            if len(es) == 1:
                out.append(int(es.pop()))
    return out


def attribute(pred: dict, pack: dict | None, fill_missing: bool, ku_chain: bool, reply: str = "",
              computed_chain: bool = True, contain: bool = True, reply_rows: bool = False) -> tuple[dict, str | None]:
    if pred["abstain"] or pack is None:
        return pred, None
    cites = list(pred["citations"])
    notes = []
    ids = [p["id"] for p in pack["passages"] if p.get("id")]
    route = pack.get("route")

    def add(sids, why):
        new = [s for s in sids if s and s not in cites]
        if new:
            cites.extend(new)
            notes.append(f"{why}: +{len(new)}")

    if fill_missing and not cites:
        support = [p["id"] for p in pack["passages"] if p.get("id")
                   and _supports(p["text"], pred["answer"], pack.get("question", ""))]
        if not support and _computed_match(pred["answer"], pack):
            support = list(pack.get("cite_plan") or [])
        add(support, "fill-missing (answer had no [E#] labels)")
    if ku_chain and route == "ku" and len(cites) == 1:
        plan = [s for s in (pack.get("cite_plan") or []) if s]
        if len(plan) == 2 and cites[0] in plan:
            add([s for s in plan if s != cites[0]], "ku-chain (superseded statement)")
    if computed_chain and cites and _computed_match(pred["answer"], pack):
        add(pack.get("cite_plan") or [], "computed-chain (sessions the computed value came from)")
    if reply_rows and cites and route == "multi":
        add([ids[k - 1] for k in _reply_rows(reply) if 1 <= k <= len(ids)], "reply-rows (instances Reactor counted)")
    if contain and cites and route in ("ssu", "ssa", "ku", "temporal") and _specific(pred["answer"]):
        ans = normalize(_LABELS.sub("", pred["answer"]))
        add([p["id"] for p in pack["passages"] if p.get("id") and _contains(p["text"], ans)], "containment")
    return {**pred, "citations": cites}, ("; ".join(notes) or None)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", nargs="+", required=True, help="results files, later ones win")
    ap.add_argument("--packs", nargs="*", default=[], help="pack files (first file wins per question)")
    ap.add_argument("--split", default="test")
    ap.add_argument("--out", required=True)
    ap.add_argument("--no-fill-missing", action="store_true")
    ap.add_argument("--no-ku-chain", action="store_true")
    ap.add_argument("--no-computed-chain", action="store_true")
    ap.add_argument("--no-contain", action="store_true")
    ap.add_argument("--reply-rows", action="store_true", help="off by default: Reactor's own working is not evidence")
    a = ap.parse_args(argv)
    best: dict[str, dict] = {}
    for f in a.results:
        if "proxy" in Path(f).parts:
            raise SystemExit(f"refusing {f}: simulator (proxy) results never go into the submission")
        for r in read_jsonl(Path(f)):
            if r.get("proxy"):
                raise SystemExit(f"refusing {f}: it contains simulator (proxy) answers; only Reactor answers are allowed")
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
            hash_ok = r.get("pack_hash") in packs_by_hash          # [E#] of the reply index THIS pack's passages
            p2, note = attribute(p, pack, not a.no_fill_missing, not a.no_ku_chain,
                                 reply=(r.get("reply") or "") if hash_ok else "",
                                 computed_chain=not a.no_computed_chain, contain=not a.no_contain,
                                 reply_rows=a.reply_rows)
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
