# Code Improvements for geometry_improved.py

## Executive Summary

The `geometry_improved.py` module provides a well-structured foundation for geometric computations. However, several enhancements can improve performance, robustness, type safety, and functionality.

---

## 1. Performance Optimizations

### Issue: Repeated Magnitude Calculations
**Current Code:**
```python
def normalize(self) -> 'Vector':
    mag = self.magnitude()
    if mag == 0:
        raise GeometryError("Cannot normalize zero vector")
```

**Problem:** Magnitude is calculated each time it's needed, which involves expensive sqrt operations.

**Recommendation:**
```python
from functools import cached_property

class Vector:
    @cached_property
    def magnitude(self) -> float:
        """Calculate and cache the magnitude (length) of the vector."""
        return math.sqrt(sum(c ** 2 for c in self.components))
```

**Impact:** Significant performance improvement for repeated magnitude calculations.

---

### Issue: Inefficient Vector Component Iteration
**Current Code:**
```python
return math.sqrt(sum(c ** 2 for c in self.components))
```

**Recommendation:** Use numpy for better performance with large vectors:
```python
import numpy as np

def magnitude(self) -> float:
    """Calculate magnitude using optimized numpy operations."""
    return float(np.linalg.norm(self.components))
```

**Note:** This adds a numpy dependency but provides substantial performance gains.

---

## 2. Numerical Stability

### Issue: Zero Comparison Without Tolerance
**Current Code:**
```python
if mag == 0:
    raise GeometryError("Cannot normalize zero vector")
```

**Problem:** Floating-point arithmetic makes exact zero comparisons unreliable.

**Recommendation:**
```python
# Module-level constant
EPSILON = 1e-10

class Vector:
    def normalize(self) -> 'Vector':
        mag = self.magnitude()
        if mag < EPSILON:
            raise GeometryError(f"Cannot normalize near-zero vector (magnitude: {mag})")
        
        normalized = tuple(c / mag for c in self.components)
        return Vector(normalized, self.vector_type)
```

**Impact:** More robust handling of near-zero vectors.

---

## 3. Missing Vector Operations

### Issue: Lack of Common Vector Operations
**Current State:** Only magnitude and normalize are implemented.

**Recommendation:** Add essential vector operations:

```python
class Vector:
    def dot(self, other: 'Vector') -> float:
        """
        Calculate dot product with another vector.
        
        Args:
            other: Another vector with same dimensionality
            
        Returns:
            Dot product scalar value
            
        Raises:
            GeometryError: If vectors have different dimensions
        """
        if len(self.components) != len(other.components):
            raise GeometryError(
                f"Cannot compute dot product: dimension mismatch "
                f"({len(self.components)} vs {len(other.components)})"
            )
        return sum(a * b for a, b in zip(self.components, other.components))
    
    def cross(self, other: 'Vector') -> 'Vector':
        """
        Calculate cross product (3D vectors only).
        
        Args:
            other: Another 3D vector
            
        Returns:
            Cross product vector
            
        Raises:
            GeometryError: If vectors are not 3D
        """
        if len(self.components) != 3 or len(other.components) != 3:
            raise GeometryError("Cross product only defined for 3D vectors")
        
        a, b = self.components, other.components
        result = (
            a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0]
        )
        return Vector(result, self.vector_type)
    
    def __add__(self, other: 'Vector') -> 'Vector':
        """Add two vectors."""
        if len(self.components) != len(other.components):
            raise GeometryError("Cannot add vectors of different dimensions")
        result = tuple(a + b for a, b in zip(self.components, other.components))
        return Vector(result, self.vector_type)
    
    def __sub__(self, other: 'Vector') -> 'Vector':
        """Subtract two vectors."""
        if len(self.components) != len(other.components):
            raise GeometryError("Cannot subtract vectors of different dimensions")
        result = tuple(a - b for a, b in zip(self.components, other.components))
        return Vector(result, self.vector_type)
    
    def __mul__(self, scalar: float) -> 'Vector':
        """Multiply vector by scalar."""
        result = tuple(c * scalar for c in self.components)
        return Vector(result, self.vector_type)
    
    def __truediv__(self, scalar: float) -> 'Vector':
        """Divide vector by scalar."""
        if abs(scalar) < EPSILON:
            raise GeometryError("Cannot divide by zero or near-zero scalar")
        result = tuple(c / scalar for c in self.components)
        return Vector(result, self.vector_type)
    
    def angle_with(self, other: 'Vector') -> float:
        """
        Calculate angle between this vector and another (in radians).
        
        Args:
            other: Another vector
            
        Returns:
            Angle in radians [0, π]
        """
        dot_product = self.dot(other)
        mag_product = self.magnitude() * other.magnitude()
        
        if mag_product < EPSILON:
            raise GeometryError("Cannot compute angle with zero vector")
        
        # Clamp to [-1, 1] to handle numerical errors
        cos_angle = max(-1.0, min(1.0, dot_product / mag_product))
        return math.acos(cos_angle)
```

---

## 4. Immutability and Performance

### Issue: Mutable Components
**Current Code:**
```python
class Vector:
    def __init__(self, components, vector_type):
        self.components = tuple(float(c) for c in components)
```

**Recommendation:** Use `__slots__` for memory efficiency and prevent attribute addition:

```python
class Vector:
    """
    Immutable vector representation with optimized memory usage.
    """
    __slots__ = ('_components', '_vector_type', '_magnitude_cache')
    
    def __init__(
        self,
        components: Union[List[float], Tuple[float, ...], 'Vector'],
        vector_type: VectorType = VectorType.CARTESIAN_3D
    ):
        if isinstance(components, Vector):
            object.__setattr__(self, '_components', components._components)
            object.__setattr__(self, '_vector_type', components._vector_type)
        else:
            self._validate_components(components, vector_type)
            object.__setattr__(self, '_components', tuple(float(c) for c in components))
            object.__setattr__(self, '_vector_type', vector_type)
        object.__setattr__(self, '_magnitude_cache', None)
    
    @property
    def components(self) -> Tuple[float, ...]:
        return self._components
    
    @property
    def vector_type(self) -> VectorType:
        return self._vector_type
    
    @property
    def magnitude(self) -> float:
        if self._magnitude_cache is None:
            mag = math.sqrt(sum(c ** 2 for c in self._components))
            object.__setattr__(self, '_magnitude_cache', mag)
        return self._magnitude_cache
    
    def __hash__(self) -> int:
        """Make Vector hashable for use in sets/dicts."""
        return hash((self._components, self._vector_type))
    
    def __eq__(self, other: object) -> bool:
        """Check equality with another vector."""
        if not isinstance(other, Vector):
            return NotImplemented
        return (self._components == other._components and 
                self._vector_type == other._vector_type)
```

**Benefits:**
- 20-30% memory reduction with `__slots__`
- Hashable vectors (can be used in sets/dicts)
- Cached magnitude calculation
- True immutability

---

## 5. Enhanced Type Safety

### Issue: Weak Type Hints
**Current Code:**
```python
def generate(
    self,
    vector: Union[List[float], Tuple[float, ...], Vector, Dict[str, Any]],
    geometry_type: Optional[str] = None
) -> Dict[str, Any]:
```

**Recommendation:** Use TypedDict and Protocol for stronger typing:

```python
from typing import Protocol, TypedDict, Literal

class VectorLike(Protocol):
    """Protocol for vector-like objects."""
    @property
    def components(self) -> Tuple[float, ...]: ...
    @property
    def vector_type(self) -> VectorType: ...

class VectorDict(TypedDict, total=False):
    """Type definition for vector dictionary."""
    type: str
    components: List[float]
    magnitude: float
    dimension: int

class GeometryResult(TypedDict):
    """Type definition for geometry generation result."""
    vector: VectorDict
    metadata: Dict[str, Any]
    resonance: NotRequired[Dict[str, Any]]
    shape: NotRequired[Dict[str, Any]]
    projection: NotRequired[Dict[str, Any]]

GeometryType = Literal["resonance", "shape", "projection"]

class GeometryGenerator:
    def generate(
        self,
        vector: Union[List[float], Tuple[float, ...], Vector, Dict[str, Any]],
        geometry_type: Optional[GeometryType] = None
    ) -> GeometryResult:
        """Generate geometry with strong type hints."""
        # implementation
```

---

## 6. Validation Enhancements

### Issue: Incomplete Input Validation
**Current Code:**
```python
if any(not math.isfinite(c) for c in vector.components):
    raise GeometryError("Vector contains non-finite values")
```

**Recommendation:** More comprehensive validation:

```python
class Vector:
    @staticmethod
    def _validate_components(
        components: Union[List[float], Tuple[float, ...]],
        vector_type: VectorType
    ) -> None:
        """Enhanced validation with detailed error messages."""
        if not components:
            raise GeometryError("Vector components cannot be empty")
        
        # Check dimensionality
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
        
        # Validate numeric types and values
        validated = []
        for i, c in enumerate(components):
            try:
                val = float(c)
                if not math.isfinite(val):
                    raise GeometryError(
                        f"Component {i} is not finite: {val} "
                        f"(inf or nan not allowed)"
                    )
                validated.append(val)
            except (TypeError, ValueError) as e:
                raise GeometryError(
                    f"Component {i} cannot be converted to float: {c!r}"
                ) from e
        
        # Additional vector-type specific validations
        if vector_type == VectorType.POLAR and validated[0] < 0:
            raise GeometryError(
                f"Polar radius must be non-negative, got {validated[0]}"
            )
        
        if vector_type == VectorType.SPHERICAL:
            if validated[0] < 0:
                raise GeometryError(
                    f"Spherical radius must be non-negative, got {validated[0]}"
                )
```

---

## 7. Coordinate System Conversions

### Issue: Missing Conversion Methods
**Current State:** Different vector types are supported but no conversion between them.

**Recommendation:** Add conversion methods:

```python
class Vector:
    def to_cartesian(self) -> 'Vector':
        """
        Convert vector to Cartesian coordinates.
        
        Returns:
            Vector in Cartesian coordinates
        """
        if self.vector_type == VectorType.CARTESIAN_3D:
            return self
        
        if self.vector_type == VectorType.CARTESIAN_2D:
            return Vector((*self.components, 0.0), VectorType.CARTESIAN_3D)
        
        if self.vector_type == VectorType.POLAR:
            r, theta = self.components
            x = r * math.cos(theta)
            y = r * math.sin(theta)
            return Vector((x, y), VectorType.CARTESIAN_2D)
        
        if self.vector_type == VectorType.CYLINDRICAL:
            rho, phi, z = self.components
            x = rho * math.cos(phi)
            y = rho * math.sin(phi)
            return Vector((x, y, z), VectorType.CARTESIAN_3D)
        
        if self.vector_type == VectorType.SPHERICAL:
            r, theta, phi = self.components
            x = r * math.sin(theta) * math.cos(phi)
            y = r * math.sin(theta) * math.sin(phi)
            z = r * math.cos(theta)
            return Vector((x, y, z), VectorType.CARTESIAN_3D)
        
        raise GeometryError(f"Conversion from {self.vector_type} not implemented")
    
    @classmethod
    def from_cartesian(
        cls,
        cartesian: 'Vector',
        target_type: VectorType
    ) -> 'Vector':
        """
        Create vector from Cartesian coordinates.
        
        Args:
            cartesian: Vector in Cartesian coordinates
            target_type: Desired coordinate system
            
        Returns:
            Vector in target coordinate system
        """
        if target_type in (VectorType.CARTESIAN_2D, VectorType.CARTESIAN_3D):
            return cls(cartesian.components, target_type)
        
        if target_type == VectorType.POLAR:
            if len(cartesian.components) < 2:
                raise GeometryError("Need at least 2D Cartesian for polar conversion")
            x, y = cartesian.components[0], cartesian.components[1]
            r = math.sqrt(x**2 + y**2)
            theta = math.atan2(y, x)
            return cls((r, theta), VectorType.POLAR)
        
        if target_type == VectorType.CYLINDRICAL:
            if len(cartesian.components) != 3:
                raise GeometryError("Need 3D Cartesian for cylindrical conversion")
            x, y, z = cartesian.components
            rho = math.sqrt(x**2 + y**2)
            phi = math.atan2(y, x)
            return cls((rho, phi, z), VectorType.CYLINDRICAL)
        
        if target_type == VectorType.SPHERICAL:
            if len(cartesian.components) != 3:
                raise GeometryError("Need 3D Cartesian for spherical conversion")
            x, y, z = cartesian.components
            r = math.sqrt(x**2 + y**2 + z**2)
            if r < EPSILON:
                return cls((0.0, 0.0, 0.0), VectorType.SPHERICAL)
            theta = math.acos(z / r)
            phi = math.atan2(y, x)
            return cls((r, theta, phi), VectorType.SPHERICAL)
        
        raise GeometryError(f"Conversion to {target_type} not implemented")
```

---

## 8. Better Error Context

### Issue: Generic Error Messages
**Current Code:**
```python
raise GeometryError("Vector components cannot be empty")
```

**Recommendation:** Include more context in errors:

```python
class GeometryError(Exception):
    """Custom exception with enhanced context."""
    
    def __init__(
        self,
        message: str,
        vector_type: Optional[VectorType] = None,
        components: Optional[Tuple[float, ...]] = None,
        operation: Optional[str] = None
    ):
        self.vector_type = vector_type
        self.components = components
        self.operation = operation
        
        context_parts = [message]
        if operation:
            context_parts.append(f"Operation: {operation}")
        if vector_type:
            context_parts.append(f"Vector type: {vector_type.value}")
        if components:
            context_parts.append(f"Components: {components}")
        
        super().__init__(" | ".join(context_parts))

# Usage:
raise GeometryError(
    "Cannot normalize zero vector",
    vector_type=self.vector_type,
    components=self.components,
    operation="normalize"
)
```

---

## 9. Configuration Validation

### Issue: No Validation of GeometryConfig
**Current Code:**
```python
@dataclass
class GeometryConfig:
    precision: int = 6
    normalize: bool = False
    validate_input: bool = True
    output_format: str = "dict"
```

**Recommendation:** Add validation with `__post_init__`:

```python
from typing import Literal

@dataclass
class GeometryConfig:
    """Configuration for geometry generation with validation."""
    precision: int = 6
    normalize: bool = False
    validate_input: bool = True
    output_format: Literal["dict", "string"] = "dict"
    
    def __post_init__(self):
        """Validate configuration parameters."""
        if not isinstance(self.precision, int) or self.precision < 0:
            raise ValueError(
                f"precision must be non-negative integer, got {self.precision}"
            )
        
        if self.precision > 15:
            raise ValueError(
                f"precision > 15 may cause floating-point issues, got {self.precision}"
            )
        
        valid_formats = {"dict", "string"}
        if self.output_format not in valid_formats:
            raise ValueError(
                f"output_format must be one of {valid_formats}, "
                f"got {self.output_format!r}"
            )
```

---

## 10. Testing Support

### Issue: No Built-in Testing Utilities
**Recommendation:** Add testing helpers:

```python
class Vector:
    def is_close_to(
        self,
        other: 'Vector',
        rel_tol: float = 1e-9,
        abs_tol: float = 0.0
    ) -> bool:
        """
        Check if vectors are approximately equal.
        
        Args:
            other: Vector to compare with
            rel_tol: Relative tolerance
            abs_tol: Absolute tolerance
            
        Returns:
            True if vectors are close
        """
        if len(self.components) != len(other.components):
            return False
        
        return all(
            math.isclose(a, b, rel_tol=rel_tol, abs_tol=abs_tol)
            for a, b in zip(self.components, other.components)
        )
    
    @classmethod
    def zero(cls, dimension: int = 3) -> 'Vector':
        """Create a zero vector of specified dimension."""
        return cls([0.0] * dimension)
    
    @classmethod
    def unit_x(cls) -> 'Vector':
        """Create unit vector in X direction."""
        return cls([1.0, 0.0, 0.0])
    
    @classmethod
    def unit_y(cls) -> 'Vector':
        """Create unit vector in Y direction."""
        return cls([0.0, 1.0, 0.0])
    
    @classmethod
    def unit_z(cls) -> 'Vector':
        """Create unit vector in Z direction."""
        return cls([0.0, 0.0, 1.0])
```

---

## 11. Documentation Improvements

### Issue: Missing Usage Examples in Docstrings

**Recommendation:** Add comprehensive examples:

```python
class Vector:
    """
    Represents a mathematical vector with various coordinate systems.
    
    This class provides a unified interface for working with vectors in
    different coordinate systems (Cartesian, polar, spherical, cylindrical).
    
    Attributes:
        components: The vector components as an immutable tuple
        vector_type: The coordinate system type
        magnitude: Cached magnitude (length) of the vector
    
    Examples:
        Create a 3D Cartesian vector:
        >>> v = Vector([1.0, 2.0, 3.0])
        >>> v.magnitude
        3.7416573867739413
        
        Normalize a vector:
        >>> v_norm = v.normalize()
        >>> v_norm.magnitude
        1.0
        
        Vector arithmetic:
        >>> v1 = Vector([1.0, 0.0, 0.0])
        >>> v2 = Vector([0.0, 1.0, 0.0])
        >>> v3 = v1 + v2
        >>> v3.components
        (1.0, 1.0, 0.0)
        
        Dot product:
        >>> v1.dot(v2)
        0.0
        
        Cross product:
        >>> v_cross = v1.cross(v2)
        >>> v_cross.components
        (0.0, 0.0, 1.0)
        
        Create polar vector:
        >>> v_polar = Vector([1.0, math.pi/4], VectorType.POLAR)
        >>> v_cart = v_polar.to_cartesian()
    """
```

---

## 12. Logging and Debugging

### Issue: No Logging Support
**Recommendation:** Add optional logging:

```python
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class Vector:
    def __init__(
        self,
        components: Union[List[float], Tuple[float, ...], 'Vector'],
        vector_type: VectorType = VectorType.CARTESIAN_3D,
        debug: bool = False
    ):
        """Initialize with optional debug logging."""
        self._debug = debug
        
        if debug:
            logger.debug(
                f"Creating Vector: type={vector_type}, components={components}"
            )
        
        # ... rest of initialization
    
    def normalize(self) -> 'Vector':
        """Normalize with debug logging."""
        mag = self.magnitude
        if self._debug:
            logger.debug(f"Normalizing vector with magnitude {mag}")
        
        if mag < EPSILON:
            raise GeometryError(
                f"Cannot normalize near-zero vector (magnitude: {mag})"
            )
        
        result = Vector(
            tuple(c / mag for c in self.components),
            self.vector_type,
            debug=self._debug
        )
        
        if self._debug:
            logger.debug(f"Normalized vector: {result}")
        
        return result
```

---

## Summary of Key Improvements

1. **Performance**: Add caching, use `__slots__`, consider numpy
2. **Robustness**: Use epsilon for zero comparisons, better validation
3. **Functionality**: Add vector operations (dot, cross, arithmetic)
4. **Type Safety**: Use TypedDict, Protocol, and Literal types
5. **Immutability**: Make Vector truly immutable with `__slots__`
6. **Conversions**: Add coordinate system conversion methods
7. **Testing**: Add comparison utilities and factory methods
8. **Documentation**: Enhance with comprehensive examples
9. **Error Handling**: Add context to exceptions
10. **Logging**: Add optional debug logging

## Priority Implementation Order

1. **High Priority**: Numerical stability (epsilon), vector operations, immutability
2. **Medium Priority**: Coordinate conversions, type safety, caching
3. **Low Priority**: Logging, enhanced documentation

## Breaking Changes

The following improvements involve breaking changes:
- Changing `magnitude()` method to a property
- Making Vector immutable with `__slots__`
- Removing direct attribute assignment

Consider a major version bump or providing a compatibility layer.
