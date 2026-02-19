"""
⚡ META-INTELLIGENCE ⚡
======================
Intelligence about intelligence.

Features:
- Self-understanding
- Capability modeling
- Recursive enhancement
- Meta-optimization
"""

import math
import numpy as np
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from collections import defaultdict
import uuid


class IntelligenceLevel(Enum):
    """Levels of intelligence"""
    REACTIVE = auto()     # Simple stimulus-response
    ADAPTIVE = auto()     # Learning from environment
    STRATEGIC = auto()    # Long-term planning
    CREATIVE = auto()     # Generating novel solutions
    REFLECTIVE = auto()   # Self-awareness
    META = auto()         # Reasoning about own cognition
    TRANSCENDENT = auto() # Beyond categorization


class CapabilityDomain(Enum):
    """Domains of capability"""
    LOGICAL = auto()
    MATHEMATICAL = auto()
    LINGUISTIC = auto()
    SPATIAL = auto()
    SOCIAL = auto()
    CREATIVE = auto()
    META = auto()


@dataclass
class CognitiveCapability:
    """A cognitive capability"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    domain: CapabilityDomain = CapabilityDomain.LOGICAL

    # Proficiency (0-1)
    proficiency: float = 0.5

    # Growth potential
    potential: float = 1.0

    # Dependencies
    prerequisites: Set[str] = field(default_factory=set)

    # Usage statistics
    times_used: int = 0
    success_rate: float = 0.0


@dataclass
class IntelligenceProfile:
    """Profile of intelligence characteristics"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Current level
    level: IntelligenceLevel = IntelligenceLevel.ADAPTIVE

    # Capabilities
    capabilities: Dict[str, CognitiveCapability] = field(default_factory=dict)

    # Metrics
    general_intelligence: float = 0.5
    fluid_intelligence: float = 0.5
    crystallized_intelligence: float = 0.5
    creative_intelligence: float = 0.5
    meta_intelligence: float = 0.5

    # Growth trajectory
    growth_rate: float = 0.01

    def get_overall_intelligence(self) -> float:
        """Calculate overall intelligence score"""
        factors = [
            self.general_intelligence,
            self.fluid_intelligence,
            self.crystallized_intelligence,
            self.creative_intelligence,
            self.meta_intelligence
        ]
        return sum(factors) / len(factors)

    def add_capability(self, capability: CognitiveCapability):
        """Add capability to profile"""
        self.capabilities[capability.id] = capability

    def get_capability(self, name: str) -> Optional[CognitiveCapability]:
        """Get capability by name"""
        for cap in self.capabilities.values():
            if cap.name == name:
                return cap
        return None


class MetaIntelligence:
    """
    Intelligence about intelligence.
    """

    def __init__(self):
        self.profile = IntelligenceProfile()

        # Self-model
        self.self_model: Dict[str, Any] = {
            'strengths': [],
            'weaknesses': [],
            'blind_spots': [],
            'growth_areas': [],
        }

        # Meta-observations
        self.observations: List[Dict[str, Any]] = []

    def observe_self(self) -> Dict[str, Any]:
        """Observe own cognitive state"""
        observation = {
            'level': self.profile.level.name,
            'overall_intelligence': self.profile.get_overall_intelligence(),
            'capabilities_count': len(self.profile.capabilities),
            'meta_awareness': self.profile.meta_intelligence,
        }
        self.observations.append(observation)
        return observation

    def analyze_capabilities(self) -> Dict[str, Any]:
        """Analyze own capabilities"""
        if not self.profile.capabilities:
            return {'analysis': 'No capabilities registered'}

        # Group by domain
        by_domain = defaultdict(list)
        for cap in self.profile.capabilities.values():
            by_domain[cap.domain].append(cap)

        # Find strengths
        strengths = [
            cap for cap in self.profile.capabilities.values()
            if cap.proficiency >= 0.8
        ]

        # Find weaknesses
        weaknesses = [
            cap for cap in self.profile.capabilities.values()
            if cap.proficiency < 0.3
        ]

        # Update self-model
        self.self_model['strengths'] = [s.name for s in strengths]
        self.self_model['weaknesses'] = [w.name for w in weaknesses]

        return {
            'domains': {d.name: len(caps) for d, caps in by_domain.items()},
            'strengths': [s.name for s in strengths],
            'weaknesses': [w.name for w in weaknesses],
            'growth_areas': [
                cap.name for cap in self.profile.capabilities.values()
                if cap.potential > cap.proficiency + 0.3
            ]
        }

    def identify_blind_spots(self) -> List[str]:
        """Identify cognitive blind spots"""
        blind_spots = []

        # Check for missing domains
        covered_domains = {
            cap.domain for cap in self.profile.capabilities.values()
        }

        for domain in CapabilityDomain:
            if domain not in covered_domains:
                blind_spots.append(f"No capabilities in {domain.name}")

        # Check for dependencies without prerequisites
        for cap in self.profile.capabilities.values():
            for prereq in cap.prerequisites:
                if prereq not in self.profile.capabilities:
                    blind_spots.append(f"Missing prerequisite: {prereq}")

        self.self_model['blind_spots'] = blind_spots
        return blind_spots

    def suggest_improvements(self) -> List[Dict[str, Any]]:
        """Suggest improvements based on self-analysis"""
        suggestions = []

        # Analyze current state
        analysis = self.analyze_capabilities()
        blind_spots = self.identify_blind_spots()

        # Suggest addressing weaknesses
        for weakness in analysis.get('weaknesses', []):
            suggestions.append({
                'type': 'improve_weakness',
                'capability': weakness,
                'action': f"Practice and study to improve {weakness}",
                'priority': 'high'
            })

        # Suggest addressing blind spots
        for blind_spot in blind_spots:
            suggestions.append({
                'type': 'address_blind_spot',
                'issue': blind_spot,
                'action': 'Develop awareness and capability',
                'priority': 'medium'
            })

        # Suggest maximizing strengths
        for strength in analysis.get('strengths', []):
            suggestions.append({
                'type': 'leverage_strength',
                'capability': strength,
                'action': f"Apply {strength} to new domains",
                'priority': 'low'
            })

        return suggestions

    def evolve_level(self) -> bool:
        """Attempt to evolve to higher intelligence level"""
        current_idx = list(IntelligenceLevel).index(self.profile.level)

        if current_idx >= len(IntelligenceLevel) - 1:
            return False  # Already at highest level

        # Check if ready for evolution
        required_intelligence = (current_idx + 1) / len(IntelligenceLevel)

        if self.profile.get_overall_intelligence() >= required_intelligence:
            self.profile.level = list(IntelligenceLevel)[current_idx + 1]
            return True

        return False


class RecursiveEnhancement:
    """
    Self-improving enhancement system.
    """

    def __init__(self, meta_intelligence: MetaIntelligence = None):
        self.meta = meta_intelligence or MetaIntelligence()

        # Enhancement history
        self.history: List[Dict[str, Any]] = []

        # Enhancement strategies
        self.strategies = {
            'practice': self._practice_enhancement,
            'integration': self._integration_enhancement,
            'abstraction': self._abstraction_enhancement,
            'synthesis': self._synthesis_enhancement,
            'meta_learning': self._meta_learning_enhancement,
        }

    def enhance(
        self,
        capability_id: str,
        strategy: str = 'practice'
    ) -> Dict[str, Any]:
        """Enhance a capability"""
        cap = self.meta.profile.capabilities.get(capability_id)
        if not cap:
            return {'success': False, 'error': 'Capability not found'}

        if strategy in self.strategies:
            result = self.strategies[strategy](cap)
        else:
            result = self._practice_enhancement(cap)

        self.history.append({
            'capability': capability_id,
            'strategy': strategy,
            'result': result
        })

        return result

    def _practice_enhancement(
        self,
        cap: CognitiveCapability
    ) -> Dict[str, Any]:
        """Enhance through practice"""
        old_proficiency = cap.proficiency
        improvement = 0.05 * (cap.potential - cap.proficiency)
        cap.proficiency = min(cap.potential, cap.proficiency + improvement)
        cap.times_used += 1

        return {
            'success': True,
            'strategy': 'practice',
            'old_proficiency': old_proficiency,
            'new_proficiency': cap.proficiency,
            'improvement': cap.proficiency - old_proficiency
        }

    def _integration_enhancement(
        self,
        cap: CognitiveCapability
    ) -> Dict[str, Any]:
        """Enhance through integration with other capabilities"""
        # Find related capabilities
        related = [
            c for c in self.meta.profile.capabilities.values()
            if c.domain == cap.domain and c.id != cap.id
        ]

        if related:
            # Boost from related capabilities
            avg_related = sum(c.proficiency for c in related) / len(related)
            boost = 0.1 * (avg_related - cap.proficiency)
            cap.proficiency = min(cap.potential, cap.proficiency + max(0, boost))

        return {
            'success': True,
            'strategy': 'integration',
            'related_count': len(related),
            'new_proficiency': cap.proficiency
        }

    def _abstraction_enhancement(
        self,
        cap: CognitiveCapability
    ) -> Dict[str, Any]:
        """Enhance through abstraction"""
        # Raise potential through abstraction
        cap.potential = min(1.0, cap.potential * 1.1)
        cap.proficiency = min(cap.potential, cap.proficiency * 1.05)

        return {
            'success': True,
            'strategy': 'abstraction',
            'new_potential': cap.potential,
            'new_proficiency': cap.proficiency
        }

    def _synthesis_enhancement(
        self,
        cap: CognitiveCapability
    ) -> Dict[str, Any]:
        """Enhance through synthesis"""
        # Create higher-order capability
        cap.proficiency = min(cap.potential, cap.proficiency * 1.15)

        return {
            'success': True,
            'strategy': 'synthesis',
            'synthesis_level': 'higher_order',
            'new_proficiency': cap.proficiency
        }

    def _meta_learning_enhancement(
        self,
        cap: CognitiveCapability
    ) -> Dict[str, Any]:
        """Enhance through meta-learning"""
        # Learn how to learn this capability better
        self.meta.profile.meta_intelligence = min(
            1.0,
            self.meta.profile.meta_intelligence * 1.05
        )

        cap.proficiency = min(cap.potential, cap.proficiency * 1.1)

        return {
            'success': True,
            'strategy': 'meta_learning',
            'meta_intelligence': self.meta.profile.meta_intelligence,
            'new_proficiency': cap.proficiency
        }

    def recursive_enhance_all(
        self,
        iterations: int = 10
    ) -> Dict[str, float]:
        """Recursively enhance all capabilities"""
        initial_proficiencies = {
            cap.name: cap.proficiency
            for cap in self.meta.profile.capabilities.values()
        }

        for _ in range(iterations):
            for cap_id in self.meta.profile.capabilities:
                # Rotate through strategies
                strategies = list(self.strategies.keys())
                strategy = strategies[_ % len(strategies)]
                self.enhance(cap_id, strategy)

        final_proficiencies = {
            cap.name: cap.proficiency
            for cap in self.meta.profile.capabilities.values()
        }

        return {
            'initial': initial_proficiencies,
            'final': final_proficiencies,
            'iterations': iterations
        }


# Export all
__all__ = [
    'IntelligenceLevel',
    'CapabilityDomain',
    'CognitiveCapability',
    'IntelligenceProfile',
    'MetaIntelligence',
    'RecursiveEnhancement',
]
