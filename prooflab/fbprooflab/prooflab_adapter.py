# prooflab_adapter.py
from __future__ import annotations
import json, pathlib, time
from datetime import datetime
from typing import List, Dict, Any, Optional

# Our shared OpenAI bridge
try:
    from fb_api_client import ask_json
except Exception:
    ask_json = None  # graceful fallback

REPORTS_DIR = pathlib.Path("./Reports").resolve()
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

def _log_urp_event(event: Dict[str, Any]) -> None:
    """Append a JSON line per URP decision to daily log."""
    stamp = datetime.utcnow().strftime("%Y-%m-%d")
    fpath = REPORTS_DIR / f"urp_calls_{stamp}.jsonl"
    event["ts_utc"] = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    with fpath.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")

def _score_reliability(urp: Dict[str, Any]) -> float:
    """
    Simple reliability proxy you can evolve later.
    Factors: presence of evidence, clarity of verdict, and confidence.
    Returns 0..1
    """
    verdict_ok = 1.0 if urp.get("verdict") in {"supported","refuted","inconclusive"} else 0.0
    evidence = urp.get("evidence") or []
    gaps = urp.get("gaps") or []
    confidence = float(urp.get("confidence") or 0.0)
    # crude mix; tune weights later
    base = 0.2 * verdict_ok + 0.5 * min(len(evidence), 5) / 5 + 0.2 * (1.0 - min(len(gaps), 5)/5) + 0.1 * max(0.0, min(confidence, 1.0))
    return round(max(0.0, min(1.0, base)), 3)

def urp(claim: str, assumptions: List[str], *, context: Optional[str]=None) -> Dict[str, Any]:
    """
    Uncertainty Resolution Protocol.
    Returns:
      {
        verdict: 'supported'|'refuted'|'inconclusive',
        evidence: [str],
        gaps: [str],
        next_tests: [str],
        assumptions_used: [str],
        risk_level: 'low'|'medium'|'high',
        confidence: float (0..1)
      }
    """
    t0 = time.perf_counter()

    # Fallback path if API bridge is unavailable (won't be smart, but will never crash)
    if ask_json is None:
        result = {
            "verdict": "inconclusive",
            "evidence": [],
            "gaps": ["AI bridge unavailable"],
            "next_tests": ["Enable fb_api_client and re-run URP."],
            "assumptions_used": assumptions[:],
            "risk_level": "medium",
            "confidence": 0.0,
        }
        result["reliability_score"] = _score_reliability(result)
        _log_urp_event({"ok": True, "latency_s": round(time.perf_counter()-t0, 3), "input_claim": claim, "result": result})
        return result

    schema = (
        '{"verdict":"string",'
        '"evidence":["string"],'
        '"gaps":["string"],'
        '"next_tests":["string"],'
        '"assumptions_used":["string"],'
        '"risk_level":"string",'
        '"confidence":"number"}'
    )

    prompt = (
        "Uncertainty Resolution Protocol (URP).\n"
        "Task: Evaluate the claim under the given assumptions.\n"
        "Be terse and technical (no fluff). Use only information derivable from the text.\n"
        "If evidence is weak or missing, be honest and set 'inconclusive' with explicit gaps and next_tests.\n\n"
        f"Claim:\n{claim}\n\n"
        f"Assumptions:\n{assumptions}\n\n"
        f"Context (optional):\n{context or 'n/a'}\n\n"
        "Return ONLY JSON with the fields per the schema."
    )

    urp_out = ask_json(
        prompt=prompt,
        schema_hint=schema,
        temperature=0
    )

    # Post-process + log
    urp_out.setdefault("assumptions_used", assumptions[:])
    urp_out.setdefault("risk_level", "medium")
    urp_out.setdefault("confidence", 0.0)
    urp_out["reliability_score"] = _score_reliability(urp_out)

    _log_urp_event({
        "ok": True,
        "latency_s": round(time.perf_counter() - t0, 3),
        "input_claim": claim,
        "n_assumptions": len(assumptions),
        "reliability_score": urp_out["reliability_score"],
        "result": urp_out
    })
    return urp_out

if __name__ == "__main__":
    # Minimal CLI: python prooflab_adapter.py "claim text" "assumption1;assumption2" "optional context"
    import sys
    claim = sys.argv[1] if len(sys.argv) > 1 else "x**2+2*x+1 equals (x+1)**2 for real x"
    assumptions = (sys.argv[2].split(";") if len(sys.argv) > 2 else ["x is real"])
    ctx = (sys.argv[3] if len(sys.argv) > 3 else None)
    print(json.dumps(urp(claim, assumptions, context=ctx), ensure_ascii=False, indent=2))

