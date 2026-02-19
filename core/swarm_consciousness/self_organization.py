"""
⚡ SELF-ORGANIZATION ⚡
======================
Self-organizing systems at the edge of chaos.

Implements:
- Self-Organizing Maps (SOM)
- Self-Organized Criticality (SOC)
- Avalanche Dynamics
- Edge of Chaos Detection
- Emergent Structure Formation
"""

import math
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
import uuid


@dataclass
class CriticalityMetrics:
    """Metrics for system criticality"""
    order_parameter: float = 0.0  # 0=disordered, 1=ordered
    entropy: float = 0.0
    correlation_length: float = 0.0
    susceptibility: float = 0.0
    avalanche_size_exponent: float = 0.0
    is_critical: bool = False


class CriticalityDetector:
    """
    Detects critical states in dynamical systems.

    Critical states are at the edge of order and chaos.
    """

    def __init__(self, history_size: int = 1000):
        self.history_size = history_size
        self.state_history: List[np.ndarray] = []
        self.event_history: List[float] = []  # Avalanche sizes

    def record_state(self, state: np.ndarray):
        """Record system state"""
        self.state_history.append(state.copy())
        if len(self.state_history) > self.history_size:
            self.state_history.pop(0)

    def record_event(self, size: float):
        """Record event/avalanche size"""
        self.event_history.append(size)
        if len(self.event_history) > self.history_size:
            self.event_history.pop(0)

    def calculate_order_parameter(self) -> float:
        """
        Calculate order parameter.

        High for ordered systems, low for disordered.
        """
        if len(self.state_history) < 2:
            return 0.0

        # Use magnetization-like order parameter
        states = np.array(self.state_history)
        mean_state = np.mean(states, axis=0)

        # Variance across time
        variance = np.mean(np.var(states, axis=0))

        # Order parameter: 1 - normalized variance
        max_var = 1.0  # Assuming normalized states
        order = 1 - min(variance / max_var, 1.0)

        return float(order)

    def calculate_entropy(self) -> float:
        """Calculate system entropy"""
        if len(self.state_history) < 10:
            return 0.0

        # Discretize states
        states = np.array(self.state_history)
        flat_states = states.flatten()

        # Histogram
        bins = min(50, len(flat_states) // 10)
        hist, _ = np.histogram(flat_states, bins=bins, density=True)

        # Shannon entropy
        hist = hist[hist > 0]  # Avoid log(0)
        entropy = -np.sum(hist * np.log2(hist + 1e-10))

        return float(entropy)

    def calculate_correlation_length(self) -> float:
        """
        Estimate correlation length.

        Long correlations indicate criticality.
        """
        if len(self.state_history) < 10:
            return 0.0

        states = np.array(self.state_history)
        n_states = len(states)

        # Autocorrelation
        correlations = []
        max_lag = min(n_states // 2, 100)

        for lag in range(1, max_lag):
            corr = np.corrcoef(
                states[:-lag].flatten(),
                states[lag:].flatten()
            )[0, 1]
            if not np.isnan(corr):
                correlations.append(abs(corr))

        if not correlations:
            return 0.0

        # Correlation length = where correlation drops below threshold
        threshold = 0.1
        for i, corr in enumerate(correlations):
            if corr < threshold:
                return float(i + 1)

        return float(len(correlations))

    def calculate_susceptibility(self) -> float:
        """
        Calculate susceptibility (response to perturbations).

        High susceptibility indicates criticality.
        """
        if len(self.state_history) < 10:
            return 0.0

        states = np.array(self.state_history)

        # Susceptibility ~ variance of mean
        means = np.mean(states, axis=1)
        susceptibility = np.var(means)

        return float(susceptibility)

    def calculate_avalanche_exponent(self) -> float:
        """
        Calculate power-law exponent of avalanche sizes.

        Critical systems have power-law distributions (exponent ~1.5).
        """
        if len(self.event_history) < 50:
            return 0.0

        sizes = np.array(self.event_history)
        sizes = sizes[sizes > 0]

        if len(sizes) < 10:
            return 0.0

        # Maximum likelihood estimation of power-law exponent
        xmin = np.min(sizes)
        n = len(sizes)

        # MLE for Pareto distribution
        exponent = 1 + n / np.sum(np.log(sizes / xmin + 1e-10))

        return float(exponent)

    def assess_criticality(self) -> CriticalityMetrics:
        """Full criticality assessment"""
        order = self.calculate_order_parameter()
        entropy = self.calculate_entropy()
        corr_length = self.calculate_correlation_length()
        susceptibility = self.calculate_susceptibility()
        exponent = self.calculate_avalanche_exponent()

        # System is critical if:
        # - Order parameter near 0.5 (between order and disorder)
        # - High correlation length
        # - High susceptibility
        # - Power-law exponent near 1.5 (sandpile universality class)

        order_score = 1 - abs(order - 0.5) * 2
        exponent_score = 1 - min(abs(exponent - 1.5), 1.0)

        critical_score = (
            0.3 * order_score +
            0.2 * min(corr_length / 10, 1.0) +
            0.2 * min(susceptibility, 1.0) +
            0.3 * exponent_score
        )

        return CriticalityMetrics(
            order_parameter=order,
            entropy=entropy,
            correlation_length=corr_length,
            susceptibility=susceptibility,
            avalanche_size_exponent=exponent,
            is_critical=critical_score > 0.6
        )


class SelfOrganizingMap:
    """
    Kohonen Self-Organizing Map.

    Unsupervised learning that preserves topology.
    """

    def __init__(
        self,
        map_size: Tuple[int, int],
        input_dim: int,
        learning_rate: float = 0.5,
        sigma: float = None
    ):
        self.map_size = map_size
        self.input_dim = input_dim
        self.learning_rate = learning_rate
        self.initial_learning_rate = learning_rate
        self.sigma = sigma or max(map_size) / 2
        self.initial_sigma = self.sigma

        # Initialize weights
        self.weights = np.random.random((map_size[0], map_size[1], input_dim))

        # Grid coordinates
        self.grid = np.array([
            [np.array([i, j]) for j in range(map_size[1])]
            for i in range(map_size[0])
        ])

        # Training state
        self.iteration = 0
        self.quantization_errors: List[float] = []

    def find_bmu(self, sample: np.ndarray) -> Tuple[int, int]:
        """Find Best Matching Unit"""
        distances = np.sum((self.weights - sample) ** 2, axis=2)
        bmu_idx = np.unravel_index(np.argmin(distances), distances.shape)
        return bmu_idx

    def neighborhood_function(
        self,
        bmu: Tuple[int, int],
        sigma: float
    ) -> np.ndarray:
        """Calculate neighborhood influence"""
        bmu_pos = np.array(bmu)

        # Distance from BMU for each neuron
        distances = np.zeros(self.map_size)
        for i in range(self.map_size[0]):
            for j in range(self.map_size[1]):
                distances[i, j] = np.sum((self.grid[i, j] - bmu_pos) ** 2)

        # Gaussian neighborhood
        return np.exp(-distances / (2 * sigma ** 2))

    def update(
        self,
        sample: np.ndarray,
        learning_rate: float,
        sigma: float
    ):
        """Update weights for one sample"""
        bmu = self.find_bmu(sample)

        # Neighborhood influence
        h = self.neighborhood_function(bmu, sigma)

        # Update weights
        for i in range(self.map_size[0]):
            for j in range(self.map_size[1]):
                influence = h[i, j] * learning_rate
                self.weights[i, j] += influence * (sample - self.weights[i, j])

        # Track quantization error
        error = np.sum((sample - self.weights[bmu]) ** 2)
        self.quantization_errors.append(error)

    def train(
        self,
        data: np.ndarray,
        epochs: int = 100,
        decay: str = 'exponential'
    ):
        """Train SOM on data"""
        n_samples = len(data)
        total_iterations = epochs * n_samples

        for epoch in range(epochs):
            # Shuffle data
            indices = np.random.permutation(n_samples)

            for idx in indices:
                sample = data[idx]

                # Decay learning rate and sigma
                progress = self.iteration / total_iterations

                if decay == 'exponential':
                    lr = self.initial_learning_rate * np.exp(-progress * 3)
                    sigma = self.initial_sigma * np.exp(-progress * 3)
                else:  # linear
                    lr = self.initial_learning_rate * (1 - progress)
                    sigma = self.initial_sigma * (1 - progress)

                sigma = max(sigma, 0.1)

                self.update(sample, lr, sigma)
                self.iteration += 1

    def map_data(self, sample: np.ndarray) -> Tuple[int, int]:
        """Map sample to grid position"""
        return self.find_bmu(sample)

    def get_u_matrix(self) -> np.ndarray:
        """Calculate U-matrix (unified distance matrix)"""
        u_matrix = np.zeros(self.map_size)

        for i in range(self.map_size[0]):
            for j in range(self.map_size[1]):
                neighbors = []

                for di, dj in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    ni, nj = i + di, j + dj
                    if 0 <= ni < self.map_size[0] and 0 <= nj < self.map_size[1]:
                        dist = np.linalg.norm(
                            self.weights[i, j] - self.weights[ni, nj]
                        )
                        neighbors.append(dist)

                u_matrix[i, j] = np.mean(neighbors) if neighbors else 0

        return u_matrix


@dataclass
class Avalanche:
    """Record of an avalanche event"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    size: int = 0
    duration: int = 0
    start_position: Tuple[int, ...] = None
    affected_cells: List[Tuple[int, ...]] = field(default_factory=list)
    peak_activity: float = 0.0


class AvalancheDynamics:
    """
    Sandpile-like avalanche dynamics.

    Demonstrates self-organized criticality.
    """

    def __init__(
        self,
        grid_size: Tuple[int, int] = (50, 50),
        threshold: float = 4.0,
        dissipation: float = 0.0
    ):
        self.grid_size = grid_size
        self.threshold = threshold
        self.dissipation = dissipation

        # Sand pile grid
        self.grid = np.zeros(grid_size)

        # Avalanche history
        self.avalanches: List[Avalanche] = []
        self.current_avalanche: Optional[Avalanche] = None

        # Statistics
        self.total_grains = 0
        self.total_topples = 0

    def add_grain(self, position: Tuple[int, int] = None):
        """Add grain to pile"""
        if position is None:
            position = (
                np.random.randint(0, self.grid_size[0]),
                np.random.randint(0, self.grid_size[1])
            )

        self.grid[position] += 1
        self.total_grains += 1

        # Check for avalanche
        if self.grid[position] >= self.threshold:
            self._trigger_avalanche(position)

    def _trigger_avalanche(self, start: Tuple[int, int]):
        """Trigger and propagate avalanche"""
        self.current_avalanche = Avalanche(
            start_position=start,
            affected_cells=[start]
        )

        # Topple until stable
        to_check = [start]

        while to_check:
            current = to_check.pop(0)

            while self.grid[current] >= self.threshold:
                self._topple(current, to_check)

        # Record avalanche
        self.current_avalanche.size = len(self.current_avalanche.affected_cells)
        self.avalanches.append(self.current_avalanche)
        self.current_avalanche = None

    def _topple(
        self,
        position: Tuple[int, int],
        to_check: List[Tuple[int, int]]
    ):
        """Topple cell and distribute grains"""
        self.grid[position] -= self.threshold
        self.total_topples += 1
        self.current_avalanche.duration += 1

        # Amount to distribute per neighbor
        distribute = (self.threshold - self.dissipation) / 4

        neighbors = [
            (position[0] - 1, position[1]),
            (position[0] + 1, position[1]),
            (position[0], position[1] - 1),
            (position[0], position[1] + 1),
        ]

        for ni, nj in neighbors:
            # Boundary conditions (open)
            if 0 <= ni < self.grid_size[0] and 0 <= nj < self.grid_size[1]:
                self.grid[ni, nj] += distribute

                if (ni, nj) not in to_check:
                    to_check.append((ni, nj))

                if (ni, nj) not in self.current_avalanche.affected_cells:
                    self.current_avalanche.affected_cells.append((ni, nj))

    def run(self, n_grains: int):
        """Run simulation by adding grains"""
        for _ in range(n_grains):
            self.add_grain()

    def get_avalanche_sizes(self) -> np.ndarray:
        """Get array of avalanche sizes"""
        return np.array([a.size for a in self.avalanches])

    def get_avalanche_durations(self) -> np.ndarray:
        """Get array of avalanche durations"""
        return np.array([a.duration for a in self.avalanches])


class EdgeOfChaos:
    """
    Maintains system at edge of chaos.

    Balances between order (frozen) and chaos (random).
    """

    def __init__(
        self,
        control_parameter: float = 0.5,
        target_criticality: float = 0.5
    ):
        self.control_parameter = control_parameter
        self.target_criticality = target_criticality

        self.criticality_detector = CriticalityDetector()

        # Adaptation
        self.adaptation_rate = 0.1
        self.history: List[float] = []

    def adapt(self, state: np.ndarray) -> float:
        """
        Adapt control parameter to maintain criticality.

        Returns new control parameter.
        """
        self.criticality_detector.record_state(state)

        metrics = self.criticality_detector.assess_criticality()
        current = metrics.order_parameter
        self.history.append(current)

        # Adjust control parameter
        error = self.target_criticality - current
        self.control_parameter += self.adaptation_rate * error

        # Keep in bounds
        self.control_parameter = max(0, min(1, self.control_parameter))

        return self.control_parameter

    def get_phase(self) -> str:
        """Get current dynamical phase"""
        if not self.history:
            return "unknown"

        avg_order = np.mean(self.history[-10:])

        if avg_order > 0.7:
            return "ordered"
        elif avg_order < 0.3:
            return "chaotic"
        else:
            return "critical"


@dataclass
class EmergentFeature:
    """Feature that emerged from self-organization"""
    name: str
    description: str
    location: Tuple[int, ...] = None
    strength: float = 0.0
    stability: float = 0.0


class EmergentStructure:
    """
    Detects structures emerging from self-organization.
    """

    def __init__(self):
        self.features: List[EmergentFeature] = []
        self.structure_history: List[np.ndarray] = []

    def record_structure(self, structure: np.ndarray):
        """Record current structure"""
        self.structure_history.append(structure.copy())

    def detect_clusters(
        self,
        structure: np.ndarray,
        threshold: float = 0.5
    ) -> List[EmergentFeature]:
        """Detect cluster structures"""
        features = []

        # Simple peak detection
        if len(structure.shape) == 2:
            for i in range(1, structure.shape[0] - 1):
                for j in range(1, structure.shape[1] - 1):
                    center = structure[i, j]
                    neighbors = [
                        structure[i-1, j], structure[i+1, j],
                        structure[i, j-1], structure[i, j+1]
                    ]

                    if center > threshold and center > max(neighbors):
                        feature = EmergentFeature(
                            name=f"cluster_{i}_{j}",
                            description="Local maximum cluster",
                            location=(i, j),
                            strength=float(center)
                        )
                        features.append(feature)

        self.features.extend(features)
        return features

    def detect_boundaries(
        self,
        structure: np.ndarray,
        gradient_threshold: float = 0.3
    ) -> List[EmergentFeature]:
        """Detect boundary structures"""
        features = []

        if len(structure.shape) == 2:
            # Gradient magnitude
            gy, gx = np.gradient(structure)
            gradient = np.sqrt(gx**2 + gy**2)

            # Find high gradient regions
            boundaries = gradient > gradient_threshold

            if np.any(boundaries):
                boundary_points = list(zip(*np.where(boundaries)))

                if boundary_points:
                    center = np.mean(boundary_points, axis=0)
                    feature = EmergentFeature(
                        name="boundary",
                        description="Phase boundary",
                        location=tuple(int(c) for c in center),
                        strength=float(np.max(gradient))
                    )
                    features.append(feature)

        self.features.extend(features)
        return features

    def calculate_stability(
        self,
        feature: EmergentFeature,
        window: int = 10
    ) -> float:
        """Calculate temporal stability of feature"""
        if len(self.structure_history) < window:
            return 0.0

        recent = self.structure_history[-window:]

        if feature.location is None:
            return 0.0

        # Check if feature persists
        persistence = 0
        for struct in recent:
            try:
                value = struct[feature.location]
                if value > feature.strength * 0.5:
                    persistence += 1
            except IndexError:
                pass

        stability = persistence / window
        feature.stability = stability
        return stability


# Export all
__all__ = [
    'CriticalityMetrics',
    'CriticalityDetector',
    'SelfOrganizingMap',
    'Avalanche',
    'AvalancheDynamics',
    'EdgeOfChaos',
    'EmergentFeature',
    'EmergentStructure',
]
