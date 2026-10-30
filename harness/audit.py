"""Build packs for TEST questions (no gold) and print them with simple flags, for qualitative review.

    python -m harness.audit --lens lenses/temporal/a_calendar.py --variant base --type temporal [--n 10] [--full]
Writes runs/audit/<type>/<lens>/<variant>/test_packs.jsonl.
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
    a = ap.parse_args(argv)
    lens = load_lens(a.lens)
    params = dict(lens.VARIANTS[a.variant])
    qs = [q for q in questions("test") if not a.type or route(q.question)[0] == a.type][: a.n]
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


if __name__ == "__main__":
    main()
