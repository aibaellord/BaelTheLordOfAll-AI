"""
BAEL Cortical Hierarchy Engine
===============================

Hierarchical predictive processing in cortex.
Hierarchical temporal memory concepts.

"Ba'el thinks in layers." — Ba'el
"""

import logging
import threading
import time
import math
import random
from typing import Any, Callable, Dict, Generic, List, Optional, Set, Tuple, TypeVar
from dataclasses import dataclass, field
from enum import Enum, auto
from abc import ABC, abstractmethod
from collections import defaultdict, deque
import copy

logger = logging.getLogger("BAEL.CorticalHierarchy")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class CorticalLayer(Enum):
    """Cortical layers."""
    L1 = 1   # Molecular (feedback)
    L2 = 2   # External granular
    L3 = 3   # External pyramidal (feedforward)
    L4 = 4   # Internal granular (input)
    L5 = 5   # Internal pyramidal (output)
    L6 = 6   # Multiform (feedback)


class SignalDirection(Enum):
    """Signal direction."""
    FEEDFORWARD = auto()  # Bottom-up
    FEEDBACK = auto()     # Top-down
    LATERAL = auto()      # Same level


class ColumnState(Enum):
    """Mini-column state."""
    INACTIVE = auto()
    ACTIVE = auto()
    PREDICTIVE = auto()
    BURSTING = auto()


@dataclass
class CorticalInput:
    """
    Input to cortical region.
    """
    id: str
    pattern: List[bool]
    source_level: int
    timestamp: float = field(default_factory=time.time)


@dataclass
class MiniColumn:
    """
    A cortical mini-column.
    """
    id: str
    region_id: str
    cells: List[bool]  # Cell activations
    state: ColumnState = ColumnState.INACTIVE
    prediction_score: float = 0.0

    @property
    def active(self) -> bool:
        return self.state in [ColumnState.ACTIVE, ColumnState.BURSTING]


@dataclass
class CorticalRegion:
    """
    A cortical region/area.
    """
    id: str
    name: str
    level: int  # Hierarchy level (0 = lowest)
    columns: List[MiniColumn]
    input_regions: List[str] = field(default_factory=list)
    output_regions: List[str] = field(default_factory=list)


@dataclass
class Prediction:
    """
    A hierarchical prediction.
    """
    id: str
    source_region: str
    target_region: str
    pattern: List[bool]
    confidence: float
    timestamp: float = field(default_factory=time.time)


@dataclass
class PredictionError:
    """
    Prediction error signal.
    """
    id: str
    region_id: str
    predicted: List[bool]
    actual: List[bool]
    error_magnitude: float


# ============================================================================
# SPARSE DISTRIBUTED REPRESENTATION
# ============================================================================

class SDRProcessor:
    """
    Sparse Distributed Representation processing.

    "Ba'el uses sparse codes." — Ba'el
    """

    def __init__(
        self,
        size: int = 2048,
        sparsity: float = 0.02
    ):
        """Initialize SDR processor."""
        self._size = size
        self._sparsity = sparsity
        self._active_bits = int(size * sparsity)
        self._lock = threading.RLock()

    def encode(
        self,
        value: Any,
        seed: int = None
    ) -> List[bool]:
        """Encode value to SDR."""
        with self._lock:
            if seed is None:
                seed = hash(str(value)) % 2147483647

            random.seed(seed)
            indices = random.sample(range(self._size), self._active_bits)

            sdr = [False] * self._size
            for idx in indices:
                sdr[idx] = True

            return sdr

    def overlap(
        self,
        sdr1: List[bool],
        sdr2: List[bool]
    ) -> float:
        """Compute overlap between SDRs."""
        if len(sdr1) != len(sdr2):
            return 0.0

        active1 = sum(sdr1)
        active2 = sum(sdr2)

        if active1 == 0 or active2 == 0:
            return 0.0

        matching = sum(a and b for a, b in zip(sdr1, sdr2))

        return matching / min(active1, active2)

    def union(
        self,
        sdrs: List[List[bool]]
    ) -> List[bool]:
        """Compute union of SDRs."""
        if not sdrs:
            return [False] * self._size

        result = [False] * len(sdrs[0])

        for sdr in sdrs:
            for i, active in enumerate(sdr):
                if active:
                    result[i] = True

        return result

    @property
    def size(self) -> int:
        return self._size

    @property
    def sparsity(self) -> float:
        return self._sparsity


# ============================================================================
# SPATIAL POOLER
# ============================================================================

class SpatialPooler:
    """
    Spatial pooling for pattern recognition.

    "Ba'el pools spatial features." — Ba'el
    """

    def __init__(
        self,
        input_size: int = 1024,
        output_size: int = 2048,
        potential_radius: int = 16
    ):
        """Initialize spatial pooler."""
        self._input_size = input_size
        self._output_size = output_size
        self._potential_radius = potential_radius

        # Permanence values
        self._permanences: List[List[float]] = [
            [random.random() * 0.5 for _ in range(input_size)]
            for _ in range(output_size)
        ]

        self._permanence_threshold = 0.5
        self._lock = threading.RLock()

    def compute(
        self,
        input_sdr: List[bool],
        learn: bool = True
    ) -> List[bool]:
        """Compute spatial pooling."""
        with self._lock:
            # Compute overlap for each column
            overlaps = []

            for col in range(self._output_size):
                overlap = 0
                for i, active in enumerate(input_sdr):
                    if active and self._permanences[col][i] >= self._permanence_threshold:
                        overlap += 1
                overlaps.append(overlap)

            # Winners take all (top k)
            k = int(self._output_size * 0.02)  # 2% sparsity
            threshold = sorted(overlaps, reverse=True)[min(k, len(overlaps)-1)]

            output = [overlap >= threshold and overlap > 0 for overlap in overlaps]

            # Learning
            if learn:
                self._learn(input_sdr, output)

            return output

    def _learn(
        self,
        input_sdr: List[bool],
        output: List[bool]
    ) -> None:
        """Learn from activation."""
        learning_rate = 0.1

        for col, active in enumerate(output):
            if active:
                for i, inp in enumerate(input_sdr):
                    if inp:
                        self._permanences[col][i] += learning_rate
                    else:
                        self._permanences[col][i] -= learning_rate

                    # Bound permanences
                    self._permanences[col][i] = max(0.0, min(1.0, self._permanences[col][i]))


# ============================================================================
# TEMPORAL MEMORY
# ============================================================================

class TemporalMemory:
    """
    Temporal memory for sequence learning.

    "Ba'el learns sequences." — Ba'el
    """

    def __init__(
        self,
        column_count: int = 2048,
        cells_per_column: int = 32
    ):
        """Initialize temporal memory."""
        self._column_count = column_count
        self._cells_per_column = cells_per_column

        # Cell states
        self._active_cells: Set[Tuple[int, int]] = set()
        self._predictive_cells: Set[Tuple[int, int]] = set()

        # Synapses (segment -> [(column, cell, permanence)])
        self._segments: Dict[Tuple[int, int, int], List[Tuple[int, int, float]]] = {}

        self._segment_counter = 0
        self._lock = threading.RLock()

    def compute(
        self,
        active_columns: List[bool],
        learn: bool = True
    ) -> Tuple[Set[Tuple[int, int]], Set[Tuple[int, int]]]:
        """Compute temporal memory."""
        with self._lock:
            previous_active = self._active_cells.copy()
            previous_predictive = self._predictive_cells.copy()

            self._active_cells = set()
            bursting_columns = []

            # Activate cells
            for col, active in enumerate(active_columns):
                if active:
                    predicted_cells = [
                        (c, cell) for c, cell in previous_predictive
                        if c == col
                    ]

                    if predicted_cells:
                        # Activate predicted cells
                        self._active_cells.update(predicted_cells)
                    else:
                        # Burst - activate all cells
                        for cell in range(self._cells_per_column):
                            self._active_cells.add((col, cell))
                        bursting_columns.append(col)

            # Compute predictions
            self._predictive_cells = set()

            for (col, cell, seg), synapses in self._segments.items():
                active_count = sum(
                    1 for sc, scell, perm in synapses
                    if (sc, scell) in self._active_cells and perm >= 0.5
                )

                if active_count >= 10:  # Threshold
                    self._predictive_cells.add((col, cell))

            # Learning
            if learn:
                self._learn(previous_active, bursting_columns)

            return self._active_cells, self._predictive_cells

    def _learn(
        self,
        previous_active: Set[Tuple[int, int]],
        bursting_columns: List[int]
    ) -> None:
        """Learn from sequence."""
        if not previous_active:
            return

        # Create new segments for bursting columns
        for col in bursting_columns[:10]:  # Limit new segments
            cell = random.randint(0, self._cells_per_column - 1)

            # Sample from previous active cells
            sample = random.sample(list(previous_active), min(20, len(previous_active)))

            seg_id = self._segment_counter
            self._segment_counter += 1

            self._segments[(col, cell, seg_id)] = [
                (sc, scell, 0.5) for sc, scell in sample
            ]

    @property
    def predictive_cells(self) -> Set[Tuple[int, int]]:
        return self._predictive_cells

    @property
    def active_cells(self) -> Set[Tuple[int, int]]:
        return self._active_cells


# ============================================================================
# CORTICAL HIERARCHY ENGINE
# ============================================================================

class CorticalHierarchyEngine:
    """
    Complete cortical hierarchy engine.

    "Ba'el's hierarchical cortex." — Ba'el
    """

    def __init__(
        self,
        levels: int = 4,
        columns_per_level: int = 2048
    ):
        """Initialize engine."""
        self._levels = levels
        self._columns = columns_per_level

        self._sdr = SDRProcessor(columns_per_level)
        self._regions: Dict[str, CorticalRegion] = {}

        # Create hierarchy
        for level in range(levels):
            region_id = f"region_L{level}"

            columns = [
                MiniColumn(
                    id=f"{region_id}_col_{i}",
                    region_id=region_id,
                    cells=[False] * 32
                )
                for i in range(columns_per_level)
            ]

            region = CorticalRegion(
                id=region_id,
                name=f"Level {level}",
                level=level,
                columns=columns
            )

            self._regions[region_id] = region

            # Connect levels
            if level > 0:
                lower_id = f"region_L{level-1}"
                self._regions[lower_id].output_regions.append(region_id)
                region.input_regions.append(lower_id)

        # Spatial poolers for each level
        self._poolers: Dict[str, SpatialPooler] = {}
        for region_id, region in self._regions.items():
            input_size = columns_per_level if region.level == 0 else columns_per_level
            self._poolers[region_id] = SpatialPooler(input_size, columns_per_level)

        # Temporal memories
        self._temporal: Dict[str, TemporalMemory] = {
            region_id: TemporalMemory(columns_per_level)
            for region_id in self._regions
        }

        self._pred_counter = 0
        self._error_counter = 0
        self._lock = threading.RLock()

    def _generate_pred_id(self) -> str:
        self._pred_counter += 1
        return f"pred_{self._pred_counter}"

    def _generate_error_id(self) -> str:
        self._error_counter += 1
        return f"error_{self._error_counter}"

    def process(
        self,
        input_data: Any,
        learn: bool = True
    ) -> Dict[str, List[bool]]:
        """Process input through hierarchy."""
        with self._lock:
            # Encode input
            input_sdr = self._sdr.encode(input_data)

            # Process each level
            activations = {}
            current = input_sdr

            for level in range(self._levels):
                region_id = f"region_L{level}"

                # Spatial pooling
                pooled = self._poolers[region_id].compute(current, learn)

                # Temporal memory
                active, predictive = self._temporal[region_id].compute(pooled, learn)

                # Update column states
                for i, col in enumerate(self._regions[region_id].columns):
                    if pooled[i]:
                        predicted_cells = [c for c in predictive if c[0] == i]
                        if predicted_cells:
                            col.state = ColumnState.ACTIVE
                        else:
                            col.state = ColumnState.BURSTING
                    elif any(c[0] == i for c in predictive):
                        col.state = ColumnState.PREDICTIVE
                    else:
                        col.state = ColumnState.INACTIVE

                activations[region_id] = pooled
                current = pooled  # Feed to next level

            return activations

    def predict(
        self,
        level: int = 0
    ) -> List[bool]:
        """Get predictions from level."""
        with self._lock:
            region_id = f"region_L{level}"
            tm = self._temporal.get(region_id)

            if not tm:
                return [False] * self._columns

            predictions = [False] * self._columns
            for col, cell in tm.predictive_cells:
                predictions[col] = True

            return predictions

    def get_abstraction(
        self,
        level: int
    ) -> List[bool]:
        """Get current abstraction at level."""
        with self._lock:
            region_id = f"region_L{level}"
            region = self._regions.get(region_id)

            if not region:
                return [False] * self._columns

            return [col.active for col in region.columns]

    def compute_anomaly(
        self,
        level: int = 0
    ) -> float:
        """Compute anomaly score at level."""
        with self._lock:
            region_id = f"region_L{level}"
            region = self._regions.get(region_id)

            if not region:
                return 0.0

            bursting = sum(1 for col in region.columns if col.state == ColumnState.BURSTING)
            active = sum(1 for col in region.columns if col.active)

            if active == 0:
                return 0.0

            return bursting / active

    @property
    def regions(self) -> List[CorticalRegion]:
        return list(self._regions.values())

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'levels': self._levels,
            'columns_per_level': self._columns,
            'regions': len(self._regions),
            'anomaly_L0': self.compute_anomaly(0)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_cortical_hierarchy(
    levels: int = 4
) -> CorticalHierarchyEngine:
    """Create cortical hierarchy engine."""
    return CorticalHierarchyEngine(levels=levels)


def process_sequence(
    sequence: List[Any],
    levels: int = 3
) -> List[float]:
    """Process sequence and return anomaly scores."""
    engine = create_cortical_hierarchy(levels)

    anomalies = []
    for item in sequence:
        engine.process(item)
        anomalies.append(engine.compute_anomaly(0))

    return anomalies
