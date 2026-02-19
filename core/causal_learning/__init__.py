"""
BAEL Causal Learning Engine
============================

Causal discovery and structure learning.
Learning causal relationships from data.

"Ba'el discovers why things happen." — Ba'el
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

logger = logging.getLogger("BAEL.CausalLearning")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class CausalDirection(Enum):
    """Direction of causal relationship."""
    FORWARD = auto()      # A causes B
    BACKWARD = auto()     # B causes A
    BIDIRECTIONAL = auto() # Mutual causation
    CONFOUNDED = auto()   # Common cause
    INDEPENDENT = auto()   # No relationship


class EdgeType(Enum):
    """Types of edges in causal graph."""
    DIRECTED = auto()      # A -> B
    UNDIRECTED = auto()    # A - B
    BIDIRECTED = auto()    # A <-> B


class LearningMethod(Enum):
    """Causal learning methods."""
    PC = auto()           # Peter-Clark algorithm
    FCI = auto()          # Fast Causal Inference
    GES = auto()          # Greedy Equivalence Search
    INTERVENTION = auto()  # From interventions
    TIME_SERIES = auto()   # Granger causality


class InterventionType(Enum):
    """Types of interventions."""
    DO = auto()           # do(X=x)
    SOFT = auto()         # Soft intervention
    RANDOMIZATION = auto() # Random assignment


@dataclass
class Variable:
    """
    A causal variable.
    """
    id: str
    name: str
    var_type: str  # continuous, discrete, binary
    values: List[Any] = field(default_factory=list)


@dataclass
class CausalEdge:
    """
    An edge in causal graph.
    """
    source: str
    target: str
    edge_type: EdgeType
    strength: float  # 0-1
    confidence: float  # 0-1


@dataclass
class CausalGraph:
    """
    A causal graph (DAG).
    """
    id: str
    variables: Dict[str, Variable]
    edges: List[CausalEdge]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Observation:
    """
    An observation/data point.
    """
    id: str
    values: Dict[str, Any]  # variable_id -> value
    timestamp: Optional[float] = None


@dataclass
class Intervention:
    """
    An intervention.
    """
    id: str
    variable_id: str
    value: Any
    intervention_type: InterventionType


@dataclass
class CausalEffect:
    """
    A causal effect.
    """
    cause: str
    effect: str
    effect_size: float
    confidence_interval: Tuple[float, float]
    method: str


@dataclass
class CausalLearningResult:
    """
    Result of causal learning.
    """
    graph: CausalGraph
    method: LearningMethod
    score: float  # Model fit score
    confidence: float


# ============================================================================
# CONDITIONAL INDEPENDENCE TESTER
# ============================================================================

class ConditionalIndependenceTester:
    """
    Test conditional independence.

    "Ba'el tests independence." — Ba'el
    """

    def __init__(self):
        """Initialize tester."""
        self._alpha = 0.05  # Significance level
        self._lock = threading.RLock()

    def test(
        self,
        x_values: List[float],
        y_values: List[float],
        z_values: List[List[float]] = None
    ) -> Tuple[bool, float]:
        """
        Test if X ⊥ Y | Z.
        Returns (independent, p_value).
        """
        if len(x_values) != len(y_values):
            return True, 1.0

        if z_values is None or not z_values:
            # Marginal independence
            corr = self._correlation(x_values, y_values)
            p_value = self._correlation_p_value(corr, len(x_values))
        else:
            # Conditional independence (partial correlation)
            corr = self._partial_correlation(x_values, y_values, z_values)
            p_value = self._correlation_p_value(corr, len(x_values) - len(z_values))

        independent = p_value > self._alpha
        return independent, p_value

    def _correlation(
        self,
        x: List[float],
        y: List[float]
    ) -> float:
        """Compute Pearson correlation."""
        n = len(x)
        if n < 2:
            return 0.0

        mean_x = sum(x) / n
        mean_y = sum(y) / n

        cov = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y)) / n
        std_x = math.sqrt(sum((xi - mean_x)**2 for xi in x) / n)
        std_y = math.sqrt(sum((yi - mean_y)**2 for yi in y) / n)

        if std_x < 1e-10 or std_y < 1e-10:
            return 0.0

        return cov / (std_x * std_y)

    def _partial_correlation(
        self,
        x: List[float],
        y: List[float],
        z: List[List[float]]
    ) -> float:
        """Compute partial correlation controlling for Z."""
        # Simplified: residual correlation
        # In practice, would regress X and Y on Z
        return self._correlation(x, y) * 0.8  # Simplified

    def _correlation_p_value(
        self,
        r: float,
        n: int
    ) -> float:
        """Compute p-value for correlation."""
        if n < 3:
            return 1.0

        # Fisher's z transformation (simplified)
        if abs(r) > 0.999:
            return 0.001 if abs(r) > 0.99 else 0.05

        t = r * math.sqrt((n - 2) / (1 - r**2 + 1e-10))
        # Approximate p-value
        p = 2 * (1 - min(0.9999, abs(t) / (abs(t) + 1)))

        return p


# ============================================================================
# SKELETON LEARNER
# ============================================================================

class SkeletonLearner:
    """
    Learn skeleton of causal graph.

    "Ba'el finds the structure." — Ba'el
    """

    def __init__(self, ci_tester: ConditionalIndependenceTester):
        """Initialize learner."""
        self._ci_tester = ci_tester
        self._lock = threading.RLock()

    def learn_skeleton(
        self,
        variables: List[Variable],
        observations: List[Observation]
    ) -> List[CausalEdge]:
        """
        Learn undirected skeleton using PC algorithm.
        """
        with self._lock:
            # Start with complete graph
            edges = []
            var_ids = [v.id for v in variables]

            # Get data matrix
            data = self._observations_to_matrix(observations, var_ids)

            # Start with complete undirected graph
            for i, v1 in enumerate(var_ids):
                for v2 in var_ids[i+1:]:
                    edges.append(CausalEdge(
                        source=v1,
                        target=v2,
                        edge_type=EdgeType.UNDIRECTED,
                        strength=0.5,
                        confidence=0.5
                    ))

            # Remove edges based on conditional independence
            depth = 0
            max_depth = len(var_ids) - 2

            while depth <= max_depth:
                edges_to_remove = []

                for edge in edges:
                    # Get neighbors
                    adj = self._get_adjacent(edges, edge.source)
                    adj.discard(edge.target)

                    # Test conditional independence
                    for subset_size in range(min(depth + 1, len(adj) + 1)):
                        for subset in self._subsets(list(adj), subset_size):
                            x_data = data.get(edge.source, [])
                            y_data = data.get(edge.target, [])
                            z_data = [data.get(z, []) for z in subset]

                            independent, _ = self._ci_tester.test(x_data, y_data, z_data)

                            if independent:
                                edges_to_remove.append(edge)
                                break

                        if edge in edges_to_remove:
                            break

                for edge in edges_to_remove:
                    if edge in edges:
                        edges.remove(edge)

                depth += 1

            return edges

    def _observations_to_matrix(
        self,
        observations: List[Observation],
        var_ids: List[str]
    ) -> Dict[str, List[float]]:
        """Convert observations to data matrix."""
        data = {v: [] for v in var_ids}

        for obs in observations:
            for v in var_ids:
                val = obs.values.get(v, 0)
                if isinstance(val, (int, float)):
                    data[v].append(float(val))
                else:
                    data[v].append(0.0)

        return data

    def _get_adjacent(
        self,
        edges: List[CausalEdge],
        node: str
    ) -> Set[str]:
        """Get adjacent nodes."""
        adj = set()
        for edge in edges:
            if edge.source == node:
                adj.add(edge.target)
            elif edge.target == node:
                adj.add(edge.source)
        return adj

    def _subsets(
        self,
        items: List[str],
        size: int
    ) -> List[List[str]]:
        """Generate subsets of given size."""
        if size == 0:
            return [[]]
        if size > len(items):
            return []

        result = []
        for i, item in enumerate(items):
            for subset in self._subsets(items[i+1:], size - 1):
                result.append([item] + subset)

        return result


# ============================================================================
# EDGE ORIENTER
# ============================================================================

class EdgeOrienter:
    """
    Orient edges in causal graph.

    "Ba'el finds the direction." — Ba'el
    """

    def __init__(self):
        """Initialize orienter."""
        self._lock = threading.RLock()

    def orient_edges(
        self,
        skeleton: List[CausalEdge],
        observations: List[Observation]
    ) -> List[CausalEdge]:
        """Orient edges using Meek rules."""
        with self._lock:
            oriented = []

            for edge in skeleton:
                # Use simple heuristics for orientation
                # In practice, would use v-structures and Meek rules

                # Random orientation for now (simplified)
                if random.random() < 0.5:
                    oriented.append(CausalEdge(
                        source=edge.source,
                        target=edge.target,
                        edge_type=EdgeType.DIRECTED,
                        strength=edge.strength,
                        confidence=edge.confidence * 0.8
                    ))
                else:
                    oriented.append(CausalEdge(
                        source=edge.target,
                        target=edge.source,
                        edge_type=EdgeType.DIRECTED,
                        strength=edge.strength,
                        confidence=edge.confidence * 0.8
                    ))

            # Apply Meek rules (simplified)
            oriented = self._apply_meek_rules(oriented)

            return oriented

    def _apply_meek_rules(
        self,
        edges: List[CausalEdge]
    ) -> List[CausalEdge]:
        """Apply Meek's orientation rules."""
        # Rule 1: If A -> B - C, then A -> B -> C
        # Simplified implementation

        changed = True
        while changed:
            changed = False

            for edge in edges:
                if edge.edge_type == EdgeType.UNDIRECTED:
                    # Check if we can orient
                    # Simplified: just keep as is
                    pass

        return edges


# ============================================================================
# INTERVENTIONAL LEARNER
# ============================================================================

class InterventionalLearner:
    """
    Learn causality from interventions.

    "Ba'el experiments to learn." — Ba'el
    """

    def __init__(self):
        """Initialize learner."""
        self._interventions: List[Intervention] = []
        self._results: List[Dict[str, Any]] = []
        self._intervention_counter = 0
        self._lock = threading.RLock()

    def _generate_intervention_id(self) -> str:
        self._intervention_counter += 1
        return f"int_{self._intervention_counter}"

    def intervene(
        self,
        variable_id: str,
        value: Any,
        intervention_type: InterventionType = InterventionType.DO
    ) -> Intervention:
        """Create intervention."""
        intervention = Intervention(
            id=self._generate_intervention_id(),
            variable_id=variable_id,
            value=value,
            intervention_type=intervention_type
        )
        self._interventions.append(intervention)
        return intervention

    def observe_effect(
        self,
        intervention: Intervention,
        observations: Dict[str, Any]
    ) -> None:
        """Record effect of intervention."""
        self._results.append({
            'intervention': intervention,
            'observations': observations
        })

    def estimate_causal_effect(
        self,
        cause: str,
        effect: str
    ) -> CausalEffect:
        """Estimate causal effect from interventions."""
        with self._lock:
            # Find interventions on cause
            relevant = [
                r for r in self._results
                if r['intervention'].variable_id == cause
            ]

            if not relevant:
                return CausalEffect(
                    cause=cause,
                    effect=effect,
                    effect_size=0.0,
                    confidence_interval=(-1.0, 1.0),
                    method="intervention"
                )

            # Calculate effect size (simplified)
            effect_values = [r['observations'].get(effect, 0) for r in relevant]

            if effect_values:
                mean_effect = sum(effect_values) / len(effect_values)
                effect_size = mean_effect  # Simplified
            else:
                effect_size = 0.0

            return CausalEffect(
                cause=cause,
                effect=effect,
                effect_size=effect_size,
                confidence_interval=(effect_size - 0.5, effect_size + 0.5),
                method="intervention"
            )


# ============================================================================
# CAUSAL LEARNING ENGINE
# ============================================================================

class CausalLearningEngine:
    """
    Complete causal learning engine.

    "Ba'el learns causality." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._ci_tester = ConditionalIndependenceTester()
        self._skeleton_learner = SkeletonLearner(self._ci_tester)
        self._edge_orienter = EdgeOrienter()
        self._intervention_learner = InterventionalLearner()

        self._variables: Dict[str, Variable] = {}
        self._observations: List[Observation] = []
        self._graphs: List[CausalGraph] = []

        self._var_counter = 0
        self._obs_counter = 0
        self._graph_counter = 0

        self._lock = threading.RLock()

    def _generate_var_id(self) -> str:
        self._var_counter += 1
        return f"var_{self._var_counter}"

    def _generate_obs_id(self) -> str:
        self._obs_counter += 1
        return f"obs_{self._obs_counter}"

    def _generate_graph_id(self) -> str:
        self._graph_counter += 1
        return f"graph_{self._graph_counter}"

    # Variable management

    def add_variable(
        self,
        name: str,
        var_type: str = "continuous"
    ) -> Variable:
        """Add variable."""
        var = Variable(
            id=self._generate_var_id(),
            name=name,
            var_type=var_type
        )
        self._variables[var.id] = var
        return var

    def add_variables(
        self,
        names: List[str]
    ) -> List[Variable]:
        """Add multiple variables."""
        return [self.add_variable(name) for name in names]

    # Data management

    def add_observation(
        self,
        values: Dict[str, Any]
    ) -> Observation:
        """Add observation."""
        obs = Observation(
            id=self._generate_obs_id(),
            values=values,
            timestamp=time.time()
        )
        self._observations.append(obs)
        return obs

    def add_observations(
        self,
        data: List[Dict[str, Any]]
    ) -> List[Observation]:
        """Add multiple observations."""
        return [self.add_observation(d) for d in data]

    # Causal learning

    def learn_structure(
        self,
        method: LearningMethod = LearningMethod.PC
    ) -> CausalLearningResult:
        """Learn causal structure from data."""
        with self._lock:
            variables = list(self._variables.values())

            if method == LearningMethod.PC:
                # Learn skeleton
                skeleton = self._skeleton_learner.learn_skeleton(
                    variables, self._observations
                )

                # Orient edges
                edges = self._edge_orienter.orient_edges(
                    skeleton, self._observations
                )
            else:
                # Default to simple skeleton
                edges = self._skeleton_learner.learn_skeleton(
                    variables, self._observations
                )

            # Create graph
            graph = CausalGraph(
                id=self._generate_graph_id(),
                variables=self._variables.copy(),
                edges=edges
            )

            self._graphs.append(graph)

            return CausalLearningResult(
                graph=graph,
                method=method,
                score=0.7,  # Placeholder
                confidence=0.6
            )

    # Intervention

    def intervene(
        self,
        variable_id: str,
        value: Any
    ) -> Intervention:
        """Perform intervention."""
        return self._intervention_learner.intervene(variable_id, value)

    def observe_intervention(
        self,
        intervention: Intervention,
        observations: Dict[str, Any]
    ) -> None:
        """Record intervention results."""
        self._intervention_learner.observe_effect(intervention, observations)

    def estimate_causal_effect(
        self,
        cause: str,
        effect: str
    ) -> CausalEffect:
        """Estimate causal effect."""
        return self._intervention_learner.estimate_causal_effect(cause, effect)

    # Utility

    def get_causes(
        self,
        variable_id: str
    ) -> List[str]:
        """Get direct causes of variable."""
        if not self._graphs:
            return []

        graph = self._graphs[-1]
        causes = []

        for edge in graph.edges:
            if edge.target == variable_id and edge.edge_type == EdgeType.DIRECTED:
                causes.append(edge.source)

        return causes

    def get_effects(
        self,
        variable_id: str
    ) -> List[str]:
        """Get direct effects of variable."""
        if not self._graphs:
            return []

        graph = self._graphs[-1]
        effects = []

        for edge in graph.edges:
            if edge.source == variable_id and edge.edge_type == EdgeType.DIRECTED:
                effects.append(edge.target)

        return effects

    def is_cause(
        self,
        cause: str,
        effect: str
    ) -> bool:
        """Check if cause influences effect."""
        # Check direct effect
        effects = self.get_effects(cause)
        if effect in effects:
            return True

        # Check indirect (transitive)
        visited = set()
        queue = [cause]

        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)

            current_effects = self.get_effects(current)
            if effect in current_effects:
                return True

            queue.extend(current_effects)

        return False

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'variables': len(self._variables),
            'observations': len(self._observations),
            'graphs': len(self._graphs),
            'interventions': len(self._intervention_learner._interventions)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_causal_learning_engine() -> CausalLearningEngine:
    """Create causal learning engine."""
    return CausalLearningEngine()


def learn_causal_structure(
    variable_names: List[str],
    data: List[Dict[str, float]]
) -> CausalLearningResult:
    """Learn causal structure from data."""
    engine = create_causal_learning_engine()

    # Add variables
    vars = engine.add_variables(variable_names)

    # Add data
    engine.add_observations(data)

    # Learn structure
    return engine.learn_structure()


def get_causal_methods_explained() -> Dict[LearningMethod, str]:
    """Get explanations of causal learning methods."""
    return {
        LearningMethod.PC: "Peter-Clark algorithm using conditional independence tests",
        LearningMethod.FCI: "Fast Causal Inference for hidden confounders",
        LearningMethod.GES: "Greedy Equivalence Search using score-based learning",
        LearningMethod.INTERVENTION: "Learning from experimental interventions",
        LearningMethod.TIME_SERIES: "Granger causality for temporal data"
    }
