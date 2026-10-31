"""KU-B r3: the full routed system (lenses/pipeline.py) with an experimental config, for e5-style routed numbers.
  v1     = configs/best.json (frozen v1)
  qt3c   = v1 with the ssu route replaced by lenses/ku/b_r3_gate.py qt3c (same role hand-off + value-type ku gate)
"""
from lenses import pipeline as _P

VARIANTS = {"v1": {"config": "configs/best.json"},
            "qt3c": {"config": "lenses/ku/scratch_b/r3_cfg_qt3c.json"},
            "qt3c_ap": {"config": "lenses/ku/scratch_b/r3_cfg_qt3c_ap.json"}}


def build(q, hx, **p):
    return _P.build(q, hx, **p)
