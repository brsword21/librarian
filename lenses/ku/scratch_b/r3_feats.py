"""Dump ku_feats of ssu-routed questions (from b_r3_gate v1 runs) per gold type."""
import json, sys
for split in sys.argv[1:] or ["dev", "dev200"]:
    for l in open(f"runs/r3-ku-b/ssu-routed/b_r3_gate/v1/{split}/per_question.jsonl"):
        r = json.loads(l)
        f = (r.get("debug") or {}).get("ku_feats")
        if not f or "pair_sc" not in f:
            continue
        if r["type"] != "ku" and not f.get("r2hit"):
            continue
        print(f"{split[:5]} {r['type']:8s} S={r.get('S') or 0:5.1f} r2={int(f['r2hit'])} d={int(f['distinct'])} sc={f['pair_sc']} cov={f['cov_min']} own={f['own']} "
              f"asst={f['asst']} head={f['head']}:{int(f['head_both'])}/{int(f['head2_both'])} cq={int(f['cue_q'])} cn={int(f['cue_n'])} diff={f['diff_types']} | {r['question'][:70]}")
        print(f"      O: {f['types_o']} | {f['raw_o'][:110]}")
        print(f"      N: {f['types_n']} | {f['raw_n'][:110]}")
