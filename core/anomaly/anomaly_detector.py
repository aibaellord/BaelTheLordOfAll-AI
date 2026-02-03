#!/usr/bin/env python3
"""
BAEL - Anomaly Detector
Advanced anomaly and outlier detection.

Features:
- Statistical methods
- Isolation Forest concepts
- Local Outlier Factor (LOF)
- One-class detection
- Threshold tuning
- Anomaly scoring
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

class DetectionMethod(Enum):
    """Detection methods."""
    STATISTICAL = "statistical"
    ISOLATION = "isolation"
    LOF = "lof"
    DISTANCE = "distance"


class AnomalyType(Enum):
    """Types of anomalies."""
    POINT = "point"
    CONTEXTUAL = "contextual"
    COLLECTIVE = "collective"


class AnomalyStatus(Enum):
    """Anomaly status."""
    NORMAL = "normal"
    ANOMALY = "anomaly"
    SUSPICIOUS = "suspicious"


class ThresholdMethod(Enum):
    """Threshold methods."""
    PERCENTILE = "percentile"
    STDDEV = "stddev"
    IQR = "iqr"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class DataPoint:
    """A data point for anomaly detection."""
    point_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    values: List[float] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    label: Optional[str] = None


@dataclass
class AnomalyScore:
    """Anomaly score for a point."""
    point_id: str = ""
    score: float = 0.0
    status: AnomalyStatus = AnomalyStatus.NORMAL
    method: DetectionMethod = DetectionMethod.STATISTICAL


@dataclass
class DetectionResult:
    """Detection result."""
    method: DetectionMethod = DetectionMethod.STATISTICAL
    threshold: float = 0.0
    total_points: int = 0
    anomalies: List[str] = field(default_factory=list)
    scores: Dict[str, float] = field(default_factory=dict)


@dataclass
class StatisticalProfile:
    """Statistical profile of data."""
    mean: List[float] = field(default_factory=list)
    std: List[float] = field(default_factory=list)
    min_val: List[float] = field(default_factory=list)
    max_val: List[float] = field(default_factory=list)
    q1: List[float] = field(default_factory=list)
    q3: List[float] = field(default_factory=list)


# =============================================================================
# DATA STORE
# =============================================================================

class AnomalyDataStore:
    """Store for data points."""

    def __init__(self):
        self._points: Dict[str, DataPoint] = {}

    def add(
        self,
        values: List[float],
        label: Optional[str] = None
    ) -> DataPoint:
        """Add a data point."""
        point = DataPoint(values=values, label=label)
        self._points[point.point_id] = point
        return point

    def get(self, point_id: str) -> Optional[DataPoint]:
        """Get a point."""
        return self._points.get(point_id)

    def all_points(self) -> List[DataPoint]:
        """Get all points."""
        return list(self._points.values())

    def dimension(self) -> int:
        """Get data dimension."""
        points = self.all_points()
        if not points or not points[0].values:
            return 0
        return len(points[0].values)


# =============================================================================
# STATISTICAL DETECTOR
# =============================================================================

class StatisticalDetector:
    """Statistical anomaly detection."""

    def __init__(self):
        self._profile: Optional[StatisticalProfile] = None

    def _compute_quartiles(self, values: List[float]) -> Tuple[float, float]:
        """Compute Q1 and Q3."""
        if not values:
            return 0.0, 0.0

        sorted_vals = sorted(values)
        n = len(sorted_vals)

        q1_idx = n // 4
        q3_idx = 3 * n // 4

        return sorted_vals[q1_idx], sorted_vals[q3_idx]

    def fit(self, points: List[DataPoint]) -> StatisticalProfile:
        """Compute statistical profile."""
        if not points:
            return StatisticalProfile()

        dim = len(points[0].values)
        n = len(points)

        means = [0.0] * dim
        stds = [0.0] * dim
        mins = [float('inf')] * dim
        maxs = [float('-inf')] * dim
        q1s = [0.0] * dim
        q3s = [0.0] * dim

        # Compute means
        for point in points:
            for i, v in enumerate(point.values):
                means[i] += v
                mins[i] = min(mins[i], v)
                maxs[i] = max(maxs[i], v)

        means = [m / n for m in means]

        # Compute stds
        for point in points:
            for i, v in enumerate(point.values):
                stds[i] += (v - means[i]) ** 2

        stds = [math.sqrt(s / n) for s in stds]

        # Compute quartiles
        for i in range(dim):
            values = [p.values[i] for p in points]
            q1s[i], q3s[i] = self._compute_quartiles(values)

        self._profile = StatisticalProfile(
            mean=means,
            std=stds,
            min_val=mins,
            max_val=maxs,
            q1=q1s,
            q3=q3s
        )

        return self._profile

    def z_score(self, point: DataPoint) -> float:
        """Compute Z-score for a point."""
        if not self._profile:
            return 0.0

        z_scores = []
        for i, v in enumerate(point.values):
            if self._profile.std[i] > 0:
                z = abs(v - self._profile.mean[i]) / self._profile.std[i]
                z_scores.append(z)

        return max(z_scores) if z_scores else 0.0

    def iqr_score(self, point: DataPoint) -> float:
        """Compute IQR-based score for a point."""
        if not self._profile:
            return 0.0

        scores = []
        for i, v in enumerate(point.values):
            iqr = self._profile.q3[i] - self._profile.q1[i]
            if iqr > 0:
                lower = self._profile.q1[i] - 1.5 * iqr
                upper = self._profile.q3[i] + 1.5 * iqr

                if v < lower:
                    scores.append((lower - v) / iqr)
                elif v > upper:
                    scores.append((v - upper) / iqr)
                else:
                    scores.append(0.0)

        return max(scores) if scores else 0.0

    def detect(
        self,
        points: List[DataPoint],
        threshold: float = 3.0,
        method: ThresholdMethod = ThresholdMethod.STDDEV
    ) -> DetectionResult:
        """Detect anomalies using statistical methods."""
        if method == ThresholdMethod.STDDEV:
            scores = {p.point_id: self.z_score(p) for p in points}
        else:
            scores = {p.point_id: self.iqr_score(p) for p in points}

        anomalies = [
            pid for pid, score in scores.items()
            if score > threshold
        ]

        return DetectionResult(
            method=DetectionMethod.STATISTICAL,
            threshold=threshold,
            total_points=len(points),
            anomalies=anomalies,
            scores=scores
        )


# =============================================================================
# ISOLATION FOREST CONCEPTS
# =============================================================================

@dataclass
class IsolationNode:
    """Node in isolation tree."""
    node_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    split_feature: int = -1
    split_value: float = 0.0
    left: Optional['IsolationNode'] = None
    right: Optional['IsolationNode'] = None
    size: int = 0


class IsolationTree:
    """A single isolation tree."""

    def __init__(self, max_depth: int = 10):
        self._max_depth = max_depth
        self._root: Optional[IsolationNode] = None

    def _build(
        self,
        points: List[DataPoint],
        depth: int = 0
    ) -> Optional[IsolationNode]:
        """Build isolation tree."""
        if not points or depth >= self._max_depth:
            node = IsolationNode(size=len(points))
            return node

        if len(points) <= 1:
            return IsolationNode(size=len(points))

        # Random feature and split
        dim = len(points[0].values)
        feature = random.randint(0, dim - 1)

        values = [p.values[feature] for p in points]
        min_val, max_val = min(values), max(values)

        if min_val == max_val:
            return IsolationNode(size=len(points))

        split = random.uniform(min_val, max_val)

        left_points = [p for p in points if p.values[feature] < split]
        right_points = [p for p in points if p.values[feature] >= split]

        node = IsolationNode(
            split_feature=feature,
            split_value=split,
            size=len(points)
        )

        node.left = self._build(left_points, depth + 1)
        node.right = self._build(right_points, depth + 1)

        return node

    def fit(self, points: List[DataPoint]) -> None:
        """Fit isolation tree."""
        self._root = self._build(points)

    def path_length(self, point: DataPoint, node: Optional[IsolationNode] = None, depth: int = 0) -> int:
        """Get path length for a point."""
        if node is None:
            node = self._root

        if node is None:
            return depth

        if node.left is None or node.right is None:
            return depth

        if point.values[node.split_feature] < node.split_value:
            return self.path_length(point, node.left, depth + 1)
        else:
            return self.path_length(point, node.right, depth + 1)


class IsolationForestDetector:
    """Isolation Forest anomaly detection."""

    def __init__(self, n_trees: int = 100, max_depth: int = 10):
        self._n_trees = n_trees
        self._max_depth = max_depth
        self._trees: List[IsolationTree] = []
        self._n_samples = 0

    def _c(self, n: int) -> float:
        """Average path length of unsuccessful search in BST."""
        if n <= 1:
            return 0
        return 2 * (math.log(n - 1) + 0.5772156649) - 2 * (n - 1) / n

    def fit(self, points: List[DataPoint], sample_size: int = 256) -> None:
        """Fit isolation forest."""
        self._n_samples = min(sample_size, len(points))
        self._trees = []

        for _ in range(self._n_trees):
            sample = random.sample(points, self._n_samples)
            tree = IsolationTree(self._max_depth)
            tree.fit(sample)
            self._trees.append(tree)

    def score(self, point: DataPoint) -> float:
        """Calculate anomaly score (higher = more anomalous)."""
        if not self._trees:
            return 0.0

        # Average path length
        avg_path = sum(
            tree.path_length(point) for tree in self._trees
        ) / len(self._trees)

        c = self._c(self._n_samples)

        if c == 0:
            return 0.5

        # Anomaly score
        return 2 ** (-avg_path / c)

    def detect(
        self,
        points: List[DataPoint],
        threshold: float = 0.6
    ) -> DetectionResult:
        """Detect anomalies."""
        scores = {p.point_id: self.score(p) for p in points}

        anomalies = [
            pid for pid, score in scores.items()
            if score > threshold
        ]

        return DetectionResult(
            method=DetectionMethod.ISOLATION,
            threshold=threshold,
            total_points=len(points),
            anomalies=anomalies,
            scores=scores
        )


# =============================================================================
# LOCAL OUTLIER FACTOR
# =============================================================================

class LOFDetector:
    """Local Outlier Factor detection."""

    def __init__(self, k: int = 5):
        self._k = k
        self._points: List[DataPoint] = []

    def _distance(self, p1: DataPoint, p2: DataPoint) -> float:
        """Euclidean distance."""
        return math.sqrt(sum(
            (a - b) ** 2 for a, b in zip(p1.values, p2.values)
        ))

    def _k_distance(self, point: DataPoint) -> float:
        """Get k-distance for a point."""
        distances = sorted([
            self._distance(point, p)
            for p in self._points
            if p.point_id != point.point_id
        ])

        return distances[self._k - 1] if len(distances) >= self._k else 0.0

    def _k_neighbors(self, point: DataPoint) -> List[DataPoint]:
        """Get k nearest neighbors."""
        with_distances = [
            (p, self._distance(point, p))
            for p in self._points
            if p.point_id != point.point_id
        ]

        with_distances.sort(key=lambda x: x[1])
        return [p for p, _ in with_distances[:self._k]]

    def _reachability_distance(self, p1: DataPoint, p2: DataPoint) -> float:
        """Reachability distance."""
        k_dist = self._k_distance(p2)
        actual_dist = self._distance(p1, p2)
        return max(k_dist, actual_dist)

    def _local_reachability_density(self, point: DataPoint) -> float:
        """Local reachability density."""
        neighbors = self._k_neighbors(point)

        if not neighbors:
            return 0.0

        sum_rd = sum(
            self._reachability_distance(point, neighbor)
            for neighbor in neighbors
        )

        if sum_rd == 0:
            return float('inf')

        return len(neighbors) / sum_rd

    def fit(self, points: List[DataPoint]) -> None:
        """Fit LOF detector."""
        self._points = points

    def score(self, point: DataPoint) -> float:
        """Calculate LOF score (higher = more anomalous)."""
        lrd_point = self._local_reachability_density(point)

        if lrd_point == 0 or lrd_point == float('inf'):
            return 1.0

        neighbors = self._k_neighbors(point)

        if not neighbors:
            return 1.0

        lof = sum(
            self._local_reachability_density(neighbor)
            for neighbor in neighbors
        ) / (len(neighbors) * lrd_point)

        return lof

    def detect(
        self,
        points: List[DataPoint],
        threshold: float = 1.5
    ) -> DetectionResult:
        """Detect anomalies."""
        scores = {p.point_id: self.score(p) for p in points}

        anomalies = [
            pid for pid, score in scores.items()
            if score > threshold
        ]

        return DetectionResult(
            method=DetectionMethod.LOF,
            threshold=threshold,
            total_points=len(points),
            anomalies=anomalies,
            scores=scores
        )


# =============================================================================
# ANOMALY DETECTOR
# =============================================================================

class AnomalyDetector:
    """
    Anomaly Detector for BAEL.

    Advanced anomaly and outlier detection.
    """

    def __init__(self):
        self._store = AnomalyDataStore()
        self._statistical = StatisticalDetector()
        self._isolation = IsolationForestDetector()
        self._lof = LOFDetector()

    # -------------------------------------------------------------------------
    # DATA
    # -------------------------------------------------------------------------

    def add_point(
        self,
        values: List[float],
        label: Optional[str] = None
    ) -> DataPoint:
        """Add a data point."""
        return self._store.add(values, label)

    def all_points(self) -> List[DataPoint]:
        """Get all points."""
        return self._store.all_points()

    # -------------------------------------------------------------------------
    # FITTING
    # -------------------------------------------------------------------------

    def fit_statistical(self) -> StatisticalProfile:
        """Fit statistical detector."""
        return self._statistical.fit(self._store.all_points())

    def fit_isolation(self, n_trees: int = 100) -> None:
        """Fit isolation forest."""
        self._isolation = IsolationForestDetector(n_trees=n_trees)
        self._isolation.fit(self._store.all_points())

    def fit_lof(self, k: int = 5) -> None:
        """Fit LOF detector."""
        self._lof = LOFDetector(k=k)
        self._lof.fit(self._store.all_points())

    # -------------------------------------------------------------------------
    # DETECTION
    # -------------------------------------------------------------------------

    def detect_statistical(
        self,
        threshold: float = 3.0
    ) -> DetectionResult:
        """Detect using statistical methods."""
        return self._statistical.detect(
            self._store.all_points(),
            threshold
        )

    def detect_isolation(
        self,
        threshold: float = 0.6
    ) -> DetectionResult:
        """Detect using isolation forest."""
        return self._isolation.detect(
            self._store.all_points(),
            threshold
        )

    def detect_lof(
        self,
        threshold: float = 1.5
    ) -> DetectionResult:
        """Detect using LOF."""
        return self._lof.detect(
            self._store.all_points(),
            threshold
        )

    # -------------------------------------------------------------------------
    # SCORING
    # -------------------------------------------------------------------------

    def score_point(
        self,
        point: DataPoint,
        method: DetectionMethod = DetectionMethod.STATISTICAL
    ) -> AnomalyScore:
        """Score a single point."""
        if method == DetectionMethod.STATISTICAL:
            score = self._statistical.z_score(point)
        elif method == DetectionMethod.ISOLATION:
            score = self._isolation.score(point)
        elif method == DetectionMethod.LOF:
            score = self._lof.score(point)
        else:
            score = 0.0

        # Determine status
        if method == DetectionMethod.STATISTICAL:
            status = AnomalyStatus.ANOMALY if score > 3.0 else (
                AnomalyStatus.SUSPICIOUS if score > 2.0 else AnomalyStatus.NORMAL
            )
        elif method == DetectionMethod.ISOLATION:
            status = AnomalyStatus.ANOMALY if score > 0.6 else (
                AnomalyStatus.SUSPICIOUS if score > 0.5 else AnomalyStatus.NORMAL
            )
        else:
            status = AnomalyStatus.ANOMALY if score > 1.5 else (
                AnomalyStatus.SUSPICIOUS if score > 1.2 else AnomalyStatus.NORMAL
            )

        return AnomalyScore(
            point_id=point.point_id,
            score=score,
            status=status,
            method=method
        )

    # -------------------------------------------------------------------------
    # ENSEMBLE
    # -------------------------------------------------------------------------

    def detect_ensemble(self) -> DetectionResult:
        """Ensemble detection using multiple methods."""
        points = self._store.all_points()

        # Get scores from all methods
        stat_scores = {p.point_id: self._statistical.z_score(p) for p in points}
        iso_scores = {p.point_id: self._isolation.score(p) for p in points}
        lof_scores = {p.point_id: self._lof.score(p) for p in points}

        # Normalize and combine
        combined = {}
        for pid in stat_scores:
            # Normalize statistical (assume max ~5)
            s1 = min(stat_scores[pid] / 5.0, 1.0)
            # Isolation already 0-1
            s2 = iso_scores.get(pid, 0.0)
            # Normalize LOF (assume max ~3)
            s3 = min(lof_scores.get(pid, 0.0) / 3.0, 1.0)

            combined[pid] = (s1 + s2 + s3) / 3.0

        anomalies = [
            pid for pid, score in combined.items()
            if score > 0.5
        ]

        return DetectionResult(
            method=DetectionMethod.STATISTICAL,
            threshold=0.5,
            total_points=len(points),
            anomalies=anomalies,
            scores=combined
        )


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Anomaly Detector."""
    print("=" * 70)
    print("BAEL - ANOMALY DETECTOR DEMO")
    print("Advanced Anomaly and Outlier Detection")
    print("=" * 70)
    print()

    detector = AnomalyDetector()

    # 1. Add Normal Data
    print("1. ADD NORMAL DATA:")
    print("-" * 40)

    # Generate normal data
    for _ in range(100):
        x = random.gauss(50, 10)
        y = random.gauss(50, 10)
        detector.add_point([x, y], "normal")

    print(f"   Added 100 normal points centered at (50, 50)")

    # Add anomalies
    anomaly_positions = [
        (0, 0),
        (100, 100),
        (50, 100),
        (100, 50),
        (0, 100)
    ]

    for x, y in anomaly_positions:
        detector.add_point([x + random.gauss(0, 2), y + random.gauss(0, 2)], "anomaly")

    print(f"   Added {len(anomaly_positions)} anomaly points")
    print(f"   Total: {len(detector.all_points())} points")
    print()

    # 2. Fit Detectors
    print("2. FIT DETECTORS:")
    print("-" * 40)

    profile = detector.fit_statistical()
    print(f"   Statistical: mean=[{profile.mean[0]:.1f}, {profile.mean[1]:.1f}]")
    print(f"                std=[{profile.std[0]:.1f}, {profile.std[1]:.1f}]")

    detector.fit_isolation(n_trees=50)
    print(f"   Isolation Forest: 50 trees fitted")

    detector.fit_lof(k=5)
    print(f"   LOF: k=5 neighbors")
    print()

    # 3. Statistical Detection
    print("3. STATISTICAL DETECTION:")
    print("-" * 40)

    result = detector.detect_statistical(threshold=2.5)
    print(f"   Threshold: {result.threshold}")
    print(f"   Anomalies found: {len(result.anomalies)}")

    # Show top scores
    top_scores = sorted(result.scores.items(), key=lambda x: -x[1])[:5]
    for pid, score in top_scores:
        point = detector._store.get(pid)
        if point:
            print(f"      Score {score:.2f}: [{point.values[0]:.1f}, {point.values[1]:.1f}]")
    print()

    # 4. Isolation Forest Detection
    print("4. ISOLATION FOREST DETECTION:")
    print("-" * 40)

    result = detector.detect_isolation(threshold=0.55)
    print(f"   Threshold: {result.threshold}")
    print(f"   Anomalies found: {len(result.anomalies)}")

    top_scores = sorted(result.scores.items(), key=lambda x: -x[1])[:5]
    for pid, score in top_scores:
        point = detector._store.get(pid)
        if point:
            print(f"      Score {score:.3f}: [{point.values[0]:.1f}, {point.values[1]:.1f}]")
    print()

    # 5. LOF Detection
    print("5. LOF DETECTION:")
    print("-" * 40)

    result = detector.detect_lof(threshold=1.3)
    print(f"   Threshold: {result.threshold}")
    print(f"   Anomalies found: {len(result.anomalies)}")

    top_scores = sorted(result.scores.items(), key=lambda x: -x[1])[:5]
    for pid, score in top_scores:
        point = detector._store.get(pid)
        if point:
            print(f"      Score {score:.2f}: [{point.values[0]:.1f}, {point.values[1]:.1f}]")
    print()

    # 6. Ensemble Detection
    print("6. ENSEMBLE DETECTION:")
    print("-" * 40)

    result = detector.detect_ensemble()
    print(f"   Threshold: {result.threshold}")
    print(f"   Anomalies found: {len(result.anomalies)}")
    print()

    # 7. Score Individual Point
    print("7. SCORE INDIVIDUAL POINT:")
    print("-" * 40)

    test_point = DataPoint(values=[0, 0])

    for method in [DetectionMethod.STATISTICAL, DetectionMethod.ISOLATION, DetectionMethod.LOF]:
        score = detector.score_point(test_point, method)
        print(f"   {method.value}: score={score.score:.3f}, status={score.status.value}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Anomaly Detector Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
