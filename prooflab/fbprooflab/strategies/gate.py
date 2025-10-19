from __future__ import annotations
from typing import Dict, Any, Optional, List
from sympy import symbols, sympify
import random

def verify_gate(symbols_list: List[str],
                continue_condition: str,
                halt_condition: str,
                numeric_trials: int = 300,
                ranges: Optional[Dict[str, List[float]]] = None) -> Dict[str, Any]:
    sym_map = {s: symbols(s, real=True) for s in symbols_list}
    C = sympify(continue_condition, locals=sym_map)
    H = sympify(halt_condition, locals=sym_map)

    report = {"conflicts": 0, "misses": 0, "trials": []}

    for _ in range(int(numeric_trials)):
        subs = {}
        for s in symbols_list:
            lo, hi = (-3.0, 3.0)
            if ranges and s in ranges: lo, hi = ranges[s]
            subs[sym_map[s]] = random.uniform(lo, hi)
        try:
            cv = bool(C.subs(subs))
            hv = bool(H.subs(subs))
            ok = not (cv and hv)
            if not ok: report["conflicts"] += 1
            if (not cv) and (not hv): report["misses"] += 1
            report["trials"].append({"continue": cv, "halt": hv, "ok": ok})
        except Exception as e:
            report["trials"].append({"error": str(e)})
    report["passed"] = (report["conflicts"] == 0) and (report["misses"] == 0)
    return report
