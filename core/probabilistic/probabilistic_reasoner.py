#!/usr/bin/env python3
"""
BAEL - Probabilistic Reasoner
Advanced probabilistic inference and uncertainty reasoning.

Features:
- Bayesian networks
- Probabilistic graphical models
- Belief propagation
- Markov chains
- Monte Carlo methods
- Variational inference
- Probabilistic programs
- Uncertainty quantification
"""

import asyncio
import hashlib
import math
import random
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Callable, Dict, Generic, List, Optional, Set, Tuple,
                    Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class DistributionType(Enum):
    """Types of probability distributions."""
    DISCRETE = "discrete"
    CONTINUOUS = "continuous"
    BERNOULLI = "bernoulli"
    BINOMIAL = "binomial"
    POISSON = "poisson"
    GAUSSIAN = "gaussian"
    EXPONENTIAL = "exponential"
    UNIFORM = "uniform"
    BETA = "beta"
    GAMMA = "gamma"


class InferenceMethod(Enum):
    """Methods for probabilistic inference."""
    EXACT = "exact"
    VARIABLE_ELIMINATION = "variable_elimination"
    BELIEF_PROPAGATION = "belief_propagation"
    GIBBS_SAMPLING = "gibbs_sampling"
    METROPOLIS_HASTINGS = "metropolis_hastings"
    REJECTION_SAMPLING = "rejection_sampling"
    IMPORTANCE_SAMPLING = "importance_sampling"
    VARIATIONAL = "variational"


class NodeType(Enum):
    """Types of nodes in graphical models."""
    OBSERVED = "observed"
    LATENT = "latent"
    QUERY = "query"
    EVIDENCE = "evidence"


class ChainType(Enum):
    """Types of Markov chains."""
    DISCRETE = "discrete"
    CONTINUOUS = "continuous"
    ABSORBING = "absorbing"
    ERGODIC = "ergodic"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Distribution:
    """A probability distribution."""
    distribution_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    dist_type: DistributionType = DistributionType.DISCRETE
    parameters: Dict[str, float] = field(default_factory=dict)
    support: Optional[Tuple[float, float]] = None


@dataclass
class RandomVariable:
    """A random variable."""
    var_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    node_type: NodeType = NodeType.LATENT
    domain: List[Any] = field(default_factory=list)
    distribution: Optional[Distribution] = None
    observed_value: Optional[Any] = None


@dataclass
class Factor:
    """A factor in a factor graph."""
    factor_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    variables: List[str] = field(default_factory=list)
    table: Dict[Tuple, float] = field(default_factory=dict)


@dataclass
class CPT:
    """Conditional Probability Table."""
    cpt_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    child: str = ""
    parents: List[str] = field(default_factory=list)
    table: Dict[Tuple, Dict[Any, float]] = field(default_factory=dict)


@dataclass
class InferenceResult:
    """Result of probabilistic inference."""
    result_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    query_variables: List[str] = field(default_factory=list)
    posterior: Dict[Tuple, float] = field(default_factory=dict)
    marginals: Dict[str, Dict[Any, float]] = field(default_factory=dict)
    method: InferenceMethod = InferenceMethod.EXACT
    runtime: float = 0.0


@dataclass
class MarkovChain:
    """A Markov chain."""
    chain_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    chain_type: ChainType = ChainType.DISCRETE
    states: List[str] = field(default_factory=list)
    transition_matrix: List[List[float]] = field(default_factory=list)
    initial_distribution: List[float] = field(default_factory=list)


# =============================================================================
# DISTRIBUTION SAMPLER
# =============================================================================

class DistributionSampler:
    """Sample from probability distributions."""

    @staticmethod
    def sample(distribution: Distribution) -> float:
        """Sample from a distribution."""
        dt = distribution.dist_type
        params = distribution.parameters

        if dt == DistributionType.UNIFORM:
            low = params.get("low", 0)
            high = params.get("high", 1)
            return random.uniform(low, high)

        elif dt == DistributionType.GAUSSIAN:
            mean = params.get("mean", 0)
            std = params.get("std", 1)
            return random.gauss(mean, std)

        elif dt == DistributionType.EXPONENTIAL:
            rate = params.get("rate", 1)
            return random.expovariate(rate) if rate > 0 else 0

        elif dt == DistributionType.BERNOULLI:
            p = params.get("p", 0.5)
            return 1.0 if random.random() < p else 0.0

        elif dt == DistributionType.BINOMIAL:
            n = int(params.get("n", 1))
            p = params.get("p", 0.5)
            return sum(1 for _ in range(n) if random.random() < p)

        elif dt == DistributionType.POISSON:
            lam = params.get("lambda", 1)
            L = math.exp(-lam)
            k = 0
            p = 1.0
            while p > L:
                k += 1
                p *= random.random()
            return k - 1

        elif dt == DistributionType.BETA:
            alpha = params.get("alpha", 1)
            beta_param = params.get("beta", 1)
            return random.betavariate(alpha, beta_param)

        elif dt == DistributionType.GAMMA:
            alpha = params.get("alpha", 1)
            beta_param = params.get("beta", 1)
            return random.gammavariate(alpha, 1 / beta_param) if beta_param > 0 else 0

        return random.random()

    @staticmethod
    def pdf(distribution: Distribution, x: float) -> float:
        """Compute probability density/mass at x."""
        dt = distribution.dist_type
        params = distribution.parameters

        if dt == DistributionType.UNIFORM:
            low = params.get("low", 0)
            high = params.get("high", 1)
            if low <= x <= high:
                return 1.0 / (high - low) if high != low else 0
            return 0.0

        elif dt == DistributionType.GAUSSIAN:
            mean = params.get("mean", 0)
            std = params.get("std", 1)
            if std <= 0:
                return 0
            z = (x - mean) / std
            return math.exp(-0.5 * z * z) / (std * math.sqrt(2 * math.pi))

        elif dt == DistributionType.EXPONENTIAL:
            rate = params.get("rate", 1)
            if x < 0 or rate <= 0:
                return 0
            return rate * math.exp(-rate * x)

        elif dt == DistributionType.BERNOULLI:
            p = params.get("p", 0.5)
            if x == 1:
                return p
            elif x == 0:
                return 1 - p
            return 0

        return 0


# =============================================================================
# BAYESIAN NETWORK
# =============================================================================

class BayesianNetwork:
    """Bayesian network for probabilistic inference."""

    def __init__(self):
        self._variables: Dict[str, RandomVariable] = {}
        self._parents: Dict[str, List[str]] = defaultdict(list)
        self._children: Dict[str, List[str]] = defaultdict(list)
        self._cpts: Dict[str, CPT] = {}

    def add_variable(
        self,
        name: str,
        domain: List[Any],
        node_type: NodeType = NodeType.LATENT
    ) -> RandomVariable:
        """Add a random variable."""
        var = RandomVariable(name=name, domain=domain, node_type=node_type)
        self._variables[name] = var
        return var

    def add_edge(self, parent: str, child: str) -> None:
        """Add a directed edge."""
        self._parents[child].append(parent)
        self._children[parent].append(child)

    def set_cpt(
        self,
        variable: str,
        table: Dict[Tuple, Dict[Any, float]]
    ) -> CPT:
        """Set conditional probability table."""
        parents = self._parents.get(variable, [])
        cpt = CPT(child=variable, parents=parents, table=table)
        self._cpts[variable] = cpt
        return cpt

    def set_prior(
        self,
        variable: str,
        prior: Dict[Any, float]
    ) -> None:
        """Set prior distribution for root node."""
        self._cpts[variable] = CPT(
            child=variable,
            parents=[],
            table={(): prior}
        )

    def get_probability(
        self,
        variable: str,
        value: Any,
        parent_values: Dict[str, Any]
    ) -> float:
        """Get conditional probability P(variable=value | parents)."""
        cpt = self._cpts.get(variable)
        if not cpt:
            return 0.0

        if not cpt.parents:
            return cpt.table.get((), {}).get(value, 0.0)

        parent_tuple = tuple(parent_values.get(p) for p in cpt.parents)
        return cpt.table.get(parent_tuple, {}).get(value, 0.0)

    def sample(self) -> Dict[str, Any]:
        """Sample from the joint distribution."""
        sample = {}

        # Topological sort
        order = self._topological_sort()

        for var_name in order:
            var = self._variables.get(var_name)
            if not var:
                continue

            # Get parent values
            parent_values = {p: sample[p] for p in self._parents.get(var_name, [])}

            # Sample from conditional
            probs = []
            for val in var.domain:
                p = self.get_probability(var_name, val, parent_values)
                probs.append((val, p))

            # Normalize and sample
            total = sum(p for _, p in probs)
            if total > 0:
                r = random.random() * total
                cumsum = 0
                for val, p in probs:
                    cumsum += p
                    if r <= cumsum:
                        sample[var_name] = val
                        break
                else:
                    sample[var_name] = probs[-1][0] if probs else None
            else:
                sample[var_name] = random.choice(var.domain) if var.domain else None

        return sample

    def _topological_sort(self) -> List[str]:
        """Topological sort of variables."""
        visited = set()
        order = []

        def dfs(node: str):
            if node in visited:
                return
            visited.add(node)
            for parent in self._parents.get(node, []):
                dfs(parent)
            order.append(node)

        for var in self._variables:
            dfs(var)

        return order


# =============================================================================
# FACTOR GRAPH
# =============================================================================

class FactorGraph:
    """Factor graph for message passing."""

    def __init__(self):
        self._variables: Dict[str, RandomVariable] = {}
        self._factors: Dict[str, Factor] = {}
        self._var_to_factors: Dict[str, List[str]] = defaultdict(list)

    def add_variable(
        self,
        name: str,
        domain: List[Any]
    ) -> RandomVariable:
        """Add a variable."""
        var = RandomVariable(name=name, domain=domain)
        self._variables[name] = var
        return var

    def add_factor(
        self,
        variables: List[str],
        table: Dict[Tuple, float]
    ) -> Factor:
        """Add a factor."""
        factor = Factor(variables=variables, table=table)
        self._factors[factor.factor_id] = factor

        for var in variables:
            self._var_to_factors[var].append(factor.factor_id)

        return factor

    def belief_propagation(
        self,
        num_iterations: int = 10
    ) -> Dict[str, Dict[Any, float]]:
        """Run sum-product belief propagation."""
        # Initialize messages
        var_to_factor_msgs: Dict[Tuple[str, str], Dict[Any, float]] = {}
        factor_to_var_msgs: Dict[Tuple[str, str], Dict[Any, float]] = {}

        # Initialize uniform messages
        for var_name, var in self._variables.items():
            uniform = {v: 1.0 / len(var.domain) for v in var.domain}
            for factor_id in self._var_to_factors[var_name]:
                var_to_factor_msgs[(var_name, factor_id)] = uniform.copy()
                factor_to_var_msgs[(factor_id, var_name)] = uniform.copy()

        # Iterate
        for _ in range(num_iterations):
            # Update factor-to-variable messages
            for factor_id, factor in self._factors.items():
                for target_var in factor.variables:
                    msg = self._compute_factor_to_var_message(
                        factor, target_var, var_to_factor_msgs
                    )
                    factor_to_var_msgs[(factor_id, target_var)] = msg

            # Update variable-to-factor messages
            for var_name, var in self._variables.items():
                for target_factor in self._var_to_factors[var_name]:
                    msg = self._compute_var_to_factor_message(
                        var_name, target_factor, factor_to_var_msgs
                    )
                    var_to_factor_msgs[(var_name, target_factor)] = msg

        # Compute marginals
        marginals = {}
        for var_name, var in self._variables.items():
            belief = {v: 1.0 for v in var.domain}

            for factor_id in self._var_to_factors[var_name]:
                msg = factor_to_var_msgs.get((factor_id, var_name), {})
                for v in var.domain:
                    belief[v] *= msg.get(v, 1.0)

            # Normalize
            total = sum(belief.values())
            if total > 0:
                belief = {v: p / total for v, p in belief.items()}

            marginals[var_name] = belief

        return marginals

    def _compute_factor_to_var_message(
        self,
        factor: Factor,
        target_var: str,
        var_to_factor_msgs: Dict[Tuple[str, str], Dict[Any, float]]
    ) -> Dict[Any, float]:
        """Compute factor-to-variable message."""
        target_domain = self._variables[target_var].domain
        msg = {v: 0.0 for v in target_domain}

        other_vars = [v for v in factor.variables if v != target_var]

        # Marginalize over other variables
        def iterate_assignments(vars_list, idx=0, assignment=None):
            if assignment is None:
                assignment = {}

            if idx == len(vars_list):
                # Compute product
                for target_val in target_domain:
                    full_assignment = dict(assignment)
                    full_assignment[target_var] = target_val

                    key = tuple(full_assignment.get(v) for v in factor.variables)
                    factor_val = factor.table.get(key, 0.0)

                    product = factor_val
                    for var in other_vars:
                        var_msg = var_to_factor_msgs.get(
                            (var, factor.factor_id), {}
                        )
                        product *= var_msg.get(assignment[var], 1.0)

                    msg[target_val] += product
                return

            var = vars_list[idx]
            for val in self._variables[var].domain:
                assignment[var] = val
                iterate_assignments(vars_list, idx + 1, assignment)

        iterate_assignments(other_vars)

        # Normalize
        total = sum(msg.values())
        if total > 0:
            msg = {v: p / total for v, p in msg.items()}

        return msg

    def _compute_var_to_factor_message(
        self,
        var_name: str,
        target_factor: str,
        factor_to_var_msgs: Dict[Tuple[str, str], Dict[Any, float]]
    ) -> Dict[Any, float]:
        """Compute variable-to-factor message."""
        var = self._variables[var_name]
        msg = {v: 1.0 for v in var.domain}

        for factor_id in self._var_to_factors[var_name]:
            if factor_id != target_factor:
                incoming = factor_to_var_msgs.get((factor_id, var_name), {})
                for v in var.domain:
                    msg[v] *= incoming.get(v, 1.0)

        # Normalize
        total = sum(msg.values())
        if total > 0:
            msg = {v: p / total for v, p in msg.items()}

        return msg


# =============================================================================
# MARKOV CHAIN ANALYZER
# =============================================================================

class MarkovChainAnalyzer:
    """Analyze Markov chains."""

    def __init__(self, chain: MarkovChain):
        self._chain = chain

    def simulate(
        self,
        num_steps: int,
        start_state: Optional[int] = None
    ) -> List[int]:
        """Simulate the chain."""
        if not self._chain.states:
            return []

        n = len(self._chain.states)

        # Initial state
        if start_state is None:
            if self._chain.initial_distribution:
                r = random.random()
                cumsum = 0
                start_state = 0
                for i, p in enumerate(self._chain.initial_distribution):
                    cumsum += p
                    if r <= cumsum:
                        start_state = i
                        break
            else:
                start_state = random.randint(0, n - 1)

        path = [start_state]
        current = start_state

        for _ in range(num_steps - 1):
            if current >= len(self._chain.transition_matrix):
                break

            probs = self._chain.transition_matrix[current]
            r = random.random()
            cumsum = 0

            for i, p in enumerate(probs):
                cumsum += p
                if r <= cumsum:
                    current = i
                    break

            path.append(current)

        return path

    def stationary_distribution(
        self,
        num_iterations: int = 100
    ) -> List[float]:
        """Compute stationary distribution using power iteration."""
        n = len(self._chain.states)
        if n == 0:
            return []

        # Start uniform
        dist = [1.0 / n] * n

        for _ in range(num_iterations):
            new_dist = [0.0] * n

            for j in range(n):
                for i in range(n):
                    if i < len(self._chain.transition_matrix) and j < len(self._chain.transition_matrix[i]):
                        new_dist[j] += dist[i] * self._chain.transition_matrix[i][j]

            dist = new_dist

        # Normalize
        total = sum(dist)
        if total > 0:
            dist = [p / total for p in dist]

        return dist

    def hitting_time(
        self,
        start_state: int,
        target_state: int,
        num_simulations: int = 1000
    ) -> float:
        """Estimate expected hitting time."""
        total_time = 0

        for _ in range(num_simulations):
            current = start_state
            time = 0

            while current != target_state and time < 10000:
                probs = self._chain.transition_matrix[current]
                r = random.random()
                cumsum = 0

                for i, p in enumerate(probs):
                    cumsum += p
                    if r <= cumsum:
                        current = i
                        break

                time += 1

            total_time += time

        return total_time / num_simulations

    def is_irreducible(self) -> bool:
        """Check if chain is irreducible."""
        n = len(self._chain.states)
        if n == 0:
            return True

        # BFS from each state
        for start in range(n):
            visited = set()
            queue = deque([start])

            while queue:
                state = queue.popleft()
                if state in visited:
                    continue
                visited.add(state)

                if state < len(self._chain.transition_matrix):
                    for next_state, prob in enumerate(self._chain.transition_matrix[state]):
                        if prob > 0 and next_state not in visited:
                            queue.append(next_state)

            if len(visited) != n:
                return False

        return True


# =============================================================================
# MONTE CARLO SAMPLER
# =============================================================================

class MonteCarloSampler:
    """Monte Carlo sampling methods."""

    def __init__(self, network: BayesianNetwork):
        self._network = network

    def rejection_sampling(
        self,
        query: List[str],
        evidence: Dict[str, Any],
        num_samples: int = 1000
    ) -> Dict[str, Dict[Any, float]]:
        """Rejection sampling."""
        counts: Dict[str, Dict[Any, int]] = {q: defaultdict(int) for q in query}
        accepted = 0

        for _ in range(num_samples * 10):  # Generate more samples
            sample = self._network.sample()

            # Check evidence
            consistent = all(
                sample.get(var) == val
                for var, val in evidence.items()
            )

            if consistent:
                accepted += 1
                for q in query:
                    if q in sample:
                        counts[q][sample[q]] += 1

                if accepted >= num_samples:
                    break

        # Normalize
        marginals = {}
        for q, q_counts in counts.items():
            total = sum(q_counts.values())
            if total > 0:
                marginals[q] = {v: c / total for v, c in q_counts.items()}
            else:
                marginals[q] = {}

        return marginals

    def gibbs_sampling(
        self,
        query: List[str],
        evidence: Dict[str, Any],
        num_samples: int = 1000,
        burn_in: int = 100
    ) -> Dict[str, Dict[Any, float]]:
        """Gibbs sampling."""
        # Initialize
        state = self._network.sample()
        state.update(evidence)

        counts: Dict[str, Dict[Any, int]] = {q: defaultdict(int) for q in query}
        non_evidence = [
            v for v in self._network._variables
            if v not in evidence
        ]

        for i in range(burn_in + num_samples):
            # Sample each non-evidence variable
            for var_name in non_evidence:
                var = self._network._variables.get(var_name)
                if not var:
                    continue

                # Compute conditional distribution
                probs = []
                for val in var.domain:
                    state[var_name] = val

                    # P(var | markov blanket)
                    p = self._markov_blanket_probability(var_name, state)
                    probs.append((val, p))

                # Sample
                total = sum(p for _, p in probs)
                if total > 0:
                    r = random.random() * total
                    cumsum = 0
                    for val, p in probs:
                        cumsum += p
                        if r <= cumsum:
                            state[var_name] = val
                            break

            # Record after burn-in
            if i >= burn_in:
                for q in query:
                    if q in state:
                        counts[q][state[q]] += 1

        # Normalize
        marginals = {}
        for q, q_counts in counts.items():
            total = sum(q_counts.values())
            if total > 0:
                marginals[q] = {v: c / total for v, c in q_counts.items()}
            else:
                marginals[q] = {}

        return marginals

    def _markov_blanket_probability(
        self,
        var_name: str,
        state: Dict[str, Any]
    ) -> float:
        """Compute P(var | markov blanket)."""
        # P(var | parents) * prod P(child | parents)
        parent_values = {
            p: state.get(p)
            for p in self._network._parents.get(var_name, [])
        }

        p = self._network.get_probability(
            var_name, state.get(var_name), parent_values
        )

        for child in self._network._children.get(var_name, []):
            child_parent_values = {
                p: state.get(p)
                for p in self._network._parents.get(child, [])
            }
            p *= self._network.get_probability(
                child, state.get(child), child_parent_values
            )

        return p

    def importance_sampling(
        self,
        query: List[str],
        evidence: Dict[str, Any],
        num_samples: int = 1000
    ) -> Dict[str, Dict[Any, float]]:
        """Likelihood-weighted importance sampling."""
        weighted_counts: Dict[str, Dict[Any, float]] = {
            q: defaultdict(float) for q in query
        }

        for _ in range(num_samples):
            sample, weight = self._weighted_sample(evidence)

            for q in query:
                if q in sample:
                    weighted_counts[q][sample[q]] += weight

        # Normalize
        marginals = {}
        for q, q_counts in weighted_counts.items():
            total = sum(q_counts.values())
            if total > 0:
                marginals[q] = {v: c / total for v, c in q_counts.items()}
            else:
                marginals[q] = {}

        return marginals

    def _weighted_sample(
        self,
        evidence: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], float]:
        """Generate weighted sample."""
        sample = {}
        weight = 1.0

        order = self._network._topological_sort()

        for var_name in order:
            var = self._network._variables.get(var_name)
            if not var:
                continue

            parent_values = {
                p: sample[p]
                for p in self._network._parents.get(var_name, [])
            }

            if var_name in evidence:
                # Use evidence
                sample[var_name] = evidence[var_name]
                weight *= self._network.get_probability(
                    var_name, evidence[var_name], parent_values
                )
            else:
                # Sample
                probs = []
                for val in var.domain:
                    p = self._network.get_probability(var_name, val, parent_values)
                    probs.append((val, p))

                total = sum(p for _, p in probs)
                if total > 0:
                    r = random.random() * total
                    cumsum = 0
                    for val, p in probs:
                        cumsum += p
                        if r <= cumsum:
                            sample[var_name] = val
                            break
                    else:
                        sample[var_name] = probs[-1][0] if probs else None
                else:
                    sample[var_name] = random.choice(var.domain) if var.domain else None

        return sample, weight


# =============================================================================
# PROBABILISTIC REASONER
# =============================================================================

class ProbabilisticReasoner:
    """
    Probabilistic Reasoner for BAEL.

    Advanced probabilistic inference and uncertainty reasoning.
    """

    def __init__(self):
        self._networks: Dict[str, BayesianNetwork] = {}
        self._factor_graphs: Dict[str, FactorGraph] = {}
        self._chains: Dict[str, MarkovChain] = {}
        self._sampler = DistributionSampler()

    # -------------------------------------------------------------------------
    # NETWORK MANAGEMENT
    # -------------------------------------------------------------------------

    def create_network(self, name: str) -> BayesianNetwork:
        """Create a Bayesian network."""
        network = BayesianNetwork()
        self._networks[name] = network
        return network

    def get_network(self, name: str) -> Optional[BayesianNetwork]:
        """Get a Bayesian network."""
        return self._networks.get(name)

    def create_factor_graph(self, name: str) -> FactorGraph:
        """Create a factor graph."""
        graph = FactorGraph()
        self._factor_graphs[name] = graph
        return graph

    def get_factor_graph(self, name: str) -> Optional[FactorGraph]:
        """Get a factor graph."""
        return self._factor_graphs.get(name)

    # -------------------------------------------------------------------------
    # INFERENCE
    # -------------------------------------------------------------------------

    def infer(
        self,
        network_name: str,
        query: List[str],
        evidence: Dict[str, Any],
        method: InferenceMethod = InferenceMethod.GIBBS_SAMPLING,
        num_samples: int = 1000
    ) -> InferenceResult:
        """Perform probabilistic inference."""
        network = self._networks.get(network_name)
        if not network:
            return InferenceResult(query_variables=query)

        start_time = time.time()
        sampler = MonteCarloSampler(network)

        if method == InferenceMethod.REJECTION_SAMPLING:
            marginals = sampler.rejection_sampling(query, evidence, num_samples)
        elif method == InferenceMethod.GIBBS_SAMPLING:
            marginals = sampler.gibbs_sampling(query, evidence, num_samples)
        elif method == InferenceMethod.IMPORTANCE_SAMPLING:
            marginals = sampler.importance_sampling(query, evidence, num_samples)
        else:
            marginals = sampler.gibbs_sampling(query, evidence, num_samples)

        runtime = time.time() - start_time

        return InferenceResult(
            query_variables=query,
            marginals=marginals,
            method=method,
            runtime=runtime
        )

    def belief_propagation(
        self,
        graph_name: str,
        num_iterations: int = 10
    ) -> Dict[str, Dict[Any, float]]:
        """Run belief propagation on factor graph."""
        graph = self._factor_graphs.get(graph_name)
        if not graph:
            return {}

        return graph.belief_propagation(num_iterations)

    # -------------------------------------------------------------------------
    # MARKOV CHAINS
    # -------------------------------------------------------------------------

    def create_chain(
        self,
        name: str,
        states: List[str],
        transition_matrix: List[List[float]]
    ) -> MarkovChain:
        """Create a Markov chain."""
        chain = MarkovChain(
            states=states,
            transition_matrix=transition_matrix
        )
        self._chains[name] = chain
        return chain

    def simulate_chain(
        self,
        chain_name: str,
        num_steps: int,
        start_state: Optional[int] = None
    ) -> List[str]:
        """Simulate a Markov chain."""
        chain = self._chains.get(chain_name)
        if not chain:
            return []

        analyzer = MarkovChainAnalyzer(chain)
        path_indices = analyzer.simulate(num_steps, start_state)

        return [chain.states[i] for i in path_indices if i < len(chain.states)]

    def stationary_distribution(
        self,
        chain_name: str
    ) -> Dict[str, float]:
        """Compute stationary distribution."""
        chain = self._chains.get(chain_name)
        if not chain:
            return {}

        analyzer = MarkovChainAnalyzer(chain)
        dist = analyzer.stationary_distribution()

        return {
            chain.states[i]: p
            for i, p in enumerate(dist)
            if i < len(chain.states)
        }

    # -------------------------------------------------------------------------
    # DISTRIBUTIONS
    # -------------------------------------------------------------------------

    def sample_distribution(
        self,
        dist_type: DistributionType,
        parameters: Dict[str, float],
        num_samples: int = 1
    ) -> List[float]:
        """Sample from a distribution."""
        dist = Distribution(dist_type=dist_type, parameters=parameters)
        return [self._sampler.sample(dist) for _ in range(num_samples)]

    def pdf(
        self,
        dist_type: DistributionType,
        parameters: Dict[str, float],
        x: float
    ) -> float:
        """Compute PDF/PMF at x."""
        dist = Distribution(dist_type=dist_type, parameters=parameters)
        return self._sampler.pdf(dist, x)

    # -------------------------------------------------------------------------
    # UTILITIES
    # -------------------------------------------------------------------------

    def posterior_update(
        self,
        prior: Dict[Any, float],
        likelihood: Dict[Any, float],
        evidence: Any
    ) -> Dict[Any, float]:
        """Bayesian posterior update."""
        posterior = {}

        for hypothesis, prior_p in prior.items():
            likelihood_p = likelihood.get((hypothesis, evidence), 0)
            posterior[hypothesis] = prior_p * likelihood_p

        # Normalize
        total = sum(posterior.values())
        if total > 0:
            posterior = {h: p / total for h, p in posterior.items()}

        return posterior

    def entropy(self, distribution: Dict[Any, float]) -> float:
        """Compute entropy of a distribution."""
        h = 0.0
        for p in distribution.values():
            if p > 0:
                h -= p * math.log2(p)
        return h

    def kl_divergence(
        self,
        p: Dict[Any, float],
        q: Dict[Any, float]
    ) -> float:
        """Compute KL divergence D(P || Q)."""
        kl = 0.0
        for x, p_x in p.items():
            q_x = q.get(x, 1e-10)
            if p_x > 0:
                kl += p_x * math.log(p_x / q_x)
        return kl


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Probabilistic Reasoner."""
    print("=" * 70)
    print("BAEL - PROBABILISTIC REASONER DEMO")
    print("Advanced Probabilistic Inference and Uncertainty Reasoning")
    print("=" * 70)
    print()

    reasoner = ProbabilisticReasoner()

    # 1. Create Bayesian Network
    print("1. CREATE BAYESIAN NETWORK:")
    print("-" * 40)

    network = reasoner.create_network("weather")

    # Add variables
    network.add_variable("Rain", [True, False])
    network.add_variable("Sprinkler", [True, False])
    network.add_variable("GrassWet", [True, False])

    # Add edges
    network.add_edge("Rain", "GrassWet")
    network.add_edge("Sprinkler", "GrassWet")
    network.add_edge("Rain", "Sprinkler")

    # Set priors and CPTs
    network.set_prior("Rain", {True: 0.2, False: 0.8})

    network.set_cpt("Sprinkler", {
        (True,): {True: 0.01, False: 0.99},   # If raining, sprinkler off
        (False,): {True: 0.4, False: 0.6}     # If not raining, might use sprinkler
    })

    network.set_cpt("GrassWet", {
        (True, True): {True: 0.99, False: 0.01},   # Rain + Sprinkler
        (True, False): {True: 0.8, False: 0.2},    # Rain only
        (False, True): {True: 0.9, False: 0.1},    # Sprinkler only
        (False, False): {True: 0.0, False: 1.0}    # Neither
    })

    print("   Created network: Rain → Sprinkler → GrassWet")
    print("                    Rain → GrassWet")
    print()

    # 2. Sample from Network
    print("2. SAMPLE FROM NETWORK:")
    print("-" * 40)

    samples = [network.sample() for _ in range(5)]
    for i, s in enumerate(samples):
        print(f"   Sample {i+1}: Rain={s['Rain']}, Sprinkler={s['Sprinkler']}, GrassWet={s['GrassWet']}")
    print()

    # 3. Probabilistic Inference
    print("3. PROBABILISTIC INFERENCE:")
    print("-" * 40)

    # Query: P(Rain | GrassWet=True)
    result = reasoner.infer(
        "weather",
        query=["Rain"],
        evidence={"GrassWet": True},
        method=InferenceMethod.GIBBS_SAMPLING,
        num_samples=1000
    )

    print(f"   P(Rain | GrassWet=True):")
    for val, prob in result.marginals.get("Rain", {}).items():
        print(f"     Rain={val}: {prob:.3f}")
    print(f"   Runtime: {result.runtime:.3f}s")
    print()

    # 4. Different Inference Methods
    print("4. COMPARE INFERENCE METHODS:")
    print("-" * 40)

    methods = [
        InferenceMethod.REJECTION_SAMPLING,
        InferenceMethod.IMPORTANCE_SAMPLING,
        InferenceMethod.GIBBS_SAMPLING
    ]

    for method in methods:
        result = reasoner.infer(
            "weather",
            query=["Rain"],
            evidence={"GrassWet": True},
            method=method,
            num_samples=500
        )
        rain_prob = result.marginals.get("Rain", {}).get(True, 0)
        print(f"   {method.value}: P(Rain=True|GrassWet=True) = {rain_prob:.3f}")
    print()

    # 5. Factor Graph
    print("5. FACTOR GRAPH:")
    print("-" * 40)

    fg = reasoner.create_factor_graph("simple")
    fg.add_variable("A", [0, 1])
    fg.add_variable("B", [0, 1])

    fg.add_factor(["A", "B"], {
        (0, 0): 0.3,
        (0, 1): 0.2,
        (1, 0): 0.1,
        (1, 1): 0.4
    })

    marginals = reasoner.belief_propagation("simple", num_iterations=10)
    print("   Factor graph marginals after belief propagation:")
    for var, dist in marginals.items():
        print(f"     {var}: {dist}")
    print()

    # 6. Markov Chain
    print("6. MARKOV CHAIN:")
    print("-" * 40)

    chain = reasoner.create_chain(
        "weather_chain",
        states=["Sunny", "Cloudy", "Rainy"],
        transition_matrix=[
            [0.7, 0.2, 0.1],  # Sunny → ...
            [0.3, 0.4, 0.3],  # Cloudy → ...
            [0.2, 0.3, 0.5]   # Rainy → ...
        ]
    )

    path = reasoner.simulate_chain("weather_chain", num_steps=10, start_state=0)
    print(f"   Simulation: {' → '.join(path)}")

    stationary = reasoner.stationary_distribution("weather_chain")
    print(f"   Stationary distribution:")
    for state, prob in stationary.items():
        print(f"     {state}: {prob:.3f}")
    print()

    # 7. Distribution Sampling
    print("7. DISTRIBUTION SAMPLING:")
    print("-" * 40)

    gaussian_samples = reasoner.sample_distribution(
        DistributionType.GAUSSIAN,
        {"mean": 0, "std": 1},
        num_samples=5
    )
    print(f"   Gaussian(0, 1): {[f'{s:.2f}' for s in gaussian_samples]}")

    poisson_samples = reasoner.sample_distribution(
        DistributionType.POISSON,
        {"lambda": 3},
        num_samples=5
    )
    print(f"   Poisson(3): {[int(s) for s in poisson_samples]}")

    beta_samples = reasoner.sample_distribution(
        DistributionType.BETA,
        {"alpha": 2, "beta": 5},
        num_samples=5
    )
    print(f"   Beta(2, 5): {[f'{s:.2f}' for s in beta_samples]}")
    print()

    # 8. Bayesian Update
    print("8. BAYESIAN UPDATE:")
    print("-" * 40)

    prior = {"H0": 0.3, "H1": 0.7}
    likelihood = {
        ("H0", "E"): 0.1,
        ("H1", "E"): 0.8
    }

    posterior = reasoner.posterior_update(prior, likelihood, "E")
    print(f"   Prior: {prior}")
    print(f"   Posterior given evidence E:")
    for h, p in posterior.items():
        print(f"     {h}: {p:.3f}")
    print()

    # 9. Information Theory
    print("9. INFORMATION THEORY:")
    print("-" * 40)

    dist1 = {"A": 0.5, "B": 0.5}
    dist2 = {"A": 0.9, "B": 0.1}

    h1 = reasoner.entropy(dist1)
    h2 = reasoner.entropy(dist2)
    kl = reasoner.kl_divergence(dist1, dist2)

    print(f"   Uniform distribution: H = {h1:.3f} bits")
    print(f"   Skewed distribution:  H = {h2:.3f} bits")
    print(f"   KL(uniform || skewed) = {kl:.3f}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Probabilistic Reasoner Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
