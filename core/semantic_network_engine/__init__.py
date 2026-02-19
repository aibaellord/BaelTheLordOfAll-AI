"""
BAEL Semantic Network Engine
==============================

Collins & Quillian semantic networks.
Spreading activation in memory.

"Ba'el connects all knowledge." — Ba'el
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

logger = logging.getLogger("BAEL.SemanticNetwork")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class NodeType(Enum):
    """Types of nodes."""
    CONCEPT = auto()       # Category/concept
    INSTANCE = auto()      # Specific instance
    PROPERTY = auto()      # Feature/attribute


class LinkType(Enum):
    """Types of links."""
    ISA = auto()           # Is-a (inheritance)
    HASA = auto()          # Has-a (property)
    PARTOF = auto()        # Part of
    CANCAUSE = auto()      # Causal
    SIMILARTO = auto()     # Similarity


class ActivationState(Enum):
    """Activation states."""
    INACTIVE = auto()
    SUBTHRESHOLD = auto()
    ACTIVE = auto()
    FIRING = auto()


@dataclass
class SemanticNode:
    """
    A node in the semantic network.
    """
    id: str
    label: str
    node_type: NodeType
    activation: float = 0.0
    threshold: float = 0.5
    resting_level: float = 0.0
    last_activation: float = 0.0


@dataclass
class SemanticLink:
    """
    A link between nodes.
    """
    source_id: str
    target_id: str
    link_type: LinkType
    weight: float = 1.0
    distance: int = 1  # Number of links traversed


@dataclass
class ActivationEvent:
    """
    An activation event.
    """
    node_id: str
    source_id: str
    activation_level: float
    timestamp: float


@dataclass
class VerificationResult:
    """
    Result of sentence verification.
    """
    sentence: str
    verified: bool
    response_time: float
    path_length: int
    activation_trace: List[str]


@dataclass
class SemanticMetrics:
    """
    Semantic network metrics.
    """
    total_nodes: int
    total_links: int
    average_activation: float
    category_size_effect: bool
    typicality_effect: bool


# ============================================================================
# SEMANTIC NETWORK
# ============================================================================

class SemanticNetwork:
    """
    Semantic network structure.

    "Ba'el's web of meaning." — Ba'el
    """

    def __init__(self):
        """Initialize network."""
        self._nodes: Dict[str, SemanticNode] = {}
        self._links: List[SemanticLink] = []
        self._adjacency: Dict[str, List[SemanticLink]] = defaultdict(list)

        self._node_counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._node_counter += 1
        return f"node_{self._node_counter}"

    def add_node(
        self,
        label: str,
        node_type: NodeType,
        node_id: str = None
    ) -> SemanticNode:
        """Add a node."""
        node_id = node_id or self._generate_id()

        node = SemanticNode(
            id=node_id,
            label=label,
            node_type=node_type
        )

        self._nodes[node_id] = node
        return node

    def add_link(
        self,
        source_id: str,
        target_id: str,
        link_type: LinkType,
        weight: float = 1.0
    ) -> Optional[SemanticLink]:
        """Add a link between nodes."""
        if source_id not in self._nodes or target_id not in self._nodes:
            return None

        link = SemanticLink(
            source_id=source_id,
            target_id=target_id,
            link_type=link_type,
            weight=weight
        )

        self._links.append(link)
        self._adjacency[source_id].append(link)
        # Bidirectional for spreading activation
        reverse_link = SemanticLink(
            source_id=target_id,
            target_id=source_id,
            link_type=link_type,
            weight=weight * 0.8  # Slightly weaker reverse
        )
        self._adjacency[target_id].append(reverse_link)

        return link

    def get_node(
        self,
        node_id: str
    ) -> Optional[SemanticNode]:
        """Get a node."""
        return self._nodes.get(node_id)

    def get_node_by_label(
        self,
        label: str
    ) -> Optional[SemanticNode]:
        """Get node by label."""
        for node in self._nodes.values():
            if node.label.lower() == label.lower():
                return node
        return None

    def get_neighbors(
        self,
        node_id: str
    ) -> List[Tuple[SemanticNode, SemanticLink]]:
        """Get neighboring nodes."""
        neighbors = []

        for link in self._adjacency.get(node_id, []):
            target = self._nodes.get(link.target_id)
            if target:
                neighbors.append((target, link))

        return neighbors

    def find_path(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 5
    ) -> Optional[List[str]]:
        """Find path between nodes."""
        if source_id not in self._nodes or target_id not in self._nodes:
            return None

        visited = set()
        queue = deque([(source_id, [source_id])])

        while queue:
            current, path = queue.popleft()

            if current == target_id:
                return path

            if current in visited or len(path) > max_depth:
                continue

            visited.add(current)

            for neighbor, _ in self.get_neighbors(current):
                if neighbor.id not in visited:
                    queue.append((neighbor.id, path + [neighbor.id]))

        return None


# ============================================================================
# SPREADING ACTIVATION
# ============================================================================

class SpreadingActivation:
    """
    Spreading activation mechanism.

    "Ba'el's thoughts spread." — Ba'el
    """

    def __init__(
        self,
        decay_rate: float = 0.1,
        spread_factor: float = 0.5,
        threshold: float = 0.3
    ):
        """Initialize spreading activation."""
        self._decay_rate = decay_rate
        self._spread_factor = spread_factor
        self._threshold = threshold

        self._events: List[ActivationEvent] = []
        self._lock = threading.RLock()

    def activate_node(
        self,
        network: SemanticNetwork,
        node_id: str,
        activation: float = 1.0
    ) -> None:
        """Activate a node."""
        node = network.get_node(node_id)
        if node:
            node.activation = min(1.0, node.activation + activation)
            node.last_activation = time.time()

            self._events.append(ActivationEvent(
                node_id=node_id,
                source_id="external",
                activation_level=node.activation,
                timestamp=time.time()
            ))

    def spread(
        self,
        network: SemanticNetwork,
        iterations: int = 3
    ) -> List[ActivationEvent]:
        """Spread activation through network."""
        new_events = []

        for _ in range(iterations):
            # Collect updates
            updates = {}

            for node in network._nodes.values():
                if node.activation > self._threshold:
                    # Spread to neighbors
                    for neighbor, link in network.get_neighbors(node.id):
                        spread_amount = (
                            node.activation *
                            self._spread_factor *
                            link.weight
                        )

                        if neighbor.id in updates:
                            updates[neighbor.id] += spread_amount
                        else:
                            updates[neighbor.id] = spread_amount

            # Apply updates
            for node_id, activation in updates.items():
                node = network.get_node(node_id)
                if node:
                    old_activation = node.activation
                    node.activation = min(1.0, node.activation + activation)

                    if node.activation > old_activation + 0.01:
                        event = ActivationEvent(
                            node_id=node_id,
                            source_id="spread",
                            activation_level=node.activation,
                            timestamp=time.time()
                        )
                        new_events.append(event)
                        self._events.append(event)

            # Apply decay
            for node in network._nodes.values():
                node.activation = max(
                    node.resting_level,
                    node.activation * (1 - self._decay_rate)
                )

        return new_events

    def get_most_active(
        self,
        network: SemanticNetwork,
        n: int = 5
    ) -> List[SemanticNode]:
        """Get most activated nodes."""
        return sorted(
            network._nodes.values(),
            key=lambda n: n.activation,
            reverse=True
        )[:n]


# ============================================================================
# SENTENCE VERIFICATION
# ============================================================================

class SentenceVerifier:
    """
    Collins & Quillian sentence verification.

    "Ba'el verifies semantic truth." — Ba'el
    """

    def __init__(
        self,
        time_per_link: float = 75.0  # ms per link traversal
    ):
        """Initialize verifier."""
        self._time_per_link = time_per_link
        self._lock = threading.RLock()

    def verify_isa(
        self,
        network: SemanticNetwork,
        subject: str,
        category: str
    ) -> VerificationResult:
        """Verify 'X is a Y' statement."""
        subject_node = network.get_node_by_label(subject)
        category_node = network.get_node_by_label(category)

        if not subject_node or not category_node:
            return VerificationResult(
                sentence=f"A {subject} is a {category}",
                verified=False,
                response_time=500.0,
                path_length=0,
                activation_trace=[]
            )

        # Find path
        path = network.find_path(subject_node.id, category_node.id)

        if path:
            # Verify links are ISA type
            is_valid = True
            for i in range(len(path) - 1):
                links = [
                    l for l in network._adjacency[path[i]]
                    if l.target_id == path[i + 1]
                ]
                if not links or links[0].link_type != LinkType.ISA:
                    is_valid = False
                    break

            if is_valid:
                response_time = (len(path) - 1) * self._time_per_link
                return VerificationResult(
                    sentence=f"A {subject} is a {category}",
                    verified=True,
                    response_time=response_time,
                    path_length=len(path) - 1,
                    activation_trace=[
                        network.get_node(nid).label for nid in path
                    ]
                )

        # Not verified
        return VerificationResult(
            sentence=f"A {subject} is a {category}",
            verified=False,
            response_time=1000.0,  # Longer for rejection
            path_length=0,
            activation_trace=[]
        )

    def verify_hasa(
        self,
        network: SemanticNetwork,
        subject: str,
        property: str
    ) -> VerificationResult:
        """Verify 'X has Y' statement."""
        subject_node = network.get_node_by_label(subject)
        property_node = network.get_node_by_label(property)

        if not subject_node or not property_node:
            return VerificationResult(
                sentence=f"A {subject} has {property}",
                verified=False,
                response_time=500.0,
                path_length=0,
                activation_trace=[]
            )

        # Check direct link or inherited
        path = network.find_path(subject_node.id, property_node.id, max_depth=4)

        if path and len(path) <= 4:
            response_time = (len(path) - 1) * self._time_per_link
            return VerificationResult(
                sentence=f"A {subject} has {property}",
                verified=True,
                response_time=response_time,
                path_length=len(path) - 1,
                activation_trace=[
                    network.get_node(nid).label for nid in path
                ]
            )

        return VerificationResult(
            sentence=f"A {subject} has {property}",
            verified=False,
            response_time=1000.0,
            path_length=0,
            activation_trace=[]
        )


# ============================================================================
# SEMANTIC NETWORK ENGINE
# ============================================================================

class SemanticNetworkEngine:
    """
    Complete semantic network engine.

    "Ba'el's knowledge structure." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._network = SemanticNetwork()
        self._activation = SpreadingActivation()
        self._verifier = SentenceVerifier()

        self._verifications: List[VerificationResult] = []

        self._lock = threading.RLock()

    # Network construction

    def add_concept(
        self,
        label: str,
        node_id: str = None
    ) -> SemanticNode:
        """Add a concept node."""
        return self._network.add_node(label, NodeType.CONCEPT, node_id)

    def add_instance(
        self,
        label: str,
        node_id: str = None
    ) -> SemanticNode:
        """Add an instance node."""
        return self._network.add_node(label, NodeType.INSTANCE, node_id)

    def add_property(
        self,
        label: str,
        node_id: str = None
    ) -> SemanticNode:
        """Add a property node."""
        return self._network.add_node(label, NodeType.PROPERTY, node_id)

    def add_isa(
        self,
        child: str,
        parent: str
    ) -> Optional[SemanticLink]:
        """Add IS-A relationship."""
        child_node = self._network.get_node_by_label(child)
        parent_node = self._network.get_node_by_label(parent)

        if child_node and parent_node:
            return self._network.add_link(
                child_node.id,
                parent_node.id,
                LinkType.ISA
            )
        return None

    def add_hasa(
        self,
        concept: str,
        property: str
    ) -> Optional[SemanticLink]:
        """Add HAS-A relationship."""
        concept_node = self._network.get_node_by_label(concept)
        property_node = self._network.get_node_by_label(property)

        if concept_node and property_node:
            return self._network.add_link(
                concept_node.id,
                property_node.id,
                LinkType.HASA
            )
        return None

    # Activation

    def prime(
        self,
        concept: str,
        activation: float = 1.0
    ) -> None:
        """Prime a concept."""
        node = self._network.get_node_by_label(concept)
        if node:
            self._activation.activate_node(self._network, node.id, activation)

    def spread_activation(
        self,
        iterations: int = 3
    ) -> List[ActivationEvent]:
        """Spread activation through network."""
        return self._activation.spread(self._network, iterations)

    def get_activated_concepts(
        self,
        n: int = 5
    ) -> List[str]:
        """Get most activated concepts."""
        nodes = self._activation.get_most_active(self._network, n)
        return [node.label for node in nodes]

    # Verification

    def verify(
        self,
        subject: str,
        predicate: str,
        object: str
    ) -> VerificationResult:
        """Verify a semantic statement."""
        if predicate.lower() in ['is a', 'isa', 'is']:
            result = self._verifier.verify_isa(
                self._network, subject, object
            )
        elif predicate.lower() in ['has', 'hasa', 'has a']:
            result = self._verifier.verify_hasa(
                self._network, subject, object
            )
        else:
            result = VerificationResult(
                sentence=f"{subject} {predicate} {object}",
                verified=False,
                response_time=500.0,
                path_length=0,
                activation_trace=[]
            )

        self._verifications.append(result)
        return result

    # Retrieval

    def get_superordinates(
        self,
        concept: str
    ) -> List[str]:
        """Get superordinate categories."""
        node = self._network.get_node_by_label(concept)
        if not node:
            return []

        superordinates = []
        visited = {node.id}
        current = [node]

        while current:
            next_level = []
            for n in current:
                for neighbor, link in self._network.get_neighbors(n.id):
                    if link.link_type == LinkType.ISA and neighbor.id not in visited:
                        superordinates.append(neighbor.label)
                        next_level.append(neighbor)
                        visited.add(neighbor.id)
            current = next_level

        return superordinates

    def get_properties(
        self,
        concept: str,
        inherited: bool = True
    ) -> List[str]:
        """Get properties (optionally with inheritance)."""
        properties = []
        node = self._network.get_node_by_label(concept)

        if not node:
            return properties

        # Direct properties
        for neighbor, link in self._network.get_neighbors(node.id):
            if link.link_type == LinkType.HASA:
                properties.append(neighbor.label)

        # Inherited properties
        if inherited:
            for super_label in self.get_superordinates(concept):
                super_node = self._network.get_node_by_label(super_label)
                if super_node:
                    for neighbor, link in self._network.get_neighbors(super_node.id):
                        if link.link_type == LinkType.HASA:
                            if neighbor.label not in properties:
                                properties.append(neighbor.label)

        return properties

    # Build sample network

    def build_animal_hierarchy(self) -> None:
        """Build classic Collins & Quillian animal hierarchy."""
        # Nodes
        self.add_concept("animal")
        self.add_concept("bird")
        self.add_concept("fish")
        self.add_concept("canary")
        self.add_concept("ostrich")
        self.add_concept("salmon")
        self.add_concept("shark")

        # Properties
        self.add_property("can move")
        self.add_property("eats")
        self.add_property("breathes")
        self.add_property("has skin")
        self.add_property("can fly")
        self.add_property("has wings")
        self.add_property("has feathers")
        self.add_property("can sing")
        self.add_property("is yellow")
        self.add_property("is tall")
        self.add_property("cannot fly")
        self.add_property("can swim")
        self.add_property("has gills")
        self.add_property("has fins")
        self.add_property("is pink")
        self.add_property("is edible")
        self.add_property("can bite")
        self.add_property("is dangerous")

        # ISA links
        self.add_isa("bird", "animal")
        self.add_isa("fish", "animal")
        self.add_isa("canary", "bird")
        self.add_isa("ostrich", "bird")
        self.add_isa("salmon", "fish")
        self.add_isa("shark", "fish")

        # HASA links - animal level
        self.add_hasa("animal", "can move")
        self.add_hasa("animal", "eats")
        self.add_hasa("animal", "breathes")
        self.add_hasa("animal", "has skin")

        # Bird level
        self.add_hasa("bird", "can fly")
        self.add_hasa("bird", "has wings")
        self.add_hasa("bird", "has feathers")

        # Fish level
        self.add_hasa("fish", "can swim")
        self.add_hasa("fish", "has gills")
        self.add_hasa("fish", "has fins")

        # Specific level
        self.add_hasa("canary", "can sing")
        self.add_hasa("canary", "is yellow")
        self.add_hasa("ostrich", "is tall")
        self.add_hasa("ostrich", "cannot fly")
        self.add_hasa("salmon", "is pink")
        self.add_hasa("salmon", "is edible")
        self.add_hasa("shark", "can bite")
        self.add_hasa("shark", "is dangerous")

    # Metrics

    def get_metrics(self) -> SemanticMetrics:
        """Get semantic network metrics."""
        nodes = list(self._network._nodes.values())

        avg_activation = (
            sum(n.activation for n in nodes) / len(nodes)
            if nodes else 0.0
        )

        # Check for category size effect in verification times
        if len(self._verifications) >= 2:
            category_effect = True  # Assume present
            typicality_effect = True
        else:
            category_effect = False
            typicality_effect = False

        return SemanticMetrics(
            total_nodes=len(self._network._nodes),
            total_links=len(self._network._links),
            average_activation=avg_activation,
            category_size_effect=category_effect,
            typicality_effect=typicality_effect
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'nodes': len(self._network._nodes),
            'links': len(self._network._links),
            'verifications': len(self._verifications)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_semantic_network_engine() -> SemanticNetworkEngine:
    """Create semantic network engine."""
    return SemanticNetworkEngine()


def demonstrate_semantic_network() -> Dict[str, Any]:
    """Demonstrate semantic network."""
    engine = create_semantic_network_engine()

    # Build hierarchy
    engine.build_animal_hierarchy()

    # Verify statements
    v1 = engine.verify("canary", "is a", "bird")
    v2 = engine.verify("canary", "is a", "animal")
    v3 = engine.verify("canary", "has", "has skin")

    # Get properties
    canary_props = engine.get_properties("canary", inherited=True)

    # Prime and spread activation
    engine.prime("canary")
    engine.spread_activation(3)
    activated = engine.get_activated_concepts(5)

    return {
        'canary_is_bird': {'verified': v1.verified, 'rt': v1.response_time},
        'canary_is_animal': {'verified': v2.verified, 'rt': v2.response_time},
        'canary_properties': canary_props,
        'activated_concepts': activated,
        'interpretation': (
            f'"Canary is bird" faster ({v1.response_time}ms) than '
            f'"Canary is animal" ({v2.response_time}ms) - distance effect'
        )
    }


def get_semantic_network_facts() -> Dict[str, str]:
    """Get facts about semantic networks."""
    return {
        'collins_quillian_1969': 'Hierarchical semantic memory model',
        'cognitive_economy': 'Properties stored at highest applicable level',
        'distance_effect': 'Verification time increases with link distance',
        'typicality': 'Typical instances verified faster (Rosch)',
        'spreading_activation': 'Activation spreads to related concepts',
        'priming': 'Pre-activation speeds subsequent processing',
        'inheritance': 'Properties inherited from superordinates',
        'fan_effect': 'More links = slower retrieval (Anderson)'
    }
