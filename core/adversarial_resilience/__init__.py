"""
⚡ ADVERSARIAL RESILIENCE MATRIX ⚡
===================================
Self-defense and robustness systems.

Features:
- Attack detection
- Adversarial robustness
- Self-healing mechanisms
- Threat analysis
"""

from .adversarial_core import (
    Threat,
    ThreatType,
    ThreatLevel,
    Attack,
    Defense,
    SecurityState,
    ThreatDetector,
)

from .robustness import (
    RobustnessMetric,
    InputValidator,
    OutputSanitizer,
    PerturbationDetector,
    AdversarialDefense,
)

from .self_healing import (
    HealthCheck,
    RecoveryAction,
    SelfHealingSystem,
    RedundancyManager,
    GracefulDegradation,
)

from .threat_intelligence import (
    ThreatSignature,
    ThreatDatabase,
    ThreatAnalyzer,
    RiskAssessment,
    SecurityOrchestrator,
)

__all__ = [
    # Adversarial Core
    'Threat',
    'ThreatType',
    'ThreatLevel',
    'Attack',
    'Defense',
    'SecurityState',
    'ThreatDetector',

    # Robustness
    'RobustnessMetric',
    'InputValidator',
    'OutputSanitizer',
    'PerturbationDetector',
    'AdversarialDefense',

    # Self-Healing
    'HealthCheck',
    'RecoveryAction',
    'SelfHealingSystem',
    'RedundancyManager',
    'GracefulDegradation',

    # Threat Intelligence
    'ThreatSignature',
    'ThreatDatabase',
    'ThreatAnalyzer',
    'RiskAssessment',
    'SecurityOrchestrator',
]
