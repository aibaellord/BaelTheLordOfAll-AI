#!/usr/bin/env python3
"""
BAEL - Hypothesis Engine
Hypothesis generation and testing for agents.

Features:
- Hypothesis generation
- Evidence collection
- Hypothesis testing
- Confidence tracking
- Theory formation
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

class HypothesisType(Enum):
    """Types of hypotheses."""
    CAUSAL = "causal"
    CORRELATIONAL = "correlational"
    DESCRIPTIVE = "descriptive"
    PREDICTIVE = "predictive"
    EXPLANATORY = "explanatory"


class HypothesisStatus(Enum):
    """Status of hypotheses."""
    PROPOSED = "proposed"
    TESTING = "testing"
    SUPPORTED = "supported"
    REJECTED = "rejected"
    INCONCLUSIVE = "inconclusive"


class EvidenceType(Enum):
    """Types of evidence."""
    OBSERVATION = "observation"
    EXPERIMENT = "experiment"
    PRIOR_KNOWLEDGE = "prior_knowledge"
    INFERENCE = "inference"
    TESTIMONY = "testimony"


class EvidenceStrength(Enum):
    """Strength of evidence."""
    WEAK = 1
    MODERATE = 2
    STRONG = 3
    DECISIVE = 4


class TestType(Enum):
    """Types of hypothesis tests."""
    CONFIRMATION = "confirmation"
    FALSIFICATION = "falsification"
    COMPARISON = "comparison"
    PREDICTION = "prediction"


class ConfidenceLevel(Enum):
    """Confidence levels."""
    VERY_LOW = 0.1
    LOW = 0.3
    MODERATE = 0.5
    HIGH = 0.7
    VERY_HIGH = 0.9


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Hypothesis:
    """A hypothesis."""
    hypothesis_id: str = ""
    statement: str = ""
    hypothesis_type: HypothesisType = HypothesisType.DESCRIPTIVE
    status: HypothesisStatus = HypothesisStatus.PROPOSED
    prior_probability: float = 0.5
    posterior_probability: float = 0.5
    confidence: float = 0.5
    evidence_ids: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.hypothesis_id:
            self.hypothesis_id = str(uuid.uuid4())[:8]


@dataclass
class Evidence:
    """Evidence for a hypothesis."""
    evidence_id: str = ""
    description: str = ""
    evidence_type: EvidenceType = EvidenceType.OBSERVATION
    strength: EvidenceStrength = EvidenceStrength.MODERATE
    supports: bool = True
    likelihood_ratio: float = 1.0
    source: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.evidence_id:
            self.evidence_id = str(uuid.uuid4())[:8]


@dataclass
class Test:
    """A hypothesis test."""
    test_id: str = ""
    hypothesis_id: str = ""
    test_type: TestType = TestType.CONFIRMATION
    prediction: str = ""
    observation: str = ""
    result: Optional[bool] = None
    confidence: float = 0.5
    executed_at: Optional[datetime] = None

    def __post_init__(self):
        if not self.test_id:
            self.test_id = str(uuid.uuid4())[:8]


@dataclass
class Theory:
    """A theory formed from hypotheses."""
    theory_id: str = ""
    name: str = ""
    description: str = ""
    hypothesis_ids: List[str] = field(default_factory=list)
    coherence: float = 0.5
    explanatory_power: float = 0.5
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.theory_id:
            self.theory_id = str(uuid.uuid4())[:8]


@dataclass
class HypothesisConfig:
    """Hypothesis engine configuration."""
    prior_default: float = 0.5
    confirmation_threshold: float = 0.8
    rejection_threshold: float = 0.2
    min_evidence_count: int = 3


# =============================================================================
# HYPOTHESIS GENERATOR
# =============================================================================

class HypothesisGenerator:
    """Generate hypotheses from observations."""

    def __init__(self, prior_default: float = 0.5):
        self._hypotheses: Dict[str, Hypothesis] = {}
        self._prior_default = prior_default
        self._templates = {
            HypothesisType.CAUSAL: "If {cause}, then {effect}",
            HypothesisType.CORRELATIONAL: "{A} correlates with {B}",
            HypothesisType.DESCRIPTIVE: "{subject} has property {property}",
            HypothesisType.PREDICTIVE: "Given {conditions}, {outcome} will occur",
            HypothesisType.EXPLANATORY: "{phenomenon} because {reason}"
        }

    def generate(
        self,
        statement: str,
        hypothesis_type: HypothesisType,
        prior_probability: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Hypothesis:
        """Generate a hypothesis."""
        hypothesis = Hypothesis(
            statement=statement,
            hypothesis_type=hypothesis_type,
            prior_probability=prior_probability or self._prior_default,
            posterior_probability=prior_probability or self._prior_default,
            metadata=metadata or {}
        )

        self._hypotheses[hypothesis.hypothesis_id] = hypothesis

        return hypothesis

    def generate_from_template(
        self,
        hypothesis_type: HypothesisType,
        **kwargs
    ) -> Hypothesis:
        """Generate hypothesis from template."""
        template = self._templates.get(hypothesis_type, "{}")

        try:
            statement = template.format(**kwargs)
        except KeyError:
            statement = str(kwargs)

        return self.generate(statement, hypothesis_type)

    def generate_causal(
        self,
        cause: str,
        effect: str
    ) -> Hypothesis:
        """Generate causal hypothesis."""
        return self.generate_from_template(
            HypothesisType.CAUSAL,
            cause=cause,
            effect=effect
        )

    def generate_predictive(
        self,
        conditions: str,
        outcome: str
    ) -> Hypothesis:
        """Generate predictive hypothesis."""
        return self.generate_from_template(
            HypothesisType.PREDICTIVE,
            conditions=conditions,
            outcome=outcome
        )

    def generate_alternatives(
        self,
        observation: str,
        num_alternatives: int = 3
    ) -> List[Hypothesis]:
        """Generate alternative hypotheses."""
        alternatives = []

        types = list(HypothesisType)

        for i in range(num_alternatives):
            hyp_type = types[i % len(types)]
            statement = f"Alternative {i + 1}: {observation} might be explained by {hyp_type.value} mechanism"

            alternatives.append(self.generate(statement, hyp_type))

        return alternatives

    def get(self, hypothesis_id: str) -> Optional[Hypothesis]:
        """Get hypothesis by ID."""
        return self._hypotheses.get(hypothesis_id)

    def get_by_status(self, status: HypothesisStatus) -> List[Hypothesis]:
        """Get hypotheses by status."""
        return [
            h for h in self._hypotheses.values()
            if h.status == status
        ]

    def get_by_type(self, hypothesis_type: HypothesisType) -> List[Hypothesis]:
        """Get hypotheses by type."""
        return [
            h for h in self._hypotheses.values()
            if h.hypothesis_type == hypothesis_type
        ]

    def count(self) -> int:
        """Count hypotheses."""
        return len(self._hypotheses)

    def all(self) -> List[Hypothesis]:
        """Get all hypotheses."""
        return list(self._hypotheses.values())


# =============================================================================
# EVIDENCE COLLECTOR
# =============================================================================

class EvidenceCollector:
    """Collect and manage evidence."""

    def __init__(self):
        self._evidence: Dict[str, Evidence] = {}
        self._by_hypothesis: Dict[str, List[str]] = defaultdict(list)

    def collect(
        self,
        description: str,
        evidence_type: EvidenceType,
        strength: EvidenceStrength = EvidenceStrength.MODERATE,
        supports: bool = True,
        source: str = ""
    ) -> Evidence:
        """Collect new evidence."""
        likelihood_ratio = self._compute_likelihood_ratio(strength, supports)

        evidence = Evidence(
            description=description,
            evidence_type=evidence_type,
            strength=strength,
            supports=supports,
            likelihood_ratio=likelihood_ratio,
            source=source
        )

        self._evidence[evidence.evidence_id] = evidence

        return evidence

    def _compute_likelihood_ratio(
        self,
        strength: EvidenceStrength,
        supports: bool
    ) -> float:
        """Compute likelihood ratio for evidence."""
        base_ratios = {
            EvidenceStrength.WEAK: 1.5,
            EvidenceStrength.MODERATE: 3.0,
            EvidenceStrength.STRONG: 10.0,
            EvidenceStrength.DECISIVE: 100.0
        }

        ratio = base_ratios.get(strength, 2.0)

        if not supports:
            ratio = 1.0 / ratio

        return ratio

    def link_to_hypothesis(
        self,
        evidence_id: str,
        hypothesis_id: str
    ) -> bool:
        """Link evidence to hypothesis."""
        if evidence_id not in self._evidence:
            return False

        self._by_hypothesis[hypothesis_id].append(evidence_id)

        return True

    def get(self, evidence_id: str) -> Optional[Evidence]:
        """Get evidence by ID."""
        return self._evidence.get(evidence_id)

    def get_for_hypothesis(self, hypothesis_id: str) -> List[Evidence]:
        """Get evidence for hypothesis."""
        evidence_ids = self._by_hypothesis.get(hypothesis_id, [])
        return [
            self._evidence[eid]
            for eid in evidence_ids
            if eid in self._evidence
        ]

    def get_supporting(self, hypothesis_id: str) -> List[Evidence]:
        """Get supporting evidence."""
        all_evidence = self.get_for_hypothesis(hypothesis_id)
        return [e for e in all_evidence if e.supports]

    def get_opposing(self, hypothesis_id: str) -> List[Evidence]:
        """Get opposing evidence."""
        all_evidence = self.get_for_hypothesis(hypothesis_id)
        return [e for e in all_evidence if not e.supports]

    def get_by_type(self, evidence_type: EvidenceType) -> List[Evidence]:
        """Get evidence by type."""
        return [
            e for e in self._evidence.values()
            if e.evidence_type == evidence_type
        ]

    def count(self) -> int:
        """Count evidence."""
        return len(self._evidence)

    def all(self) -> List[Evidence]:
        """Get all evidence."""
        return list(self._evidence.values())


# =============================================================================
# HYPOTHESIS TESTER
# =============================================================================

class HypothesisTester:
    """Test hypotheses against evidence."""

    def __init__(
        self,
        confirmation_threshold: float = 0.8,
        rejection_threshold: float = 0.2,
        min_evidence: int = 3
    ):
        self._tests: Dict[str, Test] = {}
        self._confirmation_threshold = confirmation_threshold
        self._rejection_threshold = rejection_threshold
        self._min_evidence = min_evidence

    def create_test(
        self,
        hypothesis_id: str,
        test_type: TestType,
        prediction: str
    ) -> Test:
        """Create a hypothesis test."""
        test = Test(
            hypothesis_id=hypothesis_id,
            test_type=test_type,
            prediction=prediction
        )

        self._tests[test.test_id] = test

        return test

    def execute_test(
        self,
        test_id: str,
        observation: str,
        matches_prediction: bool
    ) -> Test:
        """Execute a test with observation."""
        test = self._tests.get(test_id)

        if not test:
            raise ValueError(f"Test not found: {test_id}")

        test.observation = observation
        test.result = matches_prediction
        test.executed_at = datetime.now()

        if matches_prediction:
            test.confidence = min(1.0, test.confidence + 0.2)
        else:
            test.confidence = max(0.0, test.confidence - 0.3)

        return test

    def update_probability(
        self,
        hypothesis: Hypothesis,
        evidence: List[Evidence]
    ) -> float:
        """Update hypothesis probability with Bayesian update."""
        prior = hypothesis.prior_probability

        posterior = prior

        for e in evidence:
            odds = posterior / (1 - posterior) if posterior < 1 else 1000

            new_odds = odds * e.likelihood_ratio

            posterior = new_odds / (1 + new_odds)

        hypothesis.posterior_probability = posterior

        return posterior

    def evaluate_hypothesis(
        self,
        hypothesis: Hypothesis,
        evidence: List[Evidence]
    ) -> HypothesisStatus:
        """Evaluate hypothesis status."""
        if len(evidence) < self._min_evidence:
            hypothesis.status = HypothesisStatus.TESTING
            return hypothesis.status

        self.update_probability(hypothesis, evidence)

        if hypothesis.posterior_probability >= self._confirmation_threshold:
            hypothesis.status = HypothesisStatus.SUPPORTED
        elif hypothesis.posterior_probability <= self._rejection_threshold:
            hypothesis.status = HypothesisStatus.REJECTED
        else:
            hypothesis.status = HypothesisStatus.INCONCLUSIVE

        return hypothesis.status

    def compute_confidence(
        self,
        hypothesis: Hypothesis,
        evidence: List[Evidence]
    ) -> float:
        """Compute confidence in hypothesis."""
        if not evidence:
            return 0.0

        evidence_factor = min(1.0, len(evidence) / self._min_evidence)

        strengths = [e.strength.value for e in evidence]
        avg_strength = sum(strengths) / len(strengths)
        strength_factor = avg_strength / 4.0

        prob_factor = 2 * abs(hypothesis.posterior_probability - 0.5)

        confidence = (evidence_factor + strength_factor + prob_factor) / 3

        hypothesis.confidence = confidence

        return confidence

    def get_test(self, test_id: str) -> Optional[Test]:
        """Get test by ID."""
        return self._tests.get(test_id)

    def get_tests_for_hypothesis(self, hypothesis_id: str) -> List[Test]:
        """Get tests for hypothesis."""
        return [
            t for t in self._tests.values()
            if t.hypothesis_id == hypothesis_id
        ]

    def count(self) -> int:
        """Count tests."""
        return len(self._tests)


# =============================================================================
# THEORY BUILDER
# =============================================================================

class TheoryBuilder:
    """Build theories from hypotheses."""

    def __init__(self):
        self._theories: Dict[str, Theory] = {}

    def create_theory(
        self,
        name: str,
        description: str,
        hypotheses: List[Hypothesis]
    ) -> Theory:
        """Create a theory from hypotheses."""
        hypothesis_ids = [h.hypothesis_id for h in hypotheses]

        coherence = self._compute_coherence(hypotheses)
        explanatory_power = self._compute_explanatory_power(hypotheses)

        theory = Theory(
            name=name,
            description=description,
            hypothesis_ids=hypothesis_ids,
            coherence=coherence,
            explanatory_power=explanatory_power
        )

        self._theories[theory.theory_id] = theory

        return theory

    def _compute_coherence(self, hypotheses: List[Hypothesis]) -> float:
        """Compute theory coherence."""
        if not hypotheses:
            return 0.0

        supported = sum(
            1 for h in hypotheses
            if h.status == HypothesisStatus.SUPPORTED
        )

        inconclusive = sum(
            1 for h in hypotheses
            if h.status == HypothesisStatus.INCONCLUSIVE
        )

        rejected = sum(
            1 for h in hypotheses
            if h.status == HypothesisStatus.REJECTED
        )

        total = len(hypotheses)

        coherence = (supported + 0.5 * inconclusive - rejected) / total

        return max(0.0, min(1.0, coherence))

    def _compute_explanatory_power(self, hypotheses: List[Hypothesis]) -> float:
        """Compute explanatory power."""
        if not hypotheses:
            return 0.0

        avg_probability = sum(
            h.posterior_probability for h in hypotheses
        ) / len(hypotheses)

        type_diversity = len(set(h.hypothesis_type for h in hypotheses)) / len(HypothesisType)

        return (avg_probability + type_diversity) / 2

    def add_hypothesis_to_theory(
        self,
        theory_id: str,
        hypothesis: Hypothesis
    ) -> Optional[Theory]:
        """Add hypothesis to existing theory."""
        theory = self._theories.get(theory_id)

        if not theory:
            return None

        if hypothesis.hypothesis_id not in theory.hypothesis_ids:
            theory.hypothesis_ids.append(hypothesis.hypothesis_id)

        return theory

    def evaluate_theory(
        self,
        theory_id: str,
        hypotheses: Dict[str, Hypothesis]
    ) -> Tuple[float, float]:
        """Evaluate theory coherence and power."""
        theory = self._theories.get(theory_id)

        if not theory:
            return 0.0, 0.0

        theory_hypotheses = [
            hypotheses[hid]
            for hid in theory.hypothesis_ids
            if hid in hypotheses
        ]

        theory.coherence = self._compute_coherence(theory_hypotheses)
        theory.explanatory_power = self._compute_explanatory_power(theory_hypotheses)

        return theory.coherence, theory.explanatory_power

    def get(self, theory_id: str) -> Optional[Theory]:
        """Get theory by ID."""
        return self._theories.get(theory_id)

    def get_best_theory(self) -> Optional[Theory]:
        """Get theory with highest score."""
        if not self._theories:
            return None

        return max(
            self._theories.values(),
            key=lambda t: (t.coherence + t.explanatory_power) / 2
        )

    def count(self) -> int:
        """Count theories."""
        return len(self._theories)

    def all(self) -> List[Theory]:
        """Get all theories."""
        return list(self._theories.values())


# =============================================================================
# HYPOTHESIS ENGINE
# =============================================================================

class HypothesisEngine:
    """
    Hypothesis Engine for BAEL.

    Hypothesis generation and testing.
    """

    def __init__(self, config: Optional[HypothesisConfig] = None):
        self._config = config or HypothesisConfig()

        self._generator = HypothesisGenerator(self._config.prior_default)
        self._evidence = EvidenceCollector()
        self._tester = HypothesisTester(
            confirmation_threshold=self._config.confirmation_threshold,
            rejection_threshold=self._config.rejection_threshold,
            min_evidence=self._config.min_evidence_count
        )
        self._theory_builder = TheoryBuilder()

    # ----- Hypothesis Operations -----

    def generate(
        self,
        statement: str,
        hypothesis_type: HypothesisType,
        prior: Optional[float] = None
    ) -> Hypothesis:
        """Generate a hypothesis."""
        return self._generator.generate(statement, hypothesis_type, prior)

    def generate_causal(
        self,
        cause: str,
        effect: str
    ) -> Hypothesis:
        """Generate causal hypothesis."""
        return self._generator.generate_causal(cause, effect)

    def generate_predictive(
        self,
        conditions: str,
        outcome: str
    ) -> Hypothesis:
        """Generate predictive hypothesis."""
        return self._generator.generate_predictive(conditions, outcome)

    def generate_alternatives(
        self,
        observation: str,
        count: int = 3
    ) -> List[Hypothesis]:
        """Generate alternative hypotheses."""
        return self._generator.generate_alternatives(observation, count)

    def get_hypothesis(self, hypothesis_id: str) -> Optional[Hypothesis]:
        """Get hypothesis by ID."""
        return self._generator.get(hypothesis_id)

    def get_hypotheses_by_status(
        self,
        status: HypothesisStatus
    ) -> List[Hypothesis]:
        """Get hypotheses by status."""
        return self._generator.get_by_status(status)

    # ----- Evidence Operations -----

    def collect_evidence(
        self,
        hypothesis_id: str,
        description: str,
        evidence_type: EvidenceType,
        strength: EvidenceStrength = EvidenceStrength.MODERATE,
        supports: bool = True
    ) -> Evidence:
        """Collect evidence for hypothesis."""
        evidence = self._evidence.collect(
            description=description,
            evidence_type=evidence_type,
            strength=strength,
            supports=supports
        )

        self._evidence.link_to_hypothesis(evidence.evidence_id, hypothesis_id)

        hypothesis = self._generator.get(hypothesis_id)
        if hypothesis:
            hypothesis.evidence_ids.append(evidence.evidence_id)

        return evidence

    def get_evidence(self, evidence_id: str) -> Optional[Evidence]:
        """Get evidence by ID."""
        return self._evidence.get(evidence_id)

    def get_evidence_for_hypothesis(
        self,
        hypothesis_id: str
    ) -> List[Evidence]:
        """Get evidence for hypothesis."""
        return self._evidence.get_for_hypothesis(hypothesis_id)

    def get_supporting_evidence(
        self,
        hypothesis_id: str
    ) -> List[Evidence]:
        """Get supporting evidence."""
        return self._evidence.get_supporting(hypothesis_id)

    def get_opposing_evidence(
        self,
        hypothesis_id: str
    ) -> List[Evidence]:
        """Get opposing evidence."""
        return self._evidence.get_opposing(hypothesis_id)

    # ----- Testing Operations -----

    def create_test(
        self,
        hypothesis_id: str,
        prediction: str,
        test_type: TestType = TestType.CONFIRMATION
    ) -> Test:
        """Create a test for hypothesis."""
        return self._tester.create_test(hypothesis_id, test_type, prediction)

    def run_test(
        self,
        test_id: str,
        observation: str,
        matches: bool
    ) -> Test:
        """Run a test with observation."""
        return self._tester.execute_test(test_id, observation, matches)

    def evaluate(self, hypothesis_id: str) -> HypothesisStatus:
        """Evaluate hypothesis status."""
        hypothesis = self._generator.get(hypothesis_id)

        if not hypothesis:
            raise ValueError(f"Hypothesis not found: {hypothesis_id}")

        evidence = self._evidence.get_for_hypothesis(hypothesis_id)

        self._tester.compute_confidence(hypothesis, evidence)

        return self._tester.evaluate_hypothesis(hypothesis, evidence)

    def update_probability(self, hypothesis_id: str) -> float:
        """Update hypothesis probability."""
        hypothesis = self._generator.get(hypothesis_id)

        if not hypothesis:
            return 0.0

        evidence = self._evidence.get_for_hypothesis(hypothesis_id)

        return self._tester.update_probability(hypothesis, evidence)

    def get_confidence(self, hypothesis_id: str) -> float:
        """Get hypothesis confidence."""
        hypothesis = self._generator.get(hypothesis_id)

        if not hypothesis:
            return 0.0

        return hypothesis.confidence

    # ----- Theory Operations -----

    def create_theory(
        self,
        name: str,
        description: str,
        hypothesis_ids: List[str]
    ) -> Theory:
        """Create a theory from hypotheses."""
        hypotheses = [
            self._generator.get(hid)
            for hid in hypothesis_ids
            if self._generator.get(hid) is not None
        ]

        return self._theory_builder.create_theory(name, description, hypotheses)

    def get_theory(self, theory_id: str) -> Optional[Theory]:
        """Get theory by ID."""
        return self._theory_builder.get(theory_id)

    def get_best_theory(self) -> Optional[Theory]:
        """Get best theory."""
        return self._theory_builder.get_best_theory()

    def evaluate_theory(self, theory_id: str) -> Tuple[float, float]:
        """Evaluate theory."""
        hypotheses = {h.hypothesis_id: h for h in self._generator.all()}
        return self._theory_builder.evaluate_theory(theory_id, hypotheses)

    # ----- Ranking Operations -----

    def rank_hypotheses(self) -> List[Tuple[Hypothesis, float]]:
        """Rank hypotheses by score."""
        hypotheses = self._generator.all()

        scored = []

        for h in hypotheses:
            score = (
                h.posterior_probability * 0.5 +
                h.confidence * 0.3 +
                (1.0 if h.status == HypothesisStatus.SUPPORTED else 0.5) * 0.2
            )
            scored.append((h, score))

        scored.sort(key=lambda x: x[1], reverse=True)

        return scored

    def get_top_hypotheses(self, n: int = 5) -> List[Hypothesis]:
        """Get top n hypotheses."""
        ranked = self.rank_hypotheses()
        return [h for h, _ in ranked[:n]]

    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        hypotheses = self._generator.all()

        by_status = defaultdict(int)
        for h in hypotheses:
            by_status[h.status.value] += 1

        return {
            "total_hypotheses": len(hypotheses),
            "by_status": dict(by_status),
            "total_evidence": self._evidence.count(),
            "total_tests": self._tester.count(),
            "total_theories": self._theory_builder.count()
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Hypothesis Engine."""
    print("=" * 70)
    print("BAEL - HYPOTHESIS ENGINE DEMO")
    print("Hypothesis Generation and Testing")
    print("=" * 70)
    print()

    engine = HypothesisEngine()

    # 1. Generate Hypotheses
    print("1. GENERATE HYPOTHESES:")
    print("-" * 40)

    h1 = engine.generate(
        "Increased temperature causes faster reaction rates",
        HypothesisType.CAUSAL,
        prior=0.6
    )

    print(f"   H1: {h1.statement}")
    print(f"   Type: {h1.hypothesis_type.value}")
    print(f"   Prior: {h1.prior_probability:.2f}")
    print()

    # 2. Generate Causal Hypothesis
    print("2. GENERATE CAUSAL HYPOTHESIS:")
    print("-" * 40)

    h2 = engine.generate_causal(
        "high user engagement",
        "increased conversion rates"
    )

    print(f"   H2: {h2.statement}")
    print(f"   Status: {h2.status.value}")
    print()

    # 3. Generate Predictive Hypothesis
    print("3. GENERATE PREDICTIVE HYPOTHESIS:")
    print("-" * 40)

    h3 = engine.generate_predictive(
        "rain and cold temperatures",
        "decreased outdoor activity"
    )

    print(f"   H3: {h3.statement}")
    print()

    # 4. Generate Alternatives
    print("4. GENERATE ALTERNATIVES:")
    print("-" * 40)

    alternatives = engine.generate_alternatives(
        "system performance degradation",
        count=3
    )

    for i, alt in enumerate(alternatives, 1):
        print(f"   Alt {i}: {alt.statement[:50]}...")
    print()

    # 5. Collect Evidence
    print("5. COLLECT EVIDENCE:")
    print("-" * 40)

    e1 = engine.collect_evidence(
        h1.hypothesis_id,
        "Experiment showed 2x reaction speed at higher temp",
        EvidenceType.EXPERIMENT,
        EvidenceStrength.STRONG,
        supports=True
    )

    e2 = engine.collect_evidence(
        h1.hypothesis_id,
        "Literature review supports temperature-reaction relationship",
        EvidenceType.PRIOR_KNOWLEDGE,
        EvidenceStrength.MODERATE,
        supports=True
    )

    e3 = engine.collect_evidence(
        h1.hypothesis_id,
        "Control experiment validated results",
        EvidenceType.EXPERIMENT,
        EvidenceStrength.STRONG,
        supports=True
    )

    print(f"   Evidence 1: {e1.description[:40]}...")
    print(f"     Type: {e1.evidence_type.value}")
    print(f"     Strength: {e1.strength.name}")
    print(f"     Supports: {e1.supports}")
    print(f"   Total evidence for H1: {len(engine.get_evidence_for_hypothesis(h1.hypothesis_id))}")
    print()

    # 6. Create Test
    print("6. CREATE AND RUN TEST:")
    print("-" * 40)

    test = engine.create_test(
        h1.hypothesis_id,
        "At 50°C, reaction should be 3x faster than at 25°C"
    )

    print(f"   Test: {test.prediction}")

    engine.run_test(
        test.test_id,
        "Observed 2.8x faster reaction at 50°C",
        matches=True
    )

    print(f"   Observation: {test.observation}")
    print(f"   Result: {'Passed' if test.result else 'Failed'}")
    print()

    # 7. Update Probability
    print("7. UPDATE PROBABILITY:")
    print("-" * 40)

    print(f"   Prior probability: {h1.prior_probability:.2f}")

    new_prob = engine.update_probability(h1.hypothesis_id)

    print(f"   Posterior probability: {new_prob:.2f}")
    print()

    # 8. Evaluate Hypothesis
    print("8. EVALUATE HYPOTHESIS:")
    print("-" * 40)

    status = engine.evaluate(h1.hypothesis_id)

    print(f"   Status: {status.value}")
    print(f"   Confidence: {h1.confidence:.2f}")
    print()

    # 9. Add Evidence to H2
    print("9. ADD EVIDENCE TO H2:")
    print("-" * 40)

    engine.collect_evidence(
        h2.hypothesis_id,
        "A/B test showed 15% higher conversion with engagement features",
        EvidenceType.EXPERIMENT,
        EvidenceStrength.STRONG,
        supports=True
    )

    engine.collect_evidence(
        h2.hypothesis_id,
        "User surveys confirm engagement-conversion link",
        EvidenceType.TESTIMONY,
        EvidenceStrength.MODERATE,
        supports=True
    )

    engine.collect_evidence(
        h2.hypothesis_id,
        "Industry research supports hypothesis",
        EvidenceType.PRIOR_KNOWLEDGE,
        EvidenceStrength.MODERATE,
        supports=True
    )

    engine.evaluate(h2.hypothesis_id)

    print(f"   H2 posterior: {h2.posterior_probability:.2f}")
    print(f"   H2 status: {h2.status.value}")
    print()

    # 10. Get Supporting/Opposing Evidence
    print("10. EVIDENCE ANALYSIS:")
    print("-" * 40)

    supporting = engine.get_supporting_evidence(h1.hypothesis_id)
    opposing = engine.get_opposing_evidence(h1.hypothesis_id)

    print(f"   Supporting evidence: {len(supporting)}")
    print(f"   Opposing evidence: {len(opposing)}")
    print()

    # 11. Create Theory
    print("11. CREATE THEORY:")
    print("-" * 40)

    theory = engine.create_theory(
        "Engagement-Conversion Theory",
        "Theory explaining the relationship between user engagement and business outcomes",
        [h1.hypothesis_id, h2.hypothesis_id]
    )

    print(f"   Theory: {theory.name}")
    print(f"   Hypotheses: {len(theory.hypothesis_ids)}")
    print(f"   Coherence: {theory.coherence:.2f}")
    print(f"   Explanatory Power: {theory.explanatory_power:.2f}")
    print()

    # 12. Evaluate Theory
    print("12. EVALUATE THEORY:")
    print("-" * 40)

    coherence, power = engine.evaluate_theory(theory.theory_id)

    print(f"   Coherence: {coherence:.2f}")
    print(f"   Explanatory Power: {power:.2f}")
    print()

    # 13. Rank Hypotheses
    print("13. RANK HYPOTHESES:")
    print("-" * 40)

    top = engine.get_top_hypotheses(3)

    for i, h in enumerate(top, 1):
        print(f"   {i}. {h.statement[:40]}...")
        print(f"      Prob: {h.posterior_probability:.2f}, Status: {h.status.value}")
    print()

    # 14. Get by Status
    print("14. GET BY STATUS:")
    print("-" * 40)

    supported = engine.get_hypotheses_by_status(HypothesisStatus.SUPPORTED)
    proposed = engine.get_hypotheses_by_status(HypothesisStatus.PROPOSED)

    print(f"   Supported: {len(supported)}")
    print(f"   Proposed: {len(proposed)}")
    print()

    # 15. Summary
    print("15. ENGINE SUMMARY:")
    print("-" * 40)

    summary = engine.summary()

    for key, value in summary.items():
        print(f"   {key}: {value}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Hypothesis Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
