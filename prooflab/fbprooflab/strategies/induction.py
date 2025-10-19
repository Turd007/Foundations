from __future__ import annotations
from typing import Dict, Any, Optional
from sympy import symbols, sympify, simplify
from sympy.assumptions import assuming, Q

def prove_induction(predicate_str: str, n_symbol: str="n",
                    base_from: int=1, base_to: int=1,
                    assumptions: Optional[Dict[str,Any]]=None) -> Dict[str, Any]:
    n = symbols(n_symbol, integer=True)
    assumption_context = [Q.integer(n), Q.ge(n, base_from)]
    if assumptions and n_symbol in assumptions:
        for a in assumptions[n_symbol]:
            if a == "positive":
                assumption_context.append(Q.positive(n))
            elif a == "nonzero":
                assumption_context.append(Q.nonzero(n))
            elif a == "real":
                assumption_context.append(Q.real(n))
    Pn = sympify(predicate_str, locals={n_symbol: n})
    report = {"base_checks": [], "inductive_step": None, "predicate": str(Pn), "n_symbol": n_symbol, "base_from": base_from, "base_to": base_to}
    with assuming(*assumption_context):
        ok_all = True
        for k_val in range(base_from, base_to + 1):
            try:
                val = Pn.subs({n: k_val})
                ok = bool(simplify(val))
                report["base_checks"].append({"n": k_val, "ok": ok, "expr": str(val)})
                ok_all = ok_all and ok
            except Exception as e:
                ok_all = False
                report["base_checks"].append({"n": k_val, "error": str(e)})
        report["base_ok"] = ok_all
    k = symbols("k", integer=True)
    Pk1 = sympify(predicate_str, locals={n_symbol: k + 1})
    try:
        with assuming(Q.integer(k), Q.ge(k, base_from)):
            step_holds = bool(simplify(Pk1))
            report["inductive_step"] = {"ok": step_holds, "Pk1": str(Pk1)}
    except Exception as e:
        report["inductive_step"] = {"error": str(e)}
    report["proved"] = bool(report.get("base_ok")) and bool(report.get("inductive_step", {}).get("ok", False))
    return report
