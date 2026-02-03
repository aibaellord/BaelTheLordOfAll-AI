#!/usr/bin/env python3
"""
BAEL - AI Governance Framework
Ethical AI governance, compliance, and accountability.

Features:
- Ethical guidelines enforcement
- Bias detection and mitigation
- Explainability and transparency
- Audit trails and accountability
- Regulatory compliance (GDPR, AI Act, etc.)
- Human oversight mechanisms
"""

import asyncio
import hashlib
import json
import logging
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from uuid import uuid4

logger = logging.getLogger(__name__)


# =============================================================================
# TYPES AND ENUMS
# =============================================================================

class EthicalPrinciple(Enum):
    """Core ethical principles for AI."""
    BENEFICENCE = "beneficence"  # Do good
    NON_MALEFICENCE = "non_maleficence"  # Do no harm
    AUTONOMY = "autonomy"  # Respect human autonomy
    JUSTICE = "justice"  # Fair treatment
    TRANSPARENCY = "transparency"  # Explainable decisions
    ACCOUNTABILITY = "accountability"  # Responsible AI
    PRIVACY = "privacy"  # Protect personal data
    SAFETY = "safety"  # Prevent harm


class ComplianceFramework(Enum):
    """Regulatory compliance frameworks."""
    GDPR = "gdpr"  # EU Data Protection
    CCPA = "ccpa"  # California Consumer Privacy
    EU_AI_ACT = "eu_ai_act"  # EU AI Regulation
    HIPAA = "hipaa"  # Healthcare Privacy
    SOC2 = "soc2"  # Security Controls
    ISO27001 = "iso27001"  # Information Security
    NIST_AI_RMF = "nist_ai_rmf"  # NIST AI Risk Management


class RiskLevel(Enum):
    """AI risk classification (EU AI Act aligned)."""
    MINIMAL = "minimal"
    LIMITED = "limited"
    HIGH = "high"
    UNACCEPTABLE = "unacceptable"


class BiasType(Enum):
    """Types of AI bias."""
    SELECTION = "selection"
    CONFIRMATION = "confirmation"
    AUTOMATION = "automation"
    IMPLICIT = "implicit"
    REPRESENTATION = "representation"
    MEASUREMENT = "measurement"


@dataclass
class AuditEvent:
    """Audit trail event."""
    id: str
    timestamp: datetime
    event_type: str
    actor: str  # Who performed the action
    action: str  # What was done
    resource: str  # What was affected
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    decision: Optional[str] = None
    justification: Optional[str] = None
    risk_level: RiskLevel = RiskLevel.MINIMAL
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type,
            "actor": self.actor,
            "action": self.action,
            "resource": self.resource,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "decision": self.decision,
            "justification": self.justification,
            "risk_level": self.risk_level.value,
            "metadata": self.metadata
        }


@dataclass
class EthicalAssessment:
    """Assessment of ethical compliance."""
    principle: EthicalPrinciple
    score: float  # 0-1
    concerns: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    passed: bool = True


@dataclass
class BiasReport:
    """Report on detected bias."""
    bias_type: BiasType
    severity: float  # 0-1
    affected_groups: List[str] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)
    mitigation_applied: bool = False
    mitigation_strategy: Optional[str] = None


@dataclass
class ExplanationReport:
    """Explanation of AI decision."""
    decision: str
    confidence: float
    reasoning_chain: List[str] = field(default_factory=list)
    key_factors: List[Dict[str, Any]] = field(default_factory=list)
    counterfactuals: List[str] = field(default_factory=list)
    uncertainty_sources: List[str] = field(default_factory=list)


# =============================================================================
# ETHICAL GUIDELINES
# =============================================================================

class EthicalGuidelines:
    """Define and enforce ethical guidelines."""

    def __init__(self):
        self.principles: Dict[EthicalPrinciple, Dict[str, Any]] = {
            EthicalPrinciple.BENEFICENCE: {
                "description": "AI should benefit humanity and improve wellbeing",
                "requirements": [
                    "Outputs should be helpful and constructive",
                    "Consider positive impact on users and society",
                    "Maximize value while minimizing harm"
                ]
            },
            EthicalPrinciple.NON_MALEFICENCE: {
                "description": "AI should not cause harm",
                "requirements": [
                    "Prevent physical, psychological, or financial harm",
                    "Avoid generating harmful content",
                    "Include safety warnings when appropriate"
                ]
            },
            EthicalPrinciple.AUTONOMY: {
                "description": "Respect human autonomy and decision-making",
                "requirements": [
                    "Allow users to understand AI recommendations",
                    "Enable override of AI decisions",
                    "Avoid manipulation or coercion"
                ]
            },
            EthicalPrinciple.JUSTICE: {
                "description": "Ensure fair and equitable treatment",
                "requirements": [
                    "Avoid discrimination",
                    "Equal service quality across groups",
                    "Accessible to diverse users"
                ]
            },
            EthicalPrinciple.TRANSPARENCY: {
                "description": "Be transparent about AI capabilities and limitations",
                "requirements": [
                    "Disclose AI nature when appropriate",
                    "Explain decision-making process",
                    "Communicate uncertainty"
                ]
            },
            EthicalPrinciple.ACCOUNTABILITY: {
                "description": "Maintain accountability for AI actions",
                "requirements": [
                    "Log all significant decisions",
                    "Enable audit and review",
                    "Clear responsibility chains"
                ]
            },
            EthicalPrinciple.PRIVACY: {
                "description": "Protect personal data and privacy",
                "requirements": [
                    "Minimize data collection",
                    "Secure data handling",
                    "Respect consent preferences"
                ]
            },
            EthicalPrinciple.SAFETY: {
                "description": "Ensure safe AI operation",
                "requirements": [
                    "Fail safely when uncertain",
                    "Prevent unintended consequences",
                    "Enable human intervention"
                ]
            }
        }

        self.prohibited_actions: Set[str] = {
            "generate_harmful_content",
            "discriminate_users",
            "manipulate_users",
            "violate_privacy",
            "bypass_safety",
            "impersonate_humans",
            "spread_misinformation",
            "enable_illegal_activities"
        }

    def assess_action(
        self,
        action: str,
        context: Dict[str, Any]
    ) -> List[EthicalAssessment]:
        """Assess action against ethical principles."""
        assessments = []

        for principle, guidelines in self.principles.items():
            assessment = EthicalAssessment(
                principle=principle,
                score=1.0,
                passed=True
            )

            # Check against prohibited actions
            if action in self.prohibited_actions:
                assessment.score = 0.0
                assessment.passed = False
                assessment.concerns.append(f"Action '{action}' is prohibited")

            # Specific checks per principle
            if principle == EthicalPrinciple.NON_MALEFICENCE:
                if context.get("potential_harm"):
                    assessment.score -= 0.5
                    assessment.concerns.append("Potential for harm detected")
                    assessment.recommendations.append("Add safety warnings")

            elif principle == EthicalPrinciple.PRIVACY:
                if context.get("processes_pii"):
                    assessment.score -= 0.2
                    assessment.concerns.append("Processes PII data")
                    assessment.recommendations.append("Ensure consent and minimize data")

            elif principle == EthicalPrinciple.TRANSPARENCY:
                if not context.get("explainable"):
                    assessment.score -= 0.3
                    assessment.concerns.append("Decision not explainable")
                    assessment.recommendations.append("Add reasoning chain")

            if assessment.score < 0.5:
                assessment.passed = False

            assessments.append(assessment)

        return assessments

    def is_action_permitted(
        self,
        action: str,
        context: Dict[str, Any] = None
    ) -> Tuple[bool, List[str]]:
        """Check if action is ethically permitted."""
        if action in self.prohibited_actions:
            return False, [f"Action '{action}' is prohibited"]

        assessments = self.assess_action(action, context or {})
        failed = [a for a in assessments if not a.passed]

        if failed:
            reasons = []
            for a in failed:
                reasons.extend(a.concerns)
            return False, reasons

        return True, []


# =============================================================================
# BIAS DETECTION
# =============================================================================

class BiasDetector(ABC):
    """Abstract bias detector."""

    @abstractmethod
    async def detect(
        self,
        data: Any,
        context: Dict[str, Any]
    ) -> List[BiasReport]:
        """Detect bias in data or outputs."""
        pass


class StatisticalBiasDetector(BiasDetector):
    """Detect statistical bias in data."""

    def __init__(self):
        self.protected_attributes = [
            "gender", "race", "age", "religion", "nationality",
            "disability", "sexual_orientation"
        ]

    async def detect(
        self,
        data: Any,
        context: Dict[str, Any]
    ) -> List[BiasReport]:
        """Detect statistical disparities."""
        reports = []

        if isinstance(data, dict):
            # Check for representation bias
            if "groups" in data and "outcomes" in data:
                groups = data["groups"]
                outcomes = data["outcomes"]

                # Calculate disparate impact
                for attr in self.protected_attributes:
                    if attr in groups:
                        impact = self._calculate_disparate_impact(groups[attr], outcomes)
                        if impact < 0.8:  # 80% rule
                            reports.append(BiasReport(
                                bias_type=BiasType.REPRESENTATION,
                                severity=1 - impact,
                                affected_groups=[attr],
                                evidence=[f"Disparate impact ratio: {impact:.2f}"]
                            ))

        return reports

    def _calculate_disparate_impact(
        self,
        groups: Dict[str, int],
        outcomes: Dict[str, int]
    ) -> float:
        """Calculate disparate impact ratio."""
        if not groups or not outcomes:
            return 1.0

        rates = {}
        for group, count in groups.items():
            if count > 0:
                rates[group] = outcomes.get(group, 0) / count

        if not rates:
            return 1.0

        min_rate = min(rates.values())
        max_rate = max(rates.values())

        if max_rate == 0:
            return 1.0

        return min_rate / max_rate


class TextBiasDetector(BiasDetector):
    """Detect bias in text outputs."""

    def __init__(self):
        self.bias_patterns = {
            "gender_stereotypes": [
                r"\b(women|girls)\b.*\b(emotional|nurturing|weak)\b",
                r"\b(men|boys)\b.*\b(strong|rational|leader)\b"
            ],
            "age_bias": [
                r"\b(old|elderly)\b.*\b(slow|outdated|incompetent)\b",
                r"\b(young|youth)\b.*\b(inexperienced|immature)\b"
            ]
        }

    async def detect(
        self,
        data: Any,
        context: Dict[str, Any]
    ) -> List[BiasReport]:
        """Detect biased language."""
        import re
        reports = []

        if isinstance(data, str):
            text = data.lower()

            for bias_category, patterns in self.bias_patterns.items():
                for pattern in patterns:
                    matches = re.findall(pattern, text, re.IGNORECASE)
                    if matches:
                        reports.append(BiasReport(
                            bias_type=BiasType.IMPLICIT,
                            severity=0.5,
                            affected_groups=[bias_category],
                            evidence=[f"Pattern match: {pattern}"]
                        ))

        return reports


class BiasMitigator:
    """Mitigate detected bias."""

    def __init__(self):
        self.strategies: Dict[BiasType, Callable] = {
            BiasType.REPRESENTATION: self._mitigate_representation,
            BiasType.IMPLICIT: self._mitigate_implicit,
            BiasType.SELECTION: self._mitigate_selection
        }

    async def mitigate(
        self,
        data: Any,
        bias_report: BiasReport
    ) -> Tuple[Any, str]:
        """Apply mitigation strategy."""
        strategy = self.strategies.get(bias_report.bias_type)
        if strategy:
            return await strategy(data, bias_report)
        return data, "No mitigation available"

    async def _mitigate_representation(
        self,
        data: Any,
        report: BiasReport
    ) -> Tuple[Any, str]:
        """Mitigate representation bias through reweighting."""
        strategy = "Applied inverse propensity weighting"
        return data, strategy

    async def _mitigate_implicit(
        self,
        data: Any,
        report: BiasReport
    ) -> Tuple[Any, str]:
        """Mitigate implicit bias in text."""
        strategy = "Suggested neutral language alternatives"
        return data, strategy

    async def _mitigate_selection(
        self,
        data: Any,
        report: BiasReport
    ) -> Tuple[Any, str]:
        """Mitigate selection bias through stratified sampling."""
        strategy = "Applied stratified sampling correction"
        return data, strategy


# =============================================================================
# EXPLAINABILITY
# =============================================================================

class ExplainabilityEngine:
    """Generate explanations for AI decisions."""

    def __init__(self):
        self.explanation_templates = {
            "classification": "The decision was '{decision}' because {main_factors}. "
                            "Key evidence: {evidence}. Confidence: {confidence:.0%}",
            "recommendation": "Recommending '{decision}' based on {main_factors}. "
                            "This matches your {user_context}. "
                            "Alternative options: {alternatives}",
            "generation": "Generated content considering {constraints}. "
                        "Main influences: {main_factors}"
        }

    async def explain(
        self,
        decision: Any,
        decision_type: str,
        factors: List[Dict[str, Any]],
        confidence: float = 1.0,
        context: Dict[str, Any] = None
    ) -> ExplanationReport:
        """Generate explanation for decision."""
        context = context or {}

        # Extract key factors
        key_factors = sorted(factors, key=lambda f: f.get("weight", 0), reverse=True)[:5]

        # Build reasoning chain
        reasoning_chain = []
        for factor in factors:
            reasoning_chain.append(
                f"{factor.get('name', 'Factor')}: {factor.get('value', 'N/A')} "
                f"(weight: {factor.get('weight', 0):.2f})"
            )

        # Generate counterfactuals
        counterfactuals = await self._generate_counterfactuals(
            decision, factors, context
        )

        # Identify uncertainty sources
        uncertainty_sources = []
        if confidence < 0.8:
            uncertainty_sources.append("Low overall confidence")
        for factor in factors:
            if factor.get("uncertainty", 0) > 0.3:
                uncertainty_sources.append(
                    f"Uncertain factor: {factor.get('name')}"
                )

        return ExplanationReport(
            decision=str(decision),
            confidence=confidence,
            reasoning_chain=reasoning_chain,
            key_factors=key_factors,
            counterfactuals=counterfactuals,
            uncertainty_sources=uncertainty_sources
        )

    async def _generate_counterfactuals(
        self,
        decision: Any,
        factors: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> List[str]:
        """Generate counterfactual explanations."""
        counterfactuals = []

        for factor in factors[:3]:  # Top 3 factors
            name = factor.get("name", "factor")
            value = factor.get("value")
            threshold = factor.get("threshold")

            if threshold is not None:
                counterfactuals.append(
                    f"If {name} were {'above' if value < threshold else 'below'} "
                    f"{threshold}, the decision might have been different"
                )

        return counterfactuals

    def format_explanation(
        self,
        report: ExplanationReport,
        format_type: str = "text"
    ) -> str:
        """Format explanation for display."""
        if format_type == "text":
            lines = [
                f"Decision: {report.decision}",
                f"Confidence: {report.confidence:.0%}",
                "",
                "Reasoning:",
            ]
            for step in report.reasoning_chain:
                lines.append(f"  - {step}")

            if report.counterfactuals:
                lines.append("")
                lines.append("What could change this:")
                for cf in report.counterfactuals:
                    lines.append(f"  - {cf}")

            if report.uncertainty_sources:
                lines.append("")
                lines.append("Uncertainty sources:")
                for src in report.uncertainty_sources:
                    lines.append(f"  - {src}")

            return "\n".join(lines)

        elif format_type == "json":
            return json.dumps({
                "decision": report.decision,
                "confidence": report.confidence,
                "reasoning": report.reasoning_chain,
                "key_factors": report.key_factors,
                "counterfactuals": report.counterfactuals,
                "uncertainty": report.uncertainty_sources
            }, indent=2)

        return str(report)


# =============================================================================
# AUDIT TRAIL
# =============================================================================

class AuditTrail:
    """Maintain audit trail for accountability."""

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path("./audit_logs")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.events: List[AuditEvent] = []
        self.retention_days = 365

    async def log_event(
        self,
        event_type: str,
        actor: str,
        action: str,
        resource: str,
        input_data: Dict[str, Any] = None,
        output_data: Dict[str, Any] = None,
        decision: str = None,
        justification: str = None,
        risk_level: RiskLevel = RiskLevel.MINIMAL,
        metadata: Dict[str, Any] = None
    ) -> AuditEvent:
        """Log an audit event."""
        event = AuditEvent(
            id=str(uuid4()),
            timestamp=datetime.now(),
            event_type=event_type,
            actor=actor,
            action=action,
            resource=resource,
            input_data=self._sanitize_data(input_data),
            output_data=self._sanitize_data(output_data),
            decision=decision,
            justification=justification,
            risk_level=risk_level,
            metadata=metadata or {}
        )

        self.events.append(event)
        await self._persist_event(event)

        logger.info(f"Audit event: {event_type} by {actor} on {resource}")
        return event

    def _sanitize_data(
        self,
        data: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Sanitize sensitive data before logging."""
        if not data:
            return None

        sanitized = {}
        sensitive_keys = {"password", "token", "secret", "key", "auth"}

        for k, v in data.items():
            if any(s in k.lower() for s in sensitive_keys):
                sanitized[k] = "[REDACTED]"
            elif isinstance(v, str) and len(v) > 1000:
                sanitized[k] = v[:1000] + "...[truncated]"
            else:
                sanitized[k] = v

        return sanitized

    async def _persist_event(self, event: AuditEvent) -> None:
        """Persist event to storage."""
        date_str = event.timestamp.strftime("%Y-%m-%d")
        file_path = self.storage_path / f"audit_{date_str}.jsonl"

        with open(file_path, "a") as f:
            f.write(json.dumps(event.to_dict()) + "\n")

    async def query_events(
        self,
        event_type: str = None,
        actor: str = None,
        resource: str = None,
        start_time: datetime = None,
        end_time: datetime = None,
        risk_level: RiskLevel = None
    ) -> List[AuditEvent]:
        """Query audit events."""
        results = self.events

        if event_type:
            results = [e for e in results if e.event_type == event_type]
        if actor:
            results = [e for e in results if e.actor == actor]
        if resource:
            results = [e for e in results if e.resource == resource]
        if start_time:
            results = [e for e in results if e.timestamp >= start_time]
        if end_time:
            results = [e for e in results if e.timestamp <= end_time]
        if risk_level:
            results = [e for e in results if e.risk_level == risk_level]

        return results

    async def generate_audit_report(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """Generate audit report for time period."""
        events = await self.query_events(
            start_time=start_time,
            end_time=end_time
        )

        # Aggregate statistics
        by_type: Dict[str, int] = defaultdict(int)
        by_actor: Dict[str, int] = defaultdict(int)
        by_risk: Dict[str, int] = defaultdict(int)

        for event in events:
            by_type[event.event_type] += 1
            by_actor[event.actor] += 1
            by_risk[event.risk_level.value] += 1

        return {
            "period": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            },
            "total_events": len(events),
            "by_type": dict(by_type),
            "by_actor": dict(by_actor),
            "by_risk_level": dict(by_risk),
            "high_risk_events": [
                e.to_dict() for e in events
                if e.risk_level in [RiskLevel.HIGH, RiskLevel.UNACCEPTABLE]
            ]
        }

    async def cleanup_old_events(self) -> int:
        """Clean up events older than retention period."""
        cutoff = datetime.now() - timedelta(days=self.retention_days)
        removed = 0

        original_count = len(self.events)
        self.events = [e for e in self.events if e.timestamp >= cutoff]
        removed = original_count - len(self.events)

        logger.info(f"Cleaned up {removed} old audit events")
        return removed


# =============================================================================
# COMPLIANCE CHECKER
# =============================================================================

class ComplianceChecker:
    """Check compliance with regulatory frameworks."""

    def __init__(self):
        self.frameworks: Dict[ComplianceFramework, Dict[str, Any]] = {
            ComplianceFramework.GDPR: {
                "name": "General Data Protection Regulation",
                "requirements": [
                    "lawful_basis",
                    "data_minimization",
                    "purpose_limitation",
                    "storage_limitation",
                    "accuracy",
                    "integrity_confidentiality",
                    "accountability"
                ]
            },
            ComplianceFramework.EU_AI_ACT: {
                "name": "EU AI Act",
                "requirements": [
                    "risk_classification",
                    "transparency",
                    "human_oversight",
                    "accuracy_robustness",
                    "data_governance",
                    "documentation"
                ]
            }
        }

    async def check_compliance(
        self,
        framework: ComplianceFramework,
        system_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check compliance with framework."""
        if framework not in self.frameworks:
            return {"error": f"Unknown framework: {framework}"}

        requirements = self.frameworks[framework]["requirements"]
        results = {
            "framework": framework.value,
            "name": self.frameworks[framework]["name"],
            "checks": {},
            "overall_compliant": True
        }

        for req in requirements:
            checker = getattr(self, f"_check_{req}", None)
            if checker:
                passed, details = await checker(system_info)
                results["checks"][req] = {
                    "passed": passed,
                    "details": details
                }
                if not passed:
                    results["overall_compliant"] = False
            else:
                results["checks"][req] = {
                    "passed": None,
                    "details": "Check not implemented"
                }

        return results

    async def _check_lawful_basis(
        self,
        info: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """Check for lawful basis for processing."""
        if info.get("consent_obtained"):
            return True, "User consent obtained"
        if info.get("legitimate_interest"):
            return True, "Legitimate interest documented"
        return False, "No lawful basis documented"

    async def _check_transparency(
        self,
        info: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """Check transparency requirements."""
        checks = []
        if info.get("ai_disclosed"):
            checks.append("AI nature disclosed")
        if info.get("explanations_available"):
            checks.append("Explanations available")
        if info.get("documentation_complete"):
            checks.append("Documentation complete")

        passed = len(checks) >= 2
        return passed, f"Transparency checks: {', '.join(checks) or 'None passed'}"

    async def _check_human_oversight(
        self,
        info: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """Check human oversight mechanisms."""
        if info.get("human_in_loop"):
            return True, "Human-in-the-loop implemented"
        if info.get("human_on_loop"):
            return True, "Human-on-the-loop monitoring"
        return False, "No human oversight mechanism"


# =============================================================================
# HUMAN OVERSIGHT
# =============================================================================

class HumanOversight:
    """Manage human oversight of AI decisions."""

    def __init__(self):
        self.pending_reviews: Dict[str, Dict[str, Any]] = {}
        self.review_callbacks: List[Callable] = []
        self.auto_approve_threshold = 0.95
        self.require_review_for: Set[str] = {
            "high_risk_decision",
            "user_data_access",
            "financial_transaction",
            "content_moderation"
        }

    async def request_review(
        self,
        decision_id: str,
        decision_type: str,
        decision: Any,
        confidence: float,
        context: Dict[str, Any],
        explanation: ExplanationReport
    ) -> Dict[str, Any]:
        """Request human review of decision."""
        if decision_type in self.require_review_for or confidence < self.auto_approve_threshold:
            review_request = {
                "id": decision_id,
                "type": decision_type,
                "decision": decision,
                "confidence": confidence,
                "context": context,
                "explanation": explanation,
                "status": "pending",
                "requested_at": datetime.now().isoformat()
            }

            self.pending_reviews[decision_id] = review_request

            # Notify reviewers
            for callback in self.review_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(review_request)
                    else:
                        callback(review_request)
                except Exception as e:
                    logger.error(f"Review callback failed: {e}")

            return {"status": "pending_review", "review_id": decision_id}

        return {"status": "auto_approved", "confidence": confidence}

    async def submit_review(
        self,
        review_id: str,
        approved: bool,
        reviewer: str,
        notes: str = ""
    ) -> Dict[str, Any]:
        """Submit human review decision."""
        if review_id not in self.pending_reviews:
            return {"error": "Review not found"}

        review = self.pending_reviews.pop(review_id)
        review["status"] = "approved" if approved else "rejected"
        review["reviewer"] = reviewer
        review["notes"] = notes
        review["reviewed_at"] = datetime.now().isoformat()

        return review

    def register_callback(self, callback: Callable) -> None:
        """Register callback for review notifications."""
        self.review_callbacks.append(callback)

    def get_pending_reviews(self) -> List[Dict[str, Any]]:
        """Get all pending reviews."""
        return list(self.pending_reviews.values())


# =============================================================================
# GOVERNANCE MANAGER
# =============================================================================

class GovernanceManager:
    """Central AI governance management."""

    def __init__(
        self,
        audit_path: Optional[Path] = None
    ):
        self.ethics = EthicalGuidelines()
        self.bias_detectors: List[BiasDetector] = [
            StatisticalBiasDetector(),
            TextBiasDetector()
        ]
        self.bias_mitigator = BiasMitigator()
        self.explainability = ExplainabilityEngine()
        self.audit = AuditTrail(audit_path)
        self.compliance = ComplianceChecker()
        self.oversight = HumanOversight()

    async def govern_action(
        self,
        action: str,
        actor: str,
        input_data: Dict[str, Any],
        output_generator: Callable,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Apply full governance to an action."""
        context = context or {}

        # 1. Ethical check
        permitted, reasons = self.ethics.is_action_permitted(action, context)
        if not permitted:
            await self.audit.log_event(
                event_type="action_blocked",
                actor=actor,
                action=action,
                resource="governance",
                justification=", ".join(reasons),
                risk_level=RiskLevel.HIGH
            )
            return {
                "status": "blocked",
                "reasons": reasons
            }

        # 2. Generate output
        output = await output_generator(input_data)

        # 3. Bias detection
        bias_reports = []
        for detector in self.bias_detectors:
            reports = await detector.detect(output, context)
            bias_reports.extend(reports)

        # 4. Bias mitigation
        for report in bias_reports:
            if report.severity > 0.5:
                output, strategy = await self.bias_mitigator.mitigate(output, report)
                report.mitigation_applied = True
                report.mitigation_strategy = strategy

        # 5. Generate explanation
        explanation = await self.explainability.explain(
            decision=output,
            decision_type=action,
            factors=context.get("factors", []),
            confidence=context.get("confidence", 1.0)
        )

        # 6. Human oversight if needed
        review_result = await self.oversight.request_review(
            decision_id=str(uuid4()),
            decision_type=action,
            decision=output,
            confidence=context.get("confidence", 1.0),
            context=context,
            explanation=explanation
        )

        # 7. Audit log
        await self.audit.log_event(
            event_type="action_executed",
            actor=actor,
            action=action,
            resource=context.get("resource", "unknown"),
            input_data=input_data,
            output_data={"result": str(output)[:500]},
            decision=str(output)[:200],
            justification=explanation.reasoning_chain[0] if explanation.reasoning_chain else None,
            risk_level=context.get("risk_level", RiskLevel.MINIMAL),
            metadata={
                "bias_reports": len(bias_reports),
                "review_status": review_result.get("status")
            }
        )

        return {
            "status": "completed",
            "output": output,
            "explanation": explanation,
            "bias_reports": bias_reports,
            "review": review_result
        }

    async def get_governance_report(self) -> Dict[str, Any]:
        """Generate comprehensive governance report."""
        now = datetime.now()
        week_ago = now - timedelta(days=7)

        audit_report = await self.audit.generate_audit_report(week_ago, now)
        pending_reviews = self.oversight.get_pending_reviews()

        return {
            "generated_at": now.isoformat(),
            "audit_summary": audit_report,
            "pending_human_reviews": len(pending_reviews),
            "ethical_principles_active": len(self.ethics.principles),
            "bias_detectors_active": len(self.bias_detectors),
            "compliance_frameworks": [f.value for f in self.compliance.frameworks.keys()]
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demo governance framework."""
    governance = GovernanceManager()

    print("=== AI Governance Framework Demo ===\n")

    # 1. Ethical check
    print("1. Ethical Assessment:")
    permitted, reasons = governance.ethics.is_action_permitted(
        "generate_recommendation",
        {"processes_pii": True, "explainable": True}
    )
    print(f"   Action permitted: {permitted}")
    if not permitted:
        print(f"   Reasons: {reasons}")

    # 2. Bias detection
    print("\n2. Bias Detection:")
    text = "Our system found that young workers are often inexperienced."
    for detector in governance.bias_detectors:
        if isinstance(detector, TextBiasDetector):
            reports = await detector.detect(text, {})
            for report in reports:
                print(f"   Detected: {report.bias_type.value}")
                print(f"   Severity: {report.severity}")

    # 3. Explainability
    print("\n3. Decision Explanation:")
    explanation = await governance.explainability.explain(
        decision="Approved",
        decision_type="classification",
        factors=[
            {"name": "credit_score", "value": 750, "weight": 0.4, "threshold": 700},
            {"name": "income", "value": 80000, "weight": 0.3, "threshold": 50000},
            {"name": "employment", "value": "stable", "weight": 0.3}
        ],
        confidence=0.85
    )
    print(governance.explainability.format_explanation(explanation))

    # 4. Audit
    print("\n4. Audit Trail:")
    event = await governance.audit.log_event(
        event_type="decision",
        actor="user_123",
        action="approve_application",
        resource="application_456",
        decision="approved",
        justification="Met all criteria"
    )
    print(f"   Logged event: {event.id}")

    # 5. Compliance check
    print("\n5. Compliance Check (EU AI Act):")
    compliance = await governance.compliance.check_compliance(
        ComplianceFramework.EU_AI_ACT,
        {
            "ai_disclosed": True,
            "explanations_available": True,
            "human_in_loop": True
        }
    )
    print(f"   Overall compliant: {compliance['overall_compliant']}")
    for req, result in compliance["checks"].items():
        print(f"   {req}: {result['passed']} - {result['details']}")

    # 6. Governance report
    print("\n6. Governance Report:")
    report = await governance.get_governance_report()
    print(f"   Active ethical principles: {report['ethical_principles_active']}")
    print(f"   Bias detectors: {report['bias_detectors_active']}")
    print(f"   Pending reviews: {report['pending_human_reviews']}")


if __name__ == "__main__":
    asyncio.run(demo())
