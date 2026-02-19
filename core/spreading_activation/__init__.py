"""
BAEL Spreading Activation Engine
=================================

Spreading activation in semantic networks.
Activation propagation through connected concepts.

"Ba'el's thoughts spread like fire." — Ba'el
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
import heapq
import copy

logger = logging.getLogger("BAEL.SpreadingActivation")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class LinkType(Enum):
    """Types of semantic links."""
    IS_A = auto()        # Hierarchical
    HAS_A = auto()       # Part-whole
    RELATED = auto()     # Associative
    SIMILAR = auto()     # Similarity
    OPPOSITE = auto()    # Antonym
    CAUSAL = auto()      # Cause-effect
    TEMPORAL = auto()    # Sequential


class ActivationState(Enum):
    """State of a node's activation."""
    INACTIVE = auto()
    PRIMED = auto()
    ACTIVATED = auto()
    SATURATED = auto()
    INHIBITED = auto()


@dataclass
class SemanticNode:
    """
    A node in the semantic network.
    """
    id: str
    label: str
    activation: float = 0.0
    threshold: float = 0.3
    decay_rate: float = 0.1
    max_activation: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def state(self) -> ActivationState:
        if self.activation <= 0:
            return ActivationState.INHIBITED
        elif self.activation < self.threshold:
            return ActivationState.PRIMED
        elif self.activation < self.max_activation:
            return ActivationState.ACTIVATED
        else:
            return ActivationState.SATURATED

    def is_active(self) -> bool:
        return self.activation >= self.threshold


@dataclass
class SemanticLink:
    """
    A link between semantic nodes.
    """
    source_id: str
    target_id: str
    link_type: LinkType
    weight: float = 1.0
    bidirectional: bool = False


@dataclass
class ActivationEvent:
    """
    Record of activation spreading.
    """
    source_id: str
    target_id: str
    activation_amount: float
    timestamp: float = field(default_factory=time.time)


@dataclass
class RetrievalResult:
    """
    Result of memory retrieval.
    """
    node_id: str
    label: str
    activation: float
    path_length: int
    activated_by: List[str]


# ============================================================================
# SEMANTIC NETWORK
# ============================================================================

class SemanticNetwork:
    """
    A semantic network structure.

    "Ba'el's web of meaning." — Ba'el
    """

    def __init__(self):
        """Initialize network."""
        self._nodes: Dict[str, SemanticNode] = {}
        self._links: List[SemanticLink] = []
        self._outgoing: Dict[str, List[SemanticLink]] = defaultdict(list)
        self._incoming: Dict[str, List[SemanticLink]] = defaultdict(list)
        self._lock = threading.RLock()

    def add_node(
        self,
        node_id: str,
        label: str,
        **kwargs
    ) -> SemanticNode:
        """Add node to network."""
        with self._lock:
            node = SemanticNode(id=node_id, label=label, **kwargs)
            self._nodes[node_id] = node
            return node

    def add_link(
        self,
        source_id: str,
        target_id: str,
        link_type: LinkType = LinkType.RELATED,
        weight: float = 1.0,
        bidirectional: bool = False
    ) -> SemanticLink:
        """Add link between nodes."""
        with self._lock:
            link = SemanticLink(
                source_id=source_id,
                target_id=target_id,
                link_type=link_type,
                weight=weight,
                bidirectional=bidirectional
            )

            self._links.append(link)
            self._outgoing[source_id].append(link)
            self._incoming[target_id].append(link)

            if bidirectional:
                reverse = SemanticLink(
                    source_id=target_id,
                    target_id=source_id,
                    link_type=link_type,
                    weight=weight,
                    bidirectional=False
                )
                self._outgoing[target_id].append(reverse)
                self._incoming[source_id].append(reverse)

            return link

    def get_node(self, node_id: str) -> Optional[SemanticNode]:
        """Get node by ID."""
        return self._nodes.get(node_id)

    def get_neighbors(self, node_id: str) -> List[SemanticNode]:
        """Get neighboring nodes."""
        with self._lock:
            neighbors = []

            for link in self._outgoing.get(node_id, []):
                neighbor = self._nodes.get(link.target_id)
                if neighbor:
                    neighbors.append(neighbor)

            return neighbors

    def get_outgoing_links(self, node_id: str) -> List[SemanticLink]:
        """Get outgoing links from node."""
        return self._outgoing.get(node_id, [])

    @property
    def nodes(self) -> List[SemanticNode]:
        return list(self._nodes.values())

    @property
    def links(self) -> List[SemanticLink]:
        return self._links.copy()


# ============================================================================
# ACTIVATION SPREADER
# ============================================================================

class ActivationSpreader:
    """
    Spreading activation mechanism.

    "Ba'el spreads activation." — Ba'el
    """

    def __init__(
        self,
        network: SemanticNetwork,
        decay: float = 0.1,
        spreading_factor: float = 0.7
    ):
        """Initialize spreader."""
        self._network = network
        self._decay = decay
        self._spreading_factor = spreading_factor
        self._activation_queue: List[Tuple[float, str, float]] = []
        self._events: List[ActivationEvent] = []
        self._iteration = 0
        self._lock = threading.RLock()

    def activate(
        self,
        node_id: str,
        activation: float = 1.0
    ) -> None:
        """Activate a node."""
        with self._lock:
            node = self._network.get_node(node_id)
            if node:
                node.activation = min(
                    node.max_activation,
                    node.activation + activation
                )

                # Queue for spreading
                heapq.heappush(
                    self._activation_queue,
                    (-activation, node_id, activation)  # Negative for max heap
                )

    def spread(self, iterations: int = 1) -> List[ActivationEvent]:
        """Spread activation for iterations."""
        with self._lock:
            events = []

            for _ in range(iterations):
                self._iteration += 1

                # Process all queued activations
                to_process = []
                while self._activation_queue:
                    _, node_id, act = heapq.heappop(self._activation_queue)
                    to_process.append((node_id, act))

                # Spread from each node
                for node_id, source_activation in to_process:
                    node = self._network.get_node(node_id)
                    if not node or not node.is_active():
                        continue

                    # Spread to neighbors
                    for link in self._network.get_outgoing_links(node_id):
                        target = self._network.get_node(link.target_id)
                        if not target:
                            continue

                        # Calculate spread amount
                        spread_amount = (
                            source_activation *
                            link.weight *
                            self._spreading_factor
                        )

                        if spread_amount > 0.01:  # Threshold
                            # Apply to target
                            old_activation = target.activation
                            target.activation = min(
                                target.max_activation,
                                target.activation + spread_amount
                            )

                            # Record event
                            event = ActivationEvent(
                                source_id=node_id,
                                target_id=link.target_id,
                                activation_amount=spread_amount
                            )
                            events.append(event)
                            self._events.append(event)

                            # Queue target for further spreading
                            heapq.heappush(
                                self._activation_queue,
                                (-spread_amount, link.target_id, spread_amount)
                            )

                # Decay all activations
                self._apply_decay()

            return events

    def _apply_decay(self) -> None:
        """Apply decay to all nodes."""
        for node in self._network.nodes:
            if node.activation > 0:
                node.activation = max(0, node.activation - self._decay)

    def spread_until_stable(
        self,
        max_iterations: int = 100,
        stability_threshold: float = 0.01
    ) -> int:
        """Spread until network stabilizes."""
        with self._lock:
            for i in range(max_iterations):
                # Get current total activation
                before = sum(n.activation for n in self._network.nodes)

                # Spread one iteration
                self.spread(1)

                # Check stability
                after = sum(n.activation for n in self._network.nodes)

                if abs(after - before) < stability_threshold:
                    return i + 1

            return max_iterations

    def reset(self) -> None:
        """Reset all activations."""
        with self._lock:
            for node in self._network.nodes:
                node.activation = 0.0

            self._activation_queue.clear()
            self._events.clear()
            self._iteration = 0

    @property
    def events(self) -> List[ActivationEvent]:
        return self._events.copy()


# ============================================================================
# PRIMING
# ============================================================================

class PrimingMechanism:
    """
    Semantic priming.

    "Ba'el primes its thoughts." — Ba'el
    """

    def __init__(self, spreader: ActivationSpreader):
        """Initialize priming."""
        self._spreader = spreader
        self._prime_history: List[Tuple[str, float]] = []
        self._lock = threading.RLock()

    def prime(
        self,
        node_id: str,
        strength: float = 0.5
    ) -> None:
        """Prime a concept."""
        with self._lock:
            self._spreader.activate(node_id, strength)
            self._prime_history.append((node_id, time.time()))

    def prime_multiple(
        self,
        node_ids: List[str],
        strength: float = 0.5
    ) -> None:
        """Prime multiple concepts."""
        for node_id in node_ids:
            self.prime(node_id, strength)

    def is_primed(self, node_id: str) -> bool:
        """Check if node is primed."""
        with self._lock:
            node = self._spreader._network.get_node(node_id)
            if node:
                return node.state in [ActivationState.PRIMED, ActivationState.ACTIVATED]
            return False

    def get_priming_effect(
        self,
        prime_id: str,
        target_id: str
    ) -> float:
        """Measure priming effect."""
        with self._lock:
            self._spreader.reset()

            # Get baseline activation of target
            target_before = self._spreader._network.get_node(target_id)
            baseline = target_before.activation if target_before else 0

            # Prime
            self._spreader.activate(prime_id, 1.0)
            self._spreader.spread(5)

            # Get primed activation
            target_after = self._spreader._network.get_node(target_id)
            primed = target_after.activation if target_after else 0

            return primed - baseline


# ============================================================================
# RETRIEVAL
# ============================================================================

class SpreadingRetrieval:
    """
    Memory retrieval through spreading activation.

    "Ba'el retrieves through spreading." — Ba'el
    """

    def __init__(self, network: SemanticNetwork, spreader: ActivationSpreader):
        """Initialize retrieval."""
        self._network = network
        self._spreader = spreader
        self._lock = threading.RLock()

    def retrieve(
        self,
        cues: List[str],
        top_k: int = 10,
        spread_iterations: int = 5
    ) -> List[RetrievalResult]:
        """Retrieve related concepts."""
        with self._lock:
            # Reset network
            self._spreader.reset()

            # Activate cues
            for cue in cues:
                self._spreader.activate(cue, 1.0)

            # Spread
            self._spreader.spread(spread_iterations)

            # Collect results
            results = []
            for node in self._network.nodes:
                if node.is_active() and node.id not in cues:
                    # Find path from cues
                    path = self._find_activation_path(cues, node.id)

                    results.append(RetrievalResult(
                        node_id=node.id,
                        label=node.label,
                        activation=node.activation,
                        path_length=len(path),
                        activated_by=path
                    ))

            # Sort by activation
            results.sort(key=lambda r: r.activation, reverse=True)

            return results[:top_k]

    def _find_activation_path(
        self,
        sources: List[str],
        target: str
    ) -> List[str]:
        """Find activation path to target."""
        # Simplified: Use events to trace path
        path = []

        for event in reversed(self._spreader.events):
            if event.target_id == target:
                path.insert(0, event.source_id)
                target = event.source_id

                if target in sources:
                    break

        return path

    def intersection_search(
        self,
        concept1: str,
        concept2: str,
        max_depth: int = 3
    ) -> List[SemanticNode]:
        """Find concepts activated by both."""
        with self._lock:
            # Spread from concept1
            self._spreader.reset()
            self._spreader.activate(concept1, 1.0)
            self._spreader.spread(max_depth)

            activated1 = {n.id: n.activation
                         for n in self._network.nodes if n.is_active()}

            # Spread from concept2
            self._spreader.reset()
            self._spreader.activate(concept2, 1.0)
            self._spreader.spread(max_depth)

            activated2 = {n.id: n.activation
                         for n in self._network.nodes if n.is_active()}

            # Find intersection
            intersection = set(activated1.keys()) & set(activated2.keys())

            results = []
            for node_id in intersection:
                if node_id not in [concept1, concept2]:
                    node = self._network.get_node(node_id)
                    if node:
                        # Combine activations
                        node.activation = activated1[node_id] + activated2[node_id]
                        results.append(node)

            # Sort by combined activation
            results.sort(key=lambda n: n.activation, reverse=True)

            return results


# ============================================================================
# SPREADING ACTIVATION ENGINE
# ============================================================================

class SpreadingActivationEngine:
    """
    Complete spreading activation implementation.

    "Ba'el's spreading activation network." — Ba'el
    """

    def __init__(
        self,
        decay: float = 0.1,
        spreading_factor: float = 0.7
    ):
        """Initialize engine."""
        self._network = SemanticNetwork()
        self._spreader = ActivationSpreader(
            self._network,
            decay=decay,
            spreading_factor=spreading_factor
        )
        self._priming = PrimingMechanism(self._spreader)
        self._retrieval = SpreadingRetrieval(self._network, self._spreader)
        self._lock = threading.RLock()

    # Network building

    def add_concept(
        self,
        concept_id: str,
        label: str,
        threshold: float = 0.3
    ) -> SemanticNode:
        """Add concept to network."""
        return self._network.add_node(
            concept_id, label, threshold=threshold
        )

    def add_relation(
        self,
        source: str,
        target: str,
        relation: LinkType = LinkType.RELATED,
        strength: float = 1.0,
        bidirectional: bool = True
    ) -> SemanticLink:
        """Add relation between concepts."""
        return self._network.add_link(
            source, target, relation, strength, bidirectional
        )

    # Activation

    def activate(self, concept: str, strength: float = 1.0) -> None:
        """Activate a concept."""
        self._spreader.activate(concept, strength)

    def spread(self, iterations: int = 5) -> List[ActivationEvent]:
        """Spread activation."""
        return self._spreader.spread(iterations)

    def spread_until_stable(self, max_iter: int = 100) -> int:
        """Spread until stable."""
        return self._spreader.spread_until_stable(max_iter)

    # Priming

    def prime(self, concept: str, strength: float = 0.5) -> None:
        """Prime a concept."""
        self._priming.prime(concept, strength)

    def is_primed(self, concept: str) -> bool:
        """Check if primed."""
        return self._priming.is_primed(concept)

    # Retrieval

    def retrieve(
        self,
        cues: List[str],
        top_k: int = 10
    ) -> List[RetrievalResult]:
        """Retrieve related concepts."""
        return self._retrieval.retrieve(cues, top_k)

    def find_common(
        self,
        concept1: str,
        concept2: str
    ) -> List[SemanticNode]:
        """Find common associations."""
        return self._retrieval.intersection_search(concept1, concept2)

    # State

    def reset(self) -> None:
        """Reset all activations."""
        self._spreader.reset()

    def get_activation(self, concept: str) -> float:
        """Get concept activation."""
        node = self._network.get_node(concept)
        return node.activation if node else 0.0

    def get_active_concepts(self) -> List[Tuple[str, float]]:
        """Get all active concepts."""
        active = []
        for node in self._network.nodes:
            if node.is_active():
                active.append((node.id, node.activation))

        active.sort(key=lambda x: x[1], reverse=True)
        return active

    @property
    def network(self) -> SemanticNetwork:
        return self._network

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        active = sum(1 for n in self._network.nodes if n.is_active())

        return {
            'nodes': len(self._network.nodes),
            'links': len(self._network.links),
            'active_nodes': active,
            'total_activation': sum(n.activation for n in self._network.nodes),
            'events': len(self._spreader.events)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_spreading_activation_engine(
    decay: float = 0.1,
    spreading_factor: float = 0.7
) -> SpreadingActivationEngine:
    """Create spreading activation engine."""
    return SpreadingActivationEngine(decay, spreading_factor)


def create_semantic_network() -> SemanticNetwork:
    """Create empty semantic network."""
    return SemanticNetwork()


def quick_activation_test(
    concepts: List[Tuple[str, str]],
    relations: List[Tuple[str, str, float]],
    activate: str,
    iterations: int = 5
) -> List[Tuple[str, float]]:
    """Quick test of spreading activation."""
    engine = SpreadingActivationEngine()

    # Add concepts
    for cid, label in concepts:
        engine.add_concept(cid, label)

    # Add relations
    for src, tgt, weight in relations:
        engine.add_relation(src, tgt, strength=weight)

    # Activate and spread
    engine.activate(activate)
    engine.spread(iterations)

    return engine.get_active_concepts()
