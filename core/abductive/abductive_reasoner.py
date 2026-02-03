#!/usr/bin/env python3
"""
BAEL - Abductive Reasoner
Advanced abductive inference and explanation generation.

Features:
- Best explanation generation
- Hypothesis generation
- Evidence evaluation
- Explanation ranking
- Consistency checking
- Plausibility scoring
- Occam's razor application
- Multiple hypothesis tracking
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

class HypothesisStatus(Enum):
    """Status of a hypothesis."""
    ACTIVE = "active"
    CONFIRMED = "confirmed"
    REFUTED = "refuted"
    SUSPENDED = "suspended"


class EvidenceType(Enum):
    """Types of evidence."""
    OBSERVATION = "observation"
    TESTIMONY = "testimony"
    INFERENCE = "inference"
    EXPERIMENT = "experiment"


class ExplanationType(Enum):
    """Types of explanations."""
    CAUSAL = "causal"
    FUNCTIONAL = "functional"
    COMPOSITIONAL = "compositional"
    ANALOGICAL = "analogical"


class RankingCriterion(Enum):
    """Criteria for ranking explanations."""
    SIMPLICITY = "simplicity"  # Occam's razor
    LIKELIHOOD = "likelihood"  # P(evidence | hypothesis)
    COHERENCE = "coherence"  # Fits with background
    SCOPE = "scope"  # Explains more observations
    FERTILITY = "fertility"  # Generates new predictions


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Evidence:
    """A piece of evidence."""
    evidence_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    evidence_type: EvidenceType = EvidenceType.OBSERVATION
    reliability: float = 1.0
    timestamp: float = field(default_factory=time.time)
    source: str = ""


@dataclass
class Hypothesis:
    """A hypothesis to explain evidence."""
    hypothesis_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    status: HypothesisStatus = HypothesisStatus.ACTIVE
    prior_probability: float = 0.5
    explained_evidence: List[str] = field(default_factory=list)
    unexplained_evidence: List[str] = field(default_factory=list)
    predictions: List[str] = field(default_factory=list)
    complexity: int = 1


@dataclass
class Explanation:
    """An explanation of evidence."""
    explanation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    hypothesis: Hypothesis = field(default_factory=Hypothesis)
    explanation_type: ExplanationType = ExplanationType.CAUSAL
    confidence: float = 0.0
    reasoning: str = ""
    assumptions: List[str] = field(default_factory=list)


@dataclass
class RankingResult:
    """Result of explanation ranking."""
    result_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    ranked_explanations: List[Tuple[Explanation, float]] = field(default_factory=list)
    criterion: RankingCriterion = RankingCriterion.LIKELIHOOD
    best_explanation: Optional[Explanation] = None


# =============================================================================
# HYPOTHESIS GENERATOR
# =============================================================================

class HypothesisGenerator:
    """Generate hypotheses from evidence."""

    def __init__(self):
        self._patterns: Dict[str, List[str]] = {}
        self._domain_knowledge: Dict[str, List[str]] = {}
        self._initialize_patterns()

    def _initialize_patterns(self) -> None:
        """Initialize explanation patterns."""
        # Causal patterns
        self._patterns["effect"] = [
            "caused by {cause}",
            "result of {cause}",
            "due to {cause}"
        ]

        # Functional patterns
        self._patterns["behavior"] = [
            "intended to {goal}",
            "functions as {function}",
            "designed for {purpose}"
        ]

        # State patterns
        self._patterns["state"] = [
            "is in state {state}",
            "has property {property}",
            "exhibits {characteristic}"
        ]

        # Common domain knowledge
        self._domain_knowledge["physical"] = [
            "gravity", "friction", "heat", "pressure",
            "collision", "force", "energy", "momentum"
        ]
        self._domain_knowledge["biological"] = [
            "disease", "infection", "mutation", "adaptation",
            "metabolism", "growth", "decay"
        ]
        self._domain_knowledge["psychological"] = [
            "motivation", "fear", "desire", "belief",
            "intention", "memory", "learning"
        ]

    def generate(
        self,
        evidence: Evidence,
        domain: str = "physical"
    ) -> List[Hypothesis]:
        """Generate hypotheses to explain evidence."""
        hypotheses = []

        # Extract key terms from evidence
        terms = evidence.content.lower().split()

        # Generate causal hypotheses
        causes = self._domain_knowledge.get(domain, [])
        for cause in causes:
            if self._is_relevant(cause, terms):
                h = Hypothesis(
                    content=f"{evidence.content} caused by {cause}",
                    prior_probability=0.3,
                    explained_evidence=[evidence.evidence_id],
                    complexity=1
                )
                hypotheses.append(h)

        # Generate state hypotheses
        for term in terms[:3]:  # Focus on first few terms
            h = Hypothesis(
                content=f"Entity is in {term} state",
                prior_probability=0.2,
                explained_evidence=[evidence.evidence_id],
                complexity=1
            )
            hypotheses.append(h)

        return hypotheses[:5]  # Return top 5

    def _is_relevant(self, cause: str, terms: List[str]) -> bool:
        """Check if cause is relevant to terms."""
        # Simple relevance check
        relevant_pairs = {
            ("fall", "gravity"),
            ("heat", "temperature"),
            ("move", "force"),
            ("sick", "disease"),
            ("forgot", "memory"),
            ("afraid", "fear")
        }

        for term in terms:
            for pair in relevant_pairs:
                if term in pair and cause in pair:
                    return True

        # Default: some probability of relevance
        return random.random() < 0.3

    def generate_combined(
        self,
        evidence_list: List[Evidence],
        domain: str = "physical"
    ) -> List[Hypothesis]:
        """Generate hypotheses that explain multiple evidence."""
        # Generate individual hypotheses
        all_hypotheses = []
        for ev in evidence_list:
            all_hypotheses.extend(self.generate(ev, domain))

        # Try to find common causes
        combined = []
        cause_counts: Dict[str, List[Hypothesis]] = defaultdict(list)

        for h in all_hypotheses:
            # Extract cause from hypothesis
            for cause in self._domain_knowledge.get(domain, []):
                if cause in h.content.lower():
                    cause_counts[cause].append(h)

        # Create combined hypotheses for causes explaining multiple evidence
        for cause, hyps in cause_counts.items():
            if len(hyps) > 1:
                combined_h = Hypothesis(
                    content=f"Common cause: {cause}",
                    prior_probability=0.4,
                    explained_evidence=[
                        ev_id
                        for h in hyps
                        for ev_id in h.explained_evidence
                    ],
                    complexity=1  # Simpler because it's unified
                )
                combined.append(combined_h)

        return combined + all_hypotheses


# =============================================================================
# EVIDENCE EVALUATOR
# =============================================================================

class EvidenceEvaluator:
    """Evaluate evidence for hypotheses."""

    def __init__(self):
        self._evidence_weights: Dict[EvidenceType, float] = {
            EvidenceType.OBSERVATION: 1.0,
            EvidenceType.EXPERIMENT: 0.95,
            EvidenceType.INFERENCE: 0.7,
            EvidenceType.TESTIMONY: 0.6
        }

    def likelihood(
        self,
        evidence: Evidence,
        hypothesis: Hypothesis
    ) -> float:
        """Compute P(evidence | hypothesis)."""
        # Base likelihood from evidence type
        base = self._evidence_weights.get(evidence.evidence_type, 0.5)

        # Adjust by reliability
        base *= evidence.reliability

        # Check if evidence is explained by hypothesis
        if evidence.evidence_id in hypothesis.explained_evidence:
            return min(base * 1.5, 1.0)

        # Check content similarity
        similarity = self._content_similarity(evidence.content, hypothesis.content)

        return base * (0.5 + 0.5 * similarity)

    def _content_similarity(self, text1: str, text2: str) -> float:
        """Compute simple content similarity."""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0

    def supports(
        self,
        evidence: Evidence,
        hypothesis: Hypothesis
    ) -> Tuple[bool, float]:
        """Check if evidence supports hypothesis."""
        likelihood = self.likelihood(evidence, hypothesis)

        if likelihood > 0.7:
            return True, likelihood
        elif likelihood < 0.3:
            return False, 1 - likelihood  # Strength of contradiction
        else:
            return True, 0.5  # Neutral

    def contradicts(
        self,
        evidence: Evidence,
        hypothesis: Hypothesis
    ) -> Tuple[bool, str]:
        """Check if evidence contradicts hypothesis."""
        # Simple contradiction check based on negation patterns
        negations = ["not", "no", "never", "without", "lack"]

        ev_words = evidence.content.lower().split()
        hyp_words = hypothesis.content.lower().split()

        for neg in negations:
            if neg in ev_words and neg not in hyp_words:
                # Check if they share key terms
                shared = set(ev_words) & set(hyp_words) - set(negations)
                if shared:
                    return True, f"Evidence negates key term: {shared}"

        return False, ""


# =============================================================================
# EXPLANATION RANKER
# =============================================================================

class ExplanationRanker:
    """Rank explanations by various criteria."""

    def __init__(self):
        self._criterion_weights: Dict[RankingCriterion, float] = {
            RankingCriterion.SIMPLICITY: 0.25,
            RankingCriterion.LIKELIHOOD: 0.35,
            RankingCriterion.COHERENCE: 0.20,
            RankingCriterion.SCOPE: 0.15,
            RankingCriterion.FERTILITY: 0.05
        }

    def rank(
        self,
        explanations: List[Explanation],
        criterion: RankingCriterion = RankingCriterion.LIKELIHOOD
    ) -> RankingResult:
        """Rank explanations by criterion."""
        scored = []

        for exp in explanations:
            score = self._compute_score(exp, criterion)
            scored.append((exp, score))

        scored.sort(key=lambda x: x[1], reverse=True)

        return RankingResult(
            ranked_explanations=scored,
            criterion=criterion,
            best_explanation=scored[0][0] if scored else None
        )

    def rank_combined(
        self,
        explanations: List[Explanation]
    ) -> RankingResult:
        """Rank by weighted combination of criteria."""
        scored = []

        for exp in explanations:
            total_score = 0.0
            for criterion, weight in self._criterion_weights.items():
                total_score += weight * self._compute_score(exp, criterion)
            scored.append((exp, total_score))

        scored.sort(key=lambda x: x[1], reverse=True)

        return RankingResult(
            ranked_explanations=scored,
            best_explanation=scored[0][0] if scored else None
        )

    def _compute_score(
        self,
        explanation: Explanation,
        criterion: RankingCriterion
    ) -> float:
        """Compute score for a single criterion."""
        if criterion == RankingCriterion.SIMPLICITY:
            # Occam's razor: simpler is better
            complexity = explanation.hypothesis.complexity
            return 1.0 / (1.0 + complexity * 0.3)

        elif criterion == RankingCriterion.LIKELIHOOD:
            return explanation.confidence

        elif criterion == RankingCriterion.COHERENCE:
            # Based on number of assumptions
            num_assumptions = len(explanation.assumptions)
            return 1.0 / (1.0 + num_assumptions * 0.2)

        elif criterion == RankingCriterion.SCOPE:
            # Based on evidence explained
            num_explained = len(explanation.hypothesis.explained_evidence)
            return min(num_explained * 0.2, 1.0)

        elif criterion == RankingCriterion.FERTILITY:
            # Based on predictions
            num_predictions = len(explanation.hypothesis.predictions)
            return min(num_predictions * 0.15, 1.0)

        return 0.5


# =============================================================================
# CONSISTENCY CHECKER
# =============================================================================

class ConsistencyChecker:
    """Check consistency of hypotheses."""

    def __init__(self):
        self._contradiction_rules: List[Tuple[str, str]] = [
            ("alive", "dead"),
            ("present", "absent"),
            ("true", "false"),
            ("hot", "cold"),
            ("wet", "dry"),
            ("full", "empty")
        ]

    def is_consistent(
        self,
        hypothesis1: Hypothesis,
        hypothesis2: Hypothesis
    ) -> Tuple[bool, str]:
        """Check if two hypotheses are consistent."""
        words1 = hypothesis1.content.lower().split()
        words2 = hypothesis2.content.lower().split()

        for word1, word2 in self._contradiction_rules:
            if word1 in words1 and word2 in words2:
                return False, f"Contradiction: {word1} vs {word2}"
            if word2 in words1 and word1 in words2:
                return False, f"Contradiction: {word2} vs {word1}"

        return True, "No contradiction found"

    def find_inconsistencies(
        self,
        hypotheses: List[Hypothesis]
    ) -> List[Tuple[Hypothesis, Hypothesis, str]]:
        """Find all inconsistencies among hypotheses."""
        inconsistencies = []

        for i, h1 in enumerate(hypotheses):
            for h2 in hypotheses[i+1:]:
                consistent, reason = self.is_consistent(h1, h2)
                if not consistent:
                    inconsistencies.append((h1, h2, reason))

        return inconsistencies

    def is_self_consistent(
        self,
        hypothesis: Hypothesis
    ) -> Tuple[bool, str]:
        """Check if hypothesis is internally consistent."""
        words = hypothesis.content.lower().split()

        for word1, word2 in self._contradiction_rules:
            if word1 in words and word2 in words:
                return False, f"Self-contradiction: {word1} and {word2}"

        return True, "Self-consistent"


# =============================================================================
# HYPOTHESIS TRACKER
# =============================================================================

class HypothesisTracker:
    """Track and manage multiple hypotheses."""

    def __init__(self, max_hypotheses: int = 10):
        self._hypotheses: Dict[str, Hypothesis] = {}
        self._max = max_hypotheses
        self._consistency_checker = ConsistencyChecker()

    def add(self, hypothesis: Hypothesis) -> bool:
        """Add a hypothesis to tracking."""
        # Check consistency with existing
        for existing in self._hypotheses.values():
            consistent, _ = self._consistency_checker.is_consistent(hypothesis, existing)
            if not consistent:
                # Can still add but mark potential conflict
                pass

        if len(self._hypotheses) >= self._max:
            # Remove lowest probability hypothesis
            lowest = min(
                self._hypotheses.values(),
                key=lambda h: h.prior_probability
            )
            del self._hypotheses[lowest.hypothesis_id]

        self._hypotheses[hypothesis.hypothesis_id] = hypothesis
        return True

    def update_probability(
        self,
        hypothesis_id: str,
        evidence: Evidence,
        evaluator: EvidenceEvaluator
    ) -> None:
        """Update hypothesis probability given new evidence."""
        hypothesis = self._hypotheses.get(hypothesis_id)
        if not hypothesis:
            return

        # Simple Bayesian update
        likelihood = evaluator.likelihood(evidence, hypothesis)

        # P(H|E) ∝ P(E|H) * P(H)
        new_prob = likelihood * hypothesis.prior_probability

        # Normalize (simplified)
        hypothesis.prior_probability = min(new_prob * 2, 0.99)

    def get_active(self) -> List[Hypothesis]:
        """Get active hypotheses."""
        return [
            h for h in self._hypotheses.values()
            if h.status == HypothesisStatus.ACTIVE
        ]

    def confirm(self, hypothesis_id: str) -> None:
        """Confirm a hypothesis."""
        h = self._hypotheses.get(hypothesis_id)
        if h:
            h.status = HypothesisStatus.CONFIRMED

    def refute(self, hypothesis_id: str) -> None:
        """Refute a hypothesis."""
        h = self._hypotheses.get(hypothesis_id)
        if h:
            h.status = HypothesisStatus.REFUTED

    def get_best(self) -> Optional[Hypothesis]:
        """Get best hypothesis by probability."""
        active = self.get_active()
        if not active:
            return None
        return max(active, key=lambda h: h.prior_probability)


# =============================================================================
# ABDUCTIVE REASONER
# =============================================================================

class AbductiveReasoner:
    """
    Abductive Reasoner for BAEL.

    Advanced abductive inference and explanation generation.
    """

    def __init__(self):
        self._evidence: Dict[str, Evidence] = {}
        self._generator = HypothesisGenerator()
        self._evaluator = EvidenceEvaluator()
        self._ranker = ExplanationRanker()
        self._consistency = ConsistencyChecker()
        self._tracker = HypothesisTracker()

    # -------------------------------------------------------------------------
    # EVIDENCE MANAGEMENT
    # -------------------------------------------------------------------------

    def add_evidence(
        self,
        content: str,
        evidence_type: EvidenceType = EvidenceType.OBSERVATION,
        reliability: float = 1.0,
        source: str = ""
    ) -> Evidence:
        """Add evidence."""
        evidence = Evidence(
            content=content,
            evidence_type=evidence_type,
            reliability=reliability,
            source=source
        )
        self._evidence[evidence.evidence_id] = evidence
        return evidence

    def get_evidence(self, evidence_id: str) -> Optional[Evidence]:
        """Get evidence by ID."""
        return self._evidence.get(evidence_id)

    def get_all_evidence(self) -> List[Evidence]:
        """Get all evidence."""
        return list(self._evidence.values())

    # -------------------------------------------------------------------------
    # HYPOTHESIS GENERATION
    # -------------------------------------------------------------------------

    def generate_hypotheses(
        self,
        evidence: Evidence,
        domain: str = "physical"
    ) -> List[Hypothesis]:
        """Generate hypotheses for evidence."""
        hypotheses = self._generator.generate(evidence, domain)

        for h in hypotheses:
            self._tracker.add(h)

        return hypotheses

    def generate_unified_hypothesis(
        self,
        evidence_list: List[Evidence],
        domain: str = "physical"
    ) -> List[Hypothesis]:
        """Generate hypotheses explaining multiple evidence."""
        return self._generator.generate_combined(evidence_list, domain)

    # -------------------------------------------------------------------------
    # EXPLANATION
    # -------------------------------------------------------------------------

    def explain(
        self,
        evidence: Evidence,
        domain: str = "physical"
    ) -> Explanation:
        """Generate best explanation for evidence."""
        # Generate hypotheses
        hypotheses = self.generate_hypotheses(evidence, domain)

        if not hypotheses:
            return Explanation(
                reasoning="No hypothesis could be generated"
            )

        # Create explanations
        explanations = []
        for h in hypotheses:
            exp = Explanation(
                hypothesis=h,
                explanation_type=ExplanationType.CAUSAL,
                confidence=self._evaluator.likelihood(evidence, h),
                reasoning=f"Evidence '{evidence.content}' explained by '{h.content}'",
                assumptions=[]
            )
            explanations.append(exp)

        # Rank and return best
        result = self._ranker.rank_combined(explanations)
        return result.best_explanation or explanations[0]

    def explain_all(
        self,
        domain: str = "physical"
    ) -> List[Explanation]:
        """Explain all collected evidence."""
        evidence_list = list(self._evidence.values())

        if not evidence_list:
            return []

        # Generate unified hypotheses
        unified = self.generate_unified_hypothesis(evidence_list, domain)

        # Also generate individual explanations
        explanations = []

        for h in unified:
            exp = Explanation(
                hypothesis=h,
                explanation_type=ExplanationType.CAUSAL,
                confidence=self._compute_unified_confidence(h, evidence_list),
                reasoning=f"Unified explanation: {h.content}"
            )
            explanations.append(exp)

        # Rank
        result = self._ranker.rank_combined(explanations)
        return [exp for exp, _ in result.ranked_explanations]

    def _compute_unified_confidence(
        self,
        hypothesis: Hypothesis,
        evidence_list: List[Evidence]
    ) -> float:
        """Compute confidence for unified hypothesis."""
        total = 0.0
        for ev in evidence_list:
            total += self._evaluator.likelihood(ev, hypothesis)
        return total / len(evidence_list) if evidence_list else 0

    # -------------------------------------------------------------------------
    # EVALUATION
    # -------------------------------------------------------------------------

    def evaluate_hypothesis(
        self,
        hypothesis: Hypothesis
    ) -> Dict[str, Any]:
        """Evaluate a hypothesis against all evidence."""
        result = {
            "supporting": [],
            "contradicting": [],
            "neutral": [],
            "overall_score": 0.0
        }

        total_score = 0.0

        for ev in self._evidence.values():
            supports, strength = self._evaluator.supports(ev, hypothesis)
            contradicts, reason = self._evaluator.contradicts(ev, hypothesis)

            if contradicts:
                result["contradicting"].append({
                    "evidence": ev.content,
                    "reason": reason
                })
                total_score -= 0.3
            elif supports and strength > 0.6:
                result["supporting"].append({
                    "evidence": ev.content,
                    "strength": strength
                })
                total_score += strength
            else:
                result["neutral"].append(ev.content)

        num_evidence = len(self._evidence)
        result["overall_score"] = total_score / num_evidence if num_evidence > 0 else 0

        return result

    # -------------------------------------------------------------------------
    # RANKING
    # -------------------------------------------------------------------------

    def rank_hypotheses(
        self,
        hypotheses: Optional[List[Hypothesis]] = None,
        criterion: RankingCriterion = RankingCriterion.LIKELIHOOD
    ) -> List[Tuple[Hypothesis, float]]:
        """Rank hypotheses by criterion."""
        if hypotheses is None:
            hypotheses = self._tracker.get_active()

        # Create explanations from hypotheses
        explanations = [
            Explanation(
                hypothesis=h,
                confidence=h.prior_probability
            )
            for h in hypotheses
        ]

        result = self._ranker.rank(explanations, criterion)

        return [(exp.hypothesis, score) for exp, score in result.ranked_explanations]

    # -------------------------------------------------------------------------
    # CONSISTENCY
    # -------------------------------------------------------------------------

    def check_consistency(
        self,
        hypothesis1: Hypothesis,
        hypothesis2: Hypothesis
    ) -> Tuple[bool, str]:
        """Check consistency between hypotheses."""
        return self._consistency.is_consistent(hypothesis1, hypothesis2)

    def find_all_inconsistencies(self) -> List[Tuple[Hypothesis, Hypothesis, str]]:
        """Find all inconsistencies in active hypotheses."""
        active = self._tracker.get_active()
        return self._consistency.find_inconsistencies(active)

    # -------------------------------------------------------------------------
    # INFERENCE TO BEST EXPLANATION (IBE)
    # -------------------------------------------------------------------------

    def inference_to_best_explanation(
        self,
        domain: str = "physical"
    ) -> Optional[Explanation]:
        """Perform inference to best explanation."""
        evidence_list = list(self._evidence.values())

        if not evidence_list:
            return None

        # Generate all hypotheses
        all_hypotheses = []
        for ev in evidence_list:
            all_hypotheses.extend(self.generate_hypotheses(ev, domain))

        # Add unified hypotheses
        unified = self.generate_unified_hypothesis(evidence_list, domain)
        all_hypotheses.extend(unified)

        if not all_hypotheses:
            return None

        # Create explanations
        explanations = []
        for h in all_hypotheses:
            conf = self._compute_unified_confidence(h, evidence_list)

            # Apply Occam's razor bonus
            simplicity_bonus = 0.1 / (1 + h.complexity * 0.2)

            exp = Explanation(
                hypothesis=h,
                explanation_type=ExplanationType.CAUSAL,
                confidence=conf + simplicity_bonus,
                reasoning=self._generate_reasoning(h, evidence_list)
            )
            explanations.append(exp)

        # Rank and return best
        result = self._ranker.rank_combined(explanations)
        return result.best_explanation

    def _generate_reasoning(
        self,
        hypothesis: Hypothesis,
        evidence_list: List[Evidence]
    ) -> str:
        """Generate reasoning chain for explanation."""
        parts = [f"Hypothesis: {hypothesis.content}"]

        explained = []
        for ev in evidence_list:
            if ev.evidence_id in hypothesis.explained_evidence:
                explained.append(ev.content)

        if explained:
            parts.append(f"Explains: {', '.join(explained[:3])}")

        parts.append(f"Prior probability: {hypothesis.prior_probability:.2f}")
        parts.append(f"Complexity: {hypothesis.complexity}")

        return " | ".join(parts)

    # -------------------------------------------------------------------------
    # TRACKING
    # -------------------------------------------------------------------------

    def get_best_hypothesis(self) -> Optional[Hypothesis]:
        """Get current best hypothesis."""
        return self._tracker.get_best()

    def update_with_evidence(self, evidence: Evidence) -> None:
        """Update all hypotheses with new evidence."""
        for h in self._tracker.get_active():
            self._tracker.update_probability(
                h.hypothesis_id, evidence, self._evaluator
            )


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Abductive Reasoner."""
    print("=" * 70)
    print("BAEL - ABDUCTIVE REASONER DEMO")
    print("Advanced Abductive Inference and Explanation Generation")
    print("=" * 70)
    print()

    reasoner = AbductiveReasoner()

    # 1. Add Evidence
    print("1. ADD EVIDENCE:")
    print("-" * 40)

    ev1 = reasoner.add_evidence(
        "The grass is wet",
        EvidenceType.OBSERVATION,
        reliability=0.95,
        source="visual observation"
    )
    print(f"   Evidence 1: {ev1.content}")

    ev2 = reasoner.add_evidence(
        "The sidewalk is wet",
        EvidenceType.OBSERVATION,
        reliability=0.95,
        source="visual observation"
    )
    print(f"   Evidence 2: {ev2.content}")

    ev3 = reasoner.add_evidence(
        "Car has water droplets",
        EvidenceType.OBSERVATION,
        reliability=0.9,
        source="visual observation"
    )
    print(f"   Evidence 3: {ev3.content}")
    print()

    # 2. Generate Hypotheses
    print("2. GENERATE HYPOTHESES:")
    print("-" * 40)

    hypotheses = reasoner.generate_hypotheses(ev1, domain="physical")
    print(f"   Generated {len(hypotheses)} hypotheses for '{ev1.content}':")
    for h in hypotheses[:3]:
        print(f"     - {h.content} (prior: {h.prior_probability:.2f})")
    print()

    # 3. Explain Single Evidence
    print("3. EXPLAIN SINGLE EVIDENCE:")
    print("-" * 40)

    explanation = reasoner.explain(ev1, domain="physical")
    print(f"   Evidence: {ev1.content}")
    print(f"   Best explanation: {explanation.hypothesis.content}")
    print(f"   Confidence: {explanation.confidence:.2f}")
    print(f"   Reasoning: {explanation.reasoning}")
    print()

    # 4. Unified Explanation
    print("4. UNIFIED EXPLANATION (Multiple Evidence):")
    print("-" * 40)

    all_evidence = [ev1, ev2, ev3]
    unified = reasoner.generate_unified_hypothesis(all_evidence, domain="physical")

    print(f"   Combined evidence: {[e.content for e in all_evidence]}")
    print(f"   Unified hypotheses:")
    for h in unified[:3]:
        print(f"     - {h.content}")
        print(f"       Explains: {len(h.explained_evidence)} pieces of evidence")
    print()

    # 5. Inference to Best Explanation (IBE)
    print("5. INFERENCE TO BEST EXPLANATION:")
    print("-" * 40)

    best = reasoner.inference_to_best_explanation(domain="physical")
    if best:
        print(f"   Best explanation: {best.hypothesis.content}")
        print(f"   Confidence: {best.confidence:.2f}")
        print(f"   Type: {best.explanation_type.value}")
        print(f"   Reasoning: {best.reasoning[:100]}...")
    print()

    # 6. Hypothesis Ranking
    print("6. HYPOTHESIS RANKING:")
    print("-" * 40)

    ranked = reasoner.rank_hypotheses(
        criterion=RankingCriterion.LIKELIHOOD
    )
    print(f"   Ranked by likelihood:")
    for h, score in ranked[:3]:
        print(f"     {score:.3f}: {h.content}")

    ranked = reasoner.rank_hypotheses(
        criterion=RankingCriterion.SIMPLICITY
    )
    print(f"\n   Ranked by simplicity (Occam's razor):")
    for h, score in ranked[:3]:
        print(f"     {score:.3f}: {h.content}")
    print()

    # 7. Hypothesis Evaluation
    print("7. HYPOTHESIS EVALUATION:")
    print("-" * 40)

    if unified:
        h = unified[0]
        evaluation = reasoner.evaluate_hypothesis(h)
        print(f"   Hypothesis: {h.content}")
        print(f"   Supporting evidence: {len(evaluation['supporting'])}")
        print(f"   Contradicting evidence: {len(evaluation['contradicting'])}")
        print(f"   Overall score: {evaluation['overall_score']:.2f}")
    print()

    # 8. Consistency Checking
    print("8. CONSISTENCY CHECKING:")
    print("-" * 40)

    h1 = Hypothesis(content="The weather is hot and dry")
    h2 = Hypothesis(content="The ground is wet from rain")
    h3 = Hypothesis(content="The weather is cold")

    consistent, reason = reasoner.check_consistency(h1, h2)
    print(f"   '{h1.content}' vs '{h2.content}':")
    print(f"     Consistent: {consistent}, Reason: {reason}")

    consistent, reason = reasoner.check_consistency(h1, h3)
    print(f"   '{h1.content}' vs '{h3.content}':")
    print(f"     Consistent: {consistent}, Reason: {reason}")
    print()

    # 9. Update with New Evidence
    print("9. UPDATE WITH NEW EVIDENCE:")
    print("-" * 40)

    before = reasoner.get_best_hypothesis()
    if before:
        print(f"   Best hypothesis before update: {before.content}")
        print(f"   Probability: {before.prior_probability:.2f}")

    new_ev = reasoner.add_evidence(
        "Thunder was heard earlier",
        EvidenceType.TESTIMONY,
        reliability=0.7
    )
    reasoner.update_with_evidence(new_ev)

    after = reasoner.get_best_hypothesis()
    if after:
        print(f"\n   After adding: '{new_ev.content}'")
        print(f"   Best hypothesis: {after.content}")
        print(f"   Updated probability: {after.prior_probability:.2f}")
    print()

    # 10. Complete Scenario
    print("10. COMPLETE ABDUCTION SCENARIO:")
    print("-" * 40)

    # Reset
    reasoner = AbductiveReasoner()

    # Medical diagnosis scenario
    reasoner.add_evidence("Patient has fever", EvidenceType.OBSERVATION)
    reasoner.add_evidence("Patient has cough", EvidenceType.OBSERVATION)
    reasoner.add_evidence("Patient feels tired", EvidenceType.TESTIMONY)

    best_explanation = reasoner.inference_to_best_explanation(domain="biological")
    if best_explanation:
        print("   Medical Scenario:")
        print(f"   Symptoms: fever, cough, fatigue")
        print(f"   Best explanation: {best_explanation.hypothesis.content}")
        print(f"   Confidence: {best_explanation.confidence:.2f}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Abductive Reasoner Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
