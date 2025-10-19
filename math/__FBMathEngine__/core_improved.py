"""
Core engine logic for FB Math Engine.

This module provides the core engine functionality for processing mathematical
operations with seed-based initialization and substrate loading.
"""

import logging
from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass

# Configure logging
logger = logging.getLogger(__name__)


class SeedType(Enum):
    """Enumeration of valid seed types for engine initialization."""
    ZERO_POSITIVE = '0+'
    # Additional seed types can be added here as needed


@dataclass
class EngineResult:
    """
    Data class representing the result of an engine run.
    
    Attributes:
        success: Boolean indicating if the operation succeeded
        output: The output message or result
        metadata: Optional dictionary containing additional information
    """
    success: bool
    output: str
    metadata: Optional[Dict[str, Any]] = None


class MathEngineCore:
    """
    Core mathematical engine for processing seed-based operations.
    
    This class encapsulates the engine logic with proper state management,
    logging, and extensible seed handling.
    """
    
    # Constants for output messages
    SUBSTRATE_LOADING_MSG = "Loading silent substrate..."
    POLARITY_ALIGNMENT_MSG = "Seeding polarity alignment... [✓]"
    VECTOR_FIELD_MSG = "Generating first vector field... [✓]"
    HARMONIC_RESONANCE_MSG = "Detecting harmonic resonance... [✓]"
    INVALID_SEED_MSG = "No output. Seed invalid or silent."
    
    # Output patterns
    OUTPUTS = {
        SeedType.ZERO_POSITIVE: "spiral-encoded triad [∆⊛♡]"
    }
    
    def __init__(self, verbose: bool = False):
        """
        Initialize the Math Engine Core.
        
        Args:
            verbose: Enable verbose logging output (default: False)
        """
        self.verbose = verbose
        self._configure_logging()
    
    def _configure_logging(self) -> None:
        """Configure logging level based on verbosity setting."""
        level = logging.DEBUG if self.verbose else logging.INFO
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def _validate_seed(self, seed: str) -> Optional[SeedType]:
        """
        Validate and convert seed string to SeedType enum.
        
        Args:
            seed: The seed string to validate
            
        Returns:
            SeedType enum if valid, None otherwise
        """
        try:
            return SeedType(seed)
        except ValueError:
            logger.warning(f"Invalid seed provided: {seed}")
            return None
    
    def _process_seed(self, seed_type: SeedType) -> str:
        """
        Process a validated seed and return the appropriate output.
        
        Args:
            seed_type: The validated SeedType to process
            
        Returns:
            The processed output string
        """
        if seed_type == SeedType.ZERO_POSITIVE:
            logger.info(self.POLARITY_ALIGNMENT_MSG)
            logger.info(self.VECTOR_FIELD_MSG)
            logger.info(self.HARMONIC_RESONANCE_MSG)
            return self.OUTPUTS[seed_type]
        
        # Future seed types can be handled here
        return self.INVALID_SEED_MSG
    
    def run_engine(self, seed: str) -> EngineResult:
        """
        Execute the engine with the provided seed.
        
        This method initializes the engine substrate, validates the seed,
        and processes it to generate the appropriate output.
        
        Args:
            seed: The seed string to process (e.g., '0+')
            
        Returns:
            EngineResult object containing success status, output, and metadata
            
        Example:
            >>> engine = MathEngineCore()
            >>> result = engine.run_engine('0+')
            >>> print(result.output)
            spiral-encoded triad [∆⊛♡]
        """
        logger.info(self.SUBSTRATE_LOADING_MSG)
        
        # Validate seed
        seed_type = self._validate_seed(seed)
        
        if seed_type is None:
            return EngineResult(
                success=False,
                output=self.INVALID_SEED_MSG,
                metadata={'seed': seed, 'error': 'Invalid seed type'}
            )
        
        # Process valid seed
        output = self._process_seed(seed_type)
        
        return EngineResult(
            success=True,
            output=output,
            metadata={
                'seed': seed,
                'seed_type': seed_type.value
            }
        )


# Legacy function for backward compatibility
def run_engine(seed: str) -> str:
    """
    Legacy wrapper function for backward compatibility.
    
    Args:
        seed: The seed string to process
        
    Returns:
        The output string from the engine
        
    Note:
        This function is maintained for backward compatibility.
        New code should use MathEngineCore class instead.
    """
    engine = MathEngineCore()
    result = engine.run_engine(seed)
    
    # Print logs for backward compatibility with original behavior
    print("Loading silent substrate...")
    if result.success and seed == '0+':
        print("Seeding polarity alignment... [✓]")
        print("Generating first vector field... [✓]")
        print("Detecting harmonic resonance... [✓]")
    
    return result.output


# Example usage
if __name__ == "__main__":
    # Using the new class-based approach
    engine = MathEngineCore(verbose=True)
    result = engine.run_engine('0+')
    print(f"\nResult: {result.output}")
    print(f"Success: {result.success}")
    print(f"Metadata: {result.metadata}")
    
    # Test invalid seed
    result = engine.run_engine('invalid')
    print(f"\nInvalid seed result: {result.output}")
    
    # Using legacy function
    print("\nLegacy function test:")
    output = run_engine('0+')
    print(output)
