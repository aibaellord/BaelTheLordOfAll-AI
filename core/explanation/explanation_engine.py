#!/usr/bin/env python3
"""
BAEL - Explanation Engine
Advanced explainability and interpretability system.

Features:
- Decision explanation
- Causal reasoning
- Counterfactual analysis
- Feature attribution
- Natural language generation
- Visualization support
- Audit trail
- Confidence scoring
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

class ExplanationType(Enum):
    """Types of explanations."""
    CAUSAL = "causal"
    CONTRASTIVE = "contrastive"
    COUNTERFACTUAL = "counterfactual"
    FEATURE_BASED = "feature_based"
    EXAMPLE_BASED = "example_based"
    RULE_BASED = "rule_based"
    TRACE_BASED = "trace_based"


class AudienceType(Enum):
    """Target audiences."""
    TECHNICAL = "technical"
    NON_TECHNICAL = "non_technical"
    EXPERT = "expert"
    REGULATOR = "regulator"
    USER = "user"


class DetailLevel(Enum):
    """Explanation detail levels."""
    MINIMAL = "minimal"
    SUMMARY = "summary"
    STANDARD = "standard"
    DETAILED = "detailed"
    COMPREHENSIVE = "comprehensive"


class ConfidenceLevel(Enum):
    """Confidence levels."""
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class VisualizationType(Enum):
    """Visualization types."""
    TEXT = "text"
    TABLE = "table"
    TREE = "tree"
    GRAPH = "graph"
    CHART = "chart"
    TIMELINE = "timeline"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Decision:
    """Decision to explain."""
    decision_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    action: str = ""
    inputs: Dict[str, Any] = field(default_factory=dict)
    output: Any = None
    confidence: float = 0.5
    alternatives: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CausalFactor:
    """Causal factor in explanation."""
    factor_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    value: Any = None
    contribution: float = 0.0
    direction: str = "positive"  # positive, negative, neutral
    importance: float = 0.5
    description: str = ""


@dataclass
class Counterfactual:
    """Counterfactual scenario."""
    counterfactual_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    original_input: Dict[str, Any] = field(default_factory=dict)
    modified_input: Dict[str, Any] = field(default_factory=dict)
    changes: List[Tuple[str, Any, Any]] = field(default_factory=list)
    original_output: Any = None
    counterfactual_output: Any = None
    distance: float = 0.0
    feasibility: float = 1.0


@dataclass
class ReasoningStep:
    """Step in reasoning trace."""
    step_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    step_number: int = 0
    action: str = ""
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    rationale: str = ""
    confidence: float = 0.5
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Explanation:
    """Generated explanation."""
    explanation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    decision_id: str = ""
    explanation_type: ExplanationType = ExplanationType.CAUSAL
    audience: AudienceType = AudienceType.USER
    detail_level: DetailLevel = DetailLevel.STANDARD
    summary: str = ""
    full_text: str = ""
    factors: List[CausalFactor] = field(default_factory=list)
    counterfactuals: List[Counterfactual] = field(default_factory=list)
    reasoning_steps: List[ReasoningStep] = field(default_factory=list)
    confidence: float = 0.5
    visualization: Optional[Dict[str, Any]] = None
    generated_at: datetime = field(default_factory=datetime.now)


@dataclass
class FeatureAttribution:
    """Feature attribution."""
    feature_name: str = ""
    feature_value: Any = None
    attribution_score: float = 0.0
    baseline_value: Any = None
    contribution_direction: str = "positive"


@dataclass
class AuditRecord:
    """Audit trail record."""
    record_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    decision_id: str = ""
    explanation_id: str = ""
    actor: str = ""
    action: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ExplanationStats:
    """Explanation engine statistics."""
    total_explanations: int = 0
    explanations_by_type: Dict[str, int] = field(default_factory=dict)
    total_decisions: int = 0
    counterfactuals_generated: int = 0
    audit_records: int = 0


# =============================================================================
# CAUSAL ANALYZER
# =============================================================================

class CausalAnalyzer:
    """Analyze causal factors."""

    def __init__(self):
        self._causal_models: Dict[str, Dict[str, List[str]]] = {}

    def register_causal_model(
        self,
        model_name: str,
        dependencies: Dict[str, List[str]]
    ) -> None:
        """Register causal model (variable -> causes)."""
        self._causal_models[model_name] = dependencies

    def analyze(
        self,
        decision: Decision,
        model_name: Optional[str] = None
    ) -> List[CausalFactor]:
        """Analyze causal factors for decision."""
        factors = []

        # Simple feature importance based on input values
        for name, value in decision.inputs.items():
            importance = self._compute_importance(name, value, decision)
            contribution = self._compute_contribution(name, value, decision)

            direction = "positive" if contribution > 0 else "negative" if contribution < 0 else "neutral"

            factors.append(CausalFactor(
                name=name,
                value=value,
                contribution=abs(contribution),
                direction=direction,
                importance=importance,
                description=self._generate_factor_description(name, value, direction)
            ))

        # Sort by importance
        factors.sort(key=lambda f: f.importance, reverse=True)

        return factors

    def _compute_importance(
        self,
        name: str,
        value: Any,
        decision: Decision
    ) -> float:
        """Compute feature importance."""
        # Simple heuristic based on value magnitude
        if isinstance(value, (int, float)):
            return min(1.0, abs(value) / 100)
        elif isinstance(value, bool):
            return 0.7 if value else 0.3
        elif isinstance(value, str):
            return 0.5
        return 0.5

    def _compute_contribution(
        self,
        name: str,
        value: Any,
        decision: Decision
    ) -> float:
        """Compute feature contribution to decision."""
        # Placeholder - in real implementation would use model
        if isinstance(value, (int, float)):
            return value / 100
        elif isinstance(value, bool):
            return 0.5 if value else -0.5
        return 0.0

    def _generate_factor_description(
        self,
        name: str,
        value: Any,
        direction: str
    ) -> str:
        """Generate human-readable factor description."""
        direction_word = "increased" if direction == "positive" else "decreased" if direction == "negative" else "did not affect"
        return f"The factor '{name}' with value '{value}' {direction_word} the likelihood of this decision."


# =============================================================================
# COUNTERFACTUAL GENERATOR
# =============================================================================

class CounterfactualGenerator:
    """Generate counterfactual explanations."""

    def __init__(self):
        self._prediction_function: Optional[Callable] = None

    def set_prediction_function(
        self,
        func: Callable[[Dict[str, Any]], Any]
    ) -> None:
        """Set the prediction function for counterfactual evaluation."""
        self._prediction_function = func

    def generate(
        self,
        decision: Decision,
        target_output: Optional[Any] = None,
        max_changes: int = 3,
        num_counterfactuals: int = 3
    ) -> List[Counterfactual]:
        """Generate counterfactual explanations."""
        counterfactuals = []

        # Generate candidates by perturbing inputs
        for _ in range(num_counterfactuals * 2):
            modified = dict(decision.inputs)
            changes = []

            # Randomly select features to change
            features = list(decision.inputs.keys())
            num_changes = min(max_changes, len(features))
            features_to_change = random.sample(features, num_changes)

            for feature in features_to_change:
                original_value = decision.inputs[feature]
                new_value = self._perturb_value(original_value)
                modified[feature] = new_value
                changes.append((feature, original_value, new_value))

            # Evaluate counterfactual
            if self._prediction_function:
                cf_output = self._prediction_function(modified)
            else:
                # Simulate different output
                cf_output = not decision.output if isinstance(decision.output, bool) else "alternative"

            # Compute distance
            distance = self._compute_distance(decision.inputs, modified)

            # Check if output changed (for target or any change)
            if target_output is not None:
                if cf_output != target_output:
                    continue
            elif cf_output == decision.output:
                continue

            counterfactuals.append(Counterfactual(
                original_input=decision.inputs,
                modified_input=modified,
                changes=changes,
                original_output=decision.output,
                counterfactual_output=cf_output,
                distance=distance,
                feasibility=1.0 - distance
            ))

        # Sort by distance and return top N
        counterfactuals.sort(key=lambda c: c.distance)
        return counterfactuals[:num_counterfactuals]

    def _perturb_value(self, value: Any) -> Any:
        """Perturb a value to create counterfactual."""
        if isinstance(value, bool):
            return not value
        elif isinstance(value, int):
            return value + random.randint(-10, 10)
        elif isinstance(value, float):
            return value + random.gauss(0, value * 0.2 if value != 0 else 1)
        elif isinstance(value, str):
            alternatives = ["alternative", "different", "other"]
            return random.choice(alternatives)
        return value

    def _compute_distance(
        self,
        original: Dict[str, Any],
        modified: Dict[str, Any]
    ) -> float:
        """Compute distance between original and modified inputs."""
        total_diff = 0.0
        count = 0

        for key in original:
            v1 = original[key]
            v2 = modified.get(key, v1)

            if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
                diff = abs(v1 - v2) / (abs(v1) + 1)
                total_diff += min(1.0, diff)
            elif v1 != v2:
                total_diff += 1.0

            count += 1

        return total_diff / count if count > 0 else 0.0


# =============================================================================
# FEATURE ATTRIBUTOR
# =============================================================================

class FeatureAttributor:
    """Compute feature attributions."""

    def __init__(self):
        self._baseline: Dict[str, Any] = {}

    def set_baseline(self, baseline: Dict[str, Any]) -> None:
        """Set baseline for attribution."""
        self._baseline = baseline

    def compute_attributions(
        self,
        decision: Decision,
        prediction_function: Optional[Callable] = None
    ) -> List[FeatureAttribution]:
        """Compute feature attributions using Shapley-like approach."""
        attributions = []

        features = list(decision.inputs.keys())
        n = len(features)

        if n == 0:
            return attributions

        # Simplified Shapley approximation
        for feature in features:
            marginal_contributions = []

            # Sample permutations
            for _ in range(min(10, math.factorial(n))):
                perm = features.copy()
                random.shuffle(perm)

                # Compute marginal contribution
                idx = perm.index(feature)

                # Value without feature
                without = {f: decision.inputs[f] for f in perm[:idx]}
                without.update({f: self._baseline.get(f, 0) for f in perm[idx:]})

                # Value with feature
                with_feature = {f: decision.inputs[f] for f in perm[:idx+1]}
                with_feature.update({f: self._baseline.get(f, 0) for f in perm[idx+1:]})

                # Compute values (simplified)
                v_without = sum(v for v in without.values() if isinstance(v, (int, float)))
                v_with = sum(v for v in with_feature.values() if isinstance(v, (int, float)))

                marginal_contributions.append(v_with - v_without)

            # Average marginal contribution
            attribution = sum(marginal_contributions) / len(marginal_contributions)

            attributions.append(FeatureAttribution(
                feature_name=feature,
                feature_value=decision.inputs[feature],
                attribution_score=attribution,
                baseline_value=self._baseline.get(feature),
                contribution_direction="positive" if attribution > 0 else "negative"
            ))

        # Normalize attributions
        total = sum(abs(a.attribution_score) for a in attributions)
        if total > 0:
            for attr in attributions:
                attr.attribution_score /= total

        # Sort by absolute attribution
        attributions.sort(key=lambda a: abs(a.attribution_score), reverse=True)

        return attributions


# =============================================================================
# TEXT GENERATOR
# =============================================================================

class ExplanationTextGenerator:
    """Generate natural language explanations."""

    def __init__(self):
        self._templates = {
            ExplanationType.CAUSAL: {
                DetailLevel.MINIMAL: "The decision was made because {top_factor}.",
                DetailLevel.SUMMARY: "The decision was primarily influenced by {top_factors}.",
                DetailLevel.STANDARD: "The decision '{action}' was made based on the following factors: {factors_list}. The most important factor was {top_factor}, which had a {direction} influence on the outcome.",
                DetailLevel.DETAILED: "A comprehensive analysis shows that the decision '{action}' was driven by multiple factors. {detailed_analysis}",
            },
            ExplanationType.COUNTERFACTUAL: {
                DetailLevel.MINIMAL: "A different outcome would occur if {change}.",
                DetailLevel.SUMMARY: "The outcome would change if: {changes_list}.",
                DetailLevel.STANDARD: "If {changes_description}, then the result would have been '{alternative}' instead of '{original}'.",
            },
        }

    def generate(
        self,
        decision: Decision,
        factors: List[CausalFactor],
        counterfactuals: List[Counterfactual],
        explanation_type: ExplanationType,
        audience: AudienceType,
        detail_level: DetailLevel
    ) -> Tuple[str, str]:
        """Generate summary and full text explanation."""
        # Generate summary
        summary = self._generate_summary(
            decision, factors, counterfactuals, explanation_type
        )

        # Generate full text
        full_text = self._generate_full_text(
            decision, factors, counterfactuals,
            explanation_type, audience, detail_level
        )

        return summary, full_text

    def _generate_summary(
        self,
        decision: Decision,
        factors: List[CausalFactor],
        counterfactuals: List[Counterfactual],
        explanation_type: ExplanationType
    ) -> str:
        """Generate summary."""
        if factors:
            top_factor = factors[0].name
            return f"The decision '{decision.action}' was primarily driven by '{top_factor}'."
        return f"The decision '{decision.action}' was made based on the given inputs."

    def _generate_full_text(
        self,
        decision: Decision,
        factors: List[CausalFactor],
        counterfactuals: List[Counterfactual],
        explanation_type: ExplanationType,
        audience: AudienceType,
        detail_level: DetailLevel
    ) -> str:
        """Generate full explanation text."""
        parts = []

        # Introduction
        parts.append(f"## Decision Explanation\n")
        parts.append(f"**Decision:** {decision.action}\n")
        parts.append(f"**Confidence:** {decision.confidence:.1%}\n\n")

        # Factors
        if factors:
            parts.append("### Key Factors\n")
            for i, factor in enumerate(factors[:5], 1):
                parts.append(f"{i}. **{factor.name}**: {factor.description}\n")
            parts.append("\n")

        # Counterfactuals
        if counterfactuals and explanation_type in [ExplanationType.COUNTERFACTUAL, ExplanationType.CONTRASTIVE]:
            parts.append("### What Would Change the Outcome\n")
            for cf in counterfactuals[:3]:
                changes = ", ".join([f"{c[0]}: {c[1]} → {c[2]}" for c in cf.changes])
                parts.append(f"- If {changes}, then the outcome would be '{cf.counterfactual_output}'\n")
            parts.append("\n")

        # Audience-specific additions
        if audience == AudienceType.TECHNICAL:
            parts.append("### Technical Details\n")
            parts.append(f"- Input features: {len(decision.inputs)}\n")
            parts.append(f"- Alternatives considered: {len(decision.alternatives)}\n")

        return "".join(parts)


# =============================================================================
# AUDIT MANAGER
# =============================================================================

class AuditManager:
    """Manage audit trail."""

    def __init__(self):
        self._records: List[AuditRecord] = []

    def record(
        self,
        decision_id: str,
        explanation_id: str,
        actor: str,
        action: str,
        details: Optional[Dict[str, Any]] = None
    ) -> AuditRecord:
        """Record audit event."""
        record = AuditRecord(
            decision_id=decision_id,
            explanation_id=explanation_id,
            actor=actor,
            action=action,
            details=details or {}
        )

        self._records.append(record)
        return record

    def get_records(
        self,
        decision_id: Optional[str] = None,
        actor: Optional[str] = None,
        since: Optional[datetime] = None
    ) -> List[AuditRecord]:
        """Get audit records with optional filters."""
        records = self._records

        if decision_id:
            records = [r for r in records if r.decision_id == decision_id]
        if actor:
            records = [r for r in records if r.actor == actor]
        if since:
            records = [r for r in records if r.timestamp >= since]

        return records

    def export(self) -> List[Dict[str, Any]]:
        """Export audit trail."""
        return [
            {
                "record_id": r.record_id,
                "decision_id": r.decision_id,
                "explanation_id": r.explanation_id,
                "actor": r.actor,
                "action": r.action,
                "details": r.details,
                "timestamp": r.timestamp.isoformat()
            }
            for r in self._records
        ]


# =============================================================================
# EXPLANATION ENGINE
# =============================================================================

class ExplanationEngine:
    """
    Explanation Engine for BAEL.

    Advanced explainability and interpretability system.
    """

    def __init__(self):
        self._causal_analyzer = CausalAnalyzer()
        self._counterfactual_generator = CounterfactualGenerator()
        self._feature_attributor = FeatureAttributor()
        self._text_generator = ExplanationTextGenerator()
        self._audit_manager = AuditManager()

        self._decisions: Dict[str, Decision] = {}
        self._explanations: Dict[str, Explanation] = {}
        self._reasoning_traces: Dict[str, List[ReasoningStep]] = {}
        self._stats = ExplanationStats()

    # -------------------------------------------------------------------------
    # DECISION MANAGEMENT
    # -------------------------------------------------------------------------

    def register_decision(
        self,
        action: str,
        inputs: Dict[str, Any],
        output: Any,
        confidence: float = 0.5,
        alternatives: Optional[List[Dict[str, Any]]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Decision:
        """Register a decision to be explained."""
        decision = Decision(
            action=action,
            inputs=inputs,
            output=output,
            confidence=confidence,
            alternatives=alternatives or [],
            context=context or {}
        )

        self._decisions[decision.decision_id] = decision
        self._stats.total_decisions += 1

        # Audit
        self._audit_manager.record(
            decision.decision_id,
            "",
            "system",
            "decision_registered",
            {"action": action}
        )

        return decision

    def get_decision(self, decision_id: str) -> Optional[Decision]:
        """Get decision by ID."""
        return self._decisions.get(decision_id)

    # -------------------------------------------------------------------------
    # REASONING TRACE
    # -------------------------------------------------------------------------

    def add_reasoning_step(
        self,
        decision_id: str,
        action: str,
        inputs: Dict[str, Any],
        outputs: Dict[str, Any],
        rationale: str,
        confidence: float = 0.5
    ) -> ReasoningStep:
        """Add reasoning step to trace."""
        if decision_id not in self._reasoning_traces:
            self._reasoning_traces[decision_id] = []

        step_number = len(self._reasoning_traces[decision_id]) + 1

        step = ReasoningStep(
            step_number=step_number,
            action=action,
            inputs=inputs,
            outputs=outputs,
            rationale=rationale,
            confidence=confidence
        )

        self._reasoning_traces[decision_id].append(step)

        return step

    def get_reasoning_trace(
        self,
        decision_id: str
    ) -> List[ReasoningStep]:
        """Get reasoning trace for decision."""
        return self._reasoning_traces.get(decision_id, [])

    # -------------------------------------------------------------------------
    # EXPLANATION GENERATION
    # -------------------------------------------------------------------------

    def explain(
        self,
        decision_id: str,
        explanation_type: ExplanationType = ExplanationType.CAUSAL,
        audience: AudienceType = AudienceType.USER,
        detail_level: DetailLevel = DetailLevel.STANDARD
    ) -> Explanation:
        """Generate explanation for decision."""
        decision = self._decisions.get(decision_id)
        if not decision:
            return Explanation(summary="Decision not found", full_text="Decision not found")

        # Analyze causal factors
        factors = self._causal_analyzer.analyze(decision)

        # Generate counterfactuals if needed
        counterfactuals = []
        if explanation_type in [ExplanationType.COUNTERFACTUAL, ExplanationType.CONTRASTIVE]:
            counterfactuals = self._counterfactual_generator.generate(decision)
            self._stats.counterfactuals_generated += len(counterfactuals)

        # Get reasoning trace
        reasoning_steps = self.get_reasoning_trace(decision_id)

        # Generate text
        summary, full_text = self._text_generator.generate(
            decision, factors, counterfactuals,
            explanation_type, audience, detail_level
        )

        # Create explanation
        explanation = Explanation(
            decision_id=decision_id,
            explanation_type=explanation_type,
            audience=audience,
            detail_level=detail_level,
            summary=summary,
            full_text=full_text,
            factors=factors,
            counterfactuals=counterfactuals,
            reasoning_steps=reasoning_steps,
            confidence=decision.confidence
        )

        self._explanations[explanation.explanation_id] = explanation

        # Update stats
        self._stats.total_explanations += 1
        self._stats.explanations_by_type[explanation_type.value] = \
            self._stats.explanations_by_type.get(explanation_type.value, 0) + 1

        # Audit
        self._audit_manager.record(
            decision_id,
            explanation.explanation_id,
            "system",
            "explanation_generated",
            {"type": explanation_type.value, "audience": audience.value}
        )
        self._stats.audit_records += 1

        return explanation

    def explain_quick(
        self,
        decision_id: str
    ) -> str:
        """Generate quick one-line explanation."""
        decision = self._decisions.get(decision_id)
        if not decision:
            return "Decision not found"

        factors = self._causal_analyzer.analyze(decision)

        if factors:
            top_factor = factors[0]
            return f"Decision '{decision.action}' was mainly due to {top_factor.name}={top_factor.value}"

        return f"Decision '{decision.action}' was made based on provided inputs"

    # -------------------------------------------------------------------------
    # FEATURE ATTRIBUTION
    # -------------------------------------------------------------------------

    def get_feature_attributions(
        self,
        decision_id: str,
        baseline: Optional[Dict[str, Any]] = None
    ) -> List[FeatureAttribution]:
        """Get feature attributions for decision."""
        decision = self._decisions.get(decision_id)
        if not decision:
            return []

        if baseline:
            self._feature_attributor.set_baseline(baseline)

        return self._feature_attributor.compute_attributions(decision)

    # -------------------------------------------------------------------------
    # COUNTERFACTUAL ANALYSIS
    # -------------------------------------------------------------------------

    def generate_counterfactuals(
        self,
        decision_id: str,
        target_output: Optional[Any] = None,
        max_changes: int = 3,
        num_counterfactuals: int = 5
    ) -> List[Counterfactual]:
        """Generate counterfactual explanations."""
        decision = self._decisions.get(decision_id)
        if not decision:
            return []

        counterfactuals = self._counterfactual_generator.generate(
            decision,
            target_output,
            max_changes,
            num_counterfactuals
        )

        self._stats.counterfactuals_generated += len(counterfactuals)

        return counterfactuals

    # -------------------------------------------------------------------------
    # CONTRASTIVE EXPLANATIONS
    # -------------------------------------------------------------------------

    def explain_contrast(
        self,
        decision_id: str,
        alternative: str
    ) -> str:
        """Explain why decision was made instead of alternative."""
        decision = self._decisions.get(decision_id)
        if not decision:
            return "Decision not found"

        factors = self._causal_analyzer.analyze(decision)

        # Find factors that support the actual decision over the alternative
        parts = []
        parts.append(f"The decision '{decision.action}' was chosen over '{alternative}' because:\n")

        for factor in factors[:3]:
            if factor.direction == "positive":
                parts.append(f"- {factor.name} favored '{decision.action}'\n")

        return "".join(parts)

    # -------------------------------------------------------------------------
    # VISUALIZATION
    # -------------------------------------------------------------------------

    def get_visualization_data(
        self,
        explanation_id: str,
        viz_type: VisualizationType = VisualizationType.TABLE
    ) -> Dict[str, Any]:
        """Get data for visualization."""
        explanation = self._explanations.get(explanation_id)
        if not explanation:
            return {}

        if viz_type == VisualizationType.TABLE:
            return {
                "type": "table",
                "headers": ["Factor", "Value", "Importance", "Direction"],
                "rows": [
                    [f.name, str(f.value), f"{f.importance:.2f}", f.direction]
                    for f in explanation.factors
                ]
            }

        elif viz_type == VisualizationType.CHART:
            return {
                "type": "bar_chart",
                "labels": [f.name for f in explanation.factors],
                "values": [f.importance for f in explanation.factors],
                "title": "Feature Importance"
            }

        elif viz_type == VisualizationType.TREE:
            return {
                "type": "decision_tree",
                "nodes": [
                    {"id": f.factor_id, "label": f.name, "value": f.importance}
                    for f in explanation.factors
                ]
            }

        elif viz_type == VisualizationType.TIMELINE:
            return {
                "type": "timeline",
                "events": [
                    {
                        "step": s.step_number,
                        "action": s.action,
                        "rationale": s.rationale
                    }
                    for s in explanation.reasoning_steps
                ]
            }

        return {"type": viz_type.value, "data": {}}

    # -------------------------------------------------------------------------
    # AUDIT
    # -------------------------------------------------------------------------

    def get_audit_trail(
        self,
        decision_id: Optional[str] = None
    ) -> List[AuditRecord]:
        """Get audit trail."""
        return self._audit_manager.get_records(decision_id=decision_id)

    def export_audit_trail(self) -> List[Dict[str, Any]]:
        """Export full audit trail."""
        return self._audit_manager.export()

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def get_stats(self) -> ExplanationStats:
        """Get engine statistics."""
        return self._stats


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Explanation Engine."""
    print("=" * 70)
    print("BAEL - EXPLANATION ENGINE DEMO")
    print("Advanced Explainability and Interpretability System")
    print("=" * 70)
    print()

    engine = ExplanationEngine()

    # 1. Register Decision
    print("1. REGISTER DECISION:")
    print("-" * 40)

    decision = engine.register_decision(
        action="approve_loan",
        inputs={
            "income": 75000,
            "credit_score": 720,
            "debt_ratio": 0.3,
            "employment_years": 5,
            "loan_amount": 200000
        },
        output=True,
        confidence=0.85,
        alternatives=[
            {"action": "deny_loan", "reason": "credit_score < 700"},
            {"action": "request_review", "reason": "borderline case"}
        ],
        context={"applicant_id": "A12345", "application_date": "2024-01-15"}
    )

    print(f"   Decision ID: {decision.decision_id[:8]}...")
    print(f"   Action: {decision.action}")
    print(f"   Confidence: {decision.confidence:.1%}")
    print()

    # 2. Add Reasoning Steps
    print("2. ADD REASONING STEPS:")
    print("-" * 40)

    engine.add_reasoning_step(
        decision.decision_id,
        "check_credit_score",
        {"credit_score": 720},
        {"meets_threshold": True},
        "Credit score 720 exceeds minimum requirement of 650",
        0.95
    )

    engine.add_reasoning_step(
        decision.decision_id,
        "check_debt_ratio",
        {"debt_ratio": 0.3},
        {"acceptable": True},
        "Debt ratio 30% is below maximum threshold of 43%",
        0.90
    )

    engine.add_reasoning_step(
        decision.decision_id,
        "calculate_risk",
        {"all_factors": True},
        {"risk_level": "low"},
        "Combined factors indicate low risk profile",
        0.85
    )

    trace = engine.get_reasoning_trace(decision.decision_id)
    for step in trace:
        print(f"   Step {step.step_number}: {step.action} - {step.rationale[:50]}...")
    print()

    # 3. Generate Causal Explanation
    print("3. GENERATE CAUSAL EXPLANATION:")
    print("-" * 40)

    explanation = engine.explain(
        decision.decision_id,
        explanation_type=ExplanationType.CAUSAL,
        audience=AudienceType.USER,
        detail_level=DetailLevel.STANDARD
    )

    print(f"   Summary: {explanation.summary}")
    print()
    print("   Top Factors:")
    for factor in explanation.factors[:3]:
        print(f"     - {factor.name}: {factor.direction} (importance: {factor.importance:.2f})")
    print()

    # 4. Quick Explanation
    print("4. QUICK EXPLANATION:")
    print("-" * 40)

    quick = engine.explain_quick(decision.decision_id)
    print(f"   {quick}")
    print()

    # 5. Counterfactual Analysis
    print("5. COUNTERFACTUAL ANALYSIS:")
    print("-" * 40)

    counterfactuals = engine.generate_counterfactuals(
        decision.decision_id,
        target_output=False,
        max_changes=2,
        num_counterfactuals=3
    )

    for i, cf in enumerate(counterfactuals, 1):
        print(f"   Scenario {i}:")
        for change in cf.changes:
            print(f"     - If {change[0]}: {change[1]} → {change[2]}")
        print(f"     Outcome: {cf.original_output} → {cf.counterfactual_output}")
    print()

    # 6. Feature Attributions
    print("6. FEATURE ATTRIBUTIONS:")
    print("-" * 40)

    attributions = engine.get_feature_attributions(
        decision.decision_id,
        baseline={"income": 50000, "credit_score": 600, "debt_ratio": 0.5}
    )

    for attr in attributions:
        direction = "↑" if attr.contribution_direction == "positive" else "↓"
        print(f"   {attr.feature_name}: {attr.attribution_score:+.3f} {direction}")
    print()

    # 7. Contrastive Explanation
    print("7. CONTRASTIVE EXPLANATION:")
    print("-" * 40)

    contrast = engine.explain_contrast(decision.decision_id, "deny_loan")
    print(contrast)

    # 8. Visualization Data
    print("8. VISUALIZATION DATA:")
    print("-" * 40)

    table_viz = engine.get_visualization_data(
        explanation.explanation_id,
        VisualizationType.TABLE
    )

    print(f"   Type: {table_viz.get('type')}")
    print(f"   Headers: {table_viz.get('headers')}")
    print(f"   Rows: {len(table_viz.get('rows', []))} rows")
    print()

    # 9. Timeline Visualization
    print("9. TIMELINE VISUALIZATION:")
    print("-" * 40)

    timeline = engine.get_visualization_data(
        explanation.explanation_id,
        VisualizationType.TIMELINE
    )

    for event in timeline.get("events", []):
        print(f"   Step {event['step']}: {event['action']}")
    print()

    # 10. Full Explanation Text
    print("10. FULL EXPLANATION TEXT:")
    print("-" * 40)

    print(explanation.full_text[:500])
    print("   ...")
    print()

    # 11. Detailed Explanation
    print("11. DETAILED EXPLANATION:")
    print("-" * 40)

    detailed = engine.explain(
        decision.decision_id,
        explanation_type=ExplanationType.CAUSAL,
        audience=AudienceType.TECHNICAL,
        detail_level=DetailLevel.DETAILED
    )

    print(f"   Length: {len(detailed.full_text)} characters")
    print(f"   Factors: {len(detailed.factors)}")
    print(f"   Reasoning steps: {len(detailed.reasoning_steps)}")
    print()

    # 12. Audit Trail
    print("12. AUDIT TRAIL:")
    print("-" * 40)

    audit = engine.get_audit_trail(decision.decision_id)
    for record in audit:
        print(f"   [{record.timestamp.strftime('%H:%M:%S')}] {record.action}")
    print()

    # 13. Export Audit
    print("13. EXPORT AUDIT:")
    print("-" * 40)

    exported = engine.export_audit_trail()
    print(f"   Exported {len(exported)} audit records")
    print()

    # 14. Statistics
    print("14. STATISTICS:")
    print("-" * 40)

    stats = engine.get_stats()
    print(f"   Total explanations: {stats.total_explanations}")
    print(f"   Total decisions: {stats.total_decisions}")
    print(f"   Counterfactuals generated: {stats.counterfactuals_generated}")
    print(f"   Audit records: {stats.audit_records}")
    print(f"   By type: {stats.explanations_by_type}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Explanation Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
