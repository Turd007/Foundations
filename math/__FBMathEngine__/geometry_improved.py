"""
Geometry constructor and resonance shape utilities.

This module provides utilities for geometric computations and resonance shape
analysis, supporting various vector representations and geometric primitives.
"""

from typing import Union, List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
import math


class VectorType(Enum):
    """Enumeration of supported vector types."""
    CARTESIAN_2D = "cartesian_2d"
    CARTESIAN_3D = "cartesian_3d"
    POLAR = "polar"
    SPHERICAL = "spherical"
    CYLINDRICAL = "cylindrical"


@dataclass
class GeometryConfig:
    """Configuration for geometry generation."""
    precision: int = 6
    normalize: bool = False
    validate_input: bool = True
    output_format: str = "dict"


class GeometryError(Exception):
    """Custom exception for geometry-related errors."""
    pass


class Vector:
    """
    Represents a mathematical vector with various coordinate systems.
    
    Attributes:
        components: The vector components
        vector_type: The coordinate system type
    """
    
    def __init__(
        self,
        components: Union[List[float], Tuple[float, ...], 'Vector'],
        vector_type: VectorType = VectorType.CARTESIAN_3D
    ):
        """
        Initialize a Vector.
        
        Args:
            components: Vector components (list, tuple, or Vector)
            vector_type: The coordinate system type
            
        Raises:
            GeometryError: If components are invalid
        """
        if isinstance(components, Vector):
            self.components = components.components
            self.vector_type = components.vector_type
        else:
            self._validate_components(components, vector_type)
            self.components = tuple(float(c) for c in components)
            self.vector_type = vector_type
    
    @staticmethod
    def _validate_components(
        components: Union[List[float], Tuple[float, ...]],
        vector_type: VectorType
    ) -> None:
        """
        Validate vector components based on type.
        
        Args:
            components: Vector components to validate
            vector_type: Expected vector type
            
        Raises:
            GeometryError: If validation fails
        """
        if not components:
            raise GeometryError("Vector components cannot be empty")
        
        expected_dims = {
            VectorType.CARTESIAN_2D: 2,
            VectorType.CARTESIAN_3D: 3,
            VectorType.POLAR: 2,
            VectorType.SPHERICAL: 3,
            VectorType.CYLINDRICAL: 3
        }
        
        expected = expected_dims.get(vector_type)
        if expected and len(components) != expected:
            raise GeometryError(
                f"{vector_type.value} requires {expected} components, "
                f"got {len(components)}"
            )
        
        try:
            [float(c) for c in components]
        except (TypeError, ValueError) as e:
            raise GeometryError(f"Invalid numeric components: {e}")
    
    def magnitude(self) -> float:
        """
        Calculate the magnitude (length) of the vector.
        
        Returns:
            The magnitude of the vector
        """
        return math.sqrt(sum(c ** 2 for c in self.components))
    
    def normalize(self) -> 'Vector':
        """
        Return a normalized (unit) vector.
        
        Returns:
            A new normalized Vector
            
        Raises:
            GeometryError: If vector has zero magnitude
        """
        mag = self.magnitude()
        if mag == 0:
            raise GeometryError("Cannot normalize zero vector")
        
        normalized = tuple(c / mag for c in self.components)
        return Vector(normalized, self.vector_type)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert vector to dictionary representation.
        
        Returns:
            Dictionary with vector data
        """
        return {
            "type": self.vector_type.value,
            "components": list(self.components),
            "magnitude": self.magnitude(),
            "dimension": len(self.components)
        }
    
    def __repr__(self) -> str:
        """String representation of the vector."""
        return (f"Vector(components={self.components}, "
                f"type={self.vector_type.value})")
    
    def __str__(self) -> str:
        """User-friendly string representation."""
        components_str = ", ".join(f"{c:.4f}" for c in self.components)
        return f"{self.vector_type.value}({components_str})"


class GeometryGenerator:
    """
    Generates geometric structures from vector inputs.
    
    This class provides methods for creating various geometric primitives
    and resonance shapes based on input vectors.
    """
    
    def __init__(self, config: Optional[GeometryConfig] = None):
        """
        Initialize the geometry generator.
        
        Args:
            config: Configuration for geometry generation
        """
        self.config = config or GeometryConfig()
    
    def generate(
        self,
        vector: Union[List[float], Tuple[float, ...], Vector, Dict[str, Any]],
        geometry_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate geometry from a vector input.
        
        Args:
            vector: Input vector (various formats supported)
            geometry_type: Optional specific geometry type to generate
            
        Returns:
            Dictionary containing geometry data
            
        Raises:
            GeometryError: If input is invalid
        """
        # Convert input to Vector object
        vec = self._parse_vector(vector)
        
        # Validate if configured
        if self.config.validate_input:
            self._validate_vector(vec)
        
        # Normalize if configured
        if self.config.normalize:
            vec = vec.normalize()
        
        # Generate geometry structure
        geometry = {
            "vector": vec.to_dict(),
            "metadata": {
                "precision": self.config.precision,
                "normalized": self.config.normalize,
                "geometry_type": geometry_type or "default"
            }
        }
        
        # Add geometry-specific computations
        if geometry_type:
            geometry.update(self._compute_geometry_specific(vec, geometry_type))
        
        return geometry
    
    def _parse_vector(
        self,
        vector: Union[List[float], Tuple[float, ...], Vector, Dict[str, Any]]
    ) -> Vector:
        """
        Parse various vector input formats.
        
        Args:
            vector: Input in various formats
            
        Returns:
            Parsed Vector object
            
        Raises:
            GeometryError: If parsing fails
        """
        if isinstance(vector, Vector):
            return vector
        
        if isinstance(vector, dict):
            components = vector.get("components", [])
            vec_type_str = vector.get("type", "cartesian_3d")
            try:
                vec_type = VectorType(vec_type_str)
            except ValueError:
                vec_type = VectorType.CARTESIAN_3D
            return Vector(components, vec_type)
        
        if isinstance(vector, (list, tuple)):
            return Vector(vector)
        
        raise GeometryError(f"Unsupported vector format: {type(vector)}")
    
    def _validate_vector(self, vector: Vector) -> None:
        """
        Validate vector for geometry generation.
        
        Args:
            vector: Vector to validate
            
        Raises:
            GeometryError: If validation fails
        """
        if not vector.components:
            raise GeometryError("Vector has no components")
        
        if any(not math.isfinite(c) for c in vector.components):
            raise GeometryError("Vector contains non-finite values")
    
    def _compute_geometry_specific(
        self,
        vector: Vector,
        geometry_type: str
    ) -> Dict[str, Any]:
        """
        Compute geometry-specific properties.
        
        Args:
            vector: Input vector
            geometry_type: Type of geometry
            
        Returns:
            Dictionary with geometry-specific data
        """
        result = {}
        
        if geometry_type == "resonance":
            result["resonance"] = self._compute_resonance(vector)
        elif geometry_type == "shape":
            result["shape"] = self._compute_shape(vector)
        elif geometry_type == "projection":
            result["projection"] = self._compute_projection(vector)
        
        return result
    
    def _compute_resonance(self, vector: Vector) -> Dict[str, Any]:
        """
        Compute resonance properties from vector.
        
        Args:
            vector: Input vector
            
        Returns:
            Resonance properties
        """
        magnitude = vector.magnitude()
        return {
            "frequency": magnitude,
            "amplitude": max(abs(c) for c in vector.components),
            "phase": math.atan2(vector.components[1], vector.components[0])
            if len(vector.components) >= 2 else 0.0
        }
    
    def _compute_shape(self, vector: Vector) -> Dict[str, Any]:
        """
        Compute shape properties from vector.
        
        Args:
            vector: Input vector
            
        Returns:
            Shape properties
        """
        return {
            "dimensionality": len(vector.components),
            "bounds": {
                "min": min(vector.components),
                "max": max(vector.components)
            },
            "centroid": sum(vector.components) / len(vector.components)
        }
    
    def _compute_projection(self, vector: Vector) -> Dict[str, Any]:
        """
        Compute projection properties.
        
        Args:
            vector: Input vector
            
        Returns:
            Projection properties
        """
        projections = {}
        
        if len(vector.components) >= 2:
            projections["xy_plane"] = math.sqrt(
                vector.components[0]**2 + vector.components[1]**2
            )
        
        if len(vector.components) >= 3:
            projections["xz_plane"] = math.sqrt(
                vector.components[0]**2 + vector.components[2]**2
            )
            projections["yz_plane"] = math.sqrt(
                vector.components[1]**2 + vector.components[2]**2
            )
        
        return projections


# Convenience function maintaining backward compatibility
def generate_geometry(
    vector: Union[List[float], Tuple[float, ...], Vector, Dict[str, Any]],
    config: Optional[GeometryConfig] = None
) -> Union[str, Dict[str, Any]]:
    """
    Generate geometry from a vector input.
    
    This is a convenience function that maintains backward compatibility
    with the original simple string output while supporting enhanced features.
    
    Args:
        vector: Input vector in various formats
        config: Optional configuration for geometry generation
        
    Returns:
        Geometry representation (string for simple use, dict for complex)
        
    Raises:
        GeometryError: If input is invalid
        
    Examples:
        >>> generate_geometry([1, 2, 3])
        'Generated geometry from vector: cartesian_3d(1.0000, 2.0000, 3.0000)'
        
        >>> config = GeometryConfig(output_format="dict")
        >>> result = generate_geometry([1, 2, 3], config)
        >>> result['vector']['magnitude']
        3.7416573867739413
    """
    try:
        generator = GeometryGenerator(config)
        result = generator.generate(vector)
        
        # Return simple string format by default for compatibility
        if not config or config.output_format == "string":
            vec = generator._parse_vector(vector)
            return f"Generated geometry from vector: {vec}"
        
        return result
        
    except Exception as e:
        # For compatibility, convert errors to GeometryError
        if not isinstance(e, GeometryError):
            raise GeometryError(f"Geometry generation failed: {e}") from e
        raise


# Module-level convenience functions
def create_vector(
    components: Union[List[float], Tuple[float, ...]],
    vector_type: VectorType = VectorType.CARTESIAN_3D
) -> Vector:
    """
    Create a vector with the specified components.
    
    Args:
        components: Vector components
        vector_type: Coordinate system type
        
    Returns:
        Created Vector object
    """
    return Vector(components, vector_type)


def vector_magnitude(components: Union[List[float], Tuple[float, ...]]) -> float:
    """
    Calculate vector magnitude.
    
    Args:
        components: Vector components
        
    Returns:
        Vector magnitude
    """
    return Vector(components).magnitude()


def normalize_vector(
    components: Union[List[float], Tuple[float, ...]]
) -> List[float]:
    """
    Normalize a vector to unit length.
    
    Args:
        components: Vector components
        
    Returns:
        Normalized vector components
    """
    return list(Vector(components).normalize().components)
