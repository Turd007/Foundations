from __future__ import annotations
import re
from typing import Dict, List

# Basic operation keywords
_OPS = [
    "equals", "=", "≈", "≡",
    "greater than", ">", ">=",
    "less than", "<", "<=",
    "converges", "diverges", "is prime", "is integer",
]

def _find_symbols(s: str) -> List[str]:
    # crude symbol detector: identifiers and latex-ish tokens
    toks = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*|\\[A-Za-z]+|[α-ωΑ-Ω]", s))
    stop = {"equals","for","all","real","reals","such","that","is","are","and","or","if","then"}
    return [t for t in toks if t.lower() not in stop]

def _find_ops(s: str) -> List[str]:
    out = []
    lo = s.lower()
    for op in _OPS:
        if op in lo:
            out.append(op)
    return list(dict.fromkeys(out))

def analyze_claim(claim: str, assumptions: List[str] | None = None) -> Dict:
    assumptions = assumptions or []
    symbols = _find_symbols(claim)
    ops = _find_ops(claim)

    ambiguities: List[str] = []
    risks: List[str] = []

    if "equals" not in ops and "=" not in ops and "≡" not in ops:
        ambiguities.append("No explicit equality/relationship operator detected.")
    if any(w in claim for w in ["for all", "∀"]) and "domain" not in " ".join(assumptions).lower():
        risks.append("Global quantifier without explicit domain assumptions.")
    if "sin" in claim and "cos" in claim and "identity" not in " ".join(assumptions).lower():
        risks.append("Trigonometric identity assumed but not stated.")

    normalized_claim = claim.strip()

    return {
        "normalized_claim": normalized_claim,
        "symbols": symbols,
        "operations": ops,
        "assumptions_extracted": assumptions,
        "ambiguities": ambiguities,
        "risks": risks,
    }
