"""KU-B round 4: the frozen v2 ssu route (lenses/ssu/a_r3_route.py kg3crga, params as in configs/best.json) with its
ku hand-off lens swapped from ku/a_r3 r3w to ku/b_r4_ku (a wrapper over the same r3w). Evaluation only: in a config
this is just `"ku_lens": "lenses/ku/b_r4_ku.py", "ku_variant": "nolate_c"` in routes.ssu.params."""
from __future__ import annotations

from lenses.ku.b_r4_ku import _lens

ROUTE, ROUTE_VARIANT = "lenses/ssu/a_r3_route.py", "kg3crga"
V2 = {"ssu_lens": "lenses/ssu/merged_r3.py", "ssu_variant": "ku11fn4s_p5", "role_module": "lenses/ssa/a_r3_role.py",
      "ku_lens": "lenses/ku/a_r3.py", "ku_variant": "r3w"}

VARIANTS = {
    "v2": {},
    "nolate_c": {"ku_lens": "lenses/ku/b_r4_ku.py", "ku_variant": "nolate_c"},
    "nolate_c_cnt2": {"ku_lens": "lenses/ku/b_r4_ku.py", "ku_variant": "nolate_c_cnt2"},
}


def build(q, hx, **p):
    mod = _lens(ROUTE)
    params = dict(mod.VARIANTS[ROUTE_VARIANT], **V2)
    params.update({k: v for k, v in p.items() if k in V2})
    return mod.build(q, hx, _variant=p.get("_variant", ""), **params)
