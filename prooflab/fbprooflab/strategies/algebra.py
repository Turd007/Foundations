from sympy import symbols, sympify, simplify

def prove_identity(claim):
    # Required fields
    ss = claim["state_symbols"]          # e.g. ["x", "y"] or ["x"]
    us = claim.get("input_symbols", [])  # e.g. ["u"] or []
    fnext = claim.get("F_next", {})      # e.g. {"x": "0.6*x + 0.2*u"}

    # Build symbol environment for current-step variables
    sym_env = {name: symbols(name) for name in (ss + us)}

    # Build "next" substitutions: x_next := sympify(F_next["x"], env)
    subs_next_env = {}
    for s in ss:
        if s in fnext:
            subs_next_env[f"{s}_next"] = sympify(fnext[s], locals=sym_env)

    # Parse LHS/RHS with both current symbols and next-step substitutions
    lhs = sympify(claim["lhs"], locals={**sym_env, **subs_next_env})
    rhs = sympify(claim["rhs"], locals={**sym_env, **subs_next_env})

    res = simplify(lhs - rhs)
    ok = (res == 0)
    return {
        "verdict": "proved" if ok else "falsified",
        "symbolic_equal": ok,
        "residual": str(res),
        "lhs": str(lhs),
        "rhs": str(rhs),
    }
