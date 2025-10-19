from __future__ import annotations
from typing import Dict, Any, List, Optional
import random
from sympy import symbols, sympify, simplify

def _prove_lyapunov_impl(state_symbols: List[str],
                        F_next: List[str],
                        V_str: str,
                        unsafe_condition: Optional[str] = None,
                        assumptions: Optional[Dict[str, Any]] = None,
                        target: str = "<= 0",
                        numeric_trials: int = 400,
                        ranges: Optional[Dict[str, List[float]]] = None) -> Dict[str, Any]:

    sym_map = {s: symbols(s, real=True) for s in state_symbols}
    F_exprs = [sympify(e, locals=sym_map) for e in F_next]
    V = sympify(V_str, locals=sym_map)
    dV = simplify(V.subs({sym_map[s]: F_exprs[i] for i,s in enumerate(state_symbols)}) - V)

    U = sympify(unsafe_condition, locals=sym_map) if unsafe_condition else None
    report = {"symbolic": str(dV), "target": target, "trials": [], "passed": True}

    for _ in range(int(numeric_trials)):
        subs = {}
        for s in state_symbols:
            lo, hi = (-2.0, 2.0)
            if ranges and s in ranges: lo, hi = ranges[s]
            subs[sym_map[s]] = random.uniform(lo, hi)
        if U is not None:
            try:
                if not bool(U.subs(subs)):
                    continue
            except Exception:
                continue
        try:
            val = float(dV.subs(subs))
            ok = (val <= 1e-9) if target == "<= 0" else (val < -1e-6)
            report["trials"].append({"dV": val, "ok": bool(ok)})
            report["passed"] = report["passed"] and ok
        except Exception as e:
            report["trials"].append({"error": str(e)})
            report["passed"] = False
    return report

def prove_lyapunov(claim: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper function that matches the expected interface in registry.py"""
    return _prove_lyapunov_impl(
        state_symbols=claim["state_symbols"],
        F_next=claim["F_next"],
        V_str=claim["V"],
        unsafe_condition=claim.get("unsafe_condition"),
        assumptions=claim.get("assumptions"),
        target=claim.get("target", "<= 0"),
        numeric_trials=claim.get("numeric_trials", 400),
        ranges=claim.get("ranges")
    )
