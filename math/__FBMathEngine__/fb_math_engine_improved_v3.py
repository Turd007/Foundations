"""
fb_math_engine.py – Symbolic and numerical math utilities for Foundation's Bridge

This module provides a wrapper that attempts to import math engine functionality
from a canonical location, with robust fallback implementations using SymPy.

Features:
    - Expression evaluation and simplification
    - Equation solving with symbolic math
    - Graceful fallback when canonical module is unavailable
    - Comprehensive error handling and logging
    - Input validation and security
    - Caching for performance optimization
    - Timeout protection for long-running operations
    - Configurable behavior
    - Rate limiting for DoS protection

Example:
    >>> from fb_math_engine import evaluate_expression, solve_equation
    >>> evaluate_expression("x**2 + 2*x + 1")
    '(x + 1)**2'
    >>> solve_equation("x**2 - 4")
    ['-2', '2']
"""

import sys
import logging
import re
import time
import signal
from pathlib import Path
from typing import List, Optional, Tuple, Callable, Protocol
from contextlib import contextmanager
from functools import lru_cache
from dataclasses import dataclass
from enum import Enum
from collections import deque
from concurrent.futures import ThreadPoolExecutor

# Module version and metadata
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


class TimeoutError(MathEngineError):
    """Raised when operation exceeds timeout limit."""
    pass


class RateLimitError(MathEngineError):
    """Raised when rate limit is exceeded."""
    pass


# ============================================================================
# Configuration
# ============================================================================

class SimplificationLevel(Enum):
    """Level of simplification to apply."""
    NONE = "none"
    BASIC = "basic"
    FULL = "full"
    AGGRESSIVE = "aggressive"


@dataclass
class MathEngineConfig:
    """Configuration for math engine behavior."""
    timeout_seconds: int = 30
    cache_size: int = 128
    max_expression_length: int = 10000
    enable_validation: bool = True
    enable_rate_limiting: bool = True
    rate_limit_max_calls: int = 100
    rate_limit_time_window: int = 60  # seconds
    log_level: str = "INFO"
    default_simplification: SimplificationLevel = SimplificationLevel.FULL


# Global config instance
_config = MathEngineConfig()

# Lazy-loaded SymPy reference
_sympy = None


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
# Rate Limiting
# ============================================================================

class RateLimiter:
    """Rate limiter to prevent abuse."""
    
    def __init__(self, max_calls: int, time_window: int):
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = deque()
    
    def allow(self) -> bool:
        """Check if a call is allowed within rate limits."""
        now = time.time()
        # Remove old calls outside time window
        while self.calls and self.calls[0] < now - self.time_window:
            self.calls.popleft()
        
        if len(self.calls) < self.max_calls:
            self.calls.append(now)
            return True
        return False
    
    def reset(self):
        """Reset the rate limiter."""
        self.calls.clear()


_rate_limiter = RateLimiter(
    max_calls=_config.rate_limit_max_calls,
    time_window=_config.rate_limit_time_window
)


# ============================================================================
# Configuration Functions
# ============================================================================

def configure(config: MathEngineConfig) -> None:
    """
    Configure math engine behavior.
    
    Args:
        config: Configuration object with desired settings
    """
    global _config, _rate_limiter
    _config = config
    
    # Update logger level
    logger.setLevel(getattr(logging, config.log_level.upper()))
    
    # Clear caches if cache size changed
    _cached_evaluate_expression.cache_clear()
    _cached_solve_equation.cache_clear()
    
    # Update rate limiter
    _rate_limiter = RateLimiter(
        max_calls=config.rate_limit_max_calls,
        time_window=config.rate_limit_time_window
    )


def get_config() -> MathEngineConfig:
    """Get current configuration."""
    return _config


# ============================================================================
# Context Managers
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


@contextmanager
def timeout(seconds: int):
    """
    Context manager to timeout long-running operations.
    
    Args:
        seconds: Timeout duration in seconds
        
    Raises:
        TimeoutError: If operation exceeds timeout
        
    Note:
        This uses SIGALRM and only works on Unix-like systems.
        On Windows, this will not raise timeout errors.
    """
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Operation exceeded {seconds} second timeout")
    
    # Only set alarm on Unix-like systems
    if hasattr(signal, 'SIGALRM'):
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(seconds)
        try:
            yield
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
    else:
        # On Windows, just yield without timeout
        logger.warning("Timeout protection not available on this platform")
        yield


# ============================================================================
# SymPy Lazy Loading
# ============================================================================

def _get_sympy():
    """
    Lazy load SymPy only when needed.
    
    Returns:
        SymPy module reference
        
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
# Validation
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
        r'__\w+__',  # dunder methods
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
# Canonical Path and Import
# ============================================================================

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

def _fallback_evaluate_expression(
    expr_str: str,
    simplification: SimplificationLevel = None
) -> str:
    """
    Fallback implementation for expression evaluation using SymPy.
    
    Args:
        expr_str: String representation of mathematical expression
        simplification: Level of simplification to apply
    
    Returns:
        Simplified expression as string
        
    Raises:
        ExpressionError: If expression evaluation fails
        TimeoutError: If evaluation exceeds timeout
    """
    if simplification is None:
        simplification = _config.default_simplification
    
    try:
        sp = _get_sympy()
        
        with timeout(_config.timeout_seconds):
            expr = sp.sympify(expr_str)
            
            # Apply appropriate simplification
            if simplification == SimplificationLevel.NONE:
                simplified = expr
            elif simplification == SimplificationLevel.BASIC:
                simplified = sp.simplify(expr, ratio=1.0)
            elif simplification == SimplificationLevel.FULL:
                simplified = sp.simplify(expr)
            elif simplification == SimplificationLevel.AGGRESSIVE:
                simplified = sp.simplify(expr, ratio=2.0)
            else:
                simplified = sp.simplify(expr)
            
            return str(simplified)
        
    except sp.SympifyError as e:
        logger.error(f"Invalid expression syntax: {e}")
        raise ExpressionError(f"Invalid expression syntax: {e}") from e
    except TimeoutError as e:
        logger.error(f"Expression evaluation timed out: {e}")
        raise
    except (ValueError, TypeError, AttributeError) as e:
        logger.error(f"Expression evaluation failed: {type(e).__name__}: {e}")
        raise ExpressionError(f"Expression evaluation failed: {e}") from e


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
        List of solutions as strings
        
    Raises:
        EquationError: If equation solving fails
        TimeoutError: If solving exceeds timeout
    """
    try:
        sp = _get_sympy()
        
        with timeout(_config.timeout_seconds):
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
    except TimeoutError as e:
        logger.error(f"Equation solving timed out: {e}")
        raise
    except (ValueError, TypeError, AttributeError) as e:
        logger.error(f"Equation solving failed: {type(e).__name__}: {e}")
        raise EquationError(f"Equation solving failed: {e}") from e


# ============================================================================
# Caching Layer
# ============================================================================

@lru_cache(maxsize=128)
def _cached_evaluate_expression(expr_str: str, simplification_value: str) -> str:
    """Cached version of expression evaluation."""
    simplification = SimplificationLevel(simplification_value)
    if _canonical_eval is not None:
        return _canonical_eval(expr_str)
    return _fallback_evaluate_expression(expr_str, simplification)


@lru_cache(maxsize=128)
def _cached_solve_equation(equation_str: str, symbol_str: str) -> Tuple[str, ...]:
    """Cached version of equation solving. Returns tuple for hashability."""
    if _canonical_solve is not None:
        result = _canonical_solve(equation_str, symbol_str)
    else:
        result = _fallback_solve_equation(equation_str, symbol_str)
    return tuple(result)  # Convert list to tuple for caching


# ============================================================================
# Public API Functions
# ============================================================================

def evaluate_expression(
    expr_str: str,
    use_cache: bool = True,
    simplification: SimplificationLevel = None
) -> str:
    """
    Evaluate and simplify a mathematical expression.
    
    Attempts to use canonical implementation if available, otherwise
    uses fallback SymPy implementation.
    
    Args:
        expr_str: String representation of mathematical expression
                 (e.g., "x**2 + 2*x + 1", "sin(x) + cos(x)")
        use_cache: Whether to use cached results (default: True)
        simplification: Level of simplification to apply
    
    Returns:
        Simplified expression as string
        
    Raises:
        ValueError: If expr_str is empty or invalid
        ValidationError: If expression contains dangerous patterns
        ExpressionError: If expression evaluation fails
        TimeoutError: If evaluation exceeds timeout limit
        ImportError: If SymPy is not available (fallback mode only)
        RateLimitError: If rate limit is exceeded
        
    Examples:
        >>> evaluate_expression("x**2 + 2*x + 1")
        '(x + 1)**2'
        
        >>> evaluate_expression("sin(x)**2 + cos(x)**2")
        '1'
        
    Note:
        - Results are cached by default for better performance
        - Maximum expression length is 10000 characters
        - Evaluation timeout is 30 seconds by default
    """
    start_time = time.time()
    
    # Input validation
    if not expr_str or not isinstance(expr_str, str):
        raise ValueError("Expression string must be a non-empty string")
    
    # Rate limiting check
    if _config.enable_rate_limiting and not _rate_limiter.allow():
        raise RateLimitError("Rate limit exceeded. Try again later.")
    
    # Security validation
    _validate_expression(expr_str)
    
    if simplification is None:
        simplification = _config.default_simplification
    
    try:
        if use_cache:
            result = _cached_evaluate_expression(expr_str, simplification.value)
        else:
            if _canonical_eval is not None:
                result = _canonical_eval(expr_str)
            else:
                result = _fallback_evaluate_expression(expr_str, simplification)
        
        # Structured logging
        elapsed = time.time() - start_time
        logger.info(
            "Expression evaluated",
            extra={
                'expr_length': len(expr_str),
                'used_cache': use_cache,
                'elapsed_ms': elapsed * 1000,
                'impl_type': 'canonical' if _canonical_eval else 'fallback'
            }
        )
        
        return result
        
    except Exception as e:
        logger.error(
            "Expression evaluation failed",
            extra={
                'expr_length': len(expr_str),
                'error_type': type(e).__name__
            },
            exc_info=True
        )
        raise


def solve_equation(
    equation_str: str, 
    symbol_str: str = "x",
    use_cache: bool = True
) -> List[str]:
    """
    Solve an equation for a given symbol.
    
    Attempts to use canonical implementation if available, otherwise
    uses fallback SymPy implementation.
    
    Args:
        equation_str: String representation of equation to solve
                     (e.g., "x**2 - 4", "2*x + 3 - 7")
        symbol_str: Symbol to solve for (default: "x")
        use_cache: Whether to use cached results (default: True)
    
    Returns:
        List of solutions as strings
        
    Raises:
        ValueError: If equation_str is empty or symbol_str is invalid
        ValidationError: If expression contains dangerous patterns
        EquationError: If equation solving fails
        TimeoutError: If solving exceeds timeout limit
        ImportError: If SymPy is not available (fallback mode only)
        RateLimitError: If rate limit is exceeded
        
    Examples:
        >>> solve_equation("x**2 - 4")
        ['-2', '2']
        
        >>> solve_equation("2*x + 3", "x")
        ['-3/2']
        
    Note:
        - Results are cached by default for better performance
        - Maximum equation length is 10000 characters
        - Solving timeout is 30 seconds by default
    """
    start_time = time.time()
    
    # Input validation
    if not equation_str or not isinstance(equation_str, str):
        raise ValueError("Equation string must be a non-empty string")
    
    if not symbol_str or not isinstance(symbol_str, str):
        raise ValueError("Symbol must be a non-empty string")
    
    # Rate limiting check
    if _config.enable_rate_limiting and not _rate_limiter.allow():
        raise RateLimitError("Rate limit exceeded. Try again later.")
    
    # Security validation
    _validate_expression(equation_str)
    
    try:
        if use_cache:
            result = list(_cached_solve_equation(equation_str, symbol_str))
        else:
            if _canonical_solve is not None:
                result = _canonical_solve(equation_str, symbol_str)
            else:
                result = _fallback_solve_equation(equation_str, symbol_str)
        
        # Structured logging
        elapsed = time.time() - start_time
        logger.info(
            "Equation solved",
            extra={
                'equation_length': len(equation_str),
                'symbol': symbol_str,
                'num_solutions': len(result),
                'used_cache': use_cache,
                'elapsed_ms': elapsed * 1000,
                'impl_type': 'canonical' if _canonical_solve else 'fallback'
            }
        )
        
        return result
        
    except Exception as e:
        logger.error(
            "Equation solving failed",
            extra={
                'equation_length': len(equation_str),
                'symbol': symbol_str,
                'error_type': type(e).__name__
            },
            exc_info=True
        )
        raise


# ============================================================================
# Batch Processing
# ============================================================================

def evaluate_expressions_batch(
    expressions: List[str],
    max_workers: int = 4,
    use_cache: bool = True
) -> List[str]:
    """
    Evaluate multiple expressions in parallel.
    
    Args:
        expressions: List of expression strings
        max_workers: Maximum number of parallel workers
        use_cache: Whether to use caching for each expression
        
    Returns:
        List of simplified expressions (same order as input)
        
    Example:
        >>> expressions = ["x**2 + 1", "sin(x) + cos(x)", "y**3 - 8"]
        >>> evaluate_expressions_batch(expressions)
        ['x**2 + 1', 'sin(x) + cos(x)', '(y - 2)*(y**2 + 2*y + 4)']
    """
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        return list(executor.map(
            lambda expr: evaluate_expression(expr, use_cache=use_cache),
            expressions
        ))


def solve_equations_batch(
    equations: List[Tuple[str, str]],
    max_workers: int = 4,
    use_cache: bool = True
) -> List[List[str]]:
    """
    Solve multiple equations in parallel.
    
    Args:
        equations: List of (equation_str, symbol_str) tuples
        max_workers: Maximum number of parallel workers
        use_cache: Whether to use caching for each equation
        
    Returns:
        List of solution lists (same order as input)
        
    Example:
        >>> equations = [("x**2 - 4", "x"), ("y + 5", "y")]
        >>> solve_equations_batch(equations)
        [['-2', '2'], ['-5']]
    """
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        return list(executor.map(
            lambda eq: solve_equation(eq[0], eq[1], use_cache=use_cache),
            equations
        ))


# ============================================================================
# Testing and Utilities
# ============================================================================

def _reset_module_state():
    """
    Reset module state for testing purposes.
    
    This function clears all caches and resets configuration to defaults.
    Should only be used in testing scenarios.
    """
    global _canonical_eval, _canonical_solve, _sympy, _config, _rate_limiter
    _canonical_eval = None
    _canonical_solve = None
    _sympy = None
    _config = MathEngineConfig()
    _rate_limiter = RateLimiter(
        max_calls=_config.rate_limit_max_calls,
        time_window=_config.rate_limit_time_window
    )
    _cached_evaluate_expression.cache_clear()
    _cached_solve_equation.cache_clear()


def get_cache_info() -> dict:
    """
    Get cache statistics.
    
    Returns:
        Dictionary with cache information for both functions
    """
    return {
        'evaluate_expression': {
            'hits': _cached_evaluate_expression.cache_info().hits,
            'misses': _cached_evaluate_expression.cache_info().misses,
            'size': _cached_evaluate_expression.cache_info().currsize,
            'maxsize': _cached_evaluate_expression.cache_info().maxsize
        },
        'solve_equation': {
            'hits': _cached_solve_equation.cache_info().hits,
            'misses': _cached_solve_equation.cache_info().misses,
            'size': _cached_solve_equation.cache_info().currsize,
            'maxsize': _cached_solve_equation.cache_info().maxsize
        }
    }


def clear_cache():
    """Clear all cached results."""
    _cached_evaluate_expression.cache_clear()
    _cached_solve_equation.cache_clear()
    logger.info("Cache cleared")


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    # Main functions
    'evaluate_expression',
    'solve_equation',
    # Batch operations
    'evaluate_expressions_batch',
    'solve_equations_batch',
    # Configuration
    'configure',
    'get_config',
    'MathEngineConfig',
    'SimplificationLevel',
    # Validation
    'validate_expression',
    # Cache management
    'get_cache_info',
    'clear_cache',
    # Exceptions
    'MathEngineError',
    'ExpressionError',
    'EquationError',
    'ValidationError',
    'TimeoutError',
    'RateLimitError',
    # Metadata
    '__version__'
]

# Only expose testing utilities in debug mode
if __debug__:
    __all__.append('_reset_module_state')


# ============================================================================
# Module Initialization
# ============================================================================

# Module initialization logging
if _canonical_eval is not None:
    logger.info(
        f"Math Engine v{__version__} initialized with canonical implementations"
    )
else:
    logger.info(
        f"Math Engine v{__version__} initialized with fallback implementations"
    )
