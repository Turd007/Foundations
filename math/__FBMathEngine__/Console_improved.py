"""
Console.py - Interactive demonstration of FB Math Engine capabilities

This module provides examples and a demonstration script for using the
fb_math_engine_improved_v2 module to solve equations and evaluate expressions.

Usage:
    python Console_improved.py
    
Example:
    >>> from Console_improved import demo_solve_equation
    >>> demo_solve_equation("x**2 - 9")
    Solutions for 'x**2 - 9': ['-3', '3']
"""

from typing import List, Optional
import sys
import logging

from fb_math_engine_improved_v2 import (
    solve_equation,
    evaluate_expression,
    validate_expression,
    MathEngineError,
    EquationError,
    ExpressionError,
    ValidationError,
    TimeoutError
)

# Configure logging for console output
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


def demo_solve_equation(equation: str, symbol: str = "x") -> Optional[List[str]]:
    """
    Demonstrate equation solving with proper error handling.
    
    Args:
        equation: String representation of equation to solve
        symbol: Symbol to solve for (default: "x")
        
    Returns:
        List of solutions if successful, None if error occurs
        
    Example:
        >>> demo_solve_equation("x**2 - 4")
        Solutions for 'x**2 - 4': ['-2', '2']
    """
    try:
        # Solve the equation
        solutions = solve_equation(equation, symbol)
        
        # Display results
        if solutions:
            print(f"Solutions for '{equation}': {solutions}")
        else:
            print(f"No solutions found for '{equation}'")
        
        return solutions
        
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        return None
    except EquationError as e:
        logger.error(f"Equation solving error: {e}")
        return None
    except TimeoutError as e:
        logger.error(f"Operation timed out: {e}")
        return None
    except MathEngineError as e:
        logger.error(f"Math engine error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error: {type(e).__name__}: {e}")
        return None


def demo_evaluate_expression(expr: str) -> Optional[str]:
    """
    Demonstrate expression evaluation with proper error handling.
    
    Args:
        expr: String representation of expression to evaluate
        
    Returns:
        Simplified expression if successful, None if error occurs
        
    Example:
        >>> demo_evaluate_expression("x**2 + 2*x + 1")
        'x**2 + 2*x + 1' simplified to: '(x + 1)**2'
    """
    try:
        # Evaluate the expression
        result = evaluate_expression(expr)
        
        # Display results
        print(f"'{expr}' simplified to: '{result}'")
        
        return result
        
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        return None
    except ExpressionError as e:
        logger.error(f"Expression evaluation error: {e}")
        return None
    except TimeoutError as e:
        logger.error(f"Operation timed out: {e}")
        return None
    except MathEngineError as e:
        logger.error(f"Math engine error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error: {type(e).__name__}: {e}")
        return None


def demo_validate_input(expr: str) -> bool:
    """
    Demonstrate input validation before processing.
    
    Args:
        expr: Expression to validate
        
    Returns:
        True if valid, False otherwise
    """
    is_valid, error_msg = validate_expression(expr)
    
    if is_valid:
        print(f"✓ Expression '{expr}' is valid")
    else:
        print(f"✗ Expression '{expr}' is invalid: {error_msg}")
    
    return is_valid


def run_demos() -> None:
    """
    Run comprehensive demonstrations of math engine capabilities.
    """
    print("=" * 70)
    print("FB Math Engine - Interactive Console Demonstration")
    print("=" * 70)
    print()
    
    # Demo 1: Basic equation solving
    print("Demo 1: Solving quadratic equations")
    print("-" * 70)
    demo_solve_equation("x**2 - 4")
    demo_solve_equation("x**2 - 9")
    demo_solve_equation("x**2 + 5*x + 6")
    print()
    
    # Demo 2: Solving with different symbols
    print("Demo 2: Solving for different variables")
    print("-" * 70)
    demo_solve_equation("y**2 - 16", symbol="y")
    demo_solve_equation("2*z + 3 - 7", symbol="z")
    print()
    
    # Demo 3: Expression simplification
    print("Demo 3: Expression simplification")
    print("-" * 70)
    demo_evaluate_expression("x**2 + 2*x + 1")
    demo_evaluate_expression("sin(x)**2 + cos(x)**2")
    demo_evaluate_expression("(x + 1)*(x - 1)")
    print()
    
    # Demo 4: Input validation
    print("Demo 4: Input validation")
    print("-" * 70)
    demo_validate_input("x**2 + 1")
    demo_validate_input("2*x + 3")
    print()
    
    # Demo 5: Error handling
    print("Demo 5: Handling invalid input")
    print("-" * 70)
    demo_solve_equation("invalid_syntax^^^")
    demo_evaluate_expression("completely broken ((((")
    print()
    
    print("=" * 70)
    print("Demonstration complete!")
    print("=" * 70)


def interactive_mode() -> None:
    """
    Run interactive console mode for user input.
    """
    print("\n" + "=" * 70)
    print("Interactive Mode - Enter equations to solve or expressions to evaluate")
    print("Commands: 'solve <equation>' or 'eval <expression>' or 'quit'")
    print("=" * 70)
    print()
    
    while True:
        try:
            user_input = input(">>> ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ('quit', 'exit', 'q'):
                print("Exiting interactive mode.")
                break
            
            if user_input.lower().startswith('solve '):
                equation = user_input[6:].strip()
                demo_solve_equation(equation)
            
            elif user_input.lower().startswith('eval '):
                expression = user_input[5:].strip()
                demo_evaluate_expression(expression)
            
            elif user_input.lower().startswith('validate '):
                expression = user_input[9:].strip()
                demo_validate_input(expression)
            
            else:
                # Default to solving as equation
                demo_solve_equation(user_input)
            
            print()
            
        except KeyboardInterrupt:
            print("\nInterrupted. Exiting interactive mode.")
            break
        except EOFError:
            print("\nEOF received. Exiting interactive mode.")
            break


def main() -> int:
    """
    Main entry point for console demonstration.
    
    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        # Check for command line arguments
        if len(sys.argv) > 1:
            if sys.argv[1] in ('-h', '--help'):
                print(__doc__)
                return 0
            elif sys.argv[1] in ('-i', '--interactive'):
                interactive_mode()
                return 0
            else:
                # Treat argument as equation to solve
                equation = ' '.join(sys.argv[1:])
                demo_solve_equation(equation)
                return 0
        
        # Run standard demonstrations
        run_demos()
        
        # Optionally enter interactive mode
        response = input("\nEnter interactive mode? (y/n): ").strip().lower()
        if response in ('y', 'yes'):
            interactive_mode()
        
        return 0
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
