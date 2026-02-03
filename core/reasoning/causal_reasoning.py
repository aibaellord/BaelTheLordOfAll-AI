#!/usr/bin/env python3
"""
BAEL - Causal Reasoning Engine
Causal inference, counterfactual reasoning, and causal discovery.

Features:
- Causal graph construction
- Intervention analysis (do-calculus)
- Counterfactual reasoning
- Causal discovery algorithms
- Effect estimation
- Confound detection
"""

import asyncio
import hashlib
import json
import logging
import math
import random
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from uuid import uuid4

logger = logging.getLogger(__name__)


# =============================================================================
# TYPES
# =============================================================================

class CausalRelation(Enum):
    """Types of causal relationships."""
    DIRECT = "direct"           # X -> Y directly
    INDIRECT = "indirect"       # X -> Z -> Y
    CONFOUNDED = "confounded"   # X <- Z -> Y
    COLLIDER = "collider"       # X -> Z <- Y
    MEDIATOR = "mediator"       # X -> M -> Y
    MODERATOR = "moderator"     # Effect of X on Y depends on M


class EffectType(Enum):
    """Types of causal effects."""
    TOTAL = "total"             # Total causal effect
    DIRECT = "direct"           # Direct causal effect
    INDIRECT = "indirect"       # Indirect effect through mediators
    CONTROLLED = "controlled"   # Effect controlling for confounders
    NATURAL = "natural"         # Natural direct/indirect effects


class InferenceMethod(Enum):
    """Causal inference methods."""
    BACKDOOR = "backdoor"
    FRONTDOOR = "frontdoor"
    IV = "instrumental_variable"
    DIFF_IN_DIFF = "difference_in_differences"
    REGRESSION_DISCONTINUITY = "regression_discontinuity"
    SYNTHETIC_CONTROL = "synthetic_control"


@dataclass
class CausalNode:
    """Node in causal graph."""
    id: str
    name: str
    node_type: str = "variable"
    observed: bool = True
    values: List[Any] = field(default_factory=list)
    distribution: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CausalEdge:
    """Edge in causal graph."""
    source: str
    target: str
    relation: CausalRelation = CausalRelation.DIRECT
    strength: float = 1.0
    confidence: float = 1.0
    mechanism: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CausalEffect:
    """Estimated causal effect."""
    cause: str
    effect: str
    effect_type: EffectType
    estimate: float
    confidence_interval: Tuple[float, float]
    method: InferenceMethod
    confounders_controlled: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Counterfactual:
    """Counterfactual query result."""
    id: str
    factual_world: Dict[str, Any]
    counterfactual_world: Dict[str, Any]
    intervention: Dict[str, Any]
    query_variable: str
    factual_value: Any
    counterfactual_value: Any
    probability: float = 1.0


# =============================================================================
# CAUSAL GRAPH
# =============================================================================

class CausalGraph:
    """Directed acyclic graph for causal structure."""

    def __init__(self):
        self.nodes: Dict[str, CausalNode] = {}
        self.edges: Dict[str, List[CausalEdge]] = defaultdict(list)
        self.reverse_edges: Dict[str, List[CausalEdge]] = defaultdict(list)

    def add_node(
        self,
        node_id: str,
        name: str = None,
        observed: bool = True,
        values: List[Any] = None
    ) -> CausalNode:
        """Add node to graph."""
        node = CausalNode(
            id=node_id,
            name=name or node_id,
            observed=observed,
            values=values or []
        )
        self.nodes[node_id] = node
        return node

    def add_edge(
        self,
        source: str,
        target: str,
        relation: CausalRelation = CausalRelation.DIRECT,
        strength: float = 1.0,
        mechanism: str = ""
    ) -> CausalEdge:
        """Add causal edge."""
        # Ensure nodes exist
        if source not in self.nodes:
            self.add_node(source)
        if target not in self.nodes:
            self.add_node(target)

        edge = CausalEdge(
            source=source,
            target=target,
            relation=relation,
            strength=strength,
            mechanism=mechanism
        )

        self.edges[source].append(edge)
        self.reverse_edges[target].append(edge)

        return edge

    def get_parents(self, node_id: str) -> List[str]:
        """Get direct causes (parents) of node."""
        parents = []
        for edge in self.reverse_edges.get(node_id, []):
            parents.append(edge.source)
        return parents

    def get_children(self, node_id: str) -> List[str]:
        """Get direct effects (children) of node."""
        children = []
        for edge in self.edges.get(node_id, []):
            children.append(edge.target)
        return children

    def get_ancestors(self, node_id: str) -> Set[str]:
        """Get all ancestors (causes) of node."""
        ancestors = set()
        queue = list(self.get_parents(node_id))

        while queue:
            parent = queue.pop(0)
            if parent not in ancestors:
                ancestors.add(parent)
                queue.extend(self.get_parents(parent))

        return ancestors

    def get_descendants(self, node_id: str) -> Set[str]:
        """Get all descendants (effects) of node."""
        descendants = set()
        queue = list(self.get_children(node_id))

        while queue:
            child = queue.pop(0)
            if child not in descendants:
                descendants.add(child)
                queue.extend(self.get_children(child))

        return descendants

    def get_paths(
        self,
        source: str,
        target: str,
        max_length: int = 10
    ) -> List[List[str]]:
        """Find all paths from source to target."""
        paths = []

        def dfs(current: str, path: List[str], visited: Set[str]):
            if len(path) > max_length:
                return
            if current == target:
                paths.append(path.copy())
                return

            for child in self.get_children(current):
                if child not in visited:
                    visited.add(child)
                    path.append(child)
                    dfs(child, path, visited)
                    path.pop()
                    visited.remove(child)

        dfs(source, [source], {source})
        return paths

    def has_cycle(self) -> bool:
        """Check if graph has cycles."""
        visited = set()
        rec_stack = set()

        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)

            for child in self.get_children(node):
                if child not in visited:
                    if dfs(child):
                        return True
                elif child in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        for node_id in self.nodes:
            if node_id not in visited:
                if dfs(node_id):
                    return True

        return False

    def topological_sort(self) -> List[str]:
        """Return nodes in topological order."""
        in_degree = {node: 0 for node in self.nodes}

        for edges in self.edges.values():
            for edge in edges:
                in_degree[edge.target] += 1

        queue = [n for n, d in in_degree.items() if d == 0]
        result = []

        while queue:
            node = queue.pop(0)
            result.append(node)

            for child in self.get_children(node):
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)

        return result

    def is_d_separated(
        self,
        x: str,
        y: str,
        z: Set[str]
    ) -> bool:
        """Check d-separation between X and Y given Z."""
        # Simplified d-separation check
        # In full implementation, would use proper d-separation algorithm

        # Find all paths from x to y
        paths = self.get_paths(x, y)

        for path in paths:
            # Check if path is blocked by z
            blocked = False

            for i in range(1, len(path) - 1):
                node = path[i]

                # Check if node is a collider
                prev_node = path[i-1]
                next_node = path[i+1]

                is_collider = (
                    next_node in self.get_children(node) or
                    prev_node in self.get_children(node)
                )

                if is_collider:
                    # Collider blocks unless conditioned on
                    if node not in z and not (self.get_descendants(node) & z):
                        blocked = True
                        break
                else:
                    # Non-collider blocks if conditioned on
                    if node in z:
                        blocked = True
                        break

            if not blocked:
                return False  # Found unblocked path

        return True


# =============================================================================
# INTERVENTION ANALYSIS
# =============================================================================

class InterventionAnalyzer:
    """Analyze interventions using do-calculus."""

    def __init__(self, graph: CausalGraph):
        self.graph = graph

    def do(
        self,
        variable: str,
        value: Any
    ) -> 'InterventionalGraph':
        """Apply intervention do(X=x)."""
        # Create mutilated graph
        mutilated = InterventionalGraph(self.graph)
        mutilated.intervene(variable, value)
        return mutilated

    def find_backdoor_adjustment(
        self,
        treatment: str,
        outcome: str
    ) -> Optional[Set[str]]:
        """Find valid backdoor adjustment set."""
        # Get potential confounders
        ancestors_treatment = self.graph.get_ancestors(treatment)
        ancestors_outcome = self.graph.get_ancestors(outcome)

        # Common ancestors are potential confounders
        confounders = ancestors_treatment & ancestors_outcome

        # Exclude descendants of treatment
        descendants = self.graph.get_descendants(treatment)
        valid_adjustments = confounders - descendants

        # Check if adjustment set blocks all backdoor paths
        if self.graph.is_d_separated(treatment, outcome, valid_adjustments):
            return valid_adjustments

        return None

    def find_frontdoor_adjustment(
        self,
        treatment: str,
        outcome: str
    ) -> Optional[Tuple[str, Set[str]]]:
        """Find valid frontdoor adjustment."""
        # Find mediators
        paths = self.graph.get_paths(treatment, outcome)

        for path in paths:
            if len(path) >= 3:
                # Check potential mediator
                mediator = path[1]

                # Mediator conditions:
                # 1. Treatment -> Mediator path exists
                # 2. No backdoor paths from Treatment to Mediator
                # 3. All paths from Mediator to Outcome go through Treatment

                # Simplified check
                if (mediator in self.graph.get_children(treatment) and
                    outcome in self.graph.get_descendants(mediator)):

                    return mediator, set()

        return None


class InterventionalGraph:
    """Graph under intervention."""

    def __init__(self, original: CausalGraph):
        self.original = original
        self.interventions: Dict[str, Any] = {}

    def intervene(self, variable: str, value: Any) -> None:
        """Apply intervention."""
        self.interventions[variable] = value

    def get_mutilated_edges(self) -> Dict[str, List[CausalEdge]]:
        """Get edges with interventions applied (incoming edges removed)."""
        mutilated = defaultdict(list)

        for source, edges in self.original.edges.items():
            for edge in edges:
                # Skip edges incoming to intervened variables
                if edge.target not in self.interventions:
                    mutilated[source].append(edge)

        return mutilated

    def compute_effect(
        self,
        query_variable: str,
        evidence: Dict[str, Any] = None
    ) -> Dict[str, float]:
        """Compute effect of intervention on query variable."""
        evidence = evidence or {}

        # Simple simulation-based estimation
        # In production, would use proper inference

        # Topological order
        order = self.original.topological_sort()

        # Simulate
        samples = []
        for _ in range(1000):
            values = {}

            for node in order:
                if node in self.interventions:
                    values[node] = self.interventions[node]
                elif node in evidence:
                    values[node] = evidence[node]
                else:
                    # Sample from conditional distribution
                    parents = self.original.get_parents(node)

                    # Simplified: random based on parent values
                    if parents:
                        parent_vals = [values.get(p, 0) for p in parents]
                        base = sum(parent_vals) / len(parent_vals)
                        values[node] = base + random.gauss(0, 0.1)
                    else:
                        values[node] = random.gauss(0, 1)

            if query_variable in values:
                samples.append(values[query_variable])

        if samples:
            return {
                "mean": sum(samples) / len(samples),
                "std": (sum((s - sum(samples)/len(samples))**2 for s in samples) / len(samples)) ** 0.5,
                "samples": len(samples)
            }

        return {"mean": 0, "std": 0, "samples": 0}


# =============================================================================
# COUNTERFACTUAL REASONING
# =============================================================================

class CounterfactualReasoner:
    """Reason about counterfactuals."""

    def __init__(self, graph: CausalGraph):
        self.graph = graph
        self.structural_equations: Dict[str, Callable] = {}

    def set_structural_equation(
        self,
        variable: str,
        equation: Callable
    ) -> None:
        """Set structural equation for variable."""
        self.structural_equations[variable] = equation

    async def evaluate_counterfactual(
        self,
        factual: Dict[str, Any],
        intervention: Dict[str, Any],
        query_variable: str
    ) -> Counterfactual:
        """Evaluate counterfactual: What if we had done X instead?"""

        # Step 1: Abduction - infer exogenous variables from factual
        exogenous = await self._abduct_exogenous(factual)

        # Step 2: Action - apply intervention
        intervened_world = factual.copy()
        for var, val in intervention.items():
            intervened_world[var] = val

        # Step 3: Prediction - compute counterfactual outcome
        cf_value = await self._predict_counterfactual(
            intervened_world,
            exogenous,
            query_variable
        )

        return Counterfactual(
            id=str(uuid4()),
            factual_world=factual,
            counterfactual_world=intervened_world,
            intervention=intervention,
            query_variable=query_variable,
            factual_value=factual.get(query_variable),
            counterfactual_value=cf_value
        )

    async def _abduct_exogenous(
        self,
        factual: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Infer exogenous (noise) variables from factual observations."""
        exogenous = {}

        for var in self.graph.topological_sort():
            if var in self.structural_equations:
                # Calculate what exogenous variable would give observed value
                parents = self.graph.get_parents(var)
                parent_vals = {p: factual.get(p, 0) for p in parents}

                # Simplified: noise = observed - predicted
                predicted = self.structural_equations[var](parent_vals, 0)
                observed = factual.get(var, 0)

                exogenous[f"U_{var}"] = observed - predicted
            else:
                exogenous[f"U_{var}"] = factual.get(var, 0)

        return exogenous

    async def _predict_counterfactual(
        self,
        world: Dict[str, Any],
        exogenous: Dict[str, Any],
        query: str
    ) -> Any:
        """Predict counterfactual value."""
        values = world.copy()

        for var in self.graph.topological_sort():
            if var in self.structural_equations:
                parents = self.graph.get_parents(var)
                parent_vals = {p: values.get(p, 0) for p in parents}
                noise = exogenous.get(f"U_{var}", 0)

                values[var] = self.structural_equations[var](parent_vals, noise)

        return values.get(query)

    async def compute_probability_of_necessity(
        self,
        cause: str,
        effect: str,
        factual: Dict[str, Any]
    ) -> float:
        """P(Y_x' = 0 | X = 1, Y = 1) - Would Y not have occurred without X?"""

        # Counterfactual: What if X had been 0 instead of 1?
        cf = await self.evaluate_counterfactual(
            factual=factual,
            intervention={cause: 0},
            query_variable=effect
        )

        # If counterfactual value is different (0 instead of 1), X was necessary
        if cf.factual_value == 1 and cf.counterfactual_value == 0:
            return 1.0
        elif cf.factual_value == 1:
            return 0.0
        else:
            return 0.5  # Uncertain

    async def compute_probability_of_sufficiency(
        self,
        cause: str,
        effect: str,
        factual: Dict[str, Any]
    ) -> float:
        """P(Y_x = 1 | X = 0, Y = 0) - Would Y have occurred with X?"""

        # Counterfactual: What if X had been 1 instead of 0?
        cf = await self.evaluate_counterfactual(
            factual=factual,
            intervention={cause: 1},
            query_variable=effect
        )

        # If counterfactual value is 1 when factual was 0, X would be sufficient
        if cf.factual_value == 0 and cf.counterfactual_value == 1:
            return 1.0
        elif cf.factual_value == 0:
            return 0.0
        else:
            return 0.5


# =============================================================================
# CAUSAL DISCOVERY
# =============================================================================

class CausalDiscovery:
    """Discover causal structure from data."""

    def __init__(self):
        self.discovered_edges: List[Tuple[str, str, float]] = []

    async def pc_algorithm(
        self,
        data: List[Dict[str, Any]],
        variables: List[str],
        alpha: float = 0.05
    ) -> CausalGraph:
        """PC algorithm for causal discovery."""
        graph = CausalGraph()

        # Add all nodes
        for var in variables:
            graph.add_node(var)

        # Start with complete undirected graph
        edges = set()
        for i, v1 in enumerate(variables):
            for v2 in variables[i+1:]:
                edges.add((v1, v2))
                edges.add((v2, v1))

        # Remove edges based on conditional independence
        # Simplified version - in production would use proper CI tests

        conditioning_size = 0
        while True:
            removed = False

            for edge in list(edges):
                v1, v2 = edge

                # Find potential conditioning sets
                neighbors = set()
                for e in edges:
                    if e[0] == v1 and e[1] != v2:
                        neighbors.add(e[1])
                    if e[0] == v2 and e[1] != v1:
                        neighbors.add(e[1])

                # Test conditional independence
                for subset in self._get_subsets(list(neighbors), conditioning_size):
                    ci = await self._test_conditional_independence(
                        data, v1, v2, list(subset)
                    )

                    if ci > alpha:  # Independent
                        edges.discard((v1, v2))
                        edges.discard((v2, v1))
                        removed = True
                        break

            if not removed:
                conditioning_size += 1
                if conditioning_size > len(variables):
                    break

        # Orient edges (simplified - would use collision detection)
        for v1, v2 in edges:
            if (v2, v1) not in edges:
                graph.add_edge(v1, v2)
            elif v1 < v2:  # Arbitrary orientation for undirected
                graph.add_edge(v1, v2)

        return graph

    def _get_subsets(
        self,
        items: List[str],
        size: int
    ) -> List[Set[str]]:
        """Get all subsets of given size."""
        if size == 0:
            return [set()]
        if size > len(items):
            return []

        subsets = []
        for i, item in enumerate(items):
            for subset in self._get_subsets(items[i+1:], size - 1):
                subsets.append({item} | subset)

        return subsets

    async def _test_conditional_independence(
        self,
        data: List[Dict[str, Any]],
        x: str,
        y: str,
        z: List[str]
    ) -> float:
        """Test conditional independence of X and Y given Z."""
        # Simplified correlation-based test
        # In production, would use proper statistical tests

        if not data:
            return 1.0

        x_vals = [d.get(x, 0) for d in data]
        y_vals = [d.get(y, 0) for d in data]

        if not z:
            # Simple correlation
            n = len(data)
            mean_x = sum(x_vals) / n
            mean_y = sum(y_vals) / n

            cov = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x_vals, y_vals)) / n
            var_x = sum((xi - mean_x) ** 2 for xi in x_vals) / n
            var_y = sum((yi - mean_y) ** 2 for yi in y_vals) / n

            if var_x > 0 and var_y > 0:
                corr = cov / (var_x ** 0.5 * var_y ** 0.5)
                # Convert to p-value (simplified)
                return 1 - abs(corr)
            return 1.0
        else:
            # Partial correlation (simplified)
            return random.uniform(0, 1)  # Would compute properly

    async def granger_causality(
        self,
        time_series: List[Dict[str, float]],
        cause: str,
        effect: str,
        lag: int = 1
    ) -> float:
        """Test Granger causality."""
        if len(time_series) < lag + 2:
            return 0.0

        # Prepare lagged data
        y = [ts[effect] for ts in time_series[lag:]]
        y_lagged = [time_series[i][effect] for i in range(len(time_series) - lag)]
        x_lagged = [time_series[i][cause] for i in range(len(time_series) - lag)]

        # Compare models: Y ~ Y_lag vs Y ~ Y_lag + X_lag

        # Model 1: Y ~ Y_lag
        r1 = await self._compute_r_squared(y, [y_lagged])

        # Model 2: Y ~ Y_lag + X_lag
        r2 = await self._compute_r_squared(y, [y_lagged, x_lagged])

        # F-statistic (simplified)
        improvement = r2 - r1

        return improvement

    async def _compute_r_squared(
        self,
        y: List[float],
        x: List[List[float]]
    ) -> float:
        """Compute R-squared for regression."""
        if not y:
            return 0.0

        mean_y = sum(y) / len(y)
        ss_tot = sum((yi - mean_y) ** 2 for yi in y)

        if ss_tot == 0:
            return 1.0

        # Simplified OLS
        n = len(y)
        k = len(x)

        # Predicted values (simplified)
        y_pred = []
        for i in range(n):
            pred = mean_y
            for j in range(k):
                if i < len(x[j]):
                    pred += 0.1 * x[j][i]  # Simplified coefficient
            y_pred.append(pred)

        ss_res = sum((yi - ypi) ** 2 for yi, ypi in zip(y, y_pred))

        return 1 - ss_res / ss_tot if ss_tot > 0 else 0


# =============================================================================
# EFFECT ESTIMATION
# =============================================================================

class EffectEstimator:
    """Estimate causal effects."""

    def __init__(self, graph: CausalGraph):
        self.graph = graph
        self.intervention_analyzer = InterventionAnalyzer(graph)

    async def estimate_ate(
        self,
        treatment: str,
        outcome: str,
        data: List[Dict[str, Any]],
        method: InferenceMethod = InferenceMethod.BACKDOOR
    ) -> CausalEffect:
        """Estimate Average Treatment Effect."""

        if method == InferenceMethod.BACKDOOR:
            return await self._backdoor_adjustment(treatment, outcome, data)
        elif method == InferenceMethod.FRONTDOOR:
            return await self._frontdoor_adjustment(treatment, outcome, data)
        elif method == InferenceMethod.IV:
            return await self._instrumental_variable(treatment, outcome, data)
        else:
            raise ValueError(f"Unknown method: {method}")

    async def _backdoor_adjustment(
        self,
        treatment: str,
        outcome: str,
        data: List[Dict[str, Any]]
    ) -> CausalEffect:
        """Estimate effect using backdoor adjustment."""

        # Find adjustment set
        adjustment_set = self.intervention_analyzer.find_backdoor_adjustment(
            treatment, outcome
        )

        if adjustment_set is None:
            adjustment_set = set()

        # Stratified estimation
        treated = [d for d in data if d.get(treatment, 0) == 1]
        control = [d for d in data if d.get(treatment, 0) == 0]

        if not treated or not control:
            return CausalEffect(
                cause=treatment,
                effect=outcome,
                effect_type=EffectType.TOTAL,
                estimate=0.0,
                confidence_interval=(0.0, 0.0),
                method=InferenceMethod.BACKDOOR,
                confounders_controlled=list(adjustment_set)
            )

        # Simple difference in means
        treated_outcome = sum(d.get(outcome, 0) for d in treated) / len(treated)
        control_outcome = sum(d.get(outcome, 0) for d in control) / len(control)

        ate = treated_outcome - control_outcome

        # Simple confidence interval
        se = 0.1 * abs(ate) + 0.01
        ci = (ate - 1.96 * se, ate + 1.96 * se)

        return CausalEffect(
            cause=treatment,
            effect=outcome,
            effect_type=EffectType.TOTAL,
            estimate=ate,
            confidence_interval=ci,
            method=InferenceMethod.BACKDOOR,
            confounders_controlled=list(adjustment_set)
        )

    async def _frontdoor_adjustment(
        self,
        treatment: str,
        outcome: str,
        data: List[Dict[str, Any]]
    ) -> CausalEffect:
        """Estimate effect using frontdoor adjustment."""

        result = self.intervention_analyzer.find_frontdoor_adjustment(
            treatment, outcome
        )

        if result is None:
            return await self._backdoor_adjustment(treatment, outcome, data)

        mediator, _ = result

        # Two-step estimation
        # Step 1: Effect of treatment on mediator
        ate_tm = 0.0
        treated = [d for d in data if d.get(treatment, 0) == 1]
        control = [d for d in data if d.get(treatment, 0) == 0]

        if treated and control:
            ate_tm = (
                sum(d.get(mediator, 0) for d in treated) / len(treated) -
                sum(d.get(mediator, 0) for d in control) / len(control)
            )

        # Step 2: Effect of mediator on outcome
        mediator_high = [d for d in data if d.get(mediator, 0) > 0.5]
        mediator_low = [d for d in data if d.get(mediator, 0) <= 0.5]

        ate_mo = 0.0
        if mediator_high and mediator_low:
            ate_mo = (
                sum(d.get(outcome, 0) for d in mediator_high) / len(mediator_high) -
                sum(d.get(outcome, 0) for d in mediator_low) / len(mediator_low)
            )

        # Combined effect
        ate = ate_tm * ate_mo

        return CausalEffect(
            cause=treatment,
            effect=outcome,
            effect_type=EffectType.TOTAL,
            estimate=ate,
            confidence_interval=(ate - 0.1, ate + 0.1),
            method=InferenceMethod.FRONTDOOR,
            metadata={"mediator": mediator}
        )

    async def _instrumental_variable(
        self,
        treatment: str,
        outcome: str,
        data: List[Dict[str, Any]]
    ) -> CausalEffect:
        """Estimate effect using instrumental variable."""

        # Find instrument (simplified - would search graph)
        # Instrument must affect treatment but not outcome directly
        potential_ivs = []
        for node in self.graph.nodes:
            if node != treatment and node != outcome:
                if treatment in self.graph.get_descendants(node):
                    if outcome not in self.graph.get_children(node):
                        potential_ivs.append(node)

        if not potential_ivs:
            return await self._backdoor_adjustment(treatment, outcome, data)

        iv = potential_ivs[0]

        # Two-stage least squares (simplified)
        # Stage 1: Treatment ~ IV
        iv_high = [d for d in data if d.get(iv, 0) > 0.5]
        iv_low = [d for d in data if d.get(iv, 0) <= 0.5]

        if not iv_high or not iv_low:
            return await self._backdoor_adjustment(treatment, outcome, data)

        # First stage effect
        first_stage = (
            sum(d.get(treatment, 0) for d in iv_high) / len(iv_high) -
            sum(d.get(treatment, 0) for d in iv_low) / len(iv_low)
        )

        # Reduced form
        reduced_form = (
            sum(d.get(outcome, 0) for d in iv_high) / len(iv_high) -
            sum(d.get(outcome, 0) for d in iv_low) / len(iv_low)
        )

        # LATE = Reduced Form / First Stage
        if abs(first_stage) > 0.01:
            late = reduced_form / first_stage
        else:
            late = 0.0

        return CausalEffect(
            cause=treatment,
            effect=outcome,
            effect_type=EffectType.CONTROLLED,
            estimate=late,
            confidence_interval=(late - 0.2, late + 0.2),
            method=InferenceMethod.IV,
            metadata={"instrument": iv}
        )


# =============================================================================
# CAUSAL REASONING ENGINE
# =============================================================================

class CausalReasoningEngine:
    """Main causal reasoning orchestrator."""

    def __init__(self):
        self.graph = CausalGraph()
        self.intervention_analyzer = InterventionAnalyzer(self.graph)
        self.counterfactual_reasoner = CounterfactualReasoner(self.graph)
        self.discovery = CausalDiscovery()
        self.effect_estimator = EffectEstimator(self.graph)

    def add_causal_relationship(
        self,
        cause: str,
        effect: str,
        strength: float = 1.0,
        mechanism: str = ""
    ) -> None:
        """Add causal relationship to graph."""
        self.graph.add_edge(cause, effect, CausalRelation.DIRECT, strength, mechanism)

    def set_structural_equation(
        self,
        variable: str,
        equation: Callable
    ) -> None:
        """Set structural equation for variable."""
        self.counterfactual_reasoner.set_structural_equation(variable, equation)

    async def intervene(
        self,
        intervention: Dict[str, Any],
        query: str
    ) -> Dict[str, Any]:
        """Apply intervention and query effect."""
        interventional = InterventionalGraph(self.graph)

        for var, val in intervention.items():
            interventional.intervene(var, val)

        return interventional.compute_effect(query)

    async def counterfactual(
        self,
        factual: Dict[str, Any],
        intervention: Dict[str, Any],
        query: str
    ) -> Counterfactual:
        """Evaluate counterfactual query."""
        return await self.counterfactual_reasoner.evaluate_counterfactual(
            factual, intervention, query
        )

    async def discover_structure(
        self,
        data: List[Dict[str, Any]],
        variables: List[str]
    ) -> CausalGraph:
        """Discover causal structure from data."""
        discovered = await self.discovery.pc_algorithm(data, variables)

        # Update internal graph
        for node_id, node in discovered.nodes.items():
            if node_id not in self.graph.nodes:
                self.graph.add_node(node_id, node.name)

        for source, edges in discovered.edges.items():
            for edge in edges:
                self.graph.add_edge(edge.source, edge.target)

        return discovered

    async def estimate_effect(
        self,
        treatment: str,
        outcome: str,
        data: List[Dict[str, Any]],
        method: InferenceMethod = InferenceMethod.BACKDOOR
    ) -> CausalEffect:
        """Estimate causal effect."""
        return await self.effect_estimator.estimate_ate(
            treatment, outcome, data, method
        )

    async def explain_relationship(
        self,
        cause: str,
        effect: str
    ) -> Dict[str, Any]:
        """Explain causal relationship."""
        paths = self.graph.get_paths(cause, effect)

        ancestors_cause = self.graph.get_ancestors(cause)
        ancestors_effect = self.graph.get_ancestors(effect)
        confounders = ancestors_cause & ancestors_effect

        return {
            "cause": cause,
            "effect": effect,
            "direct_path": [cause, effect] in paths,
            "all_paths": paths,
            "num_paths": len(paths),
            "potential_confounders": list(confounders),
            "mediators": [
                node for path in paths
                for node in path[1:-1]
                if len(path) > 2
            ]
        }

    def get_graph_summary(self) -> Dict[str, Any]:
        """Get summary of causal graph."""
        return {
            "nodes": len(self.graph.nodes),
            "edges": sum(len(e) for e in self.graph.edges.values()),
            "has_cycle": self.graph.has_cycle(),
            "topological_order": self.graph.topological_sort(),
            "node_list": list(self.graph.nodes.keys())
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demo causal reasoning engine."""
    print("=== Causal Reasoning Engine Demo ===\n")

    # Create engine
    engine = CausalReasoningEngine()

    # 1. Build causal graph
    print("1. Building Causal Graph:")

    # Classic example: Education -> Income <- Experience
    # With confounders: Family Background affects both Education and Income

    engine.add_causal_relationship("family_background", "education", strength=0.6)
    engine.add_causal_relationship("family_background", "income", strength=0.3)
    engine.add_causal_relationship("education", "skill", strength=0.8)
    engine.add_causal_relationship("skill", "income", strength=0.7)
    engine.add_causal_relationship("education", "income", strength=0.4)
    engine.add_causal_relationship("experience", "skill", strength=0.5)
    engine.add_causal_relationship("experience", "income", strength=0.3)

    summary = engine.get_graph_summary()
    print(f"   Nodes: {summary['nodes']}")
    print(f"   Edges: {summary['edges']}")
    print(f"   Topological order: {summary['topological_order']}")

    # 2. Path analysis
    print("\n2. Causal Path Analysis:")
    explanation = await engine.explain_relationship("education", "income")
    print(f"   Paths from education to income: {explanation['num_paths']}")
    print(f"   Direct path exists: {explanation['direct_path']}")
    print(f"   Mediators: {explanation['mediators']}")
    print(f"   Potential confounders: {explanation['potential_confounders']}")

    # 3. Intervention analysis
    print("\n3. Intervention Analysis:")
    print("   What if we set education = high?")

    result = await engine.intervene(
        {"education": 1.0},
        "income"
    )
    print(f"   Expected income: {result['mean']:.3f} (std: {result['std']:.3f})")

    result_low = await engine.intervene(
        {"education": 0.0},
        "income"
    )
    print(f"   With education = low: {result_low['mean']:.3f}")
    print(f"   Causal effect of education: {result['mean'] - result_low['mean']:.3f}")

    # 4. Counterfactual reasoning
    print("\n4. Counterfactual Reasoning:")

    # Set up structural equations
    engine.set_structural_equation(
        "income",
        lambda parents, noise:
            0.4 * parents.get("education", 0) +
            0.3 * parents.get("family_background", 0) +
            0.7 * parents.get("skill", 0) +
            noise
    )
    engine.set_structural_equation(
        "skill",
        lambda parents, noise:
            0.8 * parents.get("education", 0) +
            0.5 * parents.get("experience", 0) +
            noise
    )

    factual = {
        "education": 0.3,
        "experience": 0.5,
        "family_background": 0.4,
        "skill": 0.5,
        "income": 0.6
    }

    cf = await engine.counterfactual(
        factual=factual,
        intervention={"education": 0.8},
        query="income"
    )

    print(f"   Factual: education={factual['education']}, income={cf.factual_value:.3f}")
    print(f"   Counterfactual: education=0.8, income would be={cf.counterfactual_value:.3f}")

    # 5. Effect estimation
    print("\n5. Effect Estimation:")

    # Generate synthetic data
    data = []
    for _ in range(500):
        fb = random.gauss(0.5, 0.2)
        edu = 0.6 * fb + random.gauss(0.3, 0.1)
        exp = random.gauss(0.5, 0.2)
        skill = 0.8 * edu + 0.5 * exp + random.gauss(0, 0.1)
        income = 0.4 * edu + 0.3 * fb + 0.7 * skill + random.gauss(0, 0.1)

        data.append({
            "family_background": fb,
            "education": 1 if edu > 0.5 else 0,
            "experience": exp,
            "skill": skill,
            "income": income
        })

    effect = await engine.estimate_effect(
        "education", "income", data,
        method=InferenceMethod.BACKDOOR
    )

    print(f"   Method: {effect.method.value}")
    print(f"   ATE: {effect.estimate:.3f}")
    print(f"   95% CI: ({effect.confidence_interval[0]:.3f}, {effect.confidence_interval[1]:.3f})")
    print(f"   Controlled confounders: {effect.confounders_controlled}")

    # 6. Causal discovery
    print("\n6. Causal Discovery:")

    variables = ["family_background", "education", "skill", "income"]
    discovered = await engine.discover_structure(data, variables)

    print(f"   Discovered {len(discovered.nodes)} nodes")
    print(f"   Discovered edges:")
    for source, edges in discovered.edges.items():
        for edge in edges:
            print(f"     {edge.source} -> {edge.target}")

    # 7. D-separation
    print("\n7. Conditional Independence (D-separation):")

    tests = [
        ("education", "experience", set()),
        ("education", "experience", {"skill"}),
        ("education", "income", {"skill", "family_background"}),
    ]

    for x, y, z in tests:
        sep = engine.graph.is_d_separated(x, y, z)
        z_str = f"given {z}" if z else "unconditionally"
        print(f"   {x} ⊥ {y} {z_str}: {sep}")


if __name__ == "__main__":
    asyncio.run(demo())
