#!/usr/bin/env python3
"""
BAEL - Causality Engine
Causal reasoning and inference for agents.

Features:
- Causal graph modeling
- Intervention analysis
- Counterfactual reasoning
- Effect estimation
- Causal discovery
"""

import asyncio
import hashlib
import json
import math
import random
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class RelationType(Enum):
    """Types of causal relationships."""
    CAUSES = "causes"
    PREVENTS = "prevents"
    ENABLES = "enables"
    INHIBITS = "inhibits"
    CORRELATES = "correlates"


class EffectType(Enum):
    """Types of effects."""
    DIRECT = "direct"
    INDIRECT = "indirect"
    TOTAL = "total"
    MEDIATED = "mediated"


class ConfidenceLevel(Enum):
    """Confidence levels."""
    VERY_LOW = 0.2
    LOW = 0.4
    MEDIUM = 0.6
    HIGH = 0.8
    VERY_HIGH = 0.95


class InterventionType(Enum):
    """Types of interventions."""
    DO = "do"
    OBSERVE = "observe"
    COUNTERFACTUAL = "counterfactual"


class DiscoveryMethod(Enum):
    """Causal discovery methods."""
    CORRELATION = "correlation"
    TEMPORAL = "temporal"
    INTERVENTION = "intervention"
    CONSTRAINT = "constraint"


class NodeState(Enum):
    """States of causal nodes."""
    UNKNOWN = "unknown"
    OBSERVED = "observed"
    INTERVENED = "intervened"
    INFERRED = "inferred"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class CausalNode:
    """A node in a causal graph."""
    node_id: str = ""
    name: str = ""
    value: Optional[Any] = None
    state: NodeState = NodeState.UNKNOWN
    parents: List[str] = field(default_factory=list)
    children: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.node_id:
            self.node_id = str(uuid.uuid4())[:8]


@dataclass
class CausalEdge:
    """An edge in a causal graph."""
    edge_id: str = ""
    source: str = ""
    target: str = ""
    relation: RelationType = RelationType.CAUSES
    strength: float = 0.5
    confidence: float = 0.5
    delay: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.edge_id:
            self.edge_id = str(uuid.uuid4())[:8]


@dataclass
class CausalEffect:
    """A causal effect estimate."""
    effect_id: str = ""
    cause: str = ""
    effect: str = ""
    effect_type: EffectType = EffectType.DIRECT
    magnitude: float = 0.0
    confidence: float = 0.5
    path: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.effect_id:
            self.effect_id = str(uuid.uuid4())[:8]


@dataclass
class Intervention:
    """An intervention in the causal graph."""
    intervention_id: str = ""
    node_id: str = ""
    intervention_type: InterventionType = InterventionType.DO
    value: Any = None
    timestamp: datetime = field(default_factory=datetime.now)
    effects: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.intervention_id:
            self.intervention_id = str(uuid.uuid4())[:8]


@dataclass
class CounterfactualQuery:
    """A counterfactual query."""
    query_id: str = ""
    factual_state: Dict[str, Any] = field(default_factory=dict)
    intervention: Dict[str, Any] = field(default_factory=dict)
    target_nodes: List[str] = field(default_factory=list)
    result: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if not self.query_id:
            self.query_id = str(uuid.uuid4())[:8]


@dataclass
class CausalConfig:
    """Causality configuration."""
    default_strength: float = 0.5
    min_confidence: float = 0.3
    propagation_decay: float = 0.8


# =============================================================================
# CAUSAL GRAPH
# =============================================================================

class CausalGraph:
    """A causal graph structure."""

    def __init__(self):
        self._nodes: Dict[str, CausalNode] = {}
        self._edges: Dict[str, CausalEdge] = {}

        self._adjacency: Dict[str, Set[str]] = defaultdict(set)
        self._reverse_adjacency: Dict[str, Set[str]] = defaultdict(set)

    def add_node(
        self,
        name: str,
        value: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> CausalNode:
        """Add a node to the graph."""
        node = CausalNode(
            name=name,
            value=value,
            metadata=metadata or {}
        )

        self._nodes[node.node_id] = node

        return node

    def get_node(self, node_id: str) -> Optional[CausalNode]:
        """Get a node by ID."""
        return self._nodes.get(node_id)

    def get_node_by_name(self, name: str) -> Optional[CausalNode]:
        """Get a node by name."""
        for node in self._nodes.values():
            if node.name == name:
                return node
        return None

    def remove_node(self, node_id: str) -> bool:
        """Remove a node from the graph."""
        if node_id not in self._nodes:
            return False

        edges_to_remove = [
            eid for eid, edge in self._edges.items()
            if edge.source == node_id or edge.target == node_id
        ]

        for eid in edges_to_remove:
            self.remove_edge(eid)

        del self._nodes[node_id]

        return True

    def add_edge(
        self,
        source: str,
        target: str,
        relation: RelationType = RelationType.CAUSES,
        strength: float = 0.5,
        confidence: float = 0.5,
        delay: float = 0.0
    ) -> Optional[CausalEdge]:
        """Add an edge to the graph."""
        if source not in self._nodes or target not in self._nodes:
            return None

        edge = CausalEdge(
            source=source,
            target=target,
            relation=relation,
            strength=strength,
            confidence=confidence,
            delay=delay
        )

        self._edges[edge.edge_id] = edge

        self._adjacency[source].add(target)
        self._reverse_adjacency[target].add(source)

        self._nodes[source].children.append(target)
        self._nodes[target].parents.append(source)

        return edge

    def get_edge(self, edge_id: str) -> Optional[CausalEdge]:
        """Get an edge by ID."""
        return self._edges.get(edge_id)

    def get_edge_between(
        self,
        source: str,
        target: str
    ) -> Optional[CausalEdge]:
        """Get edge between two nodes."""
        for edge in self._edges.values():
            if edge.source == source and edge.target == target:
                return edge
        return None

    def remove_edge(self, edge_id: str) -> bool:
        """Remove an edge from the graph."""
        edge = self._edges.get(edge_id)

        if not edge:
            return False

        self._adjacency[edge.source].discard(edge.target)
        self._reverse_adjacency[edge.target].discard(edge.source)

        if edge.target in self._nodes[edge.source].children:
            self._nodes[edge.source].children.remove(edge.target)
        if edge.source in self._nodes[edge.target].parents:
            self._nodes[edge.target].parents.remove(edge.source)

        del self._edges[edge_id]

        return True

    def get_parents(self, node_id: str) -> List[str]:
        """Get parent nodes."""
        return list(self._reverse_adjacency.get(node_id, set()))

    def get_children(self, node_id: str) -> List[str]:
        """Get child nodes."""
        return list(self._adjacency.get(node_id, set()))

    def get_ancestors(self, node_id: str) -> Set[str]:
        """Get all ancestor nodes."""
        ancestors = set()
        queue = list(self._reverse_adjacency.get(node_id, set()))

        while queue:
            current = queue.pop(0)
            if current not in ancestors:
                ancestors.add(current)
                queue.extend(self._reverse_adjacency.get(current, set()))

        return ancestors

    def get_descendants(self, node_id: str) -> Set[str]:
        """Get all descendant nodes."""
        descendants = set()
        queue = list(self._adjacency.get(node_id, set()))

        while queue:
            current = queue.pop(0)
            if current not in descendants:
                descendants.add(current)
                queue.extend(self._adjacency.get(current, set()))

        return descendants

    def find_paths(
        self,
        source: str,
        target: str,
        max_length: int = 5
    ) -> List[List[str]]:
        """Find all paths between nodes."""
        paths = []

        def dfs(current: str, path: List[str]) -> None:
            if len(path) > max_length:
                return

            if current == target:
                paths.append(path[:])
                return

            for child in self._adjacency.get(current, set()):
                if child not in path:
                    path.append(child)
                    dfs(child, path)
                    path.pop()

        dfs(source, [source])

        return paths

    def is_ancestor(self, potential_ancestor: str, node_id: str) -> bool:
        """Check if node is an ancestor."""
        return potential_ancestor in self.get_ancestors(node_id)

    def has_cycle(self) -> bool:
        """Check if graph has cycles."""
        visited = set()
        rec_stack = set()

        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)

            for child in self._adjacency.get(node, set()):
                if child not in visited:
                    if dfs(child):
                        return True
                elif child in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        for node in self._nodes:
            if node not in visited:
                if dfs(node):
                    return True

        return False

    def topological_sort(self) -> List[str]:
        """Get topological ordering of nodes."""
        in_degree = defaultdict(int)

        for node_id in self._nodes:
            in_degree[node_id] = len(self._reverse_adjacency.get(node_id, set()))

        queue = [n for n in self._nodes if in_degree[n] == 0]
        result = []

        while queue:
            node = queue.pop(0)
            result.append(node)

            for child in self._adjacency.get(node, set()):
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)

        return result

    def get_all_nodes(self) -> List[CausalNode]:
        """Get all nodes."""
        return list(self._nodes.values())

    def get_all_edges(self) -> List[CausalEdge]:
        """Get all edges."""
        return list(self._edges.values())


# =============================================================================
# EFFECT ESTIMATOR
# =============================================================================

class EffectEstimator:
    """Estimate causal effects."""

    def __init__(
        self,
        graph: CausalGraph,
        decay: float = 0.8
    ):
        self._graph = graph
        self._decay = decay

    def estimate_direct_effect(
        self,
        cause: str,
        effect: str
    ) -> Optional[CausalEffect]:
        """Estimate direct causal effect."""
        edge = self._graph.get_edge_between(cause, effect)

        if not edge:
            return None

        magnitude = edge.strength

        if edge.relation == RelationType.PREVENTS:
            magnitude = -magnitude
        elif edge.relation == RelationType.INHIBITS:
            magnitude = -magnitude * 0.5
        elif edge.relation == RelationType.ENABLES:
            magnitude = magnitude * 0.8

        return CausalEffect(
            cause=cause,
            effect=effect,
            effect_type=EffectType.DIRECT,
            magnitude=magnitude,
            confidence=edge.confidence,
            path=[cause, effect]
        )

    def estimate_total_effect(
        self,
        cause: str,
        effect: str
    ) -> Optional[CausalEffect]:
        """Estimate total causal effect through all paths."""
        paths = self._graph.find_paths(cause, effect)

        if not paths:
            return None

        total_magnitude = 0.0
        min_confidence = 1.0

        for path in paths:
            path_magnitude = 1.0
            path_confidence = 1.0

            for i in range(len(path) - 1):
                edge = self._graph.get_edge_between(path[i], path[i + 1])

                if edge:
                    edge_magnitude = edge.strength

                    if edge.relation == RelationType.PREVENTS:
                        edge_magnitude = -edge_magnitude

                    path_magnitude *= edge_magnitude * self._decay
                    path_confidence = min(path_confidence, edge.confidence)

            total_magnitude += path_magnitude
            min_confidence = min(min_confidence, path_confidence)

        return CausalEffect(
            cause=cause,
            effect=effect,
            effect_type=EffectType.TOTAL,
            magnitude=min(1.0, max(-1.0, total_magnitude)),
            confidence=min_confidence,
            path=paths[0] if paths else []
        )

    def estimate_indirect_effect(
        self,
        cause: str,
        effect: str,
        mediator: str
    ) -> Optional[CausalEffect]:
        """Estimate indirect effect through mediator."""
        cause_to_mediator = self.estimate_direct_effect(cause, mediator)
        mediator_to_effect = self.estimate_direct_effect(mediator, effect)

        if not cause_to_mediator or not mediator_to_effect:
            return None

        magnitude = (
            cause_to_mediator.magnitude *
            mediator_to_effect.magnitude *
            self._decay
        )

        confidence = min(
            cause_to_mediator.confidence,
            mediator_to_effect.confidence
        )

        return CausalEffect(
            cause=cause,
            effect=effect,
            effect_type=EffectType.MEDIATED,
            magnitude=magnitude,
            confidence=confidence,
            path=[cause, mediator, effect]
        )


# =============================================================================
# INTERVENTION HANDLER
# =============================================================================

class InterventionHandler:
    """Handle causal interventions."""

    def __init__(self, graph: CausalGraph):
        self._graph = graph
        self._interventions: List[Intervention] = []

    def do(
        self,
        node_id: str,
        value: Any
    ) -> Intervention:
        """Perform a do intervention (set value, cut incoming edges)."""
        node = self._graph.get_node(node_id)

        if not node:
            return Intervention(
                node_id=node_id,
                intervention_type=InterventionType.DO,
                value=value,
                effects={"error": "Node not found"}
            )

        old_value = node.value
        node.value = value
        node.state = NodeState.INTERVENED

        effects = self._propagate_intervention(node_id)

        intervention = Intervention(
            node_id=node_id,
            intervention_type=InterventionType.DO,
            value=value,
            effects=effects
        )

        self._interventions.append(intervention)

        return intervention

    def observe(
        self,
        node_id: str,
        value: Any
    ) -> Intervention:
        """Observe a node value (update without cutting edges)."""
        node = self._graph.get_node(node_id)

        if not node:
            return Intervention(
                node_id=node_id,
                intervention_type=InterventionType.OBSERVE,
                value=value,
                effects={"error": "Node not found"}
            )

        node.value = value
        node.state = NodeState.OBSERVED

        intervention = Intervention(
            node_id=node_id,
            intervention_type=InterventionType.OBSERVE,
            value=value,
            effects={}
        )

        self._interventions.append(intervention)

        return intervention

    def _propagate_intervention(
        self,
        node_id: str
    ) -> Dict[str, Any]:
        """Propagate intervention effects through graph."""
        effects = {}

        node = self._graph.get_node(node_id)
        if not node or node.value is None:
            return effects

        try:
            base_value = float(node.value)
        except (TypeError, ValueError):
            return effects

        descendants = self._graph.get_descendants(node_id)

        for desc_id in self._graph.topological_sort():
            if desc_id not in descendants:
                continue

            desc_node = self._graph.get_node(desc_id)
            if not desc_node:
                continue

            parent_contributions = []

            for parent_id in desc_node.parents:
                parent = self._graph.get_node(parent_id)
                edge = self._graph.get_edge_between(parent_id, desc_id)

                if parent and edge and parent.value is not None:
                    try:
                        parent_value = float(parent.value)
                        contribution = parent_value * edge.strength

                        if edge.relation == RelationType.PREVENTS:
                            contribution = -contribution

                        parent_contributions.append(contribution)
                    except (TypeError, ValueError):
                        pass

            if parent_contributions:
                new_value = sum(parent_contributions) / len(parent_contributions)
                desc_node.value = new_value
                desc_node.state = NodeState.INFERRED
                effects[desc_id] = new_value

        return effects

    def get_interventions(self) -> List[Intervention]:
        """Get intervention history."""
        return self._interventions[:]

    def reset(self) -> None:
        """Reset all nodes to unknown state."""
        for node in self._graph.get_all_nodes():
            node.state = NodeState.UNKNOWN
            node.value = None

        self._interventions.clear()


# =============================================================================
# COUNTERFACTUAL REASONER
# =============================================================================

class CounterfactualReasoner:
    """Reason about counterfactuals."""

    def __init__(
        self,
        graph: CausalGraph,
        intervention_handler: InterventionHandler
    ):
        self._graph = graph
        self._handler = intervention_handler

    def query(
        self,
        factual_state: Dict[str, Any],
        intervention: Dict[str, Any],
        target_nodes: List[str]
    ) -> CounterfactualQuery:
        """Answer a counterfactual query."""
        saved_states = {}
        for node in self._graph.get_all_nodes():
            saved_states[node.node_id] = (node.value, node.state)

        for node_id, value in factual_state.items():
            self._handler.observe(node_id, value)

        for node_id, value in intervention.items():
            self._handler.do(node_id, value)

        result = {}
        for target_id in target_nodes:
            node = self._graph.get_node(target_id)
            if node:
                result[target_id] = node.value

        for node_id, (value, state) in saved_states.items():
            node = self._graph.get_node(node_id)
            if node:
                node.value = value
                node.state = state

        return CounterfactualQuery(
            factual_state=factual_state,
            intervention=intervention,
            target_nodes=target_nodes,
            result=result
        )

    def what_if(
        self,
        condition_node: str,
        condition_value: Any,
        target_node: str
    ) -> Tuple[Any, float]:
        """Answer 'what if' question."""
        query = self.query(
            factual_state={},
            intervention={condition_node: condition_value},
            target_nodes=[target_node]
        )

        result = query.result.get(target_node) if query.result else None

        edge = self._graph.get_edge_between(condition_node, target_node)
        confidence = edge.confidence if edge else 0.5

        return result, confidence

    def compare_outcomes(
        self,
        intervention_a: Dict[str, Any],
        intervention_b: Dict[str, Any],
        target_nodes: List[str]
    ) -> Dict[str, Tuple[Any, Any]]:
        """Compare outcomes of two interventions."""
        query_a = self.query({}, intervention_a, target_nodes)
        query_b = self.query({}, intervention_b, target_nodes)

        comparison = {}

        for target in target_nodes:
            val_a = query_a.result.get(target) if query_a.result else None
            val_b = query_b.result.get(target) if query_b.result else None
            comparison[target] = (val_a, val_b)

        return comparison


# =============================================================================
# CAUSAL DISCOVERER
# =============================================================================

class CausalDiscoverer:
    """Discover causal relationships from data."""

    def __init__(self, min_confidence: float = 0.3):
        self._min_confidence = min_confidence

    def discover_from_correlations(
        self,
        data: List[Dict[str, float]],
        variables: List[str]
    ) -> List[Tuple[str, str, float]]:
        """Discover causal relationships from correlations."""
        if not data or len(data) < 2:
            return []

        edges = []

        for i, var_a in enumerate(variables):
            for var_b in variables[i + 1:]:
                corr = self._compute_correlation(data, var_a, var_b)

                if abs(corr) > self._min_confidence:
                    edges.append((var_a, var_b, corr))

        return edges

    def discover_from_temporal(
        self,
        time_series: List[Tuple[datetime, Dict[str, float]]],
        variables: List[str],
        lag: int = 1
    ) -> List[Tuple[str, str, float]]:
        """Discover causal relationships from temporal data."""
        if len(time_series) < lag + 2:
            return []

        edges = []

        for var_a in variables:
            for var_b in variables:
                if var_a == var_b:
                    continue

                granger = self._compute_granger_like(
                    time_series, var_a, var_b, lag
                )

                if granger > self._min_confidence:
                    edges.append((var_a, var_b, granger))

        return edges

    def _compute_correlation(
        self,
        data: List[Dict[str, float]],
        var_a: str,
        var_b: str
    ) -> float:
        """Compute correlation between variables."""
        values_a = [d.get(var_a, 0) for d in data]
        values_b = [d.get(var_b, 0) for d in data]

        n = len(values_a)
        if n == 0:
            return 0.0

        mean_a = sum(values_a) / n
        mean_b = sum(values_b) / n

        cov = sum((a - mean_a) * (b - mean_b) for a, b in zip(values_a, values_b)) / n

        std_a = math.sqrt(sum((a - mean_a) ** 2 for a in values_a) / n)
        std_b = math.sqrt(sum((b - mean_b) ** 2 for b in values_b) / n)

        if std_a == 0 or std_b == 0:
            return 0.0

        return cov / (std_a * std_b)

    def _compute_granger_like(
        self,
        time_series: List[Tuple[datetime, Dict[str, float]]],
        var_a: str,
        var_b: str,
        lag: int
    ) -> float:
        """Compute Granger-like causality score."""
        lagged_pairs = []

        for i in range(lag, len(time_series)):
            past_a = time_series[i - lag][1].get(var_a, 0)
            current_b = time_series[i][1].get(var_b, 0)
            lagged_pairs.append((past_a, current_b))

        if not lagged_pairs:
            return 0.0

        n = len(lagged_pairs)

        mean_a = sum(p[0] for p in lagged_pairs) / n
        mean_b = sum(p[1] for p in lagged_pairs) / n

        cov = sum((p[0] - mean_a) * (p[1] - mean_b) for p in lagged_pairs) / n

        std_a = math.sqrt(sum((p[0] - mean_a) ** 2 for p in lagged_pairs) / n)
        std_b = math.sqrt(sum((p[1] - mean_b) ** 2 for p in lagged_pairs) / n)

        if std_a == 0 or std_b == 0:
            return 0.0

        return abs(cov / (std_a * std_b))


# =============================================================================
# CAUSALITY ENGINE
# =============================================================================

class CausalityEngine:
    """
    Causality Engine for BAEL.

    Causal reasoning and inference.
    """

    def __init__(self, config: Optional[CausalConfig] = None):
        self._config = config or CausalConfig()

        self._graph = CausalGraph()
        self._effect_estimator = EffectEstimator(
            self._graph,
            decay=self._config.propagation_decay
        )
        self._intervention_handler = InterventionHandler(self._graph)
        self._counterfactual = CounterfactualReasoner(
            self._graph,
            self._intervention_handler
        )
        self._discoverer = CausalDiscoverer(
            min_confidence=self._config.min_confidence
        )

    # ----- Graph Operations -----

    def add_variable(
        self,
        name: str,
        value: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> CausalNode:
        """Add a causal variable."""
        return self._graph.add_node(name, value, metadata)

    def add_cause(
        self,
        cause: str,
        effect: str,
        strength: float = 0.5,
        confidence: float = 0.5,
        relation: RelationType = RelationType.CAUSES
    ) -> Optional[CausalEdge]:
        """Add a causal relationship."""
        return self._graph.add_edge(
            cause, effect, relation, strength, confidence
        )

    def get_variable(self, node_id: str) -> Optional[CausalNode]:
        """Get a causal variable."""
        return self._graph.get_node(node_id)

    def get_variable_by_name(self, name: str) -> Optional[CausalNode]:
        """Get a variable by name."""
        return self._graph.get_node_by_name(name)

    def get_parents(self, node_id: str) -> List[str]:
        """Get parent nodes (direct causes)."""
        return self._graph.get_parents(node_id)

    def get_children(self, node_id: str) -> List[str]:
        """Get child nodes (direct effects)."""
        return self._graph.get_children(node_id)

    def get_ancestors(self, node_id: str) -> Set[str]:
        """Get all ancestor nodes (all causes)."""
        return self._graph.get_ancestors(node_id)

    def get_descendants(self, node_id: str) -> Set[str]:
        """Get all descendant nodes (all effects)."""
        return self._graph.get_descendants(node_id)

    def find_causal_paths(
        self,
        cause: str,
        effect: str
    ) -> List[List[str]]:
        """Find causal paths between nodes."""
        return self._graph.find_paths(cause, effect)

    # ----- Effect Estimation -----

    def estimate_direct_effect(
        self,
        cause: str,
        effect: str
    ) -> Optional[CausalEffect]:
        """Estimate direct causal effect."""
        return self._effect_estimator.estimate_direct_effect(cause, effect)

    def estimate_total_effect(
        self,
        cause: str,
        effect: str
    ) -> Optional[CausalEffect]:
        """Estimate total causal effect."""
        return self._effect_estimator.estimate_total_effect(cause, effect)

    def estimate_mediated_effect(
        self,
        cause: str,
        effect: str,
        mediator: str
    ) -> Optional[CausalEffect]:
        """Estimate effect through mediator."""
        return self._effect_estimator.estimate_indirect_effect(
            cause, effect, mediator
        )

    # ----- Interventions -----

    def do(
        self,
        node_id: str,
        value: Any
    ) -> Intervention:
        """Perform do intervention."""
        return self._intervention_handler.do(node_id, value)

    def observe(
        self,
        node_id: str,
        value: Any
    ) -> Intervention:
        """Observe a value."""
        return self._intervention_handler.observe(node_id, value)

    def reset_interventions(self) -> None:
        """Reset all interventions."""
        self._intervention_handler.reset()

    # ----- Counterfactuals -----

    def counterfactual_query(
        self,
        factual_state: Dict[str, Any],
        intervention: Dict[str, Any],
        target_nodes: List[str]
    ) -> CounterfactualQuery:
        """Answer counterfactual query."""
        return self._counterfactual.query(
            factual_state, intervention, target_nodes
        )

    def what_if(
        self,
        condition_node: str,
        condition_value: Any,
        target_node: str
    ) -> Tuple[Any, float]:
        """Answer what-if question."""
        return self._counterfactual.what_if(
            condition_node, condition_value, target_node
        )

    def compare_interventions(
        self,
        intervention_a: Dict[str, Any],
        intervention_b: Dict[str, Any],
        target_nodes: List[str]
    ) -> Dict[str, Tuple[Any, Any]]:
        """Compare two interventions."""
        return self._counterfactual.compare_outcomes(
            intervention_a, intervention_b, target_nodes
        )

    # ----- Discovery -----

    def discover_from_data(
        self,
        data: List[Dict[str, float]],
        variables: List[str]
    ) -> List[Tuple[str, str, float]]:
        """Discover causal relationships from data."""
        return self._discoverer.discover_from_correlations(data, variables)

    def discover_from_timeseries(
        self,
        time_series: List[Tuple[datetime, Dict[str, float]]],
        variables: List[str],
        lag: int = 1
    ) -> List[Tuple[str, str, float]]:
        """Discover from temporal data."""
        return self._discoverer.discover_from_temporal(
            time_series, variables, lag
        )

    # ----- State -----

    def has_cycles(self) -> bool:
        """Check if causal graph has cycles."""
        return self._graph.has_cycle()

    def get_topological_order(self) -> List[str]:
        """Get topological ordering."""
        return self._graph.topological_sort()

    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        nodes = self._graph.get_all_nodes()
        edges = self._graph.get_all_edges()

        return {
            "variables": len(nodes),
            "causal_relations": len(edges),
            "has_cycles": self.has_cycles(),
            "interventions": len(self._intervention_handler.get_interventions())
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Causality Engine."""
    print("=" * 70)
    print("BAEL - CAUSALITY ENGINE DEMO")
    print("Causal Reasoning and Inference")
    print("=" * 70)
    print()

    engine = CausalityEngine()

    # 1. Create Causal Graph
    print("1. CREATE CAUSAL GRAPH:")
    print("-" * 40)

    rain = engine.add_variable("rain")
    print(f"   Added: {rain.name} ({rain.node_id})")

    sprinkler = engine.add_variable("sprinkler")
    print(f"   Added: {sprinkler.name} ({sprinkler.node_id})")

    wet_grass = engine.add_variable("wet_grass")
    print(f"   Added: {wet_grass.name} ({wet_grass.node_id})")

    slippery = engine.add_variable("slippery")
    print(f"   Added: {slippery.name} ({slippery.node_id})")
    print()

    # 2. Add Causal Relationships
    print("2. ADD CAUSAL RELATIONSHIPS:")
    print("-" * 40)

    e1 = engine.add_cause(rain.node_id, wet_grass.node_id, strength=0.8, confidence=0.9)
    print(f"   {rain.name} -> {wet_grass.name} (strength={e1.strength})")

    e2 = engine.add_cause(sprinkler.node_id, wet_grass.node_id, strength=0.7, confidence=0.85)
    print(f"   {sprinkler.name} -> {wet_grass.name} (strength={e2.strength})")

    e3 = engine.add_cause(wet_grass.node_id, slippery.node_id, strength=0.9, confidence=0.95)
    print(f"   {wet_grass.name} -> {slippery.name} (strength={e3.strength})")

    e4 = engine.add_cause(
        rain.node_id, sprinkler.node_id,
        strength=0.6, confidence=0.7,
        relation=RelationType.PREVENTS
    )
    print(f"   {rain.name} -X {sprinkler.name} (prevents, strength={e4.strength})")
    print()

    # 3. Query Graph Structure
    print("3. QUERY GRAPH STRUCTURE:")
    print("-" * 40)

    parents = engine.get_parents(wet_grass.node_id)
    print(f"   Parents of wet_grass: {len(parents)}")

    descendants = engine.get_descendants(rain.node_id)
    print(f"   Descendants of rain: {len(descendants)}")

    paths = engine.find_causal_paths(rain.node_id, slippery.node_id)
    print(f"   Paths from rain to slippery: {len(paths)}")
    print()

    # 4. Estimate Effects
    print("4. ESTIMATE CAUSAL EFFECTS:")
    print("-" * 40)

    direct = engine.estimate_direct_effect(rain.node_id, wet_grass.node_id)
    if direct:
        print(f"   Direct: rain -> wet_grass = {direct.magnitude:.2f}")

    total = engine.estimate_total_effect(rain.node_id, slippery.node_id)
    if total:
        print(f"   Total: rain -> slippery = {total.magnitude:.2f}")

    mediated = engine.estimate_mediated_effect(
        rain.node_id, slippery.node_id, wet_grass.node_id
    )
    if mediated:
        print(f"   Mediated: rain -> wet_grass -> slippery = {mediated.magnitude:.2f}")
    print()

    # 5. Perform Interventions
    print("5. PERFORM INTERVENTIONS:")
    print("-" * 40)

    intervention = engine.do(rain.node_id, 1.0)
    print(f"   do({rain.name} = 1.0)")
    print(f"   Effects propagated to {len(intervention.effects)} nodes")

    for node_id, value in intervention.effects.items():
        node = engine.get_variable(node_id)
        if node:
            print(f"     {node.name} = {value:.2f}")
    print()

    # Reset
    engine.reset_interventions()

    # 6. What-If Analysis
    print("6. WHAT-IF ANALYSIS:")
    print("-" * 40)

    result, confidence = engine.what_if(
        rain.node_id, 1.0, slippery.node_id
    )
    print(f"   What if rain=1.0? slippery = {result}")
    print(f"   Confidence: {confidence:.2f}")
    print()

    # 7. Compare Interventions
    print("7. COMPARE INTERVENTIONS:")
    print("-" * 40)

    comparison = engine.compare_interventions(
        {rain.node_id: 1.0},
        {sprinkler.node_id: 1.0},
        [wet_grass.node_id, slippery.node_id]
    )

    print("   Comparing do(rain=1) vs do(sprinkler=1):")
    for target_id, (val_a, val_b) in comparison.items():
        node = engine.get_variable(target_id)
        if node:
            print(f"     {node.name}: {val_a} vs {val_b}")
    print()

    # 8. Counterfactual Query
    print("8. COUNTERFACTUAL QUERY:")
    print("-" * 40)

    query = engine.counterfactual_query(
        factual_state={wet_grass.node_id: 1.0},
        intervention={rain.node_id: 0.0},
        target_nodes=[slippery.node_id]
    )

    print(f"   Given wet_grass=1.0, if rain had been 0.0:")
    if query.result:
        for node_id, value in query.result.items():
            node = engine.get_variable(node_id)
            if node:
                print(f"     {node.name} would be: {value}")
    print()

    # 9. Causal Discovery
    print("9. CAUSAL DISCOVERY:")
    print("-" * 40)

    data = [
        {"temperature": 30, "ice_cream": 100, "drowning": 10},
        {"temperature": 25, "ice_cream": 80, "drowning": 8},
        {"temperature": 35, "ice_cream": 120, "drowning": 12},
        {"temperature": 20, "ice_cream": 60, "drowning": 5},
        {"temperature": 40, "ice_cream": 150, "drowning": 15},
    ]

    discovered = engine.discover_from_data(
        data,
        ["temperature", "ice_cream", "drowning"]
    )

    print("   Discovered correlations:")
    for var_a, var_b, corr in discovered:
        print(f"     {var_a} <-> {var_b}: {corr:.2f}")
    print()

    # 10. Temporal Discovery
    print("10. TEMPORAL DISCOVERY:")
    print("-" * 40)

    now = datetime.now()
    time_series = [
        (now, {"ad_spend": 100, "sales": 50}),
        (now + timedelta(days=1), {"ad_spend": 120, "sales": 55}),
        (now + timedelta(days=2), {"ad_spend": 80, "sales": 45}),
        (now + timedelta(days=3), {"ad_spend": 150, "sales": 70}),
        (now + timedelta(days=4), {"ad_spend": 90, "sales": 48}),
    ]

    temporal = engine.discover_from_timeseries(
        time_series,
        ["ad_spend", "sales"],
        lag=1
    )

    print("   Temporal relationships:")
    for var_a, var_b, strength in temporal:
        print(f"     {var_a} -> {var_b}: {strength:.2f}")
    print()

    # 11. Graph Properties
    print("11. GRAPH PROPERTIES:")
    print("-" * 40)

    print(f"   Has cycles: {engine.has_cycles()}")
    print(f"   Topological order: {len(engine.get_topological_order())} nodes")
    print()

    # 12. Summary
    print("12. ENGINE SUMMARY:")
    print("-" * 40)

    summary = engine.summary()

    for key, value in summary.items():
        print(f"   {key}: {value}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Causality Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
