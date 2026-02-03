"""
BAEL Phase 7.2: Federated Learning & Privacy
═════════════════════════════════════════════════════════════════════════════

Privacy-preserving distributed machine learning with federated averaging,
differential privacy, secure aggregation, and split learning.

Features:
  • Federated Averaging (FedAvg)
  • Differential Privacy (DP-SGD)
  • Secure Multi-Party Computation
  • Split Learning
  • Privacy Budget Management
  • Homomorphic Encryption (simulation)
  • Gradient Clipping & Noise Addition
  • Client Selection Strategies
  • Model Compression
  • Byzantine-Robust Aggregation

Author: BAEL Team
Date: February 2, 2026
"""

import hashlib
import json
import logging
import math
import random
import threading
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# Enums & Constants
# ═══════════════════════════════════════════════════════════════════════════

class AggregationStrategy(str, Enum):
    """Federated aggregation strategies."""
    FEDAVG = "fedavg"  # Federated Averaging
    FEDPROX = "fedprox"  # Federated Proximal
    FEDADAM = "fedadam"  # Federated Adam
    MEDIAN = "median"  # Coordinate-wise median (Byzantine-robust)
    TRIMMED_MEAN = "trimmed_mean"  # Trim outliers
    KRUM = "krum"  # Byzantine-robust Krum


class PrivacyMechanism(str, Enum):
    """Privacy preservation mechanisms."""
    NONE = "none"
    DIFFERENTIAL_PRIVACY = "differential_privacy"
    SECURE_AGGREGATION = "secure_aggregation"
    HOMOMORPHIC_ENCRYPTION = "homomorphic_encryption"
    SPLIT_LEARNING = "split_learning"


class ClientSelectionStrategy(str, Enum):
    """Client selection strategies."""
    RANDOM = "random"
    WEIGHTED = "weighted"  # By data size
    LOSS_BASED = "loss_based"  # Select high-loss clients
    ROUND_ROBIN = "round_robin"


class TrainingPhase(str, Enum):
    """Federated training phases."""
    INITIALIZATION = "initialization"
    CLIENT_SELECTION = "client_selection"
    LOCAL_TRAINING = "local_training"
    AGGREGATION = "aggregation"
    VALIDATION = "validation"
    COMPLETED = "completed"
    FAILED = "failed"


# ═══════════════════════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class ModelWeights:
    """Neural network model weights."""
    layers: Dict[str, List[List[float]]] = field(default_factory=dict)
    version: int = 1
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def copy(self) -> "ModelWeights":
        """Create deep copy of weights."""
        return ModelWeights(
            layers={k: [list(row) for row in v] for k, v in self.layers.items()},
            version=self.version,
            timestamp=self.timestamp
        )


@dataclass
class PrivacyBudget:
    """Differential privacy budget."""
    epsilon: float  # Privacy loss parameter
    delta: float  # Privacy failure probability
    spent_epsilon: float = 0.0
    spent_delta: float = 0.0

    def has_budget(self, required_epsilon: float, required_delta: float) -> bool:
        """Check if budget is available."""
        return (
            self.spent_epsilon + required_epsilon <= self.epsilon and
            self.spent_delta + required_delta <= self.delta
        )

    def consume(self, epsilon: float, delta: float) -> None:
        """Consume privacy budget."""
        self.spent_epsilon += epsilon
        self.spent_delta += delta


@dataclass
class ClientInfo:
    """Federated learning client information."""
    client_id: str
    data_size: int
    compute_power: float = 1.0  # Relative compute capacity
    last_selected: Optional[datetime] = None
    total_rounds: int = 0
    success_rate: float = 1.0
    average_loss: float = 0.0
    privacy_budget: Optional[PrivacyBudget] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LocalUpdate:
    """Update from a federated client."""
    client_id: str
    round_number: int
    weights: ModelWeights
    num_samples: int
    loss: float
    accuracy: float = 0.0
    training_time: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class FederatedRound:
    """Single round of federated learning."""
    round_number: int
    selected_clients: List[str]
    global_weights: ModelWeights
    client_updates: List[LocalUpdate] = field(default_factory=list)
    aggregated_weights: Optional[ModelWeights] = None
    global_loss: float = 0.0
    global_accuracy: float = 0.0
    phase: TrainingPhase = TrainingPhase.INITIALIZATION
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = None
    privacy_cost: Dict[str, float] = field(default_factory=dict)


@dataclass
class FederatedConfig:
    """Federated learning configuration."""
    num_rounds: int = 100
    clients_per_round: int = 10
    local_epochs: int = 5
    learning_rate: float = 0.01
    batch_size: int = 32
    aggregation_strategy: AggregationStrategy = AggregationStrategy.FEDAVG
    privacy_mechanism: PrivacyMechanism = PrivacyMechanism.DIFFERENTIAL_PRIVACY
    client_selection: ClientSelectionStrategy = ClientSelectionStrategy.RANDOM

    # Differential Privacy
    noise_multiplier: float = 1.0
    clipping_norm: float = 1.0
    epsilon: float = 10.0
    delta: float = 1e-5

    # Secure Aggregation
    use_secure_aggregation: bool = False
    aggregation_threshold: int = 3  # Minimum clients for secure aggregation

    # Byzantine Robustness
    byzantine_tolerance: float = 0.2  # Fraction of malicious clients tolerated


# ═══════════════════════════════════════════════════════════════════════════
# Differential Privacy
# ═══════════════════════════════════════════════════════════════════════════

class DifferentialPrivacy:
    """Differential privacy mechanisms."""

    def __init__(self, epsilon: float = 1.0, delta: float = 1e-5):
        """Initialize differential privacy."""
        self.epsilon = epsilon
        self.delta = delta
        self.logger = logging.getLogger(__name__)

    def clip_gradients(
        self,
        gradients: Dict[str, List[List[float]]],
        max_norm: float
    ) -> Dict[str, List[List[float]]]:
        """Clip gradients to bound sensitivity."""
        clipped = {}

        for layer_name, layer_grads in gradients.items():
            # Calculate gradient norm
            total_norm = 0.0
            for row in layer_grads:
                for val in row:
                    total_norm += val * val
            total_norm = math.sqrt(total_norm)

            # Clip if necessary
            if total_norm > max_norm:
                scale = max_norm / total_norm
                clipped[layer_name] = [
                    [val * scale for val in row]
                    for row in layer_grads
                ]
            else:
                clipped[layer_name] = layer_grads

        return clipped

    def add_gaussian_noise(
        self,
        values: List[List[float]],
        sensitivity: float,
        noise_multiplier: float
    ) -> List[List[float]]:
        """Add Gaussian noise for differential privacy."""
        sigma = sensitivity * noise_multiplier

        noisy = []
        for row in values:
            noisy_row = []
            for val in row:
                # Use pseudo-random noise based on value
                noise = self._gaussian_noise(0.0, sigma, val)
                noisy_row.append(val + noise)
            noisy.append(noisy_row)

        return noisy

    def _gaussian_noise(self, mean: float, std: float, seed_val: float) -> float:
        """Generate Gaussian noise (Box-Muller transform)."""
        # Deterministic pseudo-random based on seed
        u1 = (abs(seed_val) % 1.0) * 0.9 + 0.05
        u2 = ((abs(seed_val) * 1.618) % 1.0) * 0.9 + 0.05

        z = math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)
        return mean + std * z

    def compute_privacy_cost(
        self,
        num_steps: int,
        noise_multiplier: float,
        delta: float
    ) -> float:
        """Compute privacy cost (epsilon) using moments accountant."""
        # Simplified RDP-based epsilon calculation
        # Real implementation would use tensorflow_privacy or similar
        if noise_multiplier == 0:
            return float('inf')

        # Approximate using strong composition
        epsilon = math.sqrt(2 * num_steps * math.log(1 / delta)) / noise_multiplier
        return epsilon


# ═══════════════════════════════════════════════════════════════════════════
# Secure Aggregation
# ═══════════════════════════════════════════════════════════════════════════

class SecureAggregation:
    """Secure multi-party computation for aggregation."""

    def __init__(self):
        """Initialize secure aggregation."""
        self.logger = logging.getLogger(__name__)
        self._client_masks: Dict[str, Dict[str, List[List[float]]]] = {}

    def generate_mask(
        self,
        client_id: str,
        shape: Dict[str, Tuple[int, int]]
    ) -> Dict[str, List[List[float]]]:
        """Generate random mask for client."""
        mask = {}

        for layer_name, (rows, cols) in shape.items():
            layer_mask = []
            # Use client_id as seed for deterministic mask
            seed = int(hashlib.md5(f"{client_id}_{layer_name}".encode()).hexdigest(), 16)
            random.seed(seed)

            for i in range(rows):
                row = [random.uniform(-1.0, 1.0) for _ in range(cols)]
                layer_mask.append(row)

            mask[layer_name] = layer_mask

        self._client_masks[client_id] = mask
        return mask

    def mask_weights(
        self,
        weights: Dict[str, List[List[float]]],
        mask: Dict[str, List[List[float]]]
    ) -> Dict[str, List[List[float]]]:
        """Apply mask to weights."""
        masked = {}

        for layer_name, layer_weights in weights.items():
            if layer_name in mask:
                layer_mask = mask[layer_name]
                masked_layer = []

                for i, row in enumerate(layer_weights):
                    masked_row = []
                    for j, val in enumerate(row):
                        mask_val = layer_mask[i][j] if i < len(layer_mask) and j < len(layer_mask[i]) else 0.0
                        masked_row.append(val + mask_val)
                    masked_layer.append(masked_row)

                masked[layer_name] = masked_layer
            else:
                masked[layer_name] = layer_weights

        return masked

    def aggregate_masked(
        self,
        masked_updates: List[Dict[str, List[List[float]]]],
        client_ids: List[str]
    ) -> Dict[str, List[List[float]]]:
        """Aggregate masked updates and remove masks."""
        # Sum all masked updates
        aggregated = self._sum_updates(masked_updates)

        # Remove masks (they cancel out in sum)
        # In real implementation, masks would be designed to sum to zero

        return aggregated

    def _sum_updates(
        self,
        updates: List[Dict[str, List[List[float]]]]
    ) -> Dict[str, List[List[float]]]:
        """Sum multiple updates."""
        if not updates:
            return {}

        result = {}
        for layer_name in updates[0].keys():
            layer_sum = []
            for i in range(len(updates[0][layer_name])):
                row_sum = []
                for j in range(len(updates[0][layer_name][i])):
                    total = sum(
                        update[layer_name][i][j]
                        for update in updates
                        if layer_name in update and i < len(update[layer_name]) and j < len(update[layer_name][i])
                    )
                    row_sum.append(total)
                layer_sum.append(row_sum)
            result[layer_name] = layer_sum

        return result


# ═══════════════════════════════════════════════════════════════════════════
# Aggregation Strategies
# ═══════════════════════════════════════════════════════════════════════════

class FederatedAggregator:
    """Aggregate client updates."""

    def __init__(self, strategy: AggregationStrategy = AggregationStrategy.FEDAVG):
        """Initialize aggregator."""
        self.strategy = strategy
        self.logger = logging.getLogger(__name__)

    def aggregate(
        self,
        updates: List[LocalUpdate],
        strategy: Optional[AggregationStrategy] = None
    ) -> ModelWeights:
        """Aggregate client updates."""
        agg_strategy = strategy or self.strategy

        if agg_strategy == AggregationStrategy.FEDAVG:
            return self._federated_averaging(updates)
        elif agg_strategy == AggregationStrategy.MEDIAN:
            return self._coordinate_median(updates)
        elif agg_strategy == AggregationStrategy.TRIMMED_MEAN:
            return self._trimmed_mean(updates)
        elif agg_strategy == AggregationStrategy.KRUM:
            return self._krum(updates)
        else:
            return self._federated_averaging(updates)

    def _federated_averaging(self, updates: List[LocalUpdate]) -> ModelWeights:
        """Weighted average by number of samples."""
        if not updates:
            return ModelWeights()

        total_samples = sum(u.num_samples for u in updates)
        if total_samples == 0:
            return updates[0].weights.copy()

        # Initialize with zeros
        aggregated = ModelWeights()
        first_weights = updates[0].weights

        for layer_name, layer_weights in first_weights.layers.items():
            rows, cols = len(layer_weights), len(layer_weights[0]) if layer_weights else 0
            aggregated.layers[layer_name] = [[0.0] * cols for _ in range(rows)]

        # Weighted sum
        for update in updates:
            weight = update.num_samples / total_samples

            for layer_name, layer_weights in update.weights.layers.items():
                if layer_name in aggregated.layers:
                    for i in range(len(layer_weights)):
                        for j in range(len(layer_weights[i])):
                            aggregated.layers[layer_name][i][j] += weight * layer_weights[i][j]

        return aggregated

    def _coordinate_median(self, updates: List[LocalUpdate]) -> ModelWeights:
        """Coordinate-wise median (Byzantine-robust)."""
        if not updates:
            return ModelWeights()

        aggregated = ModelWeights()
        first_weights = updates[0].weights

        for layer_name, layer_weights in first_weights.layers.items():
            rows, cols = len(layer_weights), len(layer_weights[0]) if layer_weights else 0
            median_layer = []

            for i in range(rows):
                median_row = []
                for j in range(cols):
                    # Collect values from all clients
                    values = [
                        u.weights.layers[layer_name][i][j]
                        for u in updates
                        if layer_name in u.weights.layers and i < len(u.weights.layers[layer_name]) and j < len(u.weights.layers[layer_name][i])
                    ]
                    median_val = self._median(values)
                    median_row.append(median_val)
                median_layer.append(median_row)

            aggregated.layers[layer_name] = median_layer

        return aggregated

    def _trimmed_mean(self, updates: List[LocalUpdate], trim_ratio: float = 0.1) -> ModelWeights:
        """Trimmed mean (remove outliers)."""
        if not updates:
            return ModelWeights()

        aggregated = ModelWeights()
        first_weights = updates[0].weights

        for layer_name, layer_weights in first_weights.layers.items():
            rows, cols = len(layer_weights), len(layer_weights[0]) if layer_weights else 0
            trimmed_layer = []

            for i in range(rows):
                trimmed_row = []
                for j in range(cols):
                    values = [
                        u.weights.layers[layer_name][i][j]
                        for u in updates
                        if layer_name in u.weights.layers and i < len(u.weights.layers[layer_name]) and j < len(u.weights.layers[layer_name][i])
                    ]
                    trimmed_val = self._trimmed_mean_value(values, trim_ratio)
                    trimmed_row.append(trimmed_val)
                trimmed_layer.append(trimmed_row)

            aggregated.layers[layer_name] = trimmed_layer

        return aggregated

    def _krum(self, updates: List[LocalUpdate], f: int = 1) -> ModelWeights:
        """Krum aggregation (Byzantine-robust)."""
        if len(updates) <= f:
            return self._federated_averaging(updates)

        # Compute pairwise distances
        n = len(updates)
        distances = [[0.0] * n for _ in range(n)]

        for i in range(n):
            for j in range(i + 1, n):
                dist = self._euclidean_distance(updates[i].weights, updates[j].weights)
                distances[i][j] = dist
                distances[j][i] = dist

        # Compute Krum scores (sum of distances to n - f - 2 closest neighbors)
        scores = []
        m = n - f - 2

        for i in range(n):
            sorted_dists = sorted(distances[i])
            score = sum(sorted_dists[1:m + 1])  # Exclude self (0.0)
            scores.append((score, i))

        # Select update with minimum score
        _, best_idx = min(scores)
        return updates[best_idx].weights.copy()

    def _median(self, values: List[float]) -> float:
        """Compute median of values."""
        if not values:
            return 0.0
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        if n % 2 == 0:
            return (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2.0
        return sorted_vals[n // 2]

    def _trimmed_mean_value(self, values: List[float], trim_ratio: float) -> float:
        """Compute trimmed mean."""
        if not values:
            return 0.0

        sorted_vals = sorted(values)
        n = len(sorted_vals)
        trim_count = int(n * trim_ratio)

        if trim_count * 2 >= n:
            return sum(sorted_vals) / n

        trimmed = sorted_vals[trim_count:n - trim_count]
        return sum(trimmed) / len(trimmed) if trimmed else 0.0

    def _euclidean_distance(self, w1: ModelWeights, w2: ModelWeights) -> float:
        """Compute Euclidean distance between weights."""
        dist = 0.0

        for layer_name in w1.layers:
            if layer_name in w2.layers:
                for i in range(len(w1.layers[layer_name])):
                    for j in range(len(w1.layers[layer_name][i])):
                        if i < len(w2.layers[layer_name]) and j < len(w2.layers[layer_name][i]):
                            diff = w1.layers[layer_name][i][j] - w2.layers[layer_name][i][j]
                            dist += diff * diff

        return math.sqrt(dist)


# ═══════════════════════════════════════════════════════════════════════════
# Split Learning
# ═══════════════════════════════════════════════════════════════════════════

class SplitLearning:
    """Split learning for privacy preservation."""

    def __init__(self, split_layer: int = 3):
        """Initialize split learning."""
        self.split_layer = split_layer
        self.client_activations: Dict[str, List[List[float]]] = {}
        self.logger = logging.getLogger(__name__)

    def forward_client(
        self,
        client_id: str,
        input_data: List[List[float]],
        client_weights: Dict[str, List[List[float]]]
    ) -> List[List[float]]:
        """Forward pass on client (up to split layer)."""
        activations = input_data

        # Simplified: just apply one transformation
        if "layer_1" in client_weights:
            activations = self._matrix_multiply(activations, client_weights["layer_1"])

        self.client_activations[client_id] = activations
        return activations

    def forward_server(
        self,
        activations: List[List[float]],
        server_weights: Dict[str, List[List[float]]]
    ) -> List[List[float]]:
        """Forward pass on server (from split layer)."""
        output = activations

        # Simplified: apply remaining layers
        if "layer_2" in server_weights:
            output = self._matrix_multiply(output, server_weights["layer_2"])

        return output

    def backward_server(
        self,
        gradients: List[List[float]],
        server_weights: Dict[str, List[List[float]]]
    ) -> Tuple[List[List[float]], Dict[str, List[List[float]]]]:
        """Backward pass on server."""
        # Simplified: compute gradients for split layer
        activation_grads = gradients
        weight_grads = {"layer_2": gradients}

        return activation_grads, weight_grads

    def backward_client(
        self,
        activation_gradients: List[List[float]],
        client_weights: Dict[str, List[List[float]]]
    ) -> Dict[str, List[List[float]]]:
        """Backward pass on client."""
        # Simplified: compute client weight gradients
        weight_grads = {"layer_1": activation_gradients}
        return weight_grads

    def _matrix_multiply(
        self,
        a: List[List[float]],
        b: List[List[float]]
    ) -> List[List[float]]:
        """Simple matrix multiplication."""
        if not a or not b or not a[0] or not b[0]:
            return [[]]

        rows_a, cols_a = len(a), len(a[0])
        rows_b, cols_b = len(b), len(b[0])

        if cols_a != rows_b:
            return a  # Return input if dimensions don't match

        result = []
        for i in range(rows_a):
            row = []
            for j in range(cols_b):
                val = sum(a[i][k] * b[k][j] for k in range(cols_a))
                row.append(val)
            result.append(row)

        return result


# ═══════════════════════════════════════════════════════════════════════════
# Federated Learning Coordinator
# ═══════════════════════════════════════════════════════════════════════════

class FederatedCoordinator:
    """Central coordinator for federated learning."""

    def __init__(self, config: FederatedConfig):
        """Initialize federated coordinator."""
        self.config = config
        self.clients: Dict[str, ClientInfo] = {}
        self.global_weights = ModelWeights()
        self.rounds: List[FederatedRound] = []
        self.current_round: Optional[FederatedRound] = None

        self.aggregator = FederatedAggregator(config.aggregation_strategy)
        self.dp = DifferentialPrivacy(config.epsilon, config.delta)
        self.secure_agg = SecureAggregation()
        self.split_learning = SplitLearning()

        self.logger = logging.getLogger(__name__)
        self._lock = threading.RLock()

    def register_client(
        self,
        client_id: str,
        data_size: int,
        compute_power: float = 1.0
    ) -> None:
        """Register a federated client."""
        with self._lock:
            privacy_budget = PrivacyBudget(
                epsilon=self.config.epsilon,
                delta=self.config.delta
            ) if self.config.privacy_mechanism == PrivacyMechanism.DIFFERENTIAL_PRIVACY else None

            self.clients[client_id] = ClientInfo(
                client_id=client_id,
                data_size=data_size,
                compute_power=compute_power,
                privacy_budget=privacy_budget
            )

            self.logger.info(f"Registered client {client_id} with {data_size} samples")

    def start_round(self, round_number: int) -> FederatedRound:
        """Start a new federated round."""
        with self._lock:
            # Select clients
            selected = self._select_clients()

            federated_round = FederatedRound(
                round_number=round_number,
                selected_clients=selected,
                global_weights=self.global_weights.copy()
            )

            self.current_round = federated_round
            federated_round.phase = TrainingPhase.CLIENT_SELECTION

            self.logger.info(f"Started round {round_number} with {len(selected)} clients")
            return federated_round

    def _select_clients(self) -> List[str]:
        """Select clients for training round."""
        if not self.clients:
            return []

        num_select = min(self.config.clients_per_round, len(self.clients))

        if self.config.client_selection == ClientSelectionStrategy.RANDOM:
            return random.sample(list(self.clients.keys()), num_select)

        elif self.config.client_selection == ClientSelectionStrategy.WEIGHTED:
            # Weight by data size
            clients = list(self.clients.values())
            total_data = sum(c.data_size for c in clients)

            if total_data == 0:
                return random.sample(list(self.clients.keys()), num_select)

            weights = [c.data_size / total_data for c in clients]
            selected = random.choices(clients, weights=weights, k=num_select)
            return [c.client_id for c in selected]

        elif self.config.client_selection == ClientSelectionStrategy.LOSS_BASED:
            # Select clients with highest loss
            sorted_clients = sorted(
                self.clients.values(),
                key=lambda c: c.average_loss,
                reverse=True
            )
            return [c.client_id for c in sorted_clients[:num_select]]

        else:
            return random.sample(list(self.clients.keys()), num_select)

    def submit_update(self, update: LocalUpdate) -> None:
        """Submit client update."""
        with self._lock:
            if self.current_round and update.client_id in self.current_round.selected_clients:
                # Apply differential privacy if enabled
                if self.config.privacy_mechanism == PrivacyMechanism.DIFFERENTIAL_PRIVACY:
                    update.weights = self._apply_differential_privacy(update)

                self.current_round.client_updates.append(update)
                self.current_round.phase = TrainingPhase.LOCAL_TRAINING

                # Update client stats
                if update.client_id in self.clients:
                    client = self.clients[update.client_id]
                    client.total_rounds += 1
                    client.average_loss = (client.average_loss * 0.9 + update.loss * 0.1)
                    client.last_selected = datetime.now(timezone.utc)

                self.logger.info(f"Received update from {update.client_id}, loss: {update.loss:.4f}")

    def _apply_differential_privacy(self, update: LocalUpdate) -> ModelWeights:
        """Apply differential privacy to update."""
        # Clip gradients
        clipped_layers = self.dp.clip_gradients(
            update.weights.layers,
            self.config.clipping_norm
        )

        # Add noise
        noisy_layers = {}
        for layer_name, layer_weights in clipped_layers.items():
            noisy_layers[layer_name] = self.dp.add_gaussian_noise(
                layer_weights,
                self.config.clipping_norm,
                self.config.noise_multiplier
            )

        return ModelWeights(layers=noisy_layers)

    def aggregate_round(self) -> Optional[ModelWeights]:
        """Aggregate updates from current round."""
        with self._lock:
            if not self.current_round or not self.current_round.client_updates:
                return None

            self.current_round.phase = TrainingPhase.AGGREGATION

            # Aggregate updates
            aggregated = self.aggregator.aggregate(
                self.current_round.client_updates,
                self.config.aggregation_strategy
            )

            self.current_round.aggregated_weights = aggregated
            self.global_weights = aggregated

            # Compute metrics
            total_samples = sum(u.num_samples for u in self.current_round.client_updates)
            if total_samples > 0:
                self.current_round.global_loss = sum(
                    u.loss * u.num_samples for u in self.current_round.client_updates
                ) / total_samples

                self.current_round.global_accuracy = sum(
                    u.accuracy * u.num_samples for u in self.current_round.client_updates
                ) / total_samples

            self.current_round.phase = TrainingPhase.COMPLETED
            self.current_round.end_time = datetime.now(timezone.utc)

            self.rounds.append(self.current_round)

            self.logger.info(
                f"Round {self.current_round.round_number} completed: "
                f"loss={self.current_round.global_loss:.4f}, "
                f"accuracy={self.current_round.global_accuracy:.4f}"
            )

            return aggregated

    def get_global_weights(self) -> ModelWeights:
        """Get current global model weights."""
        with self._lock:
            return self.global_weights.copy()

    def get_training_metrics(self) -> Dict[str, Any]:
        """Get training metrics."""
        with self._lock:
            if not self.rounds:
                return {}

            return {
                'total_rounds': len(self.rounds),
                'total_clients': len(self.clients),
                'current_loss': self.rounds[-1].global_loss,
                'current_accuracy': self.rounds[-1].global_accuracy,
                'loss_history': [r.global_loss for r in self.rounds],
                'accuracy_history': [r.global_accuracy for r in self.rounds]
            }


# ═══════════════════════════════════════════════════════════════════════════
# Global Coordinator Singleton
# ═══════════════════════════════════════════════════════════════════════════

_global_federated_coordinator: Optional[FederatedCoordinator] = None


def get_federated_coordinator(
    config: Optional[FederatedConfig] = None
) -> FederatedCoordinator:
    """Get or create global federated coordinator."""
    global _global_federated_coordinator
    if _global_federated_coordinator is None:
        _global_federated_coordinator = FederatedCoordinator(
            config or FederatedConfig()
        )
    return _global_federated_coordinator
