"""
fb_math_engine.py – Symbolic and numerical math utilities for Foundation's Bridge

This module provides a wrapper that attempts to import math engine functionality
from a canonical location, with robust fallback implementations using SymPy.

Features:
    - Expression evaluation and simplification
    - Equation solving with symbolic math
    - Graceful fallback when canonical module is unavailable
    - Comprehensive error handling with custom exceptions
    - Performance optimization with caching and lazy loading
    - Security features including input validation and timeouts
    - Configurable behavior

Example:
    >>> from fb_math_engine_improved_v2 import evaluate_expression, solve_equation
    >>> evaluate_expression("x**2 + 2*x + 1")
    '(x + 1)**2'
    >>> solve_equation("x**2 - 4")
    ['-2', '2']
"""

import logging
import re
import sys
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import List, Optional, Tuple, Callable, Protocol

# Module metadata
__version__ = "2.0.0"
__author__ = "Foundation's Bridge Team"
__license__ = "MIT"

# Configure module logger
logger = logging.getLogger(__name__)


# ============================================================================
# Custom Exceptions
# ============================================================================

class MathEngineError(Exception):
    """Base exception for math engine errors."""
    pass


class ExpressionError(MathEngineError):
    """Raised when expression evaluation fails."""
    pass


class EquationError(MathEngineError):
    """Raised when equation solving fails."""
    pass


class ValidationError(MathEngineError):
    """Raised when input validation fails."""
    pass


# ============================================================================
# Configuration
# ============================================================================

@dataclass
class MathEngineConfig:
    """Configuration for math engine behavior."""
    timeout_seconds: int = 30
    cache_size: int = 128
    max_expression_length: int = 10000
    enable_validation: bool = True
    log_level: str = "INFO"


# Global config instance
_config = MathEngineConfig()


def configure(config: MathEngineConfig) -> None:
    """
    Configure math engine behavior.
    
    Args:
        config: Configuration object with desired settings
    """
    global _config
    _config = config
    
    # Update logger level
    logger.setLevel(getattr(logging, config.log_level.upper()))
    
    logger.info(f"Math engine configured: {config}")


def get_config() -> MathEngineConfig:
    """Get current configuration."""
    return _config


# ============================================================================
# Type Protocols
# ============================================================================

class EvaluateFunction(Protocol):
    """Type protocol for evaluate_expression function."""
    def __call__(self, expr_str: str) -> str: ...


class SolveFunction(Protocol):
    """Type protocol for solve_equation function."""
    def __call__(self, equation_str: str, symbol_str: str = "x") -> List[str]: ...


# ============================================================================
# Lazy SymPy Import
# ============================================================================

_sympy = None


def _get_sympy():
    """
    Lazy load SymPy only when needed.
    
    Returns:
        SymPy module
        
    Raises:
        ImportError: If SymPy is not available
    """
    global _sympy
    if _sympy is None:
        try:
            import sympy as sp
            _sympy = sp
            logger.debug("SymPy loaded successfully")
        except ImportError as e:
            logger.error(f"SymPy not available: {e}")
            raise ImportError(
                "SymPy is required for fallback implementations. "
                "Install it with: pip install sympy"
            ) from e
    return _sympy


# ============================================================================
# Input Validation
# ============================================================================

def _validate_expression(expr_str: str) -> None:
    """
    Validate expression string for safety.
    
    Args:
        expr_str: Expression string to validate
        
    Raises:
        ValidationError: If expression contains potentially dangerous patterns
    """
    if not _config.enable_validation:
        return
    
    # Check for dangerous patterns
    dangerous_patterns = [
        r'__import__',
        r'eval\s*\(',
        r'exec\s*\(',
        r'compile\s*\(',
        r'open\s*\(',
        r'file\s*\(',
        r'input\s*\(',
        r'__\w+__',  # dunder methods/attributes
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, expr_str, re.IGNORECASE):
            raise ValidationError(
                f"Expression contains potentially dangerous pattern: {pattern}"
            )
    
    # Check for maximum length to prevent DoS
    if len(expr_str) > _config.max_expression_length:
        raise ValidationError(
            f"Expression exceeds maximum allowed length of "
            f"{_config.max_expression_length} characters"
        )


def validate_expression(expr_str: str) -> Tuple[bool, Optional[str]]:
    """
    Validate an expression without evaluating it.
    
    Args:
        expr_str: Expression string to validate
        
    Returns:
        Tuple of (is_valid, error_message)
        
    Example:
        >>> valid, error = validate_expression("x**2 + 1")
        >>> assert valid and error is None
        
        >>> valid, error = validate_expression("__import__('os')")
        >>> assert not valid and error is not None
    """
    try:
        _validate_expression(expr_str)
        
        # Try to parse (but don't evaluate)
        sp = _get_sympy()
        sp.sympify(expr_str)
        
        return True, None
    except Exception as e:
        return False, str(e)


# ============================================================================
# Timeout Support (Cross-platform)
# ============================================================================

class TimeoutError(MathEngineError):
    """Raised when operation exceeds timeout."""
    pass


def _run_with_timeout(func: Callable, args: tuple, timeout_seconds: int):
    """
    Run a function with timeout (cross-platform).
    
    Args:
        func: Function to run
        args: Arguments to pass to function
        timeout_seconds: Timeout in seconds
        
    Returns:
        Function result
        
    Raises:
        TimeoutError: If function exceeds timeout
    """
    result = [None]
    exception = [None]
    
    def worker():
        try:
            result[0] = func(*args)
        except Exception as e:
            exception[0] = e
    
    thread = threading.Thread(target=worker)
    thread.daemon = True
    thread.start()
    thread.join(timeout_seconds)
    
    if thread.is_alive():
        raise TimeoutError(
            f"Operation exceeded {timeout_seconds} second timeout"
        )
    
    if exception[0]:
        raise exception[0]
    
    return result[0]


# ============================================================================
# Canonical Path Resolution
# ============================================================================

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
            
    except (OSError, RuntimeError) as e:
        logger.error(f"Error determining canonical path: {e}")
        return None


def _try_import_canonical() -> Tuple[Optional[EvaluateFunction], Optional[SolveFunction]]:
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


# ============================================================================
# Fallback Implementations
# ============================================================================

def _fallback_evaluate_expression_impl(expr_str: str) -> str:
    """
    Internal implementation for expression evaluation using SymPy.
    
    Args:
        expr_str: String representation of mathematical expression
    
    Returns:
        Simplified expression as string
        
    Raises:
        ExpressionError: If evaluation fails
    """
    try:
        sp = _get_sympy()
        
        expr = sp.sympify(expr_str)
        simplified = sp.simplify(expr)
        return str(simplified)
        
    except sp.SympifyError as e:
        logger.error(f"Invalid expression syntax: {e}")
        raise ExpressionError(f"Invalid expression syntax: {e}") from e
    except (ValueError, TypeError, AttributeError) as e:
        logger.error(f"Expression evaluation failed: {type(e).__name__}: {e}")
        raise ExpressionError(f"Expression evaluation failed: {e}") from e


def _fallback_evaluate_expression(expr_str: str) -> str:
    """
    Fallback implementation for expression evaluation with timeout.
    
    Args:
        expr_str: String representation of mathematical expression
    
    Returns:
        Simplified expression as string
        
    Raises:
        ExpressionError: If evaluation fails
        TimeoutError: If evaluation exceeds timeout
    """
    try:
        return _run_with_timeout(
            _fallback_evaluate_expression_impl,
            (expr_str,),
            _config.timeout_seconds
        )
    except TimeoutError as e:
        logger.error(f"Expression evaluation timed out: {e}")
        raise


def _fallback_solve_equation_impl(equation_str: str, symbol_str: str) -> List[str]:
    """
    Internal implementation for equation solving using SymPy.
    
    Args:
        equation_str: String representation of equation to solve
        symbol_str: Symbol to solve for
    
    Returns:
        List of solutions as strings
        
    Raises:
        EquationError: If solving fails
    """
    try:
        sp = _get_sympy()
        
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
        logger.error(f"Invalid equation syntax: {e}")
        raise EquationError(f"Invalid equation syntax: {e}") from e
    except (ValueError, TypeError, AttributeError) as e:
        logger.error(f"Equation solving failed: {type(e).__name__}: {e}")
        raise EquationError(f"Equation solving failed: {e}") from e


def _fallback_solve_equation(equation_str: str, symbol_str: str) -> List[str]:
    """
    Fallback implementation for equation solving with timeout.
    
    Args:
        equation_str: String representation of equation to solve
        symbol_str: Symbol to solve for
    
    Returns:
        List of solutions as strings
        
    Raises:
        EquationError: If solving fails
        TimeoutError: If solving exceeds timeout
    """
    try:
        return _run_with_timeout(
            _fallback_solve_equation_impl,
            (equation_str, symbol_str),
            _config.timeout_seconds
        )
    except TimeoutError as e:
        logger.error(f"Equation solving timed out: {e}")
        raise


# ============================================================================
# Cached Implementations
# ============================================================================

@lru_cache(maxsize=128)
def _cached_evaluate_expression(expr_str: str) -> str:
    """Cached version of expression evaluation."""
    if _canonical_eval is not None:
        return _canonical_eval(expr_str)
    return _fallback_evaluate_expression(expr_str)


@lru_cache(maxsize=128)
def _cached_solve_equation(equation_str: str, symbol_str: str) -> tuple:
    """Cached version of equation solving. Returns tuple for hashability."""
    if _canonical_solve is not None:
        result = _canonical_solve(equation_str, symbol_str)
    else:
        result = _fallback_solve_equation(equation_str, symbol_str)
    return tuple(result)  # Convert list to tuple for caching


# ============================================================================
# Public API
# ============================================================================

def evaluate_expression(expr_str: str, use_cache: bool = True) -> str:
    """
    Evaluate and simplify a mathematical expression.
    
    Attempts to use canonical implementation if available, otherwise
    uses fallback SymPy implementation with timeout and caching.
    
    Args:
        expr_str: String representation of mathematical expression
                 (e.g., "x**2 + 2*x + 1", "sin(x) + cos(x)")
        use_cache: Whether to use cached results (default: True)
    
    Returns:
        Simplified expression as string
        
    Raises:
        ValueError: If expr_str is empty or invalid type
        ValidationError: If expr_str contains dangerous patterns
        ExpressionError: If expression evaluation fails
        TimeoutError: If evaluation exceeds timeout limit
        ImportError: If SymPy is not available (fallback mode only)
        
    Examples:
        >>> evaluate_expression("x**2 + 2*x + 1")
        '(x + 1)**2'
        
        >>> evaluate_expression("sin(x)**2 + cos(x)**2")
        '1'
        
    Note:
        - Results are cached by default for better performance
        - Maximum expression length is configurable (default: 10000 characters)
        - Evaluation timeout is configurable (default: 30 seconds)
        - Dangerous patterns are blocked (e.g., __import__, eval, exec)
    """
    if not expr_str or not isinstance(expr_str, str):
        raise ValueError("Expression string must be a non-empty string")
    
    _validate_expression(expr_str)
    
    if use_cache:
        return _cached_evaluate_expression(expr_str)
    
    if _canonical_eval is not None:
        return _canonical_eval(expr_str)
    
    return _fallback_evaluate_expression(expr_str)


def solve_equation(
    equation_str: str, 
    symbol_str: str = "x",
    use_cache: bool = True
) -> List[str]:
    """
    Solve an equation for a given symbol.
    
    Attempts to use canonical implementation if available, otherwise
    uses fallback SymPy implementation with timeout and caching.
    
    Args:
        equation_str: String representation of equation to solve
                     (e.g., "x**2 - 4", "2*x + 3 - 7")
        symbol_str: Symbol to solve for (default: "x")
        use_cache: Whether to use cached results (default: True)
    
    Returns:
        List of solutions as strings
        
    Raises:
        ValueError: If equation_str or symbol_str are empty or invalid type
        ValidationError: If equation_str contains dangerous patterns
        EquationError: If equation solving fails
        TimeoutError: If solving exceeds timeout limit
        ImportError: If SymPy is not available (fallback mode only)
        
    Examples:
        >>> solve_equation("x**2 - 4")
        ['-2', '2']
        
        >>> solve_equation("2*y + 3 - 7", symbol_str="y")
        ['2']
        
    Note:
        - Results are cached by default for better performance
        - Maximum equation length is configurable (default: 10000 characters)
        - Solving timeout is configurable (default: 30 seconds)
        - Dangerous patterns are blocked (e.g., __import__, eval, exec)
    """
    if not equation_str or not isinstance(equation_str, str):
        raise ValueError("Equation string must be a non-empty string")
    
    if not symbol_str or not isinstance(symbol_str, str):
        raise ValueError("Symbol must be a non-empty string")
    
    _validate_expression(equation_str)
    
    if use_cache:
        return list(_cached_solve_equation(equation_str, symbol_str))
    
    if _canonical_solve is not None:
        return _canonical_solve(equation_str, symbol_str)
    
    return _fallback_solve_equation(equation_str, symbol_str)


def clear_cache() -> None:
    """
    Clear the expression evaluation and equation solving caches.
    
    Use this to free memory or ensure fresh evaluations.
    """
    _cached_evaluate_expression.cache_clear()
    _cached_solve_equation.cache_clear()
    logger.info("Caches cleared")


# ============================================================================
# Testing Support
# ============================================================================

def _reset_module_state():
    """Reset module state for testing purposes."""
    global _canonical_eval, _canonical_solve, _sympy, _config
    _canonical_eval = None
    _canonical_solve = None
    _sympy = None
    _config = MathEngineConfig()
    clear_cache()
    logger.info("Module state reset")


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    # Main functions
    'evaluate_expression',
    'solve_equation',
    
    # Validation
    'validate_expression',
    
    # Configuration
    'configure',
    'get_config',
    'MathEngineConfig',
    
    # Cache management
    'clear_cache',
    
    # Exceptions
    'MathEngineError',
    'ExpressionError',
    'EquationError',
    'ValidationError',
    'TimeoutError',
    
    # Metadata
    '__version__',
]

# Only expose for testing in debug mode
if __debug__:
    __all__.append('_reset_module_state')


# ============================================================================
# Module Initialization
# ============================================================================

if _canonical_eval is not None:
    logger.info(
        f"Math engine v{__version__} initialized with canonical implementations"
    )
else:
    logger.info(
        f"Math engine v{__version__} initialized with fallback implementations"
    )
