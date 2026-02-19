"""
⚡ CAPABILITY ROUTER ⚡
======================
Intelligent capability routing.

Features:
- Capability discovery
- Requirement matching
- Load balancing
- Dynamic routing
"""

import math
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from collections import defaultdict
import uuid


class CapabilityType(Enum):
    """Types of capabilities"""
    REASONING = auto()
    GENERATION = auto()
    ANALYSIS = auto()
    RETRIEVAL = auto()
    TRANSFORMATION = auto()
    OPTIMIZATION = auto()
    LEARNING = auto()
    ORCHESTRATION = auto()


@dataclass
class Capability:
    """A system capability"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    capability_type: CapabilityType = CapabilityType.REASONING

    # Performance characteristics
    latency: float = 1.0  # seconds
    throughput: float = 1.0  # requests/second
    accuracy: float = 1.0  # 0-1

    # Resource requirements
    memory: float = 0.0  # GB
    compute: float = 0.0  # relative units

    # Availability
    is_available: bool = True
    cooldown: float = 0.0

    # Tags for matching
    tags: Set[str] = field(default_factory=set)

    # Embedding for semantic matching
    embedding: Optional[np.ndarray] = None


@dataclass
class CapabilityRequirement:
    """Requirements for a capability"""
    capability_type: Optional[CapabilityType] = None
    min_accuracy: float = 0.0
    max_latency: float = float('inf')

    # Semantic requirement
    description: str = ""
    required_tags: Set[str] = field(default_factory=set)

    # Optional preferences
    preferred_tags: Set[str] = field(default_factory=set)

    def matches(self, capability: Capability) -> bool:
        """Check if capability matches requirements"""
        if self.capability_type and capability.capability_type != self.capability_type:
            return False

        if capability.accuracy < self.min_accuracy:
            return False

        if capability.latency > self.max_latency:
            return False

        if not capability.is_available:
            return False

        # Check required tags
        if self.required_tags and not self.required_tags.issubset(capability.tags):
            return False

        return True

    def score(self, capability: Capability) -> float:
        """Score how well capability matches"""
        if not self.matches(capability):
            return 0.0

        score = 1.0

        # Bonus for matching preferred tags
        preferred_matches = len(self.preferred_tags & capability.tags)
        if self.preferred_tags:
            score += 0.2 * preferred_matches / len(self.preferred_tags)

        # Bonus for better accuracy
        score += 0.3 * capability.accuracy

        # Bonus for lower latency
        if self.max_latency < float('inf'):
            score += 0.2 * (1 - capability.latency / self.max_latency)

        return score


@dataclass
class CapabilityProvider:
    """Entity that provides capabilities"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""

    # Provided capabilities
    capabilities: Dict[str, Capability] = field(default_factory=dict)

    # Load information
    current_load: float = 0.0
    max_load: float = 1.0

    # Health
    is_healthy: bool = True
    last_health_check: datetime = field(default_factory=datetime.now)

    # Statistics
    total_requests: int = 0
    successful_requests: int = 0

    def add_capability(self, capability: Capability):
        """Add capability"""
        self.capabilities[capability.id] = capability

    def get_load_ratio(self) -> float:
        """Get current load ratio"""
        return self.current_load / self.max_load if self.max_load > 0 else 0

    def get_success_rate(self) -> float:
        """Get success rate"""
        if self.total_requests == 0:
            return 1.0
        return self.successful_requests / self.total_requests


class CapabilityMatcher:
    """
    Matches requirements to capabilities.
    """

    def __init__(self):
        self.providers: Dict[str, CapabilityProvider] = {}

        # Index by type
        self.by_type: Dict[CapabilityType, List[str]] = defaultdict(list)

        # Index by tags
        self.by_tag: Dict[str, List[str]] = defaultdict(list)

    def register_provider(self, provider: CapabilityProvider):
        """Register capability provider"""
        self.providers[provider.id] = provider

        for cap in provider.capabilities.values():
            self.by_type[cap.capability_type].append((provider.id, cap.id))
            for tag in cap.tags:
                self.by_tag[tag].append((provider.id, cap.id))

    def find_matching(
        self,
        requirement: CapabilityRequirement
    ) -> List[Tuple[CapabilityProvider, Capability, float]]:
        """Find matching capabilities"""
        candidates = set()

        # Filter by type
        if requirement.capability_type:
            for provider_id, cap_id in self.by_type.get(requirement.capability_type, []):
                candidates.add((provider_id, cap_id))
        else:
            # All capabilities
            for provider in self.providers.values():
                for cap_id in provider.capabilities:
                    candidates.add((provider.id, cap_id))

        # Filter by tags
        if requirement.required_tags:
            tag_matches = set()
            for tag in requirement.required_tags:
                for item in self.by_tag.get(tag, []):
                    tag_matches.add(item)
            candidates &= tag_matches

        # Score and filter
        results = []
        for provider_id, cap_id in candidates:
            provider = self.providers.get(provider_id)
            if not provider or not provider.is_healthy:
                continue

            cap = provider.capabilities.get(cap_id)
            if not cap:
                continue

            score = requirement.score(cap)
            if score > 0:
                results.append((provider, cap, score))

        # Sort by score
        results.sort(key=lambda x: -x[2])
        return results

    def find_best(
        self,
        requirement: CapabilityRequirement
    ) -> Optional[Tuple[CapabilityProvider, Capability]]:
        """Find best matching capability"""
        matches = self.find_matching(requirement)
        if matches:
            return (matches[0][0], matches[0][1])
        return None


class LoadBalancer:
    """
    Balances load across providers.
    """

    def __init__(self, strategy: str = 'weighted'):
        self.strategy = strategy

    def select(
        self,
        candidates: List[Tuple[CapabilityProvider, Capability, float]]
    ) -> Optional[Tuple[CapabilityProvider, Capability]]:
        """Select provider based on strategy"""
        if not candidates:
            return None

        if self.strategy == 'best':
            # Just take highest score
            return (candidates[0][0], candidates[0][1])

        elif self.strategy == 'round_robin':
            # Simple round robin
            return (candidates[0][0], candidates[0][1])

        elif self.strategy == 'least_loaded':
            # Select least loaded
            sorted_by_load = sorted(
                candidates,
                key=lambda x: x[0].get_load_ratio()
            )
            return (sorted_by_load[0][0], sorted_by_load[0][1])

        elif self.strategy == 'weighted':
            # Weight by score and inverse load
            weights = []
            for provider, cap, score in candidates:
                load_factor = 1 - provider.get_load_ratio()
                weight = score * load_factor * provider.get_success_rate()
                weights.append(weight)

            # Normalize
            total = sum(weights)
            if total == 0:
                return (candidates[0][0], candidates[0][1])

            probs = [w / total for w in weights]

            # Select
            idx = np.random.choice(len(candidates), p=probs)
            return (candidates[idx][0], candidates[idx][1])

        return (candidates[0][0], candidates[0][1])


class CapabilityRouter:
    """
    Routes requests to appropriate capabilities.
    """

    def __init__(self):
        self.matcher = CapabilityMatcher()
        self.balancer = LoadBalancer(strategy='weighted')

        # Routing history
        self.routing_history: List[Dict[str, Any]] = []

        # Circuit breakers
        self.failure_counts: Dict[str, int] = defaultdict(int)
        self.circuit_open: Dict[str, bool] = {}
        self.failure_threshold = 5

    def register_provider(self, provider: CapabilityProvider):
        """Register provider"""
        self.matcher.register_provider(provider)

    def route(
        self,
        requirement: CapabilityRequirement
    ) -> Optional[Tuple[CapabilityProvider, Capability]]:
        """Route request to capability"""
        # Find matching capabilities
        candidates = self.matcher.find_matching(requirement)

        # Filter by circuit breaker
        candidates = [
            (p, c, s) for p, c, s in candidates
            if not self.circuit_open.get(p.id, False)
        ]

        if not candidates:
            return None

        # Select using load balancer
        result = self.balancer.select(candidates)

        if result:
            provider, cap = result

            # Record routing
            self.routing_history.append({
                'timestamp': datetime.now(),
                'provider': provider.id,
                'capability': cap.id,
                'requirement': requirement.description
            })

            # Update load
            provider.current_load += 0.1

        return result

    def record_result(
        self,
        provider_id: str,
        success: bool
    ):
        """Record routing result"""
        if success:
            self.failure_counts[provider_id] = 0

            provider = self.matcher.providers.get(provider_id)
            if provider:
                provider.successful_requests += 1
                provider.total_requests += 1
                provider.current_load = max(0, provider.current_load - 0.1)
        else:
            self.failure_counts[provider_id] += 1

            provider = self.matcher.providers.get(provider_id)
            if provider:
                provider.total_requests += 1

            # Check circuit breaker
            if self.failure_counts[provider_id] >= self.failure_threshold:
                self.circuit_open[provider_id] = True

    def reset_circuit(self, provider_id: str):
        """Reset circuit breaker"""
        self.circuit_open[provider_id] = False
        self.failure_counts[provider_id] = 0


# Export all
__all__ = [
    'CapabilityType',
    'Capability',
    'CapabilityRequirement',
    'CapabilityProvider',
    'CapabilityMatcher',
    'LoadBalancer',
    'CapabilityRouter',
]
