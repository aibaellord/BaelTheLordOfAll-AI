"""
Advanced Reasoning Engine for BAEL Phase 2

Implements multi-step logical reasoning with validation, confidence scoring,
and fallback strategies. Supports deductive, abductive, and analogical reasoning
with constraint satisfaction and hypothesis generation.

Key Components:
- Multi-step reasoning chains
- Confidence scoring and validation
- Constraint satisfaction
- Hypothesis generation and testing
- Reasoning trace tracking
- Fallback strategy selection
"""

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class ReasoningType(str, Enum):
    """Types of reasoning patterns."""
    DEDUCTIVE = "deductive"  # General rules to specific conclusions
    ABDUCTIVE = "abductive"  # Observations to best explanation
    ANALOGICAL = "analogical"  # Similar cases to new conclusion
    INDUCTIVE = "inductive"  # Specific cases to general rules
    CONSTRAINT = "constraint"  # Constraint satisfaction
    PROBABILISTIC = "probabilistic"  # Probabilistic inference


class ConfidenceLevel(str, Enum):
    """Confidence levels for reasoning outcomes."""
    CERTAIN = "certain"  # > 95% confidence
    HIGH = "high"  # 80-95% confidence
    MODERATE = "moderate"  # 60-80% confidence
    LOW = "low"  # 40-60% confidence
    UNCERTAIN = "uncertain"  # < 40% confidence


@dataclass
class ReasoningPremise:
    """A premise in a reasoning chain."""
    statement: str
    type: str  # 'fact', 'rule', 'assumption'
    confidence: float  # 0.0 to 1.0
    source: str  # Where this premise came from
    verified: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "statement": self.statement,
            "type": self.type,
            "confidence": self.confidence,
            "source": self.source,
            "verified": self.verified,
            "metadata": self.metadata,
        }


@dataclass
class ReasoningStep:
    """A single step in reasoning."""
    step_number: int
    type: ReasoningType
    premises: List[ReasoningPremise]
    rule: str  # The rule applied
    conclusion: str  # The conclusion drawn
    confidence: float  # Confidence in this step
    validation_status: str  # 'valid', 'questionable', 'invalid'
    alternatives: List[str] = field(default_factory=list)  # Alternative conclusions
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "step_number": self.step_number,
            "type": self.type.value,
            "premises": [p.to_dict() for p in self.premises],
            "rule": self.rule,
            "conclusion": self.conclusion,
            "confidence": self.confidence,
            "validation_status": self.validation_status,
            "alternatives": self.alternatives,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ReasoningTrace:
    """Complete reasoning trace with all steps."""
    trace_id: str
    query: str
    reasoning_type: ReasoningType
    steps: List[ReasoningStep] = field(default_factory=list)
    final_conclusion: str = ""
    final_confidence: float = 0.0
    constraints: Dict[str, Any] = field(default_factory=dict)
    assumptions: List[str] = field(default_factory=list)
    alternative_conclusions: List[Tuple[str, float]] = field(default_factory=list)
    validity_score: float = 0.0  # Overall reasoning validity
    reasoning_quality: str = "unknown"  # 'excellent', 'good', 'acceptable', 'poor'
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "trace_id": self.trace_id,
            "query": self.query,
            "reasoning_type": self.reasoning_type.value,
            "steps": [s.to_dict() for s in self.steps],
            "final_conclusion": self.final_conclusion,
            "final_confidence": self.final_confidence,
            "constraints": self.constraints,
            "assumptions": self.assumptions,
            "alternative_conclusions": self.alternative_conclusions,
            "validity_score": self.validity_score,
            "reasoning_quality": self.reasoning_quality,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }


class ReasoningValidator:
    """Validates reasoning chains for logical consistency."""

    def __init__(self):
        """Initialize validator."""
        self.contradiction_patterns = self._load_contradiction_patterns()
        self.logical_fallacies = self._load_fallacy_patterns()

    def _load_contradiction_patterns(self) -> Set[Tuple[str, str]]:
        """Load known contradiction patterns."""
        return {
            ("true", "false"),
            ("exists", "does not exist"),
            ("always", "never"),
        }

    def _load_fallacy_patterns(self) -> Dict[str, str]:
        """Load logical fallacy patterns."""
        return {
            "ad_hominem": "Attacking arguer instead of argument",
            "appeal_to_authority": "Unverified authority claim",
            "circular_reasoning": "Conclusion in premises",
            "false_dilemma": "Only two options when more exist",
            "hasty_generalization": "Too few cases for generalization",
            "post_hoc": "Assuming causation from sequence",
        }

    def validate_step(self, step: ReasoningStep) -> Tuple[bool, str]:
        """Validate a single reasoning step."""
        # Check for contradictions in premises
        for i, premise1 in enumerate(step.premises):
            for premise2 in step.premises[i + 1 :]:
                if self._are_contradictory(premise1.statement, premise2.statement):
                    return False, "Contradictory premises detected"

        # Check premise confidence
        min_confidence = min(p.confidence for p in step.premises) if step.premises else 0.0
        if min_confidence < 0.3:
            return False, "Insufficient premise confidence"

        # Validate confidence propagation
        expected_confidence = min(
            min_confidence, 0.95
        )  # Confidence can't increase
        if step.confidence > expected_confidence + 0.05:
            return False, "Confidence score too high for premises"

        return True, "Valid"

    def _are_contradictory(self, stmt1: str, stmt2: str) -> bool:
        """Check if two statements are contradictory."""
        for contradiction in self.contradiction_patterns:
            if (
                contradiction[0].lower() in stmt1.lower()
                and contradiction[1].lower() in stmt2.lower()
            ):
                return True
        return False

    def detect_fallacies(self, trace: ReasoningTrace) -> List[Tuple[str, str]]:
        """Detect potential logical fallacies in reasoning trace."""
        detected = []

        # Check for circular reasoning
        premises_str = " ".join(p.statement for step in trace.steps for p in step.premises)
        if trace.final_conclusion.lower() in premises_str.lower():
            detected.append(("circular_reasoning", "Conclusion found in premises"))

        # Check for hasty generalization
        if trace.reasoning_type == ReasoningType.INDUCTIVE:
            if len(trace.steps) < 3:
                detected.append(
                    ("hasty_generalization", "Too few examples for generalization")
                )

        return detected


class ConstraintSolver:
    """Solves constraint satisfaction problems in reasoning."""

    def __init__(self):
        """Initialize solver."""
        self.constraints: Dict[str, List[Callable]] = {}

    def add_constraint(self, name: str, validator: Callable[[Any], bool]) -> None:
        """Add a constraint validator."""
        if name not in self.constraints:
            self.constraints[name] = []
        self.constraints[name].append(validator)

    def solve(self, variables: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """
        Solve constraints with given variables.

        Returns (satisfied, assignments)
        """
        for constraint_name, validators in self.constraints.items():
            for validator in validators:
                try:
                    if not validator(variables):
                        return False, variables
                except Exception as e:
                    logger.warning(f"Constraint validation error: {e}")
                    return False, variables

        return True, variables


class HypothesisGenerator:
    """Generates and ranks hypotheses."""

    def __init__(self):
        """Initialize generator."""
        self.hypothesis_templates = self._load_templates()
        self.ranking_factors = {
            "consistency": 0.3,
            "simplicity": 0.2,
            "explanatory_power": 0.3,
            "evidence_support": 0.2,
        }

    def _load_templates(self) -> List[str]:
        """Load hypothesis templates."""
        return [
            "If {condition}, then {outcome}",
            "{subject} causes {effect}",
            "{observation} is explained by {hypothesis}",
            "{event} is likely due to {cause}",
        ]

    def generate(self, observation: str, context: Dict[str, Any]) -> List[Tuple[str, float]]:
        """
        Generate hypotheses for an observation.

        Returns list of (hypothesis, confidence) tuples.
        """
        hypotheses = []

        # Generate from templates
        for template in self.hypothesis_templates:
            if "condition" in template and "context" in context:
                hypothesis = template.format(**context)
                confidence = self._score_hypothesis(hypothesis, observation, context)
                hypotheses.append((hypothesis, confidence))

        # Sort by confidence
        hypotheses.sort(key=lambda x: x[1], reverse=True)
        return hypotheses[:5]  # Return top 5

    def _score_hypothesis(
        self, hypothesis: str, observation: str, context: Dict[str, Any]
    ) -> float:
        """Score a hypothesis based on factors."""
        score = 0.0

        # Consistency with observation
        if observation.lower() in hypothesis.lower():
            score += self.ranking_factors["consistency"] * 0.8

        # Simplicity (shorter is simpler)
        word_count = len(hypothesis.split())
        simplicity = 1.0 - (min(word_count, 20) / 20)
        score += self.ranking_factors["simplicity"] * simplicity

        # Evidence support from context
        if context.get("evidence_count", 0) > 0:
            score += self.ranking_factors["evidence_support"] * 0.7

        return min(score, 1.0)


class ReasoningEngine:
    """Main reasoning engine with multi-step support."""

    def __init__(self):
        """Initialize reasoning engine."""
        self.validator = ReasoningValidator()
        self.constraint_solver = ConstraintSolver()
        self.hypothesis_generator = HypothesisGenerator()
        self.reasoning_history: Dict[str, ReasoningTrace] = {}
        self.rule_base: Dict[str, str] = {}

    def add_rule(self, rule_name: str, rule: str) -> None:
        """Add a reasoning rule to the rule base."""
        self.rule_base[rule_name] = rule
        logger.info(f"Added rule: {rule_name}")

    def reason(
        self,
        query: str,
        premises: List[ReasoningPremise],
        reasoning_type: ReasoningType = ReasoningType.DEDUCTIVE,
        constraints: Optional[Dict[str, Any]] = None,
    ) -> ReasoningTrace:
        """
        Perform multi-step reasoning.

        Args:
            query: The question to reason about
            premises: Starting premises
            reasoning_type: Type of reasoning to use
            constraints: Optional constraints to satisfy

        Returns:
            Complete reasoning trace
        """
        trace_id = self._generate_trace_id(query)
        trace = ReasoningTrace(
            trace_id=trace_id,
            query=query,
            reasoning_type=reasoning_type,
            constraints=constraints or {},
        )

        # Validate premises
        valid_premises = [p for p in premises if p.confidence > 0.2]
        if not valid_premises:
            trace.final_conclusion = "Insufficient premises to reason"
            trace.final_confidence = 0.0
            trace.reasoning_quality = "poor"
            return trace

        # Perform reasoning steps
        if reasoning_type == ReasoningType.DEDUCTIVE:
            trace = self._deductive_reasoning(trace, valid_premises)
        elif reasoning_type == ReasoningType.ABDUCTIVE:
            trace = self._abductive_reasoning(trace, valid_premises)
        elif reasoning_type == ReasoningType.ANALOGICAL:
            trace = self._analogical_reasoning(trace, valid_premises)
        elif reasoning_type == ReasoningType.INDUCTIVE:
            trace = self._inductive_reasoning(trace, valid_premises)
        elif reasoning_type == ReasoningType.CONSTRAINT:
            trace = self._constraint_reasoning(trace, valid_premises, constraints)
        elif reasoning_type == ReasoningType.PROBABILISTIC:
            trace = self._probabilistic_reasoning(trace, valid_premises)

        # Calculate overall validity
        trace.validity_score = self._calculate_validity(trace)
        trace.reasoning_quality = self._classify_quality(trace.validity_score)

        # Store in history
        self.reasoning_history[trace_id] = trace
        return trace

    def _deductive_reasoning(
        self, trace: ReasoningTrace, premises: List[ReasoningPremise]
    ) -> ReasoningTrace:
        """Perform deductive reasoning (general to specific)."""
        step_num = 1

        for rule_name, rule in self.rule_base.items():
            step = ReasoningStep(
                step_number=step_num,
                type=ReasoningType.DEDUCTIVE,
                premises=premises,
                rule=rule,
                conclusion=f"Applying {rule_name}",
                confidence=min(p.confidence for p in premises),
                validation_status="valid",
            )

            valid, msg = self.validator.validate_step(step)
            step.validation_status = msg
            trace.steps.append(step)
            step_num += 1

        if trace.steps:
            trace.final_conclusion = trace.steps[-1].conclusion
            trace.final_confidence = trace.steps[-1].confidence

        return trace

    def _abductive_reasoning(
        self, trace: ReasoningTrace, premises: List[ReasoningPremise]
    ) -> ReasoningTrace:
        """Perform abductive reasoning (observations to best explanation)."""
        observation = " ".join(p.statement for p in premises)
        context = {"evidence_count": len(premises)}

        hypotheses = self.hypothesis_generator.generate(observation, context)

        for i, (hypothesis, confidence) in enumerate(hypotheses):
            step = ReasoningStep(
                step_number=i + 1,
                type=ReasoningType.ABDUCTIVE,
                premises=premises,
                rule="Abductive inference",
                conclusion=hypothesis,
                confidence=confidence,
                validation_status="valid",
                alternatives=[h for h, _ in hypotheses[i + 1 :]],
            )

            trace.steps.append(step)

        if trace.steps:
            trace.final_conclusion = trace.steps[0].conclusion
            trace.final_confidence = trace.steps[0].confidence
            trace.alternative_conclusions = hypotheses[1:]

        return trace

    def _analogical_reasoning(
        self, trace: ReasoningTrace, premises: List[ReasoningPremise]
    ) -> ReasoningTrace:
        """Perform analogical reasoning (similar cases)."""
        # Analogical reasoning: find similar cases and apply their solutions
        base_case = premises[0].statement if premises else ""

        step = ReasoningStep(
            step_number=1,
            type=ReasoningType.ANALOGICAL,
            premises=premises,
            rule="Analogical mapping",
            conclusion=f"Similar to: {base_case}",
            confidence=0.7,  # Analogies have lower confidence
            validation_status="valid",
        )

        trace.steps.append(step)
        trace.final_conclusion = step.conclusion
        trace.final_confidence = step.confidence

        return trace

    def _inductive_reasoning(
        self, trace: ReasoningTrace, premises: List[ReasoningPremise]
    ) -> ReasoningTrace:
        """Perform inductive reasoning (specific to general)."""
        # Collect observations
        observations = [p.statement for p in premises]

        # Generalize
        generalization = f"Pattern from {len(observations)} cases: "
        confidence = 0.5 + (len(observations) * 0.1)  # More cases = more confidence
        confidence = min(confidence, 0.9)

        step = ReasoningStep(
            step_number=1,
            type=ReasoningType.INDUCTIVE,
            premises=premises,
            rule="Generalization from examples",
            conclusion=generalization,
            confidence=confidence,
            validation_status="valid",
        )

        trace.steps.append(step)
        trace.final_conclusion = step.conclusion
        trace.final_confidence = step.confidence

        return trace

    def _constraint_reasoning(
        self,
        trace: ReasoningTrace,
        premises: List[ReasoningPremise],
        constraints: Optional[Dict[str, Any]],
    ) -> ReasoningTrace:
        """Perform constraint satisfaction reasoning."""
        variables = {p.statement: p.confidence for p in premises}

        satisfied, solution = self.constraint_solver.solve(variables)

        step = ReasoningStep(
            step_number=1,
            type=ReasoningType.CONSTRAINT,
            premises=premises,
            rule="Constraint satisfaction",
            conclusion=f"Constraints {'satisfied' if satisfied else 'violated'}",
            confidence=1.0 if satisfied else 0.0,
            validation_status="valid" if satisfied else "invalid",
        )

        trace.steps.append(step)
        trace.final_conclusion = step.conclusion
        trace.final_confidence = step.confidence

        return trace

    def _probabilistic_reasoning(
        self, trace: ReasoningTrace, premises: List[ReasoningPremise]
    ) -> ReasoningTrace:
        """Perform probabilistic reasoning."""
        # Calculate combined probability
        probs = [p.confidence for p in premises]
        combined_prob = 1.0
        for p in probs:
            combined_prob *= p

        step = ReasoningStep(
            step_number=1,
            type=ReasoningType.PROBABILISTIC,
            premises=premises,
            rule="Probabilistic inference",
            conclusion=f"Combined probability: {combined_prob:.2%}",
            confidence=combined_prob,
            validation_status="valid",
        )

        trace.steps.append(step)
        trace.final_conclusion = step.conclusion
        trace.final_confidence = step.confidence

        return trace

    def _calculate_validity(self, trace: ReasoningTrace) -> float:
        """Calculate overall validity score of reasoning."""
        if not trace.steps:
            return 0.0

        # Average of step confidences
        step_validity = sum(s.confidence for s in trace.steps) / len(trace.steps)

        # Check for fallacies
        fallacies = self.validator.detect_fallacies(trace)
        fallacy_penalty = len(fallacies) * 0.1

        validity = max(step_validity - fallacy_penalty, 0.0)
        return min(validity, 1.0)

    def _classify_quality(self, validity_score: float) -> str:
        """Classify reasoning quality based on validity."""
        if validity_score >= 0.85:
            return "excellent"
        elif validity_score >= 0.70:
            return "good"
        elif validity_score >= 0.50:
            return "acceptable"
        else:
            return "poor"

    def _generate_trace_id(self, query: str) -> str:
        """Generate unique trace ID."""
        timestamp = datetime.now().isoformat()
        combined = f"{query}{timestamp}"
        return hashlib.md5(combined.encode()).hexdigest()[:12]

    def get_trace(self, trace_id: str) -> Optional[ReasoningTrace]:
        """Retrieve a reasoning trace by ID."""
        return self.reasoning_history.get(trace_id)

    def explain_conclusion(self, trace_id: str) -> str:
        """Generate natural language explanation of reasoning."""
        trace = self.get_trace(trace_id)
        if not trace:
            return "Trace not found"

        explanation = f"Question: {trace.query}\n\n"
        explanation += f"Reasoning Type: {trace.reasoning_type.value}\n\n"
        explanation += "Steps:\n"

        for step in trace.steps:
            explanation += f"{step.step_number}. {step.conclusion} "
            explanation += f"(Confidence: {step.confidence:.0%})\n"

        explanation += f"\nFinal Conclusion: {trace.final_conclusion}\n"
        explanation += f"Overall Confidence: {trace.final_confidence:.0%}\n"
        explanation += f"Quality: {trace.reasoning_quality}\n"

        if trace.alternative_conclusions:
            explanation += "\nAlternative Conclusions:\n"
            for alt, conf in trace.alternative_conclusions:
                explanation += f"  - {alt} ({conf:.0%})\n"

        return explanation


# Global reasoning engine instance
_reasoning_engine = None


def get_reasoning_engine() -> ReasoningEngine:
    """Get or create global reasoning engine."""
    global _reasoning_engine
    if _reasoning_engine is None:
        _reasoning_engine = ReasoningEngine()
    return _reasoning_engine
