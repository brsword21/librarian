"""Build packs for TEST questions (no gold) and print them with simple flags, for qualitative review.

    python -m harness.audit --lens lenses/temporal/a_calendar.py --variant base --type temporal [--n 10] [--full]
Writes runs/audit/<type>/<lens>/<variant>/test_packs.jsonl.
    --compare OLD.jsonl  after the audit, list the test packs whose route, cite_plan, passages or hint changed against an
                         older test_packs.jsonl (or compare two files without building: python -m harness.audit
                         --diff OLD.jsonl NEW.jsonl).
"""
from __future__ import annotations

import argparse
import json

from core.data import questions
from core.index import HistoryIndex
from core.pack import message_chars
from core.paths import RUNS
from core.router import route
from harness.sweep import load_lens


def flags(pack, typ: str) -> list[str]:
    f = []
    if not pack.passages:
        f.append("EMPTY")
    if typ == "temporal" and pack.computed is None:
        f.append("no-computed-days")
    if typ == "temporal" and pack.computed is not None:
        try:
            v = float(str(pack.computed).split()[0])
            if v <= 0 or v > 365:
                f.append(f"days-out-of-range:{v}")
        except ValueError:
            pass
    if typ == "ssa" and pack.passages and "assistant:" not in pack.passages[0].text:
        f.append("first-passage-has-no-assistant-turn")
    if typ == "ku" and len(pack.session_ids()) < 2:
        f.append("fewer-than-2-sessions")
    if pack.abstain_p >= 0.5:
        f.append(f"abstain_p={pack.abstain_p:.2f}")
    return f


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lens", required=True)
    ap.add_argument("--variant", required=True)
    ap.add_argument("--type")
    ap.add_argument("--n", type=int, default=999)
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--compare", help="older test_packs.jsonl to diff the new packs against")
    ap.add_argument("--qids", help="comma-separated question ids or a file with one id per line: build only these")
    a = ap.parse_args(argv)
    lens = load_lens(a.lens)
    params = dict(lens.VARIANTS[a.variant])
    qs = [q for q in questions("test") if not a.type or route(q.question)[0] == a.type][: a.n]
    if a.qids:
        from pathlib import Path
        want = set(Path(a.qids).read_text().split() if Path(a.qids).exists() else a.qids.split(","))
        qs = [q for q in qs if q.question_id in want]
    out = RUNS / "audit" / (a.type or "all") / a.lens.split("/")[-1].removesuffix(".py") / a.variant
    out.mkdir(parents=True, exist_ok=True)
    n_flag = 0
    with open(out / "test_packs.jsonl", "w", encoding="utf-8") as f:
        for q in qs:
            hx = HistoryIndex.load("test", q.history_id)
            pack = lens.build(q, hx, _variant=a.variant, **params)
            fl = flags(pack, a.type or route(q.question)[0])
            n_flag += bool(fl)
            chars = message_chars(q, pack.passages, pack.hint)
            f.write(json.dumps({"question_id": q.question_id, "question": q.question, "flags": fl, "chars": chars,
                                "hint": pack.hint, "computed": pack.computed, "abstain_p": pack.abstain_p,
                                "route": pack.route, "cite_plan": pack.planned_citations(),
                                "debug": {k: v for k, v in (pack.debug or {}).items() if k != "ranking"}
                                if isinstance(pack.debug, dict) else None,
                                "passages": [{"id": p.id, "date": p.date, "text": p.text} for p in pack.passages]},
                               ensure_ascii=False, default=str) + "\n")
            print("=" * 100)
            print(f"{q.question}  (asked {q.date_str})  chars={chars} flags={fl}")
            if pack.hint:
                print(f"HINT: {pack.hint[:400]}")
            if pack.computed is not None:
                print(f"COMPUTED: {pack.computed}")
            if isinstance(pack.debug, dict):
                dbg = {k: v for k, v in pack.debug.items() if k != "ranking"}
                if dbg:
                    print(f"DEBUG: {str(dbg)[:600]}")
            for p in pack.passages[: (99 if a.full else 4)]:
                print(f"  [{p.id} {p.date}] {p.text[: (3000 if a.full else 350)]!r}")
    print(f"\n{len(qs)} test questions, {n_flag} flagged -> {out}")
    if a.compare:
        compare(a.compare, out / "test_packs.jsonl", route_filter=a.type, partial_ok=bool(a.qids))


_SUFFIX_RX = None


def _hint_of(r: dict) -> str:
    """Hint text in either format: audit rows carry `hint`; reactor packs (reactorq.build_packs) carry question_text =
    question + hint + constant answer-format suffix."""
    global _SUFFIX_RX
    if "hint" in r:
        return (r.get("hint") or "").strip()
    if _SUFFIX_RX is None:
        import re
        _SUFFIX_RX = re.compile(r"\n?Write the final answer line as:.*$", re.S)
    qt = r.get("question_text") or ""
    q = r.get("question") or ""
    if qt.startswith(q):
        qt = qt[len(q):]
    return _SUFFIX_RX.sub("", qt).strip()


def compare(old_path, new_path, route_filter: str | None = None, partial_ok: bool = False) -> int:
    """Print every question whose route, cite_plan, passage set, passage text or hint differs between two
    test_packs.jsonl files (audit rows or reactor packs, any mix). computed / abstain_p changes are printed as info
    (they do not change what Reactor sees). Returns the number of changed packs (route, cite, passages or hint)."""
    def load(p):
        return {r["question_id"]: r for r in map(json.loads, open(p, encoding="utf-8"))}
    old, new = load(old_path), load(new_path)
    n = n_visible = 0
    for qid, b in new.items():
        o = old.get(qid)
        if o is None:
            print(f"NEW   {qid} {b['question'][:100]}")
            n += 1
            continue
        ps_o, ps_b = [p["id"] for p in o["passages"]], [p["id"] for p in b["passages"]]
        ch, info = [], []
        if o.get("route") != b.get("route"):
            ch.append(f"route {o.get('route')} -> {b.get('route')}")
        co, cb = sorted(o.get("cite_plan") or []), sorted(b.get("cite_plan") or [])
        if co != cb:
            ch.append(f"cite {co} -> {cb}")
        visible = False
        if sorted(ps_o) != sorted(ps_b):
            dates_b = {p["id"]: (p.get("date") or "")[:10] for p in b["passages"]}
            dates_o = {p["id"]: (p.get("date") or "")[:10] for p in o["passages"]}
            added = [f"+{x}@{dates_b.get(x, '')}" for x in ps_b if x not in ps_o]
            dropped = [f"-{x}@{dates_o.get(x, '')}" for x in ps_o if x not in ps_b]
            ch.append(f"passages {len(ps_o)}->{len(ps_b)} (kept {len(set(ps_o) & set(ps_b))}; "
                      f"{' '.join(added + dropped)})")
            visible = True
        elif [p["text"] for p in o["passages"]] != [p["text"] for p in b["passages"]] or ps_o != ps_b:
            ch.append(f"passage text/order ({sum(len(p['text']) for p in o['passages'])}->"
                      f"{sum(len(p['text']) for p in b['passages'])} chars)")
            visible = True
        if _hint_of(o) != _hint_of(b):
            ch.append("hint")
            visible = True
        if o.get("computed") != b.get("computed"):
            info.append(f"computed {o.get('computed')} -> {b.get('computed')}")
        ao, ab = o.get("abstain_p"), b.get("abstain_p")
        if ao is not None and ab is not None and abs(ao - ab) >= 0.05:
            info.append(f"abstain_p {ao:.2f} -> {ab:.2f}")
        if ch:
            n += 1
            n_visible += visible
            print(f"{b.get('route') or '?':8s} {qid} {'; '.join(ch)}{' | ' + '; '.join(info) if info else ''} "
                  f"| {b['question'][:90]}")
        elif info:
            print(f"(info)   {qid} {'; '.join(info)} | {b['question'][:90]}")
    missing = [q for q in old if q not in new
               and not (route_filter and old[q].get("route") not in (None, route_filter))]
    if missing and not partial_ok:
        print(f"PARTIAL DIFF: {len(missing)} questions of {old_path} are not in the new file (use --n 999)")
    print(f"{n} of {len(new)} packs changed against {old_path} ({n_visible} change what Reactor sees: "
          f"passages, passage text or hint)")
    return n


if __name__ == "__main__":
    import sys
    if len(sys.argv) in (4, 5) and sys.argv[1] == "--diff":
        compare(sys.argv[2], sys.argv[3], route_filter=sys.argv[4] if len(sys.argv) == 5 else None)
    else:
        main()
