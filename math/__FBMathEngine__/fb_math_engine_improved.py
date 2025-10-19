"""
fb_math_engine.py – Symbolic and numerical math utilities for Foundation's Bridge

This module provides a wrapper that attempts to import math engine functionality
from a canonical location, with robust fallback implementations using SymPy.

Features:
    - Expression evaluation and simplification
    - Equation solving with symbolic math
    - Graceful fallback when canonical module is unavailable
    - Comprehensive error handling and logging

Example:
    >>> from fb_math_engine import evaluate_expression, solve_equation
    >>> evaluate_expression("x**2 + 2*x + 1")
    '(x + 1)**2'
    >>> solve_equation("x**2 - 4")
    ['-2', '2']
"""

import sys
import logging
from pathlib import Path
from typing import List, Union, Optional
from contextlib import contextmanager

# Configure module logger
logger = logging.getLogger(__name__)


@contextmanager
def _temporary_path_modification(path: Path):
    """
    Context manager for temporarily modifying sys.path.
    
    Ensures sys.path is restored even if an exception occurs during import.
    
    Args:
        path: Path to temporarily add to sys.path
        
    Yields:
        None
    """
    path_str = str(path)
    sys.path.insert(0, path_str)
    try:
        yield
    finally:
        try:
            sys.path.remove(path_str)
        except ValueError:
            # Path was already removed or never added
            pass


def _get_canonical_path() -> Optional[Path]:
    """
    Calculate the canonical math engine path with validation.
    
    Returns:
        Path object if canonical location exists, None otherwise
    """
    try:
        canonical_path = (
            Path(__file__).resolve().parent.parent 
            / "FBMathEngine" 
            / "math_engine"
        )
        
        if canonical_path.exists() and canonical_path.is_dir():
            return canonical_path
        else:
            logger.warning(
                f"Canonical math engine path not found: {canonical_path}"
            )
            return None
            
    except Exception as e:
        logger.error(f"Error determining canonical path: {e}")
        return None


def _try_import_canonical():
    """
    Attempt to import functions from canonical location.
    
    Returns:
        Tuple of (evaluate_expression, solve_equation) if successful,
        (None, None) if import fails
    """
    canonical_path = _get_canonical_path()
    
    if canonical_path is None:
        logger.info("Using fallback implementations (canonical path not found)")
        return None, None
    
    try:
        with _temporary_path_modification(canonical_path):
            # Import from canonical location
            # Note: This imports a different module, not this file
            from fb_math_engine import evaluate_expression, solve_equation
            
            logger.info("Successfully imported from canonical location")
            return evaluate_expression, solve_equation
            
    except ImportError as e:
        logger.info(
            f"Canonical module not available, using fallback: {e}"
        )
        return None, None
    except Exception as e:
        logger.warning(
            f"Unexpected error importing canonical module: {e}"
        )
        return None, None


# Attempt to import from canonical location
_canonical_eval, _canonical_solve = _try_import_canonical()


def evaluate_expression(expr_str: str) -> str:
    """
    Evaluate and simplify a mathematical expression.
    
    Attempts to use canonical implementation if available, otherwise
    uses fallback SymPy implementation.
    
    Args:
        expr_str: String representation of mathematical expression
                 (e.g., "x**2 + 2*x + 1", "sin(x) + cos(x)")
    
    Returns:
        Simplified expression as string
        
    Raises:
        ValueError: If expr_str is empty or invalid
        
    Example:
        >>> evaluate_expression("x**2 + 2*x + 1")
        '(x + 1)**2'
    """
    if not expr_str or not isinstance(expr_str, str):
        raise ValueError("Expression string must be a non-empty string")
    
    if _canonical_eval is not None:
        return _canonical_eval(expr_str)
    
    # Fallback implementation
    return _fallback_evaluate_expression(expr_str)


def solve_equation(
    equation_str: str, 
    symbol_str: str = "x"
) -> List[str]:
    """
    Solve an equation for a given symbol.
    
    Attempts to use canonical implementation if available, otherwise
    uses fallback SymPy implementation.
    
    Args:
        equation_str: String representation of equation to solve
                     (e.g., "x**2 - 4", "2*x + 3 - 7")
        symbol_str: Symbol to solve for (default: "x")
    
    Returns:
        List of solutions as strings
        
    Raises:
        ValueError: If equation_str is empty or symbol_str is invalid
        
    Example:
        >>> solve_equation("x**2 - 4")
        ['-2', '2']
    """
    if not equation_str or not isinstance(equation_str, str):
        raise ValueError("Equation string must be a non-empty string")
    
    if not symbol_str or not isinstance(symbol_str, str):
        raise ValueError("Symbol must be a non-empty string")
    
    if _canonical_solve is not None:
        return _canonical_solve(equation_str, symbol_str)
    
    # Fallback implementation
    return _fallback_solve_equation(equation_str, symbol_str)


def _fallback_evaluate_expression(expr_str: str) -> str:
    """
    Fallback implementation for expression evaluation using SymPy.
    
    Args:
        expr_str: String representation of mathematical expression
    
    Returns:
        Simplified expression as string, or error message
    """
    try:
        import sympy as sp
        
        expr = sp.sympify(expr_str)
        simplified = sp.simplify(expr)
        return str(simplified)
        
    except sp.SympifyError as e:
        error_msg = f"Invalid expression syntax: {e}"
        logger.error(error_msg)
        return f"Error: {error_msg}"
    except Exception as e:
        error_msg = f"Expression evaluation failed: {type(e).__name__}: {e}"
        logger.error(error_msg)
        return f"Error: {error_msg}"


def _fallback_solve_equation(
    equation_str: str, 
    symbol_str: str = "x"
) -> List[str]:
    """
    Fallback implementation for equation solving using SymPy.
    
    Args:
        equation_str: String representation of equation to solve
        symbol_str: Symbol to solve for
    
    Returns:
        List of solutions as strings, or list with error message
    """
    try:
        import sympy as sp
        
        # Create symbol
        symbol = sp.Symbol(symbol_str)
        
        # Parse equation
        equation = sp.sympify(equation_str)
        
        # Solve equation
        solutions = sp.solve(equation, symbol)
        
        # Convert solutions to strings
        result = [str(sol) for sol in solutions]
        
        if not result:
            logger.info(f"No solutions found for equation: {equation_str}")
        
        return result
        
    except sp.SympifyError as e:
        error_msg = f"Invalid equation syntax: {e}"
        logger.error(error_msg)
        return [f"Error: {error_msg}"]
    except Exception as e:
        error_msg = f"Equation solving failed: {type(e).__name__}: {e}"
        logger.error(error_msg)
        return [f"Error: {error_msg}"]


# Public API
__all__ = ['evaluate_expression', 'solve_equation']


# Module initialization logging
if _canonical_eval is not None:
    logger.info("Module initialized with canonical implementations")
else:
    logger.info("Module initialized with fallback implementations")
