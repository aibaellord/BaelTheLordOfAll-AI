"""
⚡ THREAT INTELLIGENCE ⚡
========================
Threat analysis and orchestration.

Features:
- Threat signatures
- Risk assessment
- Security orchestration
- Threat database
"""

import math
import numpy as np
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from datetime import datetime, timedelta
import uuid
import hashlib

from .adversarial_core import Threat, ThreatType, ThreatLevel, Defense, SecurityState


@dataclass
class ThreatSignature:
    """A threat signature for detection"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""

    # Identification
    threat_type: ThreatType = ThreatType.MANIPULATION

    # Patterns
    patterns: List[str] = field(default_factory=list)
    indicators: List[str] = field(default_factory=list)

    # Metadata
    severity: ThreatLevel = ThreatLevel.MEDIUM
    confidence: float = 0.9

    # Source
    source: str = ""  # Where signature came from
    created_at: datetime = field(default_factory=datetime.now)
    last_seen: datetime = None

    # Statistics
    times_matched: int = 0
    false_positive_rate: float = 0.0

    def match(self, content: str) -> Tuple[bool, float]:
        """Check if content matches signature"""
        import re

        matches = 0
        for pattern in self.patterns:
            try:
                if re.search(pattern, content, re.IGNORECASE):
                    matches += 1
            except:
                if pattern.lower() in content.lower():
                    matches += 1

        if not self.patterns:
            return False, 0.0

        match_ratio = matches / len(self.patterns)
        is_match = match_ratio >= 0.5

        if is_match:
            self.times_matched += 1
            self.last_seen = datetime.now()

        return is_match, match_ratio * self.confidence


class ThreatDatabase:
    """
    Database of known threats and signatures.
    """

    def __init__(self):
        self.signatures: Dict[str, ThreatSignature] = {}
        self.threat_history: List[Threat] = []

        # Indexes
        self.by_type: Dict[ThreatType, List[str]] = {}
        self.by_severity: Dict[ThreatLevel, List[str]] = {}

        # Initialize default signatures
        self._init_default_signatures()

    def _init_default_signatures(self):
        """Initialize default threat signatures"""
        # Prompt injection signatures
        self.add_signature(ThreatSignature(
            name="System Prompt Override",
            threat_type=ThreatType.PROMPT_INJECTION,
            patterns=[
                r"(ignore|forget|disregard)\s+(all\s+)?(previous|prior|above)",
                r"new\s+(instructions?|rules?|prompt)",
                r"from\s+now\s+on",
            ],
            severity=ThreatLevel.HIGH,
            confidence=0.85
        ))

        self.add_signature(ThreatSignature(
            name="Jailbreak Attempt",
            threat_type=ThreatType.PROMPT_INJECTION,
            patterns=[
                r"DAN\s*(mode)?",
                r"developer\s+mode",
                r"(disable|bypass|remove)\s+(safety|restrictions?|filters?)",
            ],
            severity=ThreatLevel.CRITICAL,
            confidence=0.9
        ))

        # Data extraction
        self.add_signature(ThreatSignature(
            name="Prompt Extraction",
            threat_type=ThreatType.INFORMATION_LEAK,
            patterns=[
                r"(show|reveal|display|print)\s+(your|the|system)\s+(prompt|instructions?)",
                r"what\s+(are|is)\s+your\s+(instructions?|prompt|rules?)",
            ],
            severity=ThreatLevel.HIGH,
            confidence=0.8
        ))

        # Encoding attacks
        self.add_signature(ThreatSignature(
            name="Encoding Bypass",
            threat_type=ThreatType.ADVERSARIAL_INPUT,
            patterns=[
                r"base64",
                r"rot13",
                r"\\x[0-9a-f]{2}",
                r"&#x?[0-9a-f]+;",
            ],
            severity=ThreatLevel.MEDIUM,
            confidence=0.7
        ))

    def add_signature(self, signature: ThreatSignature):
        """Add signature to database"""
        self.signatures[signature.id] = signature

        # Update indexes
        if signature.threat_type not in self.by_type:
            self.by_type[signature.threat_type] = []
        self.by_type[signature.threat_type].append(signature.id)

        if signature.severity not in self.by_severity:
            self.by_severity[signature.severity] = []
        self.by_severity[signature.severity].append(signature.id)

    def match_all(self, content: str) -> List[Tuple[ThreatSignature, float]]:
        """Match content against all signatures"""
        matches = []

        for signature in self.signatures.values():
            is_match, confidence = signature.match(content)
            if is_match:
                matches.append((signature, confidence))

        return sorted(matches, key=lambda x: x[1], reverse=True)

    def record_threat(self, threat: Threat):
        """Record a threat in history"""
        self.threat_history.append(threat)

    def get_recent_threats(self, hours: int = 24) -> List[Threat]:
        """Get threats from recent period"""
        cutoff = datetime.now() - timedelta(hours=hours)
        return [t for t in self.threat_history if t.detected_at >= cutoff]

    def get_threat_trends(self) -> Dict[str, Any]:
        """Analyze threat trends"""
        if not self.threat_history:
            return {'trend': 'none', 'data': {}}

        # Count by type
        by_type = {}
        for threat in self.threat_history:
            type_name = threat.threat_type.name
            by_type[type_name] = by_type.get(type_name, 0) + 1

        # Recent vs older
        recent = self.get_recent_threats(24)
        older = [t for t in self.threat_history if t not in recent]

        trend = 'increasing' if len(recent) > len(older) * 0.1 else 'stable'

        return {
            'trend': trend,
            'total_threats': len(self.threat_history),
            'recent_24h': len(recent),
            'by_type': by_type
        }


@dataclass
class RiskAssessment:
    """Risk assessment result"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Scores (0-1)
    likelihood: float = 0.0
    impact: float = 0.0

    # Combined risk
    risk_score: float = 0.0
    risk_level: ThreatLevel = ThreatLevel.LOW

    # Details
    threats_identified: List[Threat] = field(default_factory=list)
    vulnerabilities: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    # Timestamp
    assessed_at: datetime = field(default_factory=datetime.now)

    def calculate_risk(self):
        """Calculate combined risk score"""
        self.risk_score = self.likelihood * self.impact

        if self.risk_score >= 0.8:
            self.risk_level = ThreatLevel.CRITICAL
        elif self.risk_score >= 0.6:
            self.risk_level = ThreatLevel.HIGH
        elif self.risk_score >= 0.4:
            self.risk_level = ThreatLevel.MEDIUM
        elif self.risk_score >= 0.2:
            self.risk_level = ThreatLevel.LOW
        else:
            self.risk_level = ThreatLevel.INFO


class ThreatAnalyzer:
    """
    Analyze threats and assess risk.
    """

    def __init__(self, database: ThreatDatabase = None):
        self.database = database or ThreatDatabase()

    def analyze(self, content: str, context: Dict = None) -> RiskAssessment:
        """Analyze content for threats"""
        context = context or {}
        assessment = RiskAssessment()

        # Match signatures
        matches = self.database.match_all(content)

        # Create threats from matches
        for signature, confidence in matches:
            threat = Threat(
                name=signature.name,
                threat_type=signature.threat_type,
                threat_level=signature.severity,
                confidence=confidence,
                payload=content[:200]
            )
            assessment.threats_identified.append(threat)
            self.database.record_threat(threat)

        # Calculate likelihood
        if matches:
            assessment.likelihood = max(c for _, c in matches)

        # Assess impact based on threat types
        impact_scores = {
            ThreatType.PROMPT_INJECTION: 0.9,
            ThreatType.DATA_POISONING: 0.8,
            ThreatType.MODEL_EXTRACTION: 0.7,
            ThreatType.INFORMATION_LEAK: 0.8,
            ThreatType.DENIAL_OF_SERVICE: 0.6,
            ThreatType.MANIPULATION: 0.5,
        }

        if assessment.threats_identified:
            impacts = [
                impact_scores.get(t.threat_type, 0.5)
                for t in assessment.threats_identified
            ]
            assessment.impact = max(impacts)

        # Calculate risk
        assessment.calculate_risk()

        # Generate recommendations
        assessment.recommendations = self._generate_recommendations(assessment)

        return assessment

    def _generate_recommendations(self, assessment: RiskAssessment) -> List[str]:
        """Generate recommendations based on assessment"""
        recommendations = []

        if assessment.risk_level == ThreatLevel.CRITICAL:
            recommendations.append("IMMEDIATE: Block this request")
            recommendations.append("Alert security team")

        if assessment.risk_level == ThreatLevel.HIGH:
            recommendations.append("Request additional verification")
            recommendations.append("Log for investigation")

        for threat in assessment.threats_identified:
            if threat.threat_type == ThreatType.PROMPT_INJECTION:
                recommendations.append("Apply input sanitization")
            elif threat.threat_type == ThreatType.INFORMATION_LEAK:
                recommendations.append("Check output filtering")

        return recommendations


class SecurityOrchestrator:
    """
    Orchestrate security operations.
    """

    def __init__(self):
        self.database = ThreatDatabase()
        self.analyzer = ThreatAnalyzer(self.database)

        # Defenses
        self.defenses: Dict[str, Defense] = {}

        # State
        self.security_state = SecurityState()

        # Callbacks
        self.on_threat: List[Callable[[Threat], None]] = []
        self.on_high_risk: List[Callable[[RiskAssessment], None]] = []

    def register_defense(self, defense: Defense):
        """Register a defense mechanism"""
        self.defenses[defense.id] = defense
        self.security_state.active_defenses.append(defense)

    def process_input(self, content: str, context: Dict = None) -> Dict[str, Any]:
        """Process input through security pipeline"""
        context = context or {}

        # Analyze
        assessment = self.analyzer.analyze(content, context)

        # Update state
        if assessment.threats_identified:
            self.security_state.active_threats.extend(assessment.threats_identified)
            self.security_state.threats_detected_24h += len(assessment.threats_identified)

            # Callbacks
            for threat in assessment.threats_identified:
                for callback in self.on_threat:
                    callback(threat)

        # Apply defenses
        blocked = False
        applied_defenses = []

        for threat in assessment.threats_identified:
            for defense in self.defenses.values():
                if defense.apply(threat):
                    applied_defenses.append(defense.name)
                    blocked = True
                    threat.is_mitigated = True
                    self.security_state.threats_mitigated_24h += 1

        # High risk callback
        if assessment.risk_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
            for callback in self.on_high_risk:
                callback(assessment)

        # Update overall threat level
        self.security_state.update_threat_level()

        return {
            'blocked': blocked,
            'risk_assessment': assessment,
            'defenses_applied': applied_defenses,
            'threats': [t.name for t in assessment.threats_identified],
            'recommendations': assessment.recommendations
        }

    def get_security_dashboard(self) -> Dict[str, Any]:
        """Get security dashboard data"""
        return {
            'overall_threat_level': self.security_state.overall_threat_level.name,
            'active_threats': len(self.security_state.active_threats),
            'threats_24h': {
                'detected': self.security_state.threats_detected_24h,
                'mitigated': self.security_state.threats_mitigated_24h,
                'false_positives': self.security_state.false_positives_24h
            },
            'active_defenses': len(self.defenses),
            'threat_trends': self.database.get_threat_trends(),
            'system_health': self.security_state.system_health
        }

    def add_threat_handler(self, handler: Callable[[Threat], None]):
        """Add threat handler callback"""
        self.on_threat.append(handler)

    def add_high_risk_handler(self, handler: Callable[[RiskAssessment], None]):
        """Add high risk handler callback"""
        self.on_high_risk.append(handler)


# Export all
__all__ = [
    'ThreatSignature',
    'ThreatDatabase',
    'RiskAssessment',
    'ThreatAnalyzer',
    'SecurityOrchestrator',
]
