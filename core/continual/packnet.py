"""
PackNet Implementation for Continual Learning

PackNet is a parameter isolation approach that prevents forgetting
by identifying and freezing the most important weights for each task.

Key Concepts:
- Network pruning identifies important weights
- Binary masks protect task-specific weights
- Remaining capacity used for new tasks
- No forgetting by design (weights are frozen)

Reference: Mallya & Lazebnik, 2018
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple
import math
from collections import defaultdict

logger = logging.getLogger("BAEL.PackNet")


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class NetworkMask:
    """
    Binary mask for a neural network layer.
    
    The mask indicates which weights are:
    - Available (can be trained)
    - Frozen (protected for a previous task)
    - Pruned (permanently removed)
    """
    layer_name: str
    total_weights: int
    frozen_weights: Set[int] = field(default_factory=set)
    pruned_weights: Set[int] = field(default_factory=set)
    task_assignments: Dict[str, Set[int]] = field(default_factory=dict)
    
    @property
    def available_weights(self) -> Set[int]:
        """Weights available for new tasks."""
        all_indices = set(range(self.total_weights))
        return all_indices - self.frozen_weights - self.pruned_weights
    
    @property
    def utilization(self) -> float:
        """Fraction of weights currently in use."""
        return len(self.frozen_weights) / self.total_weights
    
    @property
    def capacity_remaining(self) -> float:
        """Fraction of weights available for new tasks."""
        return len(self.available_weights) / self.total_weights
    
    def freeze_for_task(self, task_id: str, weight_indices: Set[int]) -> None:
        """Freeze weights for a specific task."""
        self.task_assignments[task_id] = weight_indices
        self.frozen_weights.update(weight_indices)
    
    def prune_weights(self, weight_indices: Set[int]) -> None:
        """Permanently prune weights."""
        self.pruned_weights.update(weight_indices)
    
    def get_mask_array(self) -> List[bool]:
        """Get mask as boolean array (True = trainable)."""
        return [
            i in self.available_weights
            for i in range(self.total_weights)
        ]


@dataclass
class TaskCapacity:
    """Tracks capacity allocation for a task."""
    task_id: str
    layers: Dict[str, int]  # layer_name -> num_weights
    total_weights: int
    percentage: float
    created_at: datetime = field(default_factory=datetime.now)


# =============================================================================
# PACKNET IMPLEMENTATION
# =============================================================================

class PackNet:
    """
    PackNet for parameter isolation in continual learning.
    
    PackNet prevents catastrophic forgetting by:
    1. Training network on a task
    2. Pruning unimportant weights
    3. Freezing important weights
    4. Using freed capacity for new tasks
    
    This guarantees zero forgetting since frozen weights
    cannot change during subsequent training.
    """
    
    def __init__(
        self,
        pruning_percentage: float = 0.5,
        importance_metric: str = "magnitude"
    ):
        """
        Initialize PackNet.
        
        Args:
            pruning_percentage: Fraction of weights to prune after each task
            importance_metric: How to measure weight importance
                              ("magnitude", "gradient", "fisher")
        """
        self.pruning_percentage = pruning_percentage
        self.importance_metric = importance_metric
        
        # Network masks per layer
        self.layer_masks: Dict[str, NetworkMask] = {}
        
        # Capacity tracking
        self.task_capacities: Dict[str, TaskCapacity] = {}
        
        # Current task being trained
        self.current_task: Optional[str] = None
        
        # Metrics
        self.metrics = {
            "tasks_packed": 0,
            "total_weights_frozen": 0,
            "total_weights_pruned": 0,
            "average_utilization": 0.0
        }
    
    def register_layer(self, layer_name: str, num_weights: int) -> None:
        """Register a network layer for packing."""
        self.layer_masks[layer_name] = NetworkMask(
            layer_name=layer_name,
            total_weights=num_weights
        )
        logger.debug(f"Registered layer {layer_name} with {num_weights} weights")
    
    def start_task(self, task_id: str) -> Dict[str, List[bool]]:
        """
        Start training a new task.
        
        Returns masks indicating which weights are trainable.
        """
        self.current_task = task_id
        
        masks = {}
        for layer_name, mask in self.layer_masks.items():
            masks[layer_name] = mask.get_mask_array()
            
            available = mask.capacity_remaining * 100
            logger.debug(f"Layer {layer_name}: {available:.1f}% capacity available")
        
        return masks
    
    def compute_importance(
        self,
        layer_name: str,
        weights: List[float],
        gradients: Optional[List[float]] = None
    ) -> List[float]:
        """
        Compute importance scores for weights.
        
        Args:
            layer_name: Name of the layer
            weights: Current weight values
            gradients: Gradient values (for gradient-based importance)
        
        Returns:
            Importance score for each weight
        """
        if self.importance_metric == "magnitude":
            # Weight magnitude as importance
            return [abs(w) for w in weights]
        
        elif self.importance_metric == "gradient":
            if gradients is None:
                raise ValueError("Gradients required for gradient-based importance")
            # Gradient magnitude
            return [abs(g) for g in gradients]
        
        elif self.importance_metric == "fisher":
            if gradients is None:
                raise ValueError("Gradients required for Fisher-based importance")
            # Fisher information approximation
            return [g ** 2 for g in gradients]
        
        else:
            raise ValueError(f"Unknown importance metric: {self.importance_metric}")
    
    def pack_task(
        self,
        task_id: str,
        layer_weights: Dict[str, List[float]],
        layer_gradients: Optional[Dict[str, List[float]]] = None
    ) -> Dict[str, Set[int]]:
        """
        Pack a completed task by freezing important weights.
        
        Args:
            task_id: Task identifier
            layer_weights: Weights for each layer
            layer_gradients: Gradients for each layer
        
        Returns:
            Indices of frozen weights per layer
        """
        logger.info(f"Packing task {task_id}")
        
        if task_id != self.current_task:
            logger.warning(f"Packing task {task_id} but current is {self.current_task}")
        
        frozen_weights = {}
        total_frozen = 0
        total_pruned = 0
        
        for layer_name, weights in layer_weights.items():
            mask = self.layer_masks.get(layer_name)
            if mask is None:
                continue
            
            gradients = layer_gradients.get(layer_name) if layer_gradients else None
            
            # Get available weight indices
            available = list(mask.available_weights)
            if not available:
                logger.warning(f"No available weights in layer {layer_name}")
                continue
            
            # Compute importance for available weights
            importance = self.compute_importance(layer_name, weights, gradients)
            
            # Filter to only available weights
            available_importance = [
                (i, importance[i]) for i in available
                if i < len(importance)
            ]
            
            if not available_importance:
                continue
            
            # Sort by importance (descending)
            available_importance.sort(key=lambda x: x[1], reverse=True)
            
            # Keep top weights, prune the rest
            num_to_keep = int(len(available_importance) * (1 - self.pruning_percentage))
            num_to_keep = max(1, num_to_keep)  # Keep at least 1
            
            keep_indices = set(i for i, _ in available_importance[:num_to_keep])
            prune_indices = set(i for i, _ in available_importance[num_to_keep:])
            
            # Freeze kept weights for this task
            mask.freeze_for_task(task_id, keep_indices)
            mask.prune_weights(prune_indices)
            
            frozen_weights[layer_name] = keep_indices
            total_frozen += len(keep_indices)
            total_pruned += len(prune_indices)
            
            logger.debug(
                f"Layer {layer_name}: frozen {len(keep_indices)}, "
                f"pruned {len(prune_indices)}"
            )
        
        # Track capacity
        self.task_capacities[task_id] = TaskCapacity(
            task_id=task_id,
            layers={ln: len(fw) for ln, fw in frozen_weights.items()},
            total_weights=total_frozen,
            percentage=total_frozen / self._total_network_weights()
        )
        
        # Update metrics
        self.metrics["tasks_packed"] += 1
        self.metrics["total_weights_frozen"] += total_frozen
        self.metrics["total_weights_pruned"] += total_pruned
        self.metrics["average_utilization"] = self._compute_average_utilization()
        
        self.current_task = None
        
        return frozen_weights
    
    def _total_network_weights(self) -> int:
        """Get total weights in network."""
        return sum(m.total_weights for m in self.layer_masks.values())
    
    def _compute_average_utilization(self) -> float:
        """Compute average network utilization."""
        if not self.layer_masks:
            return 0.0
        return sum(m.utilization for m in self.layer_masks.values()) / len(self.layer_masks)
    
    def get_task_mask(self, task_id: str) -> Dict[str, List[bool]]:
        """
        Get mask for a specific task (for inference).
        
        During inference, only the task's frozen weights should be active.
        """
        masks = {}
        
        for layer_name, mask in self.layer_masks.items():
            task_weights = mask.task_assignments.get(task_id, set())
            masks[layer_name] = [
                i in task_weights
                for i in range(mask.total_weights)
            ]
        
        return masks
    
    def can_fit_new_task(self, estimated_capacity_needed: float = 0.1) -> bool:
        """Check if there's enough capacity for a new task."""
        for mask in self.layer_masks.values():
            if mask.capacity_remaining < estimated_capacity_needed:
                return False
        return True
    
    def get_capacity_report(self) -> Dict[str, Any]:
        """Get detailed capacity report."""
        report = {
            "layers": {},
            "total_capacity_remaining": 0.0,
            "tasks_packed": len(self.task_capacities)
        }
        
        total_remaining = 0
        total_weights = 0
        
        for layer_name, mask in self.layer_masks.items():
            report["layers"][layer_name] = {
                "total_weights": mask.total_weights,
                "frozen": len(mask.frozen_weights),
                "pruned": len(mask.pruned_weights),
                "available": len(mask.available_weights),
                "utilization": mask.utilization,
                "capacity_remaining": mask.capacity_remaining
            }
            total_remaining += len(mask.available_weights)
            total_weights += mask.total_weights
        
        report["total_capacity_remaining"] = total_remaining / total_weights if total_weights else 0
        
        return report
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get PackNet metrics."""
        return {
            **self.metrics,
            "num_layers": len(self.layer_masks),
            "total_network_weights": self._total_network_weights(),
            "current_task": self.current_task
        }


# =============================================================================
# PROGRESSIVE PACKNET
# =============================================================================

class ProgressivePackNet(PackNet):
    """
    Progressive PackNet with dynamic capacity allocation.
    
    Instead of fixed pruning percentage, allocates capacity
    based on task complexity and network availability.
    """
    
    def __init__(self, min_capacity_per_task: float = 0.05, **kwargs):
        super().__init__(**kwargs)
        self.min_capacity_per_task = min_capacity_per_task
        self.complexity_estimates: Dict[str, float] = {}
    
    def estimate_task_complexity(
        self,
        task_id: str,
        num_examples: int,
        validation_accuracy: float
    ) -> float:
        """
        Estimate task complexity based on learning metrics.
        
        Higher complexity = more capacity needed.
        """
        # More examples and lower accuracy = more complex
        base_complexity = math.log10(num_examples + 1) / 10
        accuracy_factor = 1 - validation_accuracy  # Higher if harder to learn
        
        complexity = min(1.0, base_complexity + accuracy_factor)
        self.complexity_estimates[task_id] = complexity
        
        return complexity
    
    def compute_adaptive_pruning(self, task_id: str) -> float:
        """
        Compute adaptive pruning percentage based on task complexity.
        """
        complexity = self.complexity_estimates.get(task_id, 0.5)
        
        # More complex tasks keep more weights
        # Less complex tasks prune more aggressively
        pruning = self.pruning_percentage * (1 - 0.5 * complexity)
        
        # Ensure minimum capacity for future tasks
        avg_remaining = self._compute_average_capacity_remaining()
        if avg_remaining < 0.3:
            # Running low on capacity, prune more aggressively
            pruning = min(0.8, pruning * 1.5)
        
        return pruning
    
    def _compute_average_capacity_remaining(self) -> float:
        """Compute average remaining capacity across layers."""
        if not self.layer_masks:
            return 1.0
        return sum(m.capacity_remaining for m in self.layer_masks.values()) / len(self.layer_masks)


# =============================================================================
# DEMO
# =============================================================================

def demo():
    """Demonstrate PackNet capabilities."""
    print("PackNet Demo")
    print("=" * 60)
    
    packnet = PackNet(pruning_percentage=0.5)
    
    # Register network layers
    packnet.register_layer("layer1", 100)
    packnet.register_layer("layer2", 200)
    packnet.register_layer("layer3", 50)
    
    # Task 1
    print("\n--- Task 1 ---")
    masks = packnet.start_task("task1")
    print(f"Available for training: {sum(sum(m) for m in masks.values())} weights")
    
    # Simulate training and pack
    import random
    weights = {
        "layer1": [random.random() for _ in range(100)],
        "layer2": [random.random() for _ in range(200)],
        "layer3": [random.random() for _ in range(50)]
    }
    frozen = packnet.pack_task("task1", weights)
    print(f"Frozen: {sum(len(f) for f in frozen.values())} weights")
    
    # Task 2
    print("\n--- Task 2 ---")
    masks = packnet.start_task("task2")
    print(f"Available for training: {sum(sum(m) for m in masks.values())} weights")
    
    weights = {
        "layer1": [random.random() for _ in range(100)],
        "layer2": [random.random() for _ in range(200)],
        "layer3": [random.random() for _ in range(50)]
    }
    frozen = packnet.pack_task("task2", weights)
    print(f"Frozen: {sum(len(f) for f in frozen.values())} weights")
    
    # Capacity report
    print("\n--- Capacity Report ---")
    report = packnet.get_capacity_report()
    print(f"Tasks packed: {report['tasks_packed']}")
    print(f"Total capacity remaining: {report['total_capacity_remaining']:.1%}")
    
    for layer, info in report["layers"].items():
        print(f"  {layer}: {info['capacity_remaining']:.1%} available")
    
    print(f"\nMetrics: {packnet.get_metrics()}")


if __name__ == "__main__":
    demo()
