#!/usr/bin/env python3
"""
BAEL - Clustering Engine
Advanced clustering and unsupervised learning.

Features:
- K-Means clustering
- Hierarchical clustering
- DBSCAN density clustering
- Cluster validation metrics
- Cluster assignment
- Centroid management
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

class ClusteringMethod(Enum):
    """Clustering methods."""
    KMEANS = "kmeans"
    HIERARCHICAL = "hierarchical"
    DBSCAN = "dbscan"


class LinkageType(Enum):
    """Hierarchical linkage types."""
    SINGLE = "single"
    COMPLETE = "complete"
    AVERAGE = "average"


class ClusterStatus(Enum):
    """Cluster status."""
    ACTIVE = "active"
    MERGED = "merged"
    EMPTY = "empty"


class InitMethod(Enum):
    """Initialization methods."""
    RANDOM = "random"
    KMEANS_PP = "kmeans_pp"
    FORGY = "forgy"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Point:
    """A data point."""
    point_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    values: List[float] = field(default_factory=list)
    cluster_id: Optional[str] = None
    label: Optional[str] = None


@dataclass
class Centroid:
    """A cluster centroid."""
    centroid_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    values: List[float] = field(default_factory=list)


@dataclass
class Cluster:
    """A cluster."""
    cluster_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    centroid: Optional[Centroid] = None
    points: List[str] = field(default_factory=list)
    status: ClusterStatus = ClusterStatus.ACTIVE


@dataclass
class ClusteringResult:
    """Clustering result."""
    method: ClusteringMethod = ClusteringMethod.KMEANS
    n_clusters: int = 0
    clusters: List[Cluster] = field(default_factory=list)
    inertia: float = 0.0
    iterations: int = 0


@dataclass
class ValidationMetrics:
    """Cluster validation metrics."""
    silhouette: float = 0.0
    inertia: float = 0.0
    davies_bouldin: float = 0.0


# =============================================================================
# DISTANCE CALCULATOR
# =============================================================================

class DistanceCalculator:
    """Calculate distances between points."""

    def euclidean(self, p1: List[float], p2: List[float]) -> float:
        """Euclidean distance."""
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(p1, p2)))

    def manhattan(self, p1: List[float], p2: List[float]) -> float:
        """Manhattan distance."""
        return sum(abs(a - b) for a, b in zip(p1, p2))

    def cosine(self, p1: List[float], p2: List[float]) -> float:
        """Cosine distance."""
        dot = sum(a * b for a, b in zip(p1, p2))
        norm1 = math.sqrt(sum(a ** 2 for a in p1))
        norm2 = math.sqrt(sum(b ** 2 for b in p2))

        if norm1 == 0 or norm2 == 0:
            return 1.0

        return 1.0 - (dot / (norm1 * norm2))


# =============================================================================
# POINT STORE
# =============================================================================

class PointStore:
    """Store for data points."""

    def __init__(self):
        self._points: Dict[str, Point] = {}

    def add(
        self,
        values: List[float],
        label: Optional[str] = None
    ) -> Point:
        """Add a point."""
        point = Point(values=values, label=label)
        self._points[point.point_id] = point
        return point

    def get(self, point_id: str) -> Optional[Point]:
        """Get a point."""
        return self._points.get(point_id)

    def all_points(self) -> List[Point]:
        """Get all points."""
        return list(self._points.values())

    def assign_cluster(self, point_id: str, cluster_id: str) -> None:
        """Assign point to cluster."""
        point = self._points.get(point_id)
        if point:
            point.cluster_id = cluster_id

    def dimension(self) -> int:
        """Get point dimension."""
        points = self.all_points()
        if not points or not points[0].values:
            return 0
        return len(points[0].values)


# =============================================================================
# K-MEANS CLUSTERER
# =============================================================================

class KMeansClusterer:
    """K-Means clustering."""

    def __init__(self):
        self._distance = DistanceCalculator()
        self._centroids: List[Centroid] = []

    def _init_centroids(
        self,
        points: List[Point],
        k: int,
        method: InitMethod = InitMethod.KMEANS_PP
    ) -> List[Centroid]:
        """Initialize centroids."""
        if method == InitMethod.RANDOM:
            return self._init_random(points, k)
        elif method == InitMethod.KMEANS_PP:
            return self._init_kmeans_pp(points, k)
        elif method == InitMethod.FORGY:
            return self._init_forgy(points, k)
        return []

    def _init_random(self, points: List[Point], k: int) -> List[Centroid]:
        """Random initialization."""
        dim = len(points[0].values) if points else 0

        # Find ranges
        mins = [float('inf')] * dim
        maxs = [float('-inf')] * dim

        for p in points:
            for i, v in enumerate(p.values):
                mins[i] = min(mins[i], v)
                maxs[i] = max(maxs[i], v)

        centroids = []
        for _ in range(k):
            values = [random.uniform(mins[i], maxs[i]) for i in range(dim)]
            centroids.append(Centroid(values=values))

        return centroids

    def _init_forgy(self, points: List[Point], k: int) -> List[Centroid]:
        """Forgy initialization (random samples)."""
        samples = random.sample(points, min(k, len(points)))
        return [Centroid(values=p.values[:]) for p in samples]

    def _init_kmeans_pp(self, points: List[Point], k: int) -> List[Centroid]:
        """K-Means++ initialization."""
        centroids = []

        # First centroid: random
        first = random.choice(points)
        centroids.append(Centroid(values=first.values[:]))

        # Remaining centroids
        for _ in range(k - 1):
            # Calculate distances to nearest centroid
            distances = []
            for p in points:
                min_dist = float('inf')
                for c in centroids:
                    d = self._distance.euclidean(p.values, c.values)
                    min_dist = min(min_dist, d)
                distances.append(min_dist ** 2)

            # Weighted random selection
            total = sum(distances)
            if total == 0:
                r = random.choice(range(len(points)))
            else:
                r = random.random() * total
                cumsum = 0
                for i, d in enumerate(distances):
                    cumsum += d
                    if cumsum >= r:
                        break
                r = i

            centroids.append(Centroid(values=points[r].values[:]))

        return centroids

    def _assign_clusters(
        self,
        points: List[Point],
        centroids: List[Centroid]
    ) -> Dict[str, List[str]]:
        """Assign points to nearest centroids."""
        assignments: Dict[str, List[str]] = {c.centroid_id: [] for c in centroids}

        for point in points:
            min_dist = float('inf')
            nearest = centroids[0].centroid_id

            for centroid in centroids:
                d = self._distance.euclidean(point.values, centroid.values)
                if d < min_dist:
                    min_dist = d
                    nearest = centroid.centroid_id

            assignments[nearest].append(point.point_id)
            point.cluster_id = nearest

        return assignments

    def _update_centroids(
        self,
        points: List[Point],
        centroids: List[Centroid],
        assignments: Dict[str, List[str]]
    ) -> bool:
        """Update centroids. Returns True if changed."""
        changed = False
        point_map = {p.point_id: p for p in points}

        for centroid in centroids:
            point_ids = assignments.get(centroid.centroid_id, [])

            if not point_ids:
                continue

            # Calculate mean
            dim = len(centroid.values)
            new_values = [0.0] * dim

            for pid in point_ids:
                p = point_map[pid]
                for i, v in enumerate(p.values):
                    new_values[i] += v

            n = len(point_ids)
            new_values = [v / n for v in new_values]

            # Check if changed
            if new_values != centroid.values:
                changed = True
                centroid.values = new_values

        return changed

    def _calculate_inertia(
        self,
        points: List[Point],
        centroids: List[Centroid]
    ) -> float:
        """Calculate inertia (sum of squared distances)."""
        centroid_map = {c.centroid_id: c for c in centroids}
        inertia = 0.0

        for point in points:
            if point.cluster_id and point.cluster_id in centroid_map:
                centroid = centroid_map[point.cluster_id]
                d = self._distance.euclidean(point.values, centroid.values)
                inertia += d ** 2

        return inertia

    def fit(
        self,
        points: List[Point],
        k: int = 3,
        max_iter: int = 100,
        init: InitMethod = InitMethod.KMEANS_PP
    ) -> ClusteringResult:
        """Fit K-Means."""
        if not points:
            return ClusteringResult()

        # Initialize
        self._centroids = self._init_centroids(points, k, init)

        iterations = 0
        for _ in range(max_iter):
            iterations += 1

            # Assign
            assignments = self._assign_clusters(points, self._centroids)

            # Update
            changed = self._update_centroids(points, self._centroids, assignments)

            if not changed:
                break

        # Create clusters
        clusters = []
        for centroid in self._centroids:
            cluster = Cluster(
                cluster_id=centroid.centroid_id,
                centroid=centroid,
                points=[
                    p.point_id for p in points
                    if p.cluster_id == centroid.centroid_id
                ]
            )
            clusters.append(cluster)

        inertia = self._calculate_inertia(points, self._centroids)

        return ClusteringResult(
            method=ClusteringMethod.KMEANS,
            n_clusters=k,
            clusters=clusters,
            inertia=inertia,
            iterations=iterations
        )

    def predict(self, point: Point) -> str:
        """Predict cluster for new point."""
        min_dist = float('inf')
        nearest = ""

        for centroid in self._centroids:
            d = self._distance.euclidean(point.values, centroid.values)
            if d < min_dist:
                min_dist = d
                nearest = centroid.centroid_id

        return nearest


# =============================================================================
# HIERARCHICAL CLUSTERER
# =============================================================================

class HierarchicalClusterer:
    """Hierarchical (agglomerative) clustering."""

    def __init__(self, linkage: LinkageType = LinkageType.AVERAGE):
        self._linkage = linkage
        self._distance = DistanceCalculator()

    def _cluster_distance(
        self,
        cluster1: List[Point],
        cluster2: List[Point]
    ) -> float:
        """Calculate distance between clusters."""
        if not cluster1 or not cluster2:
            return float('inf')

        if self._linkage == LinkageType.SINGLE:
            return min(
                self._distance.euclidean(p1.values, p2.values)
                for p1 in cluster1 for p2 in cluster2
            )
        elif self._linkage == LinkageType.COMPLETE:
            return max(
                self._distance.euclidean(p1.values, p2.values)
                for p1 in cluster1 for p2 in cluster2
            )
        elif self._linkage == LinkageType.AVERAGE:
            total = sum(
                self._distance.euclidean(p1.values, p2.values)
                for p1 in cluster1 for p2 in cluster2
            )
            return total / (len(cluster1) * len(cluster2))

        return float('inf')

    def fit(
        self,
        points: List[Point],
        n_clusters: int = 3
    ) -> ClusteringResult:
        """Fit hierarchical clustering."""
        if not points:
            return ClusteringResult()

        # Start with each point as its own cluster
        clusters: Dict[str, List[Point]] = {}
        for p in points:
            clusters[p.point_id] = [p]

        iterations = 0

        while len(clusters) > n_clusters:
            iterations += 1

            # Find closest pair
            min_dist = float('inf')
            merge_pair = None

            cluster_ids = list(clusters.keys())
            for i, c1 in enumerate(cluster_ids):
                for c2 in cluster_ids[i + 1:]:
                    d = self._cluster_distance(clusters[c1], clusters[c2])
                    if d < min_dist:
                        min_dist = d
                        merge_pair = (c1, c2)

            if merge_pair:
                c1, c2 = merge_pair
                # Merge
                clusters[c1].extend(clusters[c2])
                del clusters[c2]

        # Create result clusters
        result_clusters = []
        for cluster_id, cluster_points in clusters.items():
            # Calculate centroid
            dim = len(cluster_points[0].values)
            centroid_values = [
                sum(p.values[i] for p in cluster_points) / len(cluster_points)
                for i in range(dim)
            ]

            cluster = Cluster(
                cluster_id=cluster_id,
                centroid=Centroid(values=centroid_values),
                points=[p.point_id for p in cluster_points]
            )
            result_clusters.append(cluster)

            # Update point assignments
            for p in cluster_points:
                p.cluster_id = cluster_id

        return ClusteringResult(
            method=ClusteringMethod.HIERARCHICAL,
            n_clusters=len(result_clusters),
            clusters=result_clusters,
            iterations=iterations
        )


# =============================================================================
# DBSCAN CLUSTERER
# =============================================================================

class DBSCANClusterer:
    """DBSCAN density-based clustering."""

    def __init__(self, eps: float = 0.5, min_samples: int = 5):
        self._eps = eps
        self._min_samples = min_samples
        self._distance = DistanceCalculator()

    def _neighbors(self, point: Point, points: List[Point]) -> List[Point]:
        """Find neighbors within epsilon."""
        return [
            p for p in points
            if self._distance.euclidean(point.values, p.values) <= self._eps
        ]

    def fit(self, points: List[Point]) -> ClusteringResult:
        """Fit DBSCAN."""
        if not points:
            return ClusteringResult()

        visited = set()
        noise = set()
        clusters: Dict[str, List[Point]] = {}
        current_cluster_id = ""
        cluster_count = 0

        for point in points:
            if point.point_id in visited:
                continue

            visited.add(point.point_id)
            neighbors = self._neighbors(point, points)

            if len(neighbors) < self._min_samples:
                noise.add(point.point_id)
                continue

            # Start new cluster
            cluster_count += 1
            current_cluster_id = f"cluster_{cluster_count}"
            clusters[current_cluster_id] = [point]
            point.cluster_id = current_cluster_id

            # Expand cluster
            seed_set = [n for n in neighbors if n.point_id != point.point_id]

            while seed_set:
                q = seed_set.pop(0)

                if q.point_id in noise:
                    noise.remove(q.point_id)
                    clusters[current_cluster_id].append(q)
                    q.cluster_id = current_cluster_id

                if q.point_id in visited:
                    continue

                visited.add(q.point_id)
                clusters[current_cluster_id].append(q)
                q.cluster_id = current_cluster_id

                q_neighbors = self._neighbors(q, points)
                if len(q_neighbors) >= self._min_samples:
                    seed_set.extend([
                        n for n in q_neighbors
                        if n.point_id not in visited
                    ])

        # Create result clusters
        result_clusters = []
        for cluster_id, cluster_points in clusters.items():
            # Calculate centroid
            dim = len(cluster_points[0].values) if cluster_points else 0
            if dim > 0:
                centroid_values = [
                    sum(p.values[i] for p in cluster_points) / len(cluster_points)
                    for i in range(dim)
                ]
            else:
                centroid_values = []

            cluster = Cluster(
                cluster_id=cluster_id,
                centroid=Centroid(values=centroid_values),
                points=[p.point_id for p in cluster_points]
            )
            result_clusters.append(cluster)

        return ClusteringResult(
            method=ClusteringMethod.DBSCAN,
            n_clusters=len(result_clusters),
            clusters=result_clusters
        )


# =============================================================================
# CLUSTER VALIDATOR
# =============================================================================

class ClusterValidator:
    """Validate clustering quality."""

    def __init__(self):
        self._distance = DistanceCalculator()

    def silhouette_score(
        self,
        points: List[Point],
        clusters: List[Cluster]
    ) -> float:
        """Calculate silhouette score."""
        if len(clusters) < 2:
            return 0.0

        point_map = {p.point_id: p for p in points}
        cluster_map = {c.cluster_id: c for c in clusters}

        silhouettes = []

        for point in points:
            if not point.cluster_id:
                continue

            # Get own cluster points
            own_cluster = cluster_map.get(point.cluster_id)
            if not own_cluster or len(own_cluster.points) < 2:
                continue

            # Calculate a (mean distance to own cluster)
            own_points = [
                point_map[pid] for pid in own_cluster.points
                if pid != point.point_id
            ]

            if not own_points:
                continue

            a = sum(
                self._distance.euclidean(point.values, p.values)
                for p in own_points
            ) / len(own_points)

            # Calculate b (min mean distance to other clusters)
            b = float('inf')
            for cluster in clusters:
                if cluster.cluster_id == point.cluster_id:
                    continue

                other_points = [point_map[pid] for pid in cluster.points]
                if not other_points:
                    continue

                mean_dist = sum(
                    self._distance.euclidean(point.values, p.values)
                    for p in other_points
                ) / len(other_points)

                b = min(b, mean_dist)

            if b == float('inf'):
                continue

            # Silhouette coefficient
            s = (b - a) / max(a, b) if max(a, b) > 0 else 0
            silhouettes.append(s)

        return sum(silhouettes) / len(silhouettes) if silhouettes else 0.0

    def inertia(
        self,
        points: List[Point],
        clusters: List[Cluster]
    ) -> float:
        """Calculate inertia."""
        point_map = {p.point_id: p for p in points}
        inertia = 0.0

        for cluster in clusters:
            if not cluster.centroid:
                continue

            for pid in cluster.points:
                p = point_map.get(pid)
                if p:
                    d = self._distance.euclidean(p.values, cluster.centroid.values)
                    inertia += d ** 2

        return inertia


# =============================================================================
# CLUSTERING ENGINE
# =============================================================================

class ClusteringEngine:
    """
    Clustering Engine for BAEL.

    Advanced clustering and unsupervised learning.
    """

    def __init__(self):
        self._store = PointStore()
        self._kmeans = KMeansClusterer()
        self._hierarchical = HierarchicalClusterer()
        self._dbscan = DBSCANClusterer()
        self._validator = ClusterValidator()
        self._result: Optional[ClusteringResult] = None

    # -------------------------------------------------------------------------
    # DATA
    # -------------------------------------------------------------------------

    def add_point(
        self,
        values: List[float],
        label: Optional[str] = None
    ) -> Point:
        """Add a data point."""
        return self._store.add(values, label)

    def all_points(self) -> List[Point]:
        """Get all points."""
        return self._store.all_points()

    # -------------------------------------------------------------------------
    # CLUSTERING
    # -------------------------------------------------------------------------

    def kmeans(
        self,
        k: int = 3,
        max_iter: int = 100,
        init: InitMethod = InitMethod.KMEANS_PP
    ) -> ClusteringResult:
        """Run K-Means clustering."""
        points = self._store.all_points()
        self._result = self._kmeans.fit(points, k, max_iter, init)
        return self._result

    def hierarchical(
        self,
        n_clusters: int = 3,
        linkage: LinkageType = LinkageType.AVERAGE
    ) -> ClusteringResult:
        """Run hierarchical clustering."""
        self._hierarchical = HierarchicalClusterer(linkage)
        points = self._store.all_points()
        self._result = self._hierarchical.fit(points, n_clusters)
        return self._result

    def dbscan(
        self,
        eps: float = 0.5,
        min_samples: int = 5
    ) -> ClusteringResult:
        """Run DBSCAN clustering."""
        self._dbscan = DBSCANClusterer(eps, min_samples)
        points = self._store.all_points()
        self._result = self._dbscan.fit(points)
        return self._result

    # -------------------------------------------------------------------------
    # PREDICTION
    # -------------------------------------------------------------------------

    def predict(self, values: List[float]) -> str:
        """Predict cluster for new point."""
        point = Point(values=values)
        return self._kmeans.predict(point)

    # -------------------------------------------------------------------------
    # VALIDATION
    # -------------------------------------------------------------------------

    def validate(self) -> ValidationMetrics:
        """Validate current clustering."""
        if not self._result:
            return ValidationMetrics()

        points = self._store.all_points()

        return ValidationMetrics(
            silhouette=self._validator.silhouette_score(
                points, self._result.clusters
            ),
            inertia=self._validator.inertia(
                points, self._result.clusters
            )
        )

    # -------------------------------------------------------------------------
    # UTILITIES
    # -------------------------------------------------------------------------

    def elbow_method(
        self,
        k_range: range = range(1, 11)
    ) -> Dict[int, float]:
        """Elbow method for optimal k."""
        results = {}
        points = self._store.all_points()

        for k in k_range:
            result = self._kmeans.fit(points, k)
            results[k] = result.inertia

        return results


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Clustering Engine."""
    print("=" * 70)
    print("BAEL - CLUSTERING ENGINE DEMO")
    print("Advanced Clustering and Unsupervised Learning")
    print("=" * 70)
    print()

    engine = ClusteringEngine()

    # 1. Add Points
    print("1. ADD DATA POINTS:")
    print("-" * 40)

    # Generate synthetic clusters
    clusters_data = [
        (0, 0),
        (5, 5),
        (10, 0)
    ]

    for cx, cy in clusters_data:
        for _ in range(20):
            x = cx + random.gauss(0, 0.5)
            y = cy + random.gauss(0, 0.5)
            engine.add_point([x, y])

    print(f"   Added {len(engine.all_points())} points in 3 clusters")
    print()

    # 2. K-Means Clustering
    print("2. K-MEANS CLUSTERING:")
    print("-" * 40)

    result = engine.kmeans(k=3, max_iter=100)

    print(f"   Method: {result.method.value}")
    print(f"   Clusters: {result.n_clusters}")
    print(f"   Iterations: {result.iterations}")
    print(f"   Inertia: {result.inertia:.2f}")

    for cluster in result.clusters:
        if cluster.centroid:
            print(f"   Cluster {cluster.cluster_id[:8]}: {len(cluster.points)} points")
            print(f"      Centroid: [{cluster.centroid.values[0]:.2f}, {cluster.centroid.values[1]:.2f}]")
    print()

    # 3. Validate Clustering
    print("3. VALIDATE CLUSTERING:")
    print("-" * 40)

    metrics = engine.validate()
    print(f"   Silhouette score: {metrics.silhouette:.3f}")
    print(f"   Inertia: {metrics.inertia:.2f}")
    print()

    # 4. Elbow Method
    print("4. ELBOW METHOD:")
    print("-" * 40)

    elbow = engine.elbow_method(range(1, 6))
    for k, inertia in elbow.items():
        print(f"   k={k}: inertia={inertia:.2f}")
    print()

    # 5. Hierarchical Clustering
    print("5. HIERARCHICAL CLUSTERING:")
    print("-" * 40)

    result = engine.hierarchical(n_clusters=3, linkage=LinkageType.AVERAGE)

    print(f"   Method: {result.method.value}")
    print(f"   Clusters: {result.n_clusters}")
    print(f"   Iterations: {result.iterations}")

    for cluster in result.clusters:
        print(f"   Cluster: {len(cluster.points)} points")
    print()

    # 6. DBSCAN Clustering
    print("6. DBSCAN CLUSTERING:")
    print("-" * 40)

    result = engine.dbscan(eps=1.0, min_samples=3)

    print(f"   Method: {result.method.value}")
    print(f"   Clusters found: {result.n_clusters}")

    for cluster in result.clusters:
        print(f"   Cluster {cluster.cluster_id}: {len(cluster.points)} points")
    print()

    # 7. Predict New Point
    print("7. PREDICT NEW POINT:")
    print("-" * 40)

    # Re-run kmeans for prediction
    engine.kmeans(k=3)

    new_points = [[0.5, 0.5], [5.5, 5.5], [9.5, 0.5]]
    for point in new_points:
        cluster_id = engine.predict(point)
        print(f"   Point {point} -> Cluster {cluster_id[:8]}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Clustering Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
