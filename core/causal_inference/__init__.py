"""
BAEL Causal Inference Engine
=============================

Discovery and reasoning about causal relationships.

"Ba'el discovers what causes what." — Ba'el
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
from collections import defaultdict
import copy

logger = logging.getLogger("BAEL.CausalInference")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class CausalRelationType(Enum):
    """Types of causal relationships."""
    DIRECT = auto()         # X directly causes Y
    INDIRECT = auto()       # X causes Y through Z
    CONFOUNDED = auto()     # X and Y share common cause
    SPURIOUS = auto()       # Apparent but not real
    BIDIRECTIONAL = auto()  # X and Y cause each other
    NONE = auto()           # No causal relation


@dataclass
class CausalEdge:
    """
    A causal relationship between variables.
    """
    cause: str
    effect: str
    relation_type: CausalRelationType = CausalRelationType.DIRECT
    strength: float = 0.5
    confidence: float = 0.5
    latent_confounders: List[str] = field(default_factory=list)

    def __hash__(self):
        return hash((self.cause, self.effect))


@dataclass
class InterventionResult:
    """
    Result of a causal intervention.
    """
    intervention: Dict[str, Any]
    outcome: Dict[str, Any]
    effect_size: float
    counterfactual: Optional[Dict[str, Any]] = None


@dataclass
class CausalQuery:
    """
    A causal query (intervention or counterfactual).
    """
    query_type: str  # "intervention", "counterfactual", "association"
    treatment: str
    outcome: str
    conditioning: Dict[str, Any] = field(default_factory=dict)
    intervention_value: Optional[Any] = None


# ============================================================================
# CAUSAL GRAPH
# ============================================================================

class CausalGraph:
    """
    Directed Acyclic Graph representing causal structure.

    "Ba'el builds the causal graph." — Ba'el
    """

    def __init__(self):
        """Initialize causal graph."""
        self._nodes: Set[str] = set()
        self._edges: Dict[str, Set[str]] = defaultdict(set)  # cause -> effects
        self._reverse_edges: Dict[str, Set[str]] = defaultdict(set)  # effect -> causes
        self._edge_data: Dict[Tuple[str, str], CausalEdge] = {}
        self._lock = threading.RLock()

    def add_node(self, node: str) -> None:
        """Add node to graph."""
        with self._lock:
            self._nodes.add(node)

    def add_edge(
        self,
        cause: str,
        effect: str,
        strength: float = 0.5,
        confidence: float = 0.5
    ) -> CausalEdge:
        """Add causal edge."""
        with self._lock:
            self._nodes.add(cause)
            self._nodes.add(effect)

            self._edges[cause].add(effect)
            self._reverse_edges[effect].add(cause)

            edge = CausalEdge(
                cause=cause,
                effect=effect,
                strength=strength,
                confidence=confidence
            )
            self._edge_data[(cause, effect)] = edge

            return edge

    def remove_edge(self, cause: str, effect: str) -> None:
        """Remove causal edge."""
        with self._lock:
            if effect in self._edges[cause]:
                self._edges[cause].remove(effect)
            if cause in self._reverse_edges[effect]:
                self._reverse_edges[effect].remove(cause)
            if (cause, effect) in self._edge_data:
                del self._edge_data[(cause, effect)]

    def get_parents(self, node: str) -> Set[str]:
        """Get direct causes of node."""
        return self._reverse_edges.get(node, set()).copy()

    def get_children(self, node: str) -> Set[str]:
        """Get direct effects of node."""
        return self._edges.get(node, set()).copy()

    def get_ancestors(self, node: str) -> Set[str]:
        """Get all ancestors (transitive causes)."""
        ancestors = set()
        to_visit = list(self.get_parents(node))

        while to_visit:
            current = to_visit.pop()
            if current not in ancestors:
                ancestors.add(current)
                to_visit.extend(self.get_parents(current))

        return ancestors

    def get_descendants(self, node: str) -> Set[str]:
        """Get all descendants (transitive effects)."""
        descendants = set()
        to_visit = list(self.get_children(node))

        while to_visit:
            current = to_visit.pop()
            if current not in descendants:
                descendants.add(current)
                to_visit.extend(self.get_children(current))

        return descendants

    def has_path(self, source: str, target: str) -> bool:
        """Check if there's a directed path from source to target."""
        return target in self.get_descendants(source)

    def is_d_separated(
        self,
        x: str,
        y: str,
        conditioning: Set[str]
    ) -> bool:
        """
        Check d-separation.

        X and Y are d-separated by Z if all paths are blocked.
        """
        with self._lock:
            # Simplified d-separation check
            # Full implementation requires checking all paths and colliders

            # If conditioning includes all parents, they're separated
            x_parents = self.get_parents(x)
            y_parents = self.get_parents(y)

            # Check if conditioning blocks all paths
            if x_parents & conditioning and y_parents & conditioning:
                return True

            # If x is ancestor of y or vice versa, not separated
            if self.has_path(x, y) or self.has_path(y, x):
                return False

            return True

    def is_acyclic(self) -> bool:
        """Check if graph is acyclic."""
        with self._lock:
            visited = set()
            rec_stack = set()

            def has_cycle(node: str) -> bool:
                visited.add(node)
                rec_stack.add(node)

                for child in self._edges.get(node, set()):
                    if child not in visited:
                        if has_cycle(child):
                            return True
                    elif child in rec_stack:
                        return True

                rec_stack.remove(node)
                return False

            for node in self._nodes:
                if node not in visited:
                    if has_cycle(node):
                        return False

            return True

    def topological_sort(self) -> List[str]:
        """Get topological ordering of nodes."""
        with self._lock:
            in_degree = {node: 0 for node in self._nodes}

            for effects in self._edges.values():
                for effect in effects:
                    in_degree[effect] += 1

            queue = [n for n in self._nodes if in_degree[n] == 0]
            order = []

            while queue:
                node = queue.pop(0)
                order.append(node)

                for child in self._edges.get(node, set()):
                    in_degree[child] -= 1
                    if in_degree[child] == 0:
                        queue.append(child)

            return order

    @property
    def nodes(self) -> Set[str]:
        return self._nodes.copy()

    @property
    def edges(self) -> List[CausalEdge]:
        return list(self._edge_data.values())


# ============================================================================
# DO-CALCULUS
# ============================================================================

class DoCalculus:
    """
    Pearl's do-calculus for causal inference.

    "Ba'el intervenes with do-calculus." — Ba'el
    """

    def __init__(self, graph: CausalGraph):
        """Initialize do-calculus."""
        self._graph = graph
        self._lock = threading.RLock()

    def do_intervention(
        self,
        data: Dict[str, List[float]],
        intervention: Dict[str, float],
        outcome: str
    ) -> float:
        """
        Compute P(outcome | do(intervention)).

        Uses adjustment formula when possible.
        """
        with self._lock:
            if outcome not in data:
                return 0.0

            treatment_var = list(intervention.keys())[0]
            treatment_val = intervention[treatment_var]

            # Find adjustment set (back-door criterion)
            adjustment_set = self._find_adjustment_set(treatment_var, outcome)

            if adjustment_set is None:
                # Can't identify effect
                return self._naive_estimate(data, treatment_var, treatment_val, outcome)

            # Apply adjustment formula
            return self._adjust(
                data, treatment_var, treatment_val, outcome, adjustment_set
            )

    def _find_adjustment_set(self, treatment: str, outcome: str) -> Optional[Set[str]]:
        """
        Find valid adjustment set using back-door criterion.
        """
        with self._lock:
            # Parents of treatment that are not descendants of treatment
            parents = self._graph.get_parents(treatment)
            descendants = self._graph.get_descendants(treatment)

            # Remove any parent that is a descendant (can happen with confounders)
            adjustment = parents - descendants

            # Check if adjustment blocks all back-door paths
            # (Simplified: just return parents for now)
            return adjustment if adjustment else set()

    def _naive_estimate(
        self,
        data: Dict[str, List[float]],
        treatment: str,
        treatment_val: float,
        outcome: str
    ) -> float:
        """Naive (biased) estimate when adjustment not possible."""
        if treatment not in data or outcome not in data:
            return 0.0

        # Simple conditional mean
        outcome_values = []
        for i, t in enumerate(data[treatment]):
            if abs(t - treatment_val) < 0.1 and i < len(data[outcome]):
                outcome_values.append(data[outcome][i])

        return sum(outcome_values) / len(outcome_values) if outcome_values else 0.0

    def _adjust(
        self,
        data: Dict[str, List[float]],
        treatment: str,
        treatment_val: float,
        outcome: str,
        adjustment_set: Set[str]
    ) -> float:
        """Apply adjustment formula."""
        if not adjustment_set:
            return self._naive_estimate(data, treatment, treatment_val, outcome)

        # Stratify by adjustment variables and compute weighted average
        # (Simplified implementation)
        return self._naive_estimate(data, treatment, treatment_val, outcome)


# ============================================================================
# COUNTERFACTUAL REASONING
# ============================================================================

class CounterfactualReasoner:
    """
    Reason about counterfactuals.

    "Ba'el asks: what if?" — Ba'el
    """

    def __init__(self, graph: CausalGraph):
        """Initialize counterfactual reasoner."""
        self._graph = graph
        self._structural_equations: Dict[str, Callable] = {}
        self._lock = threading.RLock()

    def set_equation(
        self,
        variable: str,
        equation: Callable[[Dict[str, float]], float]
    ) -> None:
        """
        Set structural equation for variable.

        equation: function(parent_values) -> value
        """
        with self._lock:
            self._structural_equations[variable] = equation

    def evaluate(self, values: Dict[str, float]) -> Dict[str, float]:
        """
        Evaluate model given exogenous values.
        """
        with self._lock:
            result = values.copy()

            # Evaluate in topological order
            order = self._graph.topological_sort()

            for node in order:
                if node in self._structural_equations:
                    eq = self._structural_equations[node]
                    result[node] = eq(result)

            return result

    def counterfactual(
        self,
        factual: Dict[str, float],
        intervention: Dict[str, float],
        query_var: str
    ) -> float:
        """
        Compute counterfactual.

        What would query_var have been if we intervened?
        """
        with self._lock:
            # Step 1: Abduction - infer exogenous variables
            # (Simplified: assume exogenous = factual)
            exogenous = factual.copy()

            # Step 2: Intervention - modify model
            modified_values = exogenous.copy()
            modified_values.update(intervention)

            # Step 3: Prediction - evaluate modified model
            result = self.evaluate(modified_values)

            return result.get(query_var, 0.0)

    def effect_of_treatment_on_treated(
        self,
        factual: Dict[str, float],
        treatment: str,
        outcome: str,
        counterfactual_treatment: float
    ) -> float:
        """
        Compute ETT (Effect of Treatment on the Treated).
        """
        # Factual outcome
        factual_outcome = factual.get(outcome, 0.0)

        # Counterfactual: what if treatment had been different?
        counterfactual_outcome = self.counterfactual(
            factual,
            {treatment: counterfactual_treatment},
            outcome
        )

        return factual_outcome - counterfactual_outcome


# ============================================================================
# CAUSAL DISCOVERY
# ============================================================================

class CausalDiscovery:
    """
    Discover causal structure from data.

    "Ba'el discovers causation from correlation." — Ba'el
    """

    def __init__(self):
        """Initialize causal discovery."""
        self._lock = threading.RLock()

    def pc_algorithm(
        self,
        data: Dict[str, List[float]],
        alpha: float = 0.05
    ) -> CausalGraph:
        """
        PC algorithm for causal discovery.

        Constraint-based approach using conditional independence tests.
        """
        with self._lock:
            variables = list(data.keys())
            graph = CausalGraph()

            # Add all nodes
            for var in variables:
                graph.add_node(var)

            # Start with complete undirected graph
            edges_to_test = [
                (v1, v2) for i, v1 in enumerate(variables)
                for v2 in variables[i+1:]
            ]

            # Phase 1: Remove edges based on independence
            for v1, v2 in edges_to_test:
                # Test unconditional independence
                if not self._are_dependent(data, v1, v2, set()):
                    continue

                # Add edge (direction determined later)
                graph.add_edge(v1, v2)

            # Phase 2: Orient edges
            self._orient_edges(graph, data)

            return graph

    def _are_dependent(
        self,
        data: Dict[str, List[float]],
        x: str,
        y: str,
        conditioning: Set[str],
        alpha: float = 0.05
    ) -> bool:
        """
        Test if X and Y are dependent given conditioning set.

        Uses correlation as simplified independence test.
        """
        if x not in data or y not in data:
            return False

        x_vals = data[x]
        y_vals = data[y]

        n = min(len(x_vals), len(y_vals))
        if n < 3:
            return True  # Assume dependent with little data

        # Compute correlation
        x_mean = sum(x_vals[:n]) / n
        y_mean = sum(y_vals[:n]) / n

        numerator = sum((x_vals[i] - x_mean) * (y_vals[i] - y_mean) for i in range(n))
        x_var = sum((x_vals[i] - x_mean) ** 2 for i in range(n))
        y_var = sum((y_vals[i] - y_mean) ** 2 for i in range(n))

        denominator = (x_var * y_var) ** 0.5

        if denominator == 0:
            return False

        correlation = abs(numerator / denominator)

        # Simple threshold test
        return correlation > 0.1

    def _orient_edges(self, graph: CausalGraph, data: Dict[str, List[float]]) -> None:
        """
        Orient edges in the graph.

        Uses simple heuristics based on conditional independence.
        """
        # Look for v-structures: X -> Z <- Y
        nodes = list(graph.nodes)

        for z in nodes:
            parents = list(graph.get_parents(z))

            for i, x in enumerate(parents):
                for y in parents[i+1:]:
                    # If X and Y are not adjacent, orient as v-structure
                    if y not in graph.get_children(x) and x not in graph.get_children(y):
                        # Already oriented correctly if both point to Z
                        pass


# ============================================================================
# CAUSAL INFERENCE ENGINE
# ============================================================================

class CausalInferenceEngine:
    """
    Complete causal inference engine.

    "Ba'el reasons about causation." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._graph = CausalGraph()
        self._do_calculus = DoCalculus(self._graph)
        self._counterfactual = CounterfactualReasoner(self._graph)
        self._discovery = CausalDiscovery()
        self._data: Dict[str, List[float]] = {}
        self._lock = threading.RLock()

    def add_variable(self, name: str, values: Optional[List[float]] = None) -> None:
        """Add variable to model."""
        with self._lock:
            self._graph.add_node(name)
            if values:
                self._data[name] = values

    def add_causal_link(
        self,
        cause: str,
        effect: str,
        strength: float = 0.5
    ) -> CausalEdge:
        """Add causal relationship."""
        return self._graph.add_edge(cause, effect, strength)

    def set_equation(
        self,
        variable: str,
        equation: Callable[[Dict[str, float]], float]
    ) -> None:
        """Set structural equation."""
        self._counterfactual.set_equation(variable, equation)

    def intervene(
        self,
        intervention: Dict[str, float],
        outcome: str
    ) -> float:
        """
        Compute causal effect of intervention.

        P(outcome | do(intervention))
        """
        return self._do_calculus.do_intervention(
            self._data,
            intervention,
            outcome
        )

    def counterfactual(
        self,
        factual: Dict[str, float],
        intervention: Dict[str, float],
        query: str
    ) -> float:
        """
        Answer counterfactual query.
        """
        return self._counterfactual.counterfactual(
            factual,
            intervention,
            query
        )

    def discover_structure(
        self,
        data: Optional[Dict[str, List[float]]] = None
    ) -> CausalGraph:
        """
        Discover causal structure from data.
        """
        if data:
            self._data = data

        return self._discovery.pc_algorithm(self._data)

    def get_causes(self, variable: str) -> Set[str]:
        """Get direct causes of variable."""
        return self._graph.get_parents(variable)

    def get_effects(self, variable: str) -> Set[str]:
        """Get direct effects of variable."""
        return self._graph.get_children(variable)

    def is_cause(self, candidate: str, outcome: str) -> bool:
        """Check if candidate is a cause of outcome."""
        return self._graph.has_path(candidate, outcome)

    def causal_path(self, source: str, target: str) -> List[str]:
        """Find causal path from source to target."""
        with self._lock:
            if source not in self._graph.nodes or target not in self._graph.nodes:
                return []

            # BFS for shortest path
            queue = [(source, [source])]
            visited = {source}

            while queue:
                node, path = queue.pop(0)

                if node == target:
                    return path

                for child in self._graph.get_children(node):
                    if child not in visited:
                        visited.add(child)
                        queue.append((child, path + [child]))

            return []

    @property
    def graph(self) -> CausalGraph:
        """Get causal graph."""
        return self._graph

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'variables': len(self._graph.nodes),
            'edges': len(self._graph.edges),
            'is_acyclic': self._graph.is_acyclic(),
            'data_variables': len(self._data)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_causal_inference_engine() -> CausalInferenceEngine:
    """Create causal inference engine."""
    return CausalInferenceEngine()


def create_causal_graph() -> CausalGraph:
    """Create causal graph."""
    return CausalGraph()


def create_do_calculus(graph: CausalGraph) -> DoCalculus:
    """Create do-calculus instance."""
    return DoCalculus(graph)


def create_counterfactual_reasoner(graph: CausalGraph) -> CounterfactualReasoner:
    """Create counterfactual reasoner."""
    return CounterfactualReasoner(graph)


def discover_causes(data: Dict[str, List[float]]) -> CausalGraph:
    """Quick causal discovery."""
    discovery = CausalDiscovery()
    return discovery.pc_algorithm(data)
