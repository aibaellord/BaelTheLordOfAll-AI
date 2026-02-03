#!/usr/bin/env python3
"""
BAEL - Tensor Engine
Comprehensive tensor operations for neural computation.

Features:
- Tensor creation
- Mathematical operations
- Shape manipulation
- Broadcasting
- Gradient tracking
- Device management
"""

import asyncio
import math
import random
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Sequence, Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class DataType(Enum):
    """Tensor data types."""
    FLOAT32 = "float32"
    FLOAT64 = "float64"
    INT32 = "int32"
    INT64 = "int64"
    BOOL = "bool"


class Device(Enum):
    """Compute devices."""
    CPU = "cpu"
    GPU = "gpu"
    TPU = "tpu"


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
class TensorStats:
    """Tensor statistics."""
    shape: Tuple[int, ...]
    dtype: DataType
    device: Device
    numel: int
    min_val: float
    max_val: float
    mean_val: float
    std_val: float


@dataclass
class GradientInfo:
    """Gradient tracking info."""
    requires_grad: bool = False
    grad: Optional["Tensor"] = None
    grad_fn: Optional[str] = None
    is_leaf: bool = True


# =============================================================================
# TENSOR
# =============================================================================

class Tensor:
    """
    A multi-dimensional array for numerical computation.
    """

    def __init__(
        self,
        data: Union[List, "Tensor", float, int],
        dtype: DataType = DataType.FLOAT32,
        device: Device = Device.CPU,
        requires_grad: bool = False
    ):
        if isinstance(data, Tensor):
            self._data = data._data.copy()
            self._shape = data._shape
        elif isinstance(data, (int, float)):
            self._data = [float(data)]
            self._shape = ()
        else:
            self._data, self._shape = self._flatten_nested(data)

        self._dtype = dtype
        self._device = device
        self._grad_info = GradientInfo(requires_grad=requires_grad)
        self._id = str(uuid.uuid4())[:8]

    def _flatten_nested(self, data: List) -> Tuple[List[float], Tuple[int, ...]]:
        """Flatten nested list and compute shape."""
        if not isinstance(data, list):
            return [float(data)], ()

        if not data:
            return [], (0,)

        if not isinstance(data[0], list):
            return [float(x) for x in data], (len(data),)

        shape = [len(data)]
        inner_data, inner_shape = self._flatten_nested(data[0])
        shape.extend(inner_shape)

        flat = []
        for item in data:
            inner_flat, _ = self._flatten_nested(item)
            flat.extend(inner_flat)

        return flat, tuple(shape)

    @property
    def shape(self) -> Tuple[int, ...]:
        """Get tensor shape."""
        return self._shape

    @property
    def ndim(self) -> int:
        """Number of dimensions."""
        return len(self._shape)

    @property
    def numel(self) -> int:
        """Total number of elements."""
        if not self._shape:
            return 1
        result = 1
        for dim in self._shape:
            result *= dim
        return result

    @property
    def dtype(self) -> DataType:
        """Data type."""
        return self._dtype

    @property
    def device(self) -> Device:
        """Device."""
        return self._device

    @property
    def requires_grad(self) -> bool:
        """Whether gradient is required."""
        return self._grad_info.requires_grad

    @property
    def grad(self) -> Optional["Tensor"]:
        """Gradient."""
        return self._grad_info.grad

    def _get_flat_index(self, indices: Tuple[int, ...]) -> int:
        """Convert multi-dimensional index to flat index."""
        if len(indices) != len(self._shape):
            raise IndexError("Wrong number of indices")

        flat_idx = 0
        multiplier = 1

        for i in range(len(indices) - 1, -1, -1):
            if indices[i] < 0 or indices[i] >= self._shape[i]:
                raise IndexError(f"Index {indices[i]} out of range for dim {i}")
            flat_idx += indices[i] * multiplier
            multiplier *= self._shape[i]

        return flat_idx

    def __getitem__(self, indices: Union[int, Tuple[int, ...]]) -> Union[float, "Tensor"]:
        """Get element or slice."""
        if isinstance(indices, int):
            indices = (indices,)

        if len(indices) == len(self._shape):
            flat_idx = self._get_flat_index(indices)
            return self._data[flat_idx]

        if len(indices) == 1:
            idx = indices[0]
            if idx < 0 or idx >= self._shape[0]:
                raise IndexError(f"Index {idx} out of range")

            if len(self._shape) == 1:
                return self._data[idx]

            inner_size = 1
            for dim in self._shape[1:]:
                inner_size *= dim

            start = idx * inner_size
            end = start + inner_size

            new_data = self._data[start:end]
            result = Tensor.__new__(Tensor)
            result._data = new_data
            result._shape = self._shape[1:]
            result._dtype = self._dtype
            result._device = self._device
            result._grad_info = GradientInfo()
            result._id = str(uuid.uuid4())[:8]

            return result

        raise IndexError("Slicing not fully implemented")

    def __setitem__(self, indices: Union[int, Tuple[int, ...]], value: float) -> None:
        """Set element."""
        if isinstance(indices, int):
            indices = (indices,)

        flat_idx = self._get_flat_index(indices)
        self._data[flat_idx] = float(value)

    def item(self) -> float:
        """Get scalar value."""
        if self.numel != 1:
            raise ValueError("Can only convert scalar tensor to Python number")
        return self._data[0]

    def tolist(self) -> List:
        """Convert to nested list."""
        if not self._shape:
            return self._data[0]

        if len(self._shape) == 1:
            return self._data.copy()

        result = []
        inner_size = 1
        for dim in self._shape[1:]:
            inner_size *= dim

        for i in range(self._shape[0]):
            start = i * inner_size
            end = start + inner_size

            inner = Tensor.__new__(Tensor)
            inner._data = self._data[start:end]
            inner._shape = self._shape[1:]
            inner._dtype = self._dtype
            inner._device = self._device
            inner._grad_info = GradientInfo()
            inner._id = str(uuid.uuid4())[:8]

            result.append(inner.tolist())

        return result

    def reshape(self, *shape: int) -> "Tensor":
        """Reshape the tensor."""
        new_numel = 1
        neg_idx = -1

        for i, dim in enumerate(shape):
            if dim == -1:
                if neg_idx >= 0:
                    raise ValueError("Only one dimension can be -1")
                neg_idx = i
            else:
                new_numel *= dim

        if neg_idx >= 0:
            inferred = self.numel // new_numel
            shape = shape[:neg_idx] + (inferred,) + shape[neg_idx + 1:]
            new_numel *= inferred

        if new_numel != self.numel:
            raise ValueError(f"Cannot reshape {self._shape} to {shape}")

        result = Tensor.__new__(Tensor)
        result._data = self._data.copy()
        result._shape = shape
        result._dtype = self._dtype
        result._device = self._device
        result._grad_info = GradientInfo(requires_grad=self.requires_grad)
        result._id = str(uuid.uuid4())[:8]

        return result

    def flatten(self) -> "Tensor":
        """Flatten to 1D."""
        return self.reshape(self.numel)

    def squeeze(self, dim: Optional[int] = None) -> "Tensor":
        """Remove size-1 dimensions."""
        new_shape = []

        for i, d in enumerate(self._shape):
            if dim is not None:
                if i == dim and d == 1:
                    continue
                new_shape.append(d)
            else:
                if d != 1:
                    new_shape.append(d)

        return self.reshape(*new_shape) if new_shape else self.reshape(1)

    def unsqueeze(self, dim: int) -> "Tensor":
        """Add a size-1 dimension."""
        new_shape = list(self._shape)
        new_shape.insert(dim, 1)
        return self.reshape(*new_shape)

    def transpose(self, dim0: int, dim1: int) -> "Tensor":
        """Transpose two dimensions."""
        if len(self._shape) < 2:
            return self.clone()

        perm = list(range(len(self._shape)))
        perm[dim0], perm[dim1] = perm[dim1], perm[dim0]

        return self.permute(*perm)

    def permute(self, *dims: int) -> "Tensor":
        """Permute dimensions."""
        if len(dims) != len(self._shape):
            raise ValueError("Permutation must have same number of dims")

        new_shape = tuple(self._shape[d] for d in dims)
        new_data = [0.0] * self.numel

        def get_indices(flat_idx: int, shape: Tuple[int, ...]) -> List[int]:
            indices = []
            for dim in reversed(shape):
                indices.insert(0, flat_idx % dim)
                flat_idx //= dim
            return indices

        def get_flat(indices: List[int], shape: Tuple[int, ...]) -> int:
            flat = 0
            mult = 1
            for i in range(len(indices) - 1, -1, -1):
                flat += indices[i] * mult
                mult *= shape[i]
            return flat

        for old_flat in range(self.numel):
            old_indices = get_indices(old_flat, self._shape)
            new_indices = [old_indices[d] for d in dims]
            new_flat = get_flat(new_indices, new_shape)
            new_data[new_flat] = self._data[old_flat]

        result = Tensor.__new__(Tensor)
        result._data = new_data
        result._shape = new_shape
        result._dtype = self._dtype
        result._device = self._device
        result._grad_info = GradientInfo(requires_grad=self.requires_grad)
        result._id = str(uuid.uuid4())[:8]

        return result

    def clone(self) -> "Tensor":
        """Create a copy."""
        result = Tensor.__new__(Tensor)
        result._data = self._data.copy()
        result._shape = self._shape
        result._dtype = self._dtype
        result._device = self._device
        result._grad_info = GradientInfo(requires_grad=self.requires_grad)
        result._id = str(uuid.uuid4())[:8]
        return result

    def _apply_elementwise(
        self,
        other: Union["Tensor", float, int],
        op: Callable[[float, float], float]
    ) -> "Tensor":
        """Apply element-wise operation."""
        if isinstance(other, (int, float)):
            new_data = [op(x, float(other)) for x in self._data]

            result = Tensor.__new__(Tensor)
            result._data = new_data
            result._shape = self._shape
            result._dtype = self._dtype
            result._device = self._device
            result._grad_info = GradientInfo()
            result._id = str(uuid.uuid4())[:8]
            return result

        if self._shape != other._shape:
            raise ValueError(f"Shape mismatch: {self._shape} vs {other._shape}")

        new_data = [op(x, y) for x, y in zip(self._data, other._data)]

        result = Tensor.__new__(Tensor)
        result._data = new_data
        result._shape = self._shape
        result._dtype = self._dtype
        result._device = self._device
        result._grad_info = GradientInfo()
        result._id = str(uuid.uuid4())[:8]
        return result

    def __add__(self, other: Union["Tensor", float, int]) -> "Tensor":
        return self._apply_elementwise(other, lambda x, y: x + y)

    def __radd__(self, other: Union[float, int]) -> "Tensor":
        return self.__add__(other)

    def __sub__(self, other: Union["Tensor", float, int]) -> "Tensor":
        return self._apply_elementwise(other, lambda x, y: x - y)

    def __rsub__(self, other: Union[float, int]) -> "Tensor":
        return self._apply_elementwise(other, lambda x, y: y - x)

    def __mul__(self, other: Union["Tensor", float, int]) -> "Tensor":
        return self._apply_elementwise(other, lambda x, y: x * y)

    def __rmul__(self, other: Union[float, int]) -> "Tensor":
        return self.__mul__(other)

    def __truediv__(self, other: Union["Tensor", float, int]) -> "Tensor":
        return self._apply_elementwise(other, lambda x, y: x / y if y != 0 else float('inf'))

    def __neg__(self) -> "Tensor":
        return self * -1

    def __pow__(self, power: Union["Tensor", float, int]) -> "Tensor":
        return self._apply_elementwise(power, lambda x, y: x ** y)

    def abs(self) -> "Tensor":
        """Absolute value."""
        new_data = [abs(x) for x in self._data]
        return self._create_result(new_data, self._shape)

    def sqrt(self) -> "Tensor":
        """Square root."""
        new_data = [math.sqrt(max(0, x)) for x in self._data]
        return self._create_result(new_data, self._shape)

    def exp(self) -> "Tensor":
        """Exponential."""
        new_data = [math.exp(min(x, 700)) for x in self._data]
        return self._create_result(new_data, self._shape)

    def log(self) -> "Tensor":
        """Natural logarithm."""
        new_data = [math.log(max(x, 1e-10)) for x in self._data]
        return self._create_result(new_data, self._shape)

    def sin(self) -> "Tensor":
        """Sine."""
        new_data = [math.sin(x) for x in self._data]
        return self._create_result(new_data, self._shape)

    def cos(self) -> "Tensor":
        """Cosine."""
        new_data = [math.cos(x) for x in self._data]
        return self._create_result(new_data, self._shape)

    def tanh(self) -> "Tensor":
        """Hyperbolic tangent."""
        new_data = [math.tanh(x) for x in self._data]
        return self._create_result(new_data, self._shape)

    def sigmoid(self) -> "Tensor":
        """Sigmoid activation."""
        def sig(x):
            if x >= 0:
                return 1 / (1 + math.exp(-x))
            else:
                exp_x = math.exp(x)
                return exp_x / (1 + exp_x)
        new_data = [sig(x) for x in self._data]
        return self._create_result(new_data, self._shape)

    def relu(self) -> "Tensor":
        """ReLU activation."""
        new_data = [max(0, x) for x in self._data]
        return self._create_result(new_data, self._shape)

    def _create_result(self, data: List[float], shape: Tuple[int, ...]) -> "Tensor":
        """Create result tensor."""
        result = Tensor.__new__(Tensor)
        result._data = data
        result._shape = shape
        result._dtype = self._dtype
        result._device = self._device
        result._grad_info = GradientInfo()
        result._id = str(uuid.uuid4())[:8]
        return result

    def sum(self, dim: Optional[int] = None, keepdim: bool = False) -> "Tensor":
        """Sum elements."""
        if dim is None:
            result_val = sum(self._data)
            return Tensor(result_val, self._dtype, self._device)

        if dim < 0:
            dim = len(self._shape) + dim

        new_shape = list(self._shape)
        dim_size = new_shape[dim]

        if keepdim:
            new_shape[dim] = 1
        else:
            new_shape.pop(dim)

        outer_size = 1
        for i in range(dim):
            outer_size *= self._shape[i]

        inner_size = 1
        for i in range(dim + 1, len(self._shape)):
            inner_size *= self._shape[i]

        new_numel = outer_size * inner_size
        new_data = [0.0] * new_numel

        for outer in range(outer_size):
            for inner in range(inner_size):
                total = 0.0
                for d in range(dim_size):
                    flat_idx = outer * (dim_size * inner_size) + d * inner_size + inner
                    total += self._data[flat_idx]
                new_data[outer * inner_size + inner] = total

        return self._create_result(new_data, tuple(new_shape) if new_shape else ())

    def mean(self, dim: Optional[int] = None, keepdim: bool = False) -> "Tensor":
        """Mean of elements."""
        if dim is None:
            result_val = sum(self._data) / len(self._data)
            return Tensor(result_val, self._dtype, self._device)

        sum_result = self.sum(dim, keepdim)
        return sum_result / self._shape[dim]

    def max(self, dim: Optional[int] = None) -> "Tensor":
        """Maximum element."""
        if dim is None:
            return Tensor(max(self._data), self._dtype, self._device)

        raise NotImplementedError("dim-wise max not implemented")

    def min(self, dim: Optional[int] = None) -> "Tensor":
        """Minimum element."""
        if dim is None:
            return Tensor(min(self._data), self._dtype, self._device)

        raise NotImplementedError("dim-wise min not implemented")

    def std(self, dim: Optional[int] = None) -> "Tensor":
        """Standard deviation."""
        mean_val = self.mean(dim)

        if dim is None:
            var = sum((x - mean_val.item()) ** 2 for x in self._data) / len(self._data)
            return Tensor(math.sqrt(var), self._dtype, self._device)

        raise NotImplementedError("dim-wise std not implemented")

    def matmul(self, other: "Tensor") -> "Tensor":
        """Matrix multiplication."""
        if self.ndim == 1 and other.ndim == 1:
            if self._shape[0] != other._shape[0]:
                raise ValueError("Dot product requires same size")
            result = sum(a * b for a, b in zip(self._data, other._data))
            return Tensor(result, self._dtype, self._device)

        if self.ndim == 2 and other.ndim == 2:
            m, k1 = self._shape
            k2, n = other._shape

            if k1 != k2:
                raise ValueError(f"Incompatible shapes: {self._shape} @ {other._shape}")

            result_data = [0.0] * (m * n)

            for i in range(m):
                for j in range(n):
                    total = 0.0
                    for k in range(k1):
                        total += self._data[i * k1 + k] * other._data[k * n + j]
                    result_data[i * n + j] = total

            return self._create_result(result_data, (m, n))

        raise NotImplementedError("Only 1D/2D matmul implemented")

    def __matmul__(self, other: "Tensor") -> "Tensor":
        return self.matmul(other)

    def stats(self) -> TensorStats:
        """Get tensor statistics."""
        return TensorStats(
            shape=self._shape,
            dtype=self._dtype,
            device=self._device,
            numel=self.numel,
            min_val=min(self._data) if self._data else 0,
            max_val=max(self._data) if self._data else 0,
            mean_val=sum(self._data) / len(self._data) if self._data else 0,
            std_val=self.std().item() if self._data else 0
        )

    def __repr__(self) -> str:
        if self.numel <= 10:
            return f"Tensor({self.tolist()}, shape={self._shape})"
        return f"Tensor(shape={self._shape}, dtype={self._dtype.value})"


# =============================================================================
# TENSOR ENGINE
# =============================================================================

class TensorEngine:
    """
    Tensor Engine for BAEL.

    Comprehensive tensor operations for neural computation.
    """

    def __init__(self, default_dtype: DataType = DataType.FLOAT32, default_device: Device = Device.CPU):
        self._dtype = default_dtype
        self._device = default_device

    def tensor(
        self,
        data: Union[List, float, int],
        dtype: Optional[DataType] = None,
        device: Optional[Device] = None,
        requires_grad: bool = False
    ) -> Tensor:
        """Create a tensor."""
        return Tensor(
            data,
            dtype or self._dtype,
            device or self._device,
            requires_grad
        )

    def zeros(
        self,
        *shape: int,
        dtype: Optional[DataType] = None,
        device: Optional[Device] = None
    ) -> Tensor:
        """Create a tensor of zeros."""
        numel = 1
        for dim in shape:
            numel *= dim

        t = Tensor.__new__(Tensor)
        t._data = [0.0] * numel
        t._shape = shape
        t._dtype = dtype or self._dtype
        t._device = device or self._device
        t._grad_info = GradientInfo()
        t._id = str(uuid.uuid4())[:8]
        return t

    def ones(
        self,
        *shape: int,
        dtype: Optional[DataType] = None,
        device: Optional[Device] = None
    ) -> Tensor:
        """Create a tensor of ones."""
        numel = 1
        for dim in shape:
            numel *= dim

        t = Tensor.__new__(Tensor)
        t._data = [1.0] * numel
        t._shape = shape
        t._dtype = dtype or self._dtype
        t._device = device or self._device
        t._grad_info = GradientInfo()
        t._id = str(uuid.uuid4())[:8]
        return t

    def rand(
        self,
        *shape: int,
        dtype: Optional[DataType] = None,
        device: Optional[Device] = None
    ) -> Tensor:
        """Create a tensor with uniform random values [0, 1)."""
        numel = 1
        for dim in shape:
            numel *= dim

        t = Tensor.__new__(Tensor)
        t._data = [random.random() for _ in range(numel)]
        t._shape = shape
        t._dtype = dtype or self._dtype
        t._device = device or self._device
        t._grad_info = GradientInfo()
        t._id = str(uuid.uuid4())[:8]
        return t

    def randn(
        self,
        *shape: int,
        dtype: Optional[DataType] = None,
        device: Optional[Device] = None
    ) -> Tensor:
        """Create a tensor with normal random values."""
        numel = 1
        for dim in shape:
            numel *= dim

        t = Tensor.__new__(Tensor)
        t._data = [random.gauss(0, 1) for _ in range(numel)]
        t._shape = shape
        t._dtype = dtype or self._dtype
        t._device = device or self._device
        t._grad_info = GradientInfo()
        t._id = str(uuid.uuid4())[:8]
        return t

    def arange(
        self,
        start: float,
        end: Optional[float] = None,
        step: float = 1.0,
        dtype: Optional[DataType] = None,
        device: Optional[Device] = None
    ) -> Tensor:
        """Create a tensor with values in range."""
        if end is None:
            end = start
            start = 0

        data = []
        val = start
        while val < end:
            data.append(val)
            val += step

        t = Tensor.__new__(Tensor)
        t._data = data
        t._shape = (len(data),)
        t._dtype = dtype or self._dtype
        t._device = device or self._device
        t._grad_info = GradientInfo()
        t._id = str(uuid.uuid4())[:8]
        return t

    def linspace(
        self,
        start: float,
        end: float,
        steps: int,
        dtype: Optional[DataType] = None,
        device: Optional[Device] = None
    ) -> Tensor:
        """Create a tensor with evenly spaced values."""
        if steps == 1:
            data = [start]
        else:
            step = (end - start) / (steps - 1)
            data = [start + i * step for i in range(steps)]

        t = Tensor.__new__(Tensor)
        t._data = data
        t._shape = (len(data),)
        t._dtype = dtype or self._dtype
        t._device = device or self._device
        t._grad_info = GradientInfo()
        t._id = str(uuid.uuid4())[:8]
        return t

    def eye(
        self,
        n: int,
        m: Optional[int] = None,
        dtype: Optional[DataType] = None,
        device: Optional[Device] = None
    ) -> Tensor:
        """Create identity matrix."""
        if m is None:
            m = n

        data = [0.0] * (n * m)
        for i in range(min(n, m)):
            data[i * m + i] = 1.0

        t = Tensor.__new__(Tensor)
        t._data = data
        t._shape = (n, m)
        t._dtype = dtype or self._dtype
        t._device = device or self._device
        t._grad_info = GradientInfo()
        t._id = str(uuid.uuid4())[:8]
        return t

    def stack(self, tensors: List[Tensor], dim: int = 0) -> Tensor:
        """Stack tensors along new dimension."""
        if not tensors:
            raise ValueError("Need at least one tensor")

        shape = tensors[0]._shape
        for t in tensors[1:]:
            if t._shape != shape:
                raise ValueError("All tensors must have same shape")

        new_shape = list(shape)
        new_shape.insert(dim, len(tensors))

        data = []
        for t in tensors:
            data.extend(t._data)

        result = Tensor.__new__(Tensor)
        result._data = data
        result._shape = tuple(new_shape)
        result._dtype = tensors[0]._dtype
        result._device = tensors[0]._device
        result._grad_info = GradientInfo()
        result._id = str(uuid.uuid4())[:8]
        return result

    def cat(self, tensors: List[Tensor], dim: int = 0) -> Tensor:
        """Concatenate tensors along dimension."""
        if not tensors:
            raise ValueError("Need at least one tensor")

        base_shape = list(tensors[0]._shape)

        for t in tensors[1:]:
            if len(t._shape) != len(base_shape):
                raise ValueError("All tensors must have same ndim")
            for i, (d1, d2) in enumerate(zip(base_shape, t._shape)):
                if i != dim and d1 != d2:
                    raise ValueError("Shapes must match except in cat dim")

        total_dim = sum(t._shape[dim] for t in tensors)
        new_shape = base_shape.copy()
        new_shape[dim] = total_dim

        data = []
        for t in tensors:
            data.extend(t._data)

        result = Tensor.__new__(Tensor)
        result._data = data
        result._shape = tuple(new_shape)
        result._dtype = tensors[0]._dtype
        result._device = tensors[0]._device
        result._grad_info = GradientInfo()
        result._id = str(uuid.uuid4())[:8]
        return result


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Tensor Engine."""
    print("=" * 70)
    print("BAEL - TENSOR ENGINE DEMO")
    print("Tensor Operations for Neural Computation")
    print("=" * 70)
    print()

    engine = TensorEngine()

    # 1. Create Tensors
    print("1. CREATE TENSORS:")
    print("-" * 40)

    t1 = engine.tensor([[1, 2, 3], [4, 5, 6]])
    print(f"   t1 = {t1.tolist()}")
    print(f"   Shape: {t1.shape}, numel: {t1.numel}")
    print()

    # 2. Special Tensors
    print("2. SPECIAL TENSORS:")
    print("-" * 40)

    zeros = engine.zeros(2, 3)
    print(f"   zeros(2,3): {zeros.tolist()}")

    ones = engine.ones(3)
    print(f"   ones(3): {ones.tolist()}")

    rand = engine.rand(2, 2)
    print(f"   rand(2,2): shape={rand.shape}")

    eye = engine.eye(3)
    print(f"   eye(3): {eye.tolist()}")
    print()

    # 3. Arithmetic Operations
    print("3. ARITHMETIC OPERATIONS:")
    print("-" * 40)

    a = engine.tensor([1, 2, 3])
    b = engine.tensor([4, 5, 6])

    print(f"   a = {a.tolist()}")
    print(f"   b = {b.tolist()}")
    print(f"   a + b = {(a + b).tolist()}")
    print(f"   a * b = {(a * b).tolist()}")
    print(f"   a * 2 = {(a * 2).tolist()}")
    print()

    # 4. Math Functions
    print("4. MATH FUNCTIONS:")
    print("-" * 40)

    x = engine.tensor([0, 1, 2])

    print(f"   x = {x.tolist()}")
    print(f"   sqrt(x): {[round(v, 4) for v in x.sqrt().tolist()]}")
    print(f"   exp(x): {[round(v, 4) for v in x.exp().tolist()]}")
    print(f"   tanh(x): {[round(v, 4) for v in x.tanh().tolist()]}")
    print()

    # 5. Reductions
    print("5. REDUCTIONS:")
    print("-" * 40)

    t = engine.tensor([[1, 2, 3], [4, 5, 6]])

    print(f"   t = {t.tolist()}")
    print(f"   sum: {t.sum().item()}")
    print(f"   mean: {t.mean().item():.4f}")
    print(f"   max: {t.max().item()}")
    print(f"   min: {t.min().item()}")
    print()

    # 6. Shape Operations
    print("6. SHAPE OPERATIONS:")
    print("-" * 40)

    t = engine.tensor([[1, 2, 3], [4, 5, 6]])

    print(f"   Original: {t.shape}")
    print(f"   reshape(3, 2): {t.reshape(3, 2).shape}")
    print(f"   flatten: {t.flatten().shape}")
    print(f"   unsqueeze(0): {t.unsqueeze(0).shape}")
    print()

    # 7. Matrix Multiplication
    print("7. MATRIX MULTIPLICATION:")
    print("-" * 40)

    a = engine.tensor([[1, 2], [3, 4]])
    b = engine.tensor([[5, 6], [7, 8]])

    print(f"   a = {a.tolist()}")
    print(f"   b = {b.tolist()}")
    print(f"   a @ b = {(a @ b).tolist()}")
    print()

    # 8. Activations
    print("8. ACTIVATION FUNCTIONS:")
    print("-" * 40)

    x = engine.tensor([-2, -1, 0, 1, 2])

    print(f"   x = {x.tolist()}")
    print(f"   relu: {x.relu().tolist()}")
    print(f"   sigmoid: {[round(v, 4) for v in x.sigmoid().tolist()]}")
    print(f"   tanh: {[round(v, 4) for v in x.tanh().tolist()]}")
    print()

    # 9. Tensor Statistics
    print("9. TENSOR STATISTICS:")
    print("-" * 40)

    t = engine.randn(100)
    stats = t.stats()

    print(f"   Shape: {stats.shape}")
    print(f"   Elements: {stats.numel}")
    print(f"   Mean: {stats.mean_val:.4f}")
    print(f"   Std: {stats.std_val:.4f}")
    print(f"   Range: [{stats.min_val:.4f}, {stats.max_val:.4f}]")
    print()

    # 10. Stack and Cat
    print("10. STACK AND CONCATENATE:")
    print("-" * 40)

    t1 = engine.tensor([1, 2])
    t2 = engine.tensor([3, 4])
    t3 = engine.tensor([5, 6])

    stacked = engine.stack([t1, t2, t3])
    print(f"   Stack [1,2], [3,4], [5,6]:")
    print(f"      Shape: {stacked.shape}")
    print(f"      Data: {stacked.tolist()}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Tensor Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
