#!/usr/bin/env python3
"""
BAEL - Resource Optimizer
Advanced resource optimization and allocation system.

This module implements sophisticated optimization algorithms
for maximizing resource utilization while minimizing costs,
following the zero-invest mindstate principle.

Features:
- Multi-objective optimization
- Resource pool management
- Dynamic allocation algorithms
- Cost-benefit analysis
- Load balancing
- Capacity planning
- Throttling and quotas
- Resource prediction
- Waste elimination
- Efficiency metrics
- Constraint satisfaction
- Pareto optimization
"""

import asyncio
import heapq
import logging
import math
import random
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Callable, Dict, Generic, List, Optional, Set, Tuple,
                    TypeVar, Union)
from uuid import uuid4

logger = logging.getLogger(__name__)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class ResourceType(Enum):
    """Types of resources."""
    CPU = "cpu"
    MEMORY = "memory"
    GPU = "gpu"
    STORAGE = "storage"
    NETWORK = "network"
    API_CALLS = "api_calls"
    TOKENS = "tokens"
    COMPUTE_TIME = "compute_time"
    CONCURRENT_TASKS = "concurrent_tasks"


class ResourceState(Enum):
    """State of a resource."""
    AVAILABLE = "available"
    ALLOCATED = "allocated"
    RESERVED = "reserved"
    EXHAUSTED = "exhausted"
    ERROR = "error"


class AllocationStrategy(Enum):
    """Resource allocation strategies."""
    FIRST_FIT = "first_fit"
    BEST_FIT = "best_fit"
    WORST_FIT = "worst_fit"
    ROUND_ROBIN = "round_robin"
    PRIORITY_BASED = "priority_based"
    COST_OPTIMIZED = "cost_optimized"
    BALANCED = "balanced"


class OptimizationGoal(Enum):
    """Optimization goals."""
    MINIMIZE_COST = "minimize_cost"
    MAXIMIZE_THROUGHPUT = "maximize_throughput"
    MINIMIZE_LATENCY = "minimize_latency"
    MAXIMIZE_UTILIZATION = "maximize_utilization"
    BALANCE_LOAD = "balance_load"


class ConstraintType(Enum):
    """Types of constraints."""
    HARD = "hard"      # Must be satisfied
    SOFT = "soft"      # Preferred but not required
    BUDGET = "budget"  # Resource budget


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class ResourceQuota:
    """Quota definition for a resource."""
    resource_type: ResourceType = ResourceType.API_CALLS
    limit: float = 1000.0
    period_seconds: float = 3600.0  # Per hour
    used: float = 0.0
    reset_at: datetime = field(default_factory=datetime.now)

    def is_exceeded(self) -> bool:
        """Check if quota is exceeded."""
        return self.used >= self.limit

    def remaining(self) -> float:
        """Get remaining quota."""
        return max(0, self.limit - self.used)

    def reset_if_needed(self) -> None:
        """Reset quota if period has passed."""
        now = datetime.now()
        if (now - self.reset_at).total_seconds() >= self.period_seconds:
            self.used = 0.0
            self.reset_at = now


@dataclass
class Resource:
    """A resource instance."""
    id: str = field(default_factory=lambda: str(uuid4()))
    type: ResourceType = ResourceType.CPU
    name: str = ""
    capacity: float = 100.0
    allocated: float = 0.0
    state: ResourceState = ResourceState.AVAILABLE
    cost_per_unit: float = 0.0
    provider: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)

    @property
    def available(self) -> float:
        """Get available capacity."""
        return self.capacity - self.allocated

    @property
    def utilization(self) -> float:
        """Get utilization percentage."""
        if self.capacity == 0:
            return 0.0
        return (self.allocated / self.capacity) * 100

    @property
    def is_free(self) -> bool:
        """Check if resource is free (zero cost)."""
        return self.cost_per_unit == 0


@dataclass
class ResourceRequest:
    """A request for resources."""
    id: str = field(default_factory=lambda: str(uuid4()))
    resource_type: ResourceType = ResourceType.CPU
    amount: float = 1.0
    priority: int = 5  # 1=highest, 10=lowest
    requester: str = ""
    deadline: Optional[datetime] = None
    max_cost: Optional[float] = None
    prefer_free: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Allocation:
    """A resource allocation."""
    id: str = field(default_factory=lambda: str(uuid4()))
    request_id: str = ""
    resource_id: str = ""
    amount: float = 0.0
    cost: float = 0.0
    allocated_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    released: bool = False


@dataclass
class Constraint:
    """An optimization constraint."""
    id: str = field(default_factory=lambda: str(uuid4()))
    type: ConstraintType = ConstraintType.HARD
    name: str = ""
    expression: str = ""  # e.g., "cpu_usage < 80"
    weight: float = 1.0  # For soft constraints

    def evaluate(self, context: Dict[str, Any]) -> Tuple[bool, float]:
        """
        Evaluate the constraint.
        Returns (satisfied, violation_degree)
        """
        # Simple expression evaluation
        try:
            result = eval(self.expression, {"__builtins__": {}}, context)
            return bool(result), 0.0 if result else 1.0
        except Exception:
            return False, 1.0


@dataclass
class OptimizationResult:
    """Result of an optimization run."""
    success: bool = False
    allocations: List[Allocation] = field(default_factory=list)
    total_cost: float = 0.0
    objective_value: float = 0.0
    constraints_satisfied: int = 0
    constraints_violated: int = 0
    execution_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EfficiencyMetrics:
    """Metrics about resource efficiency."""
    total_capacity: float = 0.0
    total_allocated: float = 0.0
    total_available: float = 0.0
    utilization_percent: float = 0.0
    free_resources_percent: float = 0.0
    cost_per_unit_avg: float = 0.0
    waste_percent: float = 0.0


# =============================================================================
# RESOURCE POOL
# =============================================================================

class ResourcePool:
    """
    Manages a pool of resources.

    Provides allocation, deallocation, and tracking
    of resources across different types.
    """

    def __init__(self):
        self.resources: Dict[str, Resource] = {}
        self.allocations: Dict[str, Allocation] = {}
        self.quotas: Dict[str, ResourceQuota] = {}
        self.history: List[Dict[str, Any]] = []
        self._lock = asyncio.Lock()

    async def add_resource(self, resource: Resource) -> str:
        """Add a resource to the pool."""
        async with self._lock:
            self.resources[resource.id] = resource
            self._record_event("resource_added", {"resource_id": resource.id})
            logger.info(f"Added resource: {resource.name} ({resource.id})")
            return resource.id

    async def remove_resource(self, resource_id: str) -> bool:
        """Remove a resource from the pool."""
        async with self._lock:
            if resource_id in self.resources:
                del self.resources[resource_id]
                self._record_event("resource_removed", {"resource_id": resource_id})
                return True
            return False

    async def allocate(
        self,
        request: ResourceRequest,
        strategy: AllocationStrategy = AllocationStrategy.COST_OPTIMIZED
    ) -> Optional[Allocation]:
        """Allocate resources for a request."""
        async with self._lock:
            # Find suitable resources
            candidates = self._find_candidates(request)

            if not candidates:
                logger.warning(f"No resources available for request {request.id}")
                return None

            # Apply allocation strategy
            selected = self._apply_strategy(candidates, request, strategy)

            if not selected:
                return None

            resource = selected

            # Check quota
            quota_key = f"{request.requester}:{request.resource_type.value}"
            if quota_key in self.quotas:
                quota = self.quotas[quota_key]
                quota.reset_if_needed()
                if quota.used + request.amount > quota.limit:
                    logger.warning(f"Quota exceeded for {quota_key}")
                    return None
                quota.used += request.amount

            # Create allocation
            allocation = Allocation(
                request_id=request.id,
                resource_id=resource.id,
                amount=request.amount,
                cost=resource.cost_per_unit * request.amount
            )

            # Update resource
            resource.allocated += request.amount
            if resource.allocated >= resource.capacity:
                resource.state = ResourceState.EXHAUSTED
            else:
                resource.state = ResourceState.ALLOCATED

            self.allocations[allocation.id] = allocation
            self._record_event("allocation_created", {
                "allocation_id": allocation.id,
                "resource_id": resource.id,
                "amount": request.amount
            })

            return allocation

    async def release(self, allocation_id: str) -> bool:
        """Release an allocation."""
        async with self._lock:
            allocation = self.allocations.get(allocation_id)
            if not allocation or allocation.released:
                return False

            resource = self.resources.get(allocation.resource_id)
            if resource:
                resource.allocated -= allocation.amount
                if resource.allocated <= 0:
                    resource.state = ResourceState.AVAILABLE
                    resource.allocated = 0

            allocation.released = True
            self._record_event("allocation_released", {
                "allocation_id": allocation_id
            })

            return True

    def _find_candidates(self, request: ResourceRequest) -> List[Resource]:
        """Find resources that can satisfy a request."""
        candidates = []

        for resource in self.resources.values():
            # Check type match
            if resource.type != request.resource_type:
                continue

            # Check availability
            if resource.available < request.amount:
                continue

            # Check cost constraint
            if request.max_cost is not None:
                if resource.cost_per_unit * request.amount > request.max_cost:
                    continue

            candidates.append(resource)

        # Sort by preference for free resources
        if request.prefer_free:
            candidates.sort(key=lambda r: (0 if r.is_free else 1, r.cost_per_unit))

        return candidates

    def _apply_strategy(
        self,
        candidates: List[Resource],
        request: ResourceRequest,
        strategy: AllocationStrategy
    ) -> Optional[Resource]:
        """Apply allocation strategy to select a resource."""
        if not candidates:
            return None

        if strategy == AllocationStrategy.FIRST_FIT:
            return candidates[0]

        elif strategy == AllocationStrategy.BEST_FIT:
            # Select resource with smallest available capacity >= request
            return min(candidates, key=lambda r: r.available)

        elif strategy == AllocationStrategy.WORST_FIT:
            # Select resource with largest available capacity
            return max(candidates, key=lambda r: r.available)

        elif strategy == AllocationStrategy.COST_OPTIMIZED:
            # Select cheapest resource (prefer free)
            return min(candidates, key=lambda r: r.cost_per_unit)

        elif strategy == AllocationStrategy.BALANCED:
            # Select resource with lowest utilization
            return min(candidates, key=lambda r: r.utilization)

        elif strategy == AllocationStrategy.PRIORITY_BASED:
            # For high priority, use best resources
            if request.priority <= 3:
                return max(candidates, key=lambda r: r.capacity)
            else:
                return min(candidates, key=lambda r: r.cost_per_unit)

        return candidates[0]

    def _record_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Record an event in history."""
        self.history.append({
            "type": event_type,
            "timestamp": datetime.now().isoformat(),
            "data": data
        })
        # Keep last 1000 events
        if len(self.history) > 1000:
            self.history = self.history[-1000:]

    def get_metrics(self, resource_type: Optional[ResourceType] = None) -> EfficiencyMetrics:
        """Get efficiency metrics."""
        resources = [
            r for r in self.resources.values()
            if resource_type is None or r.type == resource_type
        ]

        if not resources:
            return EfficiencyMetrics()

        total_capacity = sum(r.capacity for r in resources)
        total_allocated = sum(r.allocated for r in resources)
        total_available = sum(r.available for r in resources)
        free_resources = sum(1 for r in resources if r.is_free)

        avg_cost = sum(r.cost_per_unit for r in resources) / len(resources)

        return EfficiencyMetrics(
            total_capacity=total_capacity,
            total_allocated=total_allocated,
            total_available=total_available,
            utilization_percent=(total_allocated / total_capacity * 100) if total_capacity > 0 else 0,
            free_resources_percent=(free_resources / len(resources) * 100) if resources else 0,
            cost_per_unit_avg=avg_cost,
            waste_percent=0  # Could be calculated based on unused allocations
        )


# =============================================================================
# OPTIMIZATION ALGORITHMS
# =============================================================================

class Optimizer(ABC):
    """Base class for optimizers."""

    @abstractmethod
    async def optimize(
        self,
        requests: List[ResourceRequest],
        resources: List[Resource],
        constraints: List[Constraint],
        goal: OptimizationGoal
    ) -> OptimizationResult:
        """Run optimization."""
        pass


class GreedyOptimizer(Optimizer):
    """
    Greedy optimization algorithm.

    Fast but may not find optimal solution.
    """

    async def optimize(
        self,
        requests: List[ResourceRequest],
        resources: List[Resource],
        constraints: List[Constraint],
        goal: OptimizationGoal
    ) -> OptimizationResult:
        """Run greedy optimization."""
        start_time = time.time()
        allocations = []
        total_cost = 0.0

        # Sort requests by priority
        sorted_requests = sorted(requests, key=lambda r: r.priority)

        # Sort resources based on goal
        if goal == OptimizationGoal.MINIMIZE_COST:
            sorted_resources = sorted(resources, key=lambda r: r.cost_per_unit)
        elif goal == OptimizationGoal.MAXIMIZE_UTILIZATION:
            sorted_resources = sorted(resources, key=lambda r: -r.utilization)
        else:
            sorted_resources = list(resources)

        for request in sorted_requests:
            for resource in sorted_resources:
                if resource.type != request.resource_type:
                    continue
                if resource.available < request.amount:
                    continue

                # Create allocation
                allocation = Allocation(
                    request_id=request.id,
                    resource_id=resource.id,
                    amount=request.amount,
                    cost=resource.cost_per_unit * request.amount
                )

                allocations.append(allocation)
                total_cost += allocation.cost
                resource.allocated += request.amount
                break

        # Check constraints
        context = self._build_context(allocations, resources)
        satisfied = sum(1 for c in constraints if c.evaluate(context)[0])
        violated = len(constraints) - satisfied

        return OptimizationResult(
            success=len(allocations) == len(requests),
            allocations=allocations,
            total_cost=total_cost,
            constraints_satisfied=satisfied,
            constraints_violated=violated,
            execution_time_ms=(time.time() - start_time) * 1000
        )

    def _build_context(
        self,
        allocations: List[Allocation],
        resources: List[Resource]
    ) -> Dict[str, Any]:
        """Build context for constraint evaluation."""
        return {
            "total_cost": sum(a.cost for a in allocations),
            "num_allocations": len(allocations),
            "avg_utilization": sum(r.utilization for r in resources) / len(resources) if resources else 0
        }


class GeneticOptimizer(Optimizer):
    """
    Genetic algorithm optimizer.

    Uses evolutionary approach for complex optimization.
    """

    def __init__(
        self,
        population_size: int = 50,
        generations: int = 100,
        mutation_rate: float = 0.1,
        crossover_rate: float = 0.8
    ):
        self.population_size = population_size
        self.generations = generations
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate

    async def optimize(
        self,
        requests: List[ResourceRequest],
        resources: List[Resource],
        constraints: List[Constraint],
        goal: OptimizationGoal
    ) -> OptimizationResult:
        """Run genetic optimization."""
        start_time = time.time()

        # Initialize population
        population = self._init_population(requests, resources)

        for generation in range(self.generations):
            # Evaluate fitness
            fitness_scores = [
                self._evaluate_fitness(ind, requests, resources, constraints, goal)
                for ind in population
            ]

            # Selection
            selected = self._tournament_selection(population, fitness_scores)

            # Crossover
            offspring = []
            for i in range(0, len(selected), 2):
                if i + 1 < len(selected):
                    if random.random() < self.crossover_rate:
                        c1, c2 = self._crossover(selected[i], selected[i+1])
                        offspring.extend([c1, c2])
                    else:
                        offspring.extend([selected[i], selected[i+1]])

            # Mutation
            for ind in offspring:
                if random.random() < self.mutation_rate:
                    self._mutate(ind, len(resources))

            population = offspring

            await asyncio.sleep(0)  # Yield control

        # Get best solution
        fitness_scores = [
            self._evaluate_fitness(ind, requests, resources, constraints, goal)
            for ind in population
        ]
        best_idx = max(range(len(fitness_scores)), key=lambda i: fitness_scores[i])
        best_individual = population[best_idx]

        # Convert to allocations
        allocations = self._decode_individual(best_individual, requests, resources)
        total_cost = sum(a.cost for a in allocations)

        context = {"total_cost": total_cost, "num_allocations": len(allocations)}
        satisfied = sum(1 for c in constraints if c.evaluate(context)[0])

        return OptimizationResult(
            success=len(allocations) > 0,
            allocations=allocations,
            total_cost=total_cost,
            objective_value=fitness_scores[best_idx],
            constraints_satisfied=satisfied,
            constraints_violated=len(constraints) - satisfied,
            execution_time_ms=(time.time() - start_time) * 1000
        )

    def _init_population(
        self,
        requests: List[ResourceRequest],
        resources: List[Resource]
    ) -> List[List[int]]:
        """Initialize random population."""
        population = []
        for _ in range(self.population_size):
            # Each individual is a list of resource indices for each request
            individual = [random.randint(0, len(resources) - 1) for _ in requests]
            population.append(individual)
        return population

    def _evaluate_fitness(
        self,
        individual: List[int],
        requests: List[ResourceRequest],
        resources: List[Resource],
        constraints: List[Constraint],
        goal: OptimizationGoal
    ) -> float:
        """Evaluate fitness of an individual."""
        total_cost = 0.0
        valid_allocations = 0

        # Reset resource allocation for evaluation
        temp_allocated = {r.id: 0.0 for r in resources}

        for i, req in enumerate(requests):
            res_idx = individual[i]
            if res_idx < len(resources):
                resource = resources[res_idx]
                if (resource.type == req.resource_type and
                    resource.capacity - temp_allocated[resource.id] >= req.amount):
                    temp_allocated[resource.id] += req.amount
                    total_cost += resource.cost_per_unit * req.amount
                    valid_allocations += 1

        # Calculate fitness based on goal
        if goal == OptimizationGoal.MINIMIZE_COST:
            fitness = 1.0 / (1.0 + total_cost)
        elif goal == OptimizationGoal.MAXIMIZE_THROUGHPUT:
            fitness = valid_allocations / len(requests)
        elif goal == OptimizationGoal.MAXIMIZE_UTILIZATION:
            total_util = sum(
                temp_allocated[r.id] / r.capacity
                for r in resources if r.capacity > 0
            )
            fitness = total_util / len(resources)
        else:
            fitness = valid_allocations / len(requests) - total_cost / 1000

        # Penalize constraint violations
        context = {"total_cost": total_cost, "valid_allocations": valid_allocations}
        for constraint in constraints:
            satisfied, violation = constraint.evaluate(context)
            if not satisfied and constraint.type == ConstraintType.HARD:
                fitness *= 0.1

        return fitness

    def _tournament_selection(
        self,
        population: List[List[int]],
        fitness: List[float],
        tournament_size: int = 3
    ) -> List[List[int]]:
        """Tournament selection."""
        selected = []
        for _ in range(len(population)):
            tournament = random.sample(range(len(population)), tournament_size)
            winner = max(tournament, key=lambda i: fitness[i])
            selected.append(list(population[winner]))
        return selected

    def _crossover(
        self,
        parent1: List[int],
        parent2: List[int]
    ) -> Tuple[List[int], List[int]]:
        """Single-point crossover."""
        point = random.randint(1, len(parent1) - 1)
        child1 = parent1[:point] + parent2[point:]
        child2 = parent2[:point] + parent1[point:]
        return child1, child2

    def _mutate(self, individual: List[int], num_resources: int) -> None:
        """Random mutation."""
        idx = random.randint(0, len(individual) - 1)
        individual[idx] = random.randint(0, num_resources - 1)

    def _decode_individual(
        self,
        individual: List[int],
        requests: List[ResourceRequest],
        resources: List[Resource]
    ) -> List[Allocation]:
        """Decode individual to allocations."""
        allocations = []

        for i, req in enumerate(requests):
            res_idx = individual[i]
            if res_idx < len(resources):
                resource = resources[res_idx]
                if resource.type == req.resource_type:
                    allocation = Allocation(
                        request_id=req.id,
                        resource_id=resource.id,
                        amount=req.amount,
                        cost=resource.cost_per_unit * req.amount
                    )
                    allocations.append(allocation)

        return allocations


class LinearProgrammingOptimizer(Optimizer):
    """
    Linear programming based optimizer.

    Uses simplex-like algorithm for linear optimization problems.
    """

    async def optimize(
        self,
        requests: List[ResourceRequest],
        resources: List[Resource],
        constraints: List[Constraint],
        goal: OptimizationGoal
    ) -> OptimizationResult:
        """Run LP optimization (simplified)."""
        start_time = time.time()

        # Build cost matrix
        n_requests = len(requests)
        n_resources = len(resources)

        cost_matrix = []
        for req in requests:
            row = []
            for res in resources:
                if res.type == req.resource_type and res.available >= req.amount:
                    row.append(res.cost_per_unit * req.amount)
                else:
                    row.append(float('inf'))
            cost_matrix.append(row)

        # Simple assignment (Hungarian-like for min cost)
        allocations = []
        total_cost = 0.0
        used_resources = set()

        for i in range(n_requests):
            best_j = -1
            best_cost = float('inf')

            for j in range(n_resources):
                if j not in used_resources and cost_matrix[i][j] < best_cost:
                    best_cost = cost_matrix[i][j]
                    best_j = j

            if best_j >= 0 and best_cost < float('inf'):
                allocation = Allocation(
                    request_id=requests[i].id,
                    resource_id=resources[best_j].id,
                    amount=requests[i].amount,
                    cost=best_cost
                )
                allocations.append(allocation)
                total_cost += best_cost
                used_resources.add(best_j)

        return OptimizationResult(
            success=len(allocations) == len(requests),
            allocations=allocations,
            total_cost=total_cost,
            execution_time_ms=(time.time() - start_time) * 1000
        )


# =============================================================================
# LOAD BALANCER
# =============================================================================

class LoadBalancer:
    """
    Load balancer for distributing work across resources.

    Supports multiple balancing strategies.
    """

    def __init__(self):
        self.resources: List[Resource] = []
        self.current_index = 0
        self.weights: Dict[str, float] = {}
        self.request_counts: Dict[str, int] = defaultdict(int)

    def add_resource(self, resource: Resource, weight: float = 1.0) -> None:
        """Add a resource to the load balancer."""
        self.resources.append(resource)
        self.weights[resource.id] = weight

    def remove_resource(self, resource_id: str) -> bool:
        """Remove a resource."""
        for i, r in enumerate(self.resources):
            if r.id == resource_id:
                self.resources.pop(i)
                self.weights.pop(resource_id, None)
                return True
        return False

    def get_next_resource(
        self,
        strategy: AllocationStrategy = AllocationStrategy.ROUND_ROBIN
    ) -> Optional[Resource]:
        """Get next resource based on strategy."""
        if not self.resources:
            return None

        available = [r for r in self.resources if r.state == ResourceState.AVAILABLE]
        if not available:
            available = [r for r in self.resources if r.state != ResourceState.ERROR]

        if not available:
            return None

        if strategy == AllocationStrategy.ROUND_ROBIN:
            resource = available[self.current_index % len(available)]
            self.current_index += 1
            return resource

        elif strategy == AllocationStrategy.BALANCED:
            # Select least loaded
            return min(available, key=lambda r: r.utilization)

        elif strategy == AllocationStrategy.PRIORITY_BASED:
            # Select by weight
            weighted = [(r, self.weights.get(r.id, 1.0)) for r in available]
            total_weight = sum(w for _, w in weighted)
            threshold = random.random() * total_weight

            cumulative = 0
            for r, w in weighted:
                cumulative += w
                if cumulative >= threshold:
                    return r

            return available[0]

        return available[0]


# =============================================================================
# CAPACITY PLANNER
# =============================================================================

class CapacityPlanner:
    """
    Plans capacity based on usage patterns and predictions.

    Helps prevent resource exhaustion while minimizing waste.
    """

    def __init__(self):
        self.usage_history: Dict[str, List[Tuple[datetime, float]]] = defaultdict(list)
        self.predictions: Dict[str, float] = {}

    def record_usage(
        self,
        resource_type: ResourceType,
        usage: float,
        timestamp: Optional[datetime] = None
    ) -> None:
        """Record usage for capacity planning."""
        key = resource_type.value
        ts = timestamp or datetime.now()
        self.usage_history[key].append((ts, usage))

        # Keep last 1000 records
        if len(self.usage_history[key]) > 1000:
            self.usage_history[key] = self.usage_history[key][-1000:]

    def predict_usage(
        self,
        resource_type: ResourceType,
        horizon_hours: float = 24
    ) -> float:
        """Predict future usage."""
        key = resource_type.value
        history = self.usage_history.get(key, [])

        if len(history) < 10:
            return 0.0

        # Simple moving average prediction
        recent = [u for _, u in history[-10:]]
        avg = sum(recent) / len(recent)

        # Trend detection
        if len(history) >= 20:
            older = [u for _, u in history[-20:-10]]
            older_avg = sum(older) / len(older)
            trend = (avg - older_avg) / older_avg if older_avg > 0 else 0
        else:
            trend = 0

        # Project forward
        predicted = avg * (1 + trend * (horizon_hours / 24))
        self.predictions[key] = predicted

        return predicted

    def get_recommended_capacity(
        self,
        resource_type: ResourceType,
        buffer_percent: float = 20
    ) -> float:
        """Get recommended capacity with buffer."""
        predicted = self.predict_usage(resource_type)
        return predicted * (1 + buffer_percent / 100)


# =============================================================================
# RESOURCE OPTIMIZER
# =============================================================================

class ResourceOptimizer:
    """
    The master resource optimizer for BAEL.

    Provides unified resource optimization following
    the zero-invest mindstate principle.
    """

    def __init__(self):
        self.pool = ResourcePool()
        self.load_balancer = LoadBalancer()
        self.capacity_planner = CapacityPlanner()
        self.optimizers: Dict[str, Optimizer] = {
            "greedy": GreedyOptimizer(),
            "genetic": GeneticOptimizer(),
            "linear": LinearProgrammingOptimizer()
        }
        self.default_strategy = AllocationStrategy.COST_OPTIMIZED

    async def add_free_resource(
        self,
        name: str,
        resource_type: ResourceType,
        capacity: float,
        provider: str = ""
    ) -> str:
        """Add a free resource (zero cost)."""
        resource = Resource(
            type=resource_type,
            name=name,
            capacity=capacity,
            cost_per_unit=0.0,
            provider=provider,
            tags=["free", "zero-invest"]
        )

        resource_id = await self.pool.add_resource(resource)
        self.load_balancer.add_resource(resource)

        return resource_id

    async def request_resources(
        self,
        resource_type: ResourceType,
        amount: float,
        requester: str = "",
        priority: int = 5,
        max_cost: float = 0.0  # 0 = prefer free only
    ) -> Optional[Allocation]:
        """Request resources with zero-cost preference."""
        request = ResourceRequest(
            resource_type=resource_type,
            amount=amount,
            priority=priority,
            requester=requester,
            max_cost=max_cost if max_cost > 0 else None,
            prefer_free=True
        )

        allocation = await self.pool.allocate(request, self.default_strategy)

        if allocation:
            self.capacity_planner.record_usage(resource_type, amount)

        return allocation

    async def release_resources(self, allocation_id: str) -> bool:
        """Release allocated resources."""
        return await self.pool.release(allocation_id)

    async def optimize_allocation(
        self,
        requests: List[ResourceRequest],
        goal: OptimizationGoal = OptimizationGoal.MINIMIZE_COST,
        algorithm: str = "greedy",
        constraints: List[Constraint] = None
    ) -> OptimizationResult:
        """Run optimization on a set of requests."""
        optimizer = self.optimizers.get(algorithm, self.optimizers["greedy"])
        resources = list(self.pool.resources.values())

        return await optimizer.optimize(
            requests,
            resources,
            constraints or [],
            goal
        )

    def get_efficiency_metrics(
        self,
        resource_type: Optional[ResourceType] = None
    ) -> EfficiencyMetrics:
        """Get efficiency metrics."""
        return self.pool.get_metrics(resource_type)

    async def predict_and_plan(
        self,
        resource_type: ResourceType,
        horizon_hours: float = 24
    ) -> Dict[str, Any]:
        """Predict usage and plan capacity."""
        predicted = self.capacity_planner.predict_usage(resource_type, horizon_hours)
        recommended = self.capacity_planner.get_recommended_capacity(resource_type)
        current_metrics = self.get_efficiency_metrics(resource_type)

        return {
            "predicted_usage": predicted,
            "recommended_capacity": recommended,
            "current_capacity": current_metrics.total_capacity,
            "current_utilization": current_metrics.utilization_percent,
            "capacity_gap": max(0, recommended - current_metrics.total_capacity),
            "horizon_hours": horizon_hours
        }

    def get_free_resources_summary(self) -> Dict[str, Any]:
        """Get summary of free resources."""
        free_resources = [r for r in self.pool.resources.values() if r.is_free]

        by_type = defaultdict(list)
        for r in free_resources:
            by_type[r.type.value].append({
                "id": r.id,
                "name": r.name,
                "capacity": r.capacity,
                "available": r.available,
                "provider": r.provider
            })

        return {
            "total_free_resources": len(free_resources),
            "by_type": dict(by_type),
            "total_free_capacity": sum(r.capacity for r in free_resources)
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Resource Optimizer."""
    print("=" * 70)
    print("BAEL - RESOURCE OPTIMIZER DEMO")
    print("Zero-Invest Resource Management")
    print("=" * 70)
    print()

    # Create optimizer
    optimizer = ResourceOptimizer()

    # 1. Add Free Resources
    print("1. ADDING FREE RESOURCES:")
    print("-" * 40)

    # Add various free resources
    await optimizer.add_free_resource(
        "Oracle Cloud CPU",
        ResourceType.CPU,
        capacity=4.0,  # 4 ARM cores
        provider="Oracle Cloud Free Tier"
    )

    await optimizer.add_free_resource(
        "Oracle Cloud Memory",
        ResourceType.MEMORY,
        capacity=24576,  # 24GB in MB
        provider="Oracle Cloud Free Tier"
    )

    await optimizer.add_free_resource(
        "Colab GPU",
        ResourceType.GPU,
        capacity=1.0,
        provider="Google Colab"
    )

    await optimizer.add_free_resource(
        "Cloudflare Workers",
        ResourceType.API_CALLS,
        capacity=100000,  # 100k/day
        provider="Cloudflare"
    )

    await optimizer.add_free_resource(
        "GitHub Actions",
        ResourceType.COMPUTE_TIME,
        capacity=2000,  # minutes/month
        provider="GitHub"
    )

    summary = optimizer.get_free_resources_summary()
    print(f"   Free resources added: {summary['total_free_resources']}")
    for rtype, resources in summary["by_type"].items():
        print(f"   - {rtype}: {len(resources)} resources")
    print()

    # 2. Request Resources
    print("2. REQUESTING RESOURCES:")
    print("-" * 40)

    # Request CPU
    allocation = await optimizer.request_resources(
        ResourceType.CPU,
        amount=2.0,
        requester="reasoning_engine",
        priority=1
    )

    if allocation:
        print(f"   CPU Allocation: {allocation.amount} units")
        print(f"   Cost: ${allocation.cost:.2f} (FREE!)")

    # Request memory
    allocation2 = await optimizer.request_resources(
        ResourceType.MEMORY,
        amount=4096,  # 4GB
        requester="memory_engine"
    )

    if allocation2:
        print(f"   Memory Allocation: {allocation2.amount}MB")
        print(f"   Cost: ${allocation2.cost:.2f}")
    print()

    # 3. Efficiency Metrics
    print("3. EFFICIENCY METRICS:")
    print("-" * 40)

    metrics = optimizer.get_efficiency_metrics()
    print(f"   Total Capacity: {metrics.total_capacity:.0f}")
    print(f"   Allocated: {metrics.total_allocated:.0f}")
    print(f"   Utilization: {metrics.utilization_percent:.1f}%")
    print(f"   Free Resources: {metrics.free_resources_percent:.0f}%")
    print(f"   Avg Cost/Unit: ${metrics.cost_per_unit_avg:.4f}")
    print()

    # 4. Batch Optimization
    print("4. BATCH OPTIMIZATION:")
    print("-" * 40)

    # Create multiple requests
    requests = [
        ResourceRequest(resource_type=ResourceType.CPU, amount=1.0, priority=2),
        ResourceRequest(resource_type=ResourceType.MEMORY, amount=2048, priority=3),
        ResourceRequest(resource_type=ResourceType.GPU, amount=0.5, priority=1),
    ]

    # Optimize with greedy algorithm
    result = await optimizer.optimize_allocation(
        requests,
        goal=OptimizationGoal.MINIMIZE_COST,
        algorithm="greedy"
    )

    print(f"   Optimization Success: {result.success}")
    print(f"   Allocations Made: {len(result.allocations)}")
    print(f"   Total Cost: ${result.total_cost:.2f}")
    print(f"   Execution Time: {result.execution_time_ms:.2f}ms")
    print()

    # 5. Genetic Optimization
    print("5. GENETIC OPTIMIZATION:")
    print("-" * 40)

    result = await optimizer.optimize_allocation(
        requests,
        goal=OptimizationGoal.MAXIMIZE_UTILIZATION,
        algorithm="genetic"
    )

    print(f"   Success: {result.success}")
    print(f"   Objective Value: {result.objective_value:.4f}")
    print(f"   Execution Time: {result.execution_time_ms:.2f}ms")
    print()

    # 6. Capacity Planning
    print("6. CAPACITY PLANNING:")
    print("-" * 40)

    # Record some usage history
    for i in range(20):
        optimizer.capacity_planner.record_usage(
            ResourceType.CPU,
            2.0 + random.random() * 0.5
        )

    plan = await optimizer.predict_and_plan(ResourceType.CPU, horizon_hours=24)
    print(f"   Predicted Usage: {plan['predicted_usage']:.2f}")
    print(f"   Recommended Capacity: {plan['recommended_capacity']:.2f}")
    print(f"   Current Capacity: {plan['current_capacity']:.2f}")
    print(f"   Capacity Gap: {plan['capacity_gap']:.2f}")
    print()

    # 7. Load Balancing
    print("7. LOAD BALANCING:")
    print("-" * 40)

    lb = LoadBalancer()

    # Add resources to load balancer
    for r in optimizer.pool.resources.values():
        lb.add_resource(r)

    # Get resources using different strategies
    for strategy in [AllocationStrategy.ROUND_ROBIN, AllocationStrategy.BALANCED]:
        resource = lb.get_next_resource(strategy)
        if resource:
            print(f"   {strategy.value}: {resource.name}")
    print()

    # 8. Release Resources
    print("8. RELEASING RESOURCES:")
    print("-" * 40)

    if allocation:
        released = await optimizer.release_resources(allocation.id)
        print(f"   Released CPU allocation: {released}")

    if allocation2:
        released = await optimizer.release_resources(allocation2.id)
        print(f"   Released Memory allocation: {released}")

    final_metrics = optimizer.get_efficiency_metrics()
    print(f"   Final Utilization: {final_metrics.utilization_percent:.1f}%")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Resource Optimizer Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
