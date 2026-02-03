#!/usr/bin/env python3
"""
BAEL - Discovery Engine
Advanced scientific discovery and hypothesis generation.

Features:
- Hypothesis generation and refinement
- Experiment design
- Data-driven discovery
- Pattern mining
- Theory formation
- Discovery strategies
"""

import asyncio
import copy
import hashlib
import math
import random
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (Any, Callable, Dict, Generic, List, Optional, Set, Tuple,
                    Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class DiscoveryType(Enum):
    """Types of discovery."""
    PATTERN = "pattern"
    RELATIONSHIP = "relationship"
    ANOMALY = "anomaly"
    LAW = "law"
    THEORY = "theory"


class HypothesisStatus(Enum):
    """Status of a hypothesis."""
    PROPOSED = "proposed"
    TESTING = "testing"
    CONFIRMED = "confirmed"
    REFUTED = "refuted"
    REVISED = "revised"


class ExperimentStatus(Enum):
    """Status of an experiment."""
    DESIGNED = "designed"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class StrategyType(Enum):
    """Types of discovery strategies."""
    DATA_DRIVEN = "data_driven"
    HYPOTHESIS_DRIVEN = "hypothesis_driven"
    ANALOGY_BASED = "analogy_based"
    CONSTRAINT_BASED = "constraint_based"
    RANDOM_SEARCH = "random_search"


class RelationType(Enum):
    """Types of relationships."""
    CAUSAL = "causal"
    CORRELATIONAL = "correlational"
    FUNCTIONAL = "functional"
    STRUCTURAL = "structural"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Observation:
    """A data observation."""
    obs_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    variables: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    source: str = ""


@dataclass
class Pattern:
    """A discovered pattern."""
    pattern_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: str = ""
    variables: List[str] = field(default_factory=list)
    formula: Optional[str] = None
    support: float = 0.0
    confidence: float = 0.0
    examples: List[str] = field(default_factory=list)


@dataclass
class Relationship:
    """A discovered relationship."""
    rel_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_var: str = ""
    target_var: str = ""
    rel_type: RelationType = RelationType.CORRELATIONAL
    strength: float = 0.0
    direction: int = 1  # 1 = positive, -1 = negative
    formula: Optional[str] = None


@dataclass
class Hypothesis:
    """A scientific hypothesis."""
    hyp_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    statement: str = ""
    variables: List[str] = field(default_factory=list)
    predictions: List[str] = field(default_factory=list)
    status: HypothesisStatus = HypothesisStatus.PROPOSED
    confidence: float = 0.5
    evidence_for: List[str] = field(default_factory=list)
    evidence_against: List[str] = field(default_factory=list)


@dataclass
class Experiment:
    """An experiment design."""
    exp_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    hypothesis_id: str = ""
    description: str = ""
    independent_vars: List[str] = field(default_factory=list)
    dependent_vars: List[str] = field(default_factory=list)
    control_vars: List[str] = field(default_factory=list)
    expected_outcome: str = ""
    status: ExperimentStatus = ExperimentStatus.DESIGNED


@dataclass
class Theory:
    """A scientific theory."""
    theory_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    hypotheses: List[str] = field(default_factory=list)
    laws: List[str] = field(default_factory=list)
    explanatory_scope: List[str] = field(default_factory=list)
    predictive_power: float = 0.0


@dataclass
class Discovery:
    """A discovery."""
    disc_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    disc_type: DiscoveryType = DiscoveryType.PATTERN
    content: Any = None
    significance: float = 0.0
    novelty: float = 0.0
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())


# =============================================================================
# OBSERVATION MANAGER
# =============================================================================

class ObservationManager:
    """Manage observations."""

    def __init__(self):
        self._observations: Dict[str, Observation] = {}

    def add(
        self,
        variables: Dict[str, Any],
        source: str = ""
    ) -> Observation:
        """Add an observation."""
        obs = Observation(variables=variables, source=source)
        self._observations[obs.obs_id] = obs
        return obs

    def get(self, obs_id: str) -> Optional[Observation]:
        """Get an observation."""
        return self._observations.get(obs_id)

    def all_observations(self) -> List[Observation]:
        """Get all observations."""
        return list(self._observations.values())

    def get_variable_values(self, var_name: str) -> List[Any]:
        """Get all values for a variable."""
        return [
            obs.variables[var_name]
            for obs in self._observations.values()
            if var_name in obs.variables
        ]

    def get_variables(self) -> Set[str]:
        """Get all variable names."""
        vars = set()
        for obs in self._observations.values():
            vars.update(obs.variables.keys())
        return vars


# =============================================================================
# PATTERN MINER
# =============================================================================

class PatternMiner:
    """Mine patterns from observations."""

    def __init__(self, obs_manager: ObservationManager):
        self._obs_manager = obs_manager

    def find_frequent_values(
        self,
        min_support: float = 0.5
    ) -> List[Pattern]:
        """Find frequently occurring values."""
        patterns = []
        observations = self._obs_manager.all_observations()
        n_obs = len(observations)

        if n_obs == 0:
            return []

        for var in self._obs_manager.get_variables():
            value_counts = defaultdict(int)
            for obs in observations:
                if var in obs.variables:
                    value_counts[obs.variables[var]] += 1

            for value, count in value_counts.items():
                support = count / n_obs
                if support >= min_support:
                    pattern = Pattern(
                        description=f"{var} = {value}",
                        variables=[var],
                        support=support,
                        confidence=1.0
                    )
                    patterns.append(pattern)

        return patterns

    def find_co_occurrences(
        self,
        min_support: float = 0.3,
        min_confidence: float = 0.7
    ) -> List[Pattern]:
        """Find co-occurring values."""
        patterns = []
        observations = self._obs_manager.all_observations()
        n_obs = len(observations)

        if n_obs == 0:
            return []

        variables = list(self._obs_manager.get_variables())

        # Check pairs
        for i, var1 in enumerate(variables):
            for var2 in variables[i+1:]:
                pair_counts = defaultdict(int)
                var1_counts = defaultdict(int)

                for obs in observations:
                    if var1 in obs.variables:
                        var1_counts[obs.variables[var1]] += 1
                        if var2 in obs.variables:
                            key = (obs.variables[var1], obs.variables[var2])
                            pair_counts[key] += 1

                for (v1, v2), count in pair_counts.items():
                    support = count / n_obs
                    confidence = count / var1_counts[v1] if var1_counts[v1] > 0 else 0

                    if support >= min_support and confidence >= min_confidence:
                        pattern = Pattern(
                            description=f"{var1}={v1} → {var2}={v2}",
                            variables=[var1, var2],
                            support=support,
                            confidence=confidence
                        )
                        patterns.append(pattern)

        return patterns


# =============================================================================
# RELATIONSHIP DISCOVERER
# =============================================================================

class RelationshipDiscoverer:
    """Discover relationships between variables."""

    def __init__(self, obs_manager: ObservationManager):
        self._obs_manager = obs_manager

    def discover_correlations(
        self,
        min_strength: float = 0.5
    ) -> List[Relationship]:
        """Discover correlations between numeric variables."""
        relationships = []
        observations = self._obs_manager.all_observations()

        if len(observations) < 3:
            return []

        variables = list(self._obs_manager.get_variables())

        for i, var1 in enumerate(variables):
            for var2 in variables[i+1:]:
                vals1 = []
                vals2 = []

                for obs in observations:
                    if var1 in obs.variables and var2 in obs.variables:
                        v1 = obs.variables[var1]
                        v2 = obs.variables[var2]
                        if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
                            vals1.append(v1)
                            vals2.append(v2)

                if len(vals1) >= 3:
                    corr = self._pearson(vals1, vals2)
                    if abs(corr) >= min_strength:
                        rel = Relationship(
                            source_var=var1,
                            target_var=var2,
                            rel_type=RelationType.CORRELATIONAL,
                            strength=abs(corr),
                            direction=1 if corr > 0 else -1
                        )
                        relationships.append(rel)

        return relationships

    def discover_functional(
        self,
        tolerance: float = 0.1
    ) -> List[Relationship]:
        """Discover functional relationships (y = f(x))."""
        relationships = []
        observations = self._obs_manager.all_observations()

        if len(observations) < 3:
            return []

        variables = list(self._obs_manager.get_variables())

        for var1 in variables:
            for var2 in variables:
                if var1 == var2:
                    continue

                data = []
                for obs in observations:
                    if var1 in obs.variables and var2 in obs.variables:
                        v1 = obs.variables[var1]
                        v2 = obs.variables[var2]
                        if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
                            data.append((v1, v2))

                if len(data) >= 3:
                    # Try linear fit y = ax + b
                    fit = self._linear_fit(data)
                    if fit:
                        a, b, r2 = fit
                        if r2 >= 1 - tolerance:
                            rel = Relationship(
                                source_var=var1,
                                target_var=var2,
                                rel_type=RelationType.FUNCTIONAL,
                                strength=r2,
                                direction=1 if a > 0 else -1,
                                formula=f"{var2} = {a:.2f}*{var1} + {b:.2f}"
                            )
                            relationships.append(rel)

        return relationships

    def _pearson(self, x: List[float], y: List[float]) -> float:
        """Calculate Pearson correlation coefficient."""
        n = len(x)
        if n == 0:
            return 0

        mean_x = sum(x) / n
        mean_y = sum(y) / n

        num = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
        den_x = math.sqrt(sum((xi - mean_x) ** 2 for xi in x))
        den_y = math.sqrt(sum((yi - mean_y) ** 2 for yi in y))

        if den_x == 0 or den_y == 0:
            return 0

        return num / (den_x * den_y)

    def _linear_fit(
        self,
        data: List[Tuple[float, float]]
    ) -> Optional[Tuple[float, float, float]]:
        """Fit linear model y = ax + b, return (a, b, r2)."""
        n = len(data)
        if n < 2:
            return None

        sum_x = sum(d[0] for d in data)
        sum_y = sum(d[1] for d in data)
        sum_xy = sum(d[0] * d[1] for d in data)
        sum_x2 = sum(d[0] ** 2 for d in data)

        denom = n * sum_x2 - sum_x ** 2
        if abs(denom) < 1e-10:
            return None

        a = (n * sum_xy - sum_x * sum_y) / denom
        b = (sum_y - a * sum_x) / n

        # Calculate R2
        mean_y = sum_y / n
        ss_tot = sum((d[1] - mean_y) ** 2 for d in data)
        ss_res = sum((d[1] - (a * d[0] + b)) ** 2 for d in data)

        if ss_tot == 0:
            r2 = 1.0
        else:
            r2 = 1 - ss_res / ss_tot

        return (a, b, r2)


# =============================================================================
# HYPOTHESIS GENERATOR
# =============================================================================

class HypothesisGenerator:
    """Generate hypotheses from discoveries."""

    def __init__(self):
        self._hypotheses: Dict[str, Hypothesis] = {}

    def from_pattern(self, pattern: Pattern) -> Hypothesis:
        """Generate hypothesis from pattern."""
        hyp = Hypothesis(
            statement=f"The pattern '{pattern.description}' holds generally",
            variables=pattern.variables,
            predictions=[
                f"New observations will follow {pattern.description}"
            ],
            confidence=pattern.confidence
        )
        self._hypotheses[hyp.hyp_id] = hyp
        return hyp

    def from_relationship(self, rel: Relationship) -> Hypothesis:
        """Generate hypothesis from relationship."""
        if rel.rel_type == RelationType.FUNCTIONAL:
            statement = f"{rel.formula}"
        else:
            direction = "increases" if rel.direction > 0 else "decreases"
            statement = f"As {rel.source_var} increases, {rel.target_var} {direction}"

        hyp = Hypothesis(
            statement=statement,
            variables=[rel.source_var, rel.target_var],
            predictions=[
                f"Changes in {rel.source_var} will predict changes in {rel.target_var}"
            ],
            confidence=rel.strength
        )
        self._hypotheses[hyp.hyp_id] = hyp
        return hyp

    def propose(
        self,
        statement: str,
        variables: List[str],
        predictions: List[str]
    ) -> Hypothesis:
        """Propose a hypothesis."""
        hyp = Hypothesis(
            statement=statement,
            variables=variables,
            predictions=predictions
        )
        self._hypotheses[hyp.hyp_id] = hyp
        return hyp

    def get(self, hyp_id: str) -> Optional[Hypothesis]:
        """Get a hypothesis."""
        return self._hypotheses.get(hyp_id)

    def all_hypotheses(self) -> List[Hypothesis]:
        """Get all hypotheses."""
        return list(self._hypotheses.values())


# =============================================================================
# EXPERIMENT DESIGNER
# =============================================================================

class ExperimentDesigner:
    """Design experiments to test hypotheses."""

    def __init__(self):
        self._experiments: Dict[str, Experiment] = {}

    def design(
        self,
        hypothesis: Hypothesis,
        independent_vars: List[str],
        dependent_vars: List[str],
        control_vars: Optional[List[str]] = None
    ) -> Experiment:
        """Design an experiment."""
        exp = Experiment(
            hypothesis_id=hypothesis.hyp_id,
            description=f"Test: {hypothesis.statement}",
            independent_vars=independent_vars,
            dependent_vars=dependent_vars,
            control_vars=control_vars or [],
            expected_outcome=hypothesis.predictions[0] if hypothesis.predictions else ""
        )
        self._experiments[exp.exp_id] = exp
        return exp

    def design_from_relationship(
        self,
        rel: Relationship,
        hypothesis: Hypothesis
    ) -> Experiment:
        """Design experiment from relationship."""
        return self.design(
            hypothesis=hypothesis,
            independent_vars=[rel.source_var],
            dependent_vars=[rel.target_var]
        )

    def get(self, exp_id: str) -> Optional[Experiment]:
        """Get an experiment."""
        return self._experiments.get(exp_id)

    def all_experiments(self) -> List[Experiment]:
        """Get all experiments."""
        return list(self._experiments.values())


# =============================================================================
# THEORY BUILDER
# =============================================================================

class TheoryBuilder:
    """Build theories from confirmed hypotheses."""

    def __init__(self):
        self._theories: Dict[str, Theory] = {}

    def build(
        self,
        name: str,
        hypotheses: List[Hypothesis],
        laws: Optional[List[str]] = None
    ) -> Theory:
        """Build a theory."""
        confirmed = [h for h in hypotheses if h.status == HypothesisStatus.CONFIRMED]

        theory = Theory(
            name=name,
            hypotheses=[h.hyp_id for h in confirmed],
            laws=laws or [],
            explanatory_scope=[v for h in confirmed for v in h.variables],
            predictive_power=sum(h.confidence for h in confirmed) / len(confirmed) if confirmed else 0
        )
        self._theories[theory.theory_id] = theory
        return theory

    def get(self, theory_id: str) -> Optional[Theory]:
        """Get a theory."""
        return self._theories.get(theory_id)

    def all_theories(self) -> List[Theory]:
        """Get all theories."""
        return list(self._theories.values())


# =============================================================================
# DISCOVERY ENGINE
# =============================================================================

class DiscoveryEngine:
    """
    Discovery Engine for BAEL.

    Advanced scientific discovery and hypothesis generation.
    """

    def __init__(self):
        self._obs_manager = ObservationManager()
        self._pattern_miner = PatternMiner(self._obs_manager)
        self._rel_discoverer = RelationshipDiscoverer(self._obs_manager)
        self._hyp_generator = HypothesisGenerator()
        self._exp_designer = ExperimentDesigner()
        self._theory_builder = TheoryBuilder()
        self._discoveries: List[Discovery] = []

    # -------------------------------------------------------------------------
    # OBSERVATIONS
    # -------------------------------------------------------------------------

    def observe(
        self,
        variables: Dict[str, Any],
        source: str = ""
    ) -> Observation:
        """Record an observation."""
        return self._obs_manager.add(variables, source)

    def get_observation(self, obs_id: str) -> Optional[Observation]:
        """Get an observation."""
        return self._obs_manager.get(obs_id)

    def all_observations(self) -> List[Observation]:
        """Get all observations."""
        return self._obs_manager.all_observations()

    def get_variables(self) -> Set[str]:
        """Get all observed variables."""
        return self._obs_manager.get_variables()

    # -------------------------------------------------------------------------
    # PATTERN DISCOVERY
    # -------------------------------------------------------------------------

    def discover_patterns(
        self,
        min_support: float = 0.5
    ) -> List[Pattern]:
        """Discover patterns in observations."""
        patterns = self._pattern_miner.find_frequent_values(min_support)

        for pattern in patterns:
            disc = Discovery(
                disc_type=DiscoveryType.PATTERN,
                content=pattern,
                significance=pattern.support,
                novelty=1.0
            )
            self._discoveries.append(disc)

        return patterns

    def discover_co_occurrences(
        self,
        min_support: float = 0.3,
        min_confidence: float = 0.7
    ) -> List[Pattern]:
        """Discover co-occurring patterns."""
        patterns = self._pattern_miner.find_co_occurrences(min_support, min_confidence)

        for pattern in patterns:
            disc = Discovery(
                disc_type=DiscoveryType.PATTERN,
                content=pattern,
                significance=pattern.confidence,
                novelty=1.0
            )
            self._discoveries.append(disc)

        return patterns

    # -------------------------------------------------------------------------
    # RELATIONSHIP DISCOVERY
    # -------------------------------------------------------------------------

    def discover_correlations(
        self,
        min_strength: float = 0.5
    ) -> List[Relationship]:
        """Discover correlations."""
        rels = self._rel_discoverer.discover_correlations(min_strength)

        for rel in rels:
            disc = Discovery(
                disc_type=DiscoveryType.RELATIONSHIP,
                content=rel,
                significance=rel.strength,
                novelty=1.0
            )
            self._discoveries.append(disc)

        return rels

    def discover_functional(
        self,
        tolerance: float = 0.1
    ) -> List[Relationship]:
        """Discover functional relationships."""
        rels = self._rel_discoverer.discover_functional(tolerance)

        for rel in rels:
            disc = Discovery(
                disc_type=DiscoveryType.LAW,
                content=rel,
                significance=rel.strength,
                novelty=1.0
            )
            self._discoveries.append(disc)

        return rels

    # -------------------------------------------------------------------------
    # HYPOTHESIS
    # -------------------------------------------------------------------------

    def hypothesize_from_pattern(self, pattern: Pattern) -> Hypothesis:
        """Generate hypothesis from pattern."""
        return self._hyp_generator.from_pattern(pattern)

    def hypothesize_from_relationship(self, rel: Relationship) -> Hypothesis:
        """Generate hypothesis from relationship."""
        return self._hyp_generator.from_relationship(rel)

    def propose_hypothesis(
        self,
        statement: str,
        variables: List[str],
        predictions: List[str]
    ) -> Hypothesis:
        """Propose a hypothesis."""
        return self._hyp_generator.propose(statement, variables, predictions)

    def get_hypothesis(self, hyp_id: str) -> Optional[Hypothesis]:
        """Get a hypothesis."""
        return self._hyp_generator.get(hyp_id)

    def all_hypotheses(self) -> List[Hypothesis]:
        """Get all hypotheses."""
        return self._hyp_generator.all_hypotheses()

    def update_hypothesis(
        self,
        hyp_id: str,
        status: HypothesisStatus,
        evidence: Optional[str] = None,
        supporting: bool = True
    ) -> Optional[Hypothesis]:
        """Update hypothesis status."""
        hyp = self._hyp_generator.get(hyp_id)
        if not hyp:
            return None

        hyp.status = status
        if evidence:
            if supporting:
                hyp.evidence_for.append(evidence)
            else:
                hyp.evidence_against.append(evidence)

        return hyp

    # -------------------------------------------------------------------------
    # EXPERIMENTS
    # -------------------------------------------------------------------------

    def design_experiment(
        self,
        hypothesis: Hypothesis,
        independent_vars: List[str],
        dependent_vars: List[str],
        control_vars: Optional[List[str]] = None
    ) -> Experiment:
        """Design an experiment."""
        return self._exp_designer.design(
            hypothesis, independent_vars, dependent_vars, control_vars
        )

    def get_experiment(self, exp_id: str) -> Optional[Experiment]:
        """Get an experiment."""
        return self._exp_designer.get(exp_id)

    def all_experiments(self) -> List[Experiment]:
        """Get all experiments."""
        return self._exp_designer.all_experiments()

    # -------------------------------------------------------------------------
    # THEORIES
    # -------------------------------------------------------------------------

    def build_theory(
        self,
        name: str,
        hypotheses: List[Hypothesis],
        laws: Optional[List[str]] = None
    ) -> Theory:
        """Build a theory."""
        return self._theory_builder.build(name, hypotheses, laws)

    def get_theory(self, theory_id: str) -> Optional[Theory]:
        """Get a theory."""
        return self._theory_builder.get(theory_id)

    def all_theories(self) -> List[Theory]:
        """Get all theories."""
        return self._theory_builder.all_theories()

    # -------------------------------------------------------------------------
    # DISCOVERIES
    # -------------------------------------------------------------------------

    def all_discoveries(self) -> List[Discovery]:
        """Get all discoveries."""
        return self._discoveries

    def discoveries_by_type(self, disc_type: DiscoveryType) -> List[Discovery]:
        """Get discoveries by type."""
        return [d for d in self._discoveries if d.disc_type == disc_type]

    def top_discoveries(self, n: int = 5) -> List[Discovery]:
        """Get top n discoveries by significance."""
        return sorted(self._discoveries, key=lambda d: d.significance, reverse=True)[:n]


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Discovery Engine."""
    print("=" * 70)
    print("BAEL - DISCOVERY ENGINE DEMO")
    print("Advanced Scientific Discovery and Hypothesis Generation")
    print("=" * 70)
    print()

    engine = DiscoveryEngine()

    # 1. Add Observations
    print("1. ADD OBSERVATIONS:")
    print("-" * 40)

    # Physical law: F = m * a
    observations = [
        {"mass": 1.0, "acceleration": 2.0, "force": 2.0},
        {"mass": 2.0, "acceleration": 2.0, "force": 4.0},
        {"mass": 3.0, "acceleration": 2.0, "force": 6.0},
        {"mass": 1.0, "acceleration": 3.0, "force": 3.0},
        {"mass": 2.0, "acceleration": 3.0, "force": 6.0},
        {"mass": 1.0, "acceleration": 4.0, "force": 4.0},
    ]

    for obs in observations:
        engine.observe(obs, source="experiment")
        print(f"   {obs}")
    print()

    # 2. Discover Correlations
    print("2. DISCOVER CORRELATIONS:")
    print("-" * 40)

    correlations = engine.discover_correlations(min_strength=0.5)
    for corr in correlations:
        direction = "positive" if corr.direction > 0 else "negative"
        print(f"   {corr.source_var} ↔ {corr.target_var}: {corr.strength:.2f} ({direction})")
    print()

    # 3. Discover Functional Relationships
    print("3. DISCOVER FUNCTIONAL RELATIONSHIPS:")
    print("-" * 40)

    functional = engine.discover_functional(tolerance=0.1)
    for rel in functional:
        print(f"   {rel.formula} (R² = {rel.strength:.3f})")
    print()

    # 4. Generate Hypotheses
    print("4. GENERATE HYPOTHESES:")
    print("-" * 40)

    for rel in functional:
        hyp = engine.hypothesize_from_relationship(rel)
        print(f"   {hyp.statement}")
        print(f"      Predictions: {hyp.predictions}")
    print()

    # 5. Design Experiments
    print("5. DESIGN EXPERIMENTS:")
    print("-" * 40)

    for hyp in engine.all_hypotheses():
        exp = engine.design_experiment(
            hypothesis=hyp,
            independent_vars=["mass"],
            dependent_vars=["force"],
            control_vars=["acceleration"]
        )
        print(f"   Experiment: {exp.description}")
        print(f"      IV: {exp.independent_vars}, DV: {exp.dependent_vars}")
    print()

    # 6. Confirm Hypothesis
    print("6. CONFIRM HYPOTHESIS:")
    print("-" * 40)

    for hyp in engine.all_hypotheses():
        engine.update_hypothesis(
            hyp.hyp_id,
            status=HypothesisStatus.CONFIRMED,
            evidence="All predictions matched observations",
            supporting=True
        )
        print(f"   {hyp.statement}")
        print(f"      Status: {hyp.status.value}")
    print()

    # 7. Build Theory
    print("7. BUILD THEORY:")
    print("-" * 40)

    theory = engine.build_theory(
        name="Newton's Second Law",
        hypotheses=engine.all_hypotheses(),
        laws=["F = m × a"]
    )
    print(f"   Theory: {theory.name}")
    print(f"   Laws: {theory.laws}")
    print(f"   Predictive Power: {theory.predictive_power:.2f}")
    print()

    # 8. Pattern Discovery
    print("8. PATTERN DISCOVERY:")
    print("-" * 40)

    # Add categorical observations
    engine2 = DiscoveryEngine()

    categoricals = [
        {"weather": "sunny", "activity": "outdoor", "mood": "happy"},
        {"weather": "sunny", "activity": "outdoor", "mood": "happy"},
        {"weather": "rainy", "activity": "indoor", "mood": "neutral"},
        {"weather": "rainy", "activity": "indoor", "mood": "sad"},
        {"weather": "sunny", "activity": "outdoor", "mood": "happy"},
    ]

    for obs in categoricals:
        engine2.observe(obs)

    patterns = engine2.discover_patterns(min_support=0.4)
    for p in patterns:
        print(f"   {p.description} (support: {p.support:.2f})")
    print()

    # 9. Co-occurrence Discovery
    print("9. CO-OCCURRENCE DISCOVERY:")
    print("-" * 40)

    co_patterns = engine2.discover_co_occurrences(min_support=0.3, min_confidence=0.6)
    for p in co_patterns:
        print(f"   {p.description}")
        print(f"      Support: {p.support:.2f}, Confidence: {p.confidence:.2f}")
    print()

    # 10. Top Discoveries
    print("10. TOP DISCOVERIES:")
    print("-" * 40)

    top = engine.top_discoveries(5)
    for i, disc in enumerate(top):
        print(f"   {i+1}. Type: {disc.disc_type.value}, Significance: {disc.significance:.2f}")
        if hasattr(disc.content, 'formula') and disc.content.formula:
            print(f"      {disc.content.formula}")
        elif hasattr(disc.content, 'description'):
            print(f"      {disc.content.description}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Discovery Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
