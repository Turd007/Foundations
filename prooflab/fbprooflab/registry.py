from __future__ import annotations
from typing import Dict, Any, List
from dataclasses import dataclass
import yaml
from .claims import ClaimResult
from .strategies.algebra import prove_identity
from .strategies.induction import prove_induction
from .strategies.lyapunov import prove_lyapunov
from .strategies.gate import verify_gate
from .strategies.contraction import check_contraction

@dataclass
class ClaimSpec:
    id: str
    type: str
    data: Dict[str, Any]

def load_claims_from_yaml(path: str) -> List[ClaimSpec]:
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    out: List[ClaimSpec] = []
    for item in raw.get("claims", []):
        out.append(ClaimSpec(id=item["id"], type=item["type"], data=item))
    return out

def run_claim(spec: ClaimSpec) -> ClaimResult:
    t = spec.type
    d = spec.data

    if t == "identity":
        rep = prove_identity(d)
        status = "proved" if rep.get("symbolic_equal") else "rejected"
        return ClaimResult(id=spec.id, type=t, status=status, details=rep)

    elif t == "induction":
        rep = prove_induction(
            d["predicate"],
            d.get("n_symbol", "n"),
            int(d.get("base_from", 1)),
            int(d.get("base_to", 1)),
            d.get("assumptions")
        )
        status = "proved" if rep.get("proved") else "rejected"
        return ClaimResult(id=spec.id, type=t, status=status, details=rep)

    elif t == "lyapunov":
        # call the wrapper form, see lyapunov.py for details
        rep = prove_lyapunov(d)
        status = "proved" if (rep.get("symbolic_ok") or rep.get("ok") or rep.get("proved")) else "rejected"
        return ClaimResult(id=spec.id, type=t, status=status, details=rep)

    elif t == "gate":
        rep = verify_gate(
            d["symbols"],
            d["continue_condition"],
            d["halt_condition"],
            int(d.get("numeric_trials", 300)),
            d.get("ranges")
        )
        status = "proved" if rep.get("passed") else "rejected"
        return ClaimResult(id=spec.id, type=t, status=status, details=rep)

    elif t == "contraction":
        rep = check_contraction(
            d["state_symbols"],
            d["F_next"],
            float(d["L_bound"]),
            d.get("norm", "l2"),
            int(d.get("numeric_trials", 300)),
            d.get("ranges")
        )
        status = "proved" if rep.get("passed") else "rejected"
        return ClaimResult(id=spec.id, type=t, status=status, details=rep)

    else:
        return ClaimResult(id=spec.id, type=t, status="inconclusive", details={"error": "Unknown claim type"})

