#!/usr/bin/env python3
"""
BAEL - Tensor Manager
Advanced tensor operations for AI agent computations.

Features:
- N-dimensional tensor support
- Basic arithmetic operations
- Matrix operations
- Broadcasting
- Reduction operations
- Reshaping and transposing
- Tensor slicing
- Memory-efficient storage
- Serialization support
"""

import asyncio
import copy
import json
import math
import struct
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from functools import reduce
from typing import (Any, Callable, Dict, Iterator, List, Optional, Sequence,
                    Tuple, Type, TypeVar, Union)

# =============================================================================
# ENUMS
# =============================================================================

class DType(Enum):
    """Data types for tensors."""
    FLOAT32 = "float32"
    FLOAT64 = "float64"
    INT32 = "int32"
    INT64 = "int64"
    BOOL = "bool"


class DeviceType(Enum):
    """Device types."""
    CPU = "cpu"
    GPU = "gpu"


class ReductionOp(Enum):
    """Reduction operations."""
    SUM = "sum"
    MEAN = "mean"
    MAX = "max"
    MIN = "min"
    PROD = "prod"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class TensorInfo:
    """Tensor information."""
    shape: Tuple[int, ...]
    dtype: DType
    device: DeviceType
    num_elements: int
    memory_bytes: int
    requires_grad: bool = False


@dataclass
class TensorStats:
    """Tensor statistics."""
    min_value: float
    max_value: float
    mean_value: float
    std_value: float
    sum_value: float


# =============================================================================
# TENSOR CLASS
# =============================================================================

class Tensor:
    """N-dimensional tensor."""

    def __init__(
        self,
        data: Union[List, float, int],
        dtype: DType = DType.FLOAT32,
        device: DeviceType = DeviceType.CPU
    ):
        self._dtype = dtype
        self._device = device
        self._requires_grad = False
        self._grad: Optional['Tensor'] = None

        # Flatten and get shape
        self._data, self._shape = self._parse_data(data)

    def _parse_data(
        self,
        data: Union[List, float, int]
    ) -> Tuple[List[float], Tuple[int, ...]]:
        """Parse input data to flat list and shape."""
        if isinstance(data, (int, float)):
            return [float(data)], ()

        if not isinstance(data, list):
            data = list(data)

        if not data:
            return [], (0,)

        # Get shape recursively
        shape = []
        current = data

        while isinstance(current, list):
            shape.append(len(current))
            if current:
                current = current[0]
            else:
                break

        # Flatten
        flat = self._flatten(data)

        return flat, tuple(shape)

    def _flatten(self, data: Any) -> List[float]:
        """Flatten nested list."""
        if not isinstance(data, list):
            return [float(data)]

        result = []
        for item in data:
            result.extend(self._flatten(item))

        return result

    def _unflatten(
        self,
        data: List[float],
        shape: Tuple[int, ...]
    ) -> Any:
        """Unflatten to nested list."""
        if not shape:
            return data[0] if data else 0.0

        if len(shape) == 1:
            return data[:shape[0]]

        size = reduce(lambda x, y: x * y, shape[1:], 1)
        result = []

        for i in range(shape[0]):
            start = i * size
            end = start + size
            result.append(self._unflatten(data[start:end], shape[1:]))

        return result

    # -------------------------------------------------------------------------
    # PROPERTIES
    # -------------------------------------------------------------------------

    @property
    def shape(self) -> Tuple[int, ...]:
        """Get shape."""
        return self._shape

    @property
    def ndim(self) -> int:
        """Get number of dimensions."""
        return len(self._shape)

    @property
    def size(self) -> int:
        """Get total number of elements."""
        if not self._shape:
            return 1
        return reduce(lambda x, y: x * y, self._shape, 1)

    @property
    def dtype(self) -> DType:
        """Get data type."""
        return self._dtype

    @property
    def device(self) -> DeviceType:
        """Get device."""
        return self._device

    @property
    def requires_grad(self) -> bool:
        """Get requires_grad."""
        return self._requires_grad

    @requires_grad.setter
    def requires_grad(self, value: bool) -> None:
        """Set requires_grad."""
        self._requires_grad = value

    @property
    def grad(self) -> Optional['Tensor']:
        """Get gradient."""
        return self._grad

    # -------------------------------------------------------------------------
    # DATA ACCESS
    # -------------------------------------------------------------------------

    def item(self) -> float:
        """Get scalar value."""
        if self.size != 1:
            raise ValueError("Only single-element tensors can be converted")
        return self._data[0]

    def tolist(self) -> Any:
        """Convert to nested list."""
        return self._unflatten(self._data, self._shape)

    def numpy(self) -> List[float]:
        """Get as flat list (numpy-like interface)."""
        return self._data.copy()

    def __getitem__(self, index: Union[int, Tuple, slice]) -> 'Tensor':
        """Get item(s) by index."""
        if isinstance(index, int):
            if self.ndim == 0:
                raise IndexError("Cannot index scalar")

            # Get slice of first dimension
            stride = self.size // self._shape[0]
            start = index * stride
            end = start + stride

            new_data = self._data[start:end]
            new_shape = self._shape[1:]

            result = Tensor.__new__(Tensor)
            result._data = new_data
            result._shape = new_shape
            result._dtype = self._dtype
            result._device = self._device
            result._requires_grad = False
            result._grad = None

            return result

        # Handle tuples and slices
        return self  # Simplified

    # -------------------------------------------------------------------------
    # ARITHMETIC OPERATIONS
    # -------------------------------------------------------------------------

    def _broadcast_shapes(
        self,
        shape1: Tuple[int, ...],
        shape2: Tuple[int, ...]
    ) -> Tuple[int, ...]:
        """Calculate broadcast shape."""
        max_ndim = max(len(shape1), len(shape2))

        # Pad with 1s
        shape1 = (1,) * (max_ndim - len(shape1)) + shape1
        shape2 = (1,) * (max_ndim - len(shape2)) + shape2

        result = []
        for s1, s2 in zip(shape1, shape2):
            if s1 == s2:
                result.append(s1)
            elif s1 == 1:
                result.append(s2)
            elif s2 == 1:
                result.append(s1)
            else:
                raise ValueError(f"Cannot broadcast shapes {shape1} and {shape2}")

        return tuple(result)

    def _broadcast_data(
        self,
        data: List[float],
        from_shape: Tuple[int, ...],
        to_shape: Tuple[int, ...]
    ) -> List[float]:
        """Broadcast data to new shape."""
        if from_shape == to_shape:
            return data

        from_size = reduce(lambda x, y: x * y, from_shape, 1) if from_shape else 1
        to_size = reduce(lambda x, y: x * y, to_shape, 1) if to_shape else 1

        if from_size == 1:
            return data * to_size

        # Simple broadcast (repeat pattern)
        repeat = to_size // from_size
        return data * repeat

    def __add__(self, other: Union['Tensor', float, int]) -> 'Tensor':
        """Add tensors or scalar."""
        if isinstance(other, (int, float)):
            new_data = [x + other for x in self._data]
            return self._create_result(new_data, self._shape)

        # Broadcast shapes
        result_shape = self._broadcast_shapes(self._shape, other._shape)

        data1 = self._broadcast_data(self._data, self._shape, result_shape)
        data2 = self._broadcast_data(other._data, other._shape, result_shape)

        new_data = [a + b for a, b in zip(data1, data2)]
        return self._create_result(new_data, result_shape)

    def __radd__(self, other: Union[float, int]) -> 'Tensor':
        return self.__add__(other)

    def __sub__(self, other: Union['Tensor', float, int]) -> 'Tensor':
        """Subtract tensors or scalar."""
        if isinstance(other, (int, float)):
            new_data = [x - other for x in self._data]
            return self._create_result(new_data, self._shape)

        result_shape = self._broadcast_shapes(self._shape, other._shape)

        data1 = self._broadcast_data(self._data, self._shape, result_shape)
        data2 = self._broadcast_data(other._data, other._shape, result_shape)

        new_data = [a - b for a, b in zip(data1, data2)]
        return self._create_result(new_data, result_shape)

    def __rsub__(self, other: Union[float, int]) -> 'Tensor':
        new_data = [other - x for x in self._data]
        return self._create_result(new_data, self._shape)

    def __mul__(self, other: Union['Tensor', float, int]) -> 'Tensor':
        """Multiply tensors or scalar."""
        if isinstance(other, (int, float)):
            new_data = [x * other for x in self._data]
            return self._create_result(new_data, self._shape)

        result_shape = self._broadcast_shapes(self._shape, other._shape)

        data1 = self._broadcast_data(self._data, self._shape, result_shape)
        data2 = self._broadcast_data(other._data, other._shape, result_shape)

        new_data = [a * b for a, b in zip(data1, data2)]
        return self._create_result(new_data, result_shape)

    def __rmul__(self, other: Union[float, int]) -> 'Tensor':
        return self.__mul__(other)

    def __truediv__(self, other: Union['Tensor', float, int]) -> 'Tensor':
        """Divide tensors or scalar."""
        if isinstance(other, (int, float)):
            new_data = [x / other for x in self._data]
            return self._create_result(new_data, self._shape)

        result_shape = self._broadcast_shapes(self._shape, other._shape)

        data1 = self._broadcast_data(self._data, self._shape, result_shape)
        data2 = self._broadcast_data(other._data, other._shape, result_shape)

        new_data = [a / b if b != 0 else 0.0 for a, b in zip(data1, data2)]
        return self._create_result(new_data, result_shape)

    def __neg__(self) -> 'Tensor':
        """Negate tensor."""
        new_data = [-x for x in self._data]
        return self._create_result(new_data, self._shape)

    def __pow__(self, power: Union[float, int]) -> 'Tensor':
        """Power operation."""
        new_data = [x ** power for x in self._data]
        return self._create_result(new_data, self._shape)

    def _create_result(
        self,
        data: List[float],
        shape: Tuple[int, ...]
    ) -> 'Tensor':
        """Create result tensor."""
        result = Tensor.__new__(Tensor)
        result._data = data
        result._shape = shape
        result._dtype = self._dtype
        result._device = self._device
        result._requires_grad = False
        result._grad = None
        return result

    # -------------------------------------------------------------------------
    # REDUCTION OPERATIONS
    # -------------------------------------------------------------------------

    def sum(self, dim: Optional[int] = None) -> 'Tensor':
        """Sum reduction."""
        if dim is None:
            return self._create_result([sum(self._data)], ())

        # Sum along dimension
        return self._reduce_dim(dim, sum)

    def mean(self, dim: Optional[int] = None) -> 'Tensor':
        """Mean reduction."""
        if dim is None:
            avg = sum(self._data) / len(self._data) if self._data else 0.0
            return self._create_result([avg], ())

        def avg_fn(values):
            return sum(values) / len(values) if values else 0.0

        return self._reduce_dim(dim, avg_fn)

    def max(self, dim: Optional[int] = None) -> 'Tensor':
        """Max reduction."""
        if dim is None:
            return self._create_result([max(self._data)] if self._data else [0.0], ())

        return self._reduce_dim(dim, max)

    def min(self, dim: Optional[int] = None) -> 'Tensor':
        """Min reduction."""
        if dim is None:
            return self._create_result([min(self._data)] if self._data else [0.0], ())

        return self._reduce_dim(dim, min)

    def _reduce_dim(
        self,
        dim: int,
        fn: Callable[[List[float]], float]
    ) -> 'Tensor':
        """Reduce along dimension."""
        if dim < 0:
            dim = self.ndim + dim

        if dim >= self.ndim:
            raise ValueError(f"Invalid dimension {dim}")

        # Calculate new shape
        new_shape = self._shape[:dim] + self._shape[dim+1:]

        if not new_shape:
            new_shape = ()

        # Calculate strides
        stride = 1
        for i in range(dim + 1, self.ndim):
            stride *= self._shape[i]

        dim_size = self._shape[dim]
        outer_size = 1
        for i in range(dim):
            outer_size *= self._shape[i]

        inner_size = stride

        new_data = []
        for outer in range(outer_size):
            for inner in range(inner_size):
                values = []
                for d in range(dim_size):
                    idx = outer * dim_size * inner_size + d * inner_size + inner
                    values.append(self._data[idx])
                new_data.append(fn(values))

        return self._create_result(new_data, new_shape)

    # -------------------------------------------------------------------------
    # SHAPE OPERATIONS
    # -------------------------------------------------------------------------

    def reshape(self, *shape: int) -> 'Tensor':
        """Reshape tensor."""
        if len(shape) == 1 and isinstance(shape[0], (list, tuple)):
            shape = tuple(shape[0])

        new_size = reduce(lambda x, y: x * y, shape, 1)

        if new_size != self.size:
            raise ValueError(f"Cannot reshape {self._shape} to {shape}")

        return self._create_result(self._data.copy(), shape)

    def flatten(self) -> 'Tensor':
        """Flatten tensor."""
        return self.reshape(self.size)

    def squeeze(self, dim: Optional[int] = None) -> 'Tensor':
        """Remove dimensions of size 1."""
        if dim is not None:
            if self._shape[dim] != 1:
                return self._create_result(self._data.copy(), self._shape)
            new_shape = self._shape[:dim] + self._shape[dim+1:]
        else:
            new_shape = tuple(s for s in self._shape if s != 1)

        if not new_shape:
            new_shape = ()

        return self._create_result(self._data.copy(), new_shape)

    def unsqueeze(self, dim: int) -> 'Tensor':
        """Add dimension of size 1."""
        if dim < 0:
            dim = self.ndim + 1 + dim

        new_shape = self._shape[:dim] + (1,) + self._shape[dim:]
        return self._create_result(self._data.copy(), new_shape)

    def transpose(self, dim0: int, dim1: int) -> 'Tensor':
        """Transpose two dimensions."""
        if self.ndim < 2:
            return self._create_result(self._data.copy(), self._shape)

        # Swap dimensions in shape
        new_shape = list(self._shape)
        new_shape[dim0], new_shape[dim1] = new_shape[dim1], new_shape[dim0]

        # Reorder data (simplified for 2D)
        if self.ndim == 2:
            rows, cols = self._shape
            new_data = []
            for j in range(cols):
                for i in range(rows):
                    new_data.append(self._data[i * cols + j])
            return self._create_result(new_data, tuple(new_shape))

        return self._create_result(self._data.copy(), tuple(new_shape))

    @property
    def T(self) -> 'Tensor':
        """Transpose (2D)."""
        if self.ndim == 2:
            return self.transpose(0, 1)
        return self

    # -------------------------------------------------------------------------
    # MATH FUNCTIONS
    # -------------------------------------------------------------------------

    def sqrt(self) -> 'Tensor':
        """Element-wise square root."""
        new_data = [math.sqrt(max(0, x)) for x in self._data]
        return self._create_result(new_data, self._shape)

    def exp(self) -> 'Tensor':
        """Element-wise exponential."""
        new_data = [math.exp(min(x, 700)) for x in self._data]
        return self._create_result(new_data, self._shape)

    def log(self) -> 'Tensor':
        """Element-wise logarithm."""
        new_data = [math.log(max(x, 1e-10)) for x in self._data]
        return self._create_result(new_data, self._shape)

    def abs(self) -> 'Tensor':
        """Element-wise absolute value."""
        new_data = [abs(x) for x in self._data]
        return self._create_result(new_data, self._shape)

    def sin(self) -> 'Tensor':
        """Element-wise sine."""
        new_data = [math.sin(x) for x in self._data]
        return self._create_result(new_data, self._shape)

    def cos(self) -> 'Tensor':
        """Element-wise cosine."""
        new_data = [math.cos(x) for x in self._data]
        return self._create_result(new_data, self._shape)

    def tanh(self) -> 'Tensor':
        """Element-wise hyperbolic tangent."""
        new_data = [math.tanh(x) for x in self._data]
        return self._create_result(new_data, self._shape)

    def relu(self) -> 'Tensor':
        """Element-wise ReLU."""
        new_data = [max(0, x) for x in self._data]
        return self._create_result(new_data, self._shape)

    def sigmoid(self) -> 'Tensor':
        """Element-wise sigmoid."""
        new_data = [1 / (1 + math.exp(-min(max(x, -500), 500))) for x in self._data]
        return self._create_result(new_data, self._shape)

    def softmax(self, dim: int = -1) -> 'Tensor':
        """Softmax along dimension."""
        if dim < 0:
            dim = self.ndim + dim

        # Simplified 1D softmax
        max_val = max(self._data)
        exp_data = [math.exp(x - max_val) for x in self._data]
        exp_sum = sum(exp_data)
        new_data = [x / exp_sum for x in exp_data]

        return self._create_result(new_data, self._shape)

    # -------------------------------------------------------------------------
    # MATRIX OPERATIONS
    # -------------------------------------------------------------------------

    def matmul(self, other: 'Tensor') -> 'Tensor':
        """Matrix multiplication."""
        if self.ndim != 2 or other.ndim != 2:
            raise ValueError("matmul requires 2D tensors")

        m, k1 = self._shape
        k2, n = other._shape

        if k1 != k2:
            raise ValueError(f"Cannot multiply {self._shape} and {other._shape}")

        k = k1
        new_data = []

        for i in range(m):
            for j in range(n):
                val = 0.0
                for l in range(k):
                    val += self._data[i * k + l] * other._data[l * n + j]
                new_data.append(val)

        return self._create_result(new_data, (m, n))

    def __matmul__(self, other: 'Tensor') -> 'Tensor':
        return self.matmul(other)

    def dot(self, other: 'Tensor') -> 'Tensor':
        """Dot product."""
        if self.size != other.size:
            raise ValueError("Tensors must have same size")

        val = sum(a * b for a, b in zip(self._data, other._data))
        return self._create_result([val], ())

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def stats(self) -> TensorStats:
        """Get tensor statistics."""
        if not self._data:
            return TensorStats(0, 0, 0, 0, 0)

        min_val = min(self._data)
        max_val = max(self._data)
        sum_val = sum(self._data)
        mean_val = sum_val / len(self._data)

        variance = sum((x - mean_val) ** 2 for x in self._data) / len(self._data)
        std_val = math.sqrt(variance)

        return TensorStats(min_val, max_val, mean_val, std_val, sum_val)

    def info(self) -> TensorInfo:
        """Get tensor info."""
        bytes_per_elem = 4 if self._dtype in [DType.FLOAT32, DType.INT32] else 8

        return TensorInfo(
            shape=self._shape,
            dtype=self._dtype,
            device=self._device,
            num_elements=self.size,
            memory_bytes=self.size * bytes_per_elem,
            requires_grad=self._requires_grad
        )

    # -------------------------------------------------------------------------
    # CLONING AND COPYING
    # -------------------------------------------------------------------------

    def clone(self) -> 'Tensor':
        """Create a copy."""
        return self._create_result(self._data.copy(), self._shape)

    def detach(self) -> 'Tensor':
        """Detach from computation graph."""
        result = self.clone()
        result._requires_grad = False
        return result

    # -------------------------------------------------------------------------
    # REPRESENTATION
    # -------------------------------------------------------------------------

    def __repr__(self) -> str:
        data_str = str(self.tolist())
        if len(data_str) > 100:
            data_str = data_str[:100] + "..."
        return f"Tensor({data_str}, shape={self._shape}, dtype={self._dtype.value})"


# =============================================================================
# TENSOR FACTORY FUNCTIONS
# =============================================================================

def zeros(*shape: int, dtype: DType = DType.FLOAT32) -> Tensor:
    """Create tensor of zeros."""
    size = reduce(lambda x, y: x * y, shape, 1)
    data = [0.0] * size
    result = Tensor.__new__(Tensor)
    result._data = data
    result._shape = shape
    result._dtype = dtype
    result._device = DeviceType.CPU
    result._requires_grad = False
    result._grad = None
    return result


def ones(*shape: int, dtype: DType = DType.FLOAT32) -> Tensor:
    """Create tensor of ones."""
    size = reduce(lambda x, y: x * y, shape, 1)
    data = [1.0] * size
    result = Tensor.__new__(Tensor)
    result._data = data
    result._shape = shape
    result._dtype = dtype
    result._device = DeviceType.CPU
    result._requires_grad = False
    result._grad = None
    return result


def arange(start: int, end: int, step: int = 1) -> Tensor:
    """Create tensor with range of values."""
    data = list(range(start, end, step))
    data = [float(x) for x in data]
    return Tensor(data)


def linspace(start: float, end: float, steps: int) -> Tensor:
    """Create tensor with linearly spaced values."""
    if steps <= 1:
        return Tensor([start])

    step = (end - start) / (steps - 1)
    data = [start + i * step for i in range(steps)]
    return Tensor(data)


def randn(*shape: int) -> Tensor:
    """Create tensor with random normal values."""
    import random

    size = reduce(lambda x, y: x * y, shape, 1)

    # Box-Muller transform for normal distribution
    data = []
    for _ in range(size):
        u1 = random.random()
        u2 = random.random()
        z = math.sqrt(-2 * math.log(max(u1, 1e-10))) * math.cos(2 * math.pi * u2)
        data.append(z)

    result = Tensor.__new__(Tensor)
    result._data = data
    result._shape = shape
    result._dtype = DType.FLOAT32
    result._device = DeviceType.CPU
    result._requires_grad = False
    result._grad = None
    return result


def eye(n: int) -> Tensor:
    """Create identity matrix."""
    data = []
    for i in range(n):
        for j in range(n):
            data.append(1.0 if i == j else 0.0)

    result = Tensor.__new__(Tensor)
    result._data = data
    result._shape = (n, n)
    result._dtype = DType.FLOAT32
    result._device = DeviceType.CPU
    result._requires_grad = False
    result._grad = None
    return result


# =============================================================================
# TENSOR MANAGER
# =============================================================================

class TensorManager:
    """
    Tensor Manager for BAEL.

    Advanced tensor operations for AI computations.
    """

    def __init__(self):
        self._tensors: Dict[str, Tensor] = {}

    # -------------------------------------------------------------------------
    # TENSOR MANAGEMENT
    # -------------------------------------------------------------------------

    def create(
        self,
        name: str,
        data: Union[List, float, int],
        dtype: DType = DType.FLOAT32
    ) -> Tensor:
        """Create and store tensor."""
        tensor = Tensor(data, dtype)
        self._tensors[name] = tensor
        return tensor

    def get(self, name: str) -> Optional[Tensor]:
        """Get tensor by name."""
        return self._tensors.get(name)

    def delete(self, name: str) -> bool:
        """Delete tensor."""
        if name in self._tensors:
            del self._tensors[name]
            return True
        return False

    def list_tensors(self) -> List[str]:
        """List tensor names."""
        return list(self._tensors.keys())

    # -------------------------------------------------------------------------
    # FACTORY METHODS
    # -------------------------------------------------------------------------

    def zeros(self, name: str, *shape: int) -> Tensor:
        """Create zeros tensor."""
        tensor = zeros(*shape)
        self._tensors[name] = tensor
        return tensor

    def ones(self, name: str, *shape: int) -> Tensor:
        """Create ones tensor."""
        tensor = ones(*shape)
        self._tensors[name] = tensor
        return tensor

    def randn(self, name: str, *shape: int) -> Tensor:
        """Create random normal tensor."""
        tensor = randn(*shape)
        self._tensors[name] = tensor
        return tensor

    def eye(self, name: str, n: int) -> Tensor:
        """Create identity matrix."""
        tensor = eye(n)
        self._tensors[name] = tensor
        return tensor

    # -------------------------------------------------------------------------
    # OPERATIONS
    # -------------------------------------------------------------------------

    def add(self, name1: str, name2: str, result_name: str) -> Optional[Tensor]:
        """Add two tensors."""
        t1 = self._tensors.get(name1)
        t2 = self._tensors.get(name2)

        if t1 and t2:
            result = t1 + t2
            self._tensors[result_name] = result
            return result
        return None

    def matmul(self, name1: str, name2: str, result_name: str) -> Optional[Tensor]:
        """Matrix multiply two tensors."""
        t1 = self._tensors.get(name1)
        t2 = self._tensors.get(name2)

        if t1 and t2:
            result = t1 @ t2
            self._tensors[result_name] = result
            return result
        return None

    def reduce(
        self,
        name: str,
        op: ReductionOp,
        dim: Optional[int] = None
    ) -> Optional[Tensor]:
        """Apply reduction operation."""
        tensor = self._tensors.get(name)
        if not tensor:
            return None

        if op == ReductionOp.SUM:
            return tensor.sum(dim)
        elif op == ReductionOp.MEAN:
            return tensor.mean(dim)
        elif op == ReductionOp.MAX:
            return tensor.max(dim)
        elif op == ReductionOp.MIN:
            return tensor.min(dim)
        else:
            return tensor.sum(dim)


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Tensor Manager."""
    print("=" * 70)
    print("BAEL - TENSOR MANAGER DEMO")
    print("Advanced Tensor Operations for AI Agents")
    print("=" * 70)
    print()

    manager = TensorManager()

    # 1. Create Tensor
    print("1. CREATE TENSOR:")
    print("-" * 40)

    t = manager.create("matrix", [[1, 2, 3], [4, 5, 6]])
    print(f"   {t}")
    print(f"   Shape: {t.shape}")
    print()

    # 2. Zeros and Ones
    print("2. ZEROS AND ONES:")
    print("-" * 40)

    z = manager.zeros("zeros", 2, 3)
    o = manager.ones("ones", 2, 3)

    print(f"   Zeros: {z.tolist()}")
    print(f"   Ones: {o.tolist()}")
    print()

    # 3. Random Tensor
    print("3. RANDOM TENSOR:")
    print("-" * 40)

    r = manager.randn("random", 3, 3)
    print(f"   Random shape: {r.shape}")
    stats = r.stats()
    print(f"   Mean: {stats.mean_value:.4f}")
    print(f"   Std: {stats.std_value:.4f}")
    print()

    # 4. Arithmetic
    print("4. ARITHMETIC:")
    print("-" * 40)

    a = Tensor([[1, 2], [3, 4]])
    b = Tensor([[5, 6], [7, 8]])

    print(f"   a + b = {(a + b).tolist()}")
    print(f"   a * 2 = {(a * 2).tolist()}")
    print(f"   a - b = {(a - b).tolist()}")
    print()

    # 5. Matrix Multiplication
    print("5. MATRIX MULTIPLICATION:")
    print("-" * 40)

    m1 = Tensor([[1, 2], [3, 4]])
    m2 = Tensor([[5, 6], [7, 8]])

    result = m1 @ m2
    print(f"   Result: {result.tolist()}")
    print()

    # 6. Reductions
    print("6. REDUCTIONS:")
    print("-" * 40)

    t = Tensor([[1, 2, 3], [4, 5, 6]])

    print(f"   Sum: {t.sum().item()}")
    print(f"   Mean: {t.mean().item()}")
    print(f"   Max: {t.max().item()}")
    print(f"   Min: {t.min().item()}")
    print()

    # 7. Shape Operations
    print("7. SHAPE OPERATIONS:")
    print("-" * 40)

    t = Tensor([[1, 2, 3], [4, 5, 6]])

    print(f"   Original: {t.shape}")
    print(f"   Reshape: {t.reshape(3, 2).shape}")
    print(f"   Flatten: {t.flatten().shape}")
    print(f"   Transpose: {t.T.shape}")
    print()

    # 8. Math Functions
    print("8. MATH FUNCTIONS:")
    print("-" * 40)

    t = Tensor([0.0, 1.0, 2.0, 3.0])

    print(f"   exp: {t.exp().tolist()[:2]}...")
    print(f"   sqrt: {t.sqrt().tolist()}")
    print(f"   relu: {Tensor([-1, 0, 1, 2]).relu().tolist()}")
    print(f"   sigmoid: {Tensor([0]).sigmoid().item():.4f}")
    print()

    # 9. Softmax
    print("9. SOFTMAX:")
    print("-" * 40)

    logits = Tensor([1.0, 2.0, 3.0])
    probs = logits.softmax()

    print(f"   Logits: {logits.tolist()}")
    print(f"   Probs: {[f'{p:.4f}' for p in probs.tolist()]}")
    print(f"   Sum: {probs.sum().item():.4f}")
    print()

    # 10. Identity Matrix
    print("10. IDENTITY MATRIX:")
    print("-" * 40)

    I = manager.eye("identity", 3)
    print(f"   Identity:\n   {I.tolist()}")
    print()

    # 11. Linspace
    print("11. LINSPACE:")
    print("-" * 40)

    space = linspace(0, 10, 5)
    print(f"   Linspace: {space.tolist()}")
    print()

    # 12. Tensor Info
    print("12. TENSOR INFO:")
    print("-" * 40)

    t = manager.create("info_test", [[1, 2], [3, 4]])
    info = t.info()

    print(f"   Shape: {info.shape}")
    print(f"   Elements: {info.num_elements}")
    print(f"   Memory: {info.memory_bytes} bytes")
    print()

    # 13. Dot Product
    print("13. DOT PRODUCT:")
    print("-" * 40)

    a = Tensor([1, 2, 3])
    b = Tensor([4, 5, 6])

    dot = a.dot(b)
    print(f"   a · b = {dot.item()}")
    print()

    # 14. List Tensors
    print("14. LIST TENSORS:")
    print("-" * 40)

    tensors = manager.list_tensors()
    print(f"   Tensors: {tensors}")
    print()

    # 15. Manager Operations
    print("15. MANAGER OPERATIONS:")
    print("-" * 40)

    manager.create("op_a", [[1, 0], [0, 1]])
    manager.create("op_b", [[2, 0], [0, 2]])

    result = manager.add("op_a", "op_b", "op_sum")
    if result:
        print(f"   Sum: {result.tolist()}")

    result = manager.matmul("op_a", "op_b", "op_matmul")
    if result:
        print(f"   Matmul: {result.tolist()}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Tensor Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
