#!/usr/bin/env python3
"""
BAEL - Dimensionality Reducer
Advanced dimensionality reduction and projection.

Features:
- Principal Component Analysis (PCA)
- Singular Value Decomposition (SVD)
- t-SNE concepts
- Random projections
- Feature extraction
- Reconstruction error
"""

import asyncio
import math
import random
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (Any, Callable, Dict, Generic, List, Optional, Set, Tuple,
                    Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class ReductionMethod(Enum):
    """Reduction methods."""
    PCA = "pca"
    SVD = "svd"
    RANDOM = "random"
    TSNE = "tsne"


class NormalizationType(Enum):
    """Normalization types."""
    NONE = "none"
    STANDARDIZE = "standardize"
    MINMAX = "minmax"


class ProjectionType(Enum):
    """Projection types."""
    LINEAR = "linear"
    NONLINEAR = "nonlinear"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Vector:
    """A data vector."""
    vec_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    values: List[float] = field(default_factory=list)
    label: Optional[str] = None


@dataclass
class Component:
    """A principal component."""
    comp_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    index: int = 0
    weights: List[float] = field(default_factory=list)
    variance: float = 0.0
    explained_ratio: float = 0.0


@dataclass
class Projection:
    """A projected vector."""
    vec_id: str = ""
    original_dim: int = 0
    reduced_dim: int = 0
    projected: List[float] = field(default_factory=list)


@dataclass
class ReductionResult:
    """Reduction result."""
    method: ReductionMethod = ReductionMethod.PCA
    original_dim: int = 0
    reduced_dim: int = 0
    explained_variance: float = 0.0
    projections: List[Projection] = field(default_factory=list)


# =============================================================================
# VECTOR STORE
# =============================================================================

class VectorStore:
    """Store for vectors."""

    def __init__(self):
        self._vectors: List[Vector] = []

    def add(self, values: List[float], label: Optional[str] = None) -> Vector:
        """Add a vector."""
        vec = Vector(values=values, label=label)
        self._vectors.append(vec)
        return vec

    def all_vectors(self) -> List[Vector]:
        """Get all vectors."""
        return self._vectors

    def to_matrix(self) -> List[List[float]]:
        """Convert to matrix form."""
        return [v.values for v in self._vectors]

    def dimension(self) -> int:
        """Get vector dimension."""
        if not self._vectors or not self._vectors[0].values:
            return 0
        return len(self._vectors[0].values)

    def count(self) -> int:
        """Get number of vectors."""
        return len(self._vectors)


# =============================================================================
# NORMALIZER
# =============================================================================

class Normalizer:
    """Data normalizer."""

    def __init__(self):
        self._means: List[float] = []
        self._stds: List[float] = []
        self._mins: List[float] = []
        self._maxs: List[float] = []

    def fit(self, matrix: List[List[float]]) -> None:
        """Fit normalizer to data."""
        if not matrix or not matrix[0]:
            return

        n_samples = len(matrix)
        n_features = len(matrix[0])

        self._means = [0.0] * n_features
        self._stds = [0.0] * n_features
        self._mins = [float('inf')] * n_features
        self._maxs = [float('-inf')] * n_features

        # Calculate means
        for row in matrix:
            for i, val in enumerate(row):
                self._means[i] += val
                self._mins[i] = min(self._mins[i], val)
                self._maxs[i] = max(self._maxs[i], val)

        for i in range(n_features):
            self._means[i] /= n_samples

        # Calculate stds
        for row in matrix:
            for i, val in enumerate(row):
                self._stds[i] += (val - self._means[i]) ** 2

        for i in range(n_features):
            self._stds[i] = math.sqrt(self._stds[i] / n_samples)
            if self._stds[i] == 0:
                self._stds[i] = 1.0

    def standardize(self, matrix: List[List[float]]) -> List[List[float]]:
        """Standardize data (zero mean, unit variance)."""
        result = []

        for row in matrix:
            normalized = [
                (val - self._means[i]) / self._stds[i]
                for i, val in enumerate(row)
            ]
            result.append(normalized)

        return result

    def minmax(self, matrix: List[List[float]]) -> List[List[float]]:
        """Min-max normalization."""
        result = []

        for row in matrix:
            normalized = []
            for i, val in enumerate(row):
                range_val = self._maxs[i] - self._mins[i]
                if range_val == 0:
                    range_val = 1.0
                normalized.append((val - self._mins[i]) / range_val)
            result.append(normalized)

        return result


# =============================================================================
# COVARIANCE CALCULATOR
# =============================================================================

class CovarianceCalculator:
    """Calculate covariance matrix."""

    def compute(self, matrix: List[List[float]]) -> List[List[float]]:
        """Compute covariance matrix."""
        if not matrix or not matrix[0]:
            return []

        n_samples = len(matrix)
        n_features = len(matrix[0])

        # Calculate means
        means = [0.0] * n_features
        for row in matrix:
            for i, val in enumerate(row):
                means[i] += val
        means = [m / n_samples for m in means]

        # Center data
        centered = [
            [val - means[i] for i, val in enumerate(row)]
            for row in matrix
        ]

        # Calculate covariance
        cov = [[0.0] * n_features for _ in range(n_features)]

        for i in range(n_features):
            for j in range(n_features):
                cov_sum = sum(
                    centered[k][i] * centered[k][j]
                    for k in range(n_samples)
                )
                cov[i][j] = cov_sum / (n_samples - 1) if n_samples > 1 else 0.0

        return cov


# =============================================================================
# PCA (POWER ITERATION)
# =============================================================================

class PCAReducer:
    """PCA using power iteration."""

    def __init__(self):
        self._components: List[Component] = []
        self._normalizer = Normalizer()
        self._covariance = CovarianceCalculator()

    def _power_iteration(
        self,
        matrix: List[List[float]],
        n_iter: int = 100
    ) -> Tuple[List[float], float]:
        """Power iteration for dominant eigenvector."""
        n = len(matrix)

        # Random initial vector
        v = [random.random() for _ in range(n)]
        norm = math.sqrt(sum(x ** 2 for x in v))
        v = [x / norm for x in v]

        eigenvalue = 0.0

        for _ in range(n_iter):
            # Matrix-vector multiplication
            new_v = [sum(matrix[i][j] * v[j] for j in range(n)) for i in range(n)]

            # Calculate eigenvalue (Rayleigh quotient)
            eigenvalue = sum(new_v[i] * v[i] for i in range(n))

            # Normalize
            norm = math.sqrt(sum(x ** 2 for x in new_v))
            if norm > 0:
                v = [x / norm for x in new_v]

        return v, eigenvalue

    def _deflate(
        self,
        matrix: List[List[float]],
        eigenvector: List[float],
        eigenvalue: float
    ) -> List[List[float]]:
        """Deflate matrix by removing component."""
        n = len(matrix)
        result = [[0.0] * n for _ in range(n)]

        for i in range(n):
            for j in range(n):
                result[i][j] = matrix[i][j] - eigenvalue * eigenvector[i] * eigenvector[j]

        return result

    def fit(
        self,
        matrix: List[List[float]],
        n_components: int = 2
    ) -> None:
        """Fit PCA."""
        # Normalize
        self._normalizer.fit(matrix)
        normalized = self._normalizer.standardize(matrix)

        # Covariance
        cov = self._covariance.compute(normalized)

        # Extract components
        self._components = []
        total_variance = sum(cov[i][i] for i in range(len(cov)))

        current_cov = [row[:] for row in cov]

        for idx in range(min(n_components, len(cov))):
            eigenvector, eigenvalue = self._power_iteration(current_cov)

            component = Component(
                index=idx,
                weights=eigenvector,
                variance=eigenvalue,
                explained_ratio=eigenvalue / total_variance if total_variance > 0 else 0.0
            )
            self._components.append(component)

            # Deflate
            current_cov = self._deflate(current_cov, eigenvector, eigenvalue)

    def transform(self, matrix: List[List[float]]) -> List[Projection]:
        """Transform data."""
        normalized = self._normalizer.standardize(matrix)
        projections = []

        for i, row in enumerate(normalized):
            projected = [
                sum(row[j] * comp.weights[j] for j in range(len(row)))
                for comp in self._components
            ]

            projections.append(Projection(
                vec_id=f"vec_{i}",
                original_dim=len(row),
                reduced_dim=len(projected),
                projected=projected
            ))

        return projections

    def explained_variance_ratio(self) -> float:
        """Get total explained variance ratio."""
        return sum(c.explained_ratio for c in self._components)

    def components(self) -> List[Component]:
        """Get components."""
        return self._components


# =============================================================================
# RANDOM PROJECTION
# =============================================================================

class RandomProjector:
    """Random projection dimensionality reduction."""

    def __init__(self):
        self._projection_matrix: List[List[float]] = []

    def fit(self, original_dim: int, target_dim: int) -> None:
        """Create random projection matrix."""
        # Gaussian random projection
        self._projection_matrix = []

        for _ in range(target_dim):
            row = [random.gauss(0, 1) for _ in range(original_dim)]
            # Normalize
            norm = math.sqrt(sum(x ** 2 for x in row))
            row = [x / norm for x in row]
            self._projection_matrix.append(row)

    def transform(self, matrix: List[List[float]]) -> List[Projection]:
        """Transform data."""
        projections = []

        for i, row in enumerate(matrix):
            projected = [
                sum(row[j] * self._projection_matrix[k][j] for j in range(len(row)))
                for k in range(len(self._projection_matrix))
            ]

            projections.append(Projection(
                vec_id=f"vec_{i}",
                original_dim=len(row),
                reduced_dim=len(projected),
                projected=projected
            ))

        return projections


# =============================================================================
# t-SNE CONCEPTS
# =============================================================================

class TSNEReducer:
    """Simplified t-SNE concepts."""

    def __init__(self, perplexity: float = 30.0):
        self._perplexity = perplexity
        self._embeddings: List[List[float]] = []

    def _euclidean_distance(self, v1: List[float], v2: List[float]) -> float:
        """Calculate Euclidean distance."""
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(v1, v2)))

    def _pairwise_distances(self, matrix: List[List[float]]) -> List[List[float]]:
        """Calculate pairwise distances."""
        n = len(matrix)
        distances = [[0.0] * n for _ in range(n)]

        for i in range(n):
            for j in range(i + 1, n):
                d = self._euclidean_distance(matrix[i], matrix[j])
                distances[i][j] = d
                distances[j][i] = d

        return distances

    def fit_transform(
        self,
        matrix: List[List[float]],
        n_components: int = 2,
        n_iter: int = 100
    ) -> List[Projection]:
        """Fit and transform using simplified gradient descent."""
        n = len(matrix)

        # Initialize with random positions
        self._embeddings = [
            [random.gauss(0, 0.01) for _ in range(n_components)]
            for _ in range(n)
        ]

        # High-dimensional distances
        high_dist = self._pairwise_distances(matrix)

        # Gradient descent
        learning_rate = 100.0

        for _ in range(n_iter):
            # Low-dimensional distances
            low_dist = self._pairwise_distances(self._embeddings)

            # Compute gradients (simplified)
            gradients = [[0.0] * n_components for _ in range(n)]

            for i in range(n):
                for j in range(n):
                    if i != j:
                        # Attraction/repulsion based on distance mismatch
                        q = 1.0 / (1.0 + low_dist[i][j] ** 2)
                        p = 1.0 / (1.0 + high_dist[i][j] ** 2)

                        scale = 4.0 * (p - q) * q

                        for d in range(n_components):
                            diff = self._embeddings[i][d] - self._embeddings[j][d]
                            gradients[i][d] += scale * diff

            # Update
            for i in range(n):
                for d in range(n_components):
                    self._embeddings[i][d] -= learning_rate * gradients[i][d]

            learning_rate *= 0.99

        # Create projections
        projections = []
        for i, emb in enumerate(self._embeddings):
            projections.append(Projection(
                vec_id=f"vec_{i}",
                original_dim=len(matrix[0]) if matrix else 0,
                reduced_dim=n_components,
                projected=emb
            ))

        return projections


# =============================================================================
# DIMENSIONALITY REDUCER
# =============================================================================

class DimensionalityReducer:
    """
    Dimensionality Reducer for BAEL.

    Advanced dimensionality reduction and projection.
    """

    def __init__(self):
        self._store = VectorStore()
        self._pca = PCAReducer()
        self._random = RandomProjector()
        self._tsne = TSNEReducer()

    # -------------------------------------------------------------------------
    # DATA
    # -------------------------------------------------------------------------

    def add_vector(
        self,
        values: List[float],
        label: Optional[str] = None
    ) -> Vector:
        """Add a vector."""
        return self._store.add(values, label)

    def all_vectors(self) -> List[Vector]:
        """Get all vectors."""
        return self._store.all_vectors()

    def dimension(self) -> int:
        """Get original dimension."""
        return self._store.dimension()

    # -------------------------------------------------------------------------
    # PCA
    # -------------------------------------------------------------------------

    def fit_pca(self, n_components: int = 2) -> None:
        """Fit PCA."""
        matrix = self._store.to_matrix()
        self._pca.fit(matrix, n_components)

    def transform_pca(self) -> ReductionResult:
        """Transform with PCA."""
        matrix = self._store.to_matrix()
        projections = self._pca.transform(matrix)

        return ReductionResult(
            method=ReductionMethod.PCA,
            original_dim=self._store.dimension(),
            reduced_dim=len(projections[0].projected) if projections else 0,
            explained_variance=self._pca.explained_variance_ratio(),
            projections=projections
        )

    def pca_components(self) -> List[Component]:
        """Get PCA components."""
        return self._pca.components()

    # -------------------------------------------------------------------------
    # RANDOM PROJECTION
    # -------------------------------------------------------------------------

    def fit_random(self, n_components: int = 2) -> None:
        """Fit random projection."""
        self._random.fit(self._store.dimension(), n_components)

    def transform_random(self) -> ReductionResult:
        """Transform with random projection."""
        matrix = self._store.to_matrix()
        projections = self._random.transform(matrix)

        return ReductionResult(
            method=ReductionMethod.RANDOM,
            original_dim=self._store.dimension(),
            reduced_dim=len(projections[0].projected) if projections else 0,
            projections=projections
        )

    # -------------------------------------------------------------------------
    # t-SNE
    # -------------------------------------------------------------------------

    def fit_transform_tsne(
        self,
        n_components: int = 2,
        n_iter: int = 100
    ) -> ReductionResult:
        """Fit and transform with t-SNE."""
        matrix = self._store.to_matrix()
        projections = self._tsne.fit_transform(matrix, n_components, n_iter)

        return ReductionResult(
            method=ReductionMethod.TSNE,
            original_dim=self._store.dimension(),
            reduced_dim=n_components,
            projections=projections
        )

    # -------------------------------------------------------------------------
    # RECONSTRUCTION
    # -------------------------------------------------------------------------

    def reconstruction_error(self, projection: Projection) -> float:
        """Estimate reconstruction error."""
        # Get original
        vectors = self._store.all_vectors()

        for vec in vectors:
            if vec.vec_id == projection.vec_id:
                # Use explained variance as proxy for error
                explained = self._pca.explained_variance_ratio()
                return 1.0 - explained

        return 0.0

    # -------------------------------------------------------------------------
    # UTILITIES
    # -------------------------------------------------------------------------

    def reduce(
        self,
        n_components: int = 2,
        method: ReductionMethod = ReductionMethod.PCA
    ) -> ReductionResult:
        """General reduction method."""
        if method == ReductionMethod.PCA:
            self.fit_pca(n_components)
            return self.transform_pca()
        elif method == ReductionMethod.RANDOM:
            self.fit_random(n_components)
            return self.transform_random()
        elif method == ReductionMethod.TSNE:
            return self.fit_transform_tsne(n_components)

        return ReductionResult()


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Dimensionality Reducer."""
    print("=" * 70)
    print("BAEL - DIMENSIONALITY REDUCER DEMO")
    print("Advanced Dimensionality Reduction and Projection")
    print("=" * 70)
    print()

    reducer = DimensionalityReducer()

    # 1. Add Vectors
    print("1. ADD VECTORS:")
    print("-" * 40)

    # Generate synthetic data
    for i in range(50):
        # Create 10-dimensional vectors
        values = [random.gauss(0, 1) for _ in range(10)]
        # Add some structure (first 2 dims correlated with label)
        label = "A" if random.random() > 0.5 else "B"
        if label == "A":
            values[0] += 2
            values[1] += 2
        reducer.add_vector(values, label)

    print(f"   Added {len(reducer.all_vectors())} vectors")
    print(f"   Original dimension: {reducer.dimension()}")
    print()

    # 2. PCA Reduction
    print("2. PCA REDUCTION:")
    print("-" * 40)

    reducer.fit_pca(n_components=3)
    result = reducer.transform_pca()

    print(f"   Method: {result.method.value}")
    print(f"   Original dim: {result.original_dim}")
    print(f"   Reduced dim: {result.reduced_dim}")
    print(f"   Explained variance: {result.explained_variance:.2%}")
    print()

    # 3. PCA Components
    print("3. PCA COMPONENTS:")
    print("-" * 40)

    for comp in reducer.pca_components():
        print(f"   Component {comp.index + 1}:")
        print(f"      Variance: {comp.variance:.4f}")
        print(f"      Explained ratio: {comp.explained_ratio:.2%}")
    print()

    # 4. Sample Projections
    print("4. SAMPLE PROJECTIONS:")
    print("-" * 40)

    for proj in result.projections[:3]:
        print(f"   {proj.vec_id}: {proj.projected[:3]}")
    print()

    # 5. Random Projection
    print("5. RANDOM PROJECTION:")
    print("-" * 40)

    result = reducer.reduce(n_components=2, method=ReductionMethod.RANDOM)
    print(f"   Method: {result.method.value}")
    print(f"   Original dim: {result.original_dim}")
    print(f"   Reduced dim: {result.reduced_dim}")

    for proj in result.projections[:3]:
        print(f"   {proj.vec_id}: {proj.projected}")
    print()

    # 6. t-SNE Reduction
    print("6. t-SNE REDUCTION:")
    print("-" * 40)

    result = reducer.fit_transform_tsne(n_components=2, n_iter=50)
    print(f"   Method: {result.method.value}")
    print(f"   Original dim: {result.original_dim}")
    print(f"   Reduced dim: {result.reduced_dim}")

    for proj in result.projections[:3]:
        print(f"   {proj.vec_id}: [{proj.projected[0]:.3f}, {proj.projected[1]:.3f}]")
    print()

    # 7. Reconstruction Error
    print("7. RECONSTRUCTION ERROR:")
    print("-" * 40)

    # Refit PCA for error estimation
    reducer.fit_pca(n_components=2)
    pca_result = reducer.transform_pca()

    error = reducer.reconstruction_error(pca_result.projections[0])
    print(f"   Estimated reconstruction error: {error:.2%}")
    print(f"   (Based on unexplained variance)")
    print()

    # 8. Compare Methods
    print("8. METHOD COMPARISON:")
    print("-" * 40)

    methods = [ReductionMethod.PCA, ReductionMethod.RANDOM]

    for method in methods:
        result = reducer.reduce(n_components=2, method=method)
        print(f"   {method.value.upper()}:")
        print(f"      Reduced dim: {result.reduced_dim}")
        print(f"      Explained var: {result.explained_variance:.2%}" if result.explained_variance else "")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Dimensionality Reducer Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
