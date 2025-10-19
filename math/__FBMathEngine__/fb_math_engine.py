"""
fb_math_engine.py – Symbolic and numerical math utilities for Foundation's Bridge
"""
import sys
from pathlib import Path

# Simple re-export layer so we can import fb_math_engine directly
from fbmathengine.__FBMathEngine__.fb_math_engine import *

import sys
from pathlib import Path
# AI bridge (OpenAI) – optional helper
try:
    from fb_api_client import ask_json  # our shared client
except Exception:  # don’t crash the engine if missing
    ask_json = None
def explain_symbolic_step(expr_str: str) -> dict:
    """
    AI-assisted explanation of algebraic steps for an expression.
    Returns a dict: {steps: [str], invariants: [str], result: str}
    Falls back to a deterministic SymPy-only explanation if API is unavailable.
    """
    # If the AI bridge isn’t available, try a tiny deterministic fallback.
    if ask_json is None:
        simplified = evaluate_expression(expr_str, use_cache=True)
        return {
            "steps": [f"Simplified expression → {simplified}"],
            "invariants": ["symbolic form preserved"],
            "result": simplified,
        }

    prompt = (
        f"Given the expression:\n{expr_str}\n\n"
        "Return JSON with:\n"
        "- steps: list of algebraic transformation steps (strings)\n"
        "- invariants: list of preserved properties (e.g., identity, domain)\n"
        "- result: the simplified final expression (string)"
    )

    return ask_json(
        prompt=prompt,
        schema_hint='{"steps":["string"],"invariants":["string"],"result":"string"}',
        temperature=0
    )

# Add the canonical math_engine directory to the path
canonical_path = Path(__file__).resolve().parent.parent / "FBMathEngine" / "math_engine"
sys.path.insert(0, str(canonical_path))

# Import the actual implementations from the canonical location
try:
    from fb_math_engine import evaluate_expression, solve_equation
except ImportError:
    # Fallback implementation if canonical module is not available
    import sympy as sp
    import numpy as np

    def evaluate_expression(expr_str):
        try:
            expr = sp.sympify(expr_str)
            simplified = sp.simplify(expr)
            return str(simplified)
        except Exception as e:
            return f"Error: {e}"

    def solve_equation(equation_str, symbol_str="x"):
        try:
            x = sp.Symbol(symbol_str)
            equation = sp.sympify(equation_str)
            solutions = sp.solve(equation, x)
            return [str(sol) for sol in solutions]
        except Exception as e:
            return [f"Error: {e}"]

# Export the functions
__all__ = ['evaluate_expression', 'solve_equation'
'explain_symbolic_step',
]
