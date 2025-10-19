"""Proof strategies for different types of mathematical claims."""

from .algebra import prove_identity
from .induction import prove_induction
from .lyapunov import prove_lyapunov
from .gate import verify_gate
from .contraction import check_contraction

__all__ = [
    "prove_identity",
    "prove_induction", 
    "prove_lyapunov",
    "verify_gate",
    "check_contraction"
]
