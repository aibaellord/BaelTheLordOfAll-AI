"""
👑 CAPABILITY SYNTHESIS 👑
==========================
Synthesize new capabilities.

Features:
- Capability combination
- Emergent abilities
- Synergy detection
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from datetime import datetime
import uuid
import math

from .mastery_core import SystemCapability, CapabilityType, MasteryLevel


class SynthesisStrategy(Enum):
    """Synthesis strategies"""
    COMBINE = auto()      # Merge capabilities
    SEQUENCE = auto()     # Chain capabilities
    PARALLEL = auto()     # Run in parallel
    RECURSIVE = auto()    # Self-referential
    EMERGENT = auto()     # Discover new


@dataclass
class CapabilityCombination:
    """A combination of capabilities"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Components
    capability_ids: List[str] = field(default_factory=list)

    # Strategy
    strategy: SynthesisStrategy = SynthesisStrategy.COMBINE

    # Result
    synergy_score: float = 0.0
    combined_power: float = 0.0

    # Usage
    use_count: int = 0
    success_rate: float = 0.0


@dataclass
class EmergentCapability:
    """An emergent capability"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Identity
    name: str = ""
    description: str = ""

    # Origin
    source_capabilities: List[str] = field(default_factory=list)
    combination: Optional[CapabilityCombination] = None

    # Properties
    novelty: float = 0.0
    power: float = 0.0
    stability: float = 0.0

    # Discovered
    discovered_at: datetime = field(default_factory=datetime.now)

    def to_capability(self) -> SystemCapability:
        """Convert to system capability"""
        return SystemCapability(
            name=self.name,
            capability_type=CapabilityType.ADAPTATION,
            level=MasteryLevel(min(7, int(self.power * 7) + 1)),
            accuracy=self.stability,
            reliability=self.stability
        )


class CapabilitySynthesizer:
    """
    Synthesizes new capabilities.
    """

    def __init__(self):
        # Known capabilities
        self.capabilities: Dict[str, SystemCapability] = {}

        # Combinations tried
        self.combinations: List[CapabilityCombination] = []

        # Emergent capabilities
        self.emergent: Dict[str, EmergentCapability] = {}

        # Synergy matrix
        self.synergy_matrix: Dict[Tuple[str, str], float] = {}

        # Synthesis rules
        self.synthesis_rules: List[Callable[[List[SystemCapability]], Optional[EmergentCapability]]] = []

    def add_capability(self, capability: SystemCapability):
        """Add capability"""
        self.capabilities[capability.id] = capability

    def add_rule(
        self,
        rule: Callable[[List[SystemCapability]], Optional[EmergentCapability]]
    ):
        """Add synthesis rule"""
        self.synthesis_rules.append(rule)

    def compute_synergy(
        self,
        cap1: SystemCapability,
        cap2: SystemCapability
    ) -> float:
        """Compute synergy between capabilities"""
        key = tuple(sorted([cap1.id, cap2.id]))

        if key in self.synergy_matrix:
            return self.synergy_matrix[key]

        # Base synergy on compatibility
        synergy = 0.5

        # Same type = lower synergy (redundant)
        if cap1.capability_type == cap2.capability_type:
            synergy *= 0.7

        # Different types = higher synergy
        else:
            synergy *= 1.3

        # Level difference affects synergy
        level_diff = abs(cap1.level.value - cap2.level.value)
        synergy *= 1.0 - (level_diff * 0.1)

        # Dependency bonus
        if cap1.id in cap2.required_capabilities or cap2.id in cap1.required_capabilities:
            synergy *= 1.5

        synergy = min(1.0, max(0.0, synergy))
        self.synergy_matrix[key] = synergy

        return synergy

    def combine(
        self,
        capability_ids: List[str],
        strategy: SynthesisStrategy = SynthesisStrategy.COMBINE
    ) -> CapabilityCombination:
        """Combine capabilities"""
        capabilities = [
            self.capabilities[cid]
            for cid in capability_ids
            if cid in self.capabilities
        ]

        if len(capabilities) < 2:
            return CapabilityCombination()

        # Compute synergy
        total_synergy = 0.0
        pairs = 0

        for i, cap1 in enumerate(capabilities):
            for cap2 in capabilities[i + 1:]:
                total_synergy += self.compute_synergy(cap1, cap2)
                pairs += 1

        avg_synergy = total_synergy / pairs if pairs > 0 else 0.0

        # Compute combined power
        base_power = sum(c.get_power() for c in capabilities) / len(capabilities)

        if strategy == SynthesisStrategy.COMBINE:
            combined_power = base_power * (1 + avg_synergy)
        elif strategy == SynthesisStrategy.SEQUENCE:
            combined_power = base_power * (1 + avg_synergy * 0.5)
        elif strategy == SynthesisStrategy.PARALLEL:
            combined_power = base_power * (1 + avg_synergy * 0.8)
        elif strategy == SynthesisStrategy.RECURSIVE:
            combined_power = base_power * (1 + avg_synergy * 1.5)
        else:
            combined_power = base_power * (1 + avg_synergy * 2.0)

        combination = CapabilityCombination(
            capability_ids=capability_ids,
            strategy=strategy,
            synergy_score=avg_synergy,
            combined_power=combined_power
        )

        self.combinations.append(combination)
        return combination

    def discover_emergent(
        self,
        combination: CapabilityCombination
    ) -> Optional[EmergentCapability]:
        """Discover emergent capability"""
        capabilities = [
            self.capabilities[cid]
            for cid in combination.capability_ids
            if cid in self.capabilities
        ]

        # Apply synthesis rules
        for rule in self.synthesis_rules:
            try:
                emergent = rule(capabilities)
                if emergent:
                    emergent.combination = combination
                    emergent.source_capabilities = combination.capability_ids
                    self.emergent[emergent.id] = emergent
                    return emergent
            except Exception:
                pass

        # Default emergence if high synergy
        if combination.synergy_score > 0.7:
            cap_names = [self.capabilities[cid].name for cid in combination.capability_ids if cid in self.capabilities]

            emergent = EmergentCapability(
                name=f"Emergent_{'_'.join(cap_names[:2])}",
                description=f"Emergent from combination of {len(capabilities)} capabilities",
                source_capabilities=combination.capability_ids,
                combination=combination,
                novelty=combination.synergy_score,
                power=combination.combined_power,
                stability=0.5 + combination.synergy_score * 0.5
            )

            self.emergent[emergent.id] = emergent
            return emergent

        return None

    def find_best_combinations(
        self,
        n: int = 5,
        min_capabilities: int = 2,
        max_capabilities: int = 4
    ) -> List[CapabilityCombination]:
        """Find best capability combinations"""
        from itertools import combinations as iter_combinations

        cap_ids = list(self.capabilities.keys())
        all_combinations = []

        for size in range(min_capabilities, min(max_capabilities + 1, len(cap_ids) + 1)):
            for combo in iter_combinations(cap_ids, size):
                combination = self.combine(list(combo))
                all_combinations.append(combination)

        # Sort by combined power
        all_combinations.sort(key=lambda c: c.combined_power, reverse=True)

        return all_combinations[:n]

    def synthesize_all(self) -> List[EmergentCapability]:
        """Run full synthesis process"""
        discovered = []

        # Find best combinations
        best = self.find_best_combinations(n=10)

        # Try to discover emergent from each
        for combination in best:
            emergent = self.discover_emergent(combination)
            if emergent:
                discovered.append(emergent)

        return discovered


# Export all
__all__ = [
    'SynthesisStrategy',
    'CapabilityCombination',
    'EmergentCapability',
    'CapabilitySynthesizer',
]
