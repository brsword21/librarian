"""Offline metrics of an EvidencePack against dev gold (see CONTRACT.md)."""
from __future__ import annotations

import re

import core.paths  # noqa: F401  (puts the upstream kit on sys.path)
from score import answer_matched, evidence_f1, normalize  # upstream kit

from core.gold_turns import gold_turns
from core.types import SHORT, EvidencePack

_NUM = re.compile(r"-?\d+(?:\.\d+)?")
_WORDNUM = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen "
                                       "fourteen fifteen sixteen seventeen eighteen nineteen twenty".split())}


def first_number(text: str) -> float | None:
    t = normalize(text or "")  # number words -> digits
    m = _NUM.search(t.replace(",", ""))
    return float(m.group(0)) if m else None


def extractive(g: dict, gold_text: str) -> bool:
    """Gold answer (or an alias) occurs verbatim (normalised) in the gold turns' text."""
    hay = f" {normalize(gold_text)} "
    from score import aliases
    cands = aliases(g["answer"]) + g.get("aliases", [])
    return any(f" {c} " in hay for c in map(normalize, cands) if c)


def question_metrics(pack: EvidencePack, g: dict, hx, ms: float, chars: int) -> dict:
    t = SHORT[g["question_type"]]
    out = {"type": t, "abstain_gold": g["abstain"], "abstain_p": float(pack.abstain_p), "chars": chars,
           "ms": round(ms, 1)}
    if g["abstain"]:
        return out
    G = set(g["evidence"])
    P = set(pack.session_ids())
    A = set(gold_turns().get(g["question_id"], []))
    sr = len(P & G) / len(G) if G else 0.0
    allg = float(G <= P)
    atr = (len(A & pack.included_turns) / len(A)) if A else sr
    gold_text = " ".join(hx.units[i].text for tid in A for i in hx.turn_units(tid))
    pack_text = "\n".join(p.text for p in pack.passages)
    ac = None
    if extractive(g, gold_text):
        ac = float(answer_matched(pack_text, g))
    ha = None
    if pack.computed is not None:
        gn, pn = first_number(g["answer"]), first_number(str(pack.computed))
        text_hit = answer_matched(str(pack.computed), g) or (
            len(normalize(str(pack.computed))) > 2 and normalize(str(pack.computed)) in normalize(g["answer"]))
        if gn is not None and pn is not None:
            ha = float(text_hit or pn == gn or (t == "temporal" and pn == gn + 1))
        else:
            ha = float(text_hit)
    cf1 = evidence_f1(pack.planned_citations(), list(G))
    newest = max(G, key=lambda s: hx.sess_by_id[s]["sess_idx"] if s in hx.sess_by_id else -1) if G else None
    if t in ("ssu", "ssa"):
        pa = (atr == 1.0) and (ac is None or ac == 1.0)
    elif t == "ku":
        pa = (newest in P) and ((ac == 1.0) if ac is not None else atr == 1.0)
    elif t == "multi":
        pa = allg == 1.0 and atr == 1.0
    else:  # temporal
        pa = allg == 1.0 and ((ha == 1.0) if ha is not None else atr == 1.0)
    pa = float(pa)
    # pessimistic citation bound: Reactor cites every passage we send (post-filtering by cite_plan is not confirmed)
    cf1_all = evidence_f1(pack.session_ids(), list(G))
    out.update(SR=sr, ALL=allg, ATR=atr, AC=ac, HA=ha, CF1=cf1, PA=pa,
               S=100 * (0.65 * pa + 0.30 * cf1 - 0.05 * chars / 16000),
               CF1all=cf1_all, Sall=100 * (0.65 * pa + 0.30 * cf1_all - 0.05 * chars / 16000))
    ranking = pack.debug.get("ranking") if isinstance(pack.debug, dict) else None
    if ranking:
        gold_uids = {i for tid in A for i in hx.turn_units(tid)}
        ranks = [r for r, u in enumerate(ranking) if u in gold_uids]
        out["gold_rank"] = ranks[0] if ranks else None
    return out


def auc(pos: list[float], neg: list[float]) -> float | None:
    """P(score of an unanswerable question > score of an answerable one)."""
    if not pos or not neg:
        return None
    wins = sum((p > n) + 0.5 * (p == n) for p in pos for n in neg)
    return wins / (len(pos) * len(neg))


def summarize(rows: list[dict]) -> dict:
    ans = [r for r in rows if not r.get("abstain_gold") and "S" in r]
    def mean(key):
        vals = [r[key] for r in ans if r.get(key) is not None]
        return round(sum(vals) / len(vals), 4) if vals else None
    chars = sorted(r["chars"] for r in rows if "chars" in r)
    return {
        "n": len(rows), "n_answerable": len(ans), "errors": sum(1 for r in rows if r.get("error")),
        "S": mean("S"), "PA": mean("PA"), "ATR": mean("ATR"), "SR": mean("SR"), "ALL": mean("ALL"), "AC": mean("AC"),
        "HA": mean("HA"), "CF1": mean("CF1"), "CF1all": mean("CF1all"), "Sall": mean("Sall"),
        "chars_mean": round(sum(chars) / len(chars)) if chars else None,
        "chars_p90": chars[int(0.9 * (len(chars) - 1))] if chars else None,
        "ms_mean": round(sum(r.get("ms", 0) for r in rows) / max(1, len(rows)), 1),
        "abstain_auc": auc([r["abstain_p"] for r in rows if r.get("abstain_gold")],
                           [r["abstain_p"] for r in rows if not r.get("abstain_gold") and "abstain_p" in r]),
    }
