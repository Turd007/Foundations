"""
Resonance detection and validation module.

This module provides functionality to detect resonance states in signals,
which are critical for mathematical operations in the FB Math Engine.
"""

from typing import FrozenSet

# Valid resonance signal patterns
# These patterns indicate a resonance state in the mathematical engine:
# - "0+": Standard positive resonance state
# - "♡0+": Heart-resonance positive state (special quantum resonance)
RESONANCE_SIGNALS: FrozenSet[str] = frozenset(["0+", "♡0+"])


def detect_resonance(signal: str) -> bool:
    """
    Detect if a signal indicates a resonance state.
    
    Resonance states are special mathematical states in the FB Math Engine
    that indicate specific quantum or energy conditions. This function
    performs fast O(1) lookup to determine if a given signal matches
    any known resonance pattern.
    
    Args:
        signal: The signal string to check for resonance. Should be a
                string representing a state or measurement value.
    
    Returns:
        bool: True if the signal indicates a resonance state (matches
              one of the known resonance patterns), False otherwise.
    
    Examples:
        >>> detect_resonance("0+")
        True
        >>> detect_resonance("♡0+")
        True
        >>> detect_resonance("invalid")
        False
        >>> detect_resonance("0-")
        False
    
    Notes:
        - Uses frozenset for O(1) constant-time lookup performance
        - The heart symbol (♡) represents a special quantum resonance state
        - Signal matching is case-sensitive and exact (no whitespace trimming)
    """
    return signal in RESONANCE_SIGNALS


def detect_resonance_with_validation(signal: str) -> bool:
    """
    Detect resonance with input type validation.
    
    This is a stricter version of detect_resonance that validates
    the input type before checking for resonance. Use this when
    dealing with untrusted or external input sources.
    
    Args:
        signal: The signal string to check for resonance.
    
    Returns:
        bool: True if the signal indicates a resonance state, False otherwise.
    
    Raises:
        TypeError: If signal is not a string.
    
    Examples:
        >>> detect_resonance_with_validation("0+")
        True
        >>> detect_resonance_with_validation(123)
        Traceback (most recent call last):
        ...
        TypeError: Expected str for signal, got int
    """
    if not isinstance(signal, str):
        raise TypeError(f"Expected str for signal, got {type(signal).__name__}")
    return signal in RESONANCE_SIGNALS


class ResonanceDetector:
    """
    Configurable resonance detector with extensible signal patterns.
    
    This class provides a more flexible approach to resonance detection,
    allowing custom signal patterns to be configured at initialization.
    Useful for testing, custom configurations, or when resonance patterns
    need to be loaded from external sources.
    
    Attributes:
        resonance_signals: Immutable set of valid resonance signal patterns.
    
    Examples:
        >>> detector = ResonanceDetector()
        >>> detector.detect("0+")
        True
        
        >>> custom_detector = ResonanceDetector(["custom+", "special+"])
        >>> custom_detector.detect("custom+")
        True
        >>> custom_detector.detect("0+")
        False
    """
    
    def __init__(self, resonance_signals: list[str] | None = None):
        """
        Initialize the resonance detector.
        
        Args:
            resonance_signals: Optional list of custom resonance signal patterns.
                              If None, uses default patterns ["0+", "♡0+"].
        """
        if resonance_signals is None:
            resonance_signals = ["0+", "♡0+"]
        self.resonance_signals: FrozenSet[str] = frozenset(resonance_signals)
    
    def detect(self, signal: str) -> bool:
        """
        Detect if a signal indicates resonance.
        
        Args:
            signal: The signal string to check.
        
        Returns:
            bool: True if signal matches a resonance pattern, False otherwise.
        """
        return signal in self.resonance_signals
    
    def add_signal(self, signal: str) -> "ResonanceDetector":
        """
        Create a new detector with an additional resonance signal.
        
        Since resonance_signals is immutable, this returns a new instance
        with the additional signal included.
        
        Args:
            signal: New resonance signal pattern to add.
        
        Returns:
            ResonanceDetector: New instance with the added signal.
        
        Examples:
            >>> detector = ResonanceDetector()
            >>> new_detector = detector.add_signal("custom+")
            >>> new_detector.detect("custom+")
            True
        """
        new_signals = list(self.resonance_signals) + [signal]
        return ResonanceDetector(new_signals)
    
    def get_signals(self) -> FrozenSet[str]:
        """
        Get the current set of resonance signals.
        
        Returns:
            FrozenSet[str]: Immutable set of resonance signal patterns.
        """
        return self.resonance_signals
