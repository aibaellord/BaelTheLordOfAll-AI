"""
⚡ CAUSAL REASONING ⚡
=====================
Causal inference and counterfactual reasoning.

Features:
- Causal graph representation
- Do-calculus operations
- Counterfactual queries
- Intervention simulation
- Causal discovery
"""

import math
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from collections import defaultdict, deque
import uuid


class VariableType(Enum):
    """Types of causal variables"""
    BINARY = auto()
    CONTINUOUS = auto()
    CATEGORICAL = auto()
    ORDINAL = auto()


@dataclass
class CausalVariable:
    """Variable in causal graph"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    variable_type: VariableType = VariableType.CONTINUOUS

    # Current/observed value
    value: Optional[Any] = None

    # Distribution parameters
    mean: float = 0.0
    std: float = 1.0
    categories: List[Any] = field(default_factory=list)

    # Structural equation (how it depends on parents)
    structural_equation: Optional[Callable] = None

    # Metadata
    is_observed: bool = True
    is_intervention: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def sample(self, parent_values: Dict[str, Any] = None) -> Any:
        """Sample value from distribution"""
        if self.structural_equation and parent_values:
            return self.structural_equation(parent_values)

        if self.variable_type == VariableType.BINARY:
            return np.random.binomial(1, 0.5)
        elif self.variable_type == VariableType.CONTINUOUS:
            return np.random.normal(self.mean, self.std)
        elif self.variable_type == VariableType.CATEGORICAL:
            if self.categories:
                return np.random.choice(self.categories)
            return None
        elif self.variable_type == VariableType.ORDINAL:
            if self.categories:
                return np.random.choice(self.categories)
            return np.random.randint(0, 10)

        return None


@dataclass
class CausalEdge:
    """Edge in causal graph"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_id: str = ""
    target_id: str = ""

    # Edge properties
    strength: float = 1.0
    confidence: float = 1.0
    delay: float = 0.0  # Time delay

    # Effect function
    effect_function: Optional[Callable] = None

    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InterventionResult:
    """Result of causal intervention"""
    intervention: Dict[str, Any]
    original_values: Dict[str, Any]
    intervened_values: Dict[str, Any]
    effects: Dict[str, float]  # Variable -> effect size
    confidence: float = 1.0
    timestamp: datetime = field(default_factory=datetime.now)


class CausalGraph:
    """
    Directed Acyclic Graph for causal reasoning.
    """

    def __init__(self):
        self.variables: Dict[str, CausalVariable] = {}
        self.edges: Dict[str, CausalEdge] = {}

        # Adjacency
        self.parents: Dict[str, Set[str]] = defaultdict(set)
        self.children: Dict[str, Set[str]] = defaultdict(set)

        # Topological order cache
        self._topo_order: Optional[List[str]] = None

    def add_variable(
        self,
        name: str,
        variable_type: VariableType = VariableType.CONTINUOUS,
        **kwargs
    ) -> CausalVariable:
        """Add variable to graph"""
        var = CausalVariable(
            name=name,
            variable_type=variable_type,
            **kwargs
        )
        self.variables[var.id] = var
        self._topo_order = None
        return var

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        strength: float = 1.0,
        effect_function: Callable = None
    ) -> Optional[CausalEdge]:
        """Add causal edge"""
        if source_id not in self.variables or target_id not in self.variables:
            return None

        # Check for cycles
        if self._would_create_cycle(source_id, target_id):
            return None

        edge = CausalEdge(
            source_id=source_id,
            target_id=target_id,
            strength=strength,
            effect_function=effect_function
        )

        self.edges[edge.id] = edge
        self.parents[target_id].add(source_id)
        self.children[source_id].add(target_id)

        self._topo_order = None
        return edge

    def _would_create_cycle(
        self,
        source_id: str,
        target_id: str
    ) -> bool:
        """Check if adding edge would create cycle"""
        # BFS from target to see if we can reach source
        visited = set()
        queue = [target_id]

        while queue:
            current = queue.pop(0)
            if current == source_id:
                return True

            if current in visited:
                continue
            visited.add(current)

            queue.extend(self.children.get(current, set()))

        return False

    def get_topological_order(self) -> List[str]:
        """Get topological ordering of variables"""
        if self._topo_order is not None:
            return self._topo_order

        in_degree = {vid: len(self.parents.get(vid, set())) for vid in self.variables}
        queue = deque([vid for vid, deg in in_degree.items() if deg == 0])
        order = []

        while queue:
            vid = queue.popleft()
            order.append(vid)

            for child in self.children.get(vid, set()):
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)

        self._topo_order = order
        return order

    def get_ancestors(self, variable_id: str) -> Set[str]:
        """Get all ancestors of variable"""
        ancestors = set()
        queue = list(self.parents.get(variable_id, set()))

        while queue:
            vid = queue.pop(0)
            if vid in ancestors:
                continue
            ancestors.add(vid)
            queue.extend(self.parents.get(vid, set()))

        return ancestors

    def get_descendants(self, variable_id: str) -> Set[str]:
        """Get all descendants of variable"""
        descendants = set()
        queue = list(self.children.get(variable_id, set()))

        while queue:
            vid = queue.pop(0)
            if vid in descendants:
                continue
            descendants.add(vid)
            queue.extend(self.children.get(vid, set()))

        return descendants

    def is_d_separated(
        self,
        x: str,
        y: str,
        z: Set[str]
    ) -> bool:
        """
        Check if X and Y are d-separated given Z.

        Uses Bayes-Ball algorithm.
        """
        # Ancestors of Z
        z_ancestors = set()
        for zid in z:
            z_ancestors.update(self.get_ancestors(zid))
            z_ancestors.add(zid)

        # BFS with direction tracking
        visited = set()
        queue = [(x, 'down')]  # (node, direction)

        while queue:
            current, direction = queue.pop(0)

            if (current, direction) in visited:
                continue
            visited.add((current, direction))

            if current == y:
                return False  # Path found

            if direction == 'down':
                # Coming from parent
                if current not in z:
                    # Continue down to children
                    for child in self.children.get(current, set()):
                        queue.append((child, 'down'))
                    # Continue up to parents
                    for parent in self.parents.get(current, set()):
                        queue.append((parent, 'up'))
                else:
                    # Blocked at observed node
                    pass
            else:  # direction == 'up'
                # Coming from child
                if current not in z:
                    # Continue up to parents
                    for parent in self.parents.get(current, set()):
                        queue.append((parent, 'up'))

                # Collider handling
                if current in z or current in z_ancestors:
                    # Collider is activated
                    for child in self.children.get(current, set()):
                        queue.append((child, 'down'))

        return True  # No path found


class CausalReasoner:
    """
    Causal inference engine.

    Supports:
    - Observational queries P(Y|X)
    - Interventional queries P(Y|do(X))
    - Counterfactual queries
    """

    def __init__(self, graph: CausalGraph):
        self.graph = graph

    def intervene(
        self,
        interventions: Dict[str, Any]
    ) -> InterventionResult:
        """
        Perform do-calculus intervention.

        do(X=x) operation.
        """
        # Store original values
        original = {
            vid: var.value
            for vid, var in self.graph.variables.items()
        }

        # Apply interventions
        for var_id, value in interventions.items():
            if var_id in self.graph.variables:
                var = self.graph.variables[var_id]
                var.value = value
                var.is_intervention = True

        # Propagate effects in topological order
        order = self.graph.get_topological_order()

        for var_id in order:
            var = self.graph.variables[var_id]

            # Skip intervened variables
            if var_id in interventions:
                continue

            # Get parent values
            parent_values = {}
            for parent_id in self.graph.parents.get(var_id, set()):
                parent = self.graph.variables.get(parent_id)
                if parent:
                    parent_values[parent.name] = parent.value

            # Sample new value
            var.value = var.sample(parent_values)

        # Collect intervened values
        intervened = {
            vid: var.value
            for vid, var in self.graph.variables.items()
        }

        # Calculate effects
        effects = {}
        for vid in self.graph.variables:
            if original[vid] is not None and intervened[vid] is not None:
                try:
                    effects[vid] = float(intervened[vid]) - float(original[vid])
                except (TypeError, ValueError):
                    effects[vid] = 0.0

        # Reset intervention flags
        for var in self.graph.variables.values():
            var.is_intervention = False

        return InterventionResult(
            intervention=interventions,
            original_values=original,
            intervened_values=intervened,
            effects=effects
        )

    def estimate_causal_effect(
        self,
        treatment: str,
        outcome: str,
        treatment_values: Tuple[Any, Any] = (0, 1),
        n_samples: int = 1000
    ) -> Dict[str, float]:
        """
        Estimate Average Treatment Effect (ATE).

        ATE = E[Y|do(X=1)] - E[Y|do(X=0)]
        """
        treat_0, treat_1 = treatment_values

        outcomes_0 = []
        outcomes_1 = []

        for _ in range(n_samples):
            # Intervention do(X=0)
            result_0 = self.intervene({treatment: treat_0})
            if outcome in result_0.intervened_values:
                outcomes_0.append(result_0.intervened_values[outcome])

            # Intervention do(X=1)
            result_1 = self.intervene({treatment: treat_1})
            if outcome in result_1.intervened_values:
                outcomes_1.append(result_1.intervened_values[outcome])

        # Calculate ATE
        mean_0 = np.mean(outcomes_0) if outcomes_0 else 0
        mean_1 = np.mean(outcomes_1) if outcomes_1 else 0

        ate = mean_1 - mean_0

        return {
            'ate': ate,
            'mean_treatment': mean_1,
            'mean_control': mean_0,
            'n_samples': n_samples
        }

    def identify_confounders(
        self,
        treatment: str,
        outcome: str
    ) -> Set[str]:
        """Identify confounding variables"""
        confounders = set()

        treatment_ancestors = self.graph.get_ancestors(treatment)
        outcome_ancestors = self.graph.get_ancestors(outcome)

        # Confounders are common ancestors
        common = treatment_ancestors.intersection(outcome_ancestors)

        for var_id in common:
            # Check if it's not blocked
            if not self.graph.is_d_separated(treatment, outcome, {var_id}):
                confounders.add(var_id)

        return confounders


@dataclass
class CounterfactualQuery:
    """Query for counterfactual reasoning"""
    # Observed evidence
    evidence: Dict[str, Any] = field(default_factory=dict)

    # Hypothetical intervention
    intervention: Dict[str, Any] = field(default_factory=dict)

    # Variables to query
    query_variables: List[str] = field(default_factory=list)


class CounterfactualEngine:
    """
    Counterfactual reasoning engine.

    Answers questions like:
    "What would Y have been if X had been x', given that we observed X=x?"
    """

    def __init__(self, graph: CausalGraph):
        self.graph = graph
        self.reasoner = CausalReasoner(graph)

    def evaluate(
        self,
        query: CounterfactualQuery,
        n_samples: int = 1000
    ) -> Dict[str, Any]:
        """
        Evaluate counterfactual query.

        Three-step process:
        1. Abduction: Infer latent variables from evidence
        2. Action: Intervene on specified variables
        3. Prediction: Compute counterfactual outcomes
        """
        results = {var: [] for var in query.query_variables}

        for _ in range(n_samples):
            # Step 1: Abduction - set evidence
            for var_id, value in query.evidence.items():
                if var_id in self.graph.variables:
                    self.graph.variables[var_id].value = value

            # Step 2: Action - apply intervention
            intervention_result = self.reasoner.intervene(query.intervention)

            # Step 3: Prediction - collect query variables
            for var_id in query.query_variables:
                if var_id in intervention_result.intervened_values:
                    results[var_id].append(intervention_result.intervened_values[var_id])

        # Aggregate results
        aggregated = {}
        for var_id, values in results.items():
            if values:
                try:
                    aggregated[var_id] = {
                        'mean': np.mean(values),
                        'std': np.std(values),
                        'samples': len(values)
                    }
                except:
                    aggregated[var_id] = {
                        'mode': max(set(values), key=values.count),
                        'samples': len(values)
                    }

        return aggregated

    def what_if(
        self,
        evidence: Dict[str, Any],
        intervention: Dict[str, Any],
        outcome: str
    ) -> Dict[str, float]:
        """
        Simple what-if query.

        "What if X had been x', given current evidence?"
        """
        query = CounterfactualQuery(
            evidence=evidence,
            intervention=intervention,
            query_variables=[outcome]
        )

        return self.evaluate(query)

    def but_for(
        self,
        evidence: Dict[str, Any],
        cause: str,
        effect: str,
        alternative_cause: Any
    ) -> Dict[str, Any]:
        """
        But-for causation test.

        "But for X, would Y have occurred?"
        """
        # Observed outcome
        if effect not in evidence:
            return {'error': 'Effect not in evidence'}

        observed_effect = evidence[effect]

        # Counterfactual
        cf_result = self.what_if(
            evidence=evidence,
            intervention={cause: alternative_cause},
            outcome=effect
        )

        if effect not in cf_result:
            return {'error': 'Could not compute counterfactual'}

        cf_effect = cf_result[effect]

        # Compare
        return {
            'observed': observed_effect,
            'counterfactual': cf_effect,
            'but_for_caused': observed_effect != cf_effect.get('mean', cf_effect)
        }


# Export all
__all__ = [
    'VariableType',
    'CausalVariable',
    'CausalEdge',
    'CausalGraph',
    'InterventionResult',
    'CausalReasoner',
    'CounterfactualQuery',
    'CounterfactualEngine',
]
