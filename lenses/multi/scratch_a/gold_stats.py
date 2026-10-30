"""Where do gold turns sit for multi-session questions (dev / dev200)?"""
import json, sys, collections, statistics as st
from core.data import questions, gold, history
from core.gold_turns import gold_turns
split = sys.argv[1] if len(sys.argv) > 1 else "dev"
g, gt = gold(split), gold_turns()
roles = collections.Counter(); tpos = collections.Counter(); per_sess = collections.Counter()
lens = []; first_user = 0; nturn = 0; gold_sess_wo_turn = 0; nsess = 0
for q in questions(split):
    gg = g.get(q.question_id)
    if not gg or gg["question_type"] != "multi-session" or gg["abstain"]:
        continue
    h = history(split, q.history_id)
    tids = set(gt.get(q.question_id, []))
    cnt = collections.Counter()
    for s in h["sessions"]:
        for i, t in enumerate(s["turns"]):
            if t["turn_id"] in tids:
                roles[t["role"]] += 1; tpos[min(i, 10)] += 1; lens.append(len(t["content"]))
                cnt[s["session_id"]] += 1; nturn += 1
                if i == 0: first_user += 1
    for e in gg["evidence"]:
        nsess += 1
        per_sess[cnt.get(e, 0)] += 1
print("gold turns", nturn, "roles", dict(roles))
print("turn position (capped 10)", sorted(tpos.items()))
print("gold turns per gold session", sorted(per_sess.items()), "of", nsess)
print("turn len median", st.median(lens), "p90", sorted(lens)[int(.9*len(lens))])
