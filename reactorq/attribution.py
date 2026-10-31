"""Learned evidence attribution: which pack sessions to cite for Reactor's (unchanged) answer.

    from reactorq.attribution import attribute
    citations, note = attribute(pred, pack, reactor_result)

pred           = one predictions.jsonl row (question_id, abstain, answer without [E#] labels, citations = session ids)
pack           = the evidence pack sent to Reactor (reactorq.build_packs row: passages [{id, date, text}], cite_plan,
                 computed, route, question)
reactor_result = the raw results.jsonl row (only used for the raw answer text when pred lacks it)

Rule (organisers on Discord: "your code can select supporting sessions from the retrieved evidence: just make sure they
actually support Reactor's answer rather than blindly falling back to the top-ranked result"):
1. Reactor's own citations are always kept (on the dev calibration every Reactor citation was a gold session).
2. A pack session may be ADDED only if it supports Reactor's answer (SUPPORT RULE):
   - its text contains the answer (score.normalize whole phrase, the answer without a parenthetical, or every content
     word of a multi-word answer), or the answer's number as a token, or
     (when Reactor cited something and the answer is a bare number on the multi / temporal route, containment does not
     count: "3" in a session does not support "3 doctors"; only the computation's sessions do), or
   - our code computed the answer (pack.computed equals the answer, as a number or normalized string) and the session
     is one the computation used (pack.cite_plan).
3. Among supporting sessions not already cited, a logistic model (coefficients below, fitted on dev with gold evidence
   labels; see runs/citations/model_report.md) scores p(session is gold evidence); sessions with p >= THRESHOLD are
   added, at most MAX_ADD, best first. With no Reactor citation at all (fill-missing), supporting sessions with
   p >= FILL_THRESHOLD are cited (at most FILL_MAX), and at least the best supporting one.
4. Optional ku-chain (as in reactorq/finalize.py): on the knowledge-update route, when the citations hold exactly one
   session of a 2-session cite_plan, the other one (the superseded statement of the same attribute) is added.
   It does not satisfy the support rule (the old session holds the OLD value) and is therefore a separate switch.
Answers are never touched. Abstentions get no citations.
"""
from __future__ import annotations

import math
import re

import core.paths  # noqa: F401  (puts the upstream kit on sys.path)
from score import normalize  # upstream kit

_LABELS = re.compile(r"\s*\[\s*E\d+(?:\s*[,;]\s*E\d+)*\s*\]")
_NUM = re.compile(r"-?\d+(?:\.\d+)?")
_PAREN = re.compile(r"\s*\([^)]*\)")
_STOP = set("""a an the of to in on at for and or by with from my your i you me we our it its is was were be been
being this that these those as about into over than then so do did does have has had not no yes per each one some any
all just only more most less few many much very there here what which who when where how why""".split())

# ---- fitted model (runs/citations/train_attr.py fit --write; dev, 5-fold grouped CV, C=0.1). THRESHOLD / MAX_ADD hand-set
# from the CV optimum 0.3 / 3 to the tied conservative 0.5 / 2 (dev CV 0.6181 vs 0.6178; Reactor cites precisely).
FEATURES = ["bias", "contains", "num_match", "tok_overlap", "in_plan", "plan_comp", "plan_first", "ce_q", "ce_qa",
            "ce_q_rel", "ce_qa_rel", "spec", "n_pass_inv",
            "r_ssu", "r_ssa", "r_multi", "r_ku", "r_temporal",
            "contains_x_multi", "contains_x_temporal", "in_plan_x_multi", "in_plan_x_temporal", "in_plan_x_ku",
            "bare_num", "contains_x_bare"]
COEF = [0.6984, 0.3181, -0.2034, 0.7774, 1.1739, 0.4908, 0.6534, 0.9288, 1.4078, 0.3040, 0.9403, 0.0631, 0.7699, 0.3087, 0.0630, 0.4351, 0.0509, -0.1592, -0.1108, 0.4036, 0.4684, 0.3542, 0.1587, 0.2604, -0.1293]
THRESHOLD = 0.5                    # Reactor cited something: add supporting sessions with p >= THRESHOLD
MAX_ADD = 2                        # ... at most MAX_ADD of them
FILL_THRESHOLD = 0.4               # Reactor cited nothing: cite supporting sessions with p >= FILL_THRESHOLD
FILL_MAX = 5                       # ... at most FILL_MAX, and always the best supporting one
USE_CE = True                      # cross-encoder features (served by core.model_server); 0 when unavailable


def strip_labels(answer: str) -> str:
    return _LABELS.sub("", answer or "").strip()


def _num(s: str) -> str | None:
    m = _NUM.search(normalize(s or "").replace(",", ""))
    return m.group(0) if m else None


def _content(tokens: list[str]) -> list[str]:
    return [t for t in tokens if t not in _STOP and (len(t) > 1 or t.isdigit())]


def answer_forms(answer: str) -> list[str]:
    """Normalized whole-phrase forms of the answer: full, without parentheticals, the part before ' by '/','."""
    ans = strip_labels(answer)
    forms = [normalize(ans), normalize(_PAREN.sub("", ans))]
    head = re.split(r",| by | - |:", _PAREN.sub("", ans))[0]
    if len(normalize(head).split()) >= 2:
        forms.append(normalize(head))
    return [f for f in dict.fromkeys(forms) if f and len(f) > 1]


def computed_matches(answer: str, computed) -> bool:
    if computed is None:
        return False
    a, c = _num(answer), _num(str(computed))
    if a is not None and c is not None:
        return float(a) == float(c)
    na, nc = normalize(strip_labels(answer)), normalize(str(computed))
    return bool(nc) and (f" {nc} " in f" {na} " or f" {na} " in f" {nc} ")


def _segments(text: str, cap: int = 24) -> list[str]:
    segs = [s.strip() for s in re.split(r"\n\[\.\.\.\]\n|\n(?=user:|assistant:)", text or "") if len(s.strip()) > 15]
    return [s[:1200] for s in segs[:cap]] or [(text or "")[:1200]]


def _ce_max(query: str, segs: list[str]) -> float:
    from core.index import HistoryIndex
    return max(HistoryIndex.rerank_texts(query, segs)) if segs else -12.0


def session_features(question: str, answer: str, pack: dict, cited: set[str], use_ce: bool = True) -> list[dict]:
    """One dict per pack passage: id, support (bool), raw feature values, feature vector x (FEATURES order)."""
    passages = [p for p in pack.get("passages") or [] if p.get("id")]
    plan = [s for s in (pack.get("cite_plan") or []) if s]
    route = pack.get("route") or "?"
    forms = answer_forms(answer)
    anum = _num(strip_labels(answer))
    a_tok = _content(normalize(strip_labels(answer)).split())
    comp = computed_matches(answer, pack.get("computed"))
    bare = bool(re.fullmatch(r"-?\d+(?:\.\d+)?", normalize(strip_labels(answer))))
    rows = []
    for p in passages:
        nt = normalize(p.get("text") or "")
        padded, toks = f" {nt} ", set(nt.split())
        contains = any(f" {f} " in padded for f in forms)
        num_match = anum is not None and anum in toks
        overlap = (sum(t in toks for t in a_tok) / len(a_tok)) if a_tok else 0.0
        if len(a_tok) >= 2 and overlap >= 0.999:
            contains = True
        in_plan = p["id"] in plan
        rows.append({"id": p["id"], "contains": float(contains), "num_match": float(num_match),
                     "tok_overlap": overlap, "in_plan": float(in_plan), "plan_comp": float(in_plan and comp),
                     "plan_first": float(bool(plan) and p["id"] == plan[0]), "cited": float(p["id"] in cited)})
    if use_ce and rows:
        try:
            stmt = f"{question} {strip_labels(answer)}"
            for r, p in zip(rows, passages):
                segs = _segments(p.get("text") or "")
                r["ce_q"], r["ce_qa"] = _ce_max(question, segs), _ce_max(stmt, segs)
        except Exception:                                   # model server down: neutral CE features
            use_ce = False
    if not use_ce:
        for r in rows:
            r["ce_q"] = r["ce_qa"] = 0.0
    mq = max((r["ce_q"] for r in rows), default=0.0)
    mqa = max((r["ce_qa"] for r in rows), default=0.0)
    n_sup = sum(1 for r in rows if r["contains"] or r["num_match"]) or 1
    for r in rows:
        # a bare number answer of a count / day-gap question is not supported by a session that merely contains
        # that number ("3 doctors" vs "I have 3 kids"): there only the sessions our computation used support it
        loose = bare and route in ("multi", "temporal")
        # (gate used only when Reactor cited something; with no citation at all a containing session is the best we have)
        r["support_fill"] = bool(r["plan_comp"] or r["contains"] or r["num_match"])
        r["support"] = bool(r["plan_comp"] or (not loose and (r["contains"] or r["num_match"])))
        r["bare_num"] = float(bare)
        r["ce_q_rel"], r["ce_qa_rel"] = r["ce_q"] - mq, r["ce_qa"] - mqa
        r["spec"] = (r["contains"] or r["num_match"]) / n_sup
        r["n_pass_inv"] = 1.0 / len(rows)
        for rt in ("ssu", "ssa", "multi", "ku", "temporal"):
            r[f"r_{rt}"] = float(route == rt)
        r["contains_x_multi"] = r["contains"] * r["r_multi"]
        r["contains_x_temporal"] = r["contains"] * r["r_temporal"]
        r["in_plan_x_multi"] = r["in_plan"] * r["r_multi"]
        r["in_plan_x_temporal"] = r["in_plan"] * r["r_temporal"]
        r["in_plan_x_ku"] = r["in_plan"] * r["r_ku"]
        r["contains_x_bare"] = r["contains"] * r["bare_num"]
        r["bias"] = 1.0
        r["x"] = [float(r[f]) / (10.0 if f.startswith("ce_") else 1.0) for f in FEATURES]
    return rows


def prob(x: list[float], coef: list[float] | None = None) -> float:
    z = sum(a * b for a, b in zip(coef or COEF, x))
    return 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, z))))


def decide(rows: list[dict], cited: list[str], probs: list[float], threshold: float = None, max_add: int = None,
           fill_threshold: float = None, fill_max: int = None) -> list[str]:
    """Reactor's citations + supporting sessions with p >= threshold (best first, at most max_add); with no Reactor
    citation, supporting sessions with p >= fill_threshold (at most fill_max, at least the best one)."""
    out = list(dict.fromkeys(cited))
    key = "support" if out else "support_fill"
    cand = sorted(((p, r["id"]) for r, p in zip(rows, probs) if r.get(key, r["support"]) and r["id"] not in out),
                  reverse=True)
    if out:
        t, k = (THRESHOLD if threshold is None else threshold), (MAX_ADD if max_add is None else max_add)
        return out + [sid for p, sid in cand if p >= t][:k]
    t, k = (FILL_THRESHOLD if fill_threshold is None else fill_threshold), (FILL_MAX if fill_max is None else fill_max)
    adds = [sid for p, sid in cand if p >= t][:k]
    return adds or [sid for _, sid in cand[:1]]


def ku_chain(pack: dict, cites: list[str]) -> list[str]:
    plan = [s for s in (pack.get("cite_plan") or []) if s]
    if pack.get("route") == "ku" and len(plan) == 2 and len(set(cites) & set(plan)) == 1:
        return cites + [(set(plan) - set(cites)).pop()]
    return cites


def attribute(pred: dict, pack: dict | None, reactor_result: dict | None = None, use_ku_chain: bool = True,
              use_ce: bool | None = None) -> tuple[list[str], str | None]:
    """(citations, note). Never changes the answer; abstentions and missing packs keep pred's citations."""
    cites = list(dict.fromkeys(pred.get("citations") or []))
    if pred.get("abstain") or not pack:
        return cites, None
    answer = pred.get("answer") or strip_labels((reactor_result or {}).get("answer") or "")
    if not answer.strip():
        return cites, None
    question = pack.get("question") or pred.get("question") or ""
    rows = session_features(question, answer, pack, set(cites), USE_CE if use_ce is None else use_ce)
    probs = [prob(r["x"]) for r in rows]
    out = decide(rows, cites, probs)
    notes = []
    added = [s for s in out if s not in cites]
    if added:
        pm = {r["id"]: p for r, p in zip(rows, probs)}
        why = {r["id"]: ("computed" if r["plan_comp"] and not (r["contains"] or r["num_match"]) else "contains answer")
               for r in rows}
        notes.append("attribution added " + ", ".join(f"{s} (p={pm[s]:.2f}, {why[s]})" for s in added))
    if use_ku_chain:
        before = list(out)
        out = ku_chain(pack, out)
        if out != before:
            notes.append("ku-chain: added the superseded statement's session")
    return out, ("; ".join(notes) or None)
