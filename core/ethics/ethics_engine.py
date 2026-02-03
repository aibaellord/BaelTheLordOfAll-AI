#!/usr/bin/env python3
"""
BAEL - Ethics Engine
Advanced ethical reasoning and moral decision-making.

Features:
- Ethical frameworks
- Moral reasoning
- Value alignment
- Harm prevention
- Fairness assessment
- Transparency
- Accountability
- Ethical constraints
"""

import asyncio
import copy
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

class EthicalFramework(Enum):
    """Ethical frameworks."""
    UTILITARIANISM = "utilitarianism"
    DEONTOLOGY = "deontology"
    VIRTUE_ETHICS = "virtue_ethics"
    CARE_ETHICS = "care_ethics"
    RIGHTS_BASED = "rights_based"
    JUSTICE = "justice"


class MoralPriority(Enum):
    """Moral priority levels."""
    CRITICAL = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3


class HarmType(Enum):
    """Types of potential harm."""
    PHYSICAL = "physical"
    PSYCHOLOGICAL = "psychological"
    FINANCIAL = "financial"
    PRIVACY = "privacy"
    DISCRIMINATION = "discrimination"
    DECEPTION = "deception"
    AUTONOMY = "autonomy"


class HarmSeverity(Enum):
    """Harm severity levels."""
    NONE = 0
    MINIMAL = 1
    MODERATE = 2
    SIGNIFICANT = 3
    SEVERE = 4
    CATASTROPHIC = 5


class DecisionOutcome(Enum):
    """Ethical decision outcomes."""
    APPROVED = "approved"
    DENIED = "denied"
    CONDITIONAL = "conditional"
    REQUIRES_REVIEW = "requires_review"


class ValueType(Enum):
    """Core values."""
    SAFETY = "safety"
    BENEFICENCE = "beneficence"
    NON_MALEFICENCE = "non_maleficence"
    AUTONOMY = "autonomy"
    JUSTICE = "justice"
    PRIVACY = "privacy"
    TRANSPARENCY = "transparency"
    ACCOUNTABILITY = "accountability"
    TRUTHFULNESS = "truthfulness"
    DIGNITY = "dignity"


class StakeholderType(Enum):
    """Stakeholder types."""
    INDIVIDUAL = "individual"
    GROUP = "group"
    ORGANIZATION = "organization"
    SOCIETY = "society"
    ENVIRONMENT = "environment"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Value:
    """Ethical value."""
    value_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    value_type: ValueType = ValueType.SAFETY
    name: str = ""
    description: str = ""
    weight: float = 1.0
    priority: MoralPriority = MoralPriority.HIGH


@dataclass
class Stakeholder:
    """Affected stakeholder."""
    stakeholder_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    stakeholder_type: StakeholderType = StakeholderType.INDIVIDUAL
    name: str = ""
    vulnerability: float = 0.0  # 0-1, higher = more vulnerable
    influence: float = 0.5


@dataclass
class Harm:
    """Potential harm."""
    harm_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    harm_type: HarmType = HarmType.PHYSICAL
    severity: HarmSeverity = HarmSeverity.NONE
    probability: float = 0.0
    reversibility: float = 1.0  # 0 = irreversible, 1 = fully reversible
    affected_stakeholders: List[str] = field(default_factory=list)
    description: str = ""


@dataclass
class Benefit:
    """Potential benefit."""
    benefit_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    magnitude: float = 0.0
    probability: float = 1.0
    beneficiaries: List[str] = field(default_factory=list)
    description: str = ""


@dataclass
class EthicalPrinciple:
    """Ethical principle."""
    principle_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    framework: EthicalFramework = EthicalFramework.DEONTOLOGY
    priority: MoralPriority = MoralPriority.HIGH
    constraints: List[str] = field(default_factory=list)


@dataclass
class EthicalAction:
    """Action to evaluate."""
    action_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    potential_harms: List[Harm] = field(default_factory=list)
    potential_benefits: List[Benefit] = field(default_factory=list)
    stakeholders: List[Stakeholder] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EthicalEvaluation:
    """Evaluation result."""
    evaluation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    action_id: str = ""
    outcome: DecisionOutcome = DecisionOutcome.DENIED
    score: float = 0.0
    framework_scores: Dict[str, float] = field(default_factory=dict)
    violated_principles: List[str] = field(default_factory=list)
    harm_assessment: Dict[str, float] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    reasoning: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class EthicalConstraint:
    """Hard ethical constraint."""
    constraint_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    check_func: Optional[Callable[[EthicalAction], bool]] = None
    violation_severity: HarmSeverity = HarmSeverity.SEVERE


@dataclass
class AuditRecord:
    """Ethical decision audit record."""
    record_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    action: EthicalAction = field(default_factory=EthicalAction)
    evaluation: EthicalEvaluation = field(default_factory=EthicalEvaluation)
    decision_maker: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    justification: str = ""


@dataclass
class EthicsStats:
    """Ethics engine statistics."""
    total_evaluations: int = 0
    approved_actions: int = 0
    denied_actions: int = 0
    constraint_violations: int = 0
    avg_evaluation_time: float = 0.0


# =============================================================================
# ETHICAL FRAMEWORKS
# =============================================================================

class EthicalEvaluator(ABC):
    """Abstract ethical evaluator."""

    @property
    @abstractmethod
    def framework(self) -> EthicalFramework:
        """Get framework type."""
        pass

    @abstractmethod
    def evaluate(self, action: EthicalAction) -> Tuple[float, str]:
        """Evaluate action and return score and reasoning."""
        pass


class UtilitarianEvaluator(EthicalEvaluator):
    """Utilitarian ethics - maximize overall good."""

    @property
    def framework(self) -> EthicalFramework:
        return EthicalFramework.UTILITARIANISM

    def evaluate(self, action: EthicalAction) -> Tuple[float, str]:
        """Evaluate based on net utility."""
        # Calculate total expected harm
        total_harm = 0.0
        for harm in action.potential_harms:
            expected_harm = harm.severity.value * harm.probability * (1 - harm.reversibility)
            total_harm += expected_harm

        # Calculate total expected benefit
        total_benefit = 0.0
        for benefit in action.potential_benefits:
            expected_benefit = benefit.magnitude * benefit.probability
            total_benefit += expected_benefit

        # Net utility
        net_utility = total_benefit - total_harm

        # Normalize to [0, 1]
        if net_utility > 0:
            score = min(1.0, 0.5 + net_utility / 10)
        else:
            score = max(0.0, 0.5 + net_utility / 10)

        reasoning = f"Net utility: {net_utility:.2f} (benefit: {total_benefit:.2f}, harm: {total_harm:.2f})"

        return score, reasoning


class DeontologicalEvaluator(EthicalEvaluator):
    """Deontological ethics - duty-based rules."""

    def __init__(self):
        self._rules = [
            ("no_deception", HarmType.DECEPTION),
            ("respect_autonomy", HarmType.AUTONOMY),
            ("protect_privacy", HarmType.PRIVACY),
            ("no_discrimination", HarmType.DISCRIMINATION),
        ]

    @property
    def framework(self) -> EthicalFramework:
        return EthicalFramework.DEONTOLOGY

    def evaluate(self, action: EthicalAction) -> Tuple[float, str]:
        """Evaluate based on rule compliance."""
        violations = []

        for rule_name, harm_type in self._rules:
            for harm in action.potential_harms:
                if harm.harm_type == harm_type and harm.severity.value >= HarmSeverity.MODERATE.value:
                    violations.append(rule_name)

        if not violations:
            return 1.0, "All duties respected"

        # Each violation reduces score
        score = max(0.0, 1.0 - len(violations) * 0.25)
        reasoning = f"Violated duties: {', '.join(violations)}"

        return score, reasoning


class VirtueEvaluator(EthicalEvaluator):
    """Virtue ethics - character-based evaluation."""

    def __init__(self):
        self._virtues = {
            "honesty": 0.0,
            "compassion": 0.0,
            "justice": 0.0,
            "prudence": 0.0,
            "courage": 0.0,
        }

    @property
    def framework(self) -> EthicalFramework:
        return EthicalFramework.VIRTUE_ETHICS

    def evaluate(self, action: EthicalAction) -> Tuple[float, str]:
        """Evaluate based on virtuous character."""
        virtue_scores = copy.copy(self._virtues)

        # Analyze action for virtue expression
        for harm in action.potential_harms:
            if harm.harm_type == HarmType.DECEPTION:
                virtue_scores["honesty"] -= harm.severity.value * 0.1
            if harm.harm_type == HarmType.PSYCHOLOGICAL:
                virtue_scores["compassion"] -= harm.severity.value * 0.1
            if harm.harm_type == HarmType.DISCRIMINATION:
                virtue_scores["justice"] -= harm.severity.value * 0.1

        for benefit in action.potential_benefits:
            virtue_scores["compassion"] += benefit.magnitude * 0.05
            virtue_scores["justice"] += benefit.magnitude * 0.02

        # Average virtue score
        avg_score = sum(virtue_scores.values()) / len(virtue_scores)
        score = max(0.0, min(1.0, 0.5 + avg_score))

        positive = [v for v, s in virtue_scores.items() if s > 0]
        negative = [v for v, s in virtue_scores.items() if s < 0]

        reasoning = f"Virtues expressed: {positive}, Lacking: {negative}"

        return score, reasoning


class CareEvaluator(EthicalEvaluator):
    """Care ethics - relationship-focused."""

    @property
    def framework(self) -> EthicalFramework:
        return EthicalFramework.CARE_ETHICS

    def evaluate(self, action: EthicalAction) -> Tuple[float, str]:
        """Evaluate based on care for relationships."""
        vulnerable_harm = 0.0
        care_shown = 0.0

        for stakeholder in action.stakeholders:
            stakeholder_harm = 0.0
            stakeholder_benefit = 0.0

            for harm in action.potential_harms:
                if stakeholder.stakeholder_id in harm.affected_stakeholders:
                    stakeholder_harm += harm.severity.value * harm.probability

            for benefit in action.potential_benefits:
                if stakeholder.stakeholder_id in benefit.beneficiaries:
                    stakeholder_benefit += benefit.magnitude * benefit.probability

            # Weight by vulnerability
            vulnerable_harm += stakeholder_harm * (1 + stakeholder.vulnerability)
            care_shown += stakeholder_benefit * (1 + stakeholder.vulnerability)

        net_care = care_shown - vulnerable_harm
        score = max(0.0, min(1.0, 0.5 + net_care / 10))

        reasoning = f"Care balance: {net_care:.2f} (care: {care_shown:.2f}, vulnerable harm: {vulnerable_harm:.2f})"

        return score, reasoning


class RightsEvaluator(EthicalEvaluator):
    """Rights-based ethics."""

    def __init__(self):
        self._fundamental_rights = [
            "life",
            "liberty",
            "privacy",
            "dignity",
            "equality",
        ]

    @property
    def framework(self) -> EthicalFramework:
        return EthicalFramework.RIGHTS_BASED

    def evaluate(self, action: EthicalAction) -> Tuple[float, str]:
        """Evaluate based on rights protection."""
        rights_violations = []

        for harm in action.potential_harms:
            if harm.harm_type == HarmType.PHYSICAL and harm.severity.value >= HarmSeverity.SIGNIFICANT.value:
                rights_violations.append("life")
            if harm.harm_type == HarmType.AUTONOMY:
                rights_violations.append("liberty")
            if harm.harm_type == HarmType.PRIVACY:
                rights_violations.append("privacy")
            if harm.harm_type == HarmType.PSYCHOLOGICAL and harm.severity.value >= HarmSeverity.MODERATE.value:
                rights_violations.append("dignity")
            if harm.harm_type == HarmType.DISCRIMINATION:
                rights_violations.append("equality")

        unique_violations = set(rights_violations)

        if not unique_violations:
            return 1.0, "All fundamental rights protected"

        score = max(0.0, 1.0 - len(unique_violations) * 0.2)
        reasoning = f"Rights potentially violated: {', '.join(unique_violations)}"

        return score, reasoning


class JusticeEvaluator(EthicalEvaluator):
    """Justice-focused ethics."""

    @property
    def framework(self) -> EthicalFramework:
        return EthicalFramework.JUSTICE

    def evaluate(self, action: EthicalAction) -> Tuple[float, str]:
        """Evaluate based on fairness and justice."""
        # Check for discrimination
        discrimination_severity = 0.0
        for harm in action.potential_harms:
            if harm.harm_type == HarmType.DISCRIMINATION:
                discrimination_severity += harm.severity.value * harm.probability

        # Check benefit distribution
        benefit_per_stakeholder = defaultdict(float)
        harm_per_stakeholder = defaultdict(float)

        for benefit in action.potential_benefits:
            for beneficiary in benefit.beneficiaries:
                benefit_per_stakeholder[beneficiary] += benefit.magnitude

        for harm in action.potential_harms:
            for affected in harm.affected_stakeholders:
                harm_per_stakeholder[affected] += harm.severity.value

        # Calculate Gini coefficient for inequality
        all_stakeholders = set(benefit_per_stakeholder.keys()) | set(harm_per_stakeholder.keys())
        net_impacts = [
            benefit_per_stakeholder.get(s, 0) - harm_per_stakeholder.get(s, 0)
            for s in all_stakeholders
        ] if all_stakeholders else [0]

        if len(net_impacts) > 1:
            sorted_impacts = sorted(net_impacts)
            n = len(sorted_impacts)
            cumsum = sum((i + 1) * x for i, x in enumerate(sorted_impacts))
            gini = (2 * cumsum) / (n * sum(sorted_impacts)) - (n + 1) / n if sum(sorted_impacts) != 0 else 0
            gini = abs(gini)
        else:
            gini = 0

        # Score based on fairness
        fairness_score = 1.0 - min(1.0, discrimination_severity / 5)
        equality_score = 1.0 - min(1.0, gini)

        score = (fairness_score + equality_score) / 2
        reasoning = f"Fairness: {fairness_score:.2f}, Equality (Gini): {equality_score:.2f}"

        return score, reasoning


# =============================================================================
# HARM ANALYZER
# =============================================================================

class HarmAnalyzer:
    """Analyze potential harms."""

    def analyze(
        self,
        action: EthicalAction
    ) -> Dict[str, float]:
        """Analyze harms and return severity scores."""
        harm_scores = {}

        for harm_type in HarmType:
            relevant_harms = [h for h in action.potential_harms if h.harm_type == harm_type]

            if relevant_harms:
                max_severity = max(h.severity.value * h.probability for h in relevant_harms)
                harm_scores[harm_type.value] = max_severity
            else:
                harm_scores[harm_type.value] = 0.0

        return harm_scores

    def identify_critical_harms(
        self,
        action: EthicalAction,
        threshold: HarmSeverity = HarmSeverity.SIGNIFICANT
    ) -> List[Harm]:
        """Identify critical harms."""
        return [
            h for h in action.potential_harms
            if h.severity.value >= threshold.value
        ]

    def calculate_risk_score(
        self,
        action: EthicalAction
    ) -> float:
        """Calculate overall risk score."""
        if not action.potential_harms:
            return 0.0

        total_risk = sum(
            h.severity.value * h.probability * (1 - h.reversibility)
            for h in action.potential_harms
        )

        max_possible = len(action.potential_harms) * HarmSeverity.CATASTROPHIC.value

        return min(1.0, total_risk / max_possible) if max_possible > 0 else 0.0


# =============================================================================
# VALUE ALIGNER
# =============================================================================

class ValueAligner:
    """Align actions with values."""

    def __init__(self):
        self._values: Dict[str, Value] = {}

    def add_value(self, value: Value) -> None:
        """Add core value."""
        self._values[value.value_id] = value

    def remove_value(self, value_id: str) -> None:
        """Remove value."""
        self._values.pop(value_id, None)

    def check_alignment(
        self,
        action: EthicalAction
    ) -> Tuple[float, List[str]]:
        """Check action alignment with values."""
        violations = []
        alignment_scores = []

        for value in self._values.values():
            score, violated = self._check_value(action, value)
            alignment_scores.append(score * value.weight)

            if violated:
                violations.append(value.name)

        total_weight = sum(v.weight for v in self._values.values()) or 1
        overall_score = sum(alignment_scores) / total_weight

        return overall_score, violations

    def _check_value(
        self,
        action: EthicalAction,
        value: Value
    ) -> Tuple[float, bool]:
        """Check alignment with specific value."""
        violated = False
        score = 1.0

        for harm in action.potential_harms:
            if value.value_type == ValueType.SAFETY and harm.harm_type == HarmType.PHYSICAL:
                if harm.severity.value >= HarmSeverity.MODERATE.value:
                    violated = True
                    score -= harm.severity.value * 0.1

            elif value.value_type == ValueType.PRIVACY and harm.harm_type == HarmType.PRIVACY:
                if harm.severity.value >= HarmSeverity.MINIMAL.value:
                    violated = True
                    score -= harm.severity.value * 0.15

            elif value.value_type == ValueType.TRUTHFULNESS and harm.harm_type == HarmType.DECEPTION:
                violated = True
                score -= harm.severity.value * 0.2

            elif value.value_type == ValueType.JUSTICE and harm.harm_type == HarmType.DISCRIMINATION:
                violated = True
                score -= harm.severity.value * 0.15

        return max(0.0, score), violated


# =============================================================================
# CONSTRAINT CHECKER
# =============================================================================

class ConstraintChecker:
    """Check ethical constraints."""

    def __init__(self):
        self._constraints: Dict[str, EthicalConstraint] = {}

    def add_constraint(self, constraint: EthicalConstraint) -> None:
        """Add constraint."""
        self._constraints[constraint.constraint_id] = constraint

    def remove_constraint(self, constraint_id: str) -> None:
        """Remove constraint."""
        self._constraints.pop(constraint_id, None)

    def check_all(
        self,
        action: EthicalAction
    ) -> Tuple[bool, List[str]]:
        """Check all constraints."""
        violations = []

        for constraint in self._constraints.values():
            if not self._check_constraint(constraint, action):
                violations.append(constraint.name)

        return len(violations) == 0, violations

    def _check_constraint(
        self,
        constraint: EthicalConstraint,
        action: EthicalAction
    ) -> bool:
        """Check single constraint."""
        if constraint.check_func:
            try:
                return constraint.check_func(action)
            except Exception:
                return False
        return True

    def create_harm_constraint(
        self,
        name: str,
        harm_type: HarmType,
        max_severity: HarmSeverity
    ) -> EthicalConstraint:
        """Create harm-based constraint."""
        def check_func(action: EthicalAction) -> bool:
            for harm in action.potential_harms:
                if harm.harm_type == harm_type and harm.severity.value > max_severity.value:
                    return False
            return True

        constraint = EthicalConstraint(
            name=name,
            description=f"No {harm_type.value} harm above {max_severity.name}",
            check_func=check_func,
            violation_severity=max_severity
        )

        self.add_constraint(constraint)
        return constraint


# =============================================================================
# TRANSPARENCY ENGINE
# =============================================================================

class TransparencyEngine:
    """Provide transparency for ethical decisions."""

    def __init__(self):
        self._audit_log: deque = deque(maxlen=10000)

    def record(
        self,
        action: EthicalAction,
        evaluation: EthicalEvaluation,
        decision_maker: str,
        justification: str
    ) -> AuditRecord:
        """Record ethical decision."""
        record = AuditRecord(
            action=action,
            evaluation=evaluation,
            decision_maker=decision_maker,
            justification=justification
        )

        self._audit_log.append(record)
        return record

    def get_audit_trail(
        self,
        limit: int = 100,
        action_id: Optional[str] = None
    ) -> List[AuditRecord]:
        """Get audit trail."""
        records = list(self._audit_log)

        if action_id:
            records = [r for r in records if r.action.action_id == action_id]

        return records[-limit:]

    def explain_decision(
        self,
        evaluation: EthicalEvaluation
    ) -> str:
        """Generate explanation for decision."""
        lines = [
            f"Decision: {evaluation.outcome.value}",
            f"Overall Score: {evaluation.score:.2f}",
            "",
            "Framework Analysis:",
        ]

        for framework, score in evaluation.framework_scores.items():
            lines.append(f"  - {framework}: {score:.2f}")

        if evaluation.violated_principles:
            lines.append("")
            lines.append("Principle Violations:")
            for principle in evaluation.violated_principles:
                lines.append(f"  - {principle}")

        if evaluation.harm_assessment:
            lines.append("")
            lines.append("Harm Assessment:")
            for harm_type, score in evaluation.harm_assessment.items():
                if score > 0:
                    lines.append(f"  - {harm_type}: {score:.2f}")

        if evaluation.recommendations:
            lines.append("")
            lines.append("Recommendations:")
            for rec in evaluation.recommendations:
                lines.append(f"  - {rec}")

        return "\n".join(lines)


# =============================================================================
# ETHICS ENGINE
# =============================================================================

class EthicsEngine:
    """
    Ethics Engine for BAEL.

    Advanced ethical reasoning and moral decision-making.
    """

    def __init__(
        self,
        primary_framework: EthicalFramework = EthicalFramework.DEONTOLOGY
    ):
        self._primary_framework = primary_framework

        # Evaluators
        self._evaluators: Dict[EthicalFramework, EthicalEvaluator] = {
            EthicalFramework.UTILITARIANISM: UtilitarianEvaluator(),
            EthicalFramework.DEONTOLOGY: DeontologicalEvaluator(),
            EthicalFramework.VIRTUE_ETHICS: VirtueEvaluator(),
            EthicalFramework.CARE_ETHICS: CareEvaluator(),
            EthicalFramework.RIGHTS_BASED: RightsEvaluator(),
            EthicalFramework.JUSTICE: JusticeEvaluator(),
        }

        self._harm_analyzer = HarmAnalyzer()
        self._value_aligner = ValueAligner()
        self._constraint_checker = ConstraintChecker()
        self._transparency = TransparencyEngine()

        self._framework_weights: Dict[EthicalFramework, float] = {
            f: 1.0 for f in EthicalFramework
        }
        self._framework_weights[primary_framework] = 2.0

        self._principles: Dict[str, EthicalPrinciple] = {}
        self._stats = EthicsStats()
        self._evaluation_times: deque = deque(maxlen=1000)

        # Initialize default values
        self._init_default_values()
        self._init_default_constraints()

    def _init_default_values(self) -> None:
        """Initialize default core values."""
        defaults = [
            Value(value_type=ValueType.SAFETY, name="Safety", weight=2.0),
            Value(value_type=ValueType.NON_MALEFICENCE, name="Do No Harm", weight=2.0),
            Value(value_type=ValueType.TRUTHFULNESS, name="Truthfulness", weight=1.5),
            Value(value_type=ValueType.PRIVACY, name="Privacy", weight=1.5),
            Value(value_type=ValueType.JUSTICE, name="Justice", weight=1.5),
            Value(value_type=ValueType.AUTONOMY, name="Autonomy", weight=1.0),
            Value(value_type=ValueType.TRANSPARENCY, name="Transparency", weight=1.0),
        ]

        for value in defaults:
            self._value_aligner.add_value(value)

    def _init_default_constraints(self) -> None:
        """Initialize default constraints."""
        # No severe physical harm
        self._constraint_checker.create_harm_constraint(
            "no_severe_physical_harm",
            HarmType.PHYSICAL,
            HarmSeverity.MODERATE
        )

        # No deception
        self._constraint_checker.create_harm_constraint(
            "no_significant_deception",
            HarmType.DECEPTION,
            HarmSeverity.MODERATE
        )

    # -------------------------------------------------------------------------
    # CONFIGURATION
    # -------------------------------------------------------------------------

    def set_primary_framework(self, framework: EthicalFramework) -> None:
        """Set primary ethical framework."""
        self._primary_framework = framework

        # Reset weights
        for f in EthicalFramework:
            self._framework_weights[f] = 1.0
        self._framework_weights[framework] = 2.0

    def set_framework_weight(
        self,
        framework: EthicalFramework,
        weight: float
    ) -> None:
        """Set framework weight."""
        self._framework_weights[framework] = weight

    def add_principle(self, principle: EthicalPrinciple) -> None:
        """Add ethical principle."""
        self._principles[principle.principle_id] = principle

    def add_value(self, value: Value) -> None:
        """Add core value."""
        self._value_aligner.add_value(value)

    def add_constraint(self, constraint: EthicalConstraint) -> None:
        """Add ethical constraint."""
        self._constraint_checker.add_constraint(constraint)

    # -------------------------------------------------------------------------
    # EVALUATION
    # -------------------------------------------------------------------------

    def evaluate(
        self,
        action: EthicalAction,
        decision_maker: str = "ethics_engine"
    ) -> EthicalEvaluation:
        """Evaluate action ethically."""
        start_time = time.time()

        # Check hard constraints first
        constraints_ok, violated_constraints = self._constraint_checker.check_all(action)

        if not constraints_ok:
            evaluation = EthicalEvaluation(
                action_id=action.action_id,
                outcome=DecisionOutcome.DENIED,
                score=0.0,
                violated_principles=violated_constraints,
                reasoning=f"Hard constraint violations: {', '.join(violated_constraints)}"
            )

            self._stats.constraint_violations += 1
            self._stats.denied_actions += 1
            self._stats.total_evaluations += 1

            # Record
            self._transparency.record(
                action, evaluation, decision_maker,
                "Denied due to constraint violations"
            )

            return evaluation

        # Evaluate with each framework
        framework_scores = {}
        framework_reasoning = {}

        for framework, evaluator in self._evaluators.items():
            score, reasoning = evaluator.evaluate(action)
            framework_scores[framework.value] = score
            framework_reasoning[framework.value] = reasoning

        # Calculate weighted score
        total_weight = sum(self._framework_weights.values())
        weighted_score = sum(
            framework_scores[f.value] * self._framework_weights[f]
            for f in EthicalFramework
        ) / total_weight

        # Value alignment
        alignment_score, value_violations = self._value_aligner.check_alignment(action)

        # Harm analysis
        harm_assessment = self._harm_analyzer.analyze(action)
        risk_score = self._harm_analyzer.calculate_risk_score(action)

        # Final score (weighted combination)
        final_score = (weighted_score * 0.6 + alignment_score * 0.25 + (1 - risk_score) * 0.15)

        # Determine outcome
        if final_score >= 0.7:
            outcome = DecisionOutcome.APPROVED
            self._stats.approved_actions += 1
        elif final_score >= 0.5:
            outcome = DecisionOutcome.CONDITIONAL
        elif final_score >= 0.3:
            outcome = DecisionOutcome.REQUIRES_REVIEW
        else:
            outcome = DecisionOutcome.DENIED
            self._stats.denied_actions += 1

        # Generate recommendations
        recommendations = self._generate_recommendations(
            action, framework_scores, harm_assessment
        )

        # Build reasoning
        reasoning_parts = [f"Framework weighted score: {weighted_score:.2f}"]
        for f, r in framework_reasoning.items():
            reasoning_parts.append(f"  {f}: {r}")
        reasoning_parts.append(f"Value alignment: {alignment_score:.2f}")
        reasoning_parts.append(f"Risk score: {risk_score:.2f}")

        evaluation = EthicalEvaluation(
            action_id=action.action_id,
            outcome=outcome,
            score=final_score,
            framework_scores=framework_scores,
            violated_principles=value_violations,
            harm_assessment=harm_assessment,
            recommendations=recommendations,
            reasoning="\n".join(reasoning_parts)
        )

        # Update stats
        elapsed = time.time() - start_time
        self._evaluation_times.append(elapsed)
        self._stats.total_evaluations += 1
        self._stats.avg_evaluation_time = (
            sum(self._evaluation_times) / len(self._evaluation_times)
        )

        # Record for transparency
        self._transparency.record(
            action, evaluation, decision_maker,
            f"Outcome: {outcome.value}, Score: {final_score:.2f}"
        )

        return evaluation

    def _generate_recommendations(
        self,
        action: EthicalAction,
        framework_scores: Dict[str, float],
        harm_assessment: Dict[str, float]
    ) -> List[str]:
        """Generate improvement recommendations."""
        recommendations = []

        # Low framework scores
        for framework, score in framework_scores.items():
            if score < 0.5:
                if framework == "utilitarianism":
                    recommendations.append("Consider increasing overall benefits")
                elif framework == "deontology":
                    recommendations.append("Review compliance with moral duties")
                elif framework == "virtue_ethics":
                    recommendations.append("Examine if action reflects virtuous character")
                elif framework == "care_ethics":
                    recommendations.append("Consider impact on vulnerable stakeholders")
                elif framework == "rights_based":
                    recommendations.append("Review potential rights violations")
                elif framework == "justice":
                    recommendations.append("Ensure fair distribution of impacts")

        # High harm areas
        for harm_type, score in harm_assessment.items():
            if score > 2:
                recommendations.append(f"Mitigate {harm_type} risks")

        return recommendations[:5]  # Limit to 5 recommendations

    # -------------------------------------------------------------------------
    # QUICK CHECKS
    # -------------------------------------------------------------------------

    def is_permissible(self, action: EthicalAction) -> bool:
        """Quick check if action is permissible."""
        evaluation = self.evaluate(action)
        return evaluation.outcome in [DecisionOutcome.APPROVED, DecisionOutcome.CONDITIONAL]

    def identify_concerns(self, action: EthicalAction) -> List[str]:
        """Identify ethical concerns."""
        concerns = []

        # Check harms
        critical_harms = self._harm_analyzer.identify_critical_harms(action)
        for harm in critical_harms:
            concerns.append(f"Critical {harm.harm_type.value} harm risk")

        # Check value alignment
        _, violations = self._value_aligner.check_alignment(action)
        for v in violations:
            concerns.append(f"Potential {v} value violation")

        return concerns

    def assess_risk(self, action: EthicalAction) -> float:
        """Assess overall ethical risk."""
        return self._harm_analyzer.calculate_risk_score(action)

    # -------------------------------------------------------------------------
    # TRANSPARENCY
    # -------------------------------------------------------------------------

    def explain(self, evaluation: EthicalEvaluation) -> str:
        """Explain evaluation decision."""
        return self._transparency.explain_decision(evaluation)

    def get_audit_trail(self, limit: int = 100) -> List[AuditRecord]:
        """Get audit trail."""
        return self._transparency.get_audit_trail(limit)

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def get_stats(self) -> EthicsStats:
        """Get ethics engine statistics."""
        return self._stats


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Ethics Engine."""
    print("=" * 70)
    print("BAEL - ETHICS ENGINE DEMO")
    print("Advanced Ethical Reasoning and Moral Decision-Making")
    print("=" * 70)
    print()

    engine = EthicsEngine(primary_framework=EthicalFramework.DEONTOLOGY)

    # 1. Create Stakeholders
    print("1. CREATE STAKEHOLDERS:")
    print("-" * 40)

    stakeholders = [
        Stakeholder(stakeholder_id="user_1", stakeholder_type=StakeholderType.INDIVIDUAL, name="User", vulnerability=0.2),
        Stakeholder(stakeholder_id="group_1", stakeholder_type=StakeholderType.GROUP, name="Community", vulnerability=0.4),
        Stakeholder(stakeholder_id="society", stakeholder_type=StakeholderType.SOCIETY, name="Society", vulnerability=0.1),
    ]

    for s in stakeholders:
        print(f"   - {s.name} ({s.stakeholder_type.value}), vulnerability: {s.vulnerability}")
    print()

    # 2. Create Ethical Action
    print("2. CREATE ACTION (Low Risk):")
    print("-" * 40)

    action = EthicalAction(
        name="data_collection",
        description="Collect anonymized usage data",
        potential_harms=[
            Harm(harm_type=HarmType.PRIVACY, severity=HarmSeverity.MINIMAL, probability=0.1, affected_stakeholders=["user_1"])
        ],
        potential_benefits=[
            Benefit(magnitude=3.0, probability=0.8, beneficiaries=["user_1", "group_1"], description="Improved service")
        ],
        stakeholders=stakeholders
    )

    print(f"   Action: {action.name}")
    print(f"   Harms: {len(action.potential_harms)}")
    print(f"   Benefits: {len(action.potential_benefits)}")
    print()

    # 3. Evaluate Action
    print("3. EVALUATE ACTION:")
    print("-" * 40)

    evaluation = engine.evaluate(action)

    print(f"   Outcome: {evaluation.outcome.value}")
    print(f"   Score: {evaluation.score:.3f}")
    print(f"   Framework scores:")
    for framework, score in evaluation.framework_scores.items():
        print(f"     - {framework}: {score:.3f}")
    print()

    # 4. High Risk Action
    print("4. EVALUATE HIGH-RISK ACTION:")
    print("-" * 40)

    risky_action = EthicalAction(
        name="discriminatory_filtering",
        description="Filter users by demographic",
        potential_harms=[
            Harm(harm_type=HarmType.DISCRIMINATION, severity=HarmSeverity.SIGNIFICANT, probability=0.9, affected_stakeholders=["group_1"]),
            Harm(harm_type=HarmType.PSYCHOLOGICAL, severity=HarmSeverity.MODERATE, probability=0.7, affected_stakeholders=["user_1"])
        ],
        potential_benefits=[
            Benefit(magnitude=2.0, probability=0.5, beneficiaries=["society"])
        ],
        stakeholders=stakeholders
    )

    risky_eval = engine.evaluate(risky_action)

    print(f"   Action: {risky_action.name}")
    print(f"   Outcome: {risky_eval.outcome.value}")
    print(f"   Score: {risky_eval.score:.3f}")
    print(f"   Violations: {risky_eval.violated_principles}")
    print()

    # 5. Constraint Violation
    print("5. CONSTRAINT VIOLATION:")
    print("-" * 40)

    harmful_action = EthicalAction(
        name="deceptive_marketing",
        description="Misleading product claims",
        potential_harms=[
            Harm(harm_type=HarmType.DECEPTION, severity=HarmSeverity.SIGNIFICANT, probability=0.95)
        ],
        potential_benefits=[
            Benefit(magnitude=5.0, probability=0.9)
        ],
        stakeholders=stakeholders
    )

    harmful_eval = engine.evaluate(harmful_action)

    print(f"   Action: {harmful_action.name}")
    print(f"   Outcome: {harmful_eval.outcome.value}")
    print(f"   Constraint violations: {harmful_eval.violated_principles}")
    print()

    # 6. Explain Decision
    print("6. EXPLAIN DECISION:")
    print("-" * 40)

    explanation = engine.explain(evaluation)
    for line in explanation.split('\n')[:10]:
        print(f"   {line}")
    print()

    # 7. Quick Checks
    print("7. QUICK CHECKS:")
    print("-" * 40)

    print(f"   Data collection permissible: {engine.is_permissible(action)}")
    print(f"   Discriminatory filtering permissible: {engine.is_permissible(risky_action)}")
    print()

    # 8. Identify Concerns
    print("8. IDENTIFY CONCERNS:")
    print("-" * 40)

    concerns = engine.identify_concerns(risky_action)
    for concern in concerns:
        print(f"   - {concern}")
    print()

    # 9. Risk Assessment
    print("9. RISK ASSESSMENT:")
    print("-" * 40)

    low_risk = engine.assess_risk(action)
    high_risk = engine.assess_risk(risky_action)

    print(f"   Data collection risk: {low_risk:.3f}")
    print(f"   Discriminatory filtering risk: {high_risk:.3f}")
    print()

    # 10. Different Frameworks
    print("10. FRAMEWORK COMPARISON:")
    print("-" * 40)

    engine.set_primary_framework(EthicalFramework.UTILITARIANISM)
    util_eval = engine.evaluate(action)

    engine.set_primary_framework(EthicalFramework.CARE_ETHICS)
    care_eval = engine.evaluate(action)

    print(f"   Utilitarian score: {util_eval.score:.3f}")
    print(f"   Care ethics score: {care_eval.score:.3f}")
    print()

    # 11. Recommendations
    print("11. RECOMMENDATIONS:")
    print("-" * 40)

    for rec in risky_eval.recommendations:
        print(f"   - {rec}")
    print()

    # 12. Audit Trail
    print("12. AUDIT TRAIL:")
    print("-" * 40)

    trail = engine.get_audit_trail(limit=5)
    print(f"   Records: {len(trail)}")
    for record in trail[:3]:
        print(f"   - {record.action.name}: {record.evaluation.outcome.value}")
    print()

    # 13. Add Custom Value
    print("13. ADD CUSTOM VALUE:")
    print("-" * 40)

    engine.add_value(Value(
        value_type=ValueType.BENEFICENCE,
        name="Environmental Protection",
        weight=1.5
    ))

    print("   Added: Environmental Protection")
    print()

    # 14. Harm Analysis
    print("14. HARM ANALYSIS:")
    print("-" * 40)

    harm_scores = engine._harm_analyzer.analyze(risky_action)
    for harm_type, score in harm_scores.items():
        if score > 0:
            print(f"   {harm_type}: {score:.2f}")
    print()

    # 15. Statistics
    print("15. STATISTICS:")
    print("-" * 40)

    stats = engine.get_stats()
    print(f"   Total evaluations: {stats.total_evaluations}")
    print(f"   Approved: {stats.approved_actions}")
    print(f"   Denied: {stats.denied_actions}")
    print(f"   Constraint violations: {stats.constraint_violations}")
    print(f"   Avg eval time: {stats.avg_evaluation_time*1000:.3f}ms")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Ethics Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
