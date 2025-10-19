from __future__ import annotations
from typing import Dict, Any, List, Optional
from sympy import symbols, sympify, Matrix, lambdify
import numpy as np
import random

def check_contraction(state_symbols: List[str],
                      F_next: List[str],
                      L_bound: float,
                      norm: str = "l2",
                      numeric_trials: int = 300,
                      ranges: Optional[Dict[str, List[float]]] = None) -> Dict[str, Any]:
    sym_map = {s: symbols(s, real=True) for s in state_symbols}
    F = Matrix([sympify(e, locals=sym_map) for e in F_next])
    x = Matrix([sym_map[s] for s in state_symbols])
    J = F.jacobian(x)
    Jf = lambdify([x], J, "numpy")

    max_norm = 0.0
    for _ in range(int(numeric_trials)):
        vec = []
        for s in state_symbols:
            lo, hi = (-2.0, 2.0)
            if ranges and s in ranges: lo, hi = ranges[s]
            vec.append(random.uniform(lo, hi))
        import numpy as np
        X = np.array(vec, dtype=float).reshape(-1,1)
        try:
            Jval = np.array(Jf(X), dtype=float)
            if norm == "linf":
                nval = float(np.max(np.sum(np.abs(Jval), axis=1)))
            else:
                svals = np.linalg.svd(Jval, compute_uv=False)
                nval = float(np.max(svals))
            max_norm = max(max_norm, nval)
        except Exception:
            max_norm = float("inf"); break

    return {"max_norm": float(max_norm), "samples": int(numeric_trials), "passed": bool(max_norm <= L_bound + 1e-9),
            "norm": norm, "L_bound": float(L_bound)}
