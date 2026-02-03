"""
Experience Replay Buffers for Continual Learning

Replay buffers store experiences from previous tasks and
replay them during new task learning to prevent forgetting.

Key Concepts:
- Reservoir Sampling for bounded memory
- Prioritized Experience Replay
- Gradient-based sample selection
- Diverse coverage strategies

These complement EWC and PackNet for comprehensive
continual learning.
"""

import logging
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import math
from collections import deque
import heapq

logger = logging.getLogger("BAEL.ReplayBuffer")


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class Experience:
    """A stored learning experience."""
    id: str
    task_id: str
    input_data: Any
    output_data: Any
    loss: float = 0.0
    priority: float = 1.0
    importance: float = 1.0
    visits: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def update_access(self) -> None:
        """Update access tracking."""
        self.visits += 1
        self.last_accessed = datetime.now()


@dataclass
class BatchSample:
    """A batch of sampled experiences."""
    experiences: List[Experience]
    weights: List[float]
    indices: List[int]
    
    @property
    def size(self) -> int:
        return len(self.experiences)


# =============================================================================
# BASE REPLAY BUFFER
# =============================================================================

class ReplayBuffer(ABC):
    """Abstract base class for replay buffers."""
    
    @abstractmethod
    def add(self, experience: Experience) -> None:
        """Add an experience to the buffer."""
        pass
    
    @abstractmethod
    def sample(self, batch_size: int) -> BatchSample:
        """Sample a batch of experiences."""
        pass
    
    @abstractmethod
    def update_priorities(self, indices: List[int], priorities: List[float]) -> None:
        """Update priorities for sampled experiences."""
        pass
    
    @abstractmethod
    def __len__(self) -> int:
        """Get buffer size."""
        pass


# =============================================================================
# UNIFORM REPLAY BUFFER
# =============================================================================

class ExperienceReplayBuffer(ReplayBuffer):
    """
    Standard experience replay buffer with uniform sampling.
    
    Uses reservoir sampling to maintain a bounded buffer
    while giving all experiences equal chance of being retained.
    """
    
    def __init__(self, capacity: int = 10000):
        self.capacity = capacity
        self.buffer: List[Experience] = []
        self.position = 0
        self.total_added = 0
        
        # Task-level statistics
        self.task_counts: Dict[str, int] = {}
    
    def add(self, experience: Experience) -> None:
        """Add experience using reservoir sampling."""
        self.total_added += 1
        
        if len(self.buffer) < self.capacity:
            self.buffer.append(experience)
        else:
            # Reservoir sampling: replace with decreasing probability
            idx = random.randint(0, self.total_added - 1)
            if idx < self.capacity:
                old_task = self.buffer[idx].task_id
                self.task_counts[old_task] = self.task_counts.get(old_task, 1) - 1
                self.buffer[idx] = experience
        
        # Track task counts
        task_id = experience.task_id
        self.task_counts[task_id] = self.task_counts.get(task_id, 0) + 1
    
    def sample(self, batch_size: int) -> BatchSample:
        """Uniformly sample a batch."""
        batch_size = min(batch_size, len(self.buffer))
        indices = random.sample(range(len(self.buffer)), batch_size)
        
        experiences = [self.buffer[i] for i in indices]
        weights = [1.0 / len(self.buffer)] * batch_size
        
        for exp in experiences:
            exp.update_access()
        
        return BatchSample(experiences=experiences, weights=weights, indices=indices)
    
    def sample_by_task(self, task_id: str, batch_size: int) -> BatchSample:
        """Sample experiences from a specific task."""
        task_experiences = [
            (i, exp) for i, exp in enumerate(self.buffer)
            if exp.task_id == task_id
        ]
        
        if not task_experiences:
            return BatchSample(experiences=[], weights=[], indices=[])
        
        batch_size = min(batch_size, len(task_experiences))
        sampled = random.sample(task_experiences, batch_size)
        
        indices = [i for i, _ in sampled]
        experiences = [exp for _, exp in sampled]
        weights = [1.0 / len(task_experiences)] * batch_size
        
        return BatchSample(experiences=experiences, weights=weights, indices=indices)
    
    def update_priorities(self, indices: List[int], priorities: List[float]) -> None:
        """Update priorities (no-op for uniform buffer)."""
        for i, priority in zip(indices, priorities):
            if 0 <= i < len(self.buffer):
                self.buffer[i].priority = priority
    
    def get_task_distribution(self) -> Dict[str, float]:
        """Get distribution of experiences across tasks."""
        total = len(self.buffer)
        if total == 0:
            return {}
        return {task: count / total for task, count in self.task_counts.items()}
    
    def __len__(self) -> int:
        return len(self.buffer)


# =============================================================================
# PRIORITIZED REPLAY BUFFER
# =============================================================================

class SumTree:
    """
    Sum tree data structure for efficient prioritized sampling.
    
    Supports O(log n) updates and O(log n) sampling.
    """
    
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.tree = [0.0] * (2 * capacity - 1)
        self.data = [None] * capacity
        self.position = 0
        self.count = 0
    
    def _propagate(self, idx: int, change: float) -> None:
        """Propagate priority change up the tree."""
        parent = (idx - 1) // 2
        self.tree[parent] += change
        if parent != 0:
            self._propagate(parent, change)
    
    def _retrieve(self, idx: int, value: float) -> int:
        """Find leaf node for a given value."""
        left = 2 * idx + 1
        right = left + 1
        
        if left >= len(self.tree):
            return idx
        
        if value <= self.tree[left]:
            return self._retrieve(left, value)
        else:
            return self._retrieve(right, value - self.tree[left])
    
    @property
    def total(self) -> float:
        """Total priority sum."""
        return self.tree[0]
    
    def add(self, priority: float, data: Any) -> None:
        """Add data with priority."""
        idx = self.position + self.capacity - 1
        
        self.data[self.position] = data
        self.update(idx, priority)
        
        self.position = (self.position + 1) % self.capacity
        self.count = min(self.count + 1, self.capacity)
    
    def update(self, idx: int, priority: float) -> None:
        """Update priority at index."""
        change = priority - self.tree[idx]
        self.tree[idx] = priority
        self._propagate(idx, change)
    
    def get(self, value: float) -> Tuple[int, float, Any]:
        """Get data for a sampled value."""
        idx = self._retrieve(0, value)
        data_idx = idx - self.capacity + 1
        return idx, self.tree[idx], self.data[data_idx]


class PrioritizedReplayBuffer(ReplayBuffer):
    """
    Prioritized Experience Replay buffer.
    
    Samples experiences based on their TD-error or loss,
    giving more importance to surprising experiences.
    
    Reference: Schaul et al., 2016
    """
    
    def __init__(
        self,
        capacity: int = 10000,
        alpha: float = 0.6,
        beta: float = 0.4,
        beta_increment: float = 0.001,
        epsilon: float = 1e-6
    ):
        """
        Initialize prioritized buffer.
        
        Args:
            capacity: Maximum buffer size
            alpha: Priority exponent (0 = uniform, 1 = full prioritization)
            beta: Importance sampling exponent (annealed to 1)
            beta_increment: Beta increase per sample
            epsilon: Small constant to ensure non-zero priority
        """
        self.capacity = capacity
        self.alpha = alpha
        self.beta = beta
        self.beta_increment = beta_increment
        self.epsilon = epsilon
        
        self.tree = SumTree(capacity)
        self.max_priority = 1.0
    
    def add(self, experience: Experience) -> None:
        """Add experience with max priority."""
        priority = self._compute_priority(experience.loss)
        self.tree.add(priority, experience)
    
    def _compute_priority(self, loss: float) -> float:
        """Compute priority from loss."""
        return (abs(loss) + self.epsilon) ** self.alpha
    
    def sample(self, batch_size: int) -> BatchSample:
        """Sample based on priorities."""
        experiences = []
        indices = []
        priorities = []
        
        segment = self.tree.total / batch_size
        
        # Anneal beta
        self.beta = min(1.0, self.beta + self.beta_increment)
        
        for i in range(batch_size):
            low = segment * i
            high = segment * (i + 1)
            value = random.uniform(low, high)
            
            idx, priority, experience = self.tree.get(value)
            
            if experience is not None:
                experiences.append(experience)
                indices.append(idx)
                priorities.append(priority)
                experience.update_access()
        
        # Compute importance sampling weights
        if not priorities:
            return BatchSample(experiences=[], weights=[], indices=[])
        
        total_priority = self.tree.total
        min_prob = min(priorities) / total_priority
        max_weight = (len(self.tree.data) * min_prob) ** (-self.beta)
        
        weights = []
        for priority in priorities:
            prob = priority / total_priority
            weight = (len(self.tree.data) * prob) ** (-self.beta)
            weights.append(weight / max_weight)  # Normalize
        
        return BatchSample(experiences=experiences, weights=weights, indices=indices)
    
    def update_priorities(self, indices: List[int], priorities: List[float]) -> None:
        """Update priorities based on new losses."""
        for idx, priority in zip(indices, priorities):
            priority = self._compute_priority(priority)
            self.tree.update(idx, priority)
            self.max_priority = max(self.max_priority, priority)
    
    def __len__(self) -> int:
        return self.tree.count


# =============================================================================
# DIVERSE REPLAY BUFFER
# =============================================================================

class DiverseReplayBuffer(ReplayBuffer):
    """
    Replay buffer with diversity-aware sampling.
    
    Ensures samples cover different regions of the input space
    and balance across tasks.
    """
    
    def __init__(
        self,
        capacity: int = 10000,
        num_clusters: int = 10
    ):
        self.capacity = capacity
        self.num_clusters = num_clusters
        
        # Cluster-based storage
        self.clusters: List[List[Experience]] = [[] for _ in range(num_clusters)]
        self.total_count = 0
        
        # Task balance
        self.task_quotas: Dict[str, int] = {}
    
    def add(self, experience: Experience) -> None:
        """Add experience to appropriate cluster."""
        # Simple hash-based clustering
        cluster_id = hash(str(experience.input_data)) % self.num_clusters
        
        if self.total_count < self.capacity:
            self.clusters[cluster_id].append(experience)
            self.total_count += 1
        else:
            # Replace within same cluster (maintains diversity)
            if self.clusters[cluster_id]:
                # Replace oldest
                self.clusters[cluster_id].pop(0)
                self.clusters[cluster_id].append(experience)
    
    def sample(self, batch_size: int) -> BatchSample:
        """Sample with diversity across clusters."""
        experiences = []
        indices = []
        
        # Sample proportionally from each cluster
        non_empty = [i for i, c in enumerate(self.clusters) if c]
        if not non_empty:
            return BatchSample(experiences=[], weights=[], indices=[])
        
        per_cluster = max(1, batch_size // len(non_empty))
        
        for cluster_id in non_empty:
            cluster = self.clusters[cluster_id]
            n_samples = min(per_cluster, len(cluster))
            sampled = random.sample(range(len(cluster)), n_samples)
            
            for i in sampled:
                experiences.append(cluster[i])
                indices.append((cluster_id, i))  # 2D index
                cluster[i].update_access()
        
        weights = [1.0 / len(experiences)] * len(experiences)
        return BatchSample(experiences=experiences, weights=weights, indices=indices)
    
    def sample_balanced(self, batch_size: int) -> BatchSample:
        """Sample with balance across tasks."""
        # Group by task
        task_experiences: Dict[str, List[Experience]] = {}
        for cluster in self.clusters:
            for exp in cluster:
                if exp.task_id not in task_experiences:
                    task_experiences[exp.task_id] = []
                task_experiences[exp.task_id].append(exp)
        
        if not task_experiences:
            return BatchSample(experiences=[], weights=[], indices=[])
        
        # Sample equally from each task
        per_task = max(1, batch_size // len(task_experiences))
        experiences = []
        
        for task_id, exps in task_experiences.items():
            n_samples = min(per_task, len(exps))
            sampled = random.sample(exps, n_samples)
            experiences.extend(sampled)
        
        weights = [1.0 / len(experiences)] * len(experiences)
        return BatchSample(experiences=experiences, weights=weights, indices=[])
    
    def update_priorities(self, indices: List[int], priorities: List[float]) -> None:
        """Update priorities."""
        # For diverse buffer, priorities are secondary
        pass
    
    def __len__(self) -> int:
        return self.total_count


# =============================================================================
# GRADIENT-BASED REPLAY
# =============================================================================

class GradientReplayBuffer(ReplayBuffer):
    """
    Gradient-based experience replay.
    
    Selects experiences that would most affect current gradients,
    providing targeted replay to prevent forgetting.
    """
    
    def __init__(self, capacity: int = 10000):
        self.capacity = capacity
        self.buffer: List[Experience] = []
        self.gradient_cache: Dict[str, List[float]] = {}
    
    def add(self, experience: Experience) -> None:
        """Add experience."""
        if len(self.buffer) < self.capacity:
            self.buffer.append(experience)
        else:
            # Replace least important
            min_idx = min(
                range(len(self.buffer)),
                key=lambda i: self.buffer[i].importance
            )
            self.buffer[min_idx] = experience
    
    def update_gradients(
        self,
        exp_id: str,
        gradients: List[float]
    ) -> None:
        """Store gradient information for an experience."""
        self.gradient_cache[exp_id] = gradients
    
    def sample(self, batch_size: int) -> BatchSample:
        """Sample experiences with gradient-based selection."""
        if not self.buffer:
            return BatchSample(experiences=[], weights=[], indices=[])
        
        # Score by gradient magnitude (cached)
        scored = []
        for i, exp in enumerate(self.buffer):
            grads = self.gradient_cache.get(exp.id, [])
            grad_norm = sum(g ** 2 for g in grads) ** 0.5 if grads else exp.importance
            scored.append((i, exp, grad_norm))
        
        # Sample with probability proportional to gradient norm
        total_grad = sum(s[2] for s in scored)
        if total_grad == 0:
            # Uniform sampling fallback
            indices = random.sample(range(len(self.buffer)), min(batch_size, len(self.buffer)))
            experiences = [self.buffer[i] for i in indices]
            weights = [1.0] * len(experiences)
        else:
            probs = [s[2] / total_grad for s in scored]
            indices = random.choices(
                range(len(scored)),
                weights=probs,
                k=min(batch_size, len(scored))
            )
            experiences = [self.buffer[i] for i in indices]
            weights = [probs[i] * len(scored) for i in indices]  # Importance weights
        
        return BatchSample(experiences=experiences, weights=weights, indices=indices)
    
    def update_priorities(self, indices: List[int], priorities: List[float]) -> None:
        """Update importance scores."""
        for i, priority in zip(indices, priorities):
            if 0 <= i < len(self.buffer):
                self.buffer[i].importance = priority
    
    def __len__(self) -> int:
        return len(self.buffer)


# =============================================================================
# DEMO
# =============================================================================

def demo():
    """Demonstrate replay buffer capabilities."""
    print("Experience Replay Buffer Demo")
    print("=" * 60)
    
    # Create buffers
    uniform = ExperienceReplayBuffer(capacity=100)
    prioritized = PrioritizedReplayBuffer(capacity=100)
    diverse = DiverseReplayBuffer(capacity=100)
    
    # Add experiences
    for i in range(50):
        exp = Experience(
            id=f"exp_{i}",
            task_id=f"task_{i % 3}",
            input_data={"x": i},
            output_data={"y": i * 2},
            loss=random.random()
        )
        uniform.add(exp)
        prioritized.add(exp)
        diverse.add(exp)
    
    # Sample
    print("\nUniform Sampling:")
    batch = uniform.sample(5)
    print(f"  Sampled {batch.size} experiences")
    print(f"  Tasks: {[e.task_id for e in batch.experiences]}")
    
    print("\nPrioritized Sampling:")
    batch = prioritized.sample(5)
    print(f"  Sampled {batch.size} experiences")
    print(f"  Weights: {[f'{w:.3f}' for w in batch.weights]}")
    
    print("\nDiverse Sampling:")
    batch = diverse.sample(5)
    print(f"  Sampled {batch.size} experiences")
    
    batch = diverse.sample_balanced(9)
    print(f"  Balanced sample: {batch.size} experiences")
    print(f"  Tasks: {[e.task_id for e in batch.experiences]}")
    
    print(f"\nTask distribution (uniform): {uniform.get_task_distribution()}")


if __name__ == "__main__":
    demo()
