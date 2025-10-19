# FB-QENGINE-001: Subproject 1 – Fermion Parity-Based Qubit Schema
"""
Fermion Parity-Based Qubit Implementation

This module implements a quantum computing qubit based on fermion parity,
which uses topological braiding of quasiparticles for quantum operations.
"""

from enum import IntEnum
from typing import List, Optional


class ParityState(IntEnum):
    """Enumeration for fermion parity states."""
    EVEN = 0
    ODD = 1


class QuasiparticleError(Exception):
    """Custom exception for quasiparticle-related errors."""
    pass


class ParityError(Exception):
    """Custom exception for parity-related errors."""
    pass


class FermionParityQubit:
    """
    A qubit implementation based on fermion parity states.
    
    This class represents a quantum bit using fermion parity, where quantum
    operations are performed through topological braiding of quasiparticles.
    The qubit state is encoded in the parity (even=0, odd=1) of fermion modes.
    
    Attributes:
        parity (int): Current parity state (0 for even, 1 for odd)
        _measurement_count (int): Number of times the qubit has been measured
        _braid_count (int): Number of braiding operations performed
    
    Example:
        >>> qubit = FermionParityQubit(initial_parity=0)
        >>> qubit.braid(external_quasiparticle=1)
        >>> print(qubit.measure())
        1
    """
    
    def __init__(self, initial_parity: int = 0) -> None:
        """
        Initialize a fermion parity qubit.
        
        Args:
            initial_parity: Initial parity state (0 for even, 1 for odd).
                           Default is 0 (even parity).
        
        Raises:
            ParityError: If initial_parity is not 0 or 1.
        """
        if initial_parity not in (0, 1):
            raise ParityError(
                f"Parity must be 0 (even) or 1 (odd), got {initial_parity}"
            )
        
        self._parity: int = initial_parity
        self._measurement_count: int = 0
        self._braid_count: int = 0
    
    @property
    def parity(self) -> int:
        """
        Get the current parity state.
        
        Returns:
            int: Current parity (0 for even, 1 for odd)
        """
        return self._parity
    
    @property
    def measurement_count(self) -> int:
        """
        Get the number of measurements performed on this qubit.
        
        Returns:
            int: Number of measurement operations
        """
        return self._measurement_count
    
    @property
    def braid_count(self) -> int:
        """
        Get the number of braiding operations performed on this qubit.
        
        Returns:
            int: Number of braid operations
        """
        return self._braid_count
    
    def braid(self, external_quasiparticle: int) -> None:
        """
        Perform a topological braiding operation with an external quasiparticle.
        
        This operation flips the parity state through braiding with a single
        e/4 charge quasiparticle. The braiding is a non-Abelian operation that
        changes the fermion parity.
        
        Args:
            external_quasiparticle: Number of e/4 quasiparticles (must be 1)
        
        Raises:
            QuasiparticleError: If external_quasiparticle is not exactly 1
            TypeError: If external_quasiparticle is not an integer
        """
        if not isinstance(external_quasiparticle, int):
            raise TypeError(
                f"external_quasiparticle must be an integer, "
                f"got {type(external_quasiparticle).__name__}"
            )
        
        if external_quasiparticle != 1:
            raise QuasiparticleError(
                f"Only one e/4 quasiparticle can braid at a time, "
                f"got {external_quasiparticle}"
            )
        
        # XOR operation flips the parity bit
        self._parity ^= 1
        self._braid_count += 1
    
    def measure(self) -> int:
        """
        Measure the current parity state of the qubit.
        
        In quantum computing, measurement collapses the wavefunction. For this
        parity-based implementation, measurement returns the deterministic
        parity state.
        
        Returns:
            int: The current parity state (0 for even, 1 for odd)
        """
        self._measurement_count += 1
        return self._parity
    
    def get_state_vector(self) -> List[int]:
        """
        Get the state vector representation of the qubit.
        
        Returns a simplified state vector where:
        - [+1] represents even parity (ground state)
        - [-1] represents odd parity (excited state)
        
        Returns:
            List[int]: State vector as a single-element list containing +1 or -1
        """
        return [+1] if self._parity == 0 else [-1]
    
    def reset(self, parity: int = 0) -> None:
        """
        Reset the qubit to a specified parity state.
        
        Args:
            parity: Target parity state (0 for even, 1 for odd). Default is 0.
        
        Raises:
            ParityError: If parity is not 0 or 1.
        """
        if parity not in (0, 1):
            raise ParityError(
                f"Parity must be 0 (even) or 1 (odd), got {parity}"
            )
        self._parity = parity
    
    def get_statistics(self) -> dict:
        """
        Get statistics about operations performed on this qubit.
        
        Returns:
            dict: Dictionary containing measurement and braid operation counts
        """
        return {
            'parity': self._parity,
            'measurements': self._measurement_count,
            'braids': self._braid_count
        }
    
    def __repr__(self) -> str:
        """
        Return a developer-friendly string representation.
        
        Returns:
            str: String representation for debugging
        """
        return (
            f"FermionParityQubit(parity={self._parity}, "
            f"measurements={self._measurement_count}, "
            f"braids={self._braid_count})"
        )
    
    def __str__(self) -> str:
        """
        Return a user-friendly string representation.
        
        Returns:
            str: Human-readable string representation
        """
        parity_str = "EVEN" if self._parity == 0 else "ODD"
        state_vector = self.get_state_vector()[0]
        return f"FermionParityQubit[{parity_str}, state={state_vector:+d}]"
    
    def __eq__(self, other: object) -> bool:
        """
        Check equality based on parity state.
        
        Args:
            other: Object to compare with
        
        Returns:
            bool: True if both qubits have the same parity state
        """
        if not isinstance(other, FermionParityQubit):
            return NotImplemented
        return self._parity == other._parity
